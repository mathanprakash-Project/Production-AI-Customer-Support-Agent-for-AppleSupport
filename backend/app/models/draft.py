"""AI Draft response model storing classification, reply, and escalation rationale."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, generate_uuid, utc_now


class Draft(Base):
    __tablename__ = "drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    ticket_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tickets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    
    # Intent classification
    intent_label: Mapped[str] = mapped_column(String(64), nullable=False)
    intent_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    intent_alternatives: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, default=list)
    
    # Drafted response
    reply_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reply_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    retrieved_thread_ids: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    
    # Escalation decision
    escalation_decision: Mapped[str] = mapped_column(String(32), default="auto")  # 'auto' | 'escalate'
    escalation_reasons: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Safety validation
    safety_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    safety_flags: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)

    # Response metadata
    response_type: Mapped[str] = mapped_column(String(20), default="tweet")  # 'tweet' (280) | 'dm' (500)
    char_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Observability & Provenance
    model_name: Mapped[str] = mapped_column(String(64), default="")
    provider: Mapped[str] = mapped_column(String(32), default="ollama")
    prompt_version: Mapped[str] = mapped_column(String(32), default="v1")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    tokens_prompt: Mapped[int] = mapped_column(Integer, default=0)
    tokens_completion: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    # Relationships
    ticket = relationship("Ticket", back_populates="drafts")
    feedback = relationship("Feedback", back_populates="draft", uselist=False, cascade="all, delete-orphan", lazy="selectin")

