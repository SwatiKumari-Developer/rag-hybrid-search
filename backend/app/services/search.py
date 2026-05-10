"""
HYBRID SEARCH SERVICE
---------------------
Implements a two-stage retrieval pipeline:

  Stage 1A — Dense (Semantic) Search:
    - Embed the query using the same Sentence-Transformers model
    - Find top-K chunks by cosine similarity using pgvector's <=> operator
    - Excels at: paraphrase matching, conceptual queries, synonyms

  Stage 1B — Sparse (Keyword) Search using BM25:
    - BM25 (Best Match 25) is a probabilistic keyword ranking function
    - Considers term frequency (TF) and inverse document frequency (IDF)
    - Excels at: exact matches, rare terms, technical jargon

  Stage 2 — Reciprocal Rank Fusion (RRF):
    - Merges dense + sparse rankings without needing score normalization
    - Formula: RRF(d) = Σ 1 / (k + rank_i(d))  where k=60 is a smoothing constant
    - Research shows RRF consistently outperforms individual methods
    - Returns the top-K chunks from the fused ranking

WHY HYBRID?
  Neither dense nor sparse search is universally better.
  Dense search misses exact keyword matches. Sparse search misses semantic meaning.
  Hybrid approaches reliably outperform either alone on diverse query types.
"""

from typing import List, Dict, Any, Tuple
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import text
from rank_bm25 import BM25Okapi

from app.core.config import settings
from app.models.chunk import Chunk
from app.services.ingestion import get_embedding_model


# ─── Dense (Vector) Search ───────────────────────────────────────────────────

def dense_search(
    db: Session,
    query_embedding: List[float],
    document_ids: List[str] = None,
    top_k: int = None,
) -> List[Dict[str, Any]]:
    """
    Semantic search using pgvector cosine distance.

    The SQL uses the <=> operator (cosine distance) provided by pgvector.
    Lower distance = more similar. We convert to similarity: 1 - distance.

    An IVFFlat index (if created) speeds this up via approximate search.
    Without the index, it does exact nearest-neighbor (slower but accurate).
    """
    top_k = top_k or settings.TOP_K_DENSE

    # Build the embedding as a Postgres vector literal
    embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

    # Filter by document_ids if provided (for scoped search)
    doc_filter = ""
    params = {"embedding": embedding_str, "top_k": top_k}
    if document_ids:
        doc_filter = "AND c.document_id = ANY(:doc_ids)"
        params["doc_ids"] = document_ids

    sql = text(f"""
        SELECT
            c.id,
            c.document_id,
            c.chunk_index,
            c.text,
            c.chunk_metadata,
            d.filename,
            d.title,
            1 - (c.embedding <=> :embedding::vector) AS similarity_score
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE d.status = 'ready'
          AND c.embedding IS NOT NULL
          {doc_filter}
        ORDER BY c.embedding <=> :embedding::vector
        LIMIT :top_k
    """)

    results = db.execute(sql, params).fetchall()

    return [
        {
            "chunk_id": row.id,
            "document_id": row.document_id,
            "chunk_index": row.chunk_index,
            "text": row.text,
            "metadata": row.chunk_metadata,
            "filename": row.filename,
            "title": row.title,
            "dense_score": float(row.similarity_score),
        }
        for row in results
    ]


# ─── Sparse (BM25) Search ────────────────────────────────────────────────────

def sparse_search(
    db: Session,
    query: str,
    document_ids: List[str] = None,
    top_k: int = None,
) -> List[Dict[str, Any]]:
    """
    Keyword search using BM25 (Okapi BM25).

    BM25 ranks documents based on:
    - Term Frequency (TF): how often query terms appear in a chunk
    - Inverse Document Frequency (IDF): penalizes common words
    - Document length normalization: longer docs don't get unfair advantage

    We load all chunks from DB into memory and run BM25 over them.
    For very large corpora, consider Elasticsearch or a dedicated BM25 index.
    """
    top_k = top_k or settings.TOP_K_SPARSE

    # Fetch all chunks (with optional document filter)
    query_obj = db.query(Chunk).join(Chunk.document)
    if document_ids:
        query_obj = query_obj.filter(Chunk.document_id.in_(document_ids))

    chunks = query_obj.all()
    if not chunks:
        return []

    # Tokenize chunks (simple whitespace split; improve with NLTK for production)
    tokenized_corpus = [chunk.text.lower().split() for chunk in chunks]
    tokenized_query = query.lower().split()

    # Build BM25 index
    bm25 = BM25Okapi(tokenized_corpus)

    # Score all chunks against the query
    scores = bm25.get_scores(tokenized_query)

    # Get top-K by BM25 score
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    results = []
    for rank, idx in enumerate(top_indices):
        if scores[idx] <= 0:
            continue  # Skip irrelevant chunks
        chunk = chunks[idx]
        results.append({
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "chunk_index": chunk.chunk_index,
            "text": chunk.text,
            "metadata": chunk.chunk_metadata,
            "filename": chunk.document.filename,
            "title": chunk.document.title,
            "sparse_score": float(scores[idx]),
        })

    return results


# ─── Reciprocal Rank Fusion ───────────────────────────────────────────────────

def reciprocal_rank_fusion(
    dense_results: List[Dict],
    sparse_results: List[Dict],
    k: int = 60,
    dense_weight: float = None,
    sparse_weight: float = None,
) -> List[Dict[str, Any]]:
    """
    Merge dense and sparse rankings using Reciprocal Rank Fusion.

    RRF Formula: score(d) = Σ weight_i / (k + rank_i(d))

    Where:
    - k=60 is a smoothing constant (prevents very high scores for top-ranked docs)
    - rank_i(d) is the 1-based rank of document d in list i
    - weight_i controls how much each retriever contributes

    Why RRF over score averaging?
    - Scores from BM25 and cosine similarity are in different ranges (not comparable)
    - RRF uses ranks, which are universally comparable
    - No need for score normalization
    - Proven to be robust across diverse retrieval tasks (Cormack et al., 2009)
    """
    dense_weight = dense_weight or settings.DENSE_WEIGHT
    sparse_weight = sparse_weight or settings.SPARSE_WEIGHT

    fused_scores: Dict[str, float] = {}
    chunk_data: Dict[str, Dict] = {}

    # Score dense results
    for rank, result in enumerate(dense_results, start=1):
        cid = result["chunk_id"]
        rrf_score = dense_weight / (k + rank)
        fused_scores[cid] = fused_scores.get(cid, 0.0) + rrf_score
        if cid not in chunk_data:
            chunk_data[cid] = {**result, "dense_rank": rank, "sparse_rank": None}
        chunk_data[cid]["dense_rank"] = rank

    # Score sparse results
    for rank, result in enumerate(sparse_results, start=1):
        cid = result["chunk_id"]
        rrf_score = sparse_weight / (k + rank)
        fused_scores[cid] = fused_scores.get(cid, 0.0) + rrf_score
        if cid not in chunk_data:
            chunk_data[cid] = {**result, "dense_rank": None, "sparse_rank": rank}
        chunk_data[cid]["sparse_rank"] = rank

    # Sort by fused RRF score (descending)
    ranked = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)

    fused_results = []
    for chunk_id, rrf_score in ranked:
        entry = chunk_data[chunk_id].copy()
        entry["rrf_score"] = rrf_score
        entry["retrieval_method"] = _get_retrieval_method(entry)
        fused_results.append(entry)

    return fused_results


def _get_retrieval_method(result: Dict) -> str:
    """Describe how a chunk was retrieved (for transparency in UI)."""
    has_dense = result.get("dense_rank") is not None
    has_sparse = result.get("sparse_rank") is not None
    if has_dense and has_sparse:
        return "hybrid"
    elif has_dense:
        return "semantic"
    else:
        return "keyword"


# ─── Full Hybrid Search ───────────────────────────────────────────────────────

def hybrid_search(
    db: Session,
    query: str,
    document_ids: List[str] = None,
    top_k: int = None,
) -> Tuple[List[Dict], Dict[str, Any]]:
    """
    Full hybrid search pipeline.

    Returns:
      - List of top-K retrieved chunks with scores
      - Debug info dict with intermediate results
    """
    top_k = top_k or settings.TOP_K_FINAL
    model = get_embedding_model()

    # 1. Embed the query (same model used during ingestion)
    query_embedding = model.encode(
        [query],
        normalize_embeddings=True,
    )[0].tolist()

    # 2. Dense search (semantic/vector)
    logger.info(f"Running dense search for: '{query}'")
    dense_results = dense_search(db, query_embedding, document_ids)
    logger.info(f"Dense search returned {len(dense_results)} results")

    # 3. Sparse search (BM25/keyword)
    logger.info("Running sparse search (BM25)...")
    sparse_results = sparse_search(db, query, document_ids)
    logger.info(f"Sparse search returned {len(sparse_results)} results")

    # 4. Fuse with RRF
    fused = reciprocal_rank_fusion(dense_results, sparse_results)
    final_results = fused[:top_k]

    debug_info = {
        "query": query,
        "dense_count": len(dense_results),
        "sparse_count": len(sparse_results),
        "fused_count": len(fused),
        "final_count": len(final_results),
        "dense_weight": settings.DENSE_WEIGHT,
        "sparse_weight": settings.SPARSE_WEIGHT,
    }

    return final_results, debug_info
