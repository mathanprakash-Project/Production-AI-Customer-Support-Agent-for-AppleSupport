"""
Unit tests for Cognis-style Multi-Turn Memory system (Module 1).
Tests SessionMemoryService, UserMemoryService, ContextMemoryService,
FactExtractor, HybridSearchEngine, and MemoryManager.
"""

import pytest
from app.db.session import get_standalone_session
from app.memory.session_memory import SessionMemoryService
from app.memory.user_memory import UserMemoryService
from app.memory.context_memory import ContextMemoryService
from app.memory.fact_extractor import FactExtractor
from app.memory.hybrid_search import HybridSearchEngine
from app.memory.memory_manager import MemoryManager
import uuid
from app.llm.providers.mock import MockProvider


@pytest.mark.asyncio
async def test_session_memory_lifecycle():
    session = await get_standalone_session()
    async with session:
        service = SessionMemoryService(session)
        user_id = f"@test_user_mem_{uuid.uuid4().hex[:8]}"
        
        # 1. Create or get session
        conv_session = await service.get_or_create_session(user_identifier=user_id)
        assert conv_session.id is not None
        assert conv_session.user_identifier == user_id
        assert conv_session.turn_count == 0
        
        # 2. Add customer turn
        turn1 = await service.add_turn(
            session_id=conv_session.id,
            role="customer",
            message="Hey, my iPhone 14 won't turn on.",
            intent="charging_issues",
        )
        assert turn1.turn_index == 0
        assert turn1.role == "customer"
        
        # 3. Add agent turn
        turn2 = await service.add_turn(
            session_id=conv_session.id,
            role="agent",
            message="Have you tried force restarting it?",
        )
        assert turn2.turn_index == 1
        
        # 4. Add follow-up customer turn (multi-turn!)
        turn3 = await service.add_turn(
            session_id=conv_session.id,
            role="customer",
            message="Yes, I already tried that and it didn't help.",
        )
        assert turn3.turn_index == 2
        
        # 5. Retrieve history
        history = await service.get_history(session_id=conv_session.id)
        assert len(history) == 3
        
        # 6. Format history for LLM prompt
        formatted = await service.format_history_for_prompt(session_id=conv_session.id)
        assert "Customer: Hey, my iPhone 14 won't turn on." in formatted
        assert "Agent: Have you tried force restarting it?" in formatted
        assert "Customer: Yes, I already tried that and it didn't help." in formatted


@pytest.mark.asyncio
async def test_user_memory_facts():
    session = await get_standalone_session()
    async with session:
        service = UserMemoryService(session)
        user_id = f"@persistent_cust_{uuid.uuid4().hex[:8]}"
        
        # 1. Store facts
        fact1 = await service.store_fact(
            user_identifier=user_id,
            category="device_info",
            fact_text="Device model: iPhone 15 Pro Max",
        )
        assert fact1.id is not None
        assert fact1.category == "device_info"
        
        fact2 = await service.store_fact(
            user_identifier=user_id,
            category="os_version",
            fact_text="OS version: iOS 18.1",
        )
        assert fact2.id is not None
        
        # 2. Recall facts
        facts = await service.recall_facts(user_identifier=user_id)
        assert len(facts) >= 2
        
        # 3. User profile summary for prompt injection
        summary = await service.get_user_profile_summary(user_identifier=user_id)
        assert "iPhone 15 Pro Max" in summary
        assert "iOS 18.1" in summary


@pytest.mark.asyncio
async def test_context_memory():
    session = await get_standalone_session()
    async with session:
        service = ContextMemoryService(session)
        test_session_id = f"test-session-ctx-{uuid.uuid4().hex[:8]}"
        
        # 1. Store working context
        await service.store(test_session_id, "retrieval_k", {"count": 3, "source": "pgvector"})
        await service.store(test_session_id, "classifier_tag", {"tag": "battery_performance"})
        
        # 2. Retrieve
        val = await service.retrieve(test_session_id, "retrieval_k")
        assert val is not None
        assert val["count"] == 3
        
        # 3. Get all
        all_ctx = await service.get_all(test_session_id)
        assert "retrieval_k" in all_ctx
        assert "classifier_tag" in all_ctx
        
        # 4. Clear
        await service.clear(test_session_id)
        cleared = await service.retrieve(test_session_id, "retrieval_k")
        assert cleared is None


def test_fact_extractor_deterministic():
    extractor = FactExtractor()
    
    # Test device extraction
    facts = extractor.extract_facts_deterministic("My iPhone 14 Pro battery dies in 2 hours on iOS 18.1")
    categories = [f["category"] for f in facts]
    assert "device_info" in categories
    assert "os_version" in categories
    
    fact_texts = " ".join([f["fact"] for f in facts])
    assert "iPhone 14 Pro" in fact_texts
    assert "18.1" in fact_texts


def test_hybrid_search_rrf():
    engine = HybridSearchEngine()
    
    docs = [
        "iPhone 15 battery drain issues troubleshooting",
        "How to restart your iPad Air when frozen",
        "AirPods Pro audio crackling and disconnects",
        "Apple ID account password reset instructions",
    ]
    
    # Test BM25
    bm25_res = engine.bm25_search("battery drain", docs, top_k=2)
    assert len(bm25_res) > 0
    assert bm25_res[0][0] == 0  # First doc is most relevant
    
    # Test RRF Fusion
    rankings = [
        [(0, 0.9), (1, 0.5), (2, 0.2)],
        [(0, 0.8), (2, 0.6), (1, 0.1)],
    ]
    fused = engine.rrf_fusion(rankings, k=60)
    assert len(fused) > 0
    assert fused[0][0] == 0  # Doc 0 was ranked first in both


@pytest.mark.asyncio
async def test_memory_manager_integration():
    session = await get_standalone_session()
    async with session:
        provider = MockProvider()
        manager = MemoryManager(session, provider)
        user_id = f"@multiturn_tester_{uuid.uuid4().hex[:8]}"
        
        # Turn 1
        res1 = await manager.process_customer_message(
            user_identifier=user_id,
            message="Hi @AppleSupport, my iPhone 13 is overheating.",
        )
        assert res1["session_id"] is not None
        assert any(f["category"] == "device_info" for f in res1.get("extracted_facts", []))
        
        # Record agent reply
        await manager.record_agent_response(res1["session_id"], "Please check Settings > Battery.")
        
        # Turn 2 (Follow-up!)
        res2 = await manager.process_customer_message(
            user_identifier=user_id,
            message="I checked it, Battery Health says 74%.",
        )
        assert res2["session_id"] == res1["session_id"]  # Same session reused!
        assert "iPhone 13" in res2["conversation_history"]  # Remembers previous message!
