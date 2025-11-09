"""
Content & SEO Specialist - Marketing content generation and SEO optimization.

Domain Expertise:
- Product copywriting (descriptions, feature bullets)
- SEO optimization (keywords, meta tags, structured data)
- Platform-specific content (Instagram, Facebook, LinkedIn, Google Shopping)
- Brand voice consistency
- Content localization and tone adaptation

Responsibilities:
- Generate product descriptions (short, long, feature bullets)
- Create SEO elements (title, meta description, keywords, schema.org)
- Produce platform-specific content (social media, ecommerce)
- Adapt tone for customer segments
- Return ContentSEODraft for PM review

Does NOT:
- Persist content (PM handles after approval)
- Publish to platforms (future automation)
- Create images/graphics (Visual Assets Specialist handles this)

Architecture Pattern:
- SubAgent dict format
- Returns structured Pydantic models
- PM orchestrates and approves
"""

import logging
from typing import Any

from langchain.tools import tool
from pydantic import BaseModel, Field

from autifyme_agents.core.config import settings
from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

# =============================================================================
# Data Models - Content & SEO Specialist Outputs
# =============================================================================


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


# =============================================================================
# Tools - Content & SEO Generation
# =============================================================================


@tool
def generate_product_description(
    product_name: str,
    key_features: list[str],
    material: str | None,
    brand_voice: str,
    target_audience: str,
    max_length: int = 500,
) -> dict[str, Any]:
    """
    Generate product description aligned with brand voice.

    Args:
        product_name: Product family name
        key_features: List of key product features
        material: Material description
        brand_voice: Company brand voice
        target_audience: Target customer description
        max_length: Max description length

    Returns:
        Product description with short and long variants
    """
    # Use LLM to generate brand-aligned description
    llm = get_llm(provider="google", model="gemini-2.5-flash", temperature=0.7)

    prompt = f"""Generate compelling product description for ecommerce.

Product: {product_name}
Key Features: {', '.join(key_features)}
Material: {material or 'N/A'}
Brand Voice: {brand_voice}
Target Audience: {target_audience}

Generate TWO versions:
1. SHORT (< 160 characters): For search results, social previews
2. LONG (< {max_length} characters): For product pages, detailed view

Requirements:
- Match brand voice: {brand_voice}
- Appeal to: {target_audience}
- Highlight key benefits over features
- SEO-friendly with natural keyword use
- Compelling and conversion-focused

Format your response as JSON:
{{
    "short": "...",
    "long": "..."
}}
"""

    try:
        response = llm.invoke(prompt)
        content = response.content

        # Parse JSON response
        import json
        # Handle content as string (LangChain returns str or list)
        content_str = content if isinstance(content, str) else str(content)
        cleaned = content_str.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
        data = json.loads(cleaned)

        return {
            "short_description": data["short"][:160],
            "long_description": data["long"][:max_length],
            "generation_successful": True,
        }

    except Exception as e:
        # Fallback to template-based
        short = f"{product_name} - {key_features[0] if key_features else 'Quality product'}"
        long = f"{product_name}. {' '.join(key_features[:3])}. Perfect for {target_audience}."

        return {
            "short_description": short[:160],
            "long_description": long[:max_length],
            "generation_successful": False,
            "error": str(e),
        }


@tool
def generate_feature_bullets(
    key_features: list[str], brand_voice: str, max_bullets: int = 7
) -> list[str]:
    """
    Generate concise feature bullets.

    Args:
        key_features: Raw feature list
        brand_voice: Company brand voice
        max_bullets: Maximum number of bullets

    Returns:
        List of formatted feature bullets
    """
    # Check feature flag for LLM-based bullet generation
    if settings.ENABLE_LLM_BULLET_GENERATION:
        # TODO: Implement LLM-based bullet generation when enabled
        raise NotImplementedError("LLM-based bullet generation not yet implemented")

    # Fallback: Simple template-based formatting
    logger.warning(
        "Using template-based feature bullet formatting fallback. "
        "Enable ENABLE_LLM_BULLET_GENERATION for brand-aligned LLM generation."
    )

    bullets = []
    for feature in key_features[:max_bullets]:
        # Clean and format
        feature_clean = feature.strip()
        if not feature_clean.endswith((".", "!", "?")):
            feature_clean += "."
        bullets.append(feature_clean)

    return bullets


@tool
def generate_seo_elements(
    product_name: str,
    category: str,
    brand: str,
    short_description: str,
    keywords: list[str],
) -> dict[str, Any]:
    """
    Generate SEO meta tags and structured data.

    Args:
        product_name: Product name
        category: Product category
        brand: Brand name
        short_description: Short description (used for meta)
        keywords: Primary keywords

    Returns:
        SEO elements (title, meta description, schema.org)
    """
    # Meta title (< 60 chars)
    meta_title = f"{product_name} | {brand}"
    if len(meta_title) > 60:
        meta_title = f"{product_name[:40]}... | {brand}"

    # Meta description (< 160 chars)
    meta_description = short_description[:160]

    # Schema.org Product structured data
    schema_org = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product_name,
        "brand": {"@type": "Brand", "name": brand},
        "category": category,
        "description": short_description,
        # Offers will be added during persistence (price, availability)
    }

    return {
        "meta_title": meta_title,
        "meta_description": meta_description,
        "keywords": keywords[:15],  # Top 15 keywords
        "schema_org_data": schema_org,
    }


@tool
def generate_platform_content(
    platform: str,
    product_name: str,
    short_description: str,
    customer_segment_tone: str,
    key_features: list[str],
) -> dict[str, Any]:
    """
    Generate platform-specific content variant.

    Args:
        platform: Target platform (instagram, facebook, linkedin, etc.)
        product_name: Product name
        short_description: Product short description
        customer_segment_tone: Tone for target segment (casual, professional, etc.)
        key_features: Key features to highlight

    Returns:
        Platform-optimized content with metadata
    """
    platform_templates = {
        "instagram": {
            "content_type": "post",
            "template": f"✨ {product_name}\n\n{short_description}\n\n{' • '.join(key_features[:3])}\n\n",
            "metadata": {"recommended_aspect_ratio": "1:1", "max_hashtags": 30},
        },
        "facebook": {
            "content_type": "post",
            "template": f"{product_name}\n\n{short_description}\n\nKey Features:\n" + "\n".join([f"✓ {f}" for f in key_features[:5]]),
            "metadata": {"recommended_aspect_ratio": "1.91:1", "link_preview": True},
        },
        "linkedin": {
            "content_type": "post",
            "template": f"Introducing {product_name}\n\n{short_description}\n\nKey Benefits:\n" + "\n".join([f"• {f}" for f in key_features[:4]]),
            "metadata": {"tone": "professional", "include_company_tag": True},
        },
        "google_shopping": {
            "content_type": "catalog_description",
            "template": short_description,
            "metadata": {"character_limit": 5000, "include_gtin": True},
        },
    }

    template_data = platform_templates.get(
        platform,
        {
            "content_type": "description",
            "template": short_description,
            "metadata": {},
        },
    )

    # Generate hashtags for social platforms
    hashtags = []
    if platform in ["instagram", "facebook", "twitter"]:
        # Simple keyword-based hashtag generation
        words = product_name.split() + list(key_features[:3])
        hashtags = [f"#{word.replace(' ', '')}" for word in words[:5]]

    return {
        "platform": platform,
        "content_type": template_data["content_type"],
        "content_text": template_data["template"],
        "hashtags": hashtags,
        "content_metadata": template_data["metadata"],
    }


# =============================================================================
# Specialist Factory
# =============================================================================


def create_content_seo_specialist() -> dict[str, Any]:
    """
    Create Content & SEO Specialist as SubAgent spec.

    Specialist Responsibilities:
    - Generate product descriptions (short, long, feature bullets)
    - Create SEO elements (meta tags, keywords, schema.org)
    - Produce platform-specific content variants
    - Ensure brand voice alignment
    - Return ContentSEODraft for PM review

    Architecture:
    - SubAgent dict format
    - Generation tools only (no persistence)
    - Returns structured Pydantic model
    - PM handles HITL and persistence

    Returns:
        SubAgent spec with content generation tools
    """
    system_prompt = load_prompt("specialists/content_seo_specialist.prompt")

    description = (
        "Generates marketing content and SEO elements for products. "
        "Creates descriptions (short, long), feature bullets, meta tags, keywords, "
        "and platform-specific content (Instagram, Facebook, LinkedIn, Google Shopping). "
        "Ensures brand voice alignment and SEO best practices. "
        "Returns ContentSEODraft for PM review."
    )

    tools = [
        generate_product_description,
        generate_feature_bullets,
        generate_seo_elements,
        generate_platform_content,
    ]

    return {
        "name": "content_seo_specialist",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
    }
