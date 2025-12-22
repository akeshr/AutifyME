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

from typing import TYPE_CHECKING, Any

from langchain.chat_models import BaseChatModel

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.middleware import MultimodalInjectionMiddleware, create_execution_limits
from autifyme_agents.tools import create_view_image_tool
from autifyme_agents.tools.protocol_loader import create_load_protocol_tool

if TYPE_CHECKING:
    from autifyme_agents.schemas.models import CompanyProfile


def _get_analyst_llm() -> BaseChatModel:
    """Get fast, intelligent LLM for analyst tasks.

    Uses Gemini 3 Flash with 'low' thinking for speed + intelligence.
    Analysts are latency-sensitive (target <300ms).
    """
    return get_llm(
        provider="google",
        model="gemini-3-flash-preview",
        thinking_level="low",  # Fast visual analysis
        max_retries=3,
    )


def create_visual_analyst(
    company_profile: "CompanyProfile",
    model: BaseChatModel | None = None,
) -> dict[str, Any]:
    """Create Visual Analyst SubAgent spec.

    Args:
        company_profile: Company context for prompt formatting.
        model: Optional LLM override. Defaults to Gemini 3 Flash.

    Returns:
        SubAgent spec dict for PM's subagents list.

    Example:
        >>> analyst = create_visual_analyst(company_profile)
        >>> # Add to PM subagents
        >>> subagents = [analyst, catalog_specialist, ...]
    """
    if company_profile is None:
        raise ValueError("company_profile is required for Visual Analyst (single-tenant)")

    prompt_template = load_prompt("analysts/visual_analyst_v2.prompt")

    system_prompt = prompt_template.format(
        company_name=company_profile.name,
        industry=company_profile.industry or "Product Manufacturing",
    )

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
    # Execution limits: analysts are read-only with tight limits
    middleware = [
        *create_execution_limits(model_call_limit=50, tool_call_limit=30),
        MultimodalInjectionMiddleware(),
    ]

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
