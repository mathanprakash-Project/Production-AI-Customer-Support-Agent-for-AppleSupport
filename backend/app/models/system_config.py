"""
System configuration model for runtime parameters and thresholds.
"""

from datetime import datetime
from typing import Any, Dict
from sqlalchemy import DateTime, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, utc_now


class SystemConfig(Base):
    """
    Dynamic system configuration key-value store.
    Used for runtime tuning of escalation thresholds, brand rules, and safety parameters.
    """
    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

