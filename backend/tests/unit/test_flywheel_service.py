"""
Unit tests for Helpfulness-Weighted Flywheel Service (Module 2).
Tests flywheel metrics calculation and stale entry decay.
"""

import pytest
from app.db.session import get_standalone_session
from app.services.flywheel_service import FlywheelService


@pytest.mark.asyncio
async def test_flywheel_metrics():
    session = await get_standalone_session()
    async with session:
        service = FlywheelService(session)
        metrics = await service.get_flywheel_metrics()
        
        assert "kb_total_entries" in metrics
        assert "kb_weekly_growth" in metrics
        assert "kb_growth_rate_pct" in metrics
        assert "avg_helpfulness_ratio" in metrics
        assert "feedback_distribution" in metrics
        assert "resolved_tickets_month" in metrics
        assert "top_performing_entries" in metrics
        assert isinstance(metrics["top_performing_entries"], list)


@pytest.mark.asyncio
async def test_flywheel_decay_stale():
    session = await get_standalone_session()
    async with session:
        service = FlywheelService(session)
        decayed = await service.decay_stale_entries(days_inactive=365, decay_factor=0.9)
        assert isinstance(decayed, int)

