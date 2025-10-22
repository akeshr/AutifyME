"""Image Analysis Tool - Vision API wrapper for product image analysis.

Deterministic tool that calls OpenAI Vision API to extract visual attributes
from product images. Returns structured ImageAnalysisResult.

2-Level Architecture: Tool (not specialist) - deterministic API call
"""

import base64
import io
from pathlib import Path
from typing import Annotated

from langchain.tools import tool
from PIL import Image
from pydantic import Field

from autifyme_agents.core.exceptions import ToolExecutionError
from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.schemas.agent_outputs import ImageAnalysisResult

# Vision model optimal dimensions
# Reduced from 2048 to 1024 to minimize token usage (gpt-4.1 uses 32px patches)
# 1024px provides sufficient detail for product cataloging while reducing tokens by ~75%
MAX_DIMENSION = 1024
JPEG_QUALITY = 85

# Vision API detail mode: "low" (512px, 85 tokens) vs "high" (tiled, ~170 tokens/tile)
# For product images, "high" detail is necessary to read text, logos, materials
VISION_DETAIL = "high"

# API timeout (seconds) - vision processing can be slow, especially with high detail mode
API_TIMEOUT = 60.0


def _resize_image_for_vision_api(image_path: str) -> bytes:
    """Resize and compress image for efficient Vision API processing.

    Large images cause massive token usage. This resizes to max 1024px to reduce tokens
    by ~75% while preserving sufficient detail for product cataloging.

    Token calculation (gpt-4.1): ceil(width/32) * ceil(height/32) patches
    - 1024x1024: 32*32 = 1,024 tokens
    - 2048x2048: 64*64 = 4,096 tokens (4x more expensive!)

    Args:
        image_path: Path to source image file

    Returns:
        Optimized image as JPEG bytes (max 1024px, 85% quality)

    Raises:
        FileNotFoundError: If image file doesn't exist
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # Load image
    with Image.open(path) as img:
        # Convert RGBA to RGB (Vision API expects RGB)
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img

        # Resize if exceeds max dimension (preserve aspect ratio)
        width, height = img.size
        if max(width, height) > MAX_DIMENSION:
            if width > height:
                new_width = MAX_DIMENSION
                new_height = int(height * (MAX_DIMENSION / width))
            else:
                new_height = MAX_DIMENSION
                new_width = int(width * (MAX_DIMENSION / height))
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Save to bytes buffer as optimized JPEG
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=JPEG_QUALITY, optimize=True)
        return buffer.getvalue()


def _encode_image_to_base64_uri(image_path: str) -> str:
    """Convert local image file to base64 data URI for vision models.

    Automatically resizes large images to prevent token overflow.

    Args:
        image_path: Path to local image file

    Returns:
        Base64 data URI (e.g., "data:image/jpeg;base64,...")

    Raises:
        FileNotFoundError: If image file doesn't exist
    """
    # Resize and compress image
    image_bytes = _resize_image_for_vision_api(image_path)

    # Encode to base64
    encoded = base64.b64encode(image_bytes).decode('utf-8')
    return f"data:image/jpeg;base64,{encoded}"


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
    # Get vision-capable LLM with timeout
    llm = get_llm(provider="openai", model="gpt-5-mini", timeout=API_TIMEOUT)

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

    # Build vision message with explicit detail parameter
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": content},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_uri,
                        "detail": VISION_DETAIL,  # Explicit high-detail mode
                    },
                },
            ],
        }
    ]

    # Use standard LangChain with_structured_output (handles schema automatically)
    structured_llm = llm.with_structured_output(
        ImageAnalysisResult,  # Pass Pydantic model directly
        method="json_schema",
        include_raw=False,
    )

    result = structured_llm.invoke(messages)

    # Ensure return type matches
    if isinstance(result, ImageAnalysisResult):
        return result
    # If dict, convert to ImageAnalysisResult
    if isinstance(result, dict):
        return ImageAnalysisResult(**result)

    raise ToolExecutionError(
        tool_name="image_analysis_tool",
        message=f"Unexpected result type from Vision API: {type(result)}",
        original_error=None,
    )
