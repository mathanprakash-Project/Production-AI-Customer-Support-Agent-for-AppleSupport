"""Pydantic schemas for Support Tickets and Feedback."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TicketCreate(BaseModel):
    customer_text: str = Field(..., min_length=1, max_length=4000)
    tweet_author: Optional[str] = Field(default="@customer", max_length=100)
    source_tweet_id: Optional[str] = None


class FeedbackCreate(BaseModel):
    action: str = Field(..., description="'approve', 'edit', 'reject', 'escalate'")
    edited_text: Optional[str] = None
    final_response_text: Optional[str] = None
    notes: Optional[str] = None
    review_time_seconds: Optional[int] = None


class FeedbackResponse(BaseModel):
    id: str
    draft_id: str
    user_id: Optional[str] = None
    action: str
    edited_text: Optional[str] = None
    final_response_text: Optional[str] = None
    edit_distance_ratio: Optional[float] = None
    review_time_seconds: Optional[int] = None
    added_to_knowledge_base: Optional[bool] = False
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TicketResponse(BaseModel):
    id: str
    customer_text: str
    tweet_author: Optional[str] = None
    source_tweet_id: Optional[str] = None
    status: str
    assigned_to: Optional[str] = None
    
    # Classification & safety
    intent: Optional[str] = None
    confidence: Optional[float] = None
    sentiment_score: Optional[float] = None
    is_escalated: Optional[bool] = False
    escalation_reason: Optional[str] = None
    pii_detected: Optional[bool] = False
    pii_redacted_text: Optional[str] = None

    # Pipeline timings (ms)
    classification_time_ms: Optional[int] = None
    retrieval_time_ms: Optional[int] = None
    drafting_time_ms: Optional[int] = None
    total_pipeline_time_ms: Optional[int] = None

    # Timestamps
    created_at: datetime
    processed_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TicketListResponse(BaseModel):
    items: List[TicketResponse]
    total: int
    page: int
    size: int

