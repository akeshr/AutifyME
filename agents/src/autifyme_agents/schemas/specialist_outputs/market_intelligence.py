"""Market Intelligence Specialist output models.

Defines structured outputs for market positioning, customer segments,
and industry use case analysis.
"""

from typing import Any

from pydantic import BaseModel, Field


class PricePositionAnalysis(BaseModel):
    """Price positioning analysis."""

    suggested_positioning: str = Field(
        ..., description="budget, mid-range, premium, or luxury"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in positioning")
    reasoning: str = Field(..., description="Why this positioning was selected")
    competitive_context: str = Field(
        ..., description="Market landscape and competitive positioning"
    )
    pricing_recommendations: dict[str, Any] = Field(
        ..., description="Price ranges and strategy recommendations"
    )


class CustomerSegmentDraft(BaseModel):
    """Customer segment with messaging strategy."""

    segment_type: str = Field(
        ..., description="b2b, b2c, d2c, wholesale, enterprise, or retail"
    )
    segment_label: str = Field(..., description="Human-readable label")
    tone: str = Field(
        ...,
        description="professional, casual, technical, emotional, educational, or aspirational",
    )
    key_benefits: list[str] = Field(..., description="Top benefits for this segment")
    pain_points: list[str] = Field(..., description="Problems this product solves")
    primary_channels: list[str] = Field(
        ..., description="Marketing channels (linkedin, instagram, email, etc.)"
    )
    content_formats: list[str] = Field(
        ..., description="Content formats (carousel, video, infographic, etc.)"
    )
    pricing_notes: str | None = Field(None, description="Segment-specific pricing notes")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Segment relevance confidence")
    reasoning: str = Field(..., description="Why this segment is relevant")


class IndustryUseCaseDraft(BaseModel):
    """Industry-specific use case for B2B targeting."""

    naics_code: str = Field(..., description="NAICS industry code")
    industry_label: str = Field(..., description="Industry name")
    use_case: str = Field(..., description="How product solves industry-specific problems")
    industry_benefits: list[str] = Field(..., description="Industry-specific benefits")
    compliance_notes: str | None = Field(None, description="Regulatory/compliance considerations")
    is_primary_industry: bool = Field(..., description="Primary target industry")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Industry fit confidence")
    reasoning: str = Field(..., description="Why this industry is a good fit")


class MarketIntelligenceDraft(BaseModel):
    """Complete market intelligence analysis."""

    # Price positioning
    price_positioning: PricePositionAnalysis = Field(
        ..., description="Strategic price positioning analysis"
    )

    # Customer segments
    customer_segments: list[CustomerSegmentDraft] = Field(
        ..., description="Identified customer segments with messaging strategies"
    )

    # Industry use cases (B2B multi-industry targeting)
    industry_use_cases: list[IndustryUseCaseDraft] = Field(
        ..., description="Industry-specific targeting (ordered by relevance)"
    )

    # Strategic recommendations
    go_to_market_strategy: str = Field(
        ..., description="Recommended go-to-market approach"
    )
    differentiation_factors: list[str] = Field(
        ..., description="Key competitive differentiators"
    )

    # Analysis metadata
    analysis_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Overall analysis confidence"
    )
    analysis_notes: str = Field(..., description="Additional strategic observations")
