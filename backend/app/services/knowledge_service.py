"""
Knowledge Base Service for managing learned resolutions and self-improving RAG.
"""

import csv
import logging
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.knowledge_base import KnowledgeEntry
from app.models.ticket import Ticket
from app.llm.embeddings import get_embedding_service

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Business logic for querying, updating, and expanding the Knowledge Base."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedder = get_embedding_service()

    async def list_entries(
        self, intent: Optional[str] = None, page: int = 1, size: int = 20
    ) -> Tuple[List[KnowledgeEntry], int]:
        """List paginated knowledge entries with optional intent filter."""
        offset = (page - 1) * size
        stmt = select(KnowledgeEntry)
        count_stmt = select(func.count(KnowledgeEntry.id))

        if intent:
            stmt = stmt.where(KnowledgeEntry.intent == intent)
            count_stmt = count_stmt.where(KnowledgeEntry.intent == intent)

        stmt = stmt.order_by(KnowledgeEntry.created_at.desc()).offset(offset).limit(size)

        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar() or 0

        res = await self.db.execute(stmt)
        items = list(res.scalars().all())
        return items, total

    async def get_entry(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """Fetch a single knowledge entry by ID."""
        stmt = select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def toggle_entry(self, entry_id: str, is_active: bool) -> Optional[KnowledgeEntry]:
        """Enable or disable a knowledge base entry from active RAG retrieval."""
        entry = await self.get_entry(entry_id)
        if not entry:
            return None
        entry.is_active = is_active
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def get_stats(self) -> Dict[str, Any]:
        """Compute health and size metrics for the knowledge base."""
        total_stmt = select(func.count(KnowledgeEntry.id))
        total_res = await self.db.execute(total_stmt)
        total = total_res.scalar() or 0

        seed_stmt = select(func.count(KnowledgeEntry.id)).where(KnowledgeEntry.source_type == "seed_dataset")
        seed_res = await self.db.execute(seed_stmt)
        from_seed = seed_res.scalar() or 0

        feedback_stmt = select(func.count(KnowledgeEntry.id)).where(KnowledgeEntry.source_type == "agent_approved")
        feedback_res = await self.db.execute(feedback_stmt)
        from_feedback = feedback_res.scalar() or 0

        growth_pct = round((from_feedback / total) * 100.0, 1) if total > 0 else 0.0

        return {
            "total_entries": total,
            "from_original_dataset": from_seed,
            "from_agent_feedback": from_feedback,
            "growth_from_feedback_pct": growth_pct,
        }

    async def add_from_approved_feedback(self, ticket: Ticket, approved_text: str) -> KnowledgeEntry:
        """
        Feedback Loop Mechanism:
        When a support agent approves or customizes a draft response,
        the ticket query and approved resolution are embedded and added
        to the knowledge base so future queries retrieve it.
        """
        embedding = self.embedder.embed_text(ticket.customer_text)

        entry = KnowledgeEntry(
            source_type="agent_approved",
            source_ticket_id=ticket.id,
            customer_message=ticket.customer_text,
            resolution_text=approved_text,
            intent=ticket.intent,
            embedding=embedding,
            times_retrieved=1,
            times_helpful=1,
            helpfulness_ratio=1.0,
            is_active=True,
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        logger.info(f"Learned resolution saved to KnowledgeBase: entry_id={entry.id} intent={ticket.intent}")
        return entry

    async def update_helpfulness(self, entry_ids: List[str], was_helpful: bool) -> None:
        """
        Increment retrieval and helpfulness counts for referenced knowledge entries.
        Allows helpful responses to rise in RAG retrieval rankings.
        """
        if not entry_ids:
            return

        for entry_id in entry_ids:
            entry = await self.get_entry(entry_id)
            if entry:
                entry.times_retrieved = (entry.times_retrieved or 0) + 1
                if was_helpful:
                    entry.times_helpful = (entry.times_helpful or 0) + 1
                entry.helpfulness_ratio = (
                    round(entry.times_helpful / entry.times_retrieved, 3)
                    if entry.times_retrieved > 0
                    else 0.5
                )

        await self.db.commit()

