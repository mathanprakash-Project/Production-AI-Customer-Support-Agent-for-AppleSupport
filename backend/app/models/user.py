"""User account model for RBAC (Support Agent & Admin)."""

from datetime import datetime
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, generate_uuid, utc_now


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), default="Support Agent")
    role: Mapped[str] = mapped_column(String(32), default="agent", nullable=False)  # 'agent' | 'admin'
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    # Relationships
    assigned_tickets = relationship("Ticket", back_populates="assignee", lazy="selectin")
    feedbacks = relationship("Feedback", back_populates="user", lazy="selectin")

