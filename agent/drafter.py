import json
import logging
import time
from typing import List, Dict, Any
from openai import OpenAI
from openai import APIError, RateLimitError, APIConnectionError

from config import MODEL_NAME, BRAND, OPENAI_API_KEY

logger = logging.getLogger(__name__)

class ReplyDrafter:
    """
    Drafts replies to customer messages using an LLM, given context and intent.
    """

    def __init__(self, model: str = None):
        """
        Initializes the ReplyDrafter.
        
        Args:
            model: The name of the OpenAI model to use.
        """
        self.model = model or MODEL_NAME
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def draft_reply(self, customer_message: str, intent: str, similar_threads: List[Dict[str, Any]], brand: str = None) -> Dict[str, Any]:
        """
        Drafts a reply using the OpenAI API.
        
        Args:
            customer_message: The inbound customer message.
            intent: The classified intent of the message.
            similar_threads: A list of similar historical threads for context.
            brand: The brand name to assume the persona of.
            
        Returns:
            A dictionary containing the draft reply, confidence score, and reasoning.
        """
        brand_name = brand or BRAND
        
        context_strs = []
        for i, thread in enumerate(similar_threads, 1):
            cust_msg = thread.get('first_customer_message', '')
            brand_reply = thread.get('brand_reply', '')
            context_strs.append(f"Example {i}:\nCustomer: {cust_msg}\nBrand: {brand_reply}")
            
        context_block = "\n\n".join(context_strs)
        
        system_prompt = f"""You are the official customer support agent for {brand_name} on Twitter.
Your task is to draft a helpful, professional, and brand-aligned reply to a customer message.

Guidelines:
1. Match the brand's tone and style based on the provided historical examples.
2. The detected customer intent is: '{intent}'.
3. Provide actionable next steps or clear information.
4. DO NOT make up factual information (links, phone numbers, policies) that is not supported by the historical examples or general knowledge about the brand. If unsure, offer to look into it or ask them to DM for details.
5. Provide a confidence score (0.0 to 1.0) on how well-grounded and accurate your drafted reply is.
6. Provide a brief reasoning for your drafted reply.

Context (Historical Examples):
{context_block}

You must respond in the following JSON format ONLY:
{{
    "reply": "The actual drafted reply text",
    "confidence": 0.95,
    "reasoning": "Brief explanation of why this reply was chosen based on intent and context"
}}
"""

        user_prompt = f"Customer Message: {customer_message}"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.3
                )
                
                result_json = response.choices[0].message.content
                result = json.loads(result_json)
                
                return {
                    "reply": result.get("reply", ""),
                    "confidence": float(result.get("confidence", 0.0)),
                    "reasoning": result.get("reasoning", "")
                }
                
            except (APIError, RateLimitError, APIConnectionError) as e:
                logger.warning(f"OpenAI API error on attempt {attempt + 1}/{max_retries}: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                break
            except Exception as e:
                logger.error(f"Unexpected error during draft generation: {e}")
                break
                
        return {
            "reply": "I'm sorry, but I'm unable to draft a reply at this moment.",
            "confidence": 0.0,
            "reasoning": "Failed to generate reply due to errors."
        }
