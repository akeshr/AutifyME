"""
Ad Copy Specialist - Paid advertising copy optimization.

Domain Expertise:
- Ad headlines (multiple variants for A/B testing)
- Ad descriptions (platform-specific character limits)
- CTAs optimized for conversion
- A/B test variant generation (3-5 variants per element)
- Ad compliance (platform advertising policies)
- Persuasion techniques (urgency, scarcity, social proof)
- Landing page copy alignment

Responsibilities:
- Generate multiple ad headline variants
- Create platform-specific ad descriptions
- Design conversion-optimized CTAs
- Generate A/B test variants
- Validate ad policy compliance
- Return structured AdCopyDraft

Does NOT:
- Create organic content (Marketing Content Specialist handles this)
- Format for organic posts (Platform Adaptation Specialist handles this)
- Persist to database (PM handles persistence with HITL)

Note:
Different from Marketing Content Specialist:
- Marketing Content: Campaign narratives, organic posts, storytelling (engagement-focused)
- Ad Copy: Paid ad copy, conversion-optimized, compliance-checked (conversion-focused)

Architecture Pattern:
- SubAgent dict format (NOT create_agent)
- Returns structured Pydantic models
- PM orchestrates delegation and approval
"""

from typing import Any

from langchain.tools import tool
from pydantic import BaseModel, Field

from autifyme_agents.core.prompt_loader import load_prompt

# =============================================================================
# Data Models - Ad Copy Specialist Outputs
# =============================================================================


class AdHeadlineVariant(BaseModel):
    """Ad headline variant for A/B testing."""

    headline_text: str = Field(..., description="Ad headline text")
    character_count: int = Field(..., description="Character count")
    persuasion_technique: str = Field(
        ..., description="Persuasion technique used (urgency, scarcity, benefit, social_proof, question)"
    )
    target_emotion: str = Field(
        ..., description="Target emotion (excitement, fear, curiosity, trust)"
    )
    platform_compatibility: list[str] = Field(
        ..., description="Compatible platforms (facebook, google_ads, etc.)"
    )


class AdDescriptionVariant(BaseModel):
    """Ad description variant."""

    description_text: str = Field(..., description="Ad description text")
    character_count: int = Field(..., description="Character count")
    key_benefits_highlighted: list[str] = Field(
        ..., description="Key benefits emphasized in this variant"
    )
    cta_included: str = Field(..., description="Call-to-action included")
    platform: str = Field(..., description="Target platform")


class ABTestVariant(BaseModel):
    """Complete A/B test variant (headline + description + CTA)."""

    variant_name: str = Field(..., description="Variant identifier (A, B, C, etc.)")
    headline: str = Field(..., description="Ad headline for this variant")
    description: str = Field(..., description="Ad description for this variant")
    cta: str = Field(..., description="Call-to-action for this variant")
    hypothesis: str = Field(
        ..., description="Testing hypothesis - what we expect to learn from this variant"
    )
    target_audience_fit: str = Field(
        ..., description="Which audience segment this variant targets best"
    )


class AdCopyDraft(BaseModel):
    """Complete ad copy from Ad Copy Specialist."""

    # Ad headlines
    ad_headlines: list[AdHeadlineVariant] = Field(
        ..., description="Multiple ad headline variants (5-7 variants)"
    )

    # Ad descriptions
    ad_descriptions: list[AdDescriptionVariant] = Field(
        ..., description="Multiple ad description variants per platform (3-5 per platform)"
    )

    # A/B test variants
    ab_test_variants: list[ABTestVariant] = Field(
        ..., description="Complete A/B test variants (3-5 complete ads)"
    )

    # Compliance
    policy_compliance_check: dict[str, bool] = Field(
        ..., description="Compliance status per platform"
    )
    compliance_notes: str = Field(
        ..., description="Compliance considerations and warnings"
    )

    # Persuasion strategy
    persuasion_framework: str = Field(
        ..., description="Overall persuasion strategy used (AIDA, PAS, FAB, etc.)"
    )
    conversion_optimization_notes: str = Field(
        ..., description="How copy is optimized for conversion"
    )

    # Landing page alignment
    landing_page_recommendations: str | None = Field(
        None, description="Landing page copy alignment recommendations"
    )

    # Analysis metadata
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in ad copy effectiveness"
    )
    ad_copy_notes: str = Field(
        ..., description="Additional ad copy insights and testing recommendations"
    )


# =============================================================================
# Tools - Ad Copy Analysis
# =============================================================================


@tool
def generate_ab_test_hypotheses(
    campaign_objective: str, num_variants: int = 3
) -> dict[str, Any]:
    """
    Generate A/B test hypotheses based on campaign objective.

    Args:
        campaign_objective: Campaign objective (sales, awareness, engagement, etc.)
        num_variants: Number of test variants to suggest

    Returns:
        Dict with test variant hypotheses and testing strategy
    """
    # Generate test hypotheses based on objective
    hypothesis_templates = {
        "sales": [
            "Price-focused headline will drive more conversions than benefit-focused",
            "Urgency-based copy (limited time) will outperform evergreen messaging",
            "Specific discount percentage will convert better than generic 'Save Now'",
        ],
        "awareness": [
            "Question-based headlines will generate more engagement than statements",
            "Emotional storytelling will resonate more than feature-focused copy",
            "Inclusive language ('Join us') will outperform exclusive ('For select customers')",
        ],
        "engagement": [
            "Interactive CTAs ('Try it now') will outperform passive ('Learn more')",
            "User-generated content themes will engage more than brand messaging",
            "Challenge-based copy will drive more participation than benefit-based",
        ],
    }

    hypotheses = hypothesis_templates.get(
        campaign_objective.lower(), hypothesis_templates["sales"]
    )[:num_variants]

    return {
        "campaign_objective": campaign_objective,
        "test_variants": [
            {
                "variant_id": f"Variant {chr(65 + i)}",
                "hypothesis": hypothesis,
                "testing_focus": "headline" if i == 0 else "description" if i == 1 else "cta",
            }
            for i, hypothesis in enumerate(hypotheses)
        ],
        "testing_strategy": f"Test {num_variants} variants with focus on {campaign_objective} optimization",
        "minimum_sample_size": "1000 impressions per variant for statistical significance",
    }


@tool
def validate_ad_policy_compliance(
    ad_text: str, platform: str
) -> dict[str, Any]:
    """
    Validate ad copy against platform advertising policies.

    Args:
        ad_text: Ad copy text to validate
        platform: Platform name (facebook, google_ads, etc.)

    Returns:
        Dict with compliance status and recommendations
    """
    # Common policy violations to check
    violations = []
    warnings = []

    ad_lower = ad_text.lower()

    # Check for prohibited words/phrases (simplified - real implementation uses platform APIs)
    prohibited_words = {
        "facebook": ["click here", "100% guarantee", "miracle", "cure"],
        "google_ads": ["click here", "best", "#1", "free money"],
    }

    platform_prohibited = prohibited_words.get(platform.lower(), [])
    for word in platform_prohibited:
        if word in ad_lower:
            violations.append(f"Contains prohibited phrase: '{word}'")

    # Check for excessive capitalization
    caps_ratio = sum(1 for c in ad_text if c.isupper()) / max(len(ad_text), 1)
    if caps_ratio > 0.5:
        warnings.append("Excessive capitalization - may trigger policy review")

    # Check for excessive punctuation
    if ad_text.count("!") > 2:
        warnings.append("Multiple exclamation marks - may appear spammy")

    is_compliant = len(violations) == 0

    return {
        "platform": platform,
        "is_compliant": is_compliant,
        "violations": violations,
        "warnings": warnings,
        "recommendation": (
            "Revise ad copy to address violations before submission"
            if not is_compliant
            else "Ad copy appears compliant - review with platform guidelines before final submission"
        ),
        "severity": "critical" if violations else "warning" if warnings else "pass",
    }


# =============================================================================
# Specialist Factory
# =============================================================================


def create_ad_copy_specialist() -> dict[str, Any]:
    """
    Create Ad Copy Specialist as SubAgent spec.

    Specialist Responsibilities:
    - Generate multiple ad headline variants
    - Create platform-specific ad descriptions
    - Design conversion-optimized CTAs
    - Generate A/B test variants
    - Validate ad policy compliance
    - Return AdCopyDraft for PM review

    Architecture:
    - SubAgent dict format (DeepAgents pattern)
    - Ad copy tools only (no persistence)
    - Returns structured Pydantic model
    - PM handles HITL and persistence

    Returns:
        SubAgent spec with:
        - name: specialist identifier
        - description: delegation criteria
        - tools: ad copy creation tools
        - system_prompt: domain expertise instructions
    """
    system_prompt = load_prompt("specialists/ad_copy_specialist.prompt")

    description = (
        "Creates paid ad copy with A/B test variants and compliance validation. "
        "Adapts to missing platforms (defaults to Facebook + Google). "
        "Self-reviews compliance (validates against platform policies). "
        "Returns AdCopyDraft. "
        "Runs AFTER Marketing Content (needs messaging). Can run PARALLEL with Platform Adaptation."
    )

    # Tools for ad copy creation
    tools = [
        generate_ab_test_hypotheses,  # A/B testing strategy
        validate_ad_policy_compliance,  # Policy compliance
    ]

    return {
        "name": "ad_copy_specialist",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
    }
