import datetime
from typing import Optional
from sqlalchemy import String, Boolean, Integer, DateTime, Text, ForeignKey, JSON, Float
from sqlalchemy.orm import mapped_column, relationship

from app.db.base import Base, generate_uuid, utc_now

try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False


class ConversationSession(Base):
    __tablename__ = 'conversation_sessions'
    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_identifier = mapped_column(String(255), nullable=False)
    agent_id = mapped_column(String(36), nullable=True)
    ticket_id = mapped_column(String(36), nullable=True)
    is_active = mapped_column(Boolean, default=True)
    turn_count = mapped_column(Integer, default=0)
    created_at = mapped_column(DateTime(timezone=True), default=utc_now)
    last_active_at = mapped_column(DateTime(timezone=True), default=utc_now)
    
    turns = relationship('ConversationTurn', back_populates='session', cascade='all, delete-orphan')


class ConversationTurn(Base):
    __tablename__ = 'conversation_turns'
    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id = mapped_column(String(36), ForeignKey('conversation_sessions.id', ondelete='CASCADE'))
    role = mapped_column(String(50), nullable=False)  # 'customer' | 'agent' | 'system'
    message = mapped_column(Text, nullable=False)
    intent = mapped_column(String(255), nullable=True)
    turn_index = mapped_column(Integer, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utc_now)
    
    session = relationship('ConversationSession', back_populates='turns')


class UserMemory(Base):
    __tablename__ = 'user_memories'
    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_identifier = mapped_column(String(255), index=True, nullable=False)
    category = mapped_column(String(100), nullable=False)
    fact_text = mapped_column(Text, nullable=False)
    confidence = mapped_column(Float, default=0.8)
    source_session_id = mapped_column(String(36), ForeignKey('conversation_sessions.id', ondelete='SET NULL'), nullable=True)
    
    if PGVECTOR_AVAILABLE:
        embedding = mapped_column(Vector(384))
    else:
        embedding = mapped_column(JSON)
        
    is_active = mapped_column(Boolean, default=True)
    created_at = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class ContextMemory(Base):
    __tablename__ = 'context_memories'
    id = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id = mapped_column(String(36), ForeignKey('conversation_sessions.id', ondelete='CASCADE'), index=True)
    key = mapped_column(String(255), nullable=False)
    value = mapped_column(JSON, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utc_now)
