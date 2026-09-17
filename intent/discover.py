import json
import random
import logging
from pathlib import Path
from typing import List, Dict, Any
from pydantic import BaseModel

import openai
from openai import OpenAI
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from config import OPENAI_API_KEY, PROJECT_ROOT, MODEL_NAME

logger = logging.getLogger(__name__)

client = OpenAI(api_key=OPENAI_API_KEY)


@retry(
    wait=wait_exponential(multiplier=1, min=4, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(openai.RateLimitError)
)
def _call_openai_json(messages: List[Dict[str, str]], model: str) -> Dict[str, Any]:
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.0
    )
    return json.loads(response.choices[0].message.content)

def discover_intents(messages: List[str], model: str = 'gpt-4o-mini', n_sample: int = 500, target_intents: int = 12) -> Dict[str, Any]:
    """
    Discover intents from a list of customer messages.
    """
    logger.info(f"Starting intent discovery with {len(messages)} messages, targeting {target_intents} intents.")
    
    # 1. Sample messages
    if len(messages) > n_sample:
        sampled_messages = random.sample(messages, n_sample)
    else:
        sampled_messages = messages
        
    # 2. First pass: Identify themes in batches
    batch_size = 50
    all_themes = []
    
    logger.info("Pass 1: Identifying themes in batches.")
    for i in range(0, len(sampled_messages), batch_size):
        batch = sampled_messages[i:i + batch_size]
        batch_text = "\n".join([f"- {msg}" for msg in batch])
        prompt = (
            "Analyze the following customer support messages and identify recurring themes or issues. "
            "Return a JSON object with a single key 'themes' containing a list of strings describing the themes.\n\n"
            f"Messages:\n{batch_text}"
        )
        try:
            res = _call_openai_json([
                {"role": "system", "content": "You are a helpful assistant analyzing customer support themes."},
                {"role": "user", "content": prompt}
            ], model)
            if "themes" in res:
                all_themes.extend(res["themes"])
        except Exception as e:
            logger.error(f"Error in batch {i}: {e}")
            
    # 3. Second pass: Consolidate themes
    logger.info(f"Pass 2: Consolidating {len(all_themes)} themes into {target_intents} distinct intents.")
    themes_text = "\n".join([f"- {t}" for t in all_themes])
    prompt = (
        f"Here are themes identified from customer support messages:\n{themes_text}\n\n"
        f"Consolidate these themes into exactly {target_intents} distinct intents. "
        "Return a JSON object with a key 'intents' containing a list of intent names."
    )
    
    try:
        res = _call_openai_json([
            {"role": "system", "content": "You are a customer support analyst organizing themes."},
            {"role": "user", "content": prompt}
        ], model)
        consolidated_intents = res.get("intents", [])[:target_intents]
    except Exception as e:
        logger.error(f"Error in Pass 2: {e}")
        consolidated_intents = []
    
    # 4. Third pass: Generate descriptions, examples, keywords
    logger.info("Pass 3: Generating descriptions, examples, and keywords for each intent.")
    taxonomy = {}
    
    if consolidated_intents:
        intent_names_text = "\n".join([f"- {i}" for i in consolidated_intents])
        prompt = (
            f"We have the following consolidated intents for customer support:\n{intent_names_text}\n\n"
            "For each intent, provide a clear description, 3-5 example messages, and a list of keywords. "
            "Return a JSON object where each key is the intent name, and the value is an object containing "
            "'description', 'examples', and 'keywords' as keys."
        )
        
        try:
            res = _call_openai_json([
                {"role": "system", "content": "You are an expert customer support taxonomist. Return only a JSON object structured exactly as requested."},
                {"role": "user", "content": prompt}
            ], model)
            taxonomy = res
        except Exception as e:
            logger.error(f"Error in Pass 3: {e}")
    
    # Save taxonomy
    out_dir = PROJECT_ROOT / "intent"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "taxonomy.json"
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(taxonomy, f, indent=4, ensure_ascii=False)
        
    logger.info(f"Saved taxonomy to {out_path}")
    return taxonomy

def load_taxonomy(path: str = 'intent/taxonomy.json') -> Dict[str, Any]:
    """Load saved taxonomy."""
    full_path = PROJECT_ROOT / path if not Path(path).is_absolute() else Path(path)
    if not full_path.exists():
        logger.warning(f"Taxonomy file not found at {full_path}")
        return {}
    with open(full_path, "r", encoding="utf-8") as f:
        return json.load(f)
