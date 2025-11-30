"""
Creative Specialist - Domain expert for media and visual operations.

Domain Ownership ("How We Present"):
- Image Processing: analyze, edit, generate, extract, enhance
- Multi-product handling: detect variants, isolate products
- Visual optimization: backgrounds, lighting, framing, upscaling

Architecture:
- SubAgent spec dict for PM delegation
- Owns image_studio tool (Gemini 3 Pro Image)
- Uses MultimodalInjectionMiddleware to SEE images in delegation messages
- Returns processed images for other specialists to use
- Does NOT create database records (Catalog Specialist owns that)

Multimodal Vision:
- When PM delegates with image paths, middleware injects actual images
- Specialist's LLM sees images directly (~258 tokens per image)
- No need for separate view_image tool - images are in the message
"""

from typing import Any

from langchain.chat_models import BaseChatModel

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.middleware import MultimodalInjectionMiddleware
from autifyme_agents.tools.image_studio import create_image_studio_tool

# Creative Specialist uses Gemini 3 Pro for multimodal reasoning (can see images)
CREATIVE_SPECIALIST_MODEL = "gemini-3-pro"


def create_creative_specialist(
    model: str | BaseChatModel | None = None,
) -> dict[str, Any]:
    """Create Creative Specialist SubAgent spec.

    The specialist receives images directly via MultimodalInjectionMiddleware.
    When PM includes image paths in the task description, the middleware
    loads and injects the images so the specialist's LLM can see them.

    Args:
        model: Optional LLM override. Defaults to Gemini 3 Pro (multimodal).

    Returns:
        SubAgent spec dict: {name, description, tools, system_prompt, model, middleware}
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
        "NOTE: Include image paths in task description - specialist SEES images directly. "
        "Does NOT handle: database operations, product records, pricing."
    )

    # Use provided model or default to Gemini 3 Pro (multimodal)
    specialist_model = model if model is not None else get_llm(
        provider="google",
        model=CREATIVE_SPECIALIST_MODEL,
    )

    # Multimodal middleware injects images from paths in delegation message
    middleware = [MultimodalInjectionMiddleware()]

    spec: dict[str, Any] = {
        "name": "creative_specialist",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
        "model": specialist_model,
        "middleware": middleware,
        "interrupt_on": {},  # No HITL - read-only operations
    }

    return spec
