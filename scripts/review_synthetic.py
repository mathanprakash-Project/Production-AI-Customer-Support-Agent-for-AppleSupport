"""
Synthetic Resolutions Review Tool

CLI workflow for human-in-the-loop auditing and curation of synthetically
generated troubleshooting resolutions before ingestion into the knowledge base.

Usage:
    python scripts/review_synthetic.py --stats
    python scripts/review_synthetic.py --list
    python scripts/review_synthetic.py --approve-all
"""

import argparse
import json
import logging
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

SYNTHETIC_PATH = ROOT_DIR / "backend" / "app" / "data" / "knowledge_sources" / "synthetic_resolutions.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_synthetic():
    if not SYNTHETIC_PATH.exists():
        logger.error(f"Synthetic file not found at {SYNTHETIC_PATH}")
        return []
    with open(SYNTHETIC_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_synthetic(data):
    with open(SYNTHETIC_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Updated {SYNTHETIC_PATH}")


def main():
    parser = argparse.ArgumentParser(description="Review and curate synthetic knowledge resolutions.")
    parser.add_argument("--stats", action="store_true", help="Display review status statistics.")
    parser.add_argument("--list", action="store_true", help="List unreviewed entries.")
    parser.add_argument("--approve-all", action="store_true", help="Batch approve all unreviewed entries.")
    parser.add_argument("--limit", type=int, default=10, help="Max items to list.")
    args = parser.parse_args()

    data = load_synthetic()
    if not data:
        return

    reviewed = [d for d in data if d.get("reviewed") is True]
    unreviewed = [d for d in data if d.get("reviewed") is not True]

    if args.stats or (not args.list and not args.approve_all):
        logger.info(f"Total Synthetic Entries: {len(data)}")
        logger.info(f"  Approved/Reviewed: {len(reviewed)} ({len(reviewed)/len(data)*100:.1f}%)")
        logger.info(f"  Unreviewed: {len(unreviewed)} ({len(unreviewed)/len(data)*100:.1f}%)")

    if args.list:
        logger.info(f"Showing up to {args.limit} unreviewed entries:")
        for i, item in enumerate(unreviewed[:args.limit], 1):
            logger.info(f"[{i}] [{item.get('intent')}] Q: {item.get('customer_message')}")
            logger.info(f"     A: {item.get('resolution_text')[:80]}...")

    if args.approve_all:
        for item in data:
            item["reviewed"] = True
        save_synthetic(data)
        logger.info(f"Approved all {len(data)} synthetic resolution entries.")


if __name__ == "__main__":
    main()

