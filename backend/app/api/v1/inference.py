"""Agent Inference API routes."""

import logging
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.inference import InferenceResponse
from app.services.inference_service import InferenceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets", tags=["Inference"])


@router.post("/{ticket_id}/inference", response_model=InferenceResponse)
async def run_inference(
    ticket_id: str,
    refresh: bool = Query(False, description="Force re-generation instead of returning cached draft"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Execute AI Agent Pipeline on ticket:
    1. Classify intent into taxonomy
    2. Retrieve top-3 similar historical resolutions (pgvector)
    3. Draft grounded reply (RAG LLM)
    4. Decide escalation vs auto-handle with explicit reasons
    """
    service = InferenceService(db)
    try:
        result = await service.run_ticket_inference(ticket_id, force_fresh=refresh)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Inference execution failed for ticket {ticket_id}: {e}")
        detail_msg = str(e).strip() or type(e).__name__
        raise HTTPException(status_code=500, detail=f"Inference error: {detail_msg}")


@router.get("/{ticket_id}/drafts")
async def get_draft_history(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full audit history of drafts generated for this ticket."""
    service = InferenceService(db)
    drafts = await service.get_drafts_for_ticket(ticket_id)
    return [
        {
            "id": d.id,
            "intent": d.intent_label,
            "confidence": d.intent_confidence,
            "reply": d.reply_text,
            "decision": d.escalation_decision,
            "reasons": d.escalation_reasons,
            "latency_ms": d.latency_ms,
            "created_at": d.created_at,
        }
        for d in drafts
    ]

