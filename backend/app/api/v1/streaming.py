"""SSE Streaming endpoint for real-time AI pipeline execution."""
import json
import logging
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.streaming_service import StreamingInferenceService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tickets", tags=["Streaming"])

@router.get("/{ticket_id}/inference/stream")
async def stream_inference(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stream AI pipeline execution via Server-Sent Events.
    
    Events emitted:
    - stage_start: {stage: str, index: int, total: 5}
    - stage_complete: {stage: str, index: int, result: dict, duration_ms: int}
    - token: {content: str}  (during drafting stage)
    - draft_complete: {reply: str, confidence: float}
    - safety_result: {passed: bool, flags: list}
    - error: {message: str}
    - done: {ticket_id: str, total_ms: int}
    """
    service = StreamingInferenceService(db)
    
    async def event_generator() -> AsyncGenerator:
        try:
            async for event in service.stream_pipeline(ticket_id):
                yield {
                    "event": event["event"],
                    "data": json.dumps(event["data"]),
                }
        except ValueError as e:
            yield {"event": "error", "data": json.dumps({"message": str(e)})}
        except Exception as e:
            logger.exception(f"Streaming error for ticket {ticket_id}: {e}")
            yield {"event": "error", "data": json.dumps({"message": f"Pipeline error: {str(e)}"})} 
    
    return EventSourceResponse(event_generator())
