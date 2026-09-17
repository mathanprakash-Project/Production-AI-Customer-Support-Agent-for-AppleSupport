"""
Thread Repository with semantic vector search.
Uses pgvector cosine distance (<=>) in PostgreSQL, with Python cosine fallback.
"""

import logging
from typing import List, Optional, Tuple
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.thread import Thread, PGVECTOR_AVAILABLE
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class ThreadRepository(BaseRepository[Thread]):
    def __init__(self, db: AsyncSession):
        super().__init__(Thread, db)

    async def get_by_tweet_id(self, tweet_id: str) -> Optional[Thread]:
        result = await self.db.execute(select(Thread).where(Thread.tweet_id == tweet_id))
        return result.scalars().first()

    async def vector_search(
        self,
        query_embedding: List[float],
        top_k: int = 3,
        filter_dm: bool = True,
    ) -> List[Tuple[Thread, float]]:
        """
        Search for top-k similar threads using cosine similarity.
        Returns a list of tuples: (Thread, similarity_score).
        """
        # Determine if database dialect is PostgreSQL and pgvector is enabled
        bind = self.db.bind
        dialect_name = bind.dialect.name if bind else "sqlite"

        if dialect_name == "postgresql" and PGVECTOR_AVAILABLE:
            try:
                # Use pgvector cosine distance operator (<=>)
                stmt = select(
                    Thread,
                    (1.0 - Thread.embedding.cosine_distance(query_embedding)).label("similarity"),
                )
                if filter_dm:
                    stmt = stmt.where(Thread.is_dm_request.is_(False))
                stmt = stmt.where(Thread.author_type == "customer")
                stmt = stmt.order_by(Thread.embedding.cosine_distance(query_embedding)).limit(top_k)

                results = (await self.db.execute(stmt)).all()
                return [(row[0], float(row[1])) for row in results]
            except Exception as e:
                logger.warning(f"pgvector native search failed ({e}). Falling back to in-memory cosine search.")

        # Fallback: In-memory cosine similarity computation
        stmt = select(Thread).where(Thread.embedding.isnot(None))
        if filter_dm:
            stmt = stmt.where(Thread.is_dm_request.is_(False))
        stmt = stmt.where(Thread.author_type == "customer").limit(500)

        rows = list((await self.db.execute(stmt)).scalars().all())
        if not rows:
            return []

        q_vec = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec) or 1.0

        scored = []
        for thread in rows:
            if not thread.embedding:
                continue
            emb = np.array(thread.embedding, dtype=np.float32)
            denom = q_norm * (np.linalg.norm(emb) or 1.0)
            sim = float(np.dot(q_vec, emb) / denom)
            scored.append((thread, sim))

        # Sort descending by similarity
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

