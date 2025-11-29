"""
Image Studio Tool - Unified image processing for AutifyME.

Handles all image operations: analysis, generation, enhancement.
Uses Gemini 3 Pro Image for generation, Gemini 3 Pro for analysis.

Design:
- Atomic: Single tool for all image operations
- Stateless: Returns temp paths, no database operations
- LLM-friendly: StructuredTool with rich Pydantic schemas

Phase 5 Implementation.
"""

import base64
import logging
import tempfile
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Literal

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from autifyme_agents.core.llm_factory import get_llm

logger = logging.getLogger(__name__)


# ============================================================================
# Enums and Constants
# ============================================================================

class ImageJobType(str, Enum):
    """Supported image operations."""
    ANALYZE = "analyze"
    PRODUCT_SHOT = "product_shot"
    LIFESTYLE = "lifestyle"
    ENHANCE = "enhance"
    RESIZE = "resize"


# ============================================================================
# Input Schemas
# ============================================================================

class ImageSource(BaseModel):
    """Source image specification."""
    type: Literal["local_path", "url", "base64"] = Field(
        ...,
        description="Source type: local_path (file on disk), url (http/https), base64 (encoded data)"
    )
    value: str = Field(
        ...,
        description="The actual source: file path, URL, or base64 string"
    )


class BackgroundSpec(BaseModel):
    """Background settings for product shots."""
    type: Literal["solid", "transparent", "gradient"] = Field(
        default="solid",
        description="Background type"
    )
    color: str = Field(
        default="#FFFFFF",
        description="Background color (hex). Used for solid type."
    )


class OutputSpec(BaseModel):
    """Output specification."""
    name: str = Field(
        default="output",
        description="Output name identifier"
    )
    format: Literal["PNG", "JPEG", "WEBP"] = Field(
        default="PNG",
        description="Output format"
    )
    width: int = Field(
        default=1024,
        description="Output width in pixels"
    )
    height: int = Field(
        default=1024,
        description="Output height in pixels"
    )


class ImageStudioInput(BaseModel):
    """Input schema for image_studio tool."""

    model_config = {"extra": "forbid"}

    job_type: Literal["analyze", "product_shot", "lifestyle", "enhance", "resize"] = Field(
        ...,
        description=(
            "Type of image operation:\n"
            "- analyze: Extract visual attributes (colors, materials, dimensions, quality)\n"
            "- product_shot: Generate clean catalog image with professional background\n"
            "- lifestyle: AI-generate contextual scene featuring the product\n"
            "- enhance: Quality improvement (denoise, sharpen, upscale)\n"
            "- resize: Format/dimension conversion only"
        )
    )

    source: ImageSource = Field(
        ...,
        description="Source image. Required for all job types."
    )

    # Product context (improves generation quality)
    product_context: dict | None = Field(
        default=None,
        description="Product info: name, category, materials, colors. Improves generation quality."
    )

    # Product shot specific
    background: BackgroundSpec | None = Field(
        default=None,
        description="Background settings for product_shot. Defaults to white solid."
    )

    # Lifestyle specific
    scene_prompt: str | None = Field(
        default=None,
        description="Scene description for lifestyle generation. E.g., 'modern kitchen counter'"
    )

    # Output settings
    output: OutputSpec = Field(
        default_factory=OutputSpec,
        description="Output format and dimensions"
    )


# ============================================================================
# Output Schemas
# ============================================================================

class ImageAnalysisResult(BaseModel):
    """Result from analyze job."""
    description: str = Field(description="Overall image description")
    product_type: str | None = Field(default=None, description="Detected product type")
    materials: list[str] = Field(default_factory=list, description="Detected materials")
    colors: list[str] = Field(default_factory=list, description="Detected colors")
    dimensions_estimate: str | None = Field(default=None, description="Estimated dimensions")
    quality_score: float = Field(default=0.0, description="Image quality 0-1")
    background_type: str | None = Field(default=None, description="Current background type")
    suggestions: list[str] = Field(default_factory=list, description="Improvement suggestions")


class ImageStudioOutput(BaseModel):
    """Single generated/processed image."""
    name: str = Field(description="Output name from OutputSpec")
    temp_path: str = Field(description="Local temp path to generated image")
    base64_data: str = Field(description="Base64-encoded image data for inline display")
    mime_type: str = Field(default="image/png", description="MIME type for the image")
    preview_path: str | None = Field(default=None, description="Smaller preview for HITL")
    format: str = Field(description="Output format (PNG, JPEG, etc)")
    width: int = Field(description="Output width in pixels")
    height: int = Field(description="Output height in pixels")
    size_bytes: int = Field(default=0, description="File size in bytes")
    operations_applied: list[str] = Field(default_factory=list, description="Operations performed")

    # Pre-built for create_record
    suggested_asset_data: dict = Field(
        default_factory=dict,
        description="Ready-to-use data for assets table"
    )


class ImageStudioResult(BaseModel):
    """Complete result from image_studio tool."""
    success: bool = Field(description="Whether operation succeeded")
    job_type: str = Field(description="Job type that was executed")

    # For ANALYZE job
    analysis: ImageAnalysisResult | None = Field(default=None, description="Analysis results")

    # For generation jobs
    outputs: list[ImageStudioOutput] | None = Field(default=None, description="Generated images")

    # For regeneration/feedback
    job_spec_used: dict = Field(default_factory=dict, description="Input spec for regeneration")

    # Metadata
    processing_time_ms: int = Field(default=0, description="Processing time in milliseconds")
    llm_provider_used: str | None = Field(default=None, description="LLM/API used")
    error: str | None = Field(default=None, description="Error message if failed")


# ============================================================================
# Tool Implementation
# ============================================================================

def _load_image_as_base64(source: ImageSource) -> str:
    """Load image from source and return as base64."""
    if source.type == "local_path":
        path = Path(source.value)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {source.value}")
        return base64.b64encode(path.read_bytes()).decode("utf-8")
    elif source.type == "base64":
        return source.value
    elif source.type == "url":
        import httpx
        response = httpx.get(source.value)
        response.raise_for_status()
        return base64.b64encode(response.content).decode("utf-8")
    else:
        raise ValueError(f"Unknown source type: {source.type}")


def _get_mime_type(source: ImageSource) -> str:
    """Infer MIME type from source."""
    if source.type == "local_path":
        ext = Path(source.value).suffix.lower()
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
        return mime_map.get(ext, "image/jpeg")
    return "image/jpeg"


def _extract_generated_image(response) -> str:
    """Extract base64 image data from LLM response.

    LangChain returns generated images in response.content as blocks with
    'image_url' key containing data URL: 'data:image/png;base64,<data>'
    """
    # Check content_blocks first (newer LangChain structure)
    if hasattr(response, "content_blocks") and response.content_blocks:
        for block in response.content_blocks:
            if isinstance(block, dict):
                if block.get("type") == "image" and "base64" in block:
                    return block["base64"]
                if "image_url" in block:
                    url = block["image_url"].get("url", "")
                    if "base64," in url:
                        return url.split("base64,")[-1]

    # Check content (list of content blocks)
    if hasattr(response, "content") and isinstance(response.content, list):
        for block in response.content:
            if isinstance(block, dict):
                if "image_url" in block:
                    url = block["image_url"].get("url", "")
                    if "base64," in url:
                        return url.split("base64,")[-1]
                # Direct base64 in block
                if block.get("type") == "image" and "base64" in block:
                    return block["base64"]

    # Check additional_kwargs (fallback)
    if hasattr(response, "additional_kwargs"):
        if "image" in response.additional_kwargs:
            return response.additional_kwargs["image"]

    # Log response structure for debugging
    logger.error(
        "Could not extract image from response. "
        f"content_blocks: {getattr(response, 'content_blocks', None)}, "
        f"content type: {type(getattr(response, 'content', None))}, "
        f"additional_kwargs: {getattr(response, 'additional_kwargs', None)}"
    )
    raise ValueError("No image generated in response")


async def _run_analyze(input_data: ImageStudioInput) -> ImageStudioResult:
    """Run image analysis using Gemini 3 Pro."""
    start_time = time.time()

    try:
        # Load image
        image_b64 = _load_image_as_base64(input_data.source)
        mime_type = _get_mime_type(input_data.source)

        # Use Gemini 3 Pro for analysis (best reasoning)
        llm = get_llm(
            provider="google",
            model="gemini-3-pro-preview",
            temperature=0.3,
        )

        # Build multimodal message
        from langchain_core.messages import HumanMessage

        message = HumanMessage(
            content=[
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{image_b64}"},
                },
                {
                    "type": "text",
                    "text": """Analyze this product image and provide:
1. Overall description
2. Product type (if identifiable)
3. Materials visible
4. Colors present
5. Estimated dimensions
6. Image quality score (0-1)
7. Background type (white, colored, transparent, complex)
8. Suggestions for catalog-ready image

Respond in JSON format:
{
  "description": "...",
  "product_type": "...",
  "materials": ["..."],
  "colors": ["..."],
  "dimensions_estimate": "...",
  "quality_score": 0.8,
  "background_type": "...",
  "suggestions": ["..."]
}"""
                },
            ]
        )

        response = await llm.ainvoke([message])

        # Parse response
        import json
        content = response.content
        # Extract JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        analysis_data = json.loads(content.strip())
        analysis = ImageAnalysisResult(**analysis_data)

        processing_time = int((time.time() - start_time) * 1000)

        return ImageStudioResult(
            success=True,
            job_type="analyze",
            analysis=analysis,
            job_spec_used=input_data.model_dump(),
            processing_time_ms=processing_time,
            llm_provider_used="gemini-3-pro-preview",
        )

    except Exception as e:
        logger.exception("Image analysis failed")
        return ImageStudioResult(
            success=False,
            job_type="analyze",
            error=str(e),
            job_spec_used=input_data.model_dump(),
            processing_time_ms=int((time.time() - start_time) * 1000),
        )


async def _run_product_shot(input_data: ImageStudioInput) -> ImageStudioResult:
    """Generate product shot using Gemini 3 Pro Image."""
    start_time = time.time()

    try:
        # Load source image
        image_b64 = _load_image_as_base64(input_data.source)
        mime_type = _get_mime_type(input_data.source)

        # Get background settings
        bg = input_data.background or BackgroundSpec()
        product_ctx = input_data.product_context or {}

        # Use Gemini 3 Pro Image for generation
        llm = get_llm(
            provider="google",
            model="gemini-3-pro-image-preview",
            temperature=0.7,
            response_modalities=["IMAGE", "TEXT"],
        )

        # Build prompt
        product_name = product_ctx.get("name", "product")
        prompt = f"""Transform this product image into a professional catalog photo:

Product: {product_name}
Background: {bg.type} - {bg.color if bg.type == "solid" else ""}
Style: Clean, professional, e-commerce ready
Dimensions: {input_data.output.width}x{input_data.output.height}

Keep the product exactly as shown but:
1. Remove existing background
2. Apply clean {bg.color if bg.type == "solid" else "white"} background
3. Center the product
4. Ensure professional lighting
5. Maintain original product details and colors"""

        from langchain_core.messages import HumanMessage

        message = HumanMessage(
            content=[
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{image_b64}"},
                },
                {"type": "text", "text": prompt},
            ]
        )

        response = await llm.ainvoke([message])

        # Extract generated image from response
        generated_b64 = _extract_generated_image(response)

        # Save to temp file
        temp_dir = Path(tempfile.gettempdir()) / "image_studio"
        temp_dir.mkdir(exist_ok=True)

        output_id = str(uuid.uuid4())[:8]
        output_path = temp_dir / f"{input_data.output.name}_{output_id}.{input_data.output.format.lower()}"

        output_path.write_bytes(base64.b64decode(generated_b64))

        file_size = output_path.stat().st_size

        # Build output
        output_mime = f"image/{input_data.output.format.lower()}"
        output = ImageStudioOutput(
            name=input_data.output.name,
            temp_path=str(output_path),
            base64_data=generated_b64,
            mime_type=output_mime,
            format=input_data.output.format,
            width=input_data.output.width,
            height=input_data.output.height,
            size_bytes=file_size,
            operations_applied=["background_removal", "reframing", "lighting_adjustment"],
            suggested_asset_data={
                "name": f"{product_name} - Catalog",
                "storage_url": str(output_path),
                "mime_type": output_mime,
                "asset_type": "PRODUCT_IMAGE",
                "width": input_data.output.width,
                "height": input_data.output.height,
                "is_ai_generated": True,
                "status": "ACTIVE",
            },
        )

        processing_time = int((time.time() - start_time) * 1000)

        return ImageStudioResult(
            success=True,
            job_type="product_shot",
            outputs=[output],
            job_spec_used=input_data.model_dump(),
            processing_time_ms=processing_time,
            llm_provider_used="gemini-3-pro-image-preview",
        )

    except Exception as e:
        logger.exception("Product shot generation failed")
        return ImageStudioResult(
            success=False,
            job_type="product_shot",
            error=str(e),
            job_spec_used=input_data.model_dump(),
            processing_time_ms=int((time.time() - start_time) * 1000),
        )


async def _run_lifestyle(input_data: ImageStudioInput) -> ImageStudioResult:
    """Generate lifestyle image using Gemini 3 Pro Image."""
    start_time = time.time()

    try:
        image_b64 = _load_image_as_base64(input_data.source)
        mime_type = _get_mime_type(input_data.source)

        product_ctx = input_data.product_context or {}
        scene = input_data.scene_prompt or "modern, clean setting"

        llm = get_llm(
            provider="google",
            model="gemini-3-pro-image-preview",
            temperature=0.8,
            response_modalities=["IMAGE", "TEXT"],
        )

        product_name = product_ctx.get("name", "product")
        prompt = f"""Create a lifestyle image featuring this product:

Product: {product_name}
Scene: {scene}
Style: Professional lifestyle photography, aspirational

Place the product naturally in the scene while maintaining its exact appearance.
The scene should enhance the product's appeal for marketing purposes."""

        from langchain_core.messages import HumanMessage

        message = HumanMessage(
            content=[
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{image_b64}"},
                },
                {"type": "text", "text": prompt},
            ]
        )

        response = await llm.ainvoke([message])

        # Extract generated image from response
        generated_b64 = _extract_generated_image(response)

        temp_dir = Path(tempfile.gettempdir()) / "image_studio"
        temp_dir.mkdir(exist_ok=True)

        output_id = str(uuid.uuid4())[:8]
        output_path = temp_dir / f"{input_data.output.name}_{output_id}.{input_data.output.format.lower()}"

        output_path.write_bytes(base64.b64decode(generated_b64))

        file_size = output_path.stat().st_size

        output_mime = f"image/{input_data.output.format.lower()}"
        output = ImageStudioOutput(
            name=input_data.output.name,
            temp_path=str(output_path),
            base64_data=generated_b64,
            mime_type=output_mime,
            format=input_data.output.format,
            width=input_data.output.width,
            height=input_data.output.height,
            size_bytes=file_size,
            operations_applied=["scene_generation", "product_integration"],
            suggested_asset_data={
                "name": f"{product_name} - Lifestyle",
                "storage_url": str(output_path),
                "mime_type": output_mime,
                "asset_type": "LIFESTYLE",
                "width": input_data.output.width,
                "height": input_data.output.height,
                "is_ai_generated": True,
                "generation_prompt": scene,
                "status": "ACTIVE",
            },
        )

        processing_time = int((time.time() - start_time) * 1000)

        return ImageStudioResult(
            success=True,
            job_type="lifestyle",
            outputs=[output],
            job_spec_used=input_data.model_dump(),
            processing_time_ms=processing_time,
            llm_provider_used="gemini-3-pro-image-preview",
        )

    except Exception as e:
        logger.exception("Lifestyle generation failed")
        return ImageStudioResult(
            success=False,
            job_type="lifestyle",
            error=str(e),
            job_spec_used=input_data.model_dump(),
            processing_time_ms=int((time.time() - start_time) * 1000),
        )


async def _image_studio_impl(
    job_type: str,
    source: dict | ImageSource,
    product_context: dict | None = None,
    background: dict | BackgroundSpec | None = None,
    scene_prompt: str | None = None,
    output: dict | OutputSpec | None = None,
) -> dict:
    """Image studio implementation."""
    # Handle source - may be dict or already parsed ImageSource
    if isinstance(source, ImageSource):
        source_obj = source
    else:
        source_obj = ImageSource(**source)

    # Handle background
    if background is None:
        bg_obj = None
    elif isinstance(background, BackgroundSpec):
        bg_obj = background
    else:
        bg_obj = BackgroundSpec(**background)

    # Handle output
    if output is None:
        output_obj = OutputSpec()
    elif isinstance(output, OutputSpec):
        output_obj = output
    else:
        output_obj = OutputSpec(**output)

    # Build input
    input_data = ImageStudioInput(
        job_type=job_type,
        source=source_obj,
        product_context=product_context,
        background=bg_obj,
        scene_prompt=scene_prompt,
        output=output_obj,
    )

    # Route to handler
    if job_type == "analyze":
        result = await _run_analyze(input_data)
    elif job_type == "product_shot":
        result = await _run_product_shot(input_data)
    elif job_type == "lifestyle":
        result = await _run_lifestyle(input_data)
    else:
        result = ImageStudioResult(
            success=False,
            job_type=job_type,
            error=f"Job type '{job_type}' not yet implemented",
            job_spec_used=input_data.model_dump(),
        )

    return result.model_dump()


# ============================================================================
# Tool Factory
# ============================================================================

def create_image_studio_tool() -> StructuredTool:
    """Create the image_studio tool.

    Returns:
        StructuredTool configured for image operations.
    """
    return StructuredTool.from_function(
        coroutine=_image_studio_impl,
        name="image_studio",
        description=(
            "Unified image processing tool. Supports:\n"
            "- analyze: Extract visual attributes (colors, materials, quality)\n"
            "- product_shot: Generate clean catalog image with professional background\n"
            "- lifestyle: AI-generate contextual scene featuring the product\n"
            "\n"
            "Returns temp paths. Use write_data to persist approved assets."
        ),
        args_schema=ImageStudioInput,
    )


# Pre-instantiated tool for direct import
image_studio_tool = create_image_studio_tool()
