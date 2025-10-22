"""Image Analysis Tool - Vision API wrapper for product image analysis.

Deterministic tool that calls OpenAI Vision API to extract visual attributes
from product images. Returns structured ImageAnalysisResult.

2-Level Architecture: Tool (not specialist) - deterministic API call
"""

import base64
from pathlib import Path
from typing import Annotated

from langchain_core.tools import tool
from pydantic import Field

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.schemas.agent_outputs import ImageAnalysisResult


def _encode_image_to_base64_uri(image_path: str) -> str:
    """Convert local image file to base64 data URI for vision models.

    Args:
        image_path: Path to local image file

    Returns:
        Base64 data URI (e.g., "data:image/jpeg;base64,...")

    Raises:
        FileNotFoundError: If image file doesn't exist
    """
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # Determine MIME type from extension
    ext = path.suffix.lower()
    mime_type = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
    }.get(ext, 'image/jpeg')

    with open(path, 'rb') as f:
        image_bytes = f.read()

    encoded = base64.b64encode(image_bytes).decode('utf-8')
    return f"data:{mime_type};base64,{encoded}"


@tool
def image_analysis_tool(
    image_path: Annotated[
        str,
        Field(description="File path to product image (e.g., '/tmp/media_downloads/product.jpg')")
    ],
) -> ImageAnalysisResult:
    """Analyze product image to extract visual attributes using Vision API.

    Extracts colors, materials, style tags, dimensions, and generates detailed
    visual description. Uses OpenAI Vision model for multimodal analysis.

    Args:
        image_path: Path to image file on local filesystem

    Returns:
        ImageAnalysisResult with visual description, colors, materials, style, etc.

    Example:
        >>> result = image_analysis_tool("/tmp/product.jpg")
        >>> print(result.visual_description)
        "Blue leather sneakers with white sole..."
        >>> print(result.identified_colors)
        ["blue", "white"]
    """
    # Get vision-capable LLM
    llm = get_llm(provider="openai", model="gpt-4.1-mini")

    # Convert image to base64 data URI
    image_uri = _encode_image_to_base64_uri(image_path)

    # Vision API prompt
    content = """Analyze this product image and extract all visual attributes.

Focus on:
- Visual description (detailed, specific)
- Colors (all visible colors)
- Materials (fabric, leather, metal, etc.)
- Style tags (modern, vintage, casual, formal, etc.)
- Estimated dimensions or size indicators
- Condition and quality indicators
- Any visible brand elements or logos

Be specific and objective. Describe what you actually see."""

    # Build vision message
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": content},
                {"type": "image_url", "image_url": {"url": image_uri}},
            ],
        }
    ]

    # Call Vision API with structured output
    result = llm.with_structured_output(ImageAnalysisResult).invoke(messages)

    return result
