"""Visual Assets Specialist output models.

Defines structured outputs for image asset preparation
and visual quality assessment.
"""

from pydantic import BaseModel, Field


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
