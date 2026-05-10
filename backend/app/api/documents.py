"""
DOCUMENTS API ROUTER
--------------------
Handles document upload and management endpoints.

FastAPI Routers are like Express.js routers or Django URL patterns —
they group related endpoints and can be mounted at a URL prefix.
"""

import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from loguru import logger
from typing import List

from app.core.database import get_db
from app.models.document import Document
from app.services.ingestion import ingest_document
from app.api.schemas import DocumentResponse, DocumentListResponse

router = APIRouter(prefix="/documents", tags=["Documents"])

# Allowed file types
ALLOWED_TYPES = {"pdf", "txt", "md", "docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a document for ingestion.

    The file is saved immediately and processing runs in the background.
    The response returns instantly with status='processing'.
    Poll GET /documents/{id} to check when status becomes 'ready'.

    BackgroundTasks: FastAPI runs this after the response is sent.
    Keeps upload fast even for large documents.
    """
    # Validate file type
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{ext}'. Allowed: {ALLOWED_TYPES}",
        )

    # Read file content
    file_bytes = await file.read()
    file_size = len(file_bytes)

    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({file_size} bytes). Max: {MAX_FILE_SIZE} bytes",
        )

    # Create document record immediately
    doc = Document(
        id=str(uuid.uuid4()),
        filename=file.filename,
        file_type=ext,
        file_size=file_size,
        status="processing",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    logger.info(f"Document uploaded: {file.filename} ({file_size} bytes) → {doc.id}")

    # Run ingestion in background (non-blocking)
    background_tasks.add_task(
        ingest_document,
        db=db,
        document_id=doc.id,
        filename=file.filename,
        file_bytes=file_bytes,
        file_size=file_size,
    )

    return DocumentResponse(**doc.to_dict())


@router.get("/", response_model=DocumentListResponse)
def list_documents(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List all uploaded documents with pagination."""
    total = db.query(Document).count()
    docs = db.query(Document).order_by(Document.created_at.desc()).offset(skip).limit(limit).all()
    return DocumentListResponse(
        documents=[DocumentResponse(**d.to_dict()) for d in docs],
        total=total,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str, db: Session = Depends(get_db)):
    """Get a single document by ID. Used to poll ingestion status."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse(**doc.to_dict())


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str, db: Session = Depends(get_db)):
    """
    Delete a document and all its chunks.
    CASCADE delete in the Chunk model handles removing child chunks automatically.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(doc)
    db.commit()
    logger.info(f"Document deleted: {document_id}")
