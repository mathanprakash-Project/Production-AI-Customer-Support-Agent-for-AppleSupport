"""
Knowledge Base API endpoints for managing and auditing learned support solutions.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.knowledge import (
    KnowledgeEntryResponse,
    KnowledgeListResponse,
    KnowledgeStats,
    KnowledgeToggleRequest,
)
from app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


@router.get("", response_model=KnowledgeListResponse)
async def list_knowledge_entries(
    intent: Optional[str] = Query(None, description="Filter by intent category"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List paginated knowledge base entries with optional intent filter."""
    service = KnowledgeService(db)
    items, total = await service.list_entries(intent=intent, page=page, size=size)
    return KnowledgeListResponse(
        items=[KnowledgeEntryResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/stats", response_model=KnowledgeStats)
async def get_knowledge_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve size, origin distribution, and growth statistics for the knowledge base."""
    service = KnowledgeService(db)
    stats = await service.get_stats()
    return KnowledgeStats(**stats)


@router.get("/{entry_id}", response_model=KnowledgeEntryResponse)
async def get_knowledge_entry(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single knowledge base entry by ID."""
    service = KnowledgeService(db)
    entry = await service.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge entry not found.")
    return KnowledgeEntryResponse.model_validate(entry)


@router.patch("/{entry_id}", response_model=KnowledgeEntryResponse)
async def toggle_knowledge_entry(
    entry_id: str,
    body: KnowledgeToggleRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Enable or disable a knowledge base entry from RAG retrieval ranking."""
    service = KnowledgeService(db)
    entry = await service.toggle_entry(entry_id, body.is_active)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge entry not found.")
    return KnowledgeEntryResponse.model_validate(entry)

