"""
DATABASE MODULE
---------------
Uses SQLAlchemy as the ORM (Object Relational Mapper) to interact with PostgreSQL.
pgvector extension enables storing and querying high-dimensional float vectors
directly in Postgres — no separate vector database needed.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool
from loguru import logger
from app.core.config import settings


# Create the SQLAlchemy engine — this is the core connection to PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,  # No connection pooling for simplicity; use pool for prod
    echo=settings.DEBUG,
)

# Session factory — each request gets its own database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class all ORM models inherit from."""
    pass


def get_db():
    """
    FastAPI dependency that yields a DB session per request.
    Automatically closes the session when the request finishes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize the database:
    1. Enable pgvector extension (for vector storage/search)
    2. Create all tables defined in ORM models
    """
    with engine.connect() as conn:
        # Enable pgvector — must be done before creating vector columns
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
        logger.info("pgvector extension enabled")

    # Import models so Base knows about them before create_all
    from app.models import document, chunk  # noqa: F401
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
