"""
Creative Specialist - Professional product photographer and image editor.

Domain Ownership ("How We Present"):
- Studio-quality image processing for e-commerce
- Multi-product extraction with professional isolation
- Marketplace-ready hero shots (Amazon, Shopify, Instagram quality)
- Lifestyle and contextual scene generation

Architecture:
- SubAgent spec dict for PM delegation
- Owns image_studio tool (Gemini 3 Pro Image)
- Uses MultimodalInjectionMiddleware to SEE images in delegation messages
- Returns studio-grade processed images for catalog creation
- Does NOT create database records (Catalog Specialist owns that)

Professional Standards:
- Pure white backgrounds for hero shots
- Studio lighting with proper shadows
- Color-accurate, sharpened, enhanced output
- 70-85% product coverage, centered composition
"""

from typing import Any

from langchain.chat_models import BaseChatModel

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.middleware import MultimodalInjectionMiddleware
from autifyme_agents.tools import create_view_image_tool
from autifyme_agents.tools.image_studio import create_image_studio_tool

# Creative Specialist uses Gemini 3 Pro for multimodal reasoning (can see images)
CREATIVE_SPECIALIST_MODEL = "gemini-3-pro-preview"


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
        create_view_image_tool(),  # Quick inspection without processing
        create_image_studio_tool(),  # Professional image processing
    ]

    description = (
        "Creative Specialist - professional product photographer creating studio-quality images. "
        "Produces: marketplace-ready hero shots (pure white background, studio lighting, color-accurate), "
        "multi-product extraction with clean isolation, lifestyle shots with contextual scenes. "
        "Standards: 70-85% product coverage, proper framing, enhancement suite (sharpness, color correction, denoise). "
        "Include image paths in task - specialist SEES and diagnoses images like a professional photographer. "
        "Returns: processed image paths with professional assessment. "
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
