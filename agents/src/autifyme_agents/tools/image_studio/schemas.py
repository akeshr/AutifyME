"""Image Studio Tool - Pydantic Schemas.

Simplified schema: Creative Specialist writes natural language creative briefs.
The tool passes these directly to Gemini 3 Pro Image.

Architecture Philosophy:
- Trust the Creative Specialist's reasoning and creative vision
- No enum restrictions - full creative expression
- Minimal structure: operation type, images, creative direction, output mechanics
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

# =============================================================================
# Operation Types
# =============================================================================


class ImageOperation(str, Enum):
    """Supported image operations."""

    EDIT = "edit"          # Modify existing image
    GENERATE = "generate"  # Create new image from product


# =============================================================================
# Output Specification (API mechanics, not creative decisions)
# =============================================================================


class OutputSpec(BaseModel):
    """Output configuration - these are API parameters, not creative decisions."""

    format: Literal["PNG", "JPEG", "WEBP"] = "PNG"
    size: Literal["1K", "2K", "4K"] = "2K"
    aspect_ratio: Literal["1:1", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "original"] = "1:1"


# =============================================================================
# Main Input Schema
# =============================================================================


class ImageStudioInput(BaseModel):
    """Image Studio input - trusts Creative Specialist's creative vision.

    Architecture:
    - Creative Specialist reasons about the image task
    - Writes a complete creative brief in natural language
    - Image Studio passes this directly to Gemini 3 Pro Image
    - No enum bottlenecks, no translation loss

    The creative_direction field is where the magic happens. Write it like
    a professional photographer's brief: lighting, composition, mood,
    material treatment, technical requirements.

    EXAMPLES:

    1. Hero shot with background removal:
    ```python
    ImageStudioInput(
        operation="edit",
        source_image="inbox/thread/product.jpg",
        creative_direction=(
            "Extract the glass jar from background. "
            "Pure white (#FFFFFF) studio background. "
            "Soft studio lighting from 45-degrees camera-left, "
            "rim light for glass edge definition. "
            "Honor the glass: internal caustics, edge refraction, transparency. "
            "Product centered, 75% frame coverage. "
            "Sharp focus on label, natural falloff on edges."
        ),
        output=OutputSpec(format="PNG", size="2K", aspect_ratio="1:1")
    )
    ```

    2. Lifestyle scene generation:
    ```python
    ImageStudioInput(
        operation="generate",
        source_image="inbox/thread/product.jpg",
        creative_direction=(
            "Modern kitchen scene, morning light streaming through window. "
            "Product on white marble countertop with fresh herbs nearby. "
            "Warm color temperature, lifestyle editorial feel. "
            "Product hero position but not isolated - contextual storytelling. "
            "Shallow depth of field, product tack sharp, background soft."
        ),
        output=OutputSpec(aspect_ratio="4:3")
    )
    ```

    3. Multi-product extraction:
    ```python
    ImageStudioInput(
        operation="edit",
        source_image="inbox/thread/group.jpg",
        creative_direction=(
            "Extract the red 500ml variant (left side of image). "
            "Isolate completely from other products. "
            "Clean surgical extraction with professional edge treatment. "
            "Transparent background for compositing flexibility. "
            "Preserve exact color accuracy - this is the hero product."
        ),
        output=OutputSpec(format="PNG")
    )
    ```

    4. Enhancement and reframing:
    ```python
    ImageStudioInput(
        operation="edit",
        source_image="inbox/thread/photo.jpg",
        creative_direction=(
            "Enhance this product photo for e-commerce. "
            "Clean up the cluttered background - solid white. "
            "Boost sharpness on product details, especially the label. "
            "Color correct for accurate product representation. "
            "Crop tighter - product should dominate frame at 80% coverage. "
            "Professional studio quality output."
        )
    )
    ```
    """

    operation: ImageOperation = Field(description="Operation: edit or generate")

    source_image: str | None = Field(
        default=None,
        description=(
            "Source image storage_path (e.g., 'inbox/thread_id/photo.jpg'). "
            "Required for edit, optional for generate."
        )
    )

    reference_images: list[str] = Field(
        default_factory=list,
        description="Reference images for style/context (storage_paths, up to 14)"
    )

    creative_direction: str = Field(
        description=(
            "Complete creative brief in natural language. "
            "Write like a professional photographer: lighting, composition, mood, "
            "material treatment, background, technical requirements. "
            "Be specific and professional. This is passed directly to the image model."
        )
    )

    # Thread ID for cloud storage persistence (auto-injected from RunnableConfig)
    thread_id: str | None = Field(
        default=None,
        description=(
            "Auto-injected from session context - do not pass explicitly."
        )
    )

    # Output mechanics (API parameters, not creative decisions)
    output: OutputSpec = Field(default_factory=OutputSpec)


# =============================================================================
# Output Schemas
# =============================================================================


class ImageMetadata(BaseModel):
    """Metadata for generated/edited images."""

    width: int
    height: int
    format: str
    size_bytes: int
    aspect_ratio: str


class OutputVariant(BaseModel):
    """Single output variant (master, thumbnail, social).

    Use storage_path for all references. URL is derived where needed.
    """

    variant: str
    path: str = Field(description="Local path (ephemeral)")
    preview_path: str = Field(description="Local preview path (ephemeral)")
    metadata: ImageMetadata
    description: str | None = Field(default=None)
    storage_path: str | None = Field(
        default=None,
        description="Bucket path (e.g., 'pending/thread_id/file.png'). Use in view_image, write_data."
    )


class ImageStudioOutput(BaseModel):
    """Unified output schema for Image Studio tool."""

    success: bool
    operation: ImageOperation

    # For generate/edit operations
    outputs: list[OutputVariant] = Field(default_factory=list)

    # For asset creation (suggested data for WriteIntent)
    suggested_asset_data: str | None = Field(
        default=None,
        description="JSON string with pre-populated asset record for WriteIntent"
    )

    # Warnings, errors, and guidance
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    error_code: str | None = None
    next_steps: list[str] = Field(
        default_factory=list,
        description="Suggested next operations based on results"
    )


# =============================================================================
# Error Codes
# =============================================================================


class ImageStudioErrorCode:
    """Standard error codes for Image Studio operations."""

    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    CORRUPT_FILE = "CORRUPT_FILE"
    RATE_LIMIT = "RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    API_ERROR = "API_ERROR"
    CONTENT_POLICY = "CONTENT_POLICY"
    INVALID_INPUT = "INVALID_INPUT"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    IMAGE_TOO_LARGE = "IMAGE_TOO_LARGE"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
