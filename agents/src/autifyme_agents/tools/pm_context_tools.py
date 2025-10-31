"""PM Context Query Tools - Summary-level queries for Intelligent PM.

These tools enable PM to query catalog and taxonomy details on-demand without
loading full data. Part of Hybrid Context Feeding Strategy (Option D):
- Base context loaded at startup (catalog summary, taxonomy tree)
- Query tools provide details when PM needs them

Design:
- Summary-level only (family names, counts, NOT full product data)
- Fast queries (<500ms target)
- Lightweight responses (<200 tokens per query)
- PM uses these for intelligent discussions before delegating
"""

import logging
from uuid import UUID

from langchain.tools import tool
from langchain_core.tools import ToolException
from pydantic import BaseModel, Field

from autifyme_agents.core.ports import StorageInterface

logger = logging.getLogger(__name__)


# =============================================================================
# Query Result Models
# =============================================================================


class FamilyMatch(BaseModel):
    """Single product family match from catalog search."""

    id: str = Field(..., description="Product family UUID")
    name: str = Field(..., description="Product family name")
    variant_count: int = Field(..., description="Number of SKU variants in this family")
    category_name: str | None = Field(None, description="Category name if available")


class CatalogSearchSummary(BaseModel):
    """Summary-level search results from catalog.

    Returns matching family names and variant counts, NOT full product data.
    PM uses this to check if products exist before delegating to specialists.
    """

    query: str = Field(..., description="Search query used")
    matches: list[FamilyMatch] = Field(..., description="Matching product families (max 10)")
    total_matches: int = Field(..., description="Total number of matches found")
    has_more: bool = Field(..., description="True if more matches exist beyond limit")


class CategoryInfo(BaseModel):
    """Category details for PM understanding.

    Returns category metadata and product counts, NOT full product lists.
    PM uses this for taxonomy discussions and classification guidance.
    """

    id: str = Field(..., description="Category UUID")
    name: str = Field(..., description="Category name")
    parent_id: str | None = Field(None, description="Parent category UUID if subcategory")
    parent_name: str | None = Field(None, description="Parent category name if available")
    subcategory_count: int = Field(..., description="Number of direct subcategories")
    product_family_count: int = Field(..., description="Number of product families in this category")


# =============================================================================
# PM Query Tools
# =============================================================================


def create_search_catalog_summary_tool(storage: StorageInterface):
    """Factory for search_catalog_summary tool (PM-level summary query).

    Searches product families by name (case-insensitive substring match).
    Returns summary-level results (family names, counts) NOT full product data.

    Args:
        storage: Storage adapter with DB access

    Returns:
        LangChain tool for PM catalog search
    """

    @tool
    async def search_catalog_summary(query: str) -> CatalogSearchSummary:
        """Search catalog for product families matching query.

        Summary-level search (family names and counts only). Use this to:
        - Check if products exist ("Do we have PET jars?")
        - Find similar families ("What bottles do we make?")
        - Validate user requests before delegating

        Args:
            query: Search term (e.g., "PET jar", "bottles", "containers")

        Returns:
            CatalogSearchSummary with matching families (max 10 results)

        Example:
            query: "PET jar"
            → matches: [{"name": "PET Jars", "variant_count": 12, ...}]

            query: "bottles"
            → matches: [{"name": "PET Bottles", "variant_count": 48}, {"name": "Glass Bottles", "variant_count": 24}]
        """
        try:
            # Case-insensitive substring search on product family names
            search_pattern = f"%{query}%"

            # Query product families with search pattern
            families = await storage.query_advanced(
                table="product_families",
                columns=["id", "name", "category_id"],
                search_patterns={"name": search_pattern},
                limit=11  # Fetch 11 to detect has_more
            )

            if not families:
                return CatalogSearchSummary(
                    query=query,
                    matches=[],
                    total_matches=0,
                    has_more=False,
                )

            has_more = len(families) > 10
            families = families[:10]  # Limit to 10 for response

            # Get variant counts for each family
            matches = []
            for family in families:
                family_id = family["id"]

                # Count variants for this family
                variant_count = await storage.query_advanced(
                    table="products",
                    filters={"product_family_id": family_id},
                    count_only=True
                )

                # Get category name if category_id exists
                category_name = None
                if family.get("category_id"):
                    try:
                        categories = await storage.query_entities(
                            table="categories",
                            filters={"id": family["category_id"]},
                            columns=["name"]
                        )
                        category_name = categories[0]["name"] if categories else None
                    except Exception as e:
                        logger.warning(f"Failed to fetch category name: {e}")

                matches.append(
                    FamilyMatch(
                        id=str(family_id),
                        name=family["name"],
                        variant_count=variant_count,
                        category_name=category_name,
                    )
                )

            logger.info(
                "Catalog search completed",
                extra={"query": query, "matches_count": len(matches), "has_more": has_more}
            )

            return CatalogSearchSummary(
                query=query,
                matches=matches,
                total_matches=len(matches),
                has_more=has_more,
            )

        except Exception as e:
            logger.error(
                "Catalog search failed",
                exc_info=True,
                extra={"query": query, "error_type": type(e).__name__, "error_msg": str(e)}
            )
            raise ToolException(
                f"Failed to search catalog for '{query}': {str(e)}"
            ) from e

    return search_catalog_summary


def create_get_category_info_tool(storage: StorageInterface):
    """Factory for get_category_info tool (PM-level taxonomy query).

    Gets category details and product counts (NOT full product lists).
    Returns metadata for PM taxonomy discussions.

    Args:
        storage: Storage adapter with DB access

    Returns:
        LangChain tool for PM category info query
    """

    @tool
    async def get_category_info(category_name: str) -> CategoryInfo:
        """Get category details and product counts.

        Summary-level taxonomy query. Use this to:
        - Understand category structure
        - Check product counts in categories
        - Guide taxonomy classification discussions

        Args:
            category_name: Category name (e.g., "Food & Beverage", "PET Packaging")

        Returns:
            CategoryInfo with metadata and counts (NOT product lists)

        Example:
            category_name: "Food & Beverage"
            → {id: "...", name: "Food & Beverage", subcategory_count: 3, product_family_count: 15}
        """
        try:
            # Case-insensitive exact match on category name
            categories = await storage.query_advanced(
                table="categories",
                columns=["id", "name", "parent_id"],
                search_patterns={"name": category_name},
                limit=1
            )

            if not categories:
                raise ToolException(
                    f"Category '{category_name}' not found in taxonomy. "
                    "Check base_context.taxonomy_tree for available categories."
                )

            category = categories[0]
            category_id = UUID(category["id"])

            # Get parent category name if exists
            parent_name = None
            if category.get("parent_id"):
                try:
                    parents = await storage.query_entities(
                        table="categories",
                        filters={"id": category["parent_id"]},
                        columns=["name"]
                    )
                    parent_name = parents[0]["name"] if parents else None
                except Exception as e:
                    logger.warning(f"Failed to fetch parent category name: {e}")

            # Count subcategories
            subcategory_count = await storage.query_advanced(
                table="categories",
                filters={"parent_id": str(category_id)},
                count_only=True
            )

            # Count product families in this category
            product_family_count = await storage.query_advanced(
                table="product_families",
                filters={"category_id": str(category_id)},
                count_only=True
            )

            logger.info(
                "Category info retrieved",
                extra={
                    "category_name": category_name,
                    "subcategories": subcategory_count,
                    "families": product_family_count,
                }
            )

            return CategoryInfo(
                id=str(category_id),
                name=category["name"],
                parent_id=str(category["parent_id"]) if category.get("parent_id") else None,
                parent_name=parent_name,
                subcategory_count=subcategory_count,
                product_family_count=product_family_count,
            )

        except ToolException:
            # Re-raise ToolException as-is
            raise
        except Exception as e:
            logger.error(
                "Category info query failed",
                exc_info=True,
                extra={
                    "category_name": category_name,
                    "error_type": type(e).__name__,
                    "error_msg": str(e)
                }
            )
            raise ToolException(
                f"Failed to get category info for '{category_name}': {str(e)}"
            ) from e

    return get_category_info
