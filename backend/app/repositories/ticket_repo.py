"""Ticket Repository for support ticket persistence and querying."""

from typing import List, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ticket import Ticket
from app.repositories.base import BaseRepository


class TicketRepository(BaseRepository[Ticket]):
    def __init__(self, db: AsyncSession):
        super().__init__(Ticket, db)

    async def list_filtered(
        self,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Ticket], int]:
        stmt = select(Ticket)
        count_stmt = select(func.count(Ticket.id))

        if status:
            stmt = stmt.where(Ticket.status == status)
            count_stmt = count_stmt.where(Ticket.status == status)

        stmt = stmt.order_by(Ticket.created_at.desc()).offset(skip).limit(limit)
        
        total = (await self.db.execute(count_stmt)).scalar() or 0
        items = list((await self.db.execute(stmt)).scalars().all())
        return items, total

    async def update_status(self, ticket_id: str, new_status: str) -> Optional[Ticket]:
        ticket = await self.get(ticket_id)
        if ticket:
            ticket.status = new_status
            await self.db.flush()
            await self.db.refresh(ticket)
        return ticket

