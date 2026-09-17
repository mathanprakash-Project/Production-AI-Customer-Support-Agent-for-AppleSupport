"""
Prompt Registry and Template Manager using Jinja2.
Provides versioned prompt templates for classification, drafting, and judging.
"""

from pathlib import Path
from typing import Any, Dict
from jinja2 import Environment, FileSystemLoader, select_autoescape

PROMPTS_DIR = Path(__file__).resolve().parent


class PromptRegistry:
    """Manages versioned Jinja2 prompt templates."""

    def __init__(self, template_dir: Path = PROMPTS_DIR):
        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_name: str, version: str = "v1", **kwargs: Any) -> str:
        """
        Render a versioned prompt template.
        Example: registry.render("classifier", "v1", customer_message="...", taxonomy=[...])
        """
        filename = f"{template_name}_{version}.jinja"
        template = self.env.get_template(filename)
        return template.render(**kwargs).strip()


# Global prompt registry instance
prompt_registry = PromptRegistry()

