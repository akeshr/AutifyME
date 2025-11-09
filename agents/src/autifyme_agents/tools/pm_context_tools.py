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
from typing import Any
from uuid import UUID

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.tool_error_handler import (
    build_agent_error_response,
    build_success_response,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Query Result Models
# =============================================================================


class FamilyMatch(BaseModel):
    """Single product family match from PM-level catalog search.

    Lightweight summary (names, counts, IDs only) for PM discussions.
    NOT full product data - PM delegates to specialists for detailed operations.

    Examples:
        PET Jars family:
            FamilyMatch(
                id="550e8400-e29b-41d4-a716-446655440000",
                name="PET Jars",
                variant_count=24,
                category_name="Food & Beverage Packaging"
            )

        Small family without category:
            FamilyMatch(
                id="550e8401-e29b-41d4-a716-446655440000",
                name="Glass Bottles 200ml-500ml",
                variant_count=8,
                category_name=None
            )
    """

    id: str = Field(
        ...,
        description=(
            "Product family UUID in database. "
            "PM includes this in delegation message to specialist for entity reference. "
            "Example: '550e8400-e29b-41d4-a716-446655440000'. "
            "Specialist uses this ID to query full family details or perform operations."
        )
    )
    name: str = Field(
        ...,
        description=(
            "Product family name (human-readable). "
            "Examples: 'PET Jars', 'HDPE Bottles 500ml-5L', 'Glass Containers'. "
            "PM uses this for user-facing responses and delegation context. "
            "Shown to user: 'Found existing family: PET Jars (id: 550e8400-...)'"
        )
    )
    variant_count: int = Field(
        ...,
        description=(
            "Number of SKU variants in this family (product count). "
            "Example: 24 (means 24 distinct SKUs like JAR-PET-500ML-CLR, JAR-PET-1L-CLR, etc.). "
            "PM uses for context: 'PET Jars family has 24 existing variants'. "
            "Helps PM assess if this is small starter family (1-5 SKUs) or mature family (50+ SKUs)."
        )
    )
    category_name: str | None = Field(
        None,
        description=(
            "Category name if family is categorized (None if uncategorized). "
            "Examples: 'Food & Beverage Packaging', 'Industrial Containers', 'Cosmetic Packaging'. "
            "PM uses for taxonomy discussions: 'This family is in Food & Beverage Packaging category'. "
            "None indicates family not yet assigned to category taxonomy."
        )
    )


class CatalogSearchSummary(BaseModel):
    """Summary-level search results from PM catalog search.

    Returns matching family names and variant counts, NOT full product data.
    PM uses this to check if products exist before delegating to specialists.

    Examples:
        Single match found:
            CatalogSearchSummary(
                query="PET Jars",
                matches=[
                    FamilyMatch(
                        id="550e8400-e29b-41d4-a716-446655440000",
                        name="PET Jars",
                        variant_count=24,
                        category_name="Food & Beverage Packaging"
                    )
                ],
                total_matches=1,
                has_more=False
            )

        Multiple matches found (limited to 10):
            CatalogSearchSummary(
                query="Bottles",
                matches=[
                    FamilyMatch(id="...", name="PET Bottles", variant_count=48, category_name="..."),
                    FamilyMatch(id="...", name="HDPE Bottles", variant_count=36, category_name="..."),
                    FamilyMatch(id="...", name="Glass Bottles", variant_count=24, category_name="...")
                ],
                total_matches=3,
                has_more=False
            )

        Many matches (truncated):
            CatalogSearchSummary(
                query="Containers",
                matches=[
                    # ... 10 FamilyMatch objects
                ],
                total_matches=10,
                has_more=True  # More than 10 results exist
            )

        No matches:
            CatalogSearchSummary(
                query="Ceramic Vases",
                matches=[],
                total_matches=0,
                has_more=False
            )
    """

    query: str = Field(
        ...,
        description=(
            "Search query used (as provided by PM). "
            "Examples: 'PET Jars', 'Bottles', 'Containers', 'Glass'. "
            "Used for logging and traceability. "
            "PM can reference this in user response: 'I searched for \"{query}\" and found...'."
        )
    )
    matches: list[FamilyMatch] = Field(
        ...,
        description=(
            "Matching product families (max 10 for concise response). "
            "Empty list if no matches found. "
            "Sorted by relevance (exact name matches first, then substring matches). "
            "Each match includes id, name, variant_count, category_name for PM context. "
            "PM shows these to user or includes in delegation message to specialist."
        )
    )
    total_matches: int = Field(
        ...,
        description=(
            "Total number of matches found (before 10-match limit). "
            "Examples: 1 (single exact match), 3 (few matches), 15 (many matches truncated to 10). "
            "PM uses to inform user: '...and 5 more families' if total_matches=15 and len(matches)=10. "
            "Same as len(matches) if has_more=False."
        )
    )
    has_more: bool = Field(
        ...,
        description=(
            "True if more matches exist beyond 10-match limit (total_matches > 10). "
            "PM uses to inform user about truncated results. "
            "Example user message: 'Found 10 matching families (and 5 more)' when has_more=True."
        )
    )


class CategoryInfo(BaseModel):
    """Category details for PM taxonomy understanding.

    Returns category metadata and product counts, NOT full product lists.
    PM uses this for taxonomy discussions and classification guidance.

    Examples:
        Top-level category with subcategories:
            CategoryInfo(
                id="660e8400-e29b-41d4-a716-446655440000",
                name="Food & Beverage",
                parent_id=None,
                parent_name=None,
                subcategory_count=5,
                product_family_count=0
            )

        Subcategory with products:
            CategoryInfo(
                id="660e8401-e29b-41d4-a716-446655440000",
                name="Beverage Packaging",
                parent_id="660e8400-e29b-41d4-a716-446655440000",
                parent_name="Food & Beverage",
                subcategory_count=2,
                product_family_count=15
            )

        Leaf category (no subcategories, only products):
            CategoryInfo(
                id="660e8402-e29b-41d4-a716-446655440000",
                name="PET Bottle Packaging",
                parent_id="660e8401-e29b-41d4-a716-446655440000",
                parent_name="Beverage Packaging",
                subcategory_count=0,
                product_family_count=8
            )
    """

    id: str = Field(
        ...,
        description=(
            "Category UUID in database. "
            "PM uses to reference category in delegation messages. "
            "Example: '660e8400-e29b-41d4-a716-446655440000'. "
            "Specialist uses this ID to assign families to categories."
        )
    )
    name: str = Field(
        ...,
        description=(
            "Category name (human-readable, hierarchical). "
            "Examples: 'Food & Beverage', 'Beverage Packaging', 'PET Bottle Packaging'. "
            "PM shows this to user for taxonomy discussions. "
            "Exact match required for category assignment."
        )
    )
    parent_id: str | None = Field(
        None,
        description=(
            "Parent category UUID if this is a subcategory (None for top-level categories). "
            "Example: '660e8400-...' (Food & Beverage parent of Beverage Packaging). "
            "Used to understand taxonomy hierarchy. "
            "None indicates this is a root category."
        )
    )
    parent_name: str | None = Field(
        None,
        description=(
            "Parent category name if available (None for top-level categories). "
            "Examples: 'Food & Beverage', 'Beverage Packaging'. "
            "PM uses for context: 'This is a subcategory of Food & Beverage'. "
            "None if this is a root category or parent name unavailable."
        )
    )
    subcategory_count: int = Field(
        ...,
        description=(
            "Number of direct subcategories under this category. "
            "Example: 5 (Food & Beverage has 5 subcategories like Beverage, Dairy, Snacks, etc.). "
            "0 indicates leaf category (no further subdivision). "
            "PM uses to navigate taxonomy: 'This category has 5 subcategories you can explore'."
        )
    )
    product_family_count: int = Field(
        ...,
        description=(
            "Number of product families assigned to this specific category (not including subcategories). "
            "Example: 15 (15 families in Beverage Packaging category). "
            "0 means no families assigned yet or category used only for organization. "
            "PM uses for context: 'This category contains 15 product families'. "
            "Helps PM understand category utilization and suggest appropriate categories."
        )
    )


# =============================================================================
# Tool Input Models (OpenAI-compatible)
# =============================================================================


class SearchCatalogSummaryInput(BaseModel):
    """Input schema for search_catalog_summary tool."""

    model_config = {"extra": "forbid"}

    queries: list[str] = Field(
        ...,
        description="List of search queries to batch search (case-insensitive substring match on product family names). Use list even for single query.",
        min_length=1
    )


class GetCategoryInfoInput(BaseModel):
    """Input schema for get_category_info tool."""

    model_config = {"extra": "forbid"}

    category_name: str = Field(
        ...,
        description="Category name to retrieve information for (case-insensitive match)"
    )


# =============================================================================
# PM Query Tools
# =============================================================================


def create_search_catalog_summary_tool(storage: StorageInterface) -> BaseTool:
    """Factory for search_catalog_summary tool (PM-level summary query).

    Searches product families by name (case-insensitive substring match).
    Returns summary-level results (family names, counts) NOT full product data.

    Args:
        storage: Storage adapter with DB access

    Returns:
        LangChain tool for PM catalog search
    """

    async def _search_catalog_summary_impl(queries: list[str]) -> dict[str, Any]:
        """Search catalog for product families matching queries (batch search).

        Summary-level search (family names and counts only). Use this to:
        - Check if products exist ("Do we have PET jars?")
        - Find similar families ("What bottles do we make?")
        - Validate user requests before delegating
        - Search multiple families in single call

        Args:
            queries: List of search terms (e.g., ["PET jar", "bottles", "containers"])

        Returns:
            Dict with batch search results:
            - On success: {"success": True, "results": [{"query": str, "matches": [...], "total_matches": int, "has_more": bool}, ...]}
            - On error: {"success": False, "error": str, "error_type": str}

        Example:
            queries: ["PET jar", "bottles"]
            → {
                "success": True,
                "results": [
                    {"query": "PET jar", "matches": [{"name": "PET Jars", "variant_count": 12}], "total_matches": 1, "has_more": False},
                    {"query": "bottles", "matches": [{"name": "PET Bottles", "variant_count": 48}, {"name": "Glass Bottles", "variant_count": 24}], "total_matches": 2, "has_more": False}
                ]
              }
        """
        try:
            results = []

            for query in queries:
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
                    results.append({
                        "query": query,
                        "matches": [],
                        "total_matches": 0,
                        "has_more": False,
                    })
                    continue

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

                results.append({
                    "query": query,
                    "matches": [match.model_dump() for match in matches],
                    "total_matches": len(matches),
                    "has_more": has_more,
                })

            logger.info(
                "Batch catalog search completed",
                extra={"queries_count": len(queries), "total_results": len(results)}
            )

            return build_success_response({
                "results": results,
            })

        except Exception as e:
            logger.error(
                "Batch catalog search failed",
                exc_info=True,
                extra={"queries": queries, "error_type": type(e).__name__, "error_msg": str(e)}
            )
            return build_agent_error_response(
                exception=e,
                context={"queries": queries},
                fallback_type="QUERY_ERROR",
                fallback_action=(
                    f"Unable to search catalog for queries: {', '.join(queries)}. "
                    f"Proceed with workflow and delegate to specialist for verification."
                ),
            )

    return StructuredTool.from_function(
        coroutine=_search_catalog_summary_impl,
        name="search_catalog_summary",
        description=(
            "Batch search catalog for product families (PM-level summary: names, counts, IDs only - NOT full data). "
            "BATCH CAPABILITY: Pass list of queries to search multiple families in SINGLE call (e.g., queries=['PET jar', 'bottles', 'containers']). "
            "WHEN TO USE: PM uses this BEFORE delegating to check if products exist and to gather entity IDs for delegation messages. "
            "NOT FOR SPECIALISTS: Specialists should use search_product_families (fuzzy matching with confidence scores) or query_database (complete data with filters). "
            "CRITICAL: Include search results with IDs in your delegation message to specialist (e.g., 'Found PET Bottles (id: abc-123)')."
        ),
        args_schema=SearchCatalogSummaryInput,
    )


def create_get_category_info_tool(storage: StorageInterface) -> BaseTool:
    """Factory for get_category_info tool (PM-level taxonomy query).

    Gets category details and product counts (NOT full product lists).
    Returns metadata for PM taxonomy discussions.

    Args:
        storage: Storage adapter with DB access

    Returns:
        LangChain tool for PM category info query
    """

    async def _get_category_info_impl(category_name: str) -> dict[str, Any]:
        """Get category details and product counts.

        Summary-level taxonomy query. Use this to:
        - Understand category structure
        - Check product counts in categories
        - Guide taxonomy classification discussions

        Args:
            category_name: Category name (e.g., "Food & Beverage", "PET Packaging")

        Returns:
            Dict with category details:
            - On success: {"success": True, "id": str, "name": str, "parent_id": str|None, "parent_name": str|None, "subcategory_count": int, "product_family_count": int}
            - On error: {"success": False, "error": str, "error_type": str, "category_name": str}

        Example:
            category_name: "Food & Beverage"
            → {"success": True, "id": "...", "name": "Food & Beverage", "subcategory_count": 3, "product_family_count": 15}
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
                return {
                    "success": False,
                    "error": (
                        f"CATEGORY_NOT_FOUND: Category '{category_name}' does not exist in taxonomy.\n\n"
                        f"Agent Action: Check base_context.taxonomy_tree for available categories. "
                        f"Use exact category name or search with similar terms."
                    ),
                    "error_type": "CATEGORY_NOT_FOUND",
                    "category_name": category_name,
                }

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

            return build_success_response({
                "id": str(category_id),
                "name": category["name"],
                "parent_id": str(category["parent_id"]) if category.get("parent_id") else None,
                "parent_name": parent_name,
                "subcategory_count": subcategory_count,
                "product_family_count": product_family_count,
            })

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
            return build_agent_error_response(
                exception=e,
                context={"category_name": category_name},
                fallback_type="CATEGORY_ERROR",
                fallback_action=(
                    f"Unable to get category info for '{category_name}'. "
                    f"Use base_context.taxonomy_tree for category structure. Proceed with cached data."
                ),
            )

    return StructuredTool.from_function(
        coroutine=_get_category_info_impl,
        name="get_category_info",
        description=(
            "Get category details and product counts (PM-level taxonomy summary - NOT full product lists). "
            "WHEN TO USE: PM uses this for taxonomy discussions, checking category structure, or understanding product distribution across categories. "
            "Returns: Category metadata (ID, parent, subcategory count, product family count) - use for context in responses to user."
        ),
        args_schema=GetCategoryInfoInput,
    )
