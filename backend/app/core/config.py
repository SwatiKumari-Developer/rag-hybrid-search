from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "RAG Hybrid Search"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/rag_db"

    # Anthropic
    ANTHROPIC_API_KEY: str = ""

    # Embedding
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # Chunking
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    MAX_CHUNKS_PER_DOC: int = 500

    # Retrieval
    TOP_K_DENSE: int = 10
    TOP_K_SPARSE: int = 10
    TOP_K_FINAL: int = 5
    DENSE_WEIGHT: float = 0.6
    SPARSE_WEIGHT: float = 0.4

    # LLM
    LLM_MODEL: str = "claude-3-haiku-20240307"
    MAX_TOKENS: int = 1024
    TEMPERATURE: float = 0.2

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
