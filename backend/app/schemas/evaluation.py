"""Pydantic schemas for Evaluation dashboard and Intent catalog."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class IntentItem(BaseModel):
    label: str
    description: str
    examples: List[str] = []
    count: Optional[int] = 0


class EvalRunResponse(BaseModel):
    id: str
    started_at: datetime
    finished_at: Optional[datetime]
    git_sha: str
    model: str
    prompt_versions: Dict[str, Any]
    metrics_json: Dict[str, Any]
    notes: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class EvalSummaryResponse(BaseModel):
    latest_run: Optional[EvalRunResponse]
    headline_metrics: Dict[str, Any]
    per_class_f1: Dict[str, float]
    baselines: Dict[str, Dict[str, Any]]
    judge_agreement: Dict[str, Dict[str, float]]
    failure_examples: List[Dict[str, Any]]

