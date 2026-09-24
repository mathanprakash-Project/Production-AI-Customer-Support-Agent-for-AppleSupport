from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models.memory import ContextMemory
from app.db.base import utc_now

class ContextMemoryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def store(self, session_id: str, key: str, value: dict):
        stmt = select(ContextMemory).where(
            ContextMemory.session_id == session_id,
            ContextMemory.key == key
        )
        result = await self.db.execute(stmt)
        mem = result.scalar_one_or_none()
        
        if mem:
            mem.value = value
            mem.created_at = utc_now()
        else:
            mem = ContextMemory(
                session_id=session_id,
                key=key,
                value=value
            )
            self.db.add(mem)
            
        await self.db.commit()
        
    async def retrieve(self, session_id: str, key: str) -> Optional[dict]:
        stmt = select(ContextMemory).where(
            ContextMemory.session_id == session_id,
            ContextMemory.key == key
        )
        result = await self.db.execute(stmt)
        mem = result.scalar_one_or_none()
        return mem.value if mem else None
        
    async def get_all(self, session_id: str) -> Dict[str, dict]:
        stmt = select(ContextMemory).where(ContextMemory.session_id == session_id)
        result = await self.db.execute(stmt)
        mems = result.scalars().all()
        return {m.key: m.value for m in mems}
        
    async def clear(self, session_id: str):
        stmt = delete(ContextMemory).where(ContextMemory.session_id == session_id)
        await self.db.execute(stmt)
        await self.db.commit()
