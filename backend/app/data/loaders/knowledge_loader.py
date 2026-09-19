"""
Knowledge Sources Loader

Loads and formats knowledge from all three sources:
- iFixit repair guides
- Synthetically generated resolutions
- Apple forum threads / real support threads
Provides utilities for RAG seeding and coverage reporting.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict

logger = logging.getLogger(__name__)

DATA_DIR_DEFAULT = Path(__file__).resolve().parent.parent / "knowledge_sources"


class KnowledgeLoader:
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR_DEFAULT
        self._ifixit_cache: Optional[List[Dict]] = None
        self._synthetic_cache: Optional[List[Dict]] = None
        self._forum_cache: Optional[List[Dict]] = None

    def load_ifixit_guides(
        self,
        device_filter: Optional[str] = None,
        difficulty_filter: Optional[str] = None,
    ) -> List[Dict]:
        """Loads iFixit Apple guides, with optional device category or difficulty filtering."""
        if self._ifixit_cache is None:
            fpath = self.data_dir / "ifixit_apple_guides.json"
            if fpath.exists():
                with open(fpath, "r", encoding="utf-8") as f:
                    self._ifixit_cache = json.load(f)
            else:
                self._ifixit_cache = []

        res = self._ifixit_cache
        if device_filter:
            d_lower = device_filter.lower()
            res = [g for g in res if d_lower in g.get("device_category", "").lower() or d_lower in g.get("customer_message", "").lower()]
        if difficulty_filter:
            res = [g for g in res if g.get("difficulty", "").lower() == difficulty_filter.lower()]
        return res

    def load_synthetic_resolutions(
        self,
        min_helpfulness: float = 0.0,
        approved_only: bool = False,
    ) -> List[Dict]:
        """Loads synthetic resolutions."""
        if self._synthetic_cache is None:
            fpath = self.data_dir / "synthetic_resolutions.json"
            if fpath.exists():
                with open(fpath, "r", encoding="utf-8") as f:
                    self._synthetic_cache = json.load(f)
            else:
                self._synthetic_cache = []

        res = self._synthetic_cache
        if approved_only:
            res = [r for r in res if r.get("reviewed", False) is True]
        if min_helpfulness > 0.0:
            res = [r for r in res if r.get("helpfulness_score", 1.0) >= min_helpfulness]
        return res

    def load_forum_threads(
        self,
        solved_only: bool = False,
        min_upvotes: int = 0,
    ) -> List[Dict]:
        """Loads Apple forum / seed support threads."""
        if self._forum_cache is None:
            fpath = self.data_dir / "apple_forum_threads.json"
            if fpath.exists():
                with open(fpath, "r", encoding="utf-8") as f:
                    self._forum_cache = json.load(f)
            else:
                self._forum_cache = []

        res = self._forum_cache
        if solved_only:
            res = [t for t in res if t.get("solved", True)]
        if min_upvotes > 0:
            res = [t for t in res if t.get("upvotes", 10) >= min_upvotes]
        return res

    def get_all_knowledge_entries(self) -> List[Dict[str, Any]]:
        """
        Returns a unified list of knowledge entries ready for RAG ingestion:
        [
            {
                "customer_message": str,
                "resolution_text": str,
                "intent": str,
                "source_type": str,
                "helpfulness_ratio": float,
            }
        ]
        """
        all_entries = []

        # 1. iFixit guides
        for item in self.load_ifixit_guides():
            all_entries.append({
                "customer_message": item.get("customer_message", ""),
                "resolution_text": item.get("resolution_text", ""),
                "intent": item.get("intent", "other_inquiry"),
                "source_type": "ifixit",
                "helpfulness_ratio": 0.85,
            })

        # 2. Synthetic resolutions (reviewed only)
        for item in self.load_synthetic_resolutions(approved_only=True):
            all_entries.append({
                "customer_message": item.get("customer_message", ""),
                "resolution_text": item.get("resolution_text", ""),
                "intent": item.get("intent", "other_inquiry"),
                "source_type": "synthetic",
                "helpfulness_ratio": 0.75,
            })

        # 3. Forum / seed threads
        for item in self.load_forum_threads():
            all_entries.append({
                "customer_message": item.get("customer_message", ""),
                "resolution_text": item.get("resolution_text", ""),
                "intent": item.get("intent", "other_inquiry"),
                "source_type": item.get("source_type", "forum"),
                "helpfulness_ratio": 0.90,
            })

        return all_entries

    async def seed_knowledge_base(self, session, embedding_service) -> int:
        """
        Asynchronously seeds the knowledge base database table idempotently.
        Inserts new entries if customer_message is not already present.
        """
        from sqlalchemy import select
        from app.models.knowledge_base import KnowledgeEntry

        entries = self.get_all_knowledge_entries()
        seeded_count = 0

        for entry_data in entries:
            cust_msg = entry_data["customer_message"].strip()
            if not cust_msg:
                continue

            # Check for existence
            stmt = select(KnowledgeEntry.id).where(KnowledgeEntry.customer_message == cust_msg)
            existing = (await session.execute(stmt)).scalar_one_or_none()

            if not existing:
                emb = None
                if embedding_service:
                    try:
                        emb = embedding_service.embed_text(cust_msg)
                    except Exception as e:
                        logger.warning(f"Error embedding knowledge entry '{cust_msg[:30]}': {e}")

                new_kb = KnowledgeEntry(
                    source_type=entry_data.get("source_type", "seed_dataset"),
                    customer_message=cust_msg,
                    resolution_text=entry_data["resolution_text"],
                    intent=entry_data.get("intent"),
                    embedding=emb,
                    helpfulness_ratio=entry_data.get("helpfulness_ratio", 0.8),
                    is_active=True,
                )
                session.add(new_kb)
                seeded_count += 1

        if seeded_count > 0:
            await session.commit()
            logger.info(f"Seeded {seeded_count} new entries into KnowledgeBase.")

        return seeded_count

    def get_coverage_report(self) -> Dict[str, Any]:
        """
        Analyzes coverage across intents and device families.
        Identifies any intent gaps.
        """
        entries = self.get_all_knowledge_entries()
        intent_counts = defaultdict(int)
        source_counts = defaultdict(int)
        device_counts = defaultdict(int)

        devices = ["iphone", "ipad", "macbook", "watch", "airpods", "vision"]

        for e in entries:
            intent_counts[e.get("intent", "unknown")] += 1
            source_counts[e.get("source_type", "unknown")] += 1
            text = (e.get("customer_message", "") + " " + e.get("resolution_text", "")).lower()
            for d in devices:
                if d in text:
                    device_counts[d] += 1

        # Check against canonical intents
        canonical_intents = [
            "battery_performance", "charging_issues", "connectivity_wifi_bluetooth",
            "audio_speaker_mic", "display_screen", "hardware_damage",
            "icloud_sync_storage", "apple_id_account", "ios_update_bugs",
            "app_crashes", "performance_speed", "purchase_refund_billing",
            "lost_device_find_my", "out_of_scope"
        ]

        gaps = [c for c in canonical_intents if intent_counts[c] == 0]

        return {
            "total_entries": len(entries),
            "by_source": dict(source_counts),
            "by_intent": dict(intent_counts),
            "by_device": dict(device_counts),
            "gap_intents": gaps,
            "coverage_percentage": round(((len(canonical_intents) - len(gaps)) / len(canonical_intents)) * 100, 1),
        }

