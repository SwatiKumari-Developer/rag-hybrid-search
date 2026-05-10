"""
SCHEMAS (Pydantic Models)
--------------------------
Pydantic models define the shape of:
  - API request bodies (what the client sends)
  - API response bodies (what the server returns)

FastAPI automatically:
  - Validates incoming JSON against request schemas
  - Serializes outgoing data using response schemas
  - Generates OpenAPI docs from these schemas

This provides strong type safety and automatic validation without manual code.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ─── Document Schemas ─────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    title: Optional[str]
    content_preview: Optional[str]
    chunk_count: int
    status: str
    created_at: Optional[str]

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int


# ─── Search/Query Schemas ─────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="The question to ask")
    document_ids: Optional[List[str]] = Field(None, description="Limit search to specific docs")
    top_k: Optional[int] = Field(None, ge=1, le=20, description="Number of chunks to retrieve")
    include_debug: bool = Field(False, description="Include retrieval debug information")


class ChunkSource(BaseModel):
    document_id: str
    filename: str
    title: Optional[str]
    chunk_index: int
    retrieval_method: str   # "hybrid" | "semantic" | "keyword"
    rrf_score: float


class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: List[ChunkSource]
    model: str
    input_tokens: int
    output_tokens: int
    debug_info: Optional[Dict[str, Any]] = None


# ─── Search-only Schemas (no LLM) ─────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    document_ids: Optional[List[str]] = None
    top_k: Optional[int] = Field(5, ge=1, le=20)


class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    title: Optional[str]
    chunk_index: int
    text: str
    rrf_score: float
    dense_score: Optional[float]
    sparse_score: Optional[float]
    retrieval_method: str


class SearchResponse(BaseModel):
    query: str
    results: List[RetrievedChunk]
    total: int
    debug_info: Optional[Dict[str, Any]] = None


# ─── Health Check ─────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    embedding_model: str
