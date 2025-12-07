"""Product Analyst - External product knowledge research specialist.

Read-only analyst that researches detailed product knowledge from external sources.
Answers "What IS this product?" - proper naming, specifications, classifications.

Cross-domain reuse:
- Catalog: HSN codes, specifications, proper naming
- Marketing: Product positioning, usage context
- Quality: Standards compliance, material specifications
- Procurement: Industry classifications, sourcing context
"""

from typing import Any

from langchain.chat_models import BaseChatModel

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.tools.research_tools import (
    extract_web_content_tool,
    research_product_tool,
)


def _get_analyst_llm() -> BaseChatModel:
    """Get fast, cheap LLM for analyst tasks.

    Uses Gemini 2.5 Flash with minimal thinking for speed.
    Analysts are latency-sensitive (target <300ms).
    """
    return get_llm(
        provider="google",
        model="gemini-2.5-flash",
        temperature=0.3,  # Lower temperature for factual research
        max_retries=3,
    )


def create_product_analyst(
    model: BaseChatModel | None = None,
) -> dict[str, Any]:
    """Create Product Analyst SubAgent spec.

    Args:
        model: Optional LLM override. Defaults to Gemini 2.5 Flash.

    Returns:
        SubAgent spec dict for PM's subagents list.

    Example:
        >>> analyst = create_product_analyst()
        >>> # Add to PM subagents
        >>> subagents = [visual_analyst, analyst, ...]
    """
    system_prompt = load_prompt("analysts/product_analyst.prompt")

    description = (
        "Product Analyst - researches external product knowledge. "
        "Reports: proper industry naming, specifications, HSN codes, standards, usage context. "
        "Cross-domain reuse: serves catalog, marketing, quality, procurement workflows. "
        "Read-only - does NOT suggest actions or make recommendations."
    )

    tools: list[Any] = [
        research_product_tool,
        extract_web_content_tool,
    ]

    spec: dict[str, Any] = {
        "name": "product_analyst",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
        # No interrupt_on - analysts are read-only
    }

    if model is not None:
        spec["model"] = model
    else:
        spec["model"] = _get_analyst_llm()

    return spec
