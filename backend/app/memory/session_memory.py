import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.models.memory import ConversationSession, ConversationTurn
from app.db.base import utc_now

class SessionMemoryService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_or_create_session(self, user_identifier: str, ticket_id: Optional[str] = None, agent_id: Optional[str] = None) -> ConversationSession:
        thirty_mins_ago = utc_now() - datetime.timedelta(minutes=30)
        
        stmt = select(ConversationSession).where(
            ConversationSession.user_identifier == user_identifier,
            ConversationSession.is_active == True,
            ConversationSession.last_active_at >= thirty_mins_ago
        ).order_by(ConversationSession.last_active_at.desc())
        
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            session = ConversationSession(
                user_identifier=user_identifier,
                ticket_id=ticket_id,
                agent_id=agent_id
            )
            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)
            
        return session
    
    async def add_turn(self, session_id: str, role: str, message: str, intent: Optional[str] = None) -> ConversationTurn:
        stmt = select(ConversationSession).where(ConversationSession.id == session_id)
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            raise ValueError(f"Session {session_id} not found")
            
        turn_index = session.turn_count
        
        turn = ConversationTurn(
            session_id=session_id,
            role=role,
            message=message,
            intent=intent,
            turn_index=turn_index
        )
        
        session.turn_count += 1
        session.last_active_at = utc_now()
        
        self.db.add(turn)
        await self.db.commit()
        await self.db.refresh(turn)
        return turn
    
    async def get_history(self, session_id: str, limit: int = 10) -> List[ConversationTurn]:
        stmt = select(ConversationTurn).where(
            ConversationTurn.session_id == session_id
        ).order_by(ConversationTurn.turn_index.desc()).limit(limit)
        
        result = await self.db.execute(stmt)
        turns = result.scalars().all()
        return list(reversed(turns))
    
    async def format_history_for_prompt(self, session_id: str, limit: int = 5) -> str:
        turns = await self.get_history(session_id, limit)
        formatted = []
        for turn in turns:
            role_name = "Customer" if turn.role == 'customer' else "Agent"
            formatted.append(f"{role_name}: {turn.message}")
        return "\n".join(formatted)
    
    async def close_session(self, session_id: str):
        stmt = update(ConversationSession).where(
            ConversationSession.id == session_id
        ).values(is_active=False)
        
        await self.db.execute(stmt)
        await self.db.commit()
