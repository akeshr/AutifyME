"""Content & SEO Specialist output models.

Defines structured outputs for product content, SEO elements,
and platform-specific content variants.
"""

from typing import Any

from pydantic import BaseModel, Field


class ProductContentDraft(BaseModel):
    """Core product content."""

    short_description: str = Field(
        ..., max_length=160, description="Short description (< 160 chars for Google)"
    )
    long_description: str = Field(..., description="Full product description")
    feature_bullets: list[str] = Field(
        ..., min_length=3, max_length=10, description="Key feature bullet points"
    )


class SEOElementsDraft(BaseModel):
    """SEO optimization elements."""

    meta_title: str = Field(
        ..., max_length=60, description="SEO title (< 60 chars for Google)"
    )
    meta_description: str = Field(
        ..., max_length=160, description="Meta description (< 160 chars for Google)"
    )
    keywords: list[str] = Field(
        ..., min_length=5, max_length=20, description="Target keywords"
    )
    schema_org_data: dict[str, Any] = Field(
        ..., description="Schema.org Product structured data (JSON-LD)"
    )


class PlatformContentDraft(BaseModel):
    """Platform-specific content variant."""

    platform: str = Field(
        ..., description="instagram, facebook, linkedin, google_shopping, website, etc."
    )
    content_type: str = Field(
        ..., description="post, story, carousel, ad, catalog_description, etc."
    )
    content_text: str = Field(..., description="Actual content")
    hashtags: list[str] = Field(default_factory=list, description="Platform hashtags")
    content_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Platform-specific metadata"
    )


class ContentSEODraft(BaseModel):
    """Complete content and SEO package from Content & SEO Specialist."""

    # Core product content
    product_content: ProductContentDraft = Field(..., description="Core descriptions")

    # SEO elements
    seo_elements: SEOElementsDraft = Field(..., description="SEO optimization")

    # Platform-specific content
    platform_content: list[PlatformContentDraft] = Field(
        ..., description="Content variants per platform"
    )

    # Analysis metadata
    brand_voice_alignment: float = Field(
        ..., ge=0.0, le=1.0, description="Alignment with company brand voice"
    )
    readability_score: float = Field(
        ..., ge=0.0, le=1.0, description="Content readability (0=complex, 1=simple)"
    )
    seo_optimization_score: float = Field(
        ..., ge=0.0, le=1.0, description="SEO best practices compliance"
    )
    analysis_notes: str = Field(..., description="Content strategy notes")
