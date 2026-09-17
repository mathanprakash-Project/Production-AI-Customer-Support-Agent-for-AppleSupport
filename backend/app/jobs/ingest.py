"""
Data Ingestion Job: Preprocesses raw Twitter Customer Support CSV into Threads table.
Filters @AppleSupport, pairs customer inquiries with brand replies, strips agent sign-offs,
detects DM redirects, and generates vector embeddings.
"""

import asyncio
import csv
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from sqlalchemy import select

from app.core.config import settings
from app.db.session import async_session_factory
from app.models.thread import Thread
from app.llm.embeddings import get_embedding_service

logger = logging.getLogger(__name__)

# Regex patterns to strip support agent sign-offs (e.g., ^JM, ^SW, -Sarah, /Dan)
SIGNOFF_REGEX = re.compile(r"(\s*[\^/\-][A-Za-z]{1,4}\s*$|\s*\^[A-Za-z]{1,4}\b)")

# Regex patterns identifying canned "please DM us" redirects
DM_PATTERNS = [
    r"(?i)\bdm\s+us\b",
    r"(?i)\bsend\s+(?:us\s+)?(?:a\s+)?dm\b",
    r"(?i)\bdirect\s+message\b",
    r"(?i)\bprivate\s+message\b",
    r"(?i)\blink\s+in\s+bio\b",
    r"(?i)\bclick\s+here\s+to\s+dm\b",
]
DM_REGEX = re.compile("|".join(DM_PATTERNS))


def strip_agent_signoff(text: str) -> str:
    """Strips trailing agent sign-offs like '^JM' or '-Alex' from brand replies."""
    cleaned = SIGNOFF_REGEX.sub("", text).strip()
    return cleaned


def is_dm_response(text: str) -> bool:
    """Detects whether a brand reply is a canned redirection to Direct Messages."""
    return bool(DM_REGEX.search(text))


async def ingest_dataset(
    csv_path: Optional[str] = None,
    brand: str = settings.BRAND,
    max_rows: int = settings.SUBSAMPLE_SIZE,
):
    """Ingest Twitter customer support dataset into Postgres/SQLite threads table."""
    logger.info(f"Starting ingestion for brand '{brand}' (max_rows={max_rows})...")
    
    # Locate twcs.csv
    target_csv = None
    if csv_path and os.path.exists(csv_path):
        target_csv = csv_path
    else:
        # Search in data/
        for p in [settings.DATA_DIR, settings.PROJECT_ROOT_PATH / "data"]:
            for f in p.rglob("*.csv"):
                if "twcs" in f.name.lower():
                    target_csv = str(f)
                    break
            if target_csv:
                break

    if not target_csv:
        logger.warning(
            "twcs.csv not found in data/ directory. "
            "Skipping raw CSV load (seed threads already initialized via init_db)."
        )
        return

    logger.info(f"Reading CSV from {target_csv}...")
    embedder = get_embedding_service()
    
    # Read tweets and build author lookup
    tweets_by_id: Dict[str, Dict] = {}
    with open(target_csv, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i > 100000:  # Bound parsing memory
                break
            tweets_by_id[row["tweet_id"]] = row

    # Find brand replies and their corresponding customer inquiry
    pairs: List[Tuple[str, str, str, bool]] = []  # (tweet_id, cust_msg, brand_reply, is_dm)
    for tid, tweet in tweets_by_id.items():
        if tweet.get("author_id") == brand:
            reply_to_id = tweet.get("in_reply_to_tweet_id")
            if reply_to_id and reply_to_id in tweets_by_id:
                cust_tweet = tweets_by_id[reply_to_id]
                cust_msg = cust_tweet.get("text", "").strip()
                brand_raw = tweet.get("text", "").strip()
                brand_clean = strip_agent_signoff(brand_raw)
                is_dm = is_dm_response(brand_raw)

                if len(cust_msg) > 15 and len(brand_clean) > 10:
                    pairs.append((tid, cust_msg, brand_clean, is_dm))
                    if len(pairs) >= max_rows:
                        break

    logger.info(f"Extracted {len(pairs)} customer-brand thread pairs for @{brand}.")
    if not pairs:
        return

    # Ingest in batches into DB
    batch_size = 200
    total_inserted = 0

    async with async_session_factory() as session:
        for i in range(0, len(pairs), batch_size):
            batch = pairs[i : i + batch_size]
            cust_texts = [p[1] for p in batch]
            embeddings = embedder.embed_batch(cust_texts)

            threads_to_insert = []
            for (tid, cust_msg, brand_reply, is_dm), emb in zip(batch, embeddings):
                # Check existence
                existing = await session.execute(
                    select(Thread.id).where(Thread.tweet_id == tid)
                )
                if not existing.scalars().first():
                    thread = Thread(
                        tweet_id=tid,
                        customer_message=cust_msg,
                        brand_reply=brand_reply,
                        text_clean=brand_reply,
                        author_type="customer",
                        author_id=brand,
                        is_dm_request=is_dm,
                        embedding=emb,
                    )
                    threads_to_insert.append(thread)

            if threads_to_insert:
                session.add_all(threads_to_insert)
                await session.commit()
                total_inserted += len(threads_to_insert)
                logger.info(f"Inserted batch {i // batch_size + 1}: {total_inserted} total threads.")

    logger.info(f"Data ingestion complete. {total_inserted} threads saved.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(ingest_dataset())

