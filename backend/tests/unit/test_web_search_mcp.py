"""
Unit tests for Web Search MCP Service and Pipeline Fallback Grounding.
Tests real-time search, domain security validation, and fallback resolution.
"""

import pytest
from app.agent.pipeline import AgentPipeline
from app.llm.providers.mock import MockProvider
from app.services.web_search_service import WebSearchService, APPROVED_APPLE_DOMAINS


@pytest.mark.asyncio
async def test_web_search_service_resolution():
    service = WebSearchService(timeout=1.0)
    
    # Test intent-based query with missing internal RAG
    results = await service.search_apple_support(
        query="My iPhone 14 touch screen is completely unresponsive after update",
        intent="display_screen",
        max_results=2,
    )
    
    assert len(results) > 0
    top = results[0]
    assert top.title is not None
    assert len(top.snippet) > 20
    assert "support.apple.com" in top.url or "apple.com" in top.url
    
    # Check domain security validation
    for r in results:
        assert any(domain in r.url.lower() for domain in APPROVED_APPLE_DOMAINS)


@pytest.mark.asyncio
async def test_pipeline_web_search_fallback():
    provider = MockProvider()
    service = WebSearchService(timeout=1.0)
    
    # Initialize pipeline with web search fallback enabled and empty thread repo
    pipeline = AgentPipeline(
        provider=provider,
        web_search=service,
        use_web_search=True,
    )
    
    # Query with no internal RAG matches
    res = await pipeline.run(
        customer_message="@AppleSupport my iPhone 14 battery drains overnight after installing iOS 18",
        use_web_search=True,
    )
    
    assert res.intent.intent in ["battery_performance", "ios_update_bugs"]
    assert res.meta.web_search_used is True
    assert len(res.retrieved) > 0
    assert any(item.source == "web_search" for item in res.retrieved)
    assert any("apple.com" in (item.url or "") for item in res.retrieved)
    # Grounded via web search so not escalated for 0 RAG grounding
    assert res.escalation.decision == "auto" or res.draft.confidence >= 0.70

