"""Marketing Content Specialist output models.

Defines structured outputs for campaign narratives, headlines,
value propositions, and CTAs.
"""

from pydantic import BaseModel, Field


class HeadlineVariantDraft(BaseModel):
    """Draft headline variant for campaign."""

    headline_text: str = Field(..., description="Headline text")
    headline_type: str = Field(
        ..., description="Headline type (emotional, rational, question, statement, urgency)"
    )
    character_count: int = Field(..., description="Character count")
    use_case: str = Field(
        ..., description="Best use case (social post, email subject, landing page, etc.)"
    )


class CallToActionDraft(BaseModel):
    """Draft CTA for campaign."""

    cta_text: str = Field(..., description="CTA text")
    cta_type: str = Field(
        ..., description="CTA type (buy_now, learn_more, sign_up, download, contact_us)"
    )
    urgency_level: str = Field(
        ..., description="Urgency level (low, medium, high)"
    )
    use_case: str = Field(..., description="Best platform/context for this CTA")


class MarketingContentDraft(BaseModel):
    """Complete marketing content from Marketing Content Specialist."""

    # Campaign narrative
    campaign_narrative: str = Field(
        ..., description="Main campaign story and narrative arc"
    )
    value_proposition: str = Field(
        ..., description="Core value proposition for this campaign"
    )
    key_messages: list[str] = Field(
        ..., description="3-5 key messages to communicate"
    )

    # Headlines and hooks
    headline_variants: list[HeadlineVariantDraft] = Field(
        ..., description="Multiple headline variants (5-7 variants)"
    )

    # CTAs
    cta_variants: list[CallToActionDraft] = Field(
        ..., description="Multiple CTA variants (3-5 variants)"
    )

    # Content pillars
    content_themes: list[str] = Field(
        default_factory=list, description="Content themes for organic posts"
    )
    storytelling_angles: list[str] = Field(
        default_factory=list, description="Different angles to tell the campaign story"
    )

    # Brand voice alignment
    tone_guidelines: str = Field(
        ..., description="Tone and voice guidelines for this campaign"
    )
    brand_alignment_notes: str = Field(
        ..., description="How content aligns with brand voice"
    )

    # Analysis metadata
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in content strategy"
    )
    content_notes: str = Field(
        ..., description="Additional content recommendations"
    )
