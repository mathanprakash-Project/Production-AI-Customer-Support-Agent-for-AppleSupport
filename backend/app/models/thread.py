"""
Historical Twitter thread model for RAG grounding and vector retrieval.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, generate_uuid, utc_now

try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False


class Thread(Base):
    """
    Represents a historical customer-brand conversation turn or reconstructed thread.
    Stored with semantic embedding for nearest-neighbor similarity search.
    """
    __tablename__ = "threads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    tweet_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    thread_root_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    author_type: Mapped[str] = mapped_column(String(32), default="customer")  # 'customer' | 'brand'
    author_id: Mapped[str] = mapped_column(String(64), index=True, default="AppleSupport")
    
    # Text contents
    customer_message: Mapped[str] = mapped_column(Text, nullable=False)
    brand_reply: Mapped[str] = mapped_column(Text, default="", nullable=False)
    text_clean: Mapped[str] = mapped_column(Text, default="")
    text_raw: Mapped[str] = mapped_column(Text, default="")
    
    # Metadata filters
    is_dm_request: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    intent_label: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    
    # Vector embedding (384-dimensional dense vector)
    # Uses Vector(384) in PostgreSQL/pgvector, or JSON array in SQLite
    if PGVECTOR_AVAILABLE:
        embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(384), nullable=True)
    else:
        embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)
        
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


# Indexing for filtering
Index("ix_threads_dm_author", Thread.is_dm_request, Thread.author_type)

