"""
DOCUMENT MODEL
--------------
Represents an ingested document in PostgreSQL.
Each document has metadata and links to many Chunks.
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)        # pdf, txt, docx, etc.
    file_size = Column(Integer, nullable=False)            # bytes
    title = Column(String(500), nullable=True)
    content_preview = Column(Text, nullable=True)          # First 500 chars
    doc_metadata = Column(JSON, default={})                # Flexible metadata
    chunk_count = Column(Integer, default=0)
    status = Column(String(50), default="processing")      # processing | ready | error
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # One document → many chunks
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "title": self.title,
            "content_preview": self.content_preview,
            "chunk_count": self.chunk_count,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
