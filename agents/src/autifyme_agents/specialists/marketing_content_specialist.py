"""
Marketing Content Specialist - Marketing-specific content creation and storytelling.

Domain Expertise:
- Campaign narratives and storytelling
- Value propositions and messaging
- Headlines and hooks for campaigns
- Call-to-actions (CTAs) optimized for conversion
- Email marketing copy, blog posts, social media organic posts
- Brand voice consistency across campaigns

Responsibilities:
- Create campaign narrative and story arc
- Generate value propositions and messaging frameworks
- Create multiple headline variants
- Design conversion-optimized CTAs
- Ensure brand voice consistency
- Return structured MarketingContentDraft

Does NOT:
- Format for specific platforms (Platform Adaptation Specialist handles this)
- Create paid ad copy (Ad Copy Specialist handles this)
- Target specific audiences (Audience Intelligence Specialist handles this)
- Persist to database (PM handles persistence with HITL)

Note:
Different from Content & SEO Specialist:
- Content & SEO: Product descriptions, feature bullets, meta tags (product-focused)
- Marketing Content: Campaign stories, value props, CTAs (campaign-focused)

Architecture Pattern:
- SubAgent dict format (NOT create_agent)
- Returns structured Pydantic models
- PM orchestrates delegation and approval
"""

from typing import Any

from pydantic import BaseModel, Field

from autifyme_agents.core.prompt_loader import load_prompt

# =============================================================================
# Data Models - Marketing Content Specialist Outputs
# =============================================================================


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


# =============================================================================
# Specialist Factory
# =============================================================================


def create_marketing_content_specialist() -> dict[str, Any]:
    """
    Create Marketing Content Specialist as SubAgent spec.

    Specialist Responsibilities:
    - Create campaign narrative and story arc
    - Generate value propositions and key messages
    - Create multiple headline and CTA variants
    - Ensure brand voice consistency
    - Return MarketingContentDraft for PM review

    Architecture:
    - SubAgent dict format (DeepAgents pattern)
    - Content creation (no persistence, no platform formatting)
    - Returns structured Pydantic model
    - PM handles HITL and persistence

    Returns:
        SubAgent spec with:
        - name: specialist identifier
        - description: delegation criteria
        - tools: content creation tools (if any)
        - system_prompt: domain expertise instructions
    """
    system_prompt = load_prompt("specialists/marketing_content_specialist.prompt")

    description = (
        "Creates campaign narratives, value propositions, headlines, and CTAs. "
        "Adapts to missing brand voice (uses professional neutral tone, flags assumption). "
        "Self-reviews content (validates brand alignment and message clarity). "
        "Returns MarketingContentDraft. "
        "Run AFTER Campaign Strategy (needs objectives). Can run PARALLEL with Audience + Visual Assets."
    )

    # No tools needed - specialist uses LLM for creative content generation
    tools = []

    return {
        "name": "marketing_content_specialist",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
    }
