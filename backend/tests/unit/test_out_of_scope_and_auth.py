import pytest
from app.agent.classifier import IntentClassifier
from app.agent.drafter import ReplyDrafter
from app.agent.escalation import EscalationEngine
from app.agent.pipeline import AgentPipeline
from app.llm.providers.mock import MockProvider
from app.schemas.inference import RetrievedThreadItem


@pytest.fixture
def mock_provider():
    return MockProvider()


@pytest.fixture
def escalation_engine():
    return EscalationEngine()


@pytest.fixture
def pipeline(mock_provider):
    return AgentPipeline(provider=mock_provider)


@pytest.mark.asyncio
async def test_out_of_scope_produce_query(pipeline):
    """Test that 'apple 1 kg how much?' is classified as out_of_scope and does NOT mention battery or apps."""
    res = await pipeline.run("apple 1 kg how much?")
    assert res.intent.intent == "out_of_scope"
    assert "battery" not in res.draft.reply.lower()
    assert "settings > battery" not in res.draft.reply.lower()
    assert "produce" in res.draft.reply.lower() or "grocery" in res.draft.reply.lower() or "apple ecosystem" in res.draft.reply.lower()
    assert res.escalation.decision == "escalate"
    assert any("HITL" in reason or "out of scope" in reason.lower() for reason in res.escalation.reasons)


@pytest.mark.asyncio
async def test_out_of_scope_cost_inquiry(pipeline):
    """Test that 'why apple products are costly in indai' drafts polite ecosystem guidance and not battery."""
    res = await pipeline.run("why apple products are costly in indai")
    assert res.intent.intent == "out_of_scope"
    assert "battery" not in res.draft.reply.lower()
    assert "apple.com" in res.draft.reply.lower() or "ecosystem" in res.draft.reply.lower()
    assert res.escalation.decision == "escalate"


@pytest.mark.asyncio
async def test_out_of_scope_marriage_query(pipeline):
    """Test that personal query 'my wife not talking to me' does not draft charging advice."""
    res = await pipeline.run("my wife not talking to me")
    assert res.intent.intent == "out_of_scope"
    assert "charging port" not in res.draft.reply.lower()
    assert "cable" not in res.draft.reply.lower()
    assert "personal" in res.draft.reply.lower() or "ecosystem" in res.draft.reply.lower()
    assert res.escalation.decision == "escalate"


def test_rag_similarity_below_60_triggers_hitl(escalation_engine):
    """Test that top RAG similarity < 0.60 forces HITL approval."""
    decision = escalation_engine.decide(
        customer_message="My iPhone is having an unusual screen issue.",
        intent="display_screen",
        intent_confidence=0.85,
        draft_confidence=0.85,
        has_similar_history=True,
        rag_similarity=0.45,  # 45% < 60%
    )
    assert decision.decision == "escalate"
    assert any("below 60% threshold" in r for r in decision.reasons)


@pytest.mark.asyncio
async def test_touch_screen_not_working_query(pipeline, mock_provider):
    """Test that '@AppleSupport touch screen not working ' is classified as display_screen and NOT charging."""
    res = await pipeline.run("@AppleSupport touch screen not working ", use_web_search=False)
    assert res.intent.intent == "display_screen"
    assert "charging port" not in res.draft.reply.lower()
    assert "cable" not in res.draft.reply.lower()
    # Without RAG database, it must escalate to HITL and provide polite ecosystem request
    assert res.escalation.decision == "escalate"
    assert "apple devices and ecosystem services" in res.draft.reply.lower() or "details" in res.draft.reply.lower()

    # When grounded RAG context is available (>= 60%), drafter produces display troubleshooting
    drafter = ReplyDrafter(provider=mock_provider)
    grounded_threads = [
        RetrievedThreadItem(
            thread_id="seed-109",
            similarity=0.88,
            customer_msg="My iPhone touch screen is not working",
            brand_reply="Try a force restart for unresponsive touch screen.",
            intent_label="display_screen",
        )
    ]
    draft, _, _, _ = await drafter.draft(
        customer_message="@AppleSupport touch screen not working ",
        intent="display_screen",
        retrieved_threads=grounded_threads,
    )
    assert "force restart" in draft.reply.lower() or "display" in draft.reply.lower() or "touch screen" in draft.reply.lower()
    assert "charging port" not in draft.reply.lower()



@pytest.mark.asyncio
async def test_apk_download_query(pipeline):
    """Test that 'I can't download APK in my iphone x' clarifies App Store / APK incompatibility."""
    res = await pipeline.run("I can't download APK in my iphone x")
    assert res.intent.intent == "out_of_scope"
    assert "charging port" not in res.draft.reply.lower()
    assert "apk" in res.draft.reply.lower()
    assert "app store" in res.draft.reply.lower()
    assert res.escalation.decision == "escalate"


@pytest.mark.asyncio
async def test_low_rag_match_draft_polite_reply(mock_provider):
    """Test that low RAG similarity (< 60%) produces a polite Apple ecosystem inquiry."""
    drafter = ReplyDrafter(provider=mock_provider)
    low_rag_threads = [
        RetrievedThreadItem(
            thread_id="test-1",
            similarity=0.42,  # < 0.60
            customer_msg="Unrelated issue",
            brand_reply="Try something else",
            intent_label="general",
        )
    ]
    draft, _, _, _ = await drafter.draft(
        customer_message="Unrecognized problem with device",
        intent="display_screen",
        retrieved_threads=low_rag_threads,
    )
    assert "apple devices and ecosystem services" in draft.reply.lower() or "details" in draft.reply.lower()
    assert draft.confidence == 0.80


@pytest.mark.asyncio
async def test_iphone_12_software_query(pipeline):
    """
    Test that '@apple support hey i have a few problem with my software with my apple iphone 12':
    1. Is classified as 'ios_update_bugs' (NOT 'out_of_scope').
    2. Acknowledges 'iPhone 12' in the drafted reply.
    3. Does NOT ask the customer for their device model (since it was already provided).
    """
    query = "@apple support hey i have a few problem with my software with my apple iphone 12"
    res = await pipeline.run(query)

    # 1. Classification check
    assert res.intent.intent == "ios_update_bugs"

    # 2. Device awareness check
    reply_lower = res.draft.reply.lower()
    assert "iphone 12" in reply_lower

    # 3. Grounded reply check
    assert "what is your device model" not in reply_lower
    assert "what device" not in reply_lower
    assert "software" in reply_lower or "ios" in reply_lower


@pytest.mark.asyncio
async def test_iphone_12_exchange_web_search_query(pipeline):
    """
    Test that '@apple support i need to exchange my i phone 12 can what is the process':
    1. Is classified as 'purchase_refund_billing' (NOT 'out_of_scope').
    2. Triggers web search grounding when RAG has 0 matches.
    3. Retrieved threads contain official Apple Trade In reference (https://www.apple.com/shop/trade-in).
    4. Drafted reply instructs on trade-in and includes the official Apple link without asking for device model.
    """
    query = "@apple support i need to exchange my i phone 12 can what is the process"
    res = await pipeline.run(query)

    # 1. Classification check
    assert res.intent.intent == "purchase_refund_billing"

    # 2. Web search check
    assert res.meta.web_search_used is True
    assert len(res.retrieved) > 0
    assert any(t.source == "web_search" for t in res.retrieved)

    # 3. Grounded link check
    assert any("trade-in" in (t.url or "") or "trade" in t.brand_reply.lower() for t in res.retrieved)

    # 4. Draft reply check
    reply_lower = res.draft.reply.lower()
    assert "trade" in reply_lower or "exchange" in reply_lower
    assert "https://www.apple.com/shop/trade-in" in res.draft.reply
    assert "share more details about your apple device model" not in reply_lower
