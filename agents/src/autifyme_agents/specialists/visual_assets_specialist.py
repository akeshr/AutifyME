"""
Visual Assets Specialist - Image preparation and asset coordination.

Domain Expertise:
- Image analysis and quality assessment
- Multi-platform image specifications (Instagram, Facebook, Google Shopping)
- Image variant organization (family-level vs variant-specific)
- Product photography best practices
- Visual merchandising and presentation

Responsibilities:
- Analyze existing product images for quality and completeness
- Identify which images should be family-level vs variant-specific
- Prepare image metadata (dimensions, types, alt text)
- Return VisualAssetsDraft for PM review

Does NOT:
- Upload images to storage (PM handles after approval)
- Generate new images (Phase 2 feature - currently uses existing images)
- Create actual graphics (works with provided images)

Architecture Pattern:
- SubAgent dict format
- Returns structured Pydantic models
- PM orchestrates and approves
"""

from typing import Any

from langchain.tools import tool
from pydantic import BaseModel, Field

from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.tools.image_analysis_tool import image_analysis_tool

# =============================================================================
# Data Models - Visual Assets Specialist Outputs
# =============================================================================


class ImageAssetDraft(BaseModel):
    """Draft specification for a single image asset."""

    url: str = Field(..., description="Image URL or local path")
    alt_text: str = Field(..., description="SEO-optimized alt text")
    image_type: str = Field(
        ...,
        description="primary, gallery, thumbnail, lifestyle, closeup, or video_thumbnail",
    )
    display_order: int = Field(..., description="Sort order in gallery")
    is_primary: bool = Field(default=False, description="Hero image for listings")

    # Multi-level targeting
    for_family: bool = Field(
        default=True, description="True if image applies to all variants"
    )
    for_specific_sku: str | None = Field(
        None, description="If set, image is variant-specific (e.g., 'SHOE-M-RED')"
    )

    # Quality metadata
    width: int | None = None
    height: int | None = None
    file_size_bytes: int | None = None
    quality_score: float = Field(
        ..., ge=0.0, le=1.0, description="Image quality assessment (0-1)"
    )
    quality_notes: str = Field(..., description="Quality assessment notes")


class VisualAssetsDraft(BaseModel):
    """Complete visual assets package from Visual Assets Specialist."""

    # Image assets
    images: list[ImageAssetDraft] = Field(..., description="All product images organized")

    # Coverage analysis
    has_primary_image: bool = Field(..., description="At least one hero image exists")
    has_lifestyle_images: bool = Field(
        ..., description="Lifestyle/context images exist"
    )
    has_closeup_images: bool = Field(..., description="Detail/closeup images exist")
    variant_coverage: dict[str, bool] = Field(
        default_factory=dict,
        description="Which variants have specific images (sku -> has_image)",
    )

    # Quality assessment
    overall_quality_score: float = Field(
        ..., ge=0.0, le=1.0, description="Average quality across all images"
    )
    image_count: int = Field(..., description="Total number of images")

    # Recommendations
    missing_asset_types: list[str] = Field(
        default_factory=list, description="Recommended additional image types"
    )
    improvement_suggestions: list[str] = Field(
        default_factory=list, description="Quality improvement recommendations"
    )

    # Analysis metadata
    analysis_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in asset organization"
    )
    analysis_notes: str = Field(..., description="Additional observations")


# =============================================================================
# Tools - Visual Assets Analysis
# =============================================================================


@tool
def assess_image_quality(image_path: str) -> dict[str, Any]:
    """
    Assess image quality for ecommerce use.

    Analyzes:
    - Resolution (min 800x800 for product images)
    - Clarity and focus
    - Lighting quality
    - Background cleanliness
    - Composition

    Args:
        image_path: Path to image file

    Returns:
        Quality assessment with score and recommendations
    """
    import os

    from PIL import Image

    try:
        # Get file metadata
        file_size = os.path.getsize(image_path)

        # Open image to check dimensions
        with Image.open(image_path) as img:
            width, height = img.size
            format_type = img.format

        # Quality scoring (simplified for Phase 1)
        quality_score = 1.0
        quality_issues = []
        recommendations = []

        # Resolution check
        min_dimension = min(width, height)
        if min_dimension < 500:
            quality_score -= 0.4
            quality_issues.append("Low resolution (< 500px)")
            recommendations.append("Use higher resolution images (min 800x800)")
        elif min_dimension < 800:
            quality_score -= 0.2
            quality_issues.append("Below recommended resolution")
            recommendations.append("Consider higher resolution for better quality")

        # Aspect ratio check (square is ideal for product images)
        aspect_ratio = width / height
        if aspect_ratio < 0.8 or aspect_ratio > 1.2:
            quality_score -= 0.1
            quality_issues.append("Non-square aspect ratio")
            recommendations.append("Square images (1:1) work best across platforms")

        # File size check
        if file_size > 5 * 1024 * 1024:  # > 5MB
            quality_issues.append("Large file size may slow loading")
            recommendations.append("Optimize image size for web (< 2MB recommended)")

        quality_score = max(quality_score, 0.0)

        return {
            "quality_score": quality_score,
            "width": width,
            "height": height,
            "file_size_bytes": file_size,
            "format": format_type,
            "quality_issues": quality_issues,
            "recommendations": recommendations,
            "is_suitable": quality_score >= 0.6,
        }

    except Exception as e:
        return {
            "quality_score": 0.0,
            "error": str(e),
            "quality_issues": ["Cannot analyze image"],
            "recommendations": ["Verify image file is valid"],
            "is_suitable": False,
        }


@tool
def categorize_image_type(image_description: str, visual_elements: list[str]) -> str:
    """
    Categorize image into type based on analysis.

    Types:
    - primary: Clean product shot on white/neutral background
    - lifestyle: Product in use/context
    - closeup: Detail shot showing materials/construction
    - gallery: Additional angles/views

    Args:
        image_description: Description from image analysis
        visual_elements: List of visual elements detected

    Returns:
        Image type classification
    """
    description_lower = image_description.lower()
    elements_text = " ".join(visual_elements).lower()

    # Check for lifestyle indicators
    lifestyle_keywords = [
        "person", "wearing", "using", "context", "environment",
        "lifestyle", "scene", "background", "setting"
    ]
    if any(kw in description_lower or kw in elements_text for kw in lifestyle_keywords):
        return "lifestyle"

    # Check for closeup indicators
    closeup_keywords = [
        "detail", "close-up", "closeup", "texture", "material",
        "stitching", "fabric", "construction", "finish"
    ]
    if any(kw in description_lower or kw in elements_text for kw in closeup_keywords):
        return "closeup"

    # Check for clean product shot
    clean_keywords = [
        "white background", "neutral background", "isolated",
        "clean", "studio", "product only"
    ]
    if any(kw in description_lower or kw in elements_text for kw in clean_keywords):
        return "primary"

    # Default to gallery
    return "gallery"


@tool
def generate_alt_text(
    product_name: str, variant_details: str | None, image_type: str
) -> str:
    """
    Generate SEO-optimized alt text for image.

    Args:
        product_name: Product family name
        variant_details: Variant-specific details (e.g., "Medium, Red")
        image_type: Image type (primary, lifestyle, closeup, gallery)

    Returns:
        SEO-optimized alt text
    """
    type_descriptions = {
        "primary": "product image",
        "lifestyle": "lifestyle image showing product in use",
        "closeup": "closeup detail image",
        "gallery": "product view",
    }

    type_desc = type_descriptions.get(image_type, "image")

    if variant_details:
        alt_text = f"{product_name} - {variant_details} - {type_desc}"
    else:
        alt_text = f"{product_name} - {type_desc}"

    # Keep under 125 characters for optimal SEO
    if len(alt_text) > 125:
        alt_text = alt_text[:122] + "..."

    return alt_text


# =============================================================================
# Specialist Factory
# =============================================================================


def create_visual_assets_specialist() -> dict[str, Any]:
    """
    Create Visual Assets Specialist as SubAgent spec.

    Specialist Responsibilities:
    - Analyze product images for quality and type
    - Organize images (family-level vs variant-specific)
    - Generate image metadata (alt text, dimensions, quality scores)
    - Identify missing asset types
    - Return VisualAssetsDraft for PM review

    Architecture:
    - SubAgent dict format
    - Analysis tools only (no persistence)
    - Returns structured Pydantic model
    - PM handles HITL and persistence

    Note: Phase 1 works with existing images. Phase 2 will add image generation.

    Returns:
        SubAgent spec with visual assets tools
    """
    system_prompt = load_prompt("specialists/visual_assets_specialist.prompt")

    description = (
        "Analyzes and organizes product images for ecommerce. "
        "Assesses image quality, categorizes image types (primary, lifestyle, closeup), "
        "generates SEO-optimized alt text, and identifies missing assets. "
        "Organizes images into family-level (shared) vs variant-specific. "
        "Returns VisualAssetsDraft for PM review."
    )

    tools = [
        image_analysis_tool,  # Multimodal image analysis
        assess_image_quality,  # Quality scoring
        categorize_image_type,  # Type classification
        generate_alt_text,  # SEO alt text generation
    ]

    return {
        "name": "visual_assets_specialist",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
    }
