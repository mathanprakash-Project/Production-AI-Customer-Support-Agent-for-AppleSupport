"""
Knowledge Base Seeding Script

Idempotently populates the KnowledgeBase with entries from:
- iFixit repair guides
- Reviewed synthetic resolutions
- Apple Support forum / seed threads

Usage:
    python scripts/seed_knowledge_base.py [--dry-run] [--source ifixit|synthetic|forum|all]
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Ensure backend package is in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.data.loaders.knowledge_loader import KnowledgeLoader
from app.db.session import async_session_factory, engine
from app.llm.embeddings import get_embedding_service
from app.db.base import Base

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="Seed knowledge base from JSON knowledge sources.")
    parser.add_argument("--dry-run", action="store_true", help="Preview entries to seed without writing to DB.")
    parser.add_argument("--source", default="all", choices=["all", "ifixit", "synthetic", "forum"], help="Specific source to seed.")
    args = parser.parse_args()

    loader = KnowledgeLoader()
    coverage = loader.get_coverage_report()
    logger.info("Knowledge Sources Coverage Summary:")
    logger.info(f"  Total Entries Available: {coverage['total_entries']}")
    logger.info(f"  By Source: {coverage['by_source']}")
    logger.info(f"  Coverage Percentage: {coverage['coverage_percentage']}%")
    if coverage["gap_intents"]:
        logger.warning(f"  Gap Intents: {coverage['gap_intents']}")

    all_entries = loader.get_all_knowledge_entries()
    if args.source != "all":
        all_entries = [e for e in all_entries if e.get("source_type") == args.source]

    logger.info(f"Selected {len(all_entries)} entries from source filter '{args.source}'.")

    if args.dry_run:
        logger.info("Dry run requested. Displaying first 5 entries:")
        for i, entry in enumerate(all_entries[:5], 1):
            logger.info(f"[{i}] [{entry['source_type']}] [{entry['intent']}] {entry['customer_message'][:60]}...")
        logger.info("Dry run finished. 0 changes made.")
        return

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    embedder = get_embedding_service()
    async with async_session_factory() as session:
        seeded = await loader.seed_knowledge_base(session, embedder)
        logger.info(f"Successfully seeded {seeded} new knowledge entries into database.")


if __name__ == "__main__":
    asyncio.run(main())

