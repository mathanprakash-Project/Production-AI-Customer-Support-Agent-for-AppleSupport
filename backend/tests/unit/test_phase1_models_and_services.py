"""
Unit tests for Phase 1 models, KnowledgeService, AnalyticsService, and enhanced FeedbackService.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_standalone_session
from app.models.knowledge_base import KnowledgeEntry
from app.models.escalation_log import EscalationLog
from app.models.analytics_daily import AnalyticsDaily
from app.models.system_config import SystemConfig
from app.models.ticket import Ticket
from app.models.draft import Draft
from app.schemas.ticket import FeedbackCreate
from app.services.knowledge_service import KnowledgeService
from app.services.feedback_service import FeedbackService
from app.services.analytics_service import AnalyticsService


@pytest.mark.asyncio
async def test_knowledge_entry_and_stats():
    session = await get_standalone_session()
    async with session:
        service = KnowledgeService(session)
        
        # Test add knowledge entry
        entry = KnowledgeEntry(
            source_type="agent_approved",
            customer_message="My iPhone battery drains overnight",
            resolution_text="Check background app refresh and battery health in settings.",
            intent="battery_performance",
            times_retrieved=2,
            times_helpful=2,
            helpfulness_ratio=1.0,
            is_active=True,
        )
        session.add(entry)
        await session.commit()
        await session.refresh(entry)

        assert entry.id is not None
        assert entry.is_active is True

        # Test list_entries
        entries, total = await service.list_entries(intent="battery_performance")
        assert total >= 1
        assert any(e.id == entry.id for e in entries)

        # Test toggle_entry
        toggled = await service.toggle_entry(entry.id, False)
        assert toggled.is_active is False

        # Test stats
        stats = await service.get_stats()
        assert "total_entries" in stats
        assert "growth_from_feedback_pct" in stats


@pytest.mark.asyncio
async def test_feedback_service_with_edit_distance_and_kb_loop():
    session = await get_standalone_session()
    async with session:
        # Create ticket and draft
        ticket = Ticket(
            customer_text="Left AirPod won't connect to MacBook",
            intent="connectivity_wifi_bluetooth",
            status="drafted",
        )
        session.add(ticket)
        await session.flush()

        draft = Draft(
            ticket_id=ticket.id,
            intent_label="connectivity_wifi_bluetooth",
            intent_confidence=0.92,
            reply_text="Reset your AirPods by holding the button on the case for 15 seconds.",
            reply_confidence=0.88,
            escalation_decision="auto",
        )
        session.add(draft)
        await session.commit()

        feedback_service = FeedbackService(session)

        # 1. Test 'approve' action -> edit_distance = 0.0
        fb_approve = await feedback_service.record_feedback(
            ticket_id=ticket.id,
            data=FeedbackCreate(action="approve", review_time_seconds=25),
        )
        assert fb_approve.action == "approve"
        assert fb_approve.edit_distance_ratio == 0.0
        assert fb_approve.final_response_text == draft.reply_text

        # 2. Test 'edit' action -> edit_distance > 0.0
        ticket2 = Ticket(customer_text="Screen has green tint", status="drafted")
        session.add(ticket2)
        await session.flush()

        draft2 = Draft(
            ticket_id=ticket2.id,
            intent_label="display_screen",
            intent_confidence=0.85,
            reply_text="Please restart your iPhone.",
            reply_confidence=0.80,
            escalation_decision="auto",
        )
        session.add(draft2)
        await session.commit()

        fb_edit = await feedback_service.record_feedback(
            ticket_id=ticket2.id,
            data=FeedbackCreate(
                action="edit",
                final_response_text="Please restart your iPhone and check True Tone settings.",
                review_time_seconds=40,
            ),
        )
        assert fb_edit.action == "edit"
        assert fb_edit.edit_distance_ratio > 0.0
        assert "True Tone" in fb_edit.final_response_text


@pytest.mark.asyncio
async def test_analytics_service_metrics():
    session = await get_standalone_session()
    async with session:
        service = AnalyticsService(session)

        overview = await service.get_overview()
        assert overview.tickets_today >= 0
        assert 0.0 <= overview.draft_approval_rate <= 100.0
        assert overview.time_saved_hours >= 0.0

        distribution = await service.get_intent_distribution(period="week")
        assert distribution.period == "week"
        assert isinstance(distribution.distribution, list)

        trend = await service.get_confidence_trend()
        assert len(trend.points) >= 1

        summary = await service.get_feedback_summary()
        assert len(summary.summary) >= 1

        time_saved = await service.get_time_saved()
        assert time_saved.total_approved_drafts >= 0
        assert time_saved.hours_saved >= 0.0
