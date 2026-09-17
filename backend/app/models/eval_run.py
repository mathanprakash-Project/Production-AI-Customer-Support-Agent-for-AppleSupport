"""Evaluation Run model for persisting offline and online benchmark runs."""

from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import DateTime, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, generate_uuid, utc_now


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    git_sha: Mapped[str] = mapped_column(String(40), default="HEAD")
    model: Mapped[str] = mapped_column(String(64), default="")
    prompt_versions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)
    metrics_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

