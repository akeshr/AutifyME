"""Image Studio Tool - Gemini 3 Pro Image (Nano Banana Pro) implementation.

Unified tool for product image operations using structured Pydantic schemas.
Converts structured input to Gemini API calls, handles responses, saves outputs.

Architecture: Atomic tool - one powerful LLM = one powerful tool.
"""

from __future__ import annotations

import base64
import logging
import platform
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.tools import StructuredTool
from PIL import Image

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.tool_error_handler import (
    build_agent_error_response,
    build_success_response,
)
from autifyme_agents.tools.image_studio.schemas import (
    AnalysisAttributes,
    AnalysisResult,
    BackgroundSpec,
    EnhancementSpec,
    FramingSpec,
    ImageMetadata,
    ImageOperation,
    ImageStudioErrorCode,
    ImageStudioInput,
    ImageStudioOutput,
    LightingSpec,
    OutputSpec,
    OutputVariant,
    ProductPlacement,
    SceneSpec,
)

logger = logging.getLogger(__name__)

# Use same temp directory as WhatsApp media downloads (consistency)
if platform.system() == "Windows":
    MEDIA_DIR = Path(tempfile.gettempdir()) / "media_downloads"
else:
    MEDIA_DIR = Path("/tmp/media_downloads")
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# Image processing constants
MAX_DIMENSION = 2048
JPEG_QUALITY = 85

# Gemini 3 Pro Image model ID
GEMINI_3_IMAGE_MODEL = "gemini-3-pro-image-preview"


# =============================================================================
# LLM Helper
# =============================================================================


def _get_gemini3_image_llm(
    output_spec: OutputSpec | None = None,
    for_analysis: bool = False,
):
    """Get Gemini 3 Pro Image LLM with proper configuration.

    Args:
        output_spec: Output specifications for image generation/editing
        for_analysis: If True, only TEXT modality (no image generation)

    Returns:
        Configured LLM for Gemini 3 Pro Image
    """
    if for_analysis:
        # Analysis only needs TEXT output
        return get_llm(
            provider="google",
            model=GEMINI_3_IMAGE_MODEL,
            response_modalities=["TEXT"],
        )

    # For edit/generate, include IMAGE modality with config
    aspect_ratio = output_spec.aspect_ratio if output_spec else "1:1"
    image_size = output_spec.size if output_spec else "2K"

    return get_llm(
        provider="google",
        model=GEMINI_3_IMAGE_MODEL,
        response_modalities=["TEXT", "IMAGE"],
        image_aspect_ratio=aspect_ratio,
        image_size=image_size,
    )


# =============================================================================
# Image Utilities
# =============================================================================


def _load_and_encode_image(image_path: str) -> tuple[str, str]:
    """Load image, resize if needed, encode to base64 data URI.

    Args:
        image_path: Path to source image

    Returns:
        Tuple of (base64_data_uri, mime_type)

    Raises:
        FileNotFoundError: If image doesn't exist
        ValueError: If image is corrupt
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    try:
        with Image.open(path) as img:
            # Determine format
            fmt = img.format or "JPEG"
            mime_type = f"image/{fmt.lower()}"

            # Convert to RGB if needed
            if img.mode in ("RGBA", "LA", "P"):
                rgb_img = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "RGBA":
                    rgb_img.paste(img, mask=img.split()[-1])
                else:
                    rgb_img.paste(img)
                img = rgb_img
                fmt = "JPEG"
                mime_type = "image/jpeg"

            # Resize if too large
            width, height = img.size
            if max(width, height) > MAX_DIMENSION:
                if width > height:
                    new_width = MAX_DIMENSION
                    new_height = int(height * (MAX_DIMENSION / width))
                else:
                    new_height = MAX_DIMENSION
                    new_width = int(width * (MAX_DIMENSION / height))
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Encode to base64
            import io

            buffer = io.BytesIO()
            img.save(buffer, format=fmt, quality=JPEG_QUALITY, optimize=True)
            encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")

            return f"data:{mime_type};base64,{encoded}", mime_type

    except Exception as e:
        if "cannot identify image file" in str(e).lower():
            raise ValueError(f"Corrupt or invalid image: {image_path}") from e
        raise


def _save_base64_image(
    base64_data: str,
    operation: str,
    output_spec: OutputSpec,
) -> tuple[Path, ImageMetadata]:
    """Save base64 image data to temp file.

    Args:
        base64_data: Base64 encoded image (may include data URI prefix)
        operation: Operation name for filename
        output_spec: Output configuration

    Returns:
        Tuple of (file_path, metadata)
    """
    # Strip data URI prefix if present
    if "," in base64_data:
        base64_data = base64_data.split(",", 1)[1]

    # Decode
    image_bytes = base64.b64decode(base64_data)

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    extension = output_spec.format.lower()
    filename = f"{timestamp}_{operation}_{unique_id}.{extension}"
    file_path = MEDIA_DIR / filename

    # Save file
    file_path.write_bytes(image_bytes)

    # Get metadata
    with Image.open(file_path) as img:
        width, height = img.size
        metadata = ImageMetadata(
            width=width,
            height=height,
            format=output_spec.format,
            size_bytes=len(image_bytes),
            aspect_ratio=f"{width}:{height}",
        )

    logger.info(
        f"Saved image to {file_path}",
        extra={"width": width, "height": height, "size_bytes": len(image_bytes)},
    )

    return file_path, metadata


# =============================================================================
# Prompt Builders
# =============================================================================


def _build_analyze_prompt(analysis: AnalysisAttributes) -> str:
    """Build analysis prompt from AnalysisAttributes."""
    sections = []

    if analysis.colors:
        sections.append("COLORS: List all dominant colors visible (e.g., 'transparent', 'amber', 'white')")
    if analysis.materials:
        sections.append("MATERIALS: Identify materials (e.g., 'PET plastic', 'glass', 'aluminum')")
    if analysis.dimensions:
        sections.append("DIMENSIONS: Estimate size/dimensions from visual cues or labels")
    if analysis.condition:
        sections.append("CONDITION: Assess product condition (new, used, damaged)")
    if analysis.brand_text:
        sections.append("BRAND_TEXT: Extract all visible text, logos, brand names")
    if analysis.product_category:
        sections.append("PRODUCT_CATEGORY: Classify product type (e.g., 'jar', 'bottle', 'container')")
    if analysis.quality_score:
        sections.append("QUALITY_SCORE: Rate image quality 0.0-1.0 (lighting, focus, composition)")
    if analysis.background_type:
        sections.append("BACKGROUND_TYPE: Describe background (solid, cluttered, gradient, transparent)")

    for attr in analysis.custom_attributes:
        sections.append(f"CUSTOM - {attr.upper()}: Extract {attr}")

    return f"""Analyze this product image and extract the following attributes:

{chr(10).join(f'- {s}' for s in sections)}

Also detect:
- PRODUCT_COUNT: How many distinct products are in the image?
- If multiple products detected, set multi_product_warning

Return structured JSON matching the AnalysisResult schema."""


def _build_edit_prompt(input_spec: ImageStudioInput) -> str:
    """Build edit prompt from structured input."""
    instructions = ["Edit this product image with the following specifications:"]

    if input_spec.background:
        bg = input_spec.background
        if bg.type == "solid":
            instructions.append(f"BACKGROUND: Replace with solid {bg.color} color")
        elif bg.type == "transparent":
            instructions.append("BACKGROUND: Make background transparent (PNG)")
        elif bg.type == "gradient":
            instructions.append(f"BACKGROUND: Apply gradient from {bg.color} to {bg.gradient_end}")
        elif bg.type == "blur":
            instructions.append(f"BACKGROUND: Blur background ({bg.blur_strength} strength)")

    if input_spec.lighting:
        lt = input_spec.lighting
        instructions.append(
            f"LIGHTING: Apply {lt.type} lighting from {lt.direction}, "
            f"intensity={lt.intensity}, temperature={lt.color_temperature}"
        )

    if input_spec.framing:
        fr = input_spec.framing
        instructions.append(
            f"FRAMING: Product should cover {fr.product_coverage_percent}% of frame, "
            f"aligned {fr.alignment}, angle={fr.angle}, padding={fr.padding_percent}%"
        )

    if input_spec.enhancement:
        en = input_spec.enhancement
        enhancements = []
        if en.sharpness != "none":
            enhancements.append(f"sharpness={en.sharpness}")
        if en.contrast != "none":
            enhancements.append(f"contrast={en.contrast}")
        if en.saturation != "none":
            enhancements.append(f"saturation={en.saturation}")
        if en.denoise:
            enhancements.append("denoise")
        if en.upscale != "none":
            enhancements.append(f"upscale={en.upscale}")
        if en.color_correction:
            enhancements.append("color_correction")
        if enhancements:
            instructions.append(f"ENHANCE: Apply {', '.join(enhancements)}")

    # Output specs
    out = input_spec.output
    instructions.append(
        f"OUTPUT: Generate {out.size} image, aspect ratio {out.aspect_ratio}, format {out.format}"
    )

    return "\n".join(instructions)


def _build_generate_prompt(input_spec: ImageStudioInput) -> str:
    """Build generation prompt from structured input."""
    if not input_spec.scene:
        return "Generate a professional product photo with clean studio background."

    sc = input_spec.scene
    pl = input_spec.placement or ProductPlacement()

    prompt = f"""Generate a lifestyle product photograph:

SCENE:
- Environment: {sc.environment}
- Style: {sc.style}
- Mood: {sc.mood}
- Time of day: {sc.time_of_day}

PRODUCT PLACEMENT:
- Position: {pl.position}
- Scale: {pl.scale}
- Surface: {pl.surface or 'appropriate for scene'}

The product from the source image should be seamlessly placed in this scene.
Maintain product details and proportions accurately.
"""

    # Output specs
    out = input_spec.output
    prompt += f"\nOUTPUT: {out.size} image, aspect ratio {out.aspect_ratio}, format {out.format}"

    return prompt


# =============================================================================
# Operation Handlers
# =============================================================================


def _handle_analyze(input_spec: ImageStudioInput) -> ImageStudioOutput:
    """Handle analyze operation."""
    if not input_spec.source_image:
        return ImageStudioOutput(
            success=False,
            operation=ImageOperation.ANALYZE,
            error="source_image required for analyze operation",
            error_code=ImageStudioErrorCode.INVALID_INPUT,
        )

    try:
        # Load and encode image
        image_uri, _ = _load_and_encode_image(input_spec.source_image)

        # Get Gemini 3 Pro Image for analysis (TEXT output only)
        llm = _get_gemini3_image_llm(for_analysis=True)

        # Build prompt
        analysis_attrs = input_spec.analysis or AnalysisAttributes()
        prompt = _build_analyze_prompt(analysis_attrs)

        # Build message with image
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_uri}},
                ],
            }
        ]

        # Get structured output
        structured_llm = llm.with_structured_output(
            AnalysisResult,
            method="json_schema",
            include_raw=False,
        )

        result = structured_llm.invoke(messages)

        # Convert to AnalysisResult if needed
        if isinstance(result, dict):
            result = AnalysisResult(**result)

        # Check for warnings
        warnings = []
        if result.quality_score < 0.5:
            warnings.append(f"Low image quality score: {result.quality_score:.2f}")
        if result.product_count > 1:
            warnings.append(f"Multiple products detected: {result.product_count}")
            result.multi_product_warning = (
                f"Image contains {result.product_count} products. "
                "Consider using single product images for catalog."
            )

        return ImageStudioOutput(
            success=True,
            operation=ImageOperation.ANALYZE,
            analysis=result,
            warnings=warnings,
        )

    except FileNotFoundError as e:
        return ImageStudioOutput(
            success=False,
            operation=ImageOperation.ANALYZE,
            error=str(e),
            error_code=ImageStudioErrorCode.FILE_NOT_FOUND,
        )
    except ValueError as e:
        return ImageStudioOutput(
            success=False,
            operation=ImageOperation.ANALYZE,
            error=str(e),
            error_code=ImageStudioErrorCode.CORRUPT_FILE,
        )
    except Exception as e:
        logger.exception("Analyze operation failed")
        return ImageStudioOutput(
            success=False,
            operation=ImageOperation.ANALYZE,
            error=str(e),
            error_code=ImageStudioErrorCode.API_ERROR,
        )


def _handle_edit(input_spec: ImageStudioInput) -> ImageStudioOutput:
    """Handle edit operation."""
    if not input_spec.source_image:
        return ImageStudioOutput(
            success=False,
            operation=ImageOperation.EDIT,
            error="source_image required for edit operation",
            error_code=ImageStudioErrorCode.INVALID_INPUT,
        )

    try:
        # Load and encode image
        image_uri, _ = _load_and_encode_image(input_spec.source_image)

        # Get Gemini 3 Pro Image for editing with output config
        llm = _get_gemini3_image_llm(output_spec=input_spec.output)

        # Build prompt
        prompt = _build_edit_prompt(input_spec)

        # Build message with image
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_uri}},
                ],
            }
        ]

        # Invoke
        response = llm.invoke(messages)

        # Extract image from response
        image_data = None
        if hasattr(response, "additional_kwargs"):
            image_data = response.additional_kwargs.get("image")

        if not image_data:
            return ImageStudioOutput(
                success=False,
                operation=ImageOperation.EDIT,
                error="No image returned from API",
                error_code=ImageStudioErrorCode.API_ERROR,
            )

        # Save output
        file_path, metadata = _save_base64_image(
            image_data,
            "edit",
            input_spec.output,
        )

        output_variant = OutputVariant(
            variant="master",
            path=str(file_path),
            preview_path=str(file_path),
            metadata=metadata,
        )

        return ImageStudioOutput(
            success=True,
            operation=ImageOperation.EDIT,
            outputs=[output_variant],
        )

    except FileNotFoundError as e:
        return ImageStudioOutput(
            success=False,
            operation=ImageOperation.EDIT,
            error=str(e),
            error_code=ImageStudioErrorCode.FILE_NOT_FOUND,
        )
    except ValueError as e:
        return ImageStudioOutput(
            success=False,
            operation=ImageOperation.EDIT,
            error=str(e),
            error_code=ImageStudioErrorCode.CORRUPT_FILE,
        )
    except Exception as e:
        logger.exception("Edit operation failed")
        return ImageStudioOutput(
            success=False,
            operation=ImageOperation.EDIT,
            error=str(e),
            error_code=ImageStudioErrorCode.API_ERROR,
        )


def _handle_generate(input_spec: ImageStudioInput) -> ImageStudioOutput:
    """Handle generate operation (lifestyle shots)."""
    try:
        # Get Gemini 3 Pro Image for generation with output config
        llm = _get_gemini3_image_llm(output_spec=input_spec.output)

        # Build prompt
        prompt = _build_generate_prompt(input_spec)

        # Build message (optionally with source image for reference)
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]

        if input_spec.source_image:
            image_uri, _ = _load_and_encode_image(input_spec.source_image)
            content.append({"type": "image_url", "image_url": {"url": image_uri}})

        # Add reference images (up to 14 for Gemini 3)
        for ref_path in input_spec.reference_images[:14]:
            try:
                ref_uri, _ = _load_and_encode_image(ref_path)
                content.append({"type": "image_url", "image_url": {"url": ref_uri}})
            except Exception as e:
                logger.warning(f"Failed to load reference image {ref_path}: {e}")

        messages = [{"role": "user", "content": content}]

        # Invoke
        response = llm.invoke(messages)

        # Extract image from response
        image_data = None
        if hasattr(response, "additional_kwargs"):
            image_data = response.additional_kwargs.get("image")

        if not image_data:
            return ImageStudioOutput(
                success=False,
                operation=ImageOperation.GENERATE,
                error="No image returned from API",
                error_code=ImageStudioErrorCode.API_ERROR,
            )

        # Save output
        file_path, metadata = _save_base64_image(
            image_data,
            "generate",
            input_spec.output,
        )

        output_variant = OutputVariant(
            variant="master",
            path=str(file_path),
            preview_path=str(file_path),
            metadata=metadata,
        )

        return ImageStudioOutput(
            success=True,
            operation=ImageOperation.GENERATE,
            outputs=[output_variant],
        )

    except FileNotFoundError as e:
        return ImageStudioOutput(
            success=False,
            operation=ImageOperation.GENERATE,
            error=str(e),
            error_code=ImageStudioErrorCode.FILE_NOT_FOUND,
        )
    except Exception as e:
        logger.exception("Generate operation failed")
        return ImageStudioOutput(
            success=False,
            operation=ImageOperation.GENERATE,
            error=str(e),
            error_code=ImageStudioErrorCode.API_ERROR,
        )


# =============================================================================
# Main Tool Entry Point
# =============================================================================


def _image_studio_impl(
    operation: str,
    source_image: str | None = None,
    reference_images: list[str] | None = None,
    background: dict | None = None,
    lighting: dict | None = None,
    framing: dict | None = None,
    enhancement: dict | None = None,
    scene: dict | None = None,
    placement: dict | None = None,
    analysis: dict | None = None,
    output: dict | None = None,
) -> dict[str, Any]:
    """Image Studio tool implementation.

    Internal function that handles the actual processing.
    Converts dict inputs to Pydantic models and dispatches to handlers.
    """
    try:
        # Helper to handle both dict and Pydantic model inputs
        # (LangChain's args_schema may already convert dicts to Pydantic models)
        def _maybe_convert(value, model_class):
            if value is None:
                return None
            if isinstance(value, model_class):
                return value  # Already converted by args_schema
            if isinstance(value, dict):
                return model_class(**value)  # Convert dict to model
            return value

        # Build input spec from individual fields
        input_spec = ImageStudioInput(
            operation=ImageOperation(operation) if isinstance(operation, str) else operation,
            source_image=source_image,
            reference_images=reference_images or [],
            background=_maybe_convert(background, BackgroundSpec),
            lighting=_maybe_convert(lighting, LightingSpec),
            framing=_maybe_convert(framing, FramingSpec),
            enhancement=_maybe_convert(enhancement, EnhancementSpec),
            scene=_maybe_convert(scene, SceneSpec),
            placement=_maybe_convert(placement, ProductPlacement),
            analysis=_maybe_convert(analysis, AnalysisAttributes),
            output=_maybe_convert(output, OutputSpec) or OutputSpec(),
        )

        # Dispatch to handler
        if input_spec.operation == ImageOperation.ANALYZE:
            result = _handle_analyze(input_spec)
        elif input_spec.operation == ImageOperation.EDIT:
            result = _handle_edit(input_spec)
        elif input_spec.operation == ImageOperation.GENERATE:
            result = _handle_generate(input_spec)
        else:
            result = ImageStudioOutput(
                success=False,
                operation=input_spec.operation,
                error=f"Unknown operation: {input_spec.operation}",
                error_code=ImageStudioErrorCode.INVALID_INPUT,
            )

        # Convert to dict for return
        if result.success:
            return build_success_response(result.model_dump())
        else:
            return {
                "success": False,
                "error": result.error,
                "error_code": result.error_code,
                "operation": result.operation.value,
                "warnings": result.warnings,
            }

    except Exception as e:
        logger.exception("Image Studio tool failed")
        return build_agent_error_response(
            exception=e,
            context={"operation": operation, "source_image": source_image},
            fallback_type="IMAGE_STUDIO_ERROR",
            fallback_action=(
                "Image processing failed. Retry once. If fails again, "
                "continue without image processing and inform user."
            ),
        )


def create_image_studio_tool() -> StructuredTool:
    """Create the Image Studio tool with structured input.

    Returns StructuredTool for use in agent toolkits.
    """
    return StructuredTool.from_function(
        func=_image_studio_impl,
        name="image_studio",
        description=(
            "Process product images using Gemini 3 Pro Image (Nano Banana Pro). "
            "Supports three operations:\n"
            "- analyze: Extract visual attributes (colors, materials, quality)\n"
            "- edit: Modify image (background removal, enhancement, lighting)\n"
            "- generate: Create lifestyle shots with product in scene\n\n"
            "All parameters are structured - no string instructions needed. "
            "Returns structured output with file paths for HITL preview."
        ),
        args_schema=ImageStudioInput,
        return_direct=False,
    )
