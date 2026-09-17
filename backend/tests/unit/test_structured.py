import pytest
from pydantic import BaseModel
from app.llm.structured import clean_json_text, parse_and_validate_structured


class SampleSchema(BaseModel):
    intent: str
    confidence: float


def test_clean_json_markdown():
    text = "```json\n{\"intent\": \"iphone_wont_charge\", \"confidence\": 0.95}\n```"
    cleaned = clean_json_text(text)
    assert cleaned == "{\"intent\": \"iphone_wont_charge\", \"confidence\": 0.95}"


@pytest.mark.asyncio
async def test_parse_valid_json():
    text = "{\"intent\": \"battery_drain\", \"confidence\": 0.88}"
    result = await parse_and_validate_structured(text, SampleSchema)
    assert result.intent == "battery_drain"
    assert result.confidence == 0.88


@pytest.mark.asyncio
async def test_parse_with_repair():
    malformed = "intent: battery_drain, confidence: 0.8"

    async def mock_repair(prompt):
        return "{\"intent\": \"battery_drain\", \"confidence\": 0.80}"

    result = await parse_and_validate_structured(
        malformed,
        SampleSchema,
        repair_func=mock_repair,
    )
    assert result.intent == "battery_drain"
    assert result.confidence == 0.80


@pytest.mark.asyncio
async def test_parse_fallback_to_safe_default():
    malformed = "Totally invalid response with no recovery"
    safe_default = SampleSchema(intent="fallback", confidence=0.5)

    async def failing_repair(prompt):
        return "still broken"

    result = await parse_and_validate_structured(
        malformed,
        SampleSchema,
        repair_func=failing_repair,
        safe_default=safe_default,
    )
    assert result.intent == "fallback"
    assert result.confidence == 0.5

