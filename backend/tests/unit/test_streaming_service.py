"""
Unit tests for SSE Streaming Pipeline Service (Module 4).
Tests stage event generation, token streaming, and draft persistence.
"""

import pytest
from app.db.session import get_standalone_session
from app.models.ticket import Ticket
from app.services.streaming_service import StreamingInferenceService


@pytest.mark.asyncio
async def test_streaming_pipeline_events():
    session = await get_standalone_session()
    async with session:
        # Create a test ticket
        ticket = Ticket(
            customer_text="My iPhone 14 won't charge with any cable overnight",
            tweet_author="@streaming_tester",
            status="open",
        )
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)
        
        service = StreamingInferenceService(session)
        events = []
        async for event in service.stream_pipeline(ticket.id):
            events.append(event)
        
        event_types = [e["event"] for e in events]
        assert "stage_start" in event_types
        assert "stage_complete" in event_types
        assert "token" in event_types
        assert "draft_complete" in event_types
        assert "safety_result" in event_types
        assert "done" in event_types
        
        # Verify done payload
        done_event = next(e for e in events if e["event"] == "done")
        assert done_event["data"]["ticket_id"] == ticket.id
        assert done_event["data"]["draft_id"] is not None

