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
    """Get fast LLM for analyst tasks.

    Uses Gemini 2.0 Flash for speed and reliability.
    Analysts are latency-sensitive (target <300ms).
    """
    return get_llm(
        provider="google",
        model="gemini-2.0-flash",
        temperature=1.0,
        max_retries=3,
    )


def create_product_analyst(
    model: BaseChatModel | None = None,
) -> dict[str, Any]:
    """Create Product Analyst SubAgent spec.

    Args:
        model: Optional LLM override. Defaults to Gemini 2.0 Flash.

    Returns:
        SubAgent spec dict for PM's subagents list.

    Example:
        >>> analyst = create_product_analyst()
        >>> # Add to PM subagents
        >>> subagents = [visual_analyst, analyst, ...]
    """
    system_prompt = load_prompt("analysts/product_analyst.prompt")

    description = (
        "ROLE: Analyst (read-only, external research)\n"
        "MISSION: Comprehensive product research - convert unknown products into catalog-ready specifications.\n\n"
        "OWNERSHIP (ALL external research):\n"
        "- Technical specifications: capacity, dimensions, weight, materials\n"
        "- Certifications & compliance: BPA-free, FSSAI, FDA, CE, ISO standards\n"
        "- Tax classification: HSN/HS codes, GST rates\n"
        "- Industry standards: naming conventions, categorization\n"
        "- Market context: similar products, typical pricing ranges\n"
        "- Web research + source-backed summaries\n\n"
        "INPUTS I NEED:\n"
        "- Product cues: brand/model/keywords OR an image path to infer them\n"
        "- Target market/jurisdiction if compliance matters (e.g., India)\n\n"
        "OUTPUTS I PRODUCE:\n"
        "- Comprehensive research brief: specs, materials, certifications, HSN, market context\n"
        "- Source-backed findings with links\n"
        "- Clear unknowns/assumptions for user to confirm\n"
        "- If long: write product_research_[item].md to thread directory\n\n"
        "TOOLS I USE:\n"
        "- research_product_tool, extract_web_content_tool, view_image\n\n"
        "GUARDRAILS:\n"
        "- No internal DB reads/writes; no record creation; no image editing\n"
        "- catalog_specialist handles CRUD - I provide research findings"
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
