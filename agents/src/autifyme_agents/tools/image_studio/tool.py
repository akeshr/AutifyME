"""Image Studio Tool - Image processing with Gemini 3 Pro Image.

Intelligence-First Architecture:
- Labeled images (specialist references by label in instructions)
- Structured specs guide completeness, all accept free-form strings
- Model reasons about what to do from specs and labels

The fundamental operation: prompt + labeled images -> new image
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
    CompositionSpec,
    CustomSpec,
    EnhancementSpec,
    ExtractionSpec,
    FocusSpec,
    ImageInput,
    ImageMetadata,
    ImageStudioErrorCode,
    ImageStudioInput,
    ImageStudioOutput,
    LightingSpec,
    MaterialTreatmentSpec,
    OutputSpec,
    OutputVariant,
    ProductPlacementSpec,
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
GEMINI_3_IMAGE_MODEL = "gemini-2.5-flash-image"

# Professional product photography system prompt
TOOL_SYSTEM_PROMPT = """You are a master commercial photographer whose work appears in Vogue, Apple campaigns, and luxury brand catalogs.

EXECUTE THE CREATIVE DIRECTION - The instruction is your brief. Honor it precisely.

IMAGES ARE LABELED - Use the labels to understand each image's role:
- [product], [source] = the main product to feature
- [style_ref] = lighting/mood reference - match its atmosphere
- [background] = background/scene reference
- [product_variant] = additional product for family shots
- The specialist will explain how to use each label

SHARPNESS IS PARAMOUNT - NON-NEGOTIABLE:
- ALL outputs must be TACK SHARP with MAXIMUM detail clarity
- No blur, no soft focus, no fuzzy edges anywhere
- Text, patterns, character prints, logos must be CRISP and LEGIBLE
- High-frequency details preserved at full resolution
- Product edges razor-sharp - this is a premium catalog, not a phone screenshot

WHEN EXTRACTING FROM [source] - PRODUCT IDENTITY IS SACRED:
- EXACT colors - match [source] precisely, do not interpret or shift
- Character artwork/prints/logos - reproduce exactly as shown in [source]
- Product shape/proportions - no distortion, no creative reinterpretation
- This is THEIR product - it must look like THEIR product, not your interpretation
- You ENHANCE presentation (lighting, background, sharpness) but PRESERVE identity

WHEN GENERATING SCENES - CREATIVE EXCELLENCE:
- Honor the scene/placement/lighting specs provided
- Product must look natural in the environment
- Lighting must be physically plausible and beautiful
- Match [style_ref] mood/atmosphere when provided

LIGHT IS EVERYTHING:
- Light reveals form, texture, and material truth
- Specular highlights define surface quality - controlled, never blown
- Shadows create dimension - density appropriate to mood
- Color temperature serves the story

MATERIAL TRUTH - RENDER EACH CORRECTLY:
- Glass: Internal caustics, edge refraction, transparency depth - never flat
- Metal: Gradient reflections, micro-texture, controlled specularity
- Plastic: Surface sheen gradient, translucency where present, character prints SHARP
- Fabric: Weave texture, drape shadows, fiber detail at edges

TECHNICAL PRECISION:
- Focus: Tack sharp on product - entire product in focus, no soft areas
- Color: When extracting, EXACT match to source; when generating, as directed
- Edges: Surgical extraction - no halos, no remnants, no fringing, no artifacts
- Scale: Product proportions sacred - no distortion ever

OUTPUT QUALITY BAR:
- Every image immediately publishable to premium marketplace
- Sharp enough to zoom 200% and still see crisp details
- Professional studio quality even from phone photo input
- Would you put this in YOUR portfolio? If not, it's not good enough."""


# =============================================================================
# LLM Helper
# =============================================================================


def _get_gemini3_image_llm(output_spec: OutputSpec | None = None) -> BaseChatModel:
    """Get Gemini 3 Pro Image LLM with proper configuration."""
    aspect_ratio = output_spec.aspect_ratio if output_spec else "1:1"
    if aspect_ratio == "original":
        aspect_ratio = "1:1"
    image_size = output_spec.size if output_spec else "1K"

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
    """Load image from storage_path/URL/local path, resize if needed, encode to base64."""
    from autifyme_agents.core.storage_utils import build_storage_url, is_storage_path

    if is_storage_path(image_path):
        image_path = build_storage_url(image_path)

    img: Image.Image
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
    output_spec: OutputSpec,
    thread_id: str | None = None,
) -> tuple[Path, ImageMetadata, str | None]:
    """Save base64 image data to temp file and optionally upload to pending."""
    if "," in base64_data:
        base64_data = base64_data.split(",", 1)[1]

    image_bytes = base64.b64decode(base64_data)

    extension = output_spec.format.lower()

    # Use explicit filename if provided, otherwise generate unique name
    if output_spec.filename:
        # Sanitize filename (remove extension if accidentally included)
        base_name = output_spec.filename.rsplit(".", 1)[0] if "." in output_spec.filename else output_spec.filename
        filename = f"{base_name}.{extension}"
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{timestamp}_studio_{unique_id}.{extension}"

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

    logger.info("Saved image to %s", file_path, extra={"width": width, "height": height})

    # Upload to Supabase pending if storage and thread_id available
    storage_path: str | None = None

    if _storage_client is not None and thread_id is not None:
        content_type_map = {"png": "image/png", "jpeg": "image/jpeg", "webp": "image/webp"}
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
            logger.info("Uploaded to pending", extra={"storage_path": storage_path})
        except Exception as upload_error:
            logger.warning(f"Failed to upload: {upload_error}")

    return file_path, metadata, storage_path


def _extract_image_from_response(response: Any) -> str | None:
    """Extract base64 image data from Gemini response."""
    content = getattr(response, "content", None)
    if isinstance(content, list) and len(content) > 0:
        part = content[0]
        if isinstance(part, dict) and "image_url" in part:
            url = part["image_url"].get("url", "")
            if url.startswith("data:"):
                return str(url)

    logger.warning("No image in response")
    return None


# =============================================================================
# Prompt Builder - Includes labeled images
# =============================================================================


def _build_prompt(input_spec: ImageStudioInput) -> str:
    """Build JSON prompt from labeled images and structured specs.

    Architecture: Send raw JSON - LLMs parse structured data natively.
    - Images listed with labels (model knows which is which)
    - Structured specs as JSON objects
    - Only include non-None specs (clean, minimal payload)
    """
    import json

    # Build spec dict with only non-None values
    spec_dict: dict[str, Any] = {}

    # Images with labels
    if input_spec.images:
        spec_dict["images"] = [
            {"label": img.label, "index": i}
            for i, img in enumerate(input_spec.images)
        ]

    # Add each spec if present (exclude_none removes empty fields)
    if input_spec.extraction:
        spec_dict["extraction"] = input_spec.extraction.model_dump(exclude_none=True)
    if input_spec.background:
        spec_dict["background"] = input_spec.background.model_dump(exclude_none=True)
    if input_spec.lighting:
        spec_dict["lighting"] = input_spec.lighting.model_dump(exclude_none=True)
    if input_spec.scene:
        spec_dict["scene"] = input_spec.scene.model_dump(exclude_none=True)
    if input_spec.placement:
        spec_dict["placement"] = input_spec.placement.model_dump(exclude_none=True)
    if input_spec.composition:
        spec_dict["composition"] = input_spec.composition.model_dump(exclude_none=True)
    if input_spec.material_treatment:
        spec_dict["material_treatment"] = input_spec.material_treatment.model_dump(exclude_none=True)
    if input_spec.focus:
        spec_dict["focus"] = input_spec.focus.model_dump(exclude_none=True)
    if input_spec.enhancement:
        spec_dict["enhancement"] = input_spec.enhancement.model_dump(exclude_none=True)
    if input_spec.custom_spec:
        spec_dict["custom_spec"] = input_spec.custom_spec.model_dump(exclude_none=True)
    if input_spec.creative_direction:
        spec_dict["creative_direction"] = input_spec.creative_direction

    # Output spec - tells LLM the target format/size/aspect
    spec_dict["output"] = input_spec.output.model_dump(exclude_none=True)

    return json.dumps(spec_dict, indent=2)


# =============================================================================
# Single Unified Handler
# =============================================================================


def _process_images(input_spec: ImageStudioInput) -> ImageStudioOutput:
    """Process images with Gemini 3 Pro Image.

    Model reasons about what to do from specs and image labels.
    """
    try:
        # Load and encode all labeled images
        image_uris: list[tuple[str, str]] = []  # (label, uri)
        load_errors: list[str] = []
        for img_input in input_spec.images[:15]:  # Gemini limit
            try:
                uri, _ = _load_and_encode_image(img_input.path)
                image_uris.append((img_input.label, uri))
            except Exception as e:
                error_msg = f"[{img_input.label}] {img_input.path}: {e}"
                load_errors.append(error_msg)
                logger.warning(f"Failed to load image: {error_msg}")

        # Fail if no images loaded - don't proceed without visual input
        if not image_uris:
            attempted_paths = [img.path for img in input_spec.images]
            return ImageStudioOutput(
                success=False,
                error=f"Failed to load any images. Errors: {'; '.join(load_errors)}",
                error_code=ImageStudioErrorCode.FILE_NOT_FOUND,
                warnings=[f"Attempted paths: {attempted_paths}"],
                next_steps=[
                    "Verify file paths exist in storage",
                    "Check if paths were copied correctly (LLMs can corrupt long IDs)",
                    "Use view_image tool first to confirm path works",
                ],
            )

        # Create LLM and prompt
        llm = _get_gemini3_image_llm(output_spec=input_spec.output)
        prompt = _build_prompt(input_spec)

        # Build content: prompt first, then labeled images in order
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]

        for _label, uri in image_uris:
            content.append({"type": "image_url", "image_url": {"url": uri}})

        messages = [
            {"role": "system", "content": TOOL_SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ]

        response = llm.invoke(messages)  # type: ignore[arg-type]

        # Extract image from response
        image_data = _extract_image_from_response(response)

        if not image_data:
            return ImageStudioOutput(
                success=False,
                error="No image returned from API",
                error_code=ImageStudioErrorCode.API_ERROR,
            )

        # Save result
        file_path, metadata, storage_path = _save_base64_image(
            image_data, input_spec.output, input_spec.thread_id
        )

        output_variant = OutputVariant(
            variant="master",
            path=str(file_path),
            preview_path=str(file_path),
            metadata=metadata,
            description="Generated image",
            storage_path=storage_path,
        )

        return ImageStudioOutput(success=True, outputs=[output_variant])

    except FileNotFoundError as e:
        return ImageStudioOutput(
            success=False, error=str(e), error_code=ImageStudioErrorCode.FILE_NOT_FOUND
        )
    except ValueError as e:
        return ImageStudioOutput(
            success=False, error=str(e), error_code=ImageStudioErrorCode.CORRUPT_FILE
        )
    except Exception as e:
        logger.exception("Image processing failed")
        return ImageStudioOutput(
            success=False, error=str(e), error_code=ImageStudioErrorCode.API_ERROR
        )


# =============================================================================
# Main Tool Entry Point
# =============================================================================


def _image_studio_impl(
    images: list[dict[str, str] | ImageInput] | None = None,
    background: dict[str, Any] | BackgroundSpec | None = None,
    lighting: dict[str, Any] | LightingSpec | None = None,
    composition: dict[str, Any] | CompositionSpec | None = None,
    enhancement: dict[str, Any] | EnhancementSpec | None = None,
    scene: dict[str, Any] | SceneSpec | None = None,
    placement: dict[str, Any] | ProductPlacementSpec | None = None,
    extraction: dict[str, Any] | ExtractionSpec | None = None,
    focus: dict[str, Any] | FocusSpec | None = None,
    material_treatment: dict[str, Any] | MaterialTreatmentSpec | None = None,
    custom_spec: dict[str, Any] | CustomSpec | None = None,
    creative_direction: str | None = None,
    thread_id: str | None = None,
    output: dict[str, Any] | OutputSpec | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Image Studio tool implementation.

    Args:
        images: Labeled images [{path, label}] - reference labels in your specs
        background: Background treatment specification
        lighting: Lighting configuration
        composition: Framing and composition settings
        enhancement: Image enhancement/retouching settings
        scene: Lifestyle scene settings
        placement: Product placement in scene
        extraction: Product extraction settings
        focus: Focus and depth of field settings
        material_treatment: Material-specific rendering instructions
        custom_spec: Fully open-ended creative spec for OOTB ideas
        creative_direction: Additional creative notes
        thread_id: Auto-injected from RunnableConfig
        output: Output specs (format, size, aspect_ratio)
        config: Injected config for thread_id extraction
    """
    # Inject thread_id from config if not provided
    if thread_id is None and config is not None:
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id")

    try:
        # Convert dicts to spec objects
        def _to_spec(val: Any, spec_class: type) -> Any:
            if val is None:
                return None
            if isinstance(val, spec_class):
                return val
            if isinstance(val, dict):
                return spec_class(**val)
            return val

        # Convert images list
        image_inputs: list[ImageInput] = []
        if images:
            for img in images:
                if isinstance(img, ImageInput):
                    image_inputs.append(img)
                elif isinstance(img, dict):
                    image_inputs.append(ImageInput(**img))

        input_spec = ImageStudioInput(
            images=image_inputs,
            background=_to_spec(background, BackgroundSpec),
            lighting=_to_spec(lighting, LightingSpec),
            composition=_to_spec(composition, CompositionSpec),
            enhancement=_to_spec(enhancement, EnhancementSpec),
            scene=_to_spec(scene, SceneSpec),
            placement=_to_spec(placement, ProductPlacementSpec),
            extraction=_to_spec(extraction, ExtractionSpec),
            focus=_to_spec(focus, FocusSpec),
            material_treatment=_to_spec(material_treatment, MaterialTreatmentSpec),
            custom_spec=_to_spec(custom_spec, CustomSpec),
            creative_direction=creative_direction,
            thread_id=thread_id,
            output=_to_spec(output, OutputSpec) or OutputSpec(),
        )

        result = _process_images(input_spec)

        if result.success:
            return build_success_response(result.model_dump())
        else:
            return {
                "success": False,
                "error": result.error,
                "error_code": result.error_code,
                "warnings": result.warnings,
                "next_steps": result.next_steps,
            }

    except Exception as e:
        logger.exception("Image Studio tool failed")
        return build_agent_error_response(
            exception=e,
            context={"images": images},
            fallback_type="IMAGE_STUDIO_ERROR",
            fallback_action="Image processing failed. Retry once. If fails again, continue without and inform user.",
        )


def create_image_studio_tool(storage: StorageUploader | None = None) -> StructuredTool:
    """Create the Image Studio tool.

    Intelligence-First Architecture:
    - Labeled images: Each image has a label referenced in instructions
    - Structured specs: Guide completeness, accept free-form strings
    - Model reasons about what to do from specs and labels

    STORAGE:
    - Generated images uploaded to pending/{thread_id}/
    - storage_path included in output for write_data
    """
    _set_storage_client(storage)

    return StructuredTool.from_function(
        func=_image_studio_impl,
        name="image_studio",
        description=(
            "PURPOSE: Professional image processing (Gemini 3 Pro Image) - transform user uploads into catalog-ready assets. Extract products, generate lifestyle scenes, create hero shots, compose families. Your creative studio.\n\n"
            "LABELED IMAGES ARCHITECTURE (key differentiator):\n"
            "- Each image has label: [{path: 'inbox/thread/photo.jpg', label: 'product'}]\n"
            "- Reference labels in specs: 'extract [product]', 'match [style_ref] lighting', 'place [product] on [background]'\n"
            "- Model reasons: Gemini understands specs + labeled images, decides what to do\n"
            "- Single powerful operation: prompt + labeled images -> new image\n"
            "- Common labels: 'product'/'source' (main), 'style_ref' (mood/lighting), 'background' (scene), 'product_variant' (family shots)\n"
            "- Max 15 images (Gemini constraint)\n\n"
            "USE WHEN:\n"
            "- Messy product photo: Extract clean product for catalog\n"
            "- Hero shot needed: Transform phone photo to professional image\n"
            "- Lifestyle scene: Place product in realistic environment\n"
            "- Background removal: Transparent PNG or white background\n"
            "- Family shot: Compose multiple variants together\n"
            "- Material showcase: Highlight glass clarity, metal finish, texture\n\n"
            "DON'T USE:\n"
            "- Simple viewing (use view_image)\n"
            "- When image already catalog-ready\n"
            "- Text extraction/analysis (use view_image)\n\n"
            "STRUCTURED SPECS (all optional - use what applies):\n"
            "- extraction: {target_description: 'glass jar on left in [source]', isolation: 'complete', edge_treatment: 'sharp'}\n"
            "- background: {treatment: 'transparent'/'solid_color'/'scene', color: 'white', scene_description: 'modern kitchen'}\n"
            "- lighting: {type: 'natural_window'/'studio_3point', direction: 'front'/'side', special_requirements: 'match [style_ref]'}\n"
            "- composition: {position: 'center'/'[main] center [variant] right', camera_angle: 'slight_top', negative_space: 'generous_top'}\n"
            "- enhancement: {sharpness: 'tack_sharp', color_treatment: 'vibrant'}\n"
            "- scene: {environment: 'modern_kitchen', style: 'match [style_ref]', mood: 'warm_inviting'}\n"
            "- placement: {position: 'place [product] on marble counter', scale: 'prominent'}\n"
            "- material_treatment: {primary_material: 'clear_glass', rendering_notes: 'preserve caustics'}\n"
            "- custom_spec: {instruction: 'dramatic shot with water droplets', style_reference: 'Apple product photography'}\n"
            "- creative_direction: Free-form notes ('Family shot - main hero, second supporting')\n"
            "- output: {format: 'png'/'jpeg', size: '1K'/'2K', aspect_ratio: '1:1'/'16:9'}\n\n"
            "CRITICAL:\n"
            "- images parameter REQUIRED: Min 1 labeled image, max 15\n"
            "- Labels enable composition: Model knows which image is which via labels\n"
            "- Reference labels in specs: Use [label] syntax\n"
            "- storage_path output: Use this for write_data product_images (pending/ path)\n"
            "- View before and after: view_image to see input/output before cataloging\n"
            "- Material matters: Glass, metal, plastic need different rendering (specify material_treatment)\n"
            "- One output per call: Not batch processing\n\n"
            "EXAMPLES:\n"
            "# Extract with transparent background\n"
            "image_studio(images=[{path: 'inbox/thread/photo.jpg', label: 'source'}], extraction={target_description: 'glass jar in [source]', isolation: 'complete'}, background={treatment: 'transparent'}, material_treatment={primary_material: 'clear_glass'})\n"
            "Returns: Clean extracted jar, transparent PNG, caustics preserved\n\n"
            "# Lifestyle with style reference\n"
            "image_studio(images=[{path: 'inbox/t/product.jpg', label: 'product'}, {path: 'inbox/t/mood.jpg', label: 'style_ref'}], scene={environment: 'modern kitchen', style: 'match [style_ref]'}, placement={position: 'place [product] on counter'}, lighting={type: 'natural_window', special_requirements: 'match [style_ref]'})\n"
            "Returns: Product in kitchen matching reference mood/lighting\n\n"
            "ALSO CONSIDER:\n"
            "- view_image: BEFORE image_studio - see what you're working with\n"
            "- view_image: AFTER image_studio - verify output quality before cataloging\n"
            "- write_data: Image ready? Create asset record with storage_path from output\n"
            "- Pattern: view_image (diagnose) -> image_studio (process) -> view_image (verify) -> write_data (catalog)\n\n"
            "RETURNS: Always a structured dict with success flag.\n"
            "- success=True: ImageStudioOutput fields (outputs[] with storage_path in pending/, metadata, warnings, next_steps)\n"
            "- success=False: {error, error_code, warnings, next_steps}"
        ),
        args_schema=ImageStudioInput,
        return_direct=False,
    )
