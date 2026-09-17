"""
Escalation Log model tracking tickets escalated to human specialists.
"""

from datetime import datetime
from typing import Any, List, Optional
from sqlalchemy import DateTime, Float, ForeignKey, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, generate_uuid, utc_now


class EscalationLog(Base):
    """
    Audit log for escalated customer queries.
    Captures the trigger rules, risk scores, and who escalated (system vs agent).
    """
    __tablename__ = "escalation_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    ticket_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tickets.id", ondelete="CASCADE"), index=True, nullable=False
    )

    escalation_reasons: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    escalated_by: Mapped[str] = mapped_column(String(32), default="system")  # 'system' | 'agent'
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

