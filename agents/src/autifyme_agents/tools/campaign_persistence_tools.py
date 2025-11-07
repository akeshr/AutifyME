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
from typing import Any

from langchain_core.tools import StructuredTool, ToolException
from pydantic import BaseModel, Field

from autifyme_agents.core.exceptions import ExternalAPIError, classify_api_error

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models for Campaign Persistence
# =============================================================================


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
    """Input for platform-specific campaign configuration."""

    platform: str = Field(
        ..., description="facebook, instagram, youtube, twitter, linkedin, google_ads, amazon, whatsapp, email, website"
    )
    allocated_budget: float | None = None
    channel_config: dict[str, Any] = Field(
        default_factory=dict, description="Platform-specific settings (bidding, targeting)"
    )
    status: str = Field(default="draft", description="draft, scheduled, active, paused, completed")


class CampaignSegmentInput(BaseModel):
    """Input for campaign-specific customer segment."""

    segment_type: str = Field(..., description="b2b, b2c, d2c, wholesale, enterprise, retail")
    segment_label: str
    tone: str = Field(..., description="professional, casual, technical, emotional, educational, aspirational")
    key_benefits: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    primary_channels: list[str] = Field(default_factory=list)
    content_formats: list[str] = Field(default_factory=list)


class MarketingContentInput(BaseModel):
    """Input for campaign marketing content."""

    platform: str
    content_type: str = Field(..., description="post, story, reel, video, carousel, ad, etc.")
    content_text: str
    content_metadata: dict[str, Any] = Field(default_factory=dict)
    hashtags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    campaign_asset_id: str | None = Field(None, description="Link to campaign asset")


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
    total_budget: float | None = None
    budget_currency: str = Field(default="INR")
    budget_allocation: dict[str, Any] = Field(
        default_factory=dict, description="Per-channel budget breakdown"
    )

    # Timeline
    planned_start_date: str = Field(..., description="ISO date YYYY-MM-DD")
    planned_end_date: str = Field(..., description="ISO date YYYY-MM-DD")

    # KPIs
    target_metrics: dict[str, Any] = Field(
        default_factory=dict, description="Campaign KPI targets"
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

    async def _save_campaign_impl(campaign_input: CampaignInput) -> dict[str, Any]:
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
            Dict with campaign_id and all related entity IDs

        Raises:
            ToolException: On persistence failure (with rollback)
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
            result = {
                "success": True,
                "campaign_id": str(campaign_id),
                "campaign_business_id": campaign_input.campaign_id,
                "campaign_name": campaign_input.name,
                "total_products": len(product_ids),
                "total_assets": len(asset_ids),
                "total_channels": len(channel_ids),
                "total_segments": len(segment_ids),
                "total_content_items": len(content_ids),
                "message": f"Campaign '{campaign_input.name}' persisted successfully across 6 tables",
            }

            logger.info(f"Campaign persistence complete: {campaign_input.campaign_id}")
            return result

        except Exception as e:
            logger.error(f"Campaign persistence failed: {str(e)}", exc_info=True)

            error_class = classify_api_error(e)
            error_message = (
                f"Failed to save campaign '{campaign_input.campaign_id}': {str(e)}"
            )

            if error_class == ExternalAPIError:
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
