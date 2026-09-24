from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.memory.session_memory import SessionMemoryService
from app.memory.user_memory import UserMemoryService
from app.memory.context_memory import ContextMemoryService
from app.memory.fact_extractor import FactExtractor

try:
    from app.llm.base import LLMProvider
except ImportError:
    LLMProvider = None

logger = logging.getLogger(__name__)

class MemoryManager:
    def __init__(self, db: AsyncSession, provider: Optional[LLMProvider] = None):
        self.session_memory = SessionMemoryService(db)
        self.user_memory = UserMemoryService(db)
        self.context_memory = ContextMemoryService(db)
        self.fact_extractor = FactExtractor(provider)
        
    async def process_customer_message(self, user_identifier: str, message: str, ticket_id: Optional[str] = None, agent_id: Optional[str] = None) -> Dict:
        # 1. Get or create session
        session = await self.session_memory.get_or_create_session(user_identifier, ticket_id, agent_id)
        
        # 2. Add customer turn to session
        await self.session_memory.add_turn(session.id, 'customer', message)
        
        # 3. Extract facts
        history = await self.session_memory.format_history_for_prompt(session.id, limit=3)
        extracted_facts = await self.fact_extractor.extract_facts_llm(message, history)
        
        # 4. Store extracted facts in user memory
        stored_facts = []
        for fact in extracted_facts:
            try:
                stored_fact = await self.user_memory.store_fact(
                    user_identifier=user_identifier,
                    category=fact['category'],
                    fact_text=fact['fact'],
                    session_id=session.id
                )
                stored_facts.append(stored_fact)
            except Exception as e:
                logger.error(f"Failed to store fact: {e}")
                
        # 5. Recall relevant user facts
        user_profile = await self.user_memory.get_user_profile_summary(user_identifier)
        
        # 6. Format conversation history
        conversation_history = await self.session_memory.format_history_for_prompt(session.id)
        
        return {
            'session_id': session.id,
            'conversation_history': conversation_history,
            'user_profile': user_profile,
            'extracted_facts': extracted_facts
        }
        
    async def record_agent_response(self, session_id: str, response: str):
        # Add agent turn to session history
        await self.session_memory.add_turn(session_id, 'agent', response)
        
    async def get_full_context(self, session_id: str, user_identifier: str, query: Optional[str] = None) -> Dict:
        conversation_history = await self.session_memory.format_history_for_prompt(session_id)
        user_profile = await self.user_memory.get_user_profile_summary(user_identifier)
        context_data = await self.context_memory.get_all(session_id)
        
        return {
            'conversation_history': conversation_history,
            'user_profile': user_profile,
            'context_data': context_data
        }
        
    async def store_pipeline_context(self, session_id: str, key: str, value: dict):
        await self.context_memory.store(session_id, key, value)
