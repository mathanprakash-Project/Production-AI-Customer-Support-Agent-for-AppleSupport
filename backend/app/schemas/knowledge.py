"""
Pydantic schemas for the Knowledge Base.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class KnowledgeEntryResponse(BaseModel):
    id: str
    source_type: str
    source_ticket_id: Optional[str] = None
    customer_message: str
    resolution_text: str
    intent: Optional[str] = None
    times_retrieved: int = 0
    times_helpful: int = 0
    helpfulness_ratio: Optional[float] = 0.5
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgeListResponse(BaseModel):
    items: List[KnowledgeEntryResponse]
    total: int
    page: int
    size: int


class KnowledgeStats(BaseModel):
    total_entries: int
    from_original_dataset: int
    from_agent_feedback: int
    growth_from_feedback_pct: float


class KnowledgeToggleRequest(BaseModel):
    is_active: bool

