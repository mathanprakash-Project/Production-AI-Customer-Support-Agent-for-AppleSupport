"""Intent Taxonomy catalog API routes."""

from typing import List
from fastapi import APIRouter
from app.agent.classifier import DEFAULT_TAXONOMY
from app.schemas.evaluation import IntentItem

router = APIRouter(prefix="/intents", tags=["Intents"])


@router.get("", response_model=List[IntentItem])
async def list_intents():
    """Retrieve the discovered intent taxonomy with descriptions and examples."""
    return [
        IntentItem(
            label=item["label"],
            description=item["description"],
            examples=item.get("examples", []),
            count=item.get("count", 0),
        )
        for item in DEFAULT_TAXONOMY
    ]

