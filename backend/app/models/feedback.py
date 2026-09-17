"""Human-in-the-loop feedback model capturing support agent decisions."""

from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, generate_uuid, utc_now


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    draft_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("drafts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    action: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # 'approve' | 'edit' | 'reject' | 'escalate'
    edited_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    final_response_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    edit_distance_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    review_time_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    # Relationships
    draft = relationship("Draft", back_populates="feedback")
    user = relationship("User", back_populates="feedbacks")

