"""
Structured output enforcement with automatic single-turn repair.
Handles JSON parsing, schema validation, and fallback handling.
"""

import json
import logging
import re
from typing import Any, Callable, Dict, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def clean_json_text(text: str) -> str:
    """Extract and sanitize JSON string from possible markdown code fences."""
    text = text.strip()
    # Match ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    else:
        # Match from first '{' to last '}'
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]
    return text


async def parse_and_validate_structured(
    text: str,
    schema: Type[T],
    repair_func: Optional[Callable[[str, str], Any]] = None,
    safe_default: Optional[T] = None,
) -> T:
    """
    Parses JSON from model output and validates with Pydantic.
    If parsing/validation fails and repair_func is provided, attempts one repair.
    If repair fails, returns safe_default if given, else raises ValidationError.
    """
    cleaned = clean_json_text(text)
    try:
        data = json.loads(cleaned)
        return schema.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as initial_err:
        logger.warning(f"Structured output validation failed: {initial_err}. Initiating repair...")
        
        if repair_func is not None:
            repair_prompt = (
                f"The following JSON response was malformed or failed validation against the schema:\n\n"
                f"--- Malformed Output ---\n{text}\n\n"
                f"--- Error Details ---\n{str(initial_err)}\n\n"
                f"--- Target Schema ---\n{json.dumps(schema.model_json_schema(), indent=2)}\n\n"
                f"Fix the JSON so it is strictly valid JSON matching the exact schema. Return ONLY valid JSON, no explanations."
            )
            try:
                repaired_text = await repair_func(repair_prompt)
                cleaned_repaired = clean_json_text(repaired_text)
                repaired_data = json.loads(cleaned_repaired)
                return schema.model_validate(repaired_data)
            except Exception as repair_err:
                logger.error(f"Structured output repair failed: {repair_err}")

        if safe_default is not None:
            logger.warning("Returning configured safe default for structured output.")
            return safe_default

        raise initial_err

