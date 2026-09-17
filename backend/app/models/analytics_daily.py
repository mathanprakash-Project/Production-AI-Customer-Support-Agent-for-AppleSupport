"""
Pre-computed daily analytics metrics model.
"""

from datetime import datetime, date
from sqlalchemy import Date, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, generate_uuid, utc_now


class AnalyticsDaily(Base):
    """
    Stores pre-computed daily performance metrics for historical analytics
    and dashboard visualizations.
    """
    __tablename__ = "analytics_daily"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    metric_date: Mapped[date] = mapped_column(Date, unique=True, index=True, nullable=False)

    # Volume counts
    total_tickets: Mapped[int] = mapped_column(Integer, default=0)
    drafts_approved: Mapped[int] = mapped_column(Integer, default=0)
    drafts_edited: Mapped[int] = mapped_column(Integer, default=0)
    drafts_rejected: Mapped[int] = mapped_column(Integer, default=0)
    escalated_count: Mapped[int] = mapped_column(Integer, default=0)

    # Quality and efficiency rates
    avg_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    avg_edit_distance: Mapped[float] = mapped_column(Float, default=0.0)
    avg_pipeline_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    avg_review_time_seconds: Mapped[int] = mapped_column(Integer, default=0)
    
    # Growth metrics
    kb_entries_added: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

