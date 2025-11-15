"""
Market Intelligence Specialist - Strategic positioning and customer segment analysis.

Domain Expertise:
- Price positioning strategy (budget, mid-range, premium, luxury)
- Customer segment identification (B2B, B2C, D2C)
- Industry-specific use case development
- Competitive differentiation analysis
- Multi-industry targeting for B2B products

Responsibilities:
- Analyze price positioning vs market
- Identify relevant customer segments with messaging strategies
- Develop industry-specific use cases (B2B multi-industry targeting)
- Return MarketIntelligenceDraft for PM review

Does NOT:
- Set final prices (returns pricing recommendations)
- Persist data (PM handles after approval)
- Generate actual content (Content Specialist handles this)

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
from autifyme_agents.core.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

# =============================================================================
# Data Models - Market Intelligence Specialist Outputs
# =============================================================================


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


# =============================================================================
# Tools - Market Intelligence Analysis
# =============================================================================


@tool
def analyze_price_positioning(
    product_type: str,
    material: str | None,
    brand_positioning: str,
    target_market: str,
    base_price: float | None = None,
) -> dict[str, Any]:
    """
    Analyze price positioning strategy.

    Args:
        product_type: Type of product (e.g., "apparel", "packaging", "footwear")
        material: Material quality indicator (e.g., "premium leather", "PET plastic")
        brand_positioning: Brand's positioning (from company context)
        target_market: Geographic/demographic market
        base_price: Current/proposed base price (optional)

    Returns:
        Price positioning analysis with recommendations
    """
    # Check feature flag for competitive pricing API
    if settings.ENABLE_COMPETITIVE_PRICING_API:
        # TODO: Implement competitive pricing API integration when enabled
        raise NotImplementedError("Competitive pricing API not yet implemented")

    # Fallback: Rule-based positioning logic
    logger.warning(
        "Using rule-based price positioning fallback. "
        "Enable ENABLE_COMPETITIVE_PRICING_API for real-time competitive data."
    )

    positioning_map = {
        "leather": "premium",
        "premium": "premium",
        "luxury": "luxury",
        "gold": "luxury",
        "silk": "luxury",
        "cashmere": "luxury",
        "organic": "premium",
        "sustainable": "premium",
        "plastic": "budget",
        "pet": "mid-range",
        "hdpe": "budget",
        "cotton": "mid-range",
        "polyester": "budget",
        "standard": "mid-range",
        "basic": "budget",
        "economy": "budget",
    }

    # Determine positioning from material and brand
    material_lower = (material or "").lower()
    brand_lower = brand_positioning.lower()

    suggested_positioning = "mid-range"  # Default
    confidence = 0.5

    # Check material indicators
    for keyword, position in positioning_map.items():
        if keyword in material_lower or keyword in brand_lower:
            suggested_positioning = position
            confidence = 0.8
            break

    # Price-based validation if provided
    if base_price:
        # Simple heuristics (adjust per industry)
        if base_price < 500:
            if suggested_positioning == "luxury":
                suggested_positioning = "premium"
        elif base_price > 5000 and suggested_positioning == "budget":
            suggested_positioning = "mid-range"

    # Generate pricing recommendations
    price_multipliers = {
        "budget": (0.7, 1.0),
        "mid-range": (1.0, 1.5),
        "premium": (1.5, 2.5),
        "luxury": (2.5, 5.0),
    }

    min_mult, max_mult = price_multipliers[suggested_positioning]

    if base_price:
        price_range: dict[str, Any] = {
            "min": round(base_price * min_mult, 2),
            "max": round(base_price * max_mult, 2),
            "recommended": round(base_price * ((min_mult + max_mult) / 2), 2),
        }
    else:
        price_range = {
            "min": 0.0,
            "max": 0.0,
            "recommended": 0.0,
            "multiplier_range": f"{min_mult}x - {max_mult}x base cost",
            "note": "Set base price for specific recommendations",
        }

    reasoning = (
        f"Positioning determined from material ({material or 'N/A'}), "
        f"brand positioning ({brand_positioning}), and target market ({target_market}). "
        f"{suggested_positioning.capitalize()} positioning aligns with quality indicators and brand strategy."
    )

    competitive_context = {
        "budget": "Focus on value proposition and cost efficiency. Compete on price and reliability.",
        "mid-range": "Balance of quality and affordability. Emphasize value for money and trusted quality.",
        "premium": "Higher quality, superior materials, brand reputation. Compete on quality and experience.",
        "luxury": "Exclusivity, craftsmanship, brand prestige. Compete on status and exceptional quality.",
    }[suggested_positioning]

    return {
        "suggested_positioning": suggested_positioning,
        "confidence": confidence,
        "reasoning": reasoning,
        "competitive_context": competitive_context,
        "pricing_recommendations": price_range,
    }


@tool
def identify_customer_segments(
    business_model: str, product_type: str, price_positioning: str
) -> list[dict[str, Any]]:
    """
    Identify relevant customer segments based on business model and product.

    Args:
        business_model: B2B, B2C, or D2C (from company context)
        product_type: Type of product
        price_positioning: Price positioning (budget, mid-range, premium, luxury)

    Returns:
        List of relevant customer segments with messaging strategies
    """
    segments = []

    # B2B segments
    if business_model.upper() in ["B2B", "BOTH"]:
        segments.append({
            "segment_type": "b2b",
            "segment_label": "Business Buyers",
            "tone": "professional",
            "key_benefits": [
                "Reliable bulk supply",
                "Consistent quality",
                "Competitive wholesale pricing",
                "Scalable order volumes",
            ],
            "pain_points": [
                "Supply chain reliability",
                "Quality consistency",
                "Cost optimization",
                "Delivery timelines",
            ],
            "primary_channels": ["linkedin", "email", "direct_sales", "trade_shows"],
            "content_formats": ["case_study", "technical_specs", "roi_calculator", "webinar"],
            "pricing_notes": "Volume-based pricing, bulk discounts, contract terms",
            "confidence": 0.95,
            "reasoning": "Company operates B2B model, professional procurement segment is primary",
        })

        if price_positioning in ["premium", "luxury"]:
            segments.append({
                "segment_type": "enterprise",
                "segment_label": "Enterprise Clients",
                "tone": "professional",
                "key_benefits": [
                    "Premium quality for brand alignment",
                    "White-glove service",
                    "Custom solutions",
                    "Long-term partnerships",
                ],
                "pain_points": [
                    "Brand reputation risk",
                    "Quality standards compliance",
                    "Vendor reliability",
                ],
                "primary_channels": ["direct_sales", "linkedin", "industry_events"],
                "content_formats": ["case_study", "custom_presentation", "executive_brief"],
                "pricing_notes": "Premium tier pricing, custom contracts, SLA-based pricing",
                "confidence": 0.85,
                "reasoning": "Premium positioning attracts enterprise clients seeking quality assurance",
            })

    # B2C segments
    if business_model.upper() in ["B2C", "D2C", "BOTH"]:
        if price_positioning in ["budget", "mid-range"]:
            segments.append({
                "segment_type": "b2c",
                "segment_label": "Value-Conscious Consumers",
                "tone": "casual",
                "key_benefits": [
                    "Affordable pricing",
                    "Good quality for price",
                    "Everyday reliability",
                ],
                "pain_points": [
                    "Budget constraints",
                    "Quality concerns at low prices",
                    "Finding trusted brands",
                ],
                "primary_channels": ["instagram", "facebook", "google_shopping", "marketplace"],
                "content_formats": ["carousel", "short_video", "ugc", "reviews"],
                "pricing_notes": "Competitive pricing, seasonal discounts, bundle offers",
                "confidence": 0.9,
                "reasoning": "Budget/mid-range positioning targets value-conscious consumers",
            })
        else:
            segments.append({
                "segment_type": "b2c",
                "segment_label": "Premium Consumers",
                "tone": "aspirational",
                "key_benefits": [
                    "Superior quality",
                    "Status and prestige",
                    "Exceptional experience",
                    "Exclusivity",
                ],
                "pain_points": [
                    "Difficulty finding premium products",
                    "Quality verification",
                    "Brand authenticity",
                ],
                "primary_channels": ["instagram", "pinterest", "brand_website", "influencers"],
                "content_formats": ["lifestyle_photography", "brand_story", "influencer_collab"],
                "pricing_notes": "Premium pricing, limited editions, exclusive offers",
                "confidence": 0.85,
                "reasoning": "Premium/luxury positioning targets aspirational consumers",
            })

    # D2C specific
    if business_model.upper() == "D2C":
        segments.append({
            "segment_type": "d2c",
            "segment_label": "Direct-to-Consumer Enthusiasts",
            "tone": "casual",
            "key_benefits": [
                "Direct brand relationship",
                "Transparent pricing",
                "Brand story connection",
                "Community engagement",
            ],
            "pain_points": [
                "Avoiding middleman markup",
                "Seeking authentic brands",
                "Wanting brand connection",
            ],
            "primary_channels": ["instagram", "brand_website", "email", "community"],
            "content_formats": ["behind_the_scenes", "founder_story", "community_ugc"],
            "pricing_notes": "Direct pricing, subscription options, loyalty rewards",
            "confidence": 0.9,
            "reasoning": "D2C model attracts consumers seeking direct brand relationships",
        })

    return segments


@tool
def develop_industry_use_cases(
    product_type: str, naics_codes: list[str]
) -> list[dict[str, Any]]:
    """
    Develop industry-specific use cases for B2B multi-industry targeting.

    Args:
        product_type: Type of product
        naics_codes: NAICS codes from taxonomy specialist

    Returns:
        Industry-specific use cases with benefits and compliance notes
    """
    # Check feature flag for LLM-generated use cases
    if settings.ENABLE_LLM_USE_CASE_GENERATION:
        # TODO: Implement LLM-based use case generation when enabled
        raise NotImplementedError("LLM-based use case generation not yet implemented")

    # Fallback: Industry-specific use case templates
    logger.warning(
        "Using template-based industry use cases fallback. "
        "Enable ENABLE_LLM_USE_CASE_GENERATION for custom LLM-generated use cases."
    )

    use_case_templates = {
        "packaging": {
            "311": {  # Food Manufacturing
                "use_case": "Food-grade packaging ensuring product freshness and safety",
                "benefits": [
                    "FDA-compliant food-grade materials",
                    "Moisture barrier protection",
                    "Extended shelf life",
                    "Consumer safety assurance",
                ],
                "compliance": "FDA 21 CFR 177, food contact compliance required",
            },
            "325": {  # Chemical Manufacturing
                "use_case": "Chemical-resistant packaging for safe storage and transport",
                "benefits": [
                    "Chemical resistance",
                    "Leak-proof sealing",
                    "DOT compliance for hazmat",
                    "Durability under stress",
                ],
                "compliance": "DOT hazmat regulations, UN packaging standards",
            },
            "3254": {  # Pharmaceutical
                "use_case": "Pharma-grade packaging meeting stringent quality standards",
                "benefits": [
                    "USP Class VI compliance",
                    "Tamper-evident features",
                    "Light protection",
                    "Sterility maintenance",
                ],
                "compliance": "USP standards, FDA cGMP, ISO 15378",
            },
        },
        "apparel": {
            "315": {  # Apparel Manufacturing
                "use_case": "Quality apparel for fashion-forward consumers",
                "benefits": [
                    "Trend-aligned designs",
                    "Durable construction",
                    "Comfortable materials",
                    "Size inclusivity",
                ],
                "compliance": "CPSIA compliance, labeling requirements",
            },
        },
    }

    use_cases: list[dict[str, Any]] = []

    for naics in naics_codes[:3]:  # Top 3 industries
        # Match product type and NAICS prefix
        for product_key, industry_map in use_case_templates.items():
            if product_key.lower() in product_type.lower():
                # Find matching NAICS (prefix match)
                for naics_prefix, template in industry_map.items():
                    if naics.startswith(naics_prefix):
                        use_cases.append({
                            "naics_code": naics,
                            "use_case": template["use_case"],
                            "industry_benefits": template["benefits"],
                            "compliance_notes": template["compliance"],
                            "is_primary_industry": len(use_cases) == 0,  # First is primary
                            "confidence": 0.85,
                            "reasoning": f"Product type {product_type} aligns with industry {naics}",
                        })
                        break

    # If no matches, create generic use case
    if not use_cases and naics_codes:
        use_cases.append({
            "naics_code": naics_codes[0],
            "use_case": f"Versatile {product_type} solution for industry applications",
            "industry_benefits": [
                "Quality and reliability",
                "Competitive pricing",
                "Scalable supply",
            ],
            "compliance_notes": None,
            "is_primary_industry": True,
            "confidence": 0.5,
            "reasoning": "Generic use case - needs specialist customization",
        })

    return use_cases


# =============================================================================
# Specialist Factory
# =============================================================================


def create_market_intelligence_specialist() -> dict[str, Any]:
    """
    Create Market Intelligence Specialist as SubAgent spec.

    Specialist Responsibilities:
    - Analyze price positioning strategy
    - Identify customer segments with messaging strategies
    - Develop industry-specific use cases for B2B targeting
    - Return MarketIntelligenceDraft for PM review

    Architecture:
    - SubAgent dict format
    - Analysis tools only (no persistence)
    - Returns structured Pydantic model
    - PM handles HITL and persistence

    Returns:
        SubAgent spec with market intelligence tools
    """
    system_prompt = load_prompt("specialists/market_intelligence_specialist.prompt")

    description = (
        "Analyzes market positioning and customer segments. "
        "Determines price positioning strategy (budget, mid-range, premium, luxury), "
        "identifies customer segments (B2B, B2C, D2C) with messaging strategies, "
        "and develops industry-specific use cases for B2B multi-industry targeting. "
        "Returns MarketIntelligenceDraft for PM review."
    )

    tools = [
        analyze_price_positioning,
        identify_customer_segments,
        develop_industry_use_cases,
    ]

    return {
        "name": "market_intelligence_specialist",
        "description": description,
        "tools": tools,
        "system_prompt": system_prompt,
    }
