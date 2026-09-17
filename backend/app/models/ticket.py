"""Support ticket model representing incoming customer inquiries."""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, generate_uuid, utc_now


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    customer_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_tweet_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="open", index=True, nullable=False
    )  # 'open' | 'drafted' | 'resolved' | 'escalated'
    assigned_to: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tweet_author: Mapped[Optional[str]] = mapped_column(String(100), default="@customer", nullable=True)
    
    # AI Classification results cached on ticket
    intent: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Escalation & Safety metadata
    is_escalated: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    escalation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pii_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    pii_redacted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Pipeline timing breakdown in ms
    classification_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    retrieval_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    drafting_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_pipeline_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationships
    assignee = relationship("User", back_populates="assigned_tickets")
    drafts = relationship("Draft", back_populates="ticket", cascade="all, delete-orphan", lazy="selectin")

