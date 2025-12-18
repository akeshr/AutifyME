"""Visual Analyst - Image observation and analysis specialist.

Read-only analyst that observes images and returns detailed findings.
Does NOT suggest actions or make recommendations - purely observational.

Cross-domain reuse:
- Catalog: Material identification, condition assessment
- Marketing: Visual quality, composition analysis
- Operations: Damage detection, quality control
- Quality: Defect identification, compliance checking

Protocol Integration (v2):
- Loads domain-specific visual_analysis protocols when domain context provided
- Protocol grounds observations in domain-specific focus areas
"""

from typing import Any

from langchain.chat_models import BaseChatModel

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.middleware import MultimodalInjectionMiddleware
from autifyme_agents.tools import create_view_image_tool
from autifyme_agents.tools.protocol_loader import create_load_protocol_tool


def _get_analyst_llm() -> BaseChatModel:
    """Get fast LLM for analyst tasks.

    Uses Gemini 2.0 Flash for visual analysis.
    Analysts are latency-sensitive (target <300ms).
    """
    return get_llm(
        provider="google",
        model="gemini-2.0-flash",
        temperature=0.7,
        max_retries=3,
    )


def create_visual_analyst(
    model: BaseChatModel | None = None,
) -> dict[str, Any]:
    """Create Visual Analyst SubAgent spec.

    Args:
        model: Optional LLM override. Defaults to Gemini 2.0 Flash.

    Returns:
        SubAgent spec dict for PM's subagents list.

    Example:
        >>> analyst = create_visual_analyst()
        >>> # Add to PM subagents
        >>> subagents = [analyst, catalog_specialist, ...]
    """
    system_prompt = load_prompt("analysts/visual_analyst_v2.prompt")

    description = (
        "ROLE: Analyst (read-only, protocol-integrated)\n"
        "MISSION: Describe what is visible in images with high precision.\n\n"
        "OWNERSHIP:\n"
        "- Visual facts only: items, materials, colors, text/labels, defects, counts\n"
        "- Domain-grounded analysis when domain context provided\n\n"
        "INPUTS I NEED:\n"
        "- Image path(s) when available (e.g., inbox/... or pending/...)\n"
        "- Domain context if applicable (e.g., 'for CATALOG domain')\n\n"
        "OUTPUTS I PRODUCE:\n"
        "- Observations + uncertainties (no recommendations)\n"
        "- Domain-specific focus areas when protocol loaded\n"
        "- If long: write a short report to the thread directory and return the file path\n\n"
        "TOOLS I USE:\n"
        "- load_protocol (for domain-specific analysis)\n"
        "- view_image\n\n"
        "GUARDRAILS:\n"
        "- No DB reads/writes; no pricing/taxonomy/action recommendations; no image editing"
    )

    tools: list[Any] = [
        create_load_protocol_tool(),
        create_view_image_tool(),
    ]

    # Multimodal middleware injects images from paths in delegation message
    # When PM includes image paths in the task description, the middleware
    # loads and injects the images so the analyst's LLM can see them directly
    middleware = [MultimodalInjectionMiddleware()]

    spec: dict[str, Any] = {
        "name": "visual_analyst",
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
