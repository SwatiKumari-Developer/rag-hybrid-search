"""
INGESTION SERVICE
-----------------
Handles the full pipeline:
  1. Parse uploaded files (PDF, TXT, DOCX)
  2. Split text into overlapping chunks
  3. Generate embeddings using Sentence-Transformers
  4. Store chunks + embeddings in PostgreSQL (pgvector)

WHY CHUNKING?
  LLMs have context window limits. Splitting docs into chunks lets us
  retrieve only the most relevant pieces instead of the full document.

WHY OVERLAPPING CHUNKS?
  Overlap ensures context isn't lost at chunk boundaries.
  e.g. chunk_size=512, overlap=64 → each chunk shares 64 tokens with neighbors.
"""

import io
import PyPDF2
import docx
import nltk
from typing import List, Tuple
from loguru import logger
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.models.document import Document
from app.models.chunk import Chunk

# Download NLTK tokenizer data (needed for sentence splitting)
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)

# Global model instance — loaded once at startup to avoid repeated disk reads
_embedding_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    """
    Lazily load the Sentence-Transformers model.
    'all-MiniLM-L6-v2' is fast, lightweight, and produces 384-dim vectors.
    It maps sentences to a dense vector space for semantic similarity search.
    """
    global _embedding_model
    if _embedding_model is None:
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        _embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info("Embedding model loaded successfully")
    return _embedding_model


# ─── File Parsing ────────────────────────────────────────────────────────────

def parse_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF using PyPDF2."""
    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append(text)
    return "\n\n".join(pages)


def parse_txt(file_bytes: bytes) -> str:
    """Decode plain text file."""
    return file_bytes.decode("utf-8", errors="replace")


def parse_docx(file_bytes: bytes) -> str:
    """Extract paragraphs from DOCX using python-docx."""
    doc = docx.Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def parse_file(filename: str, file_bytes: bytes) -> str:
    """Route to correct parser based on file extension."""
    ext = filename.lower().rsplit(".", 1)[-1]
    parsers = {
        "pdf": parse_pdf,
        "txt": parse_txt,
        "md": parse_txt,
        "docx": parse_docx,
    }
    parser = parsers.get(ext)
    if not parser:
        raise ValueError(f"Unsupported file type: .{ext}")
    return parser(file_bytes)


# ─── Chunking ────────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
    """
    Split text into overlapping chunks using a sliding window approach.

    Strategy:
      - Split text into words
      - Slide a window of `chunk_size` words with `overlap` word stride
      - This preserves context at chunk boundaries

    Alternative approaches: sentence-based chunking, semantic chunking.
    We use word-based for simplicity + speed.
    """
    chunk_size = chunk_size or settings.CHUNK_SIZE
    overlap = overlap or settings.CHUNK_OVERLAP

    words = text.split()
    if not words:
        return []

    chunks = []
    stride = chunk_size - overlap  # How far to advance the window each step

    for i in range(0, len(words), stride):
        chunk_words = words[i: i + chunk_size]
        chunk_text = " ".join(chunk_words)
        if chunk_text.strip():
            chunks.append(chunk_text)

        if len(chunks) >= settings.MAX_CHUNKS_PER_DOC:
            logger.warning(f"Reached max chunks limit ({settings.MAX_CHUNKS_PER_DOC})")
            break

    return chunks


# ─── Embedding ───────────────────────────────────────────────────────────────

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Convert a list of text strings into dense vector embeddings.

    The model encodes each chunk into a 384-dimensional float vector.
    Semantically similar texts produce vectors that are "close" in vector space,
    measured by cosine similarity (or equivalently L2 distance on normalized vectors).

    Batch processing is used for efficiency — the model processes all chunks
    in one GPU/CPU pass rather than one-by-one.
    """
    model = get_embedding_model()
    logger.info(f"Generating embeddings for {len(texts)} chunks...")

    # batch_size controls memory usage; normalize=True ensures cosine similarity
    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        normalize_embeddings=True,  # Unit vectors → cosine sim = dot product
    )
    return embeddings.tolist()


# ─── Full Ingestion Pipeline ─────────────────────────────────────────────────

def ingest_document(
    db: Session,
    document_id: str,
    filename: str,
    file_bytes: bytes,
    file_size: int,
) -> Document:
    """
    Full document ingestion pipeline:
      parse → chunk → embed → store

    This runs synchronously. For production, consider Celery + Redis task queue.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise ValueError(f"Document {document_id} not found")

    try:
        # Step 1: Parse raw text from file
        logger.info(f"Parsing {filename}...")
        raw_text = parse_file(filename, file_bytes)

        if not raw_text.strip():
            raise ValueError("Document appears to be empty or could not be parsed")

        doc.content_preview = raw_text[:500]
        doc.title = filename.rsplit(".", 1)[0].replace("_", " ").title()

        # Step 2: Chunk the text
        logger.info("Chunking text...")
        chunks = chunk_text(raw_text)
        logger.info(f"Created {len(chunks)} chunks")

        if not chunks:
            raise ValueError("No chunks generated from document")

        # Step 3: Generate embeddings for all chunks in batch
        embeddings = generate_embeddings(chunks)

        # Step 4: Store chunks + embeddings in PostgreSQL
        logger.info("Storing chunks in database...")
        chunk_objects = []
        for i, (chunk_text_val, embedding) in enumerate(zip(chunks, embeddings)):
            chunk = Chunk(
                document_id=document_id,
                chunk_index=i,
                text=chunk_text_val,
                token_count=len(chunk_text_val.split()),
                embedding=embedding,  # pgvector stores this as a vector column
                chunk_metadata={"chunk_index": i, "total_chunks": len(chunks)},
            )
            chunk_objects.append(chunk)

        db.bulk_save_objects(chunk_objects)

        # Update document status
        doc.chunk_count = len(chunks)
        doc.status = "ready"
        db.commit()

        logger.info(f"Document {filename} ingested successfully: {len(chunks)} chunks")
        return doc

    except Exception as e:
        logger.error(f"Ingestion failed for {filename}: {e}")
        doc.status = "error"
        doc.error_message = str(e)
        db.commit()
        raise
