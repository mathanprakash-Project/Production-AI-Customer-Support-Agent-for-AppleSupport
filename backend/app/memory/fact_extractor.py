import re
import json
import logging
from typing import List, Dict, Optional
try:
    from app.llm.base import LLMProvider
except ImportError:
    LLMProvider = None

logger = logging.getLogger(__name__)

FACT_CATEGORIES = [
    'device_info', 'os_version', 'past_issues', 'account_info', 
    'preferences', 'purchase_history', 'contact_history', 'location', 
    'warranty_status', 'family_sharing', 'subscription_info', 
    'accessibility_needs', 'language_preference'
]

class FactExtractor:
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider
        
        # Regex patterns for deterministic extraction
        self.patterns = {
            'device_info': [
                r'(?i)\b(iphone\s*\d+\s*(?:pro|max|plus|mini)?)\b',
                r'(?i)\b(ipad\s*(?:pro|air|mini)?\s*\d*)\b',
                r'(?i)\b(macbook\s*(?:pro|air)?\s*\d*)\b',
                r'(?i)\b(apple\s*watch\s*(?:series|se|ultra)?\s*\d*)\b',
                r'(?i)\b(airpods\s*(?:pro|max)?\s*\d*)\b',
                r'(?i)\b(mac\s*(?:mini|pro|studio)?)\b',
                r'(?i)\b(imac)\b'
            ],
            'os_version': [
                r'(?i)\b(ios\s*\d+(?:\.\d+)*)\b',
                r'(?i)\b(ipados\s*\d+(?:\.\d+)*)\b',
                r'(?i)\b(macos\s*(?:sonoma|ventura|monterey|big\s*sur|catalina|mojave)?(?:\s*\d+(?:\.\d+)*)?)\b',
                r'(?i)\b(watchos\s*\d+(?:\.\d+)*)\b',
                r'(?i)\b(tvos\s*\d+(?:\.\d+)*)\b'
            ],
            'account_info': [
                r'(?i)\b(apple\s*id)\b',
                r'(?i)\b(icloud(?:\s*(?:plus|\+))?)\b',
                r'(?i)\b(apple\s*one)\b',
                r'(?i)\b(apple\s*music)\b',
                r'(?i)\b(apple\s*tv\+?)\b'
            ]
        }
        
    def extract_facts_deterministic(self, message: str) -> List[Dict[str, str]]:
        facts = []
        
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, message)
                for match in matches:
                    fact = match.group(1).strip()
                    if fact:
                        facts.append({
                            'category': category,
                            'fact': fact
                        })
                        
        # Deduplicate
        unique_facts = []
        seen = set()
        for f in facts:
            key = f"{f['category']}:{f['fact'].lower()}"
            if key not in seen:
                seen.add(key)
                unique_facts.append(f)
                
        return unique_facts
        
    async def extract_facts_llm(self, message: str, conversation_history: str = '') -> List[Dict[str, str]]:
        if not self.provider:
            return self.extract_facts_deterministic(message)
            
        prompt = f"""Extract relevant facts about the user from their message.
Use these categories: {', '.join(FACT_CATEGORIES)}
Message: {message}
History: {conversation_history}

Output ONLY valid JSON in this format:
[
  {{"category": "device_info", "fact": "iPhone 15 Pro"}}
]
If no facts are found, output []."""

        try:
            # Assuming provider has a generate_text or similar method
            if hasattr(self.provider, 'generate_text'):
                response = await self.provider.generate_text(prompt)
            else:
                return self.extract_facts_deterministic(message)
                
            # Parse JSON
            match = re.search(r'\[.*\]', response, re.DOTALL)
            if match:
                facts = json.loads(match.group(0))
                # Validate categories
                return [f for f in facts if f.get('category') in FACT_CATEGORIES and f.get('fact')]
            return self.extract_facts_deterministic(message)
            
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return self.extract_facts_deterministic(message)
