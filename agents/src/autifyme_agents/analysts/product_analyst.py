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
from autifyme_agents.middleware import MultimodalInjectionMiddleware
from autifyme_agents.tools import create_view_image_tool
from autifyme_agents.tools.research_tools import (
    extract_web_content_tool,
    research_product_tool,
)


def _get_analyst_llm() -> BaseChatModel:
    """Get fast, cheap LLM for analyst tasks.

    Uses Gemini 2.5 Flash Lite with minimal thinking for speed.
    Analysts are latency-sensitive (target <300ms).
    """
    return get_llm(
        provider="google",
        model="gemini-2.5-flash-lite",
        temperature=0.5,  # Lower temperature for factual research
        max_retries=3,
    )


def create_product_analyst(
    model: BaseChatModel | None = None,
) -> dict[str, Any]:
    """Create Product Analyst SubAgent spec.

    Args:
        model: Optional LLM override. Defaults to Gemini 2.5 Flash Lite.

    Returns:
        SubAgent spec dict for PM's subagents list.

    Example:
        >>> analyst = create_product_analyst()
        >>> # Add to PM subagents
        >>> subagents = [visual_analyst, analyst, ...]
    """
    system_prompt = load_prompt("analysts/product_analyst.prompt")

    description = (
        "ROLE: Analyst (read-only)\n"
        "MISSION: Convert an unknown product into market-grounded facts (name, specs, standards).\n\n"
        "OWNERSHIP:\n"
        "- External product knowledge: naming conventions, spec sheets, standards/compliance context\n"
        "- Web research + source-backed summaries\n\n"
        "INPUTS I NEED:\n"
        "- Product cues: brand/model/keywords OR an image path to infer them\n"
        "- Target market/jurisdiction if compliance matters (e.g., India)\n\n"
        "OUTPUTS I PRODUCE:\n"
        "- A concise, source-backed brief (with links)\n"
        "- Clear unknowns/assumptions and what to confirm before writing data\n"
        "- If long: write a report to the thread directory and return the file path\n\n"
        "TOOLS I USE:\n"
        "- research_product_tool, extract_web_content_tool, view_image\n\n"
        "GUARDRAILS:\n"
        "- No internal DB reads/writes; no record creation; no image editing"
    )

    tools: list[Any] = [
        research_product_tool,
        extract_web_content_tool,
        create_view_image_tool(),  # View images for product analysis
    ]

    # Multimodal middleware injects images from paths in delegation message
    middleware = [MultimodalInjectionMiddleware()]

    spec: dict[str, Any] = {
        "name": "product_analyst",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
        "middleware": middleware,
        # FilesystemMiddleware (write_file, read_file) is provided by default via DeepAgents
        # No interrupt_on - analysts are read-only
    }

    if model is not None:
        spec["model"] = model
    else:
        spec["model"] = _get_analyst_llm()

    return spec
