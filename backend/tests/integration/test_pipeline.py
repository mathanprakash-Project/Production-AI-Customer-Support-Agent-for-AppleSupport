import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.base import Base
from app.models.thread import Thread
from app.repositories.thread_repo import ThreadRepository
from app.llm.providers.mock import MockProvider
from app.agent.pipeline import AgentPipeline


@pytest.mark.asyncio
async def test_agent_pipeline_end_to_end():
    # Setup in-memory test database
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        # Seed test thread
        thread = Thread(
            tweet_id="test-thread-01",
            customer_message="My phone won't charge with any cable.",
            brand_reply="Try restarting your phone and using an Apple-certified cable.",
            author_type="customer",
            is_dm_request=False,
            intent_label="charging_issues",
            embedding=[0.05] * 384,
        )
        session.add(thread)
        await session.commit()

        # Initialize pipeline with MockProvider
        mock_llm = MockProvider("mock-test-model")
        thread_repo = ThreadRepository(session)
        pipeline = AgentPipeline(provider=mock_llm, thread_repo=thread_repo)

        # Run pipeline
        response = await pipeline.run("My iPhone 13 won't charge overnight. Port seems clean.")

        assert response.ticket_id == "transient-ticket"
        assert response.intent.intent == "charging_issues"
        assert response.intent.confidence >= 0.8
        assert len(response.draft.reply) > 20
        assert response.escalation.decision in ["auto", "escalate"]
        assert response.meta.model == "mock-test-model"
        assert response.meta.latency_ms > 0

