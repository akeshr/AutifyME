"""
Creative Specialist - Domain expert for media and visual operations.

Domain Ownership ("How We Present"):
- Image Processing: analyze, edit, generate, extract, enhance
- Multi-product handling: detect variants, isolate products
- Visual optimization: backgrounds, lighting, framing, upscaling

Architecture:
- SubAgent spec dict for PM delegation
- Owns image_studio tool (Gemini 3 Pro Image)
- Returns processed images for other specialists to use
- Does NOT create database records (Catalog Specialist owns that)
"""

from typing import Any

from langchain.chat_models import BaseChatModel

from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.tools.image_studio import create_image_studio_tool


def create_creative_specialist(
    model: str | BaseChatModel | None = None,
) -> dict[str, Any]:
    """Create Creative Specialist SubAgent spec.

    Args:
        model: Optional LLM (string or instance). None uses PM's default.

    Returns:
        SubAgent spec dict: {name, description, tools, system_prompt, model}
    """
    system_prompt = load_prompt("specialists/creative_specialist.prompt")

    tools: list[Any] = [
        create_image_studio_tool(),
    ]

    description = (
        "Creative Specialist - domain expert for media and visual operations. "
        "Handles: image analysis, multi-product detection, variant extraction, "
        "background removal/replacement, enhancement, lifestyle generation. "
        "Capabilities: analyze group photos (detect 2+ products), extract individual "
        "products, optimize images, generate scenes. Returns processed image paths. "
        "Does NOT handle: database operations, product records, pricing."
    )

    spec: dict[str, Any] = {
        "name": "creative_specialist",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
        "interrupt_on": {},  # No HITL - read-only operations
    }

    if model is not None:
        spec["model"] = model

    return spec
