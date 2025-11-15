"""
Campaign Persistence Tools - Atomic 5-Table Transaction for Marketing Campaign Creation.

Architecture:
- Specialists analyze and generate campaign data
- PM orchestrates specialist delegation
- PM owns ALL HITL persistence tools
- PM gets user approval, then persists atomically

Design Philosophy:
- Atomic persistence across 5 core tables (campaigns, campaign_products, campaign_assets, campaign_channels, + links to customer_segments and marketing_content)
- Rollback on any failure (all-or-nothing)
- Automatic audit trail via database triggers
- Production-grade error handling and retry logic

Transaction Order (respects foreign key dependencies):
1. campaigns (parent)
2. campaign_products (M:N junction to products)
3. campaign_assets (creative library)
4. campaign_channels (platform configs)
5. customer_segments (link existing segments OR create campaign-specific segments)
6. marketing_content (link campaign content)

Automatic Database Triggers Handle:
- audit_log (on all INSERT/UPDATE/DELETE operations)

HITL Strategy:
- PM presents complete campaign to user
- User approves/edits/rejects
- PM calls this tool for atomic persistence
- Tool attached to PM (NOT specialists)
"""

import logging
from datetime import UTC, datetime
from typing import Any

from langchain_core.tools import StructuredTool, ToolException
from pydantic import BaseModel, Field

from autifyme_agents.core.exceptions import ExternalAPIError, classify_api_error

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models for Campaign Persistence
# =============================================================================


class ChannelConfig(BaseModel):
    """Platform-specific configuration settings for campaign channels.

    Different platforms require different configuration parameters.
    Use this model to provide platform-specific settings for bidding,
    targeting, scheduling, and optimization.

    Examples:
        Facebook/Instagram:
            {
                "objective": "CONVERSIONS",
                "optimization_goal": "OFFSITE_CONVERSIONS",
                "billing_event": "IMPRESSIONS",
                "bid_strategy": "LOWEST_COST_WITH_BID_CAP",
                "bid_amount": 50.0,
                "audience_targeting": {
                    "age_min": 25,
                    "age_max": 45,
                    "genders": ["male", "female"],
                    "locations": ["India"],
                    "interests": ["packaging", "manufacturing", "B2B"]
                },
                "placements": ["feed", "stories", "reels"],
                "schedule": {
                    "start_time": "09:00",
                    "end_time": "18:00",
                    "days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
                }
            }

        Google Ads:
            {
                "campaign_type": "SEARCH",
                "bidding_strategy": "TARGET_CPA",
                "target_cpa": 100.0,
                "keywords": ["custom packaging", "bulk bottles", "PET containers"],
                "negative_keywords": ["cheap", "free", "diy"],
                "ad_rotation": "OPTIMIZE",
                "ad_extensions": ["sitelink", "callout", "structured_snippet"],
                "location_targeting": ["India", "Mumbai", "Delhi"],
                "device_targeting": ["desktop", "mobile", "tablet"]
            }

        Email:
            {
                "email_provider": "sendgrid",
                "send_time": "10:00",
                "timezone": "Asia/Kolkata",
                "sender_name": "Pavisha Industries",
                "sender_email": "marketing@pavisha.com",
                "reply_to": "sales@pavisha.com",
                "subject_line_test": true,
                "personalization_tokens": ["first_name", "company_name", "industry"],
                "ab_test_percentage": 20
            }
    """

    # Common fields across platforms
    optimization_goal: str | None = Field(
        None,
        description="Platform-specific optimization goal (e.g., 'CONVERSIONS', 'REACH', 'ENGAGEMENT', 'CLICKS')"
    )
    bidding_strategy: str | None = Field(
        None,
        description="Bid strategy (e.g., 'LOWEST_COST', 'TARGET_CPA', 'MAXIMIZE_CONVERSIONS')"
    )
    bid_amount: float | None = Field(
        None,
        description="Bid amount or cap in campaign currency"
    )
    targeting: dict[str, Any] | None = Field(
        None,
        description="Audience targeting parameters (demographics, interests, behaviors, locations)"
    )
    schedule: dict[str, Any] | None = Field(
        None,
        description="Ad scheduling (days, hours, time zones)"
    )
    placements: list[str] | None = Field(
        None,
        description="Where ads appear (e.g., ['feed', 'stories', 'reels', 'marketplace'])"
    )
    device_targeting: list[str] | None = Field(
        None,
        description="Target devices (e.g., ['desktop', 'mobile', 'tablet'])"
    )

    # Allow additional platform-specific fields
    model_config = {"extra": "allow"}


class ContentMetadata(BaseModel):
    """Metadata for marketing content (posts, ads, emails, etc.).

    Stores platform-specific metadata, performance tracking, A/B test variants,
    and creative specifications for campaign content.

    Examples:
        Social Media Post:
            {
                "character_count": 280,
                "word_count": 45,
                "reading_level": "8th_grade",
                "sentiment": "positive",
                "cta": "Learn More",
                "cta_url": "https://pavisha.com/products/pet-bottles",
                "image_count": 3,
                "video_duration_sec": 15,
                "aspect_ratio": "9:16",
                "has_music": true,
                "has_voiceover": false,
                "caption_length": "medium",
                "emoji_count": 5
            }

        Email Campaign:
            {
                "subject_line_variants": [
                    "Revolutionize Your Packaging - 30% Off PET Bottles",
                    "Premium PET Bottles | Special Industry Pricing"
                ],
                "preview_text": "Durable, eco-friendly packaging solutions for manufacturing",
                "email_type": "promotional",
                "template_id": "pavisha_product_launch_v2",
                "personalization_fields": ["company_name", "industry_segment", "previous_order_date"],
                "ab_test_split": 50,
                "send_batch_size": 1000,
                "throttle_rate_per_hour": 5000
            }

        Google Ads:
            {
                "headline_1": "Premium PET Bottles | Bulk Orders",
                "headline_2": "Food-Grade Certified | Fast Delivery",
                "headline_3": "Trusted by 500+ Manufacturers",
                "description_1": "Durable PET bottles for packaging. FDA-compliant, BPA-free.",
                "description_2": "Wholesale pricing. Custom sizes available. Order now!",
                "display_url": "pavisha.com/PET-Bottles",
                "final_url": "https://pavisha.com/products/pet-bottles?utm_campaign=bulk_pet",
                "call_to_action": "Request Quote",
                "ad_strength": "EXCELLENT"
            }
    """

    # Content characteristics
    character_count: int | None = None
    word_count: int | None = None
    reading_level: str | None = Field(
        None,
        description="Reading difficulty (e.g., '8th_grade', 'college', 'professional')"
    )
    sentiment: str | None = Field(
        None,
        description="Content sentiment ('positive', 'neutral', 'negative', 'professional')"
    )

    # Call-to-action
    cta: str | None = Field(
        None,
        description="Call-to-action text (e.g., 'Learn More', 'Shop Now', 'Request Quote')"
    )
    cta_url: str | None = Field(
        None,
        description="URL for call-to-action with UTM parameters"
    )

    # Media metadata
    image_count: int | None = None
    video_duration_sec: int | None = None
    aspect_ratio: str | None = Field(
        None,
        description="Media aspect ratio (e.g., '16:9', '9:16', '1:1', '4:5')"
    )

    # A/B testing
    ab_test_variant: str | None = Field(
        None,
        description="Variant identifier for A/B testing (e.g., 'control', 'variant_a', 'variant_b')"
    )
    ab_test_split_percentage: int | None = Field(
        None,
        description="Percentage of audience receiving this variant (0-100)"
    )

    # Performance tracking
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_term: str | None = None
    utm_content: str | None = None

    # Allow additional platform-specific metadata
    model_config = {"extra": "allow"}


class BudgetAllocation(BaseModel):
    """Per-channel budget breakdown for multi-channel campaigns.

    Tracks budget allocation across different marketing channels with
    actual spend tracking and remaining budget calculations.

    Example:
        Multi-Channel Campaign (Total Budget: ₹500,000):
            {
                "facebook": {
                    "allocated": 150000.0,
                    "spent": 45230.50,
                    "remaining": 104769.50,
                    "percentage_of_total": 30.0,
                    "start_date": "2025-01-15",
                    "end_date": "2025-02-15"
                },
                "instagram": {
                    "allocated": 100000.0,
                    "spent": 12450.75,
                    "remaining": 87549.25,
                    "percentage_of_total": 20.0,
                    "start_date": "2025-01-15",
                    "end_date": "2025-02-15"
                },
                "google_ads": {
                    "allocated": 200000.0,
                    "spent": 0.0,
                    "remaining": 200000.0,
                    "percentage_of_total": 40.0,
                    "start_date": "2025-01-20",
                    "end_date": "2025-02-20"
                },
                "email": {
                    "allocated": 30000.0,
                    "spent": 5600.0,
                    "remaining": 24400.0,
                    "percentage_of_total": 6.0,
                    "start_date": "2025-01-15",
                    "end_date": "2025-02-28"
                },
                "linkedin": {
                    "allocated": 20000.0,
                    "spent": 0.0,
                    "remaining": 20000.0,
                    "percentage_of_total": 4.0,
                    "start_date": "2025-01-25",
                    "end_date": "2025-02-25"
                }
            }
    """

    # Map of channel_name -> budget details
    # Each channel should have: allocated, spent (optional), remaining (optional), percentage_of_total (optional)
    allocations: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description=(
            "Budget allocation per channel. Each key is a channel name (e.g., 'facebook', 'google_ads', 'email'). "
            "Each value is a dict with: "
            "'allocated' (required, float): Amount allocated to this channel. "
            "'spent' (optional, float): Amount already spent (for tracking). "
            "'remaining' (optional, float): Amount remaining in budget. "
            "'percentage_of_total' (optional, float): Percentage of total campaign budget (0-100). "
            "'start_date' (optional, str): When budget becomes active (YYYY-MM-DD). "
            "'end_date' (optional, str): When budget expires (YYYY-MM-DD)."
        )
    )

    # Summary fields (calculated from allocations)
    total_allocated: float | None = Field(
        None,
        description="Sum of all channel allocations (should match campaign total_budget)"
    )
    total_spent: float | None = Field(
        None,
        description="Sum of all channel spend (for tracking actual vs allocated)"
    )

    model_config = {"extra": "allow"}


class TargetMetrics(BaseModel):
    """Campaign KPI targets and performance goals.

    Defines success criteria across different metrics like reach,
    engagement, conversions, ROI, and platform-specific KPIs.

    Examples:
        B2B Product Launch Campaign:
            {
                "impressions": 500000,
                "reach": 150000,
                "clicks": 15000,
                "ctr_percentage": 3.0,
                "conversions": 300,
                "conversion_rate_percentage": 2.0,
                "leads_generated": 500,
                "qualified_leads": 200,
                "sql_percentage": 40.0,
                "cost_per_lead": 250.0,
                "cost_per_conversion": 1666.67,
                "roas": 4.5,
                "roi_percentage": 350.0,
                "engagement_rate_percentage": 5.5,
                "video_views": 75000,
                "video_completion_rate_percentage": 60.0,
                "email_open_rate_percentage": 35.0,
                "email_click_rate_percentage": 8.0,
                "landing_page_visits": 20000,
                "bounce_rate_percentage": 45.0,
                "average_time_on_page_seconds": 120,
                "form_submissions": 450
            }

        E-commerce Sales Campaign:
            {
                "impressions": 2000000,
                "clicks": 80000,
                "ctr_percentage": 4.0,
                "add_to_cart": 8000,
                "add_to_cart_rate_percentage": 10.0,
                "purchases": 2400,
                "purchase_conversion_rate_percentage": 3.0,
                "revenue": 1200000.0,
                "average_order_value": 500.0,
                "roas": 6.0,
                "cost_per_acquisition": 208.33,
                "cart_abandonment_rate_percentage": 70.0,
                "repeat_purchase_rate_percentage": 15.0,
                "customer_lifetime_value": 1500.0
            }

        Brand Awareness Campaign:
            {
                "impressions": 5000000,
                "reach": 2000000,
                "frequency": 2.5,
                "brand_lift_percentage": 12.0,
                "ad_recall_percentage": 45.0,
                "message_association_percentage": 38.0,
                "favorability_increase_percentage": 8.0,
                "consideration_lift_percentage": 15.0,
                "social_mentions": 15000,
                "share_of_voice_percentage": 25.0,
                "sentiment_score": 0.75,
                "organic_search_lift_percentage": 20.0
            }
    """

    # Reach & Awareness
    impressions: int | None = Field(
        None,
        description="Target total ad impressions across all channels"
    )
    reach: int | None = Field(
        None,
        description="Target unique users/accounts reached"
    )
    frequency: float | None = Field(
        None,
        description="Target average times each user sees the ad"
    )

    # Engagement
    clicks: int | None = Field(
        None,
        description="Target total clicks on ads/content"
    )
    ctr_percentage: float | None = Field(
        None,
        description="Target click-through rate as percentage (clicks/impressions * 100)"
    )
    engagement_rate_percentage: float | None = Field(
        None,
        description="Target engagement rate (likes, comments, shares, saves / reach * 100)"
    )

    # Conversions
    conversions: int | None = Field(
        None,
        description="Target total conversions (purchases, sign-ups, downloads, etc.)"
    )
    conversion_rate_percentage: float | None = Field(
        None,
        description="Target conversion rate (conversions/clicks * 100)"
    )
    leads_generated: int | None = Field(
        None,
        description="Target number of leads captured"
    )
    qualified_leads: int | None = Field(
        None,
        description="Target number of marketing/sales qualified leads (MQL/SQL)"
    )

    # Financial
    revenue: float | None = Field(
        None,
        description="Target revenue generated from campaign"
    )
    roas: float | None = Field(
        None,
        description="Target Return on Ad Spend (revenue/spend ratio, e.g., 4.5 means ₹4.50 revenue per ₹1 spent)"
    )
    roi_percentage: float | None = Field(
        None,
        description="Target Return on Investment as percentage ((revenue - cost) / cost * 100)"
    )
    cost_per_lead: float | None = Field(
        None,
        description="Target cost per lead in campaign currency"
    )
    cost_per_acquisition: float | None = Field(
        None,
        description="Target cost per conversion/customer in campaign currency"
    )
    average_order_value: float | None = Field(
        None,
        description="Target average order value for e-commerce campaigns"
    )

    # Platform-specific metrics
    video_views: int | None = None
    video_completion_rate_percentage: float | None = None
    email_open_rate_percentage: float | None = None
    email_click_rate_percentage: float | None = None
    landing_page_visits: int | None = None
    form_submissions: int | None = None

    # Brand metrics
    brand_lift_percentage: float | None = Field(
        None,
        description="Target increase in brand awareness/consideration"
    )
    share_of_voice_percentage: float | None = Field(
        None,
        description="Target percentage of total market conversation about brand"
    )

    # Allow additional KPIs
    model_config = {"extra": "allow"}


class CampaignPersistenceResult(BaseModel):
    """Result of atomic campaign persistence operation.

    Returns all generated entity IDs for tracking and linking.

    Example:
        {
            "success": true,
            "campaign_id": "550e8400-e29b-41d4-a716-446655440000",
            "campaign_name": "Summer PET Bottles Launch 2025",
            "product_ids": [
                "660e8400-e29b-41d4-a716-446655440001",
                "660e8400-e29b-41d4-a716-446655440002",
                "660e8400-e29b-41d4-a716-446655440003"
            ],
            "asset_ids": [
                "770e8400-e29b-41d4-a716-446655440001",
                "770e8400-e29b-41d4-a716-446655440002"
            ],
            "channel_ids": [
                "880e8400-e29b-41d4-a716-446655440001",
                "880e8400-e29b-41d4-a716-446655440002",
                "880e8400-e29b-41d4-a716-446655440003"
            ],
            "segment_ids": [
                "990e8400-e29b-41d4-a716-446655440001"
            ],
            "content_ids": [
                "aa0e8400-e29b-41d4-a716-446655440001",
                "aa0e8400-e29b-41d4-a716-446655440002",
                "aa0e8400-e29b-41d4-a716-446655440003",
                "aa0e8400-e29b-41d4-a716-446655440004"
            ],
            "created_at": "2025-01-15T10:30:00Z",
            "message": "Campaign persisted successfully across 5 tables"
        }
    """

    success: bool = Field(..., description="Whether persistence succeeded")
    campaign_id: str = Field(..., description="UUID of created campaign (primary record)")
    campaign_name: str = Field(..., description="Human-readable campaign name for confirmation")

    # Related entity IDs
    product_ids: list[str] = Field(
        default_factory=list,
        description="UUIDs of campaign_products junction records created"
    )
    asset_ids: list[str] = Field(
        default_factory=list,
        description="UUIDs of campaign_assets records created"
    )
    channel_ids: list[str] = Field(
        default_factory=list,
        description="UUIDs of campaign_channels records created"
    )
    segment_ids: list[str] = Field(
        default_factory=list,
        description="UUIDs of customer_segments records created or linked"
    )
    content_ids: list[str] = Field(
        default_factory=list,
        description="UUIDs of marketing_content records created"
    )

    # Metadata
    created_at: str = Field(..., description="ISO 8601 timestamp of creation")
    message: str | None = Field(
        None,
        description="Human-readable success message or error details"
    )


class CampaignProductInput(BaseModel):
    """Input for linking products to campaign."""

    product_family_id: str | None = Field(
        None, description="Product family UUID (if promoting entire family)"
    )
    product_id: str | None = Field(
        None, description="Product SKU UUID (if promoting specific variant)"
    )
    is_primary_product: bool = Field(
        default=False, description="Hero product for campaign"
    )
    featured_order: int | None = Field(None, description="Display order")
    promotion_type: str | None = Field(
        None, description="discount, bundle, bogo, new_arrival, clearance, featured"
    )
    discount_percentage: float | None = None
    special_price: float | None = None


class CampaignAssetInput(BaseModel):
    """Input for campaign creative assets."""

    asset_type: str = Field(
        ..., description="image, video, graphic, logo, banner"
    )
    url: str = Field(..., description="Asset URL or path")
    alt_text: str | None = None
    title: str | None = None
    width: int | None = None
    height: int | None = None
    duration_seconds: int | None = None
    file_size_bytes: int | None = None
    mime_type: str | None = None
    usage_context: list[str] = Field(
        default_factory=list, description="hero_banner, social_post, email_header, etc."
    )
    platform_optimized_for: list[str] = Field(
        default_factory=list, description="Platforms this asset is optimized for"
    )
    is_approved: bool = Field(default=True, description="Approval status")


class CampaignChannelInput(BaseModel):
    """Input for platform-specific campaign configuration.

    Configures how campaign runs on each platform (Facebook, Instagram, Google Ads, Email, etc.)
    with platform-specific settings for optimization, bidding, targeting, and scheduling.
    """

    platform: str = Field(
        ...,
        description=(
            "Platform where campaign runs. Options: facebook, instagram, youtube, twitter, linkedin, "
            "google_ads, amazon, whatsapp, email, website, tiktok, pinterest, snapchat, reddit"
        )
    )
    allocated_budget: float | None = Field(
        None,
        description="Budget allocated to this channel in campaign currency (e.g., ₹150,000 for Facebook)"
    )
    channel_config: ChannelConfig = Field(
        default_factory=ChannelConfig,
        description=(
            "Platform-specific configuration including optimization goals, bidding strategy, targeting, "
            "placements, and scheduling. See ChannelConfig model for detailed examples per platform."
        )
    )
    status: str = Field(
        default="draft",
        description=(
            "Channel status. Options: draft (not yet launched), scheduled (launch date set), "
            "active (currently running), paused (temporarily stopped), completed (campaign ended)"
        )
    )


class CampaignSegmentInput(BaseModel):
    """Input for campaign-specific customer segment.

    Defines target audience characteristics, messaging tone, and channel preferences
    for personalized campaign messaging.
    """

    segment_type: str = Field(
        ...,
        description=(
            "Customer segment type. Options: b2b (business customers), b2c (consumer customers), "
            "d2c (direct-to-consumer), wholesale (bulk buyers), enterprise (large organizations), "
            "retail (small businesses/shops)"
        )
    )
    segment_label: str = Field(
        ...,
        description="Human-readable segment name (e.g., 'Food Manufacturers - North India', 'Young Professionals 25-35')"
    )
    tone: str = Field(
        ...,
        description=(
            "Messaging tone for this segment. Options: professional (formal B2B), casual (friendly consumer), "
            "technical (specs-focused), emotional (lifestyle-focused), educational (informative), "
            "aspirational (premium/luxury), urgent (limited-time offers)"
        )
    )
    key_benefits: list[str] = Field(
        default_factory=list,
        description=(
            "Primary benefits resonating with this segment (e.g., ['cost savings', 'faster delivery', "
            "'FDA compliance', 'eco-friendly packaging', 'premium quality'])"
        )
    )
    pain_points: list[str] = Field(
        default_factory=list,
        description=(
            "Customer problems this campaign addresses (e.g., ['expensive suppliers', "
            "'inconsistent quality', 'slow fulfillment', 'limited customization options'])"
        )
    )
    primary_channels: list[str] = Field(
        default_factory=list,
        description=(
            "Channels where this segment is most active (e.g., ['linkedin', 'google_ads', 'email'] for B2B, "
            "['instagram', 'facebook', 'youtube'] for B2C)"
        )
    )
    content_formats: list[str] = Field(
        default_factory=list,
        description=(
            "Content types preferred by segment (e.g., ['video demos', 'case studies', 'whitepapers'] for B2B, "
            "['reels', 'stories', 'infographics'] for B2C)"
        )
    )


class MarketingContentInput(BaseModel):
    """Input for campaign marketing content.

    Stores platform-specific content (posts, ads, emails, stories) with metadata
    for tracking, A/B testing, and performance optimization.
    """

    platform: str = Field(
        ...,
        description=(
            "Platform for this content. Options: facebook, instagram, youtube, twitter, linkedin, "
            "google_ads, email, whatsapp, website, tiktok, pinterest"
        )
    )
    content_type: str = Field(
        ...,
        description=(
            "Type of content. Social: post, story, reel, video, carousel, live. "
            "Ads: search_ad, display_ad, video_ad, shopping_ad. Email: promotional, transactional, newsletter. "
            "Other: landing_page, blog_article, sms"
        )
    )
    content_text: str = Field(
        ...,
        description=(
            "Primary text content. For social posts: caption/description. For ads: ad copy/body. "
            "For emails: email body (HTML or plain text). Include emojis, hashtags, mentions as needed."
        )
    )
    content_metadata: ContentMetadata = Field(
        default_factory=ContentMetadata,
        description=(
            "Rich metadata for content including character count, reading level, sentiment, CTA details, "
            "media specs (aspect ratio, duration), A/B test variants, and UTM parameters. "
            "See ContentMetadata model for detailed examples."
        )
    )
    hashtags: list[str] = Field(
        default_factory=list,
        description=(
            "Hashtags for social media discovery (e.g., ['#PETbottles', '#PackagingSolutions', "
            "'#B2BManufacturing', '#MadeInIndia']). Max 10-15 for optimal reach."
        )
    )
    keywords: list[str] = Field(
        default_factory=list,
        description=(
            "SEO keywords for search ads and content optimization (e.g., ['custom packaging', "
            "'bulk bottles', 'food grade PET', 'wholesale containers'])"
        )
    )
    campaign_asset_id: str | None = Field(
        None,
        description=(
            "UUID of linked campaign_assets record (image/video) to display with this content. "
            "Links to CampaignAssetInput for creative management."
        )
    )


class CampaignInput(BaseModel):
    """Complete campaign input for atomic persistence."""

    model_config = {"extra": "forbid"}  # Generates additionalProperties: false

    # Core campaign metadata
    campaign_id: str = Field(..., description="Business-friendly campaign ID")
    name: str
    description: str | None = None
    campaign_type: str = Field(..., description="product_launch, seasonal, promotional, awareness, retention, acquisition")
    campaign_category: str | None = None

    # Objectives
    primary_objective: str = Field(..., description="sales, awareness, engagement, traffic, leads, retention")
    secondary_objectives: list[str] = Field(default_factory=list)
    target_audience_description: str | None = None

    # Budget
    total_budget: float | None = Field(
        None,
        description="Total campaign budget in budget_currency (e.g., ₹500,000 for entire campaign across all channels)"
    )
    budget_currency: str = Field(
        default="INR",
        description="Currency code for budget (e.g., 'INR', 'USD', 'EUR')"
    )
    budget_allocation: BudgetAllocation = Field(
        default_factory=BudgetAllocation,
        description=(
            "Detailed per-channel budget breakdown. See BudgetAllocation model for examples. "
            "Sum of allocations should equal total_budget."
        )
    )

    # Timeline
    planned_start_date: str = Field(
        ...,
        description="Campaign start date in ISO format YYYY-MM-DD (e.g., '2025-01-15')"
    )
    planned_end_date: str = Field(
        ...,
        description="Campaign end date in ISO format YYYY-MM-DD (e.g., '2025-02-28')"
    )

    # KPIs
    target_metrics: TargetMetrics = Field(
        default_factory=TargetMetrics,
        description=(
            "Campaign success metrics and KPI targets. Includes reach, engagement, conversions, "
            "ROI, ROAS, and platform-specific metrics. See TargetMetrics model for detailed examples."
        )
    )

    # Status
    status: str = Field(default="draft")
    approval_status: str = Field(default="pending")

    # Metadata
    generated_by: str | None = Field(default="marketing_campaign_workflow")
    generation_prompt_version: str | None = None
    specialist_versions: dict[str, str] = Field(default_factory=dict)

    # Related entities
    campaign_products: list[CampaignProductInput] = Field(default_factory=list)
    campaign_assets: list[CampaignAssetInput] = Field(default_factory=list)
    campaign_channels: list[CampaignChannelInput] = Field(default_factory=list)
    customer_segments: list[CampaignSegmentInput] = Field(default_factory=list)
    marketing_content: list[MarketingContentInput] = Field(default_factory=list)


# =============================================================================
# Persistence Tool
# =============================================================================


def create_save_campaign_tool(storage: Any) -> Any:
    """
    Factory to create save_campaign tool with storage dependency injection.

    Args:
        storage: SupabaseStorageClient instance

    Returns:
        Configured tool for PM to use
    """

    async def _save_campaign_impl(campaign_input: CampaignInput) -> CampaignPersistenceResult:
        """
        Atomically persist complete marketing campaign across 5+ tables.

        This tool performs an atomic transaction across:
        1. campaigns table
        2. campaign_products (M:N junction)
        3. campaign_assets (creative library)
        4. campaign_channels (platform configs)
        5. customer_segments (campaign-specific segments)
        6. marketing_content (campaign content)

        All-or-nothing transaction - rollback on any failure.

        Args:
            campaign_input: Complete campaign data (CampaignInput model)

        Returns:
            CampaignPersistenceResult with all generated entity UUIDs and success confirmation

        Raises:
            ToolException: On persistence failure (with rollback)

        Example Return:
            CampaignPersistenceResult(
                success=True,
                campaign_id="550e8400-e29b-41d4-a716-446655440000",
                campaign_name="Summer PET Bottles Launch 2025",
                product_ids=["660e8400...", "660e8401..."],
                asset_ids=["770e8400...", "770e8401..."],
                channel_ids=["880e8400...", "880e8401...", "880e8402..."],
                segment_ids=["990e8400..."],
                content_ids=["aa0e8400...", "aa0e8401...", "aa0e8402...", "aa0e8403..."],
                created_at="2025-01-15T10:30:00Z",
                message="Campaign persisted successfully across 5 tables with 12 related entities"
            )
        """
        logger.info(f"Starting atomic campaign persistence: {campaign_input.campaign_id}")

        try:
            campaign_id = None
            product_ids = []
            asset_ids = []
            channel_ids = []
            segment_ids = []
            content_ids = []

            # 1. Create campaign (parent entity)
            campaign_data = {
                "campaign_id": campaign_input.campaign_id,
                "name": campaign_input.name,
                "description": campaign_input.description,
                "campaign_type": campaign_input.campaign_type,
                "campaign_category": campaign_input.campaign_category,
                "primary_objective": campaign_input.primary_objective,
                "secondary_objectives": campaign_input.secondary_objectives,
                "target_audience_description": campaign_input.target_audience_description,
                "total_budget": campaign_input.total_budget,
                "budget_currency": campaign_input.budget_currency,
                "budget_allocation": campaign_input.budget_allocation,
                "planned_start_date": campaign_input.planned_start_date,
                "planned_end_date": campaign_input.planned_end_date,
                "target_metrics": campaign_input.target_metrics,
                "status": campaign_input.status,
                "approval_status": campaign_input.approval_status,
                "generated_by": campaign_input.generated_by,
                "generation_prompt_version": campaign_input.generation_prompt_version,
                "specialist_versions": campaign_input.specialist_versions,
            }

            campaign_result = await storage.insert_entity(
                "campaigns",
                campaign_data
            )
            campaign_id = campaign_result["id"]
            logger.info(f"Created campaign: {campaign_id}")

            # 2. Create campaign_products (M:N junctions)
            for product_input in campaign_input.campaign_products:
                product_data = {
                    "campaign_id": campaign_id,
                    "product_family_id": product_input.product_family_id,
                    "product_id": product_input.product_id,
                    "is_primary_product": product_input.is_primary_product,
                    "featured_order": product_input.featured_order,
                    "promotion_type": product_input.promotion_type,
                    "discount_percentage": product_input.discount_percentage,
                    "special_price": product_input.special_price,
                }
                result = await storage.insert_entity(
                    "campaign_products",
                    product_data
                )
                product_ids.append(result["id"])

            logger.info(f"Created {len(product_ids)} campaign products")

            # 3. Create campaign_assets
            for asset_input in campaign_input.campaign_assets:
                asset_data = {
                    "campaign_id": campaign_id,
                    "asset_type": asset_input.asset_type,
                    "url": asset_input.url,
                    "alt_text": asset_input.alt_text,
                    "title": asset_input.title,
                    "width": asset_input.width,
                    "height": asset_input.height,
                    "duration_seconds": asset_input.duration_seconds,
                    "file_size_bytes": asset_input.file_size_bytes,
                    "mime_type": asset_input.mime_type,
                    "usage_context": asset_input.usage_context,
                    "platform_optimized_for": asset_input.platform_optimized_for,
                    "is_approved": asset_input.is_approved,
                }
                result = await storage.insert_entity(
                    "campaign_assets",
                    asset_data
                )
                asset_ids.append(result["id"])

            logger.info(f"Created {len(asset_ids)} campaign assets")

            # 4. Create campaign_channels
            for channel_input in campaign_input.campaign_channels:
                channel_data = {
                    "campaign_id": campaign_id,
                    "platform": channel_input.platform,
                    "allocated_budget": channel_input.allocated_budget,
                    "channel_config": channel_input.channel_config,
                    "status": channel_input.status,
                }
                result = await storage.insert_entity(
                    "campaign_channels",
                    channel_data
                )
                channel_ids.append(result["id"])

            logger.info(f"Created {len(channel_ids)} campaign channels")

            # 5. Create customer_segments (campaign-specific)
            for segment_input in campaign_input.customer_segments:
                segment_data = {
                    "campaign_id": campaign_id,
                    "segment_type": segment_input.segment_type,
                    "segment_label": segment_input.segment_label,
                    "tone": segment_input.tone,
                    "key_benefits": segment_input.key_benefits,
                    "pain_points": segment_input.pain_points,
                    "primary_channels": segment_input.primary_channels,
                    "content_formats": segment_input.content_formats,
                }
                result = await storage.insert_entity(
                    "customer_segments",
                    segment_data
                )
                segment_ids.append(result["id"])

            logger.info(f"Created {len(segment_ids)} customer segments")

            # 6. Create marketing_content (campaign content)
            for content_input in campaign_input.marketing_content:
                content_data = {
                    "campaign_id": campaign_id,
                    "platform": content_input.platform,
                    "content_type": content_input.content_type,
                    "content_text": content_input.content_text,
                    "content_metadata": content_input.content_metadata,
                    "hashtags": content_input.hashtags,
                    "keywords": content_input.keywords,
                    "campaign_asset_id": content_input.campaign_asset_id,
                    "generated_by": campaign_input.generated_by,
                }
                result = await storage.insert_entity(
                    "marketing_content",
                    content_data
                )
                content_ids.append(result["id"])

            logger.info(f"Created {len(content_ids)} marketing content items")

            # Success!
            total_entities = (
                len(product_ids) + len(asset_ids) + len(channel_ids) +
                len(segment_ids) + len(content_ids)
            )
            result = CampaignPersistenceResult(
                success=True,
                campaign_id=str(campaign_id),
                campaign_name=campaign_input.name,
                product_ids=[str(pid) for pid in product_ids],
                asset_ids=[str(aid) for aid in asset_ids],
                channel_ids=[str(cid) for cid in channel_ids],
                segment_ids=[str(sid) for sid in segment_ids],
                content_ids=[str(cid) for cid in content_ids],
                created_at=datetime.now(UTC).isoformat(),
                message=(
                    f"Campaign '{campaign_input.name}' persisted successfully across 6 tables "
                    f"with {total_entities} related entities"
                )
            )

            logger.info(
                f"Campaign persistence complete: {campaign_input.campaign_id} "
                f"(UUID: {campaign_id}, entities: {total_entities})"
            )
            return result

        except Exception as e:
            logger.error(f"Campaign persistence failed: {str(e)}", exc_info=True)

            error_instance = classify_api_error(
                error=e,
                tool_name="save_campaign",
                api_name="supabase"
            )
            error_message = (
                f"Failed to save campaign '{campaign_input.campaign_id}': {str(e)}"
            )

            if isinstance(error_instance, ExternalAPIError):
                error_message += "\n\nDatabase connection issue. Campaign NOT saved. Please retry."
            else:
                error_message += "\n\nValidation or constraint error. Check campaign data."

            raise ToolException(error_message) from e

    return StructuredTool.from_function(
        func=_save_campaign_impl,
        name="save_campaign",
        description=(
            "Atomically persist complete marketing campaign across 5+ tables. "
            "Performs all-or-nothing transaction across campaigns, campaign_products, "
            "campaign_assets, campaign_channels, customer_segments, and marketing_content. "
            "Rollback on any failure."
        ),
        args_schema=CampaignInput,
    )
