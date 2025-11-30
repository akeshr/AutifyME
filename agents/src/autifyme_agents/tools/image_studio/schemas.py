"""Image Studio Tool - Pydantic Schemas.

Comprehensive input/output schemas for Gemini 3 Pro Image operations.
Supports: analyze, edit, generate with full multi-product handling.
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

    ANALYZE = "analyze"    # Extract visual attributes, detect multiple products
    EDIT = "edit"          # Modify image: background, enhance, extract, crop
    GENERATE = "generate"  # Create new image: lifestyle, studio, composite


# =============================================================================
# Input Specification Models
# =============================================================================


class BackgroundSpec(BaseModel):
    """Background configuration for edit/generate operations."""

    type: Literal["solid", "gradient", "transparent", "blur", "scene", "remove"] = "solid"
    color: str = Field(default="#FFFFFF", description="Primary color (hex)")
    gradient_end: str | None = Field(default=None, description="End color for gradients")
    blur_strength: Literal["light", "medium", "heavy"] | None = None
    scene_description: str | None = Field(
        default=None,
        description="For type='scene': describe the background scene to generate"
    )


class LightingSpec(BaseModel):
    """Lighting configuration for professional product photography."""

    type: Literal["studio", "natural", "dramatic", "soft", "hard", "rim", "split"] = "studio"
    direction: Literal["front", "side", "back", "top", "ambient", "45deg"] = "front"
    intensity: Literal["low", "medium", "high"] = "medium"
    color_temperature: Literal["warm", "neutral", "cool"] = "neutral"
    shadows: Literal["none", "soft", "hard"] = "soft"


class FramingSpec(BaseModel):
    """Product framing and composition settings."""

    product_coverage_percent: int = Field(
        default=80,
        ge=20,
        le=100,
        description="How much of frame product should occupy (20-100%)",
    )
    padding_percent: int = Field(
        default=10,
        ge=0,
        le=50,
        description="Padding around product",
    )
    alignment: Literal["center", "bottom", "top", "left", "right", "bottom-left", "bottom-right", "top-left", "top-right"] = "center"
    angle: Literal["front", "45deg", "side", "top-down", "hero", "low-angle", "eye-level"] = "front"
    crop_to_product: bool = Field(
        default=False,
        description="Crop image to focus on product, removing excess background"
    )


class EnhancementSpec(BaseModel):
    """Image enhancement settings."""

    sharpness: Literal["none", "subtle", "medium", "high"] = "medium"
    contrast: Literal["none", "subtle", "medium", "high"] = "subtle"
    saturation: Literal["none", "subtle", "medium", "high"] = "none"
    brightness: Literal["none", "subtle", "medium", "high"] = "none"
    denoise: bool = Field(default=False, description="Apply noise reduction")
    upscale: Literal["none", "2x", "4x"] = "none"
    color_correction: bool = Field(default=True, description="Auto color correction")
    remove_blemishes: bool = Field(default=False, description="Remove dust, scratches, imperfections")
    restore_details: bool = Field(default=False, description="AI-enhance fine details")


class SceneSpec(BaseModel):
    """Lifestyle scene settings for generate operation."""

    environment: Literal[
        "kitchen", "living_room", "office", "outdoor", "restaurant",
        "retail", "warehouse", "studio", "bathroom", "garden",
        "cafe", "gym", "bedroom", "dining_room", "custom"
    ]
    style: Literal["modern", "traditional", "minimalist", "rustic", "industrial", "luxury", "casual", "professional"] = "modern"
    mood: Literal["professional", "cozy", "vibrant", "elegant", "casual", "warm", "cool", "dramatic"] = "professional"
    time_of_day: Literal["morning", "afternoon", "evening", "night", "golden_hour"] = "afternoon"
    custom_description: str | None = Field(
        default=None,
        description="For environment='custom': describe the scene in detail"
    )


class ProductPlacement(BaseModel):
    """Product placement in generated scenes."""

    position: Literal["center", "foreground", "left", "right", "table", "shelf", "counter", "floor", "floating", "hand"] = "center"
    scale: Literal["dominant", "balanced", "subtle", "actual_size"] = "balanced"
    surface: Literal["table", "counter", "floor", "shelf", "hand", "floating", "pedestal", "fabric"] | None = None
    angle: Literal["straight", "tilted", "laying", "standing"] = "straight"
    shadow: bool = Field(default=True, description="Add realistic shadow under product")


class ExtractionSpec(BaseModel):
    """Extract specific product(s) from multi-product image.

    Use this when working with group photos containing multiple products/variants.
    """

    target_description: str = Field(
        description="Description of product to extract: 'the red variant', 'the 500ml jar', 'product on the left'"
    )
    position_hint: Literal["left", "center", "right", "top", "bottom", "foreground", "background", "largest", "smallest"] | None = Field(
        default=None,
        description="Hint about product position in image"
    )
    isolate: bool = Field(
        default=True,
        description="Remove all other products, keep only target"
    )
    clean_edges: bool = Field(
        default=True,
        description="Clean up edges after extraction"
    )


class FocusRegionSpec(BaseModel):
    """Specify region to focus on or crop to."""

    type: Literal["center", "product", "custom", "face", "label", "detail"] = "product"
    position: Literal["left", "center", "right", "top", "bottom", "top-left", "top-right", "bottom-left", "bottom-right"] | None = None
    zoom_level: float = Field(
        default=1.0,
        ge=0.5,
        le=4.0,
        description="Zoom level: 1.0=no zoom, 2.0=2x zoom"
    )
    custom_focus: str | None = Field(
        default=None,
        description="For type='custom': describe what to focus on"
    )


class AnalysisAttributes(BaseModel):
    """Configuration for analyze operation - what to extract.

    Enable all relevant attributes for comprehensive product analysis.
    """

    colors: bool = Field(default=True, description="Extract dominant colors")
    materials: bool = Field(default=True, description="Identify materials")
    dimensions: bool = Field(default=True, description="Estimate dimensions from visual cues")
    condition: bool = Field(default=True, description="Assess condition (new, used, damaged)")
    brand_text: bool = Field(default=True, description="Extract visible text, logos, brand names")
    product_category: bool = Field(default=True, description="Classify product type")
    quality_score: bool = Field(default=True, description="Rate image quality 0-1")
    background_type: bool = Field(default=True, description="Identify background type")

    # Multi-product analysis
    detect_all_products: bool = Field(
        default=True,
        description="Detect and list ALL products in image (for group photos)"
    )
    identify_variants: bool = Field(
        default=True,
        description="Identify product variants (size, color, etc.)"
    )

    custom_attributes: list[str] = Field(
        default_factory=list,
        description="Additional attributes: ['certifications', 'packaging_type', 'target_age']"
    )


class OutputSpec(BaseModel):
    """Output configuration for generated/edited images."""

    format: Literal["PNG", "JPEG", "WEBP"] = "PNG"
    size: Literal["1K", "2K", "4K"] = "2K"
    aspect_ratio: Literal["1:1", "3:4", "4:3", "9:16", "16:9", "original"] = "1:1"
    quality: int = Field(default=90, ge=1, le=100, description="JPEG quality")
    variants: list[Literal["master", "thumbnail", "social", "square", "portrait", "landscape"]] = Field(
        default_factory=lambda: ["master"],
        description="Output variants to generate",
    )


# =============================================================================
# Main Input Schema
# =============================================================================


class ImageStudioInput(BaseModel):
    """Unified input schema for Image Studio tool.

    CAPABILITIES (Gemini 3 Pro Image):

    ANALYZE:
    - Single product: Extract all visual attributes
    - Multi-product group: Detect ALL products, list positions, identify variants
    - Quality assessment: Score image quality, suggest improvements
    - Text extraction: All visible text, logos, brand names

    EDIT:
    - Background: Remove, replace solid/gradient, blur, or generate scene
    - Extract product: Isolate specific product from group photo
    - Enhance: Sharpen, denoise, upscale, color correct, restore details
    - Reframe: Crop, zoom, change composition
    - Lighting: Adjust studio/natural/dramatic lighting

    GENERATE:
    - Lifestyle shots: Product in realistic scenes (kitchen, office, etc.)
    - Studio shots: Clean professional backgrounds
    - Composites: Combine products with generated backgrounds
    - Variations: Same product in different scenes/angles

    EXAMPLES:

    1. Analyze group photo with multiple variants:
    ```python
    ImageStudioInput(
        operation="analyze",
        source_image="/tmp/group.jpg",
        analysis=AnalysisAttributes(
            detect_all_products=True,
            identify_variants=True,
            custom_attributes=["variant_size", "variant_color"]
        )
    )
    ```

    2. Extract single product from group:
    ```python
    ImageStudioInput(
        operation="edit",
        source_image="/tmp/group.jpg",
        extraction=ExtractionSpec(
            target_description="the red 500ml variant",
            position_hint="left",
            isolate=True
        ),
        background=BackgroundSpec(type="transparent"),
        output=OutputSpec(format="PNG")
    )
    ```

    3. Remove background and enhance:
    ```python
    ImageStudioInput(
        operation="edit",
        source_image="/tmp/product.jpg",
        background=BackgroundSpec(type="transparent"),
        enhancement=EnhancementSpec(
            sharpness="medium",
            denoise=True,
            upscale="2x"
        ),
        output=OutputSpec(format="PNG", size="4K")
    )
    ```

    4. Generate lifestyle shot:
    ```python
    ImageStudioInput(
        operation="generate",
        source_image="/tmp/product.jpg",
        scene=SceneSpec(
            environment="kitchen",
            style="modern",
            mood="warm",
            time_of_day="morning"
        ),
        placement=ProductPlacement(
            position="counter",
            scale="dominant",
            shadow=True
        ),
        output=OutputSpec(aspect_ratio="4:3")
    )
    ```

    5. Complex edit with custom instruction:
    ```python
    ImageStudioInput(
        operation="edit",
        source_image="/tmp/group.jpg",
        custom_instruction="Extract each of the 3 jar variants separately and create individual product shots with white background",
        output=OutputSpec(format="PNG")
    )
    ```
    """

    operation: ImageOperation = Field(description="Operation: analyze, edit, generate")
    source_image: str | None = Field(
        default=None,
        description="Path to source image (required for analyze/edit, optional for generate)"
    )
    reference_images: list[str] = Field(
        default_factory=list,
        description="Additional reference images for style/context (up to 14)"
    )

    # Custom instruction for complex operations
    custom_instruction: str | None = Field(
        default=None,
        description=(
            "Free-form instruction for complex operations beyond structured parameters. "
            "Examples: 'Extract each product variant and create separate images', "
            "'Combine these 3 products into a family shot', "
            "'Create a before/after comparison'"
        )
    )

    # Structured operation specs (provide based on operation type)
    background: BackgroundSpec | None = None
    lighting: LightingSpec | None = None
    framing: FramingSpec | None = None
    enhancement: EnhancementSpec | None = None
    scene: SceneSpec | None = None
    placement: ProductPlacement | None = None
    analysis: AnalysisAttributes | None = None
    extraction: ExtractionSpec | None = None
    focus: FocusRegionSpec | None = None

    output: OutputSpec = Field(default_factory=OutputSpec)


# =============================================================================
# Output Schemas
# =============================================================================


class CustomAttribute(BaseModel):
    """Key-value pair for custom attributes (Gemini-compatible)."""

    name: str = Field(description="Attribute name")
    value: str = Field(description="Attribute value")


class ProductDetection(BaseModel):
    """Single product detected in multi-product image."""

    index: int = Field(description="Product index (1-based)")
    description: str = Field(description="Brief description of this product")
    position: str = Field(description="Position in image: left, center, right, top, bottom")
    relative_size: Literal["largest", "medium", "smallest"] = "medium"
    distinguishing_features: list[str] = Field(
        default_factory=list,
        description="Features that distinguish this from others: color, size, label"
    )
    suggested_extraction: str = Field(
        default="",
        description="Suggested extraction description for this product"
    )


class ImageMetadata(BaseModel):
    """Metadata for generated/edited images."""

    width: int
    height: int
    format: str
    size_bytes: int
    aspect_ratio: str


class AnalysisResult(BaseModel):
    """Result from analyze operation.

    For multi-product images, product_inventory lists each detected product.
    """

    # Single-product attributes
    colors: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    dimensions: str | None = None
    condition: str | None = None
    brand_text: list[str] = Field(default_factory=list)
    product_category: str | None = None
    background_type: str | None = None
    quality_score: float = Field(ge=0.0, le=1.0, default=0.0)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    custom_attributes: list[CustomAttribute] = Field(
        default_factory=list,
        description="Custom extracted attributes as key-value pairs"
    )

    # Multi-product detection
    product_count: int = Field(default=1, description="Number of products detected")
    multi_product_warning: str | None = Field(
        default=None,
        description="Warning and guidance for multi-product images"
    )
    product_inventory: list[ProductDetection] = Field(
        default_factory=list,
        description="Detailed inventory of each product detected"
    )

    # Variant detection
    detected_variants: list[str] = Field(
        default_factory=list,
        description="Variant types detected: '500ml red', '1L blue', etc."
    )
    variant_axis: str | None = Field(
        default=None,
        description="Primary variant axis if detected: Size, Color, Material"
    )

    # Recommendations
    suggested_operations: list[str] = Field(
        default_factory=list,
        description="Recommended follow-up operations: 'Extract each variant', 'Remove background'"
    )


class OutputVariant(BaseModel):
    """Single output variant (master, thumbnail, social)."""

    variant: str
    path: str
    preview_path: str
    metadata: ImageMetadata
    description: str | None = Field(
        default=None,
        description="Description of what this variant contains"
    )


class ImageStudioOutput(BaseModel):
    """Unified output schema for Image Studio tool."""

    success: bool
    operation: ImageOperation

    # For generate/edit operations
    outputs: list[OutputVariant] = Field(default_factory=list)

    # For analyze operation
    analysis: AnalysisResult | None = None

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
