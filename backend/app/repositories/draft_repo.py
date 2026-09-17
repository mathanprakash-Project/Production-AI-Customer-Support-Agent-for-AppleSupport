"""Draft Repository for persisting AI generation outputs and metrics."""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.draft import Draft
from app.repositories.base import BaseRepository


class DraftRepository(BaseRepository[Draft]):
    def __init__(self, db: AsyncSession):
        super().__init__(Draft, db)

    async def get_by_ticket_id(self, ticket_id: str) -> List[Draft]:
        stmt = (
            select(Draft)
            .where(Draft.ticket_id == ticket_id)
            .order_by(Draft.created_at.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_latest_by_ticket_id(self, ticket_id: str) -> Optional[Draft]:
        stmt = (
            select(Draft)
            .where(Draft.ticket_id == ticket_id)
            .order_by(Draft.created_at.desc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalars().first()

