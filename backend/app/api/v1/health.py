"""Liveness and readiness health check API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.core.config import settings
from app.llm.factory import get_llm_provider

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Service liveness and readiness probe."""
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    provider = get_llm_provider()
    llm_ok = await provider.health()

    status_str = "healthy" if (db_ok and llm_ok) else "degraded"

    return {
        "status": status_str,
        "database": db_ok,
        "llm_provider": {
            "name": provider.provider_name,
            "model": provider.model_name,
            "healthy": llm_ok,
        },
        "brand": settings.BRAND,
    }

