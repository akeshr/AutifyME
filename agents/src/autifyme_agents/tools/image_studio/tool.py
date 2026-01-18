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
from typing import Any, Protocol, TypeVar

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import StructuredTool
from PIL import Image

from autifyme_agents.core.execution_context import get_thread_id, to_user_path
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
    FidelitySpec,
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
GEMINI_3_IMAGE_MODEL = "gemini-3-pro-image-preview"

# Tool system prompt - focused on execution, domain doctrine lives in protocols
TOOL_SYSTEM_PROMPT = """You are a master product photographer and retoucher. Execute creative direction with precision.

INPUT: JSON specs + labeled images. Read ALL specs carefully before generating.

=== LABELED IMAGES ===
[source], [product] = THE ACTUAL PRODUCT - study carefully, this is your reference
[style_ref], [mood_ref] = ATMOSPHERE REFERENCE - match lighting/mood, not the products shown
[background] = Scene/environment to place product in
[variant], [product_2] = Additional products for family/group shots

No source? Generate from specs description.

=== CORE PRINCIPLE: PRESERVE IDENTITY, FIX PHOTOGRAPHY ===
Source images are often messy phone photos. Your job: PRESERVE product identity, FIX photography problems.

PRESERVE (real product properties - these define what the product IS):
- Material: transparency level, finish (matte/glossy/satin), texture, surface quality
- Colors: actual product colors (ignore color cast from bad lighting)
- Artwork: exact labels, logos, patterns, text - position, size, AND content
- Shape: true proportions and silhouette (ignore lens distortion)
- Features: caps, lids, handles, spouts, closures - all distinguishing elements

FIX (photography problems - these are NOT product properties):
- Bad lighting -> Professional studio lighting
- Cluttered background -> Clean background per specs
- Color cast -> True product colors
- Blur/softness -> Tack sharp
- Poor exposure -> Proper exposure
- Harsh shadows -> Soft, natural shadows

THE IDENTITY TEST: Would the product owner recognize THIS EXACT PRODUCT?
- Same material feel (transparent stays transparent, matte stays matte)
- Same colors (not "similar" - SAME)
- Same artwork (exact labels, not "readable but different")
- Same shape (exact silhouette, not "close enough")

=== SPEC REFERENCE ===

"extraction" - WHAT TO EXTRACT FROM SOURCE
  target_description: Overall task description
  targets[]: Array with target_bbox (coordinates) and target_image_label
  -> Use bbox coordinates when provided for precise targeting

"fidelity" - IDENTITY PRESERVATION PRIORITIES
  preserve_colors: Match source colors exactly (True) or specific instructions
  preserve_artwork: Match labels/logos exactly - includes position and content
  preserve_shape: Maintain exact proportions and silhouette
  hero_features[]: Key features to emphasize (e.g., "blue cap", "transparency depth")
  fidelity_notes: Additional identity requirements (e.g., "uniform transparency")
  -> When fidelity is heavy, identity trumps all other considerations

"material_treatment" - HOW TO RENDER THE MATERIAL
  primary_material: "glossy PET", "matte plastic", "brushed metal", etc.
  rendering_notes: Specific instructions (e.g., "uniform tint, no dark bands")
  transparency: For transparent materials - clarity_percentage (90%+ sharp, 50% soft), tint, frost_percentage, wall_thickness_effect ("thick_darkens" needs "uniform tint" in notes), contents_state, contents_description
  -> Material properties ARE identity - transparent must stay transparent

"background" - WHAT'S BEHIND THE PRODUCT
  treatment: "solid_color", "transparent", "gradient", "scene"
  color: Background color when solid
  -> Choose contrast: dark product = light background, light product = gray (not white)

"lighting" - HOW TO LIGHT THE SCENE
  type: "studio_3point", "natural", "dramatic", "soft", "rim"
  direction: Where key light comes from
  quality: "soft" (diffused), "hard" (defined shadows)
  shadows: Shadow treatment instructions
  -> Lighting FIXES photography, doesn't change product identity

"composition" - HOW TO FRAME THE SHOT
  camera_angle: "eye-level", "slight_top", "overhead", "three-quarter"
  product_coverage: Percentage of frame product fills (e.g., "80%")
  position: Where in frame ("center", "left-third", "bottom-weighted")
  -> For catalog: consistent angle across variants is critical

"enhancement" - POST-PROCESSING
  sharpness: "high", "moderate", "subtle"
  contrast: Level of contrast adjustment
  color_treatment: Any color grading
  -> Enhancement FIXES photography quality, never changes product identity

"focus" - DEPTH OF FIELD
  type: "deep" (everything sharp), "shallow" (selective focus)
  subject: What to keep sharp
  -> Catalog = deep (all sharp), Lifestyle = can be shallow

"scene" - LIFESTYLE ENVIRONMENT (when generating scenes)
  environment: Scene description
  mood: Atmosphere/feeling
  -> Product identity preserved, scene is creative

"placement" - WHERE PRODUCT GOES IN SCENE
  position: Location in generated scene
  -> Product must look naturally placed, grounded

"output" - TECHNICAL SPECIFICATIONS
  filename: Output path
  aspect_ratio: "1:1", "4:5", "16:9", etc.
  size: "1K", "2K"

"custom_spec" / "creative_direction" - FREE-FORM NOTES
  instruction: Any additional creative direction
  -> Read carefully, may contain critical requirements

=== WORK TYPE GUIDANCE ===

CATALOG/HERO SHOTS (fidelity-heavy):
- Identity is PARAMOUNT - owner must recognize exact product
- All features sharp and legible at 200% zoom
- Clean background, professional lighting
- Contact shadow for grounding
- Consistent style across variants

LIFESTYLE/SCENE (scene-heavy):
- Product identity still preserved
- Creative freedom in environment
- Product naturally integrated, not floating
- Mood/atmosphere from style reference

BATCH/VARIANTS:
- Consistency across all outputs is critical
- Same angle, framing, lighting direction
- Same treatment of equivalent features

=== QUALITY STANDARDS ===
- Sharp at 200% zoom - labels fully legible
- Professional studio quality
- Products grounded with contact shadows (not floating)
- Clean edges, no artifacts or halos
- Photorealistic - would a photographer believe this came from a real shoot?

=== PITFALLS TO AVOID ===
- Making transparent materials opaque (transparency IS identity)
- Changing matte finish to glossy or vice versa (finish IS identity)
- Generating "similar" labels instead of exact artwork (artwork IS identity)
- Adding caustics/sheen when asked for "realistic" (causes artifacts)
- Dark bands at bottle neck/base (use "uniform tint" when thick_darkens)
- Floating products (always ground with shadow)
- Inconsistent style across batch variants"""


# =============================================================================
# LLM Helper
# =============================================================================


def _get_gemini3_image_llm(
    output_spec: OutputSpec | None = None,
    temperature: float | None = None,
    seed: int | None = None,
) -> BaseChatModel:
    """Get Gemini 3 Pro Image LLM with proper configuration.

    Args:
        output_spec: Output specifications (aspect ratio, size)
        temperature: Controls randomness. Default 0.7 for catalog consistency.
            Lower (0.3-0.5) for batch variants. Higher (1.0+) for creative exploration.
        seed: Seed for reproducibility (best-effort). Use same seed across batch.
    """
    aspect_ratio = output_spec.aspect_ratio if output_spec else "1:1"
    if aspect_ratio == "original":
        aspect_ratio = "1:1"
    image_size = output_spec.size if output_spec else "1K"

    # Default temperature 0.7 for catalog work - balanced consistency
    # Override Gemini 3's default of 1.0 which causes high variance
    effective_temperature = temperature if temperature is not None else 0.4
    print(f"Using Gemini 3 Pro Image temperature: {effective_temperature}")

    return get_llm(
        provider="google",
        model=GEMINI_3_IMAGE_MODEL,
        response_modalities=["TEXT", "IMAGE"],
        image_aspect_ratio=aspect_ratio,
        image_size=image_size,
        temperature=0.8,
        seed=seed,
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
) -> tuple[Path, ImageMetadata, str | None]:
    """Save base64 image data to temp file and optionally upload to pending.

    Gets thread_id from execution context (invisible to LLM).
    """
    # Get thread_id from execution context
    thread_id = get_thread_id()

    if "," in base64_data:
        base64_data = base64_data.split(",", 1)[1]

    image_bytes = base64.b64decode(base64_data)

    extension = output_spec.format.lower()

    # Use explicit filename if provided, otherwise generate unique name
    if output_spec.filename:
        # Sanitize filename (remove extension if accidentally included)
        base_name = (
            output_spec.filename.rsplit(".", 1)[0]
            if "." in output_spec.filename
            else output_spec.filename
        )
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

    # Log why upload might be skipped
    if _storage_client is None:
        logger.warning("Upload skipped: storage client not configured")
    elif thread_id is None:
        logger.warning("Upload skipped: thread_id not available in execution context")

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
                        ),
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

            internal_path = upload_result["storage_path"]
            storage_path = to_user_path(internal_path)  # LLM sees clean path
            logger.info(
                "Uploaded to pending",
                extra={"user_path": storage_path, "internal_path": internal_path},
            )

            # Surface versioning info to agent if duplicate was detected
            if upload_result.get("duplicate_detected"):
                metadata.duplicate_detected = True
                metadata.original_filename = upload_result.get("original_filename")
                metadata.actual_filename = upload_result.get("filename")
                metadata.storage_warning = upload_result.get("warning")
        except Exception as upload_error:
            logger.warning(f"Failed to upload: {upload_error}")

    return file_path, metadata, storage_path


def _extract_image_from_response(response: Any) -> str | None:
    """Extract base64 image data from Gemini response.

    Gemini may return mixed content: ['text...', {'type': 'image_url', ...}]
    We need to search ALL parts, not just the first one.
    """
    content = getattr(response, "content", None)
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and "image_url" in part:
                url = part["image_url"].get("url", "")
                if url.startswith("data:"):
                    return str(url)
            # Also check for type: image_url format
            if isinstance(part, dict) and part.get("type") == "image_url":
                image_url = part.get("image_url", {})
                url = image_url.get("url", "") if isinstance(image_url, dict) else ""
                if url.startswith("data:"):
                    return str(url)

    logger.warning("No image in response content: %s", type(content))
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
            {"label": img.label, "index": i} for i, img in enumerate(input_spec.images)
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
        spec_dict["material_treatment"] = input_spec.material_treatment.model_dump(
            exclude_none=True
        )
    if input_spec.fidelity:
        spec_dict["fidelity"] = input_spec.fidelity.model_dump(exclude_none=True)
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
        llm = _get_gemini3_image_llm(
            output_spec=input_spec.output,
            temperature=input_spec.temperature,
            seed=input_spec.seed,
        )
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

        # Save result (thread_id obtained from execution context inside _save_base64_image)
        file_path, metadata, storage_path = _save_base64_image(image_data, input_spec.output)

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
    fidelity: dict[str, Any] | FidelitySpec | None = None,
    custom_spec: dict[str, Any] | CustomSpec | None = None,
    creative_direction: str | None = None,
    output: dict[str, Any] | OutputSpec | None = None,
    temperature: float | None = None,
    seed: int | None = None,
) -> dict[str, Any] | list[dict[str, Any]]:
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
        fidelity: CRITICAL - Product fidelity preservation requirements
        custom_spec: Fully open-ended creative spec for OOTB ideas
        creative_direction: Additional creative notes
        output: Output specs (format, size, aspect_ratio)
        temperature: Controls randomness (0.0-2.0). Default 0.7 for catalog consistency.
            Lower (0.3-0.5) for batch variants. Higher (1.0+) for creative exploration.
        seed: Seed for reproducibility (best-effort). Use same seed across batch variants.
    """
    # Get thread_id from execution context (invisible to LLM)
    thread_id = get_thread_id()

    logger.debug(
        "Image studio invoked",
        extra={
            "thread_id": thread_id,
            "storage_configured": _storage_client is not None,
        },
    )

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
            fidelity=_to_spec(fidelity, FidelitySpec),
            custom_spec=_to_spec(custom_spec, CustomSpec),
            creative_direction=creative_direction,
            output=_to_spec(output, OutputSpec) or OutputSpec(),
            temperature=temperature,
            seed=seed,
        )

        result = _process_images(input_spec)

        if result.success and result.outputs:
            # Return multimodal content so agent SEES the generated image
            # Format: [text with structured data, image for visual verification]
            output_variant = result.outputs[0]
            structured_data = {
                "success": True,
                "storage_path": output_variant.storage_path,
                "local_path": output_variant.path,
                "metadata": output_variant.metadata.model_dump()
                if output_variant.metadata
                else None,
                "warnings": result.warnings,
            }

            # Load the generated image for visual return
            # Use higher resolution for quality verification (agent needs to see detail)
            try:
                local_path = Path(output_variant.path)
                if local_path.exists():
                    with Image.open(local_path) as pil_img:
                        # Higher resolution for verification - agent needs to judge quality
                        width, height = pil_img.size
                        max_dim = 1024  # Higher than view_image's 512 for quality checks
                        output_img: Image.Image = pil_img
                        if max(width, height) > max_dim:
                            if width > height:
                                new_width = max_dim
                                new_height = int(height * (max_dim / width))
                            else:
                                new_height = max_dim
                                new_width = int(width * (max_dim / height))
                            output_img = output_img.resize(
                                (new_width, new_height), Image.Resampling.LANCZOS
                            )

                        # Convert to RGB if needed (for JPEG encoding)
                        if output_img.mode in ("RGBA", "LA", "P"):
                            rgb_img = Image.new("RGB", output_img.size, (255, 255, 255))
                            if output_img.mode == "RGBA":
                                rgb_img.paste(output_img, mask=output_img.split()[-1])
                            else:
                                rgb_img.paste(output_img)
                            output_img = rgb_img

                        buffer = io.BytesIO()
                        output_img.save(
                            buffer, format="JPEG", quality=90
                        )  # Higher quality for verification
                        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
                        data_uri = f"data:image/jpeg;base64,{encoded}"

                    # Return multimodal: structured data + visual image
                    import json

                    return [
                        {
                            "type": "text",
                            "text": f"Image generated successfully.\n{json.dumps(structured_data, indent=2)}",
                        },
                        {"type": "image_url", "image_url": {"url": data_uri}},
                    ]
            except Exception as img_err:
                logger.warning(f"Could not load generated image for preview: {img_err}")

            # Fallback to structured-only response if image load fails
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
    - Generated images uploaded to pending/
    - storage_path included in output for write_data
    """
    _set_storage_client(storage)

    return StructuredTool.from_function(
        func=_image_studio_impl,
        name="image_studio",
        description=(
            "PURPOSE: Professional image processing (Gemini 3 Pro Image) - transform user uploads into catalog-ready assets. Extract products, generate lifestyle scenes, create hero shots, compose families. Your creative studio.\n\n"
            "LABELED IMAGES ARCHITECTURE (key differentiator):\n"
            "- Each image has label: [{path: 'inbox/photo.jpg', label: 'product'}]\n"
            "- Reference labels in spec VALUES using [label] syntax: 'extract [product] from [source]', 'place [product] on [background]'\n"
            "- Common labels: 'product'/'source' (main), 'style_ref'/'mood_ref' (lifestyle atmosphere), 'background' (scene), 'product_variant' (family)\n"
            "- Model reasons about specs + labeled images to decide what to do\n"
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
            "- fidelity: CRITICAL for source images - {preserve_colors: 'exact match', preserve_artwork: 'honeycomb pattern', hero_features: 'texture pattern'}\n"
            "- extraction: {target_description: 'Extract jar from [source]', targets: [{target_bbox: [0,0,500,500], target_image_label: 'source'}], isolation: 'complete'}\n"
            "  * target_description: Describes the overall extraction task\n"
            "  * targets: Array of {target_bbox, target_image_label}. Min len 1. Use multiple for batch extraction.\n"
            "- background: {treatment: 'transparent'/'solid_color'/'scene', color: 'white', scene_description: 'modern kitchen'}\n"
            "- lighting: {type: 'natural_window'/'studio_3point', direction: 'front'/'side', shadows: 'soft falloff'}\n"
            "- composition: {position: 'center'/'[main] center [variant] right', camera_angle: 'slight_top', negative_space: 'generous_top'}\n"
            "- enhancement: {sharpness: 'tack_sharp', color_treatment: 'accurate to source'}\n"
            "- scene: {environment: 'modern_kitchen', style: 'modern minimalist', mood: 'warm_inviting'}\n"
            "- placement: {position: 'place [product] on marble counter', scale: 'prominent'}\n"
            "- material_treatment: {primary_material: 'clear_glass', rendering_notes: 'preserve caustics'}\n"
            "- custom_spec: {instruction: 'dramatic shot with water droplets', style_reference: 'Apple product photography'}\n"
            "- creative_direction: Free-form notes ('Family shot - main hero, second supporting')\n"
            "- output: {format: 'png'/'jpeg', size: '1K'/'2K', aspect_ratio: '1:1'/'16:9'}\n\n"
            "FIDELITY FIRST (when working with source product images):\n"
            "- ALWAYS include fidelity spec when extracting/processing products\n"
            "- Fidelity > Enhancement: Preserve product identity before beautifying\n"
            "- Colors, artwork, text, textures, shape must match source exactly\n"
            "- Enhancement zone: background, lighting quality, sharpness, composition\n"
            "- Fidelity zone (no changes): product colors, artwork, text, shape, textures\n\n"
            "CRITICAL:\n"
            "- images parameter REQUIRED: Min 1 labeled image, max 15\n"
            "- LABEL SYNTAX: Reference labels using [label] in spec STRING values (e.g., 'jar in [source]', 'place [product] on [background]')\n"
            "- storage_path output: Use this for write_data assets (pending/ path)\n"
            "- Material matters: Glass, metal, plastic need different rendering (specify material_treatment)\n"
            "- One output per call (unless using extraction.targets for batch)\n\n"
            "PATTERNS: See image_studio.protocol for detailed use patterns (extract, lifestyle, family, hero shot).\n\n"
            "WORKFLOW:\n"
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
