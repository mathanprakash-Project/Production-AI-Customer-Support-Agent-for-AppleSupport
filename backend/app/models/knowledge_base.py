"""
Knowledge Base entry model for self-updating RAG retrieval.
Stores resolved customer issues and resolutions with embeddings and helpfulness tracking.
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


class KnowledgeEntry(Base):
    """
    Represents an entry in the self-updating knowledge base.
    Can originate from the seed dataset, agent-approved feedback, or manual upload.
    Maintains retrieval and helpfulness statistics to weight ranking over time.
    """
    __tablename__ = "knowledge_base"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    
    # Source metadata
    source_type: Mapped[str] = mapped_column(String(32), default="seed_dataset", nullable=False)
    # "seed_dataset" | "agent_approved" | "manual_upload"
    source_ticket_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    # Question & Resolution pair
    customer_message: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Classification
    intent: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)

    # Semantic vector embedding (384 dims for all-MiniLM-L6-v2)
    if PGVECTOR_AVAILABLE:
        embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(384), nullable=True)
    else:
        embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)

    # Helpfulness signals
    times_retrieved: Mapped[int] = mapped_column(Integer, default=0)
    times_helpful: Mapped[int] = mapped_column(Integer, default=0)
    helpfulness_ratio: Mapped[Optional[float]] = mapped_column(Float, default=0.5, nullable=True)

    # Lifecycle
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


# Index for active search filtering
Index("ix_knowledge_base_active_intent", KnowledgeEntry.is_active, KnowledgeEntry.intent)

