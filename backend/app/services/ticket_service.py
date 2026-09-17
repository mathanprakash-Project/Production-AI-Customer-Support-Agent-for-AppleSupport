"""Service layer for ticket management."""

from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ticket import Ticket
from app.repositories.ticket_repo import TicketRepository
from app.schemas.ticket import TicketCreate


class TicketService:
    def __init__(self, db: AsyncSession):
        self.repo = TicketRepository(db)

    async def list_tickets(
        self,
        status: Optional[str] = None,
        page: int = 1,
        size: int = 50,
    ) -> Tuple[List[Ticket], int]:
        skip = (page - 1) * size
        return await self.repo.list_filtered(status=status, skip=skip, limit=size)

    async def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        return await self.repo.get(ticket_id)

    async def create_ticket(self, data: TicketCreate) -> Ticket:
        ticket = Ticket(
            customer_text=data.customer_text,
            tweet_author=data.tweet_author or "@customer",
            source_tweet_id=data.source_tweet_id,
            status="open",
        )
        return await self.repo.create(ticket)

    async def update_status(self, ticket_id: str, new_status: str) -> Optional[Ticket]:
        return await self.repo.update_status(ticket_id, new_status)

