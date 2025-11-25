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

from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.schemas.specialist_outputs.marketing_content import (
    CallToActionDraft,  # noqa: F401
    HeadlineVariantDraft,  # noqa: F401
    MarketingContentDraft,  # noqa: F401
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
    tools: list[Any] = []

    return {
        "name": "marketing_content_specialist",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
    }
