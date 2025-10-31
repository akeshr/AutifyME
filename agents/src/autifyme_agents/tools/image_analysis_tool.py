"""Image Analysis Tool - Vision API wrapper for product image analysis.

Deterministic tool that calls OpenAI Vision API to extract visual attributes
from product images. Returns structured ImageAnalysisResult.

2-Level Architecture: Tool (not specialist) - deterministic API call
"""

import base64
import io
from pathlib import Path
from typing import Annotated, Any

from langchain.tools import tool
from PIL import Image
from pydantic import Field

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.schemas.agent_outputs import ImageAnalysisResult
from autifyme_agents.core.tool_error_handler import (
    build_agent_error_response,
    build_success_response,
)

# Vision model optimal dimensions (OpenAI recommends max 2048px)
MAX_DIMENSION = 2048
JPEG_QUALITY = 85


def _resize_image_for_vision_api(image_path: str) -> bytes:
    """Resize and compress image for efficient Vision API processing.

    Large images (e.g., 5MB phone photos) cause massive token usage when base64-encoded.
    This resizes to max 2048px (OpenAI's high-detail threshold) while preserving aspect ratio.

    Args:
        image_path: Path to source image file

    Returns:
        Optimized image as JPEG bytes

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
) -> dict[str, Any]:
    """Analyze product image to extract visual attributes using Vision API.

    Extracts colors, materials, style tags, dimensions, and generates detailed
    visual description. Uses OpenAI Vision model for multimodal analysis.

    Args:
        image_path: Path to image file on local filesystem

    Returns:
        Dict with analysis results or error:
        - On success: {"success": True, "visual_description": str, "identified_colors": [...], "identified_materials": [...], ...}
        - On error: {"success": False, "error": str, "error_type": str, "image_path": str}

    Example:
        >>> result = image_analysis_tool("/tmp/product.jpg")
        >>> print(result["visual_description"])
        "Blue leather sneakers with white sole..."
        >>> print(result["identified_colors"])
        ["blue", "white"]
    """
    try:
        # Get vision-capable LLM
        llm = get_llm(provider="google", model="gemini-2.5-flash")

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

        # Use standard LangChain with_structured_output (handles schema automatically)
        structured_llm = llm.with_structured_output(
            ImageAnalysisResult,  # Pass Pydantic model directly
            method="json_schema",
            include_raw=False,
        )

        result = structured_llm.invoke(messages)

        # Convert to dict for consistent return format
        if isinstance(result, ImageAnalysisResult):
            return build_success_response(result.model_dump())
        # If dict, convert to ImageAnalysisResult then serialize
        if isinstance(result, dict):
            analysis = ImageAnalysisResult(**result)
            return build_success_response(analysis.model_dump())

        # Unexpected result type
        return build_agent_error_response(
            exception=ValueError(f"Expected ImageAnalysisResult but got {type(result)}"),
            context={"image_path": image_path},
            fallback_type="ANALYSIS_ERROR",
            fallback_action=(
                "Vision API integration issue. Retry analysis or inform user. "
                "If persistent, contact system administrator."
            ),
        )

    except FileNotFoundError as exc:
        # Image file not found
        return build_agent_error_response(
            exception=exc,
            context={"image_path": image_path},
            fallback_type="ANALYSIS_ERROR",
            fallback_action=(
                "Verify image_path is correct. Check if image was downloaded successfully. "
                "Request image from user again if missing."
            ),
        )
    except Exception as exc:
        return build_agent_error_response(
            exception=exc,
            context={"image_path": image_path},
            fallback_type="ANALYSIS_ERROR",
            fallback_action=(
                "Unexpected error during image analysis. Retry once. "
                "If fails again, continue workflow without visual analysis and inform user."
            ),
        )
