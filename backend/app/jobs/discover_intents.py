"""
Intent Discovery Job: Discovers taxonomy by clustering embeddings and using LLM to name clusters.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List
import numpy as np
from sklearn.cluster import KMeans
from sqlalchemy import select

from app.core.config import settings
from app.db.session import async_session_factory
from app.models.thread import Thread
from app.llm.factory import get_llm_provider

logger = logging.getLogger(__name__)


async def discover_intents(n_clusters: int = 12) -> List[Dict[str, Any]]:
    """Cluster historical customer messages and name clusters using LLM."""
    logger.info(f"Starting intent discovery for {n_clusters} clusters...")

    async with async_session_factory() as session:
        stmt = select(Thread).where(Thread.embedding.isnot(None)).limit(1000)
        threads = list((await session.execute(stmt)).scalars().all())

    if len(threads) < n_clusters:
        logger.warning("Not enough threads in database to perform clustering. Using default taxonomy.")
        from app.agent.classifier import DEFAULT_TAXONOMY
        return DEFAULT_TAXONOMY

    embeddings = np.array([t.embedding for t in threads], dtype=np.float32)
    messages = [t.customer_message for t in threads]

    # Cluster using KMeans
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    labels = kmeans.fit_predict(embeddings)

    provider = get_llm_provider()
    discovered_taxonomy = []

    for cluster_id in range(n_clusters):
        cluster_indices = np.where(labels == cluster_id)[0]
        # Pick top 4 representative messages closest to cluster centroid
        centroid = kmeans.cluster_centers_[cluster_id]
        dists = np.linalg.norm(embeddings[cluster_indices] - centroid, axis=1)
        top_sample_indices = cluster_indices[np.argsort(dists)[:4]]
        sample_messages = [messages[idx] for idx in top_sample_indices]

        # LLM prompt to label cluster
        prompt = (
            "Analyze these 4 representative customer tweets to Apple Support from a single cluster:\n"
            + "\n".join(f"- {m}" for m in sample_messages)
            + "\n\nProvide a snake_case intent label (e.g. 'iphone_battery_drain') and a 1-sentence description. "
            "Output JSON with keys 'label' and 'description'."
        )

        try:
            res = await provider.generate(prompt, temperature=0.0)
            data = json.loads(res.text)
            label = data.get("label", f"cluster_{cluster_id}").strip().lower().replace(" ", "_")
            desc = data.get("description", "Discovered customer intent category.")
        except Exception:
            label = f"support_intent_{cluster_id}"
            desc = f"Customer issues relating to cluster {cluster_id}"

        discovered_taxonomy.append({
            "label": label,
            "description": desc,
            "examples": sample_messages[:2],
            "count": len(cluster_indices),
        })

    # Save snapshot
    out_path = settings.BACKEND_DIR / "app" / "config" / "intents.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(discovered_taxonomy, f, indent=2)

    logger.info(f"Discovered taxonomy saved to {out_path}")
    return discovered_taxonomy


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(discover_intents())

