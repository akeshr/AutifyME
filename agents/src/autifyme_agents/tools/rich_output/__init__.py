"""Rich Output Engine - Generate branded HTML pages from structured data.

Enables agents to present complex data visually instead of text walls.
LLM-powered HTML generation with client company branding.
"""

from autifyme_agents.tools.rich_output.schemas import (
    FieldHint,
    RichOutputInput,
    RichOutputResult,
)
from autifyme_agents.tools.rich_output.tool import create_rich_output_tool

__all__ = [
    "FieldHint",
    "RichOutputInput",
    "RichOutputResult",
    "create_rich_output_tool",
]
