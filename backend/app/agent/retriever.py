"""
Stage 3: RAG Semantic Retriever.
Retrieves top-k historical support threads and verified knowledge base entries.
Applies helpfulness-weighted ranking:
  final_score = (vector_similarity * 0.7) + (helpfulness_ratio * 0.3)
Includes keyword fallback for uncommon terms.
"""

import logging
from typing import List, Optional
import numpy as np
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.llm.embeddings import EmbeddingService, get_embedding_service
from app.models.knowledge_base import KnowledgeEntry, PGVECTOR_AVAILABLE
from app.repositories.thread_repo import ThreadRepository
from app.schemas.inference import RetrievedThreadItem

logger = logging.getLogger(__name__)


class SemanticRetriever:
    """Retrieves top-k historical resolutions for grounded response synthesis."""

    def __init__(
        self,
        thread_repo: Optional[ThreadRepository] = None,
        db: Optional[AsyncSession] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        self.repo = thread_repo
        self.db = db or (thread_repo.db if thread_repo else None)
        self.embedder = embedding_service or get_embedding_service()

    async def retrieve(
        self,
        query: str,
        top_k: int = 3,
        filter_dm: bool = True,
        intent_filter: Optional[str] = None,
    ) -> List[RetrievedThreadItem]:
        """
        Compute query embedding and retrieve top-k similar solutions with
        helpfulness weighting.
        """
        if not query or len(query.strip()) < 3:
            return []

        query_vec = self.embedder.embed_text(query)
        items: List[RetrievedThreadItem] = []
        seen_texts = set()

        # 1. First search KnowledgeBase entries if session available
        if self.db:
            try:
                kb_items = await self._search_knowledge_base(
                    query_text=query,
                    query_vec=query_vec,
                    top_k=top_k * 2,
                    intent_filter=intent_filter,
                )
                for item in kb_items:
                    brand_norm = item.brand_reply.strip().lower()[:60]
                    if brand_norm not in seen_texts:
                        seen_texts.add(brand_norm)
                        items.append(item)
            except Exception as e:
                logger.warning(f"KnowledgeBase vector search failed ({e}), falling back to threads.")

        # 2. If knowledge base has fewer than top_k, query thread repository
        if len(items) < top_k and self.repo:
            try:
                scored_threads = await self.repo.vector_search(
                    query_embedding=query_vec,
                    top_k=(top_k - len(items)) * 2,
                    filter_dm=filter_dm,
                )
                for thread, sim in scored_threads:
                    brand_norm = thread.brand_reply.strip().lower()[:60]
                    if brand_norm in seen_texts:
                        continue
                    seen_texts.add(brand_norm)
                    items.append(
                        RetrievedThreadItem(
                            thread_id=thread.tweet_id,
                            similarity=round(sim, 3),
                            customer_msg=thread.customer_message,
                            brand_reply=thread.brand_reply,
                            intent_label=thread.intent_label,
                        )
                    )
            except Exception as e:
                logger.error(f"Thread vector search failed: {e}")

        # 3. Keyword fallback if still fewer than top_k
        if len(items) < top_k and self.db:
            keyword_items = await self._keyword_fallback(query, limit=top_k - len(items), seen_texts=seen_texts)
            items.extend(keyword_items)

        # Sort by similarity score descending and cap at top_k
        items.sort(key=lambda x: x.similarity, reverse=True)
        return items[:top_k]

    async def _search_knowledge_base(
        self,
        query_text: str,
        query_vec: List[float],
        top_k: int = 6,
        intent_filter: Optional[str] = None,
    ) -> List[RetrievedThreadItem]:
        """Search active KnowledgeBase items with helpfulness-weighted ranking."""
        stmt = select(KnowledgeEntry).where(KnowledgeEntry.is_active == True)
        if intent_filter:
            stmt = stmt.where(or_(KnowledgeEntry.intent == intent_filter, KnowledgeEntry.intent.is_(None)))

        res = await self.db.execute(stmt.limit(200))
        entries = list(res.scalars().all())

        if not entries:
            return []

        scored: List[RetrievedThreadItem] = []
        q_norm = np.linalg.norm(query_vec)
        if q_norm == 0:
            return []

        for entry in entries:
            if not entry.embedding:
                continue
            e_vec = entry.embedding
            # In-memory cosine similarity
            sim = float(np.dot(query_vec, e_vec) / (q_norm * np.linalg.norm(e_vec)))
            sim = max(0.0, min(1.0, sim))

            # Helpfulness weight formula: final = (vector_sim * 0.7) + (helpfulness_ratio * 0.3)
            helpfulness = entry.helpfulness_ratio if entry.helpfulness_ratio is not None else 0.5
            final_score = round((sim * 0.7) + (helpfulness * 0.3), 3)

            scored.append(
                RetrievedThreadItem(
                    thread_id=entry.id,
                    similarity=final_score,
                    customer_msg=entry.customer_message,
                    brand_reply=entry.resolution_text,
                    intent_label=entry.intent,
                )
            )

        scored.sort(key=lambda x: x.similarity, reverse=True)
        return scored[:top_k]

    async def _keyword_fallback(
        self, query: str, limit: int, seen_texts: set
    ) -> List[RetrievedThreadItem]:
        """Simple keyword matching fallback when vector similarities are sparse."""
        words = [w.lower() for w in query.split() if len(w) > 3 and w.isalnum()]
        stop_words = {"this", "that", "with", "have", "from", "need", "help", "your", "what"}
        keywords = [w for w in words if w not in stop_words][:3]

        if not keywords:
            return []

        conditions = [KnowledgeEntry.customer_message.ilike(f"%{kw}%") for kw in keywords]
        stmt = select(KnowledgeEntry).where(KnowledgeEntry.is_active == True).where(or_(*conditions)).limit(limit)

        res = await self.db.execute(stmt)
        entries = list(res.scalars().all())
        results = []

        for entry in entries:
            brand_norm = entry.resolution_text.strip().lower()[:60]
            if brand_norm in seen_texts:
                continue
            seen_texts.add(brand_norm)
            results.append(
                RetrievedThreadItem(
                    thread_id=entry.id,
                    similarity=0.50,
                    customer_msg=entry.customer_message,
                    brand_reply=entry.resolution_text,
                    intent_label=entry.intent,
                )
            )
        return results
