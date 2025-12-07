"""Visual Analyst - Image observation and analysis specialist.

Read-only analyst that observes images and returns detailed findings.
Does NOT suggest actions or make recommendations - purely observational.

Cross-domain reuse:
- Catalog: Material identification, condition assessment
- Marketing: Visual quality, composition analysis
- Operations: Damage detection, quality control
- Quality: Defect identification, compliance checking
"""

from typing import Any

from langchain.chat_models import BaseChatModel

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.tools import create_view_image_tool


def _get_analyst_llm() -> BaseChatModel:
    """Get fast, cheap LLM for analyst tasks.

    Uses Gemini 2.5 Flash with minimal thinking for speed.
    Analysts are latency-sensitive (target <300ms).
    """
    return get_llm(
        provider="google",
        model="gemini-2.5-flash",
        temperature=0.3,  # Lower temperature for consistent observations
        max_retries=3,
    )


def create_visual_analyst(
    model: BaseChatModel | None = None,
) -> dict[str, Any]:
    """Create Visual Analyst SubAgent spec.

    Args:
        model: Optional LLM override. Defaults to Gemini 2.5 Flash.

    Returns:
        SubAgent spec dict for PM's subagents list.

    Example:
        >>> analyst = create_visual_analyst()
        >>> # Add to PM subagents
        >>> subagents = [analyst, catalog_specialist, ...]
    """
    system_prompt = load_prompt("analysts/visual_analyst.prompt")

    description = (
        "Visual Analyst - observes images and returns detailed findings. "
        "Reports: materials, style/era, condition, dimensions, quality indicators. "
        "Cross-domain reuse: serves catalog, marketing, operations, quality workflows. "
        "Read-only - does NOT suggest actions or make recommendations."
    )

    tools: list[Any] = [
        create_view_image_tool(),
    ]

    spec: dict[str, Any] = {
        "name": "visual_analyst",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
        # FilesystemMiddleware (write_file, read_file) is provided by default via DeepAgents
        # No interrupt_on - analysts are read-only
    }

    if model is not None:
        spec["model"] = model
    else:
        spec["model"] = _get_analyst_llm()

    return spec
