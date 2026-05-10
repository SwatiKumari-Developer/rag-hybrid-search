"""
CHUNK MODEL
-----------
A chunk is a fixed-size piece of a document's text.
The `embedding` column uses pgvector's Vector type to store
a 384-dimensional float array — enabling cosine similarity search
directly in SQL using the <=> operator.
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base
from app.core.config import settings
import uuid


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)          # Position in document
    text = Column(Text, nullable=False)                    # Raw text content
    token_count = Column(Integer, default=0)               # Approximate token length

    # THE KEY COLUMN: 384-dim vector embedding stored in PostgreSQL via pgvector
    # This enables fast approximate nearest-neighbor (ANN) search using ivfflat index
    embedding = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=True)

    chunk_metadata = Column(JSON, default={})              # Page number, section, etc.
    created_at = Column(DateTime, default=datetime.utcnow)

    # Many chunks → one document
    document = relationship("Document", back_populates="chunks")

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "token_count": self.token_count,
            "chunk_metadata": self.chunk_metadata,
        }
