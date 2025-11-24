"""
Platform Adaptation Specialist - Multi-platform content formatting and optimization.

Domain Expertise:
- Platform-specific content formatting (Facebook, Instagram, YouTube, X, WhatsApp, Amazon, Google Ads, Website)
- Character limit compliance for each platform
- Image size and aspect ratio optimization
- Platform best practices (hashtags, @mentions, emojis, formatting)
- Compliance with platform advertising policies

Platform Coverage:
- Facebook: Feed posts, Stories, Reels, Carousel ads
- Instagram: Feed posts, Stories, Reels, Shopping tags
- YouTube: Video titles, descriptions, tags, cards
- X (Twitter): Tweets, Threads, Twitter Cards
- WhatsApp Business: Business messages, Status updates
- Amazon: A+ Content, Enhanced descriptions, Sponsored ads
- Google Ads: Search ads, Display ads, Shopping ads
- Website/Landing Pages: Hero sections, CTAs, forms

Responsibilities:
- Format marketing content for each target platform
- Ensure character limit compliance
- Optimize images for platform requirements
- Apply platform best practices
- Validate platform policy compliance
- Return structured PlatformContentVariantsDraft

Does NOT:
- Create base content (Marketing Content Specialist handles this)
- Create paid ad copy (Ad Copy Specialist handles this)
- Persist to database (PM handles persistence with HITL)

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
# Data Models - Platform Adaptation Specialist Outputs
# =============================================================================


class PlatformContentVariant(BaseModel):
    """Content variant for a single platform."""

    platform: str = Field(
        ..., description="Platform name (facebook, instagram, youtube, twitter, linkedin, etc.)"
    )
    content_type: str = Field(
        ..., description="Content type (post, story, reel, video, ad, etc.)"
    )
    content_text: str = Field(..., description="Formatted content text")
    character_count: int = Field(..., description="Character count")
    character_limit: int | None = Field(
        None, description="Platform character limit (if applicable)"
    )
    hashtags: list[str] = Field(
        default_factory=list, description="Platform-specific hashtags"
    )
    mentions: list[str] = Field(
        default_factory=list, description="@ mentions (if applicable)"
    )
    image_specs: dict[str, Any] | None = Field(
        None, description="Image requirements (size, aspect ratio, format)"
    )
    platform_specific_notes: str = Field(
        ..., description="Platform-specific formatting notes and compliance"
    )


class PlatformContentVariantsDraft(BaseModel):
    """Complete platform adaptations from Platform Adaptation Specialist."""

    # Platform variants
    platform_variants: list[PlatformContentVariant] = Field(
        ..., description="Content formatted for each platform"
    )

    # Compliance checks
    all_compliant: bool = Field(
        ..., description="Whether all variants pass platform policy compliance"
    )
    compliance_issues: list[str] = Field(
        default_factory=list, description="Any compliance concerns found"
    )

    # Optimization recommendations
    platform_recommendations: dict[str, str] = Field(
        ..., description="Best practices per platform"
    )
    cross_platform_notes: str = Field(
        ..., description="Cross-platform consistency notes"
    )

    # Analysis metadata
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in platform adaptations"
    )
    adaptation_notes: str = Field(
        ..., description="Additional platform optimization insights"
    )


# =============================================================================
# Tools - Platform Adaptation Analysis
# =============================================================================


@tool
def validate_platform_character_limits(
    platform: str, content_text: str
) -> dict[str, Any]:
    """
    Validate content against platform character limits.

    Args:
        platform: Platform name (facebook, instagram, twitter, etc.)
        content_text: Content text to validate

    Returns:
        Dict with validation results and compliance status
    """
    # Platform character limits
    limits = {
        "facebook": {"post": 63206, "ad_headline": 40, "ad_description": 125},
        "instagram": {"caption": 2200, "bio": 150},
        "twitter": {"tweet": 280, "bio": 160},
        "youtube": {"title": 100, "description": 5000},
        "linkedin": {"post": 3000, "headline": 120},
        "whatsapp": {"message": 4096},
        "google_ads": {"headline": 30, "description": 90},
    }

    platform_limits = limits.get(platform.lower(), {"default": 1000})
    char_count = len(content_text)

    is_compliant = True
    limit_exceeded = None

    for content_type, limit in platform_limits.items():
        if char_count > limit:
            is_compliant = False
            limit_exceeded = f"{platform} {content_type} limit ({limit} chars)"
            break

    return {
        "platform": platform,
        "character_count": char_count,
        "is_compliant": is_compliant,
        "limit_exceeded": limit_exceeded,
        "available_limits": platform_limits,
        "recommendation": (
            f"Content exceeds {limit_exceeded}. Trim by {char_count - min(platform_limits.values())} characters"
            if not is_compliant
            else "Content length is compliant"
        ),
    }


@tool
def suggest_platform_hashtags(
    platform: str, content_theme: str, max_hashtags: int = 5
) -> dict[str, Any]:
    """
    Suggest platform-specific hashtags based on content theme.

    Args:
        platform: Platform name
        content_theme: Content theme or topic
        max_hashtags: Maximum number of hashtags to suggest

    Returns:
        Dict with hashtag suggestions and best practices
    """
    # Platform hashtag strategies
    hashtag_strategies = {
        "instagram": {
            "max_recommended": 30,
            "strategy": "Mix of broad, niche, and branded hashtags",
        },
        "twitter": {
            "max_recommended": 2,
            "strategy": "1-2 relevant trending hashtags",
        },
        "linkedin": {
            "max_recommended": 3,
            "strategy": "Professional industry-specific hashtags",
        },
        "facebook": {
            "max_recommended": 2,
            "strategy": "Minimal hashtag use, focus on organic reach",
        },
        "tiktok": {
            "max_recommended": 5,
            "strategy": "Trending + niche hashtags for discoverability",
        },
    }

    strategy = hashtag_strategies.get(
        platform.lower(), {"max_recommended": 5, "strategy": "Standard hashtag usage"}
    )

    # Generate sample hashtags (can be enhanced with real hashtag API)
    theme_clean = content_theme.lower().replace(" ", "")
    sample_hashtags = [
        f"#{theme_clean}",
        f"#{theme_clean}campaign",
        "#marketing",
        "#branding",
        "#socialmedia",
    ][:max_hashtags]

    return {
        "platform": platform,
        "suggested_hashtags": sample_hashtags,
        "max_recommended": strategy["max_recommended"],
        "strategy": strategy["strategy"],
        "best_practices": f"For {platform}, {strategy['strategy']}. Limit to {strategy['max_recommended']} hashtags.",
    }


# =============================================================================
# Specialist Factory
# =============================================================================


def create_platform_adaptation_specialist() -> dict[str, Any]:
    """
    Create Platform Adaptation Specialist as SubAgent spec.

    Specialist Responsibilities:
    - Format marketing content for each target platform
    - Ensure character limit compliance
    - Optimize for platform-specific requirements
    - Apply platform best practices (hashtags, formatting)
    - Validate platform policy compliance
    - Return PlatformContentVariantsDraft for PM review

    Architecture:
    - SubAgent dict format (DeepAgents pattern)
    - Platform formatting tools only (no persistence)
    - Returns structured Pydantic model
    - PM handles HITL and persistence

    Returns:
        SubAgent spec with:
        - name: specialist identifier
        - description: delegation criteria
        - tools: platform adaptation tools
        - system_prompt: domain expertise instructions
    """
    system_prompt = load_prompt("specialists/platform_adaptation_specialist.prompt")

    description = (
        "Formats content for 8+ platforms with character limits and hashtags. "
        "Adapts to unclear platforms (formats for Facebook, Instagram, Google). "
        "Self-reviews formatting (validates compliance and character limits). "
        "Returns PlatformContentVariantsDraft. "
        "Runs AFTER Marketing Content (needs base content). Can run PARALLEL with Ad Copy."
    )

    # Tools for platform adaptation
    tools = [
        validate_platform_character_limits,  # Character limit validation
        suggest_platform_hashtags,  # Hashtag strategy
    ]

    return {
        "name": "platform_adaptation_specialist",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
    }
