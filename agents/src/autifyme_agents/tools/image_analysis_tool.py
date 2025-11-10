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
from autifyme_agents.core.tool_error_handler import (
    build_agent_error_response,
    build_success_response,
)
from autifyme_agents.schemas.agent_outputs import ImageAnalysisResult

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
        Field(description=(
            "Absolute file path to product image on local filesystem (e.g., '/tmp/media_downloads/product.jpg'). "
            "CRITICAL: Use the path returned from download_<platform>_media tool, NOT the media_id from raw message. "
            "Path must point to locally downloaded file before calling this tool."
        ))
    ],
) -> dict[str, Any]:
    """Analyze product image to extract visual attributes using Vision API (Google Gemini multimodal).

    WHEN TO USE: After downloading media via download_<platform>_media, use this to extract visual features for product cataloging or analysis.
    Extracts: colors, materials, style tags, visual description, dimensions/size indicators, condition, brand elements.
    Returns: Structured ImageAnalysisResult with all visual attributes for use in product operations.
    ERROR HANDLING: If image not found, verify download_<platform>_media was called first. If analysis fails, workflow can continue without visual data (inform user).

    Args:
        image_path: Absolute path to downloaded image file (from download_<platform>_media result)

    Returns:
        Dict with analysis results or error:
        - On success: {"success": True, "visual_description": str, "identified_colors": [...], "identified_materials": [...], "style_tags": [...], ...}
        - On error: {"success": False, "error": str, "error_type": str, "image_path": str, "agent_action": str}
    """
    try:
        # Get vision-capable LLM
        llm = get_llm(provider="google", model="gemini-2.5-flash-preview-09-2025")

        # Convert image to base64 data URI
        image_uri = _encode_image_to_base64_uri(image_path)

        # Vision API prompt (aligned with ImageAnalysisResult schema)
        content = """Analyze this product image and extract ALL visual attributes.

Extract for EACH field:

1. VISUAL_DESCRIPTION (required):
   - Detailed, objective description suitable for e-commerce
   - Describe shape, design, packaging, features visible
   - Be specific and factual (what you see, not assumptions)

2. IDENTIFIED_COLORS (list):
   - All dominant colors visible in product
   - Examples: Clear, Amber, Blue, White, Transparent, etc.
   - List multiple if product has color variations

3. IDENTIFIED_MATERIALS (list):
   - Materials identified from visual inspection
   - Examples: PET, Glass, Aluminum, Cardboard, Plastic, Metal, Wood, etc.
   - Be specific if possible (e.g., "PET plastic" not just "plastic")

4. STYLE_TAGS (list):
   - Style/aesthetic keywords
   - Examples: modern, industrial, vintage, minimalist, decorative, functional
   - Describe design language you observe

5. DIMENSIONS_INDICATORS (optional string):
   - Size/dimension indicators visible (labels, markings, context clues)
   - Examples: "500ml capacity marked on label", "appears ~20cm height based on proportions"
   - Leave null if no size indicators visible

6. CONDITION_ASSESSMENT (optional string):
   - Product condition/quality indicators
   - Examples: "new/unused condition", "minor wear on edges", "excellent condition"
   - Leave null if condition unclear from image

7. BRAND_ELEMENTS (list):
   - Visible brands, logos, manufacturer markings, certifications
   - Examples: "Pavisha logo on cap", "FDA marking on bottom", "CE certification visible"
   - List all visible text/markings

IMPORTANT: Be thorough - extract ALL visible information for each field."""

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
