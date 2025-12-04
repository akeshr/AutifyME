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
    ImageMetadata,
    ImageOperation,
    ImageStudioErrorCode,
    ImageStudioInput,
    ImageStudioOutput,
    OutputSpec,
    OutputVariant,
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
# Prompt Builder
# =============================================================================


def _build_prompt(input_spec: ImageStudioInput) -> str:
    """Build prompt from creative direction.

    The Creative Specialist has already crafted a complete creative brief.
    We pass it directly - no translation, no enum conversion, no loss.
    """
    # Creative direction is the primary instruction
    prompt_parts = [input_spec.creative_direction]

    # Add output specs as technical requirements
    out = input_spec.output
    prompt_parts.append(
        f"\nTECHNICAL OUTPUT: {out.size} resolution, {out.aspect_ratio} aspect ratio, {out.format} format."
    )

    return "\n".join(prompt_parts)


# =============================================================================
# Operation Handlers
# =============================================================================


def _handle_edit(input_spec: ImageStudioInput) -> ImageStudioOutput:
    """Handle edit operation - pass creative direction directly to Gemini."""
    if not input_spec.source_image:
        return ImageStudioOutput(
            success=False,
            operation=ImageOperation.EDIT,
            error="source_image required for edit operation",
            error_code=ImageStudioErrorCode.INVALID_INPUT,
        )

    try:
        # Load and validate source image FIRST (before LLM creation)
        # This ensures FileNotFoundError is raised before any API calls
        source_uri, _ = _load_and_encode_image(input_spec.source_image)

        # Load reference images early too
        ref_uris: list[str] = []
        for ref_path in input_spec.reference_images[:14]:
            try:
                ref_uri, _ = _load_and_encode_image(ref_path)
                ref_uris.append(ref_uri)
            except Exception as e:
                logger.warning("Failed to load reference image %s: %s", ref_path, e)

        # Now create LLM (may require API credentials)
        llm = _get_gemini3_image_llm(output_spec=input_spec.output)
        prompt = _build_prompt(input_spec)

        # Build content with pre-loaded images
        content: list[dict[str, Any]] = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": source_uri}},
        ]

        # Add reference images
        for ref_uri in ref_uris:
            content.append({"type": "image_url", "image_url": {"url": ref_uri}})

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

        # Description is simply "Edited image" - creative_direction contains the details
        description = "Edited image"

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
    """Handle generate operation - pass creative direction directly to Gemini."""
    try:
        llm = _get_gemini3_image_llm(output_spec=input_spec.output)
        prompt = _build_prompt(input_spec)

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

        # Description is simply "Generated image" - creative_direction contains the details
        description = "Generated image"

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
    creative_direction: str,
    source_image: str | None = None,
    reference_images: list[str] | None = None,
    thread_id: str | None = None,
    output: dict[str, Any] | OutputSpec | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Image Studio tool implementation.

    Args:
        operation: "edit" or "generate"
        creative_direction: Complete creative brief from the specialist
        source_image: Source image storage_path (required for edit)
        reference_images: Additional reference images
        thread_id: Auto-injected from RunnableConfig
        output: Output specs (format, size, aspect_ratio)
        config: Injected config for thread_id extraction
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
        # Convert output dict to OutputSpec if needed
        output_spec = OutputSpec()
        if output is not None:
            if isinstance(output, OutputSpec):
                output_spec = output
            elif isinstance(output, dict):
                output_spec = OutputSpec(**output)

        input_spec = ImageStudioInput(
            operation=ImageOperation(operation) if isinstance(operation, str) else operation,
            source_image=source_image,
            reference_images=reference_images or [],
            creative_direction=creative_direction,
            thread_id=thread_id,
            output=output_spec,
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

    Architecture:
    - Creative Specialist writes natural language creative briefs
    - Tool passes creative_direction directly to Gemini 3 Pro Image
    - No enum restrictions, full creative expression

    STORAGE:
    - Generated images are uploaded to pending/{thread_id}/ for persistence
    - storage_path is included in output for write_data
    """
    # Set module-level storage client
    _set_storage_client(storage)

    return StructuredTool.from_function(
        func=_image_studio_impl,
        name="image_studio",
        description="""Professional image editing and generation with Gemini 3 Pro Image.

OPERATIONS:
- edit: Modify existing image (background removal, extraction, enhancement, reframing)
- generate: Create new lifestyle/studio shots from product image

KEY PARAMETER - creative_direction:
Write a complete creative brief like a professional photographer would:
- Lighting: direction, quality, temperature, shadows
- Composition: framing, product placement, coverage
- Background: type, color, scene description
- Material treatment: how to handle glass, metal, fabric, etc.
- Technical: sharpness, color accuracy, edge treatment

EXAMPLES:
- "Extract glass jar, pure white background, soft studio lighting from 45-degrees, rim light for glass edge definition, 80% frame coverage"
- "Modern kitchen scene, morning light through window, product on marble counter with herbs, warm editorial feel"
- "Isolate red 500ml variant from left side, transparent background, surgical edge treatment"

OUTPUT: Returns storage_path in pending/ for write_data.""",
        args_schema=ImageStudioInput,
        return_direct=False,
    )
