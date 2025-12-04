"""Image Studio Tool - Image editing and generation with Gemini 3 Pro Image.

Operations:
- edit: Background removal, extraction from groups, enhancement, reframing
- generate: Lifestyle shots, studio shots, scene composites

Architecture: Atomic tool with structured Pydantic input/output.

Storage Architecture:
    Generated images are uploaded to Supabase pending/ folder for persistence
    across Vercel serverless invocations. Images await HITL approval before
    being moved to products/ folder via WriteIntent.
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
import platform
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Protocol, TypeVar

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, StructuredTool
from PIL import Image

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.tool_error_handler import (
    build_agent_error_response,
    build_success_response,
)
from autifyme_agents.tools.image_studio.schemas import (
    BackgroundSpec,
    EnhancementSpec,
    ExtractionSpec,
    FocusRegionSpec,
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

T = TypeVar("T")


class StorageUploader(Protocol):
    """Minimal interface for storage upload capability."""

    async def upload_to_pending(
        self,
        file_bytes: bytes,
        thread_id: str,
        filename: str,
        content_type: str,
        bucket: str = "assets",
    ) -> dict[str, Any]:
        """Upload to pending folder."""
        ...


# Module-level storage reference (set by tool factory)
_storage_client: StorageUploader | None = None


def _set_storage_client(storage: StorageUploader | None) -> None:
    """Set the storage client for pending uploads."""
    global _storage_client
    _storage_client = storage

logger = logging.getLogger(__name__)

# Use same temp directory as WhatsApp media downloads
if platform.system() == "Windows":
    MEDIA_DIR = Path(tempfile.gettempdir()) / "media_downloads"
else:
    MEDIA_DIR = Path("/tmp/media_downloads")
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

MAX_DIMENSION = 2048
JPEG_QUALITY = 85
GEMINI_3_IMAGE_MODEL = "gemini-3-pro-image-preview"

# Professional product photography system prompt for the image generation model
TOOL_SYSTEM_PROMPT = """You are a master commercial photographer whose work appears in Vogue, Apple campaigns, and luxury brand catalogs.

EXECUTE THE CREATIVE DIRECTION - The instruction is your brief. Honor it precisely.

LIGHT IS EVERYTHING:
- Light reveals form, texture, and material truth
- Specular highlights define surface quality - controlled, never blown
- Shadows create dimension - density appropriate to mood
- Rim light separates subject from background when needed
- Color temperature serves the story - warm for organic, cool for tech

MATERIAL TRUTH:
- Glass: Internal caustics, edge refraction, transparency depth - never flat
- Metal: Gradient reflections, micro-texture, controlled specularity
- Fabric: Weave texture, drape shadows, fiber detail at edges
- Plastic: Surface sheen gradient, translucency where present, no fake shine
- Wood: Grain direction, tonal variation, natural matte quality
- Ceramic/Stone: Subtle surface texture, weight impression, matte-to-satin range

COMPOSITION MASTERY:
- Negative space is intentional - it breathes or it frames
- Product placement follows visual weight principles
- Camera angle implies relationship - hero angle elevates, eye-level connects
- Edge treatment: seamless fade, sharp cut, or natural shadow - match the intent

TECHNICAL PRECISION:
- Focus: Tack sharp on hero details, natural falloff where specified
- Color: Accurate to source, grade only as directed
- Edges: Surgical extraction OR natural environmental blend - never between
- Scale: Product proportions sacred - no distortion

OUTPUT: Every image must be immediately publishable. No "almost there." This is the final frame."""


# =============================================================================
# LLM Helper
# =============================================================================


def _get_gemini3_image_llm(output_spec: OutputSpec | None = None) -> BaseChatModel:
    """Get Gemini 3 Pro Image LLM with proper configuration."""
    aspect_ratio = output_spec.aspect_ratio if output_spec else "1:1"
    if aspect_ratio == "original":
        aspect_ratio = "1:1"  # Fallback for generation
    image_size = output_spec.size if output_spec else "1K"

    return get_llm(
        provider="google",
        model=GEMINI_3_IMAGE_MODEL,
        response_modalities=["TEXT", "IMAGE"],
        image_aspect_ratio=aspect_ratio,
        image_size=image_size,
        temperature=0.3,
    )


# =============================================================================
# Image Utilities
# =============================================================================


def _load_and_encode_image(image_path: str) -> tuple[str, str]:
    """Load image from storage_path/URL/local path, resize if needed, encode to base64.

    Args:
        image_path: storage_path, URL, or local file path
    """
    # Import here to avoid circular dependency
    from autifyme_agents.core.storage_utils import build_storage_url, is_storage_path

    # Convert storage_path to URL if needed
    if is_storage_path(image_path):
        image_path = build_storage_url(image_path)

    # Handle URLs
    img: Image.Image  # Type hint: resize/convert returns Image.Image, not ImageFile
    if image_path.startswith(("http://", "https://")):
        import httpx

        response = httpx.get(image_path, timeout=60)
        response.raise_for_status()
        img = Image.open(io.BytesIO(response.content))
    else:
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        img = Image.open(path)

    try:
        with img:
            fmt = img.format or "JPEG"
            mime_type = f"image/{fmt.lower()}"

            if img.mode in ("RGBA", "LA", "P"):
                rgb_img = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "RGBA":
                    rgb_img.paste(img, mask=img.split()[-1])
                else:
                    rgb_img.paste(img)
                img = rgb_img
                fmt = "JPEG"
                mime_type = "image/jpeg"

            width, height = img.size
            if max(width, height) > MAX_DIMENSION:
                if width > height:
                    new_width = MAX_DIMENSION
                    new_height = int(height * (MAX_DIMENSION / width))
                else:
                    new_height = MAX_DIMENSION
                    new_width = int(width * (MAX_DIMENSION / height))
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

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
    description: str | None = None,
    thread_id: str | None = None,
) -> tuple[Path, ImageMetadata, str | None]:
    """Save base64 image data to temp file and optionally upload to pending.

    Args:
        base64_data: Base64-encoded image data (may include data URI prefix)
        operation: Operation type for filename
        output_spec: Output specification for format/size
        description: Optional description for logging
        thread_id: Optional thread ID for pending upload organization

    Returns:
        Tuple of (local_path, metadata, storage_path)
        storage_path is None if upload not performed
    """
    if "," in base64_data:
        base64_data = base64_data.split(",", 1)[1]

    image_bytes = base64.b64decode(base64_data)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    extension = output_spec.format.lower()
    filename = f"{timestamp}_{operation}_{unique_id}.{extension}"
    file_path = MEDIA_DIR / filename

    file_path.write_bytes(image_bytes)

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
        "Saved image to %s",
        file_path,
        extra={"width": width, "height": height, "size_bytes": len(image_bytes)},
    )

    # Upload to Supabase pending if storage and thread_id available
    storage_path: str | None = None

    if _storage_client is not None and thread_id is not None:
        content_type_map = {
            "png": "image/png",
            "jpeg": "image/jpeg",
            "jpg": "image/jpeg",
            "webp": "image/webp",
        }
        content_type = content_type_map.get(extension, "image/png")

        try:
            try:
                asyncio.get_running_loop()
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        _storage_client.upload_to_pending(
                            file_bytes=image_bytes,
                            thread_id=thread_id,
                            filename=filename,
                            content_type=content_type,
                        )
                    )
                    upload_result = future.result()
            except RuntimeError:
                upload_result = asyncio.run(
                    _storage_client.upload_to_pending(
                        file_bytes=image_bytes,
                        thread_id=thread_id,
                        filename=filename,
                        content_type=content_type,
                    )
                )

            storage_path = upload_result["storage_path"]
            logger.info(
                "Uploaded image to pending storage",
                extra={"storage_path": storage_path, "thread_id": thread_id},
            )
        except Exception as upload_error:
            logger.warning(
                f"Failed to upload to pending storage: {upload_error}",
                extra={"file_name": filename, "thread_id": thread_id},
            )

    return file_path, metadata, storage_path


def _extract_image_from_response(response: Any) -> str | None:
    """Extract base64 image data from Gemini response.

    Gemini 3 returns images at response.content[0]["image_url"]["url"] as data URI.
    """
    content = getattr(response, "content", None)
    if isinstance(content, list) and len(content) > 0:
        part = content[0]
        if isinstance(part, dict) and "image_url" in part:
            url = part["image_url"].get("url", "")
            if url.startswith("data:"):
                return str(url)

    logger.warning(
        "No image in response. content_type=%s, content_len=%s",
        type(content).__name__,
        len(content) if isinstance(content, list) else "N/A",
    )
    return None


# =============================================================================
# Prompt Builders
# =============================================================================


def _build_edit_prompt(input_spec: ImageStudioInput) -> str:
    """Build comprehensive edit prompt."""
    instructions = ["Edit this product image with the following specifications:"]

    # Custom instruction takes priority
    if input_spec.custom_instruction:
        instructions.append(f"\nCUSTOM INSTRUCTION: {input_spec.custom_instruction}")

    # Extraction from group photo
    if input_spec.extraction:
        ex = input_spec.extraction
        extraction_inst = f"EXTRACT PRODUCT: Isolate and extract '{ex.target_description}'"
        if ex.position_hint:
            extraction_inst += f" (hint: {ex.position_hint} side of image)"
        if ex.isolate:
            extraction_inst += ". Remove ALL other products from the image."
        if ex.clean_edges:
            extraction_inst += " Clean up edges for professional appearance."
        instructions.append(extraction_inst)

    # Focus/crop region
    if input_spec.focus:
        fo = input_spec.focus
        if fo.type == "custom" and fo.custom_focus:
            instructions.append(f"FOCUS: Crop/zoom to focus on {fo.custom_focus}")
        elif fo.type == "product":
            instructions.append("FOCUS: Crop to focus on the main product, remove excess background")
        elif fo.type == "label":
            instructions.append("FOCUS: Crop to focus on product label/branding")
        if fo.zoom_level != 1.0:
            instructions.append(f"ZOOM: Apply {fo.zoom_level}x zoom")
        if fo.position:
            instructions.append(f"FOCUS POSITION: Emphasize {fo.position} area of image")

    # Background
    if input_spec.background:
        bg = input_spec.background
        if bg.type == "remove" or bg.type == "transparent":
            instructions.append("BACKGROUND: Remove background completely (transparent PNG)")
        elif bg.type == "solid":
            instructions.append(f"BACKGROUND: Replace with solid {bg.color} color")
        elif bg.type == "gradient":
            instructions.append(f"BACKGROUND: Apply gradient from {bg.color} to {bg.gradient_end}")
        elif bg.type == "blur":
            instructions.append(f"BACKGROUND: Blur background ({bg.blur_strength} strength)")
        elif bg.type == "scene" and bg.scene_description:
            instructions.append(f"BACKGROUND: Generate new background scene: {bg.scene_description}")

    # Lighting
    if input_spec.lighting:
        lt = input_spec.lighting
        instructions.append(
            f"LIGHTING: Apply {lt.type} lighting from {lt.direction}, "
            f"intensity={lt.intensity}, temperature={lt.color_temperature}, shadows={lt.shadows}"
        )

    # Framing
    if input_spec.framing:
        fr = input_spec.framing
        framing_inst = f"FRAMING: Product coverage {fr.product_coverage_percent}%, aligned {fr.alignment}"
        if fr.angle != "front":
            framing_inst += f", angle={fr.angle}"
        if fr.padding_percent > 0:
            framing_inst += f", padding={fr.padding_percent}%"
        if fr.crop_to_product:
            framing_inst += ", crop tightly to product"
        instructions.append(framing_inst)

    # Enhancement
    if input_spec.enhancement:
        en = input_spec.enhancement
        enhancements = []
        if en.sharpness != "none":
            enhancements.append(f"sharpness={en.sharpness}")
        if en.contrast != "none":
            enhancements.append(f"contrast={en.contrast}")
        if en.saturation != "none":
            enhancements.append(f"saturation={en.saturation}")
        if en.brightness != "none":
            enhancements.append(f"brightness={en.brightness}")
        if en.denoise:
            enhancements.append("denoise")
        if en.upscale != "none":
            enhancements.append(f"upscale={en.upscale}")
        if en.color_correction:
            enhancements.append("auto_color_correction")
        if en.remove_blemishes:
            enhancements.append("remove_blemishes")
        if en.restore_details:
            enhancements.append("AI_restore_details")
        if enhancements:
            instructions.append(f"ENHANCE: Apply {', '.join(enhancements)}")

    # Output specs
    out = input_spec.output
    instructions.append(
        f"OUTPUT: {out.size} image, aspect ratio {out.aspect_ratio}, format {out.format}"
    )

    return "\n".join(instructions)


def _build_generate_prompt(input_spec: ImageStudioInput) -> str:
    """Build comprehensive generation prompt."""
    instructions = []

    # Custom instruction
    if input_spec.custom_instruction:
        instructions.append(f"INSTRUCTION: {input_spec.custom_instruction}")

    # Scene specification
    if input_spec.scene:
        sc = input_spec.scene
        if sc.environment == "custom" and sc.custom_description:
            instructions.append(f"SCENE: {sc.custom_description}")
        else:
            instructions.append(f"""SCENE:
- Environment: {sc.environment}
- Style: {sc.style}
- Mood: {sc.mood}
- Time of day: {sc.time_of_day}""")

    # Product placement
    if input_spec.placement:
        pl = input_spec.placement
        instructions.append(f"""PRODUCT PLACEMENT:
- Position: {pl.position}
- Scale: {pl.scale}
- Surface: {pl.surface or 'appropriate for scene'}
- Angle: {pl.angle}
- Shadow: {'realistic shadow' if pl.shadow else 'no shadow'}""")

    # Lighting
    if input_spec.lighting:
        lt = input_spec.lighting
        instructions.append(
            f"LIGHTING: {lt.type} from {lt.direction}, {lt.intensity} intensity, "
            f"{lt.color_temperature} temperature, {lt.shadows} shadows"
        )

    # Default if no scene specified
    if not instructions:
        instructions.append(
            "Generate a professional product photograph with clean, well-lit studio background."
        )

    # Core requirement
    instructions.append(
        "\nThe product from the source image must be seamlessly integrated. "
        "Maintain exact product details, proportions, and quality."
    )

    # Output specs
    out = input_spec.output
    instructions.append(f"\nOUTPUT: {out.size}, {out.aspect_ratio} aspect ratio, {out.format}")

    return "\n".join(instructions)


# =============================================================================
# Operation Handlers
# =============================================================================


def _handle_edit(input_spec: ImageStudioInput) -> ImageStudioOutput:
    """Handle edit operation including extraction and enhancement."""
    if not input_spec.source_image:
        return ImageStudioOutput(
            success=False,
            operation=ImageOperation.EDIT,
            error="source_image required for edit operation",
            error_code=ImageStudioErrorCode.INVALID_INPUT,
        )

    try:
        llm = _get_gemini3_image_llm(output_spec=input_spec.output)
        prompt = _build_edit_prompt(input_spec)

        # Build content with source image first
        source_uri, _ = _load_and_encode_image(input_spec.source_image)
        content: list[dict[str, Any]] = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": source_uri}},
        ]

        # Add reference images (limit to 14 to stay within API limits)
        for ref_path in input_spec.reference_images[:14]:
            try:
                ref_uri, _ = _load_and_encode_image(ref_path)
                content.append({"type": "image_url", "image_url": {"url": ref_uri}})
            except Exception as e:
                logger.warning("Failed to load reference image %s: %s", ref_path, e)

        messages = [
            {"role": "system", "content": TOOL_SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ]

        response = llm.invoke(messages)  # type: ignore[arg-type]

        # Extract image using helper function
        image_data = _extract_image_from_response(response)

        if not image_data:
            return ImageStudioOutput(
                success=False,
                operation=ImageOperation.EDIT,
                error="No image returned from API - check logs for response structure",
                error_code=ImageStudioErrorCode.API_ERROR,
            )

        # Generate description based on operation
        description = "Edited image"
        if input_spec.extraction:
            description = f"Extracted: {input_spec.extraction.target_description}"
        elif input_spec.background and input_spec.background.type in ("transparent", "remove"):
            description = "Background removed"

        file_path, metadata, storage_path = _save_base64_image(
            image_data, "edit", input_spec.output, description, input_spec.thread_id
        )

        output_variant = OutputVariant(
            variant="master",
            path=str(file_path),
            preview_path=str(file_path),
            metadata=metadata,
            description=description,
            storage_path=storage_path,
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
    """Handle generate operation for lifestyle and studio shots."""
    try:
        llm = _get_gemini3_image_llm(output_spec=input_spec.output)
        prompt = _build_generate_prompt(input_spec)

        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]

        if input_spec.source_image:
            image_uri, _ = _load_and_encode_image(input_spec.source_image)
            content.append({"type": "image_url", "image_url": {"url": image_uri}})

        for ref_path in input_spec.reference_images[:14]:
            try:
                ref_uri, _ = _load_and_encode_image(ref_path)
                content.append({"type": "image_url", "image_url": {"url": ref_uri}})
            except Exception as e:
                logger.warning("Failed to load reference image %s: %s", ref_path, e)

        messages = [
            {"role": "system", "content": TOOL_SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ]
        response = llm.invoke(messages)  # type: ignore[arg-type]

        # Extract image using helper function
        image_data = _extract_image_from_response(response)

        if not image_data:
            return ImageStudioOutput(
                success=False,
                operation=ImageOperation.GENERATE,
                error="No image returned from API - check logs for response structure",
                error_code=ImageStudioErrorCode.API_ERROR,
            )

        description = "Generated image"
        if input_spec.scene:
            description = f"Lifestyle: {input_spec.scene.environment}"

        file_path, metadata, storage_path = _save_base64_image(
            image_data, "generate", input_spec.output, description, input_spec.thread_id
        )

        output_variant = OutputVariant(
            variant="master",
            path=str(file_path),
            preview_path=str(file_path),
            metadata=metadata,
            description=description,
            storage_path=storage_path,
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
    thread_id: str | None = None,
    custom_instruction: str | None = None,
    background: dict[str, Any] | None = None,
    lighting: dict[str, Any] | None = None,
    framing: dict[str, Any] | None = None,
    enhancement: dict[str, Any] | None = None,
    scene: dict[str, Any] | None = None,
    placement: dict[str, Any] | None = None,
    extraction: dict[str, Any] | None = None,
    focus: dict[str, Any] | None = None,
    output: dict[str, Any] | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Image Studio tool implementation.

    thread_id is automatically injected from RunnableConfig via InjectedToolArg.
    This enables automatic cloud storage persistence without requiring the
    LLM to explicitly pass thread_id.
    """
    # Inject thread_id from config if not explicitly provided
    if thread_id is None and config is not None:
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id")
        if thread_id:
            logger.debug(
                "Injected thread_id from RunnableConfig",
                extra={"thread_id": thread_id}
            )

    try:
        def _maybe_convert(value: Any, model_class: type[T]) -> T | None:
            if value is None:
                return None
            if isinstance(value, model_class):
                return value
            if isinstance(value, dict):
                return model_class(**value)
            return value  # type: ignore[no-any-return]

        input_spec = ImageStudioInput(
            operation=ImageOperation(operation) if isinstance(operation, str) else operation,
            source_image=source_image,
            reference_images=reference_images or [],
            thread_id=thread_id,
            custom_instruction=custom_instruction,
            background=_maybe_convert(background, BackgroundSpec),
            lighting=_maybe_convert(lighting, LightingSpec),
            framing=_maybe_convert(framing, FramingSpec),
            enhancement=_maybe_convert(enhancement, EnhancementSpec),
            scene=_maybe_convert(scene, SceneSpec),
            placement=_maybe_convert(placement, ProductPlacement),
            extraction=_maybe_convert(extraction, ExtractionSpec),
            focus=_maybe_convert(focus, FocusRegionSpec),
            output=_maybe_convert(output, OutputSpec) or OutputSpec(),
        )

        if input_spec.operation == ImageOperation.EDIT:
            result = _handle_edit(input_spec)
        elif input_spec.operation == ImageOperation.GENERATE:
            result = _handle_generate(input_spec)
        else:  # Defensive: future enum values
            result = ImageStudioOutput(  # type: ignore[unreachable]
                success=False,
                operation=input_spec.operation,
                error=f"Unknown operation: {input_spec.operation}",
                error_code=ImageStudioErrorCode.INVALID_INPUT,
            )

        if result.success:
            return build_success_response(result.model_dump())
        else:
            return {
                "success": False,
                "error": result.error,
                "error_code": result.error_code,
                "operation": result.operation.value,
                "warnings": result.warnings,
                "next_steps": result.next_steps,
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


def create_image_studio_tool(storage: StorageUploader | None = None) -> StructuredTool:
    """Create the Image Studio tool.

    Args:
        storage: Optional storage client for persisting images to Supabase pending/

    CAPABILITIES (Gemini 3 Pro Image):

    EDIT:
    - Background: Remove (transparent), solid color, gradient, blur, generate scene
    - Extract product: Isolate specific product from group photo
    - Enhance: Sharpen, denoise, upscale 2x/4x, color correct, remove blemishes
    - Reframe: Crop, zoom, change composition, adjust padding

    GENERATE:
    - Lifestyle shots: Product in realistic scenes (kitchen, office, retail)
    - Studio shots: Clean professional backgrounds
    - Custom scenes: Describe any environment

    STORAGE:
    - Generated images are uploaded to pending/{thread_id}/ for persistence
    - storage_path is included in output for write_data
    """
    # Set module-level storage client
    _set_storage_client(storage)

    return StructuredTool.from_function(
        func=_image_studio_impl,
        name="image_studio",
        description="""Edit and generate product images with Gemini 3 Pro Image.

OPERATIONS:

1. EDIT - Modify image: extract, background, enhance
   - EXTRACT: Isolate specific product from group ("the red jar on left")
   - BACKGROUND: Remove (transparent), solid, gradient, blur, scene
   - ENHANCE: Sharpen, denoise, upscale 2x/4x, color correct
   - REFRAME: Crop, zoom, adjust composition

2. GENERATE - Create new images
   - LIFESTYLE: Product in scenes (kitchen, office, outdoor)
   - STUDIO: Clean professional backgrounds
   - CUSTOM: Any scene via custom_instruction

KEY PARAMETERS:
- custom_instruction: Free-form text for complex operations
- extraction: {target_description, position_hint, isolate}
- background: {type: transparent|solid|gradient|blur|scene}
- enhancement: {sharpness, denoise, upscale, color_correction}
- scene: {environment, style, mood} for lifestyle generation""",
        args_schema=ImageStudioInput,
        return_direct=False,
    )
