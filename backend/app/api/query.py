"""
QUERY API ROUTER
----------------
Two main endpoints:

  POST /query/ask
    - Full RAG pipeline: search → retrieve → generate
    - Returns LLM-generated answer with cited sources

  POST /query/search
    - Search only (no LLM generation)
    - Returns ranked chunks with scores
    - Useful for debugging retrieval quality
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.services.search import hybrid_search
from app.services.llm import generate_answer
from app.api.schemas import (
    QueryRequest, QueryResponse, ChunkSource,
    SearchRequest, SearchResponse, RetrievedChunk,
)

router = APIRouter(prefix="/query", tags=["Query"])


@router.post("/ask", response_model=QueryResponse)
def ask_question(request: QueryRequest, db: Session = Depends(get_db)):
    """
    Full RAG pipeline endpoint:
      1. Hybrid search (dense + sparse + RRF)
      2. LLM answer generation using retrieved chunks

    This is the primary user-facing endpoint.
    """
    logger.info(f"Received query: '{request.query}'")

    # Step 1: Retrieve relevant chunks via hybrid search
    chunks, debug_info = hybrid_search(
        db=db,
        query=request.query,
        document_ids=request.document_ids,
        top_k=request.top_k,
    )

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail="No relevant documents found. Please upload documents first.",
        )

    # Step 2: Generate LLM answer from retrieved context
    result = generate_answer(query=request.query, chunks=chunks)

    return QueryResponse(
        query=request.query,
        answer=result["answer"],
        sources=[ChunkSource(**s) for s in result["sources"]],
        model=result["model"],
        input_tokens=result["input_tokens"],
        output_tokens=result["output_tokens"],
        debug_info=debug_info if request.include_debug else None,
    )


@router.post("/search", response_model=SearchResponse)
def search_documents(request: SearchRequest, db: Session = Depends(get_db)):
    """
    Search-only endpoint — returns ranked chunks without LLM generation.

    Useful for:
    - Evaluating retrieval quality
    - Building custom UIs that handle answer generation differently
    - Debugging why certain chunks were/weren't retrieved
    """
    logger.info(f"Search request: '{request.query}'")

    chunks, debug_info = hybrid_search(
        db=db,
        query=request.query,
        document_ids=request.document_ids,
        top_k=request.top_k,
    )

    results = []
    for chunk in chunks:
        results.append(RetrievedChunk(
            chunk_id=chunk["chunk_id"],
            document_id=chunk["document_id"],
            filename=chunk["filename"],
            title=chunk.get("title"),
            chunk_index=chunk["chunk_index"],
            text=chunk["text"],
            rrf_score=chunk.get("rrf_score", 0),
            dense_score=chunk.get("dense_score"),
            sparse_score=chunk.get("sparse_score"),
            retrieval_method=chunk.get("retrieval_method", "hybrid"),
        ))

    return SearchResponse(
        query=request.query,
        results=results,
        total=len(results),
        debug_info=debug_info,
    )
