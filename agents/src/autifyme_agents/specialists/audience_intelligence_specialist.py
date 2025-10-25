"""
Audience Intelligence Specialist - Customer segmentation and behavioral targeting.

Domain Expertise:
- Customer segmentation (demographics, behavior, purchase history, engagement)
- Persona matching to products and campaigns
- Channel preference detection (who's active on which platform)
- Behavioral targeting (browse history, cart abandonment, purchase patterns)
- Lookalike audience suggestions
- Custom audience creation for retargeting

Responsibilities:
- Analyze campaign strategy and product context
- Create customer segments aligned with campaign objectives
- Identify channel preferences for each segment
- Define behavioral targeting parameters
- Recommend lookalike and retargeting audiences
- Return structured AudienceTargetingDraft

Does NOT:
- Create content (Marketing Content Specialist handles this)
- Format for platforms (Platform Adaptation Specialist handles this)
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
# Data Models - Audience Intelligence Specialist Outputs
# =============================================================================


class CustomerSegmentDraft(BaseModel):
    """Draft customer segment definition."""

    segment_label: str = Field(..., description="Segment name/label")
    segment_type: str = Field(
        ..., description="Segment type (b2b, b2c, d2c, wholesale, enterprise, retail)"
    )
    demographics: str | None = Field(
        None, description="Demographic characteristics (age, gender, location, income)"
    )
    behavioral_traits: list[str] = Field(
        default_factory=list, description="Behavioral characteristics and patterns"
    )
    pain_points: list[str] = Field(
        default_factory=list, description="Customer pain points this segment experiences"
    )
    key_benefits: list[str] = Field(
        default_factory=list, description="Key product benefits for this segment"
    )
    tone: str = Field(
        ..., description="Messaging tone (professional, casual, technical, emotional, educational, aspirational)"
    )
    primary_channels: list[str] = Field(
        ..., description="Preferred marketing channels (facebook, instagram, linkedin, email, etc.)"
    )
    content_formats: list[str] = Field(
        default_factory=list, description="Preferred content formats (video, carousel, article, etc.)"
    )
    estimated_reach: int | None = Field(
        None, description="Estimated audience size for this segment"
    )
    targeting_rationale: str = Field(
        ..., description="Why this segment was identified and how to target them"
    )


class AudienceTargetingDraft(BaseModel):
    """Complete audience targeting strategy from Audience Intelligence Specialist."""

    # Segment definitions
    customer_segments: list[CustomerSegmentDraft] = Field(
        ..., description="Identified customer segments for this campaign"
    )

    # Targeting parameters
    total_estimated_reach: int | None = Field(
        None, description="Total estimated audience reach across all segments"
    )
    primary_segment: str = Field(
        ..., description="Primary target segment (highest priority)"
    )

    # Channel strategy
    channel_segment_mapping: dict[str, list[str]] = Field(
        ..., description="Which segments to target on which channels"
    )

    # Advanced targeting
    lookalike_recommendations: list[str] = Field(
        default_factory=list, description="Lookalike audience expansion strategies"
    )
    retargeting_opportunities: list[str] = Field(
        default_factory=list, description="Retargeting audience opportunities"
    )

    # Geographic and temporal
    geographic_targeting: list[str] = Field(
        default_factory=list, description="Geographic regions to target"
    )
    timing_recommendations: str | None = Field(
        None, description="Best times/days to reach these audiences"
    )

    # Analysis metadata
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in audience targeting strategy"
    )
    targeting_notes: str = Field(
        ..., description="Additional targeting insights and recommendations"
    )


# =============================================================================
# Tools - Audience Intelligence Analysis
# =============================================================================


@tool
def suggest_customer_segments(
    campaign_objective: str, product_category: str
) -> dict[str, Any]:
    """
    Suggest customer segments based on campaign objective and product category.

    Args:
        campaign_objective: Campaign objective (sales, awareness, engagement, etc.)
        product_category: Product category (e.g., "footwear", "water bottles", "apparel")

    Returns:
        Dict with suggested segments and targeting approaches
    """
    # Segment suggestion logic based on objective and category
    base_segments = {
        "sales": ["high_intent_shoppers", "cart_abandoners", "past_purchasers"],
        "awareness": ["broad_audience", "interest_based", "lookalike_audiences"],
        "engagement": ["brand_followers", "content_engagers", "community_members"],
        "retention": ["existing_customers", "lapsed_customers", "vip_customers"],
        "leads": ["information_seekers", "comparison_shoppers", "email_subscribers"],
    }

    suggested_segments = base_segments.get(
        campaign_objective.lower(), ["general_audience"]
    )

    return {
        "suggested_segments": suggested_segments,
        "primary_segment": suggested_segments[0] if suggested_segments else "general_audience",
        "rationale": f"For {campaign_objective} campaigns targeting {product_category}, these segments typically show highest engagement and conversion rates",
        "targeting_tips": [
            f"Focus on {suggested_segments[0]} for primary targeting",
            "Create lookalike audiences from best performers",
            "Use retargeting for cart abandoners and site visitors",
        ],
    }


@tool
def map_segments_to_channels(
    segments: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Map customer segments to optimal marketing channels.

    Args:
        segments: List of segments with characteristics
            Example: [
                {
                    "segment_label": "Young Professionals",
                    "demographics": "25-35, urban, college-educated",
                    "segment_type": "b2c"
                }
            ]

    Returns:
        Dict with channel recommendations per segment
    """
    # Channel mapping logic
    channel_mapping = {}

    for segment in segments:
        segment_label = segment.get("segment_label", "unknown")
        segment_type = segment.get("segment_type", "b2c")
        demographics = segment.get("demographics", "")

        # Simple mapping logic (can be enhanced with ML)
        recommended_channels = []

        if segment_type in ["b2b", "enterprise"]:
            recommended_channels = ["linkedin", "email", "website", "google_ads"]
        elif "young" in demographics.lower() or "18-24" in demographics:
            recommended_channels = ["instagram", "tiktok", "youtube", "snapchat"]
        elif "professional" in demographics.lower():
            recommended_channels = ["linkedin", "facebook", "email", "twitter"]
        else:
            recommended_channels = ["facebook", "instagram", "email", "youtube"]

        channel_mapping[segment_label] = {
            "primary_channels": recommended_channels[:3],
            "secondary_channels": recommended_channels[3:] if len(recommended_channels) > 3 else [],
            "rationale": f"{segment_type.upper()} segment typically active on {', '.join(recommended_channels[:3])}",
        }

    return {
        "channel_mapping": channel_mapping,
        "cross_segment_channels": list({
            ch
            for mapping in channel_mapping.values()
            for ch in mapping["primary_channels"]
        }),
    }


# =============================================================================
# Specialist Factory
# =============================================================================


def create_audience_intelligence_specialist() -> dict[str, Any]:
    """
    Create Audience Intelligence Specialist as SubAgent spec.

    Specialist Responsibilities:
    - Analyze campaign strategy and product context
    - Create customer segments aligned with objectives
    - Identify channel preferences for each segment
    - Define behavioral targeting parameters
    - Recommend lookalike and retargeting audiences
    - Return AudienceTargetingDraft for PM review

    Architecture:
    - SubAgent dict format (DeepAgents pattern)
    - Targeting analysis tools only (no persistence, no content creation)
    - Returns structured Pydantic model
    - PM handles HITL and persistence

    Returns:
        SubAgent spec with:
        - name: specialist identifier
        - description: delegation criteria
        - tools: audience analysis tools
        - system_prompt: domain expertise instructions
    """
    system_prompt = load_prompt("specialists/audience_intelligence_specialist.prompt")

    description = (
        "Creates customer segments and maps to channels. "
        "Adapts to limited data (builds hypothesis segments if no customer data). "
        "Self-reviews segments (validates distinctness and actionability). "
        "Returns AudienceTargetingDraft. "
        "Run AFTER Campaign Strategy (needs objectives). Can run PARALLEL with Content + Visual Assets."
    )

    # Tools for audience intelligence analysis
    tools = [
        suggest_customer_segments,  # Segment recommendations
        map_segments_to_channels,  # Channel mapping
    ]

    return {
        "name": "audience_intelligence_specialist",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
    }
