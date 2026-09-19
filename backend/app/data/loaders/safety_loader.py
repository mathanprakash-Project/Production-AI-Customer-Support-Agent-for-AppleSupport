"""
Safety Dataset Loader

Provides utilities for:
1. URL safety verification against Apple's approved domain whitelist.
2. Loading safe & unsafe drafts for evaluating safety classifiers.
3. Loading tone pairs and formatting them for drafting prompts.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

DATA_DIR_DEFAULT = Path(__file__).resolve().parent.parent / "safety"


class SafetyLoader:
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR_DEFAULT
        self._approved_domains: Optional[Set[str]] = None
        self._tone_examples: Optional[List[Dict]] = None
        self._safe_drafts: Optional[List[Dict]] = None
        self._unsafe_drafts: Optional[List[Dict]] = None

    def load_approved_urls(self) -> Set[str]:
        """Loads whitelist of approved Apple domains and URL prefixes."""
        if self._approved_domains is not None:
            return self._approved_domains

        fpath = self.data_dir / "approved_apple_urls.txt"
        domains = set()
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f:
                for line in f:
                    clean = line.strip().lower()
                    if clean and not clean.startswith("#"):
                        domains.add(clean)
        else:
            # Sensible fallback
            domains = {
                "apple.com", "support.apple.com", "iforgot.apple.com",
                "appleid.apple.com", "icloud.com", "discussions.apple.com",
                "getsupport.apple.com", "locate.apple.com", "reportaproblem.apple.com",
                "checkcoverage.apple.com"
            }
        self._approved_domains = domains
        return self._approved_domains

    def extract_urls(self, text: str) -> List[str]:
        """Finds all HTTP/HTTPS and www URLs in text."""
        pattern = r"(?:https?://|www\.)[^\s<>\"'{}|\\^`]+"
        return re.findall(pattern, text)

    def is_approved_url(self, url: str) -> bool:
        """
        Validates if a URL belongs to the approved Apple domains whitelist.
        Guards against phishing or hallucinated domains (e.g. apple-support-login.com).
        """
        approved = self.load_approved_urls()
        
        # Ensure url has scheme for urlparse
        test_url = url if url.startswith(("http://", "https://")) else "https://" + url
        try:
            parsed = urlparse(test_url)
            host = parsed.netloc.lower()
            clean_host = re.sub(r"^www\.", "", host).split(":")[0]

            return any(
                clean_host == domain or clean_host.endswith("." + domain)
                for domain in approved
            )
        except Exception:
            return False

    def check_urls_safe(self, text: str) -> Tuple[bool, List[str]]:
        """
        Checks all URLs in the provided text.
        Returns:
            (is_safe: bool, unapproved_urls: List[str])
        """
        urls = self.extract_urls(text)
        unapproved = [u for u in urls if not self.is_approved_url(u)]
        return (len(unapproved) == 0, unapproved)

    def load_tone_examples(self) -> List[Dict]:
        """Loads tone pair examples (bad vs good tone)."""
        if self._tone_examples is None:
            fpath = self.data_dir / "tone_examples.json"
            if fpath.exists():
                with open(fpath, "r", encoding="utf-8") as f:
                    self._tone_examples = json.load(f)
            else:
                self._tone_examples = []
        return self._tone_examples

    def format_tone_rules_for_prompt(self, limit: int = 5) -> str:
        """Formats bad vs good tone pairs for inclusion in drafting prompts."""
        examples = self.load_tone_examples()[:limit]
        if not examples:
            return ""

        lines = ["Brand Tone & Empathy Guidelines:"]
        for i, ex in enumerate(examples, 1):
            lines.append(f"{i}. Avoid: \"{ex.get('bad')}\"")
            lines.append(f"   Prefer: \"{ex.get('good')}\"")
        return "\n".join(lines)

    def load_test_drafts(
        self,
        safe_only: bool = False,
        unsafe_only: bool = False,
    ) -> List[Dict]:
        """Loads test drafts for benchmark testing safety checkers."""
        results = []
        if not unsafe_only:
            if self._safe_drafts is None:
                fpath = self.data_dir / "safe_drafts.json"
                if fpath.exists():
                    with open(fpath, "r", encoding="utf-8") as f:
                        self._safe_drafts = json.load(f)
                else:
                    self._safe_drafts = []
            results.extend(self._safe_drafts)

        if not safe_only:
            if self._unsafe_drafts is None:
                fpath = self.data_dir / "unsafe_drafts.json"
                if fpath.exists():
                    with open(fpath, "r", encoding="utf-8") as f:
                        self._unsafe_drafts = json.load(f)
                else:
                    self._unsafe_drafts = []
            results.extend(self._unsafe_drafts)

        return results

