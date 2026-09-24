import math
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.memory import UserMemory
from app.db.base import utc_now
try:
    from app.llm.embeddings import EmbeddingService, get_embedding_service
except ImportError:
    EmbeddingService = None
    def get_embedding_service(): return None

class UserMemoryService:
    def __init__(self, db: AsyncSession, embedding_service: Optional[EmbeddingService] = None):
        self.db = db
        self.embedding_service = embedding_service or get_embedding_service()
        
    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2: return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0 or norm2 == 0: return 0.0
        return dot / (norm1 * norm2)
        
    async def store_fact(self, user_identifier: str, category: str, fact_text: str, confidence: float = 0.8, session_id: Optional[str] = None) -> UserMemory:
        embedding = None
        if self.embedding_service:
            try:
                embedding = await self.embedding_service.embed_query(fact_text)
            except Exception:
                pass
                
        # Check for duplicates if embedding exists
        if embedding:
            stmt = select(UserMemory).where(
                UserMemory.user_identifier == user_identifier,
                UserMemory.category == category,
                UserMemory.is_active == True
            )
            result = await self.db.execute(stmt)
            existing_facts = result.scalars().all()
            
            for fact in existing_facts:
                if fact.embedding and isinstance(fact.embedding, list):
                    sim = self._cosine_similarity(embedding, fact.embedding)
                    if sim > 0.9:
                        fact.fact_text = fact_text
                        fact.confidence = confidence
                        fact.updated_at = utc_now()
                        if session_id:
                            fact.source_session_id = session_id
                        await self.db.commit()
                        await self.db.refresh(fact)
                        return fact
                        
        new_fact = UserMemory(
            user_identifier=user_identifier,
            category=category,
            fact_text=fact_text,
            confidence=confidence,
            source_session_id=session_id,
            embedding=embedding
        )
        self.db.add(new_fact)
        await self.db.commit()
        await self.db.refresh(new_fact)
        return new_fact
        
    async def recall_facts(self, user_identifier: str, query: Optional[str] = None, limit: int = 5) -> List[UserMemory]:
        stmt = select(UserMemory).where(
            UserMemory.user_identifier == user_identifier,
            UserMemory.is_active == True
        )
        result = await self.db.execute(stmt)
        facts = list(result.scalars().all())
        
        if not query or not self.embedding_service:
            return facts[:limit]
            
        try:
            query_emb = await self.embedding_service.embed_query(query)
            scored = []
            for f in facts:
                if f.embedding and isinstance(f.embedding, list):
                    score = self._cosine_similarity(query_emb, f.embedding)
                    scored.append((score, f))
                else:
                    scored.append((0.0, f))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [f for s, f in scored[:limit]]
        except Exception:
            return facts[:limit]
            
    async def get_user_profile_summary(self, user_identifier: str) -> str:
        facts = await self.recall_facts(user_identifier, limit=50)
        if not facts:
            return "No known facts about this customer."
            
        summary_lines = ["Known facts about this customer:"]
        
        facts_by_cat = {}
        for f in facts:
            facts_by_cat.setdefault(f.category, []).append(f.fact_text)
            
        for cat, texts in facts_by_cat.items():
            for text in texts:
                summary_lines.append(f"- {cat}: {text}")
                
        return "\n".join(summary_lines)
        
    async def deactivate_fact(self, fact_id: str):
        stmt = update(UserMemory).where(UserMemory.id == fact_id).values(is_active=False)
        await self.db.execute(stmt)
        await self.db.commit()
