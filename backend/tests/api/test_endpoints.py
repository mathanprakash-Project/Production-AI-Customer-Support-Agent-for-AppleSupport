import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/health")
        assert res.status_code == 200
        data = res.json()
        assert "status" in data
        assert "brand" in data
        assert data["brand"] == "AppleSupport"


@pytest.mark.asyncio
async def test_auth_and_tickets_crud():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Login
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "agent@tweetsupport.local", "password": "agent123"},
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. List tickets
        list_res = await client.get("/api/v1/tickets", headers=headers)
        assert list_res.status_code == 200
        assert "items" in list_res.json()

        # 3. Create ticket
        create_res = await client.post(
            "/api/v1/tickets",
            json={"customer_text": "iPhone battery dies from 100% to 10% in 1 hour. Need help."},
            headers=headers,
        )
        assert create_res.status_code == 201
        ticket_id = create_res.json()["id"]

        # 4. Run inference
        inf_res = await client.post(
            f"/api/v1/tickets/{ticket_id}/inference",
            headers=headers,
        )
        assert inf_res.status_code == 200
        inf_data = inf_res.json()
        assert "intent" in inf_data
        assert "draft" in inf_data
        assert "escalation" in inf_data

        # 5. Submit feedback
        fb_res = await client.post(
            f"/api/v1/tickets/{ticket_id}/feedback",
            json={"action": "approve", "notes": "Approved by automated test."},
            headers=headers,
        )
        assert fb_res.status_code == 200
        assert fb_res.json()["action"] == "approve"


@pytest.mark.asyncio
async def test_intents_and_evaluation_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Intents
        intents_res = await client.get("/api/v1/intents")
        assert intents_res.status_code == 200
        intents = intents_res.json()
        assert len(intents) >= 10

        # 2. Evaluation summary
        eval_res = await client.get("/api/v1/evaluation/latest")
        assert eval_res.status_code == 200
        eval_data = eval_res.json()
        assert "headline_metrics" in eval_data
        assert "baselines" in eval_data

