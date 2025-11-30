"""Image Studio Tool - Pydantic Schemas.

Structured input/output schemas for Gemini 3 Pro Image (Nano Banana Pro) operations.
All image operations use typed fields - NO string instructions.

Design Decision: Single unified tool with structured Pydantic schema.
One powerful LLM = One powerful tool. Specialist orchestrates by constructing
appropriate input schema for analyze, edit, or generate operations.
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

    ANALYZE = "analyze"  # Extract visual attributes
    GENERATE = "generate"  # Create new image (lifestyle shots)
    EDIT = "edit"  # Modify existing image (background, enhance)


# =============================================================================
# Input Specification Models
# =============================================================================


class BackgroundSpec(BaseModel):
    """Background configuration for edit/generate operations."""

    type: Literal["solid", "gradient", "transparent", "blur", "scene"] = "solid"
    color: str = Field(default="#FFFFFF", description="Primary color (hex)")
    gradient_end: str | None = Field(default=None, description="End color for gradients")
    blur_strength: Literal["light", "medium", "heavy"] | None = None


class LightingSpec(BaseModel):
    """Lighting configuration for professional product photography."""

    type: Literal["studio", "natural", "dramatic", "soft", "hard"] = "studio"
    direction: Literal["front", "side", "back", "top", "ambient"] = "front"
    intensity: Literal["low", "medium", "high"] = "medium"
    color_temperature: Literal["warm", "neutral", "cool"] = "neutral"


class FramingSpec(BaseModel):
    """Product framing and composition settings."""

    product_coverage_percent: int = Field(
        default=80,
        ge=50,
        le=95,
        description="How much of frame product should occupy",
    )
    padding_percent: int = Field(
        default=10,
        ge=5,
        le=30,
        description="Padding around product",
    )
    alignment: Literal["center", "bottom", "top", "left", "right"] = "center"
    angle: Literal["front", "45deg", "side", "top-down", "hero"] = "front"


class EnhancementSpec(BaseModel):
    """Image enhancement settings."""

    sharpness: Literal["none", "subtle", "medium", "high"] = "medium"
    contrast: Literal["none", "subtle", "medium", "high"] = "subtle"
    saturation: Literal["none", "subtle", "medium", "high"] = "none"
    denoise: bool = Field(default=False, description="Apply noise reduction")
    upscale: Literal["none", "2x", "4x"] = "none"
    color_correction: bool = Field(default=True, description="Auto color correction")


class SceneSpec(BaseModel):
    """Lifestyle scene settings for generate operation."""

    environment: Literal[
        "kitchen",
        "living_room",
        "office",
        "outdoor",
        "restaurant",
        "retail",
        "warehouse",
        "studio",
    ]
    style: Literal["modern", "traditional", "minimalist", "rustic", "industrial"] = (
        "modern"
    )
    mood: Literal["professional", "cozy", "vibrant", "elegant", "casual"] = (
        "professional"
    )
    time_of_day: Literal["morning", "afternoon", "evening", "night"] = "afternoon"


class ProductPlacement(BaseModel):
    """Product placement in generated scenes."""

    position: Literal["center", "foreground", "left", "right", "table", "shelf"] = (
        "center"
    )
    scale: Literal["dominant", "balanced", "subtle"] = "balanced"
    surface: Literal["table", "counter", "floor", "shelf", "hand", "floating"] | None = (
        None
    )


class AnalysisAttributes(BaseModel):
    """Configuration for analyze operation - what to extract."""

    colors: bool = Field(default=True, description="Extract dominant colors")
    materials: bool = Field(default=True, description="Identify materials")
    dimensions: bool = Field(default=True, description="Estimate dimensions")
    condition: bool = Field(default=True, description="Assess condition")
    brand_text: bool = Field(default=True, description="Extract visible text/brands")
    product_category: bool = Field(default=True, description="Classify product type")
    quality_score: bool = Field(default=True, description="Rate image quality 0-1")
    background_type: bool = Field(default=True, description="Identify background")
    custom_attributes: list[str] = Field(
        default_factory=list,
        description="Additional attributes to extract",
    )


class OutputSpec(BaseModel):
    """Output configuration for generated/edited images."""

    format: Literal["PNG", "JPEG", "WEBP"] = "PNG"
    size: Literal["1K", "2K", "4K"] = "2K"
    aspect_ratio: Literal["1:1", "3:4", "4:3", "9:16", "16:9"] = "1:1"
    quality: int = Field(default=90, ge=1, le=100, description="JPEG quality")
    variants: list[Literal["master", "thumbnail", "social"]] = Field(
        default_factory=lambda: ["master"],
        description="Output variants to generate",
    )


# =============================================================================
# Main Input Schema
# =============================================================================


class ImageStudioInput(BaseModel):
    """Unified input schema for Image Studio tool.

    Specialist constructs this schema based on the operation needed.
    All parameters are typed - no string instructions.

    Examples:
        # Analyze product image
        ImageStudioInput(
            operation=ImageOperation.ANALYZE,
            source_image="/tmp/product.jpg",
            analysis=AnalysisAttributes(),
        )

        # Edit: Remove background, enhance
        ImageStudioInput(
            operation=ImageOperation.EDIT,
            source_image="/tmp/product.jpg",
            background=BackgroundSpec(type="solid", color="#FFFFFF"),
            enhancement=EnhancementSpec(sharpness="medium"),
            output=OutputSpec(format="PNG"),
        )

        # Generate lifestyle shot
        ImageStudioInput(
            operation=ImageOperation.GENERATE,
            source_image="/tmp/product.jpg",
            scene=SceneSpec(environment="kitchen", style="modern"),
            placement=ProductPlacement(position="table", scale="dominant"),
            output=OutputSpec(aspect_ratio="4:3"),
        )
    """

    operation: ImageOperation = Field(description="Operation type")
    source_image: str | None = Field(
        default=None,
        description="Path to source image (required for analyze/edit)",
    )
    reference_images: list[str] = Field(
        default_factory=list,
        description="Additional reference images (up to 14 for Gemini 3)",
    )

    # Operation-specific specs (provide based on operation type)
    background: BackgroundSpec | None = None
    lighting: LightingSpec | None = None
    framing: FramingSpec | None = None
    enhancement: EnhancementSpec | None = None
    scene: SceneSpec | None = None
    placement: ProductPlacement | None = None
    analysis: AnalysisAttributes | None = None

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


class AnalysisResult(BaseModel):
    """Result from analyze operation."""

    colors: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    dimensions: str | None = None
    condition: str | None = None
    brand_text: list[str] = Field(default_factory=list)
    product_category: str | None = None
    background_type: str | None = None
    quality_score: float = Field(ge=0.0, le=1.0, default=0.0)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    custom_attributes: dict = Field(default_factory=dict)

    # Multi-product detection
    product_count: int = Field(default=1, description="Number of products detected")
    multi_product_warning: str | None = Field(
        default=None,
        description="Warning if multiple products detected",
    )


class OutputVariant(BaseModel):
    """Single output variant (master, thumbnail, social)."""

    variant: str  # "master", "thumbnail", "social"
    path: str  # Temp file path
    preview_path: str  # Path for HITL preview
    metadata: ImageMetadata


class ImageStudioOutput(BaseModel):
    """Unified output schema for Image Studio tool.

    Success/error status with operation-specific results.
    """

    success: bool
    operation: ImageOperation

    # For generate/edit operations
    outputs: list[OutputVariant] = Field(default_factory=list)

    # For analyze operation
    analysis: AnalysisResult | None = None

    # For asset creation (suggested data for WriteIntent)
    suggested_asset_data: dict | None = Field(
        default=None,
        description="Pre-populated asset record for WriteIntent",
    )

    # Warnings and errors
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    error_code: str | None = Field(
        default=None,
        description="Machine-readable error code",
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
