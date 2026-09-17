"""
Re-indexing Job: Computes or refreshes embeddings for all threads in the database.
"""

import asyncio
import logging
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.thread import Thread
from app.llm.embeddings import get_embedding_service

logger = logging.getLogger(__name__)


async def reindex_threads(batch_size: int = 100):
    """Backfill missing vector embeddings for stored threads."""
    logger.info("Starting embedding re-index job...")
    embedder = get_embedding_service()

    async with async_session_factory() as session:
        # Fetch threads with missing embeddings
        stmt = select(Thread).where(Thread.embedding.is_(None)).limit(1000)
        threads = list((await session.execute(stmt)).scalars().all())

        if not threads:
            logger.info("All threads already have embeddings. Nothing to re-index.")
            return

        logger.info(f"Re-indexing {len(threads)} threads...")
        for i in range(0, len(threads), batch_size):
            batch = threads[i : i + batch_size]
            texts = [t.customer_message for t in batch]
            embeddings = embedder.embed_batch(texts)

            for thread, emb in zip(batch, embeddings):
                thread.embedding = emb

            await session.commit()
            logger.info(f"Re-indexed {min(i + batch_size, len(threads))}/{len(threads)} threads.")

    logger.info("Re-indexing completed successfully.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(reindex_threads())

