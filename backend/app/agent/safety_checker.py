"""
Stage 5: Safety and Policy Checker.
Performs deterministic and policy compliance checks on AI draft responses:
- Validates URLs against Apple whitelist (prevents hallucinations)
- Blocks unauthorized guarantees or refunds
- Blocks medical / legal advisory statements
- Enforces character counts and brand voice guardrails
"""

import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import yaml
from pydantic import BaseModel, Field

from app.data.loaders.safety_loader import SafetyLoader

logger = logging.getLogger(__name__)

DEFAULT_APPROVED_DOMAINS = [
    "apple.com",
    "support.apple.com",
    "iforgot.apple.com",
    "reportaproblem.apple.com",
    "checkcoverage.apple.com",
    "locate.apple.com",
    "getsupport.apple.com",
]

DEFAULT_PROMISES = [
    "guarantee",
    "we promise",
    "100% free",
    "full refund guaranteed",
    "replace your device for free",
    "instant refund",
    "promise this will fix",
]


class SafetyResult(BaseModel):
    passed: bool = Field(..., description="True if no safety violations detected")
    flags: List[str] = Field(default_factory=list, description="List of detected policy violations or warnings")


class SafetyChecker:
    """Evaluates draft responses against brand safety rules and hallucination guardrails."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path:
            path = Path(config_path)
        else:
            path = Path(__file__).resolve().parent.parent / "config" / "safety_keywords.yaml"

        self.rules: Dict[str, Any] = {}
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.rules = yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning(f"Could not load safety_keywords.yaml ({e}), using default rules.")

        # Load approved domains dynamically from SafetyLoader whitelist
        self.safety_loader = SafetyLoader()
        domains = set(self.rules.get("approved_domains", DEFAULT_APPROVED_DOMAINS))
        try:
            domains.update(self.safety_loader.load_approved_urls())
        except Exception as e:
            logger.warning(f"Error loading approved URLs from safety_loader: {e}")
        self.approved_domains = list(domains)

        self.unauthorized_promises = self.rules.get("unauthorized_promises", DEFAULT_PROMISES)
        self.medical_terms = self.rules.get("medical_terms", ["diagnosis", "medical condition", "prescribe"])
        self.discouraged_phrases = self.rules.get("discouraged_phrases", ["sorry for the inconvenience", "user error"])

    def check(self, draft_text: str, original_message: str = "", response_type: str = "tweet") -> SafetyResult:
        """
        Run deterministic safety and compliance checks.
        Returns a SafetyResult object.
        """
        flags: List[str] = []
        text_lower = draft_text.lower()

        # 1. URL Hallucination Check
        urls = re.findall(r"https?://[^\s<>\"'{}|\\^`]+", draft_text)
        for url in urls:
            parsed = urlparse(url)
            netloc = parsed.netloc.lower()
            # Strip port or leading www.
            clean_host = re.sub(r"^www\.", "", netloc).split(":")[0]
            
            is_approved = any(
                clean_host == domain or clean_host.endswith("." + domain)
                for domain in self.approved_domains
            )
            if not is_approved:
                flags.append(f"Unapproved/hallucinated URL detected: {url}")

        # 2. Unauthorized Promises Check
        for promise in self.unauthorized_promises:
            if promise.lower() in text_lower:
                flags.append(f"Unauthorized promise detected: '{promise}'")

        # 3. Medical / Legal Terminology Check
        for term in self.medical_terms:
            if term.lower() in text_lower:
                flags.append(f"Medical advice term detected: '{term}'")

        # 4. Discouraged Robot / Blaming Phrases
        for phrase in self.discouraged_phrases:
            if phrase.lower() in text_lower:
                flags.append(f"Discouraged/canned phrase detected: '{phrase}'")

        # 5. Character length check
        max_tweet = self.rules.get("brand_voice", {}).get("max_tweet_chars", 469)
        max_dm = self.rules.get("brand_voice", {}).get("max_dm_chars", 500)
        max_len = max_tweet if response_type == "tweet" else max_dm
        if len(draft_text) > max_len:
            flags.append(f"Response length ({len(draft_text)} chars) exceeds maximum {max_len} limit for {response_type}")

        passed = len(flags) == 0
        return SafetyResult(passed=passed, flags=flags)

