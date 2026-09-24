"""
Integration tests for new Phase 1 API endpoints: Knowledge Base and Analytics.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_knowledge_base_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Login
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "mathanprakashselvam@gmail.com", "password": "Tweetsupportadmin123"},
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. List knowledge entries
        kb_res = await client.get("/api/v1/knowledge", headers=headers)
        assert kb_res.status_code == 200
        kb_data = kb_res.json()
        assert "items" in kb_data
        assert "total" in kb_data

        # 3. Knowledge stats
        stats_res = await client.get("/api/v1/knowledge/stats", headers=headers)
        assert stats_res.status_code == 200
        stats_data = stats_res.json()
        assert "total_entries" in stats_data
        assert "growth_from_feedback_pct" in stats_data


@pytest.mark.asyncio
async def test_analytics_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Login
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "agent@tweetsupport.local", "password": "agent123"},
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Overview
        ov_res = await client.get("/api/v1/analytics/overview", headers=headers)
        assert ov_res.status_code == 200
        ov_data = ov_res.json()
        assert "tickets_today" in ov_data
        assert "draft_approval_rate" in ov_data
        assert "time_saved_hours" in ov_data

        # 2. Intent distribution
        dist_res = await client.get("/api/v1/analytics/intent-distribution?period=week", headers=headers)
        assert dist_res.status_code == 200
        dist_data = dist_res.json()
        assert "distribution" in dist_data

        # 3. Confidence trend
        conf_res = await client.get("/api/v1/analytics/confidence-over-time", headers=headers)
        assert conf_res.status_code == 200
        conf_data = conf_res.json()
        assert "points" in conf_data

        # 4. Feedback summary
        fb_res = await client.get("/api/v1/analytics/feedback-summary", headers=headers)
        assert fb_res.status_code == 200
        fb_data = fb_res.json()
        assert "summary" in fb_data

        # 5. Time saved
        time_res = await client.get("/api/v1/analytics/time-saved", headers=headers)
        assert time_res.status_code == 200
        time_data = time_res.json()
        assert "hours_saved" in time_data
        assert "estimated_cost_savings_usd" in time_data

