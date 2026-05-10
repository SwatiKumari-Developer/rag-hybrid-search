"""
MAIN APPLICATION
----------------
FastAPI is the web framework. Key advantages over Flask:
  - Native async support (important for I/O-heavy AI workloads)
  - Automatic OpenAPI/Swagger docs at /docs
  - Pydantic integration for request/response validation
  - Type hints throughout = better IDE support + fewer bugs

Application startup:
  1. Configure logging
  2. Initialize database (create tables, enable pgvector)
  3. Register all API routers
  4. Configure CORS middleware

Access the interactive API docs at: http://localhost:8000/docs
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.database import init_db
from app.api import documents, query, health

# Setup logging first
setup_logging()

# Create FastAPI app instance
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## RAG Application with Hybrid Search

A production-ready Retrieval-Augmented Generation (RAG) system featuring:

- **Document Ingestion**: Upload PDF, TXT, DOCX files
- **Chunking**: Sliding window text splitting with overlap
- **Embeddings**: Sentence-Transformers (all-MiniLM-L6-v2)
- **Dense Search**: pgvector cosine similarity search
- **Sparse Search**: BM25 keyword search
- **Hybrid Fusion**: Reciprocal Rank Fusion (RRF)
- **Answer Generation**: Anthropic Claude LLM

### Quick Start
1. Upload a document via `POST /documents/upload`
2. Ask a question via `POST /query/ask`
    """,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS Middleware ──────────────────────────────────────────────────────────
# CORS (Cross-Origin Resource Sharing) allows the React frontend
# (running on localhost:5173) to call the API (running on localhost:8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Register Routers ─────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(documents.router, prefix="/api/v1")
app.include_router(query.router, prefix="/api/v1")


# ─── Startup Event ────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    """Runs once when the server starts."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    os.makedirs("logs", exist_ok=True)

    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down...")


@app.get("/")
def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }
