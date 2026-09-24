"""
Pydantic schemas for structured LLM inference, Agent responses, and Judge outputs.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IntentAlternative(BaseModel):
    label: str = Field(..., description="Alternative intent name")
    confidence: float = Field(..., description="Estimated probability")


class IntentClassificationSchema(BaseModel):
    """Schema enforced on LLM during intent classification."""
    intent: str = Field(..., description="Classified intent label from allowed taxonomy")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")
    reasoning: Optional[str] = Field(default="", description="Rationale for intent assignment")
    alternatives: List[IntentAlternative] = Field(default_factory=list, description="Top alternative candidate intents")


class RetrievedThreadItem(BaseModel):
    thread_id: str
    similarity: float
    customer_msg: str
    brand_reply: str
    intent_label: Optional[str] = None
    source: Optional[str] = "internal_rag"  # "internal_rag" | "web_search"
    url: Optional[str] = None


class DraftReplySchema(BaseModel):
    """Schema enforced on LLM during reply drafting."""
    reply: str = Field(..., description="The complete drafted reply text")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in reply helpfulness")
    grounded_thread_ids: List[str] = Field(default_factory=list, description="Thread IDs cited for grounding")
    reasoning: Optional[str] = Field(default="", description="Summary of troubleshooting approach")


class EscalationDecision(BaseModel):
    decision: str = Field(..., description="'auto' or 'escalate'")
    reasons: List[str] = Field(default_factory=list, description="Triggered escalation rule reasons")
    risk_score: float = Field(default=0.0, description="Composite risk metric")


class SafetyResultSchema(BaseModel):
    passed: bool = True
    flags: List[str] = Field(default_factory=list)


class InferenceMeta(BaseModel):
    model: str
    provider: str
    prompt_version: str
    latency_ms: int
    tokens_prompt: int = 0
    tokens_completion: int = 0
    classification_ms: Optional[int] = None
    escalation_ms: Optional[int] = None
    retrieval_ms: Optional[int] = None
    drafting_ms: Optional[int] = None
    safety_ms: Optional[int] = None
    web_search_used: Optional[bool] = False
    web_search_ms: Optional[int] = None


class InferenceResponse(BaseModel):
    """Canonical full agent response envelope matching frontend specification."""
    ticket_id: str
    customer_message: str
    intent: IntentClassificationSchema
    retrieved: List[RetrievedThreadItem]
    draft: DraftReplySchema
    escalation: EscalationDecision
    meta: InferenceMeta
    safety: SafetyResultSchema = Field(default_factory=SafetyResultSchema)
    draft_id: Optional[str] = None


class JudgeEvaluationSchema(BaseModel):
    """Schema enforced on LLM Judge evaluating 5 dimensions on 1-5 scale."""
    relevance: int = Field(..., ge=1, le=5, description="1-5 relevance score")
    accuracy: int = Field(..., ge=1, le=5, description="1-5 accuracy score")
    tone: int = Field(..., ge=1, le=5, description="1-5 tone score")
    completeness: int = Field(..., ge=1, le=5, description="1-5 completeness score")
    groundedness: int = Field(..., ge=1, le=5, description="1-5 groundedness score")
    overall_score: float = Field(..., ge=1.0, le=5.0, description="Average composite score")
    critique: str = Field(..., description="Qualitative critique of strengths and weaknesses")

