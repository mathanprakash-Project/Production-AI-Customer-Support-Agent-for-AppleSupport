"""
Structured logging configuration with PII scrubbing.
"""

import logging
import re
import sys
from typing import Any, Dict

EMAIL_REGEX = re.compile(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
PHONE_REGEX = re.compile(r"\b(?:\+?1[-. ]?)?\(?[2-9]\d{2}\)?[-. ]?\d{3}[-. ]?\d{4}\b")
CARD_REGEX = re.compile(r"\b(?:\d{4}[- ]?){3}\d{4}\b")


def scrub_pii(text: str) -> str:
    """Scrub sensitive customer PII from log strings."""
    if not isinstance(text, str):
        return text
    text = EMAIL_REGEX.sub(r"[EMAIL_REDACTED]", text)
    text = PHONE_REGEX.sub(r"[PHONE_REDACTED]", text)
    text = CARD_REGEX.sub(r"[CARD_REDACTED]", text)
    return text


class PIIScrubbingFormatter(logging.Formatter):
    """Custom logging formatter that scrubs PII before emitting records."""

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        return scrub_pii(original)


def setup_logging(debug: bool = False):
    """Configure root logger with structured formatting and PII scrubbing."""
    log_level = logging.DEBUG if debug else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    formatter = PIIScrubbingFormatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers = [handler]

