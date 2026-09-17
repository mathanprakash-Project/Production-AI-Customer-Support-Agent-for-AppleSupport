"""
Pydantic schemas for analytics metrics, charts, and ROI calculations.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class TopIntentMetric(BaseModel):
    name: str
    count: int
    pct: float


class AnalyticsOverview(BaseModel):
    tickets_today: int
    draft_approval_rate: float
    avg_response_time_seconds: float
    escalation_rate: float
    time_saved_hours: float
    avg_edit_distance: float
    knowledge_base_size: int
    top_intents: List[TopIntentMetric]


class IntentDistributionResponse(BaseModel):
    period: str
    total_tickets: int
    distribution: List[TopIntentMetric]


class ConfidenceTrendPoint(BaseModel):
    date: str
    avg_confidence: float
    ticket_count: int


class ConfidenceTrendResponse(BaseModel):
    points: List[ConfidenceTrendPoint]


class FeedbackSummaryItem(BaseModel):
    intent: str
    approved: int
    edited: int
    rejected: int
    escalated: int
    total: int
    approval_rate: float


class FeedbackSummaryResponse(BaseModel):
    summary: List[FeedbackSummaryItem]


class TimeSavedResponse(BaseModel):
    total_approved_drafts: int
    hours_saved: float
    estimated_cost_savings_usd: float
    manual_baseline_minutes_per_ticket: float = 4.5
    ai_assisted_review_minutes_per_ticket: float = 0.5
    formula: str = "(approved_tickets * 4.5m) - (approved_tickets * avg_review_time)"

