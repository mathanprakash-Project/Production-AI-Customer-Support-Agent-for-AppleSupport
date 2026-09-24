"""Helpfulness-Weighted Flywheel Service.
Tracks feedback patterns, ticket reopens, and adjusts knowledge base helpfulness weights."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import Feedback
from app.models.knowledge_base import KnowledgeEntry
from app.models.ticket import Ticket
from app.models.draft import Draft

logger = logging.getLogger(__name__)

class FlywheelService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_flywheel_metrics(self) -> Dict[str, Any]:
        """Calculate flywheel velocity metrics."""
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # KB growth this week
        weekly_growth = await self.db.execute(
            select(func.count(KnowledgeEntry.id)).where(
                and_(
                    KnowledgeEntry.source_type == "agent_approved",
                    KnowledgeEntry.created_at >= week_ago
                )
            )
        )
        weekly_new = weekly_growth.scalar() or 0
        
        # Total KB size
        total_kb = await self.db.execute(select(func.count(KnowledgeEntry.id)))
        total_size = total_kb.scalar() or 0
        
        # Average helpfulness
        avg_help = await self.db.execute(
            select(func.avg(KnowledgeEntry.helpfulness_ratio)).where(KnowledgeEntry.is_active == True)
        )
        avg_helpfulness = round(float(avg_help.scalar() or 0.5), 3)
        
        # Feedback distribution this month
        feedback_counts = await self.db.execute(
            select(Feedback.action, func.count(Feedback.id)).where(
                Feedback.created_at >= month_ago
            ).group_by(Feedback.action)
        )
        feedback_dist = {row[0]: row[1] for row in feedback_counts.fetchall()}
        
        # Reopen rate: tickets resolved then reopened (status changed back to open)
        resolved_count = await self.db.execute(
            select(func.count(Ticket.id)).where(
                and_(
                    Ticket.resolved_at.isnot(None),
                    Ticket.created_at >= month_ago
                )
            )
        )
        resolved = resolved_count.scalar() or 0
        
        # Top performing KB entries
        top_entries = await self.db.execute(
            select(KnowledgeEntry)
            .where(KnowledgeEntry.is_active == True)
            .order_by(KnowledgeEntry.times_retrieved.desc())
            .limit(5)
        )
        top_performers = [
            {
                "id": e.id[:8],
                "intent": e.intent or "unknown",
                "times_retrieved": e.times_retrieved,
                "helpfulness_ratio": e.helpfulness_ratio,
            }
            for e in top_entries.scalars().all()
        ]
        
        return {
            "kb_total_entries": total_size,
            "kb_weekly_growth": weekly_new,
            "kb_growth_rate_pct": round((weekly_new / max(total_size, 1)) * 100, 1),
            "avg_helpfulness_ratio": avg_helpfulness,
            "feedback_distribution": feedback_dist,
            "resolved_tickets_month": resolved,
            "top_performing_entries": top_performers,
        }
    
    async def decay_stale_entries(self, days_inactive: int = 90, decay_factor: float = 0.95):
        """Decay helpfulness ratio for entries not retrieved recently."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_inactive)
        stale = await self.db.execute(
            select(KnowledgeEntry).where(
                and_(
                    KnowledgeEntry.is_active == True,
                    KnowledgeEntry.updated_at < cutoff,
                    KnowledgeEntry.helpfulness_ratio > 0.1
                )
            )
        )
        entries = stale.scalars().all()
        decayed = 0
        for entry in entries:
            entry.helpfulness_ratio = round(max(0.1, (entry.helpfulness_ratio or 0.5) * decay_factor), 3)
            decayed += 1
        
        if decayed > 0:
            await self.db.commit()
            logger.info(f"Decayed helpfulness for {decayed} stale KB entries.")
        return decayed
