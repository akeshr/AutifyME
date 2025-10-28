"""Product CRUD Tools - READ and DELETE operations.

Architecture:
- Complements product_persistence_tools.py (handles CREATE/UPDATE)
- Specialists return appropriate draft type
- PM calls appropriate tool based on draft_type:
  * query → query_product_data
  * deletion → delete_product_data
  * full_family/variant_addition/axis_addition/family_update → save_product_family

Design Philosophy:
- Focused tools for each operation type
- Type-safe routing via draft models
- Complete CRUD coverage across all 9 tables
"""

import logging
from typing import Any
from uuid import UUID

from langchain.tools import tool
from langchain_core.tools import ToolException
from pydantic import BaseModel, Field

from autifyme_agents.core.exceptions import classify_api_error
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient

# Import draft types and result models
from autifyme_agents.schemas.product_drafts import ProductQueryDraft, ProductDeletionDraft

logger = logging.getLogger(__name__)


# =============================================================================
# Result Models
# =============================================================================


class QueryResult(BaseModel):
    """Result of read/query operation."""

    success: bool
    family_data: dict[str, Any] | None = None
    sku_data: list[dict[str, Any]] | None = None
    variant_structure: dict[str, Any] | None = None
    industry_targets: list[dict[str, Any]] | None = None
    customer_segments: list[dict[str, Any]] | None = None
    images: list[dict[str, Any]] | None = None
    marketing_content: list[dict[str, Any]] | None = None
    error_message: str | None = None


class DeletionResult(BaseModel):
    """Result of delete operation."""

    success: bool
    operation: str = "delete"
    deletion_scope: str
    records_deleted: int = 0
    soft_deleted: bool
    affected_tables: list[str] = Field(default_factory=list)
    error_message: str | None = None


# =============================================================================
# READ Operation
# =============================================================================


def create_query_product_data_tool(storage: SupabaseStorageClient) -> object:
    """Create tool for querying product data (READ operations).

    Args:
        storage: Supabase storage client

    Returns:
        LangChain tool that accepts ProductQueryDraft and returns QueryResult
    """

    @tool("query_product_data")
    async def query_product_data(
        family_id: str,
        retrieve_family_details: bool = False,
        retrieve_all_skus: bool = False,
        retrieve_specific_skus: list[str] | None = None,
        retrieve_variant_structure: bool = False,
        retrieve_industry_targets: bool = False,
        retrieve_customer_segments: bool = False,
        retrieve_images: bool = False,
        retrieve_marketing_content: bool = False,
        retrieve_marketing_by_platform: str | None = None,
    ) -> QueryResult:
        """
        Retrieve product data based on query specification.

        Args:
            family_id: Product family UUID to query
            retrieve_family_details: Get complete family metadata
            retrieve_all_skus: Get all product variants
            retrieve_specific_skus: Get specific SKUs by code
            retrieve_variant_structure: Get axes + values configuration
            retrieve_industry_targets: Get industry targeting data
            retrieve_customer_segments: Get customer segment data
            retrieve_images: Get all product images
            retrieve_marketing_content: Get all marketing content
            retrieve_marketing_by_platform: Get content for specific platform

        Returns:
            QueryResult with requested data

        Raises:
            ToolException: On database errors
        """
        client = storage._ensure_client()
        result = QueryResult(success=False)

        try:
            family_id_str = str(family_id)

            # Family details
            if retrieve_family_details:
                family = (
                    client.table("product_families")
                    .select("*")
                    .eq("id", family_id_str)
                    .single()
                    .execute()
                )
                result.family_data = family.data

            # All SKUs
            if retrieve_all_skus:
                skus = (
                    client.table("products")
                    .select("*")
                    .eq("product_family_id", family_id_str)
                    .execute()
                )
                result.sku_data = skus.data

            # Specific SKUs
            if retrieve_specific_skus:
                skus = (
                    client.table("products")
                    .select("*")
                    .in_("sku", retrieve_specific_skus)
                    .execute()
                )
                result.sku_data = skus.data

            # Variant structure
            if retrieve_variant_structure:
                axes = (
                    client.table("variant_axes")
                    .select("*, variant_values(*)")
                    .eq("product_family_id", family_id_str)
                    .execute()
                )
                result.variant_structure = {"axes": axes.data}

            # Industry targets
            if retrieve_industry_targets:
                industries = (
                    client.table("product_family_industries")
                    .select("*")
                    .eq("product_family_id", family_id_str)
                    .execute()
                )
                result.industry_targets = industries.data

            # Customer segments
            if retrieve_customer_segments:
                segments = (
                    client.table("customer_segments")
                    .select("*")
                    .eq("product_family_id", family_id_str)
                    .execute()
                )
                result.customer_segments = segments.data

            # Images
            if retrieve_images:
                images = (
                    client.table("product_images")
                    .select("*")
                    .eq("product_family_id", family_id_str)
                    .execute()
                )
                result.images = images.data

            # Marketing content
            if retrieve_marketing_content:
                if retrieve_marketing_by_platform:
                    content = (
                        client.table("marketing_content")
                        .select("*")
                        .eq("product_family_id", family_id_str)
                        .eq("platform", retrieve_marketing_by_platform)
                        .execute()
                    )
                else:
                    content = (
                        client.table("marketing_content")
                        .select("*")
                        .eq("product_family_id", family_id_str)
                        .execute()
                    )
                result.marketing_content = content.data

            result.success = True
            logger.info(f"Retrieved data for family {family_id}")

            return result

        except Exception as e:
            logger.error("Failed to query product data", exc_info=True)
            result.error_message = str(e)
            raise ToolException(f"Failed to query product data: {str(e)}") from e

    return query_product_data


# =============================================================================
# DELETE Operation
# =============================================================================


def create_delete_product_data_tool(storage: SupabaseStorageClient) -> object:
    """Create tool for deleting product data (DELETE operations).

    Args:
        storage: Supabase storage client

    Returns:
        LangChain tool that accepts ProductDeletionDraft params and returns DeletionResult
    """

    @tool("delete_product_data")
    async def delete_product_data(
        family_id: str,
        deletion_scope: str,
        soft_delete: bool = True,
        target_skus: list[str] | None = None,
        target_axis_name: str | None = None,
        target_value_sku_code: str | None = None,
        target_industry_naics: str | None = None,
        target_segment_type: str | None = None,
        target_image_urls: list[str] | None = None,
        target_content_ids: list[str] | None = None,
    ) -> DeletionResult:
        """
        Delete product data with impact-based cascading.

        CRITICAL: Specialist must calculate impact analysis BEFORE calling this tool.
        PM must get explicit user confirmation before executing deletion.

        Args:
            family_id: Product family UUID
            deletion_scope: One of: entire_family, specific_skus, variant_axis,
                           variant_value, industry_target, customer_segment, images, marketing_content
            soft_delete: If True, mark as inactive. If False, hard delete from DB
            target_skus: For specific_skus scope
            target_axis_name: For variant_axis scope
            target_value_sku_code: For variant_value scope
            target_industry_naics: For industry_target scope
            target_segment_type: For customer_segment scope
            target_image_urls: For images scope
            target_content_ids: For marketing_content scope

        Returns:
            DeletionResult with records deleted count

        Raises:
            ToolException: On database errors
        """
        client = storage._ensure_client()
        result = DeletionResult(
            success=False, deletion_scope=deletion_scope, soft_deleted=soft_delete
        )

        try:
            family_id_str = str(family_id)
            records_deleted = 0

            # ENTIRE FAMILY DELETION
            if deletion_scope == "entire_family":
                if soft_delete:
                    # Soft delete: mark as inactive
                    client.table("product_families").update(
                        {"is_active": False}
                    ).eq("id", family_id_str).execute()
                    records_deleted = 1
                else:
                    # Hard delete: cascades via foreign keys
                    client.table("product_families").delete().eq(
                        "id", family_id_str
                    ).execute()
                    records_deleted = 1  # Plus cascaded records

                result.affected_tables = [
                    "product_families",
                    "products",
                    "variant_axes",
                    "variant_values",
                    "product_images",
                    "marketing_content",
                ]

            # SPECIFIC SKUs DELETION
            elif deletion_scope == "specific_skus" and target_skus:
                for sku in target_skus:
                    if soft_delete:
                        client.table("products").update(
                            {"availability": "discontinued"}
                        ).eq("sku", sku).execute()
                    else:
                        client.table("products").delete().eq("sku", sku).execute()
                    records_deleted += 1

                result.affected_tables = ["products", "product_variant_values"]

            # VARIANT AXIS DELETION
            elif deletion_scope == "variant_axis" and target_axis_name:
                # Get axis_id
                axis = (
                    client.table("variant_axes")
                    .select("id")
                    .eq("product_family_id", family_id_str)
                    .eq("name", target_axis_name)
                    .single()
                    .execute()
                )

                axis_id = axis.data["id"]

                if soft_delete:
                    # Mark axis as inactive
                    client.table("variant_axes").update({"is_active": False}).eq(
                        "id", axis_id
                    ).execute()
                else:
                    # Delete axis (cascades to values)
                    client.table("variant_axes").delete().eq("id", axis_id).execute()

                records_deleted = 1
                result.affected_tables = ["variant_axes", "variant_values"]

            # VARIANT VALUE DELETION
            elif deletion_scope == "variant_value" and target_value_sku_code:
                # Get value_id
                value = (
                    client.table("variant_values")
                    .select("id")
                    .eq("sku_code", target_value_sku_code)
                    .single()
                    .execute()
                )

                value_id = value.data["id"]

                if soft_delete:
                    # Mark value as inactive
                    client.table("variant_values").update({"is_active": False}).eq(
                        "id", value_id
                    ).execute()
                else:
                    # Delete value
                    client.table("variant_values").delete().eq(
                        "id", value_id
                    ).execute()

                records_deleted = 1
                result.affected_tables = ["variant_values"]

            # AUXILIARY TABLE DELETIONS
            elif deletion_scope == "industry_target" and target_industry_naics:
                client.table("product_family_industries").delete().eq(
                    "product_family_id", family_id_str
                ).eq("industry_naics_code", target_industry_naics).execute()
                records_deleted = 1
                result.affected_tables = ["product_family_industries"]

            elif deletion_scope == "customer_segment" and target_segment_type:
                client.table("customer_segments").delete().eq(
                    "product_family_id", family_id_str
                ).eq("segment_type", target_segment_type).execute()
                records_deleted = 1
                result.affected_tables = ["customer_segments"]

            elif deletion_scope == "images" and target_image_urls:
                for url in target_image_urls:
                    client.table("product_images").delete().eq("url", url).execute()
                    records_deleted += 1
                result.affected_tables = ["product_images"]

            elif deletion_scope == "marketing_content" and target_content_ids:
                for content_id in target_content_ids:
                    client.table("marketing_content").delete().eq(
                        "id", content_id
                    ).execute()
                    records_deleted += 1
                result.affected_tables = ["marketing_content"]

            result.success = True
            result.records_deleted = records_deleted

            logger.info(
                f"Deleted {records_deleted} records for family {family_id}, "
                f"scope={deletion_scope}, soft_delete={soft_delete}"
            )

            return result

        except Exception as e:
            logger.error("Failed to delete product data", exc_info=True)
            result.error_message = str(e)
            raise ToolException(f"Failed to delete product data: {str(e)}") from e

    return delete_product_data
