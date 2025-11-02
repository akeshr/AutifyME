"""Query database tool - flexible data retrieval for specialists.

Gives specialists direct query access with advanced filtering, relations,
pattern matching, and counting capabilities.
"""

import logging
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.tool_error_handler import (
    build_agent_error_response,
    build_success_response,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Model (OpenAI requires additionalProperties: false)
# =============================================================================


class QueryDatabaseInput(BaseModel):
    """Input schema for query_database tool."""

    model_config = {"extra": "forbid"}  # Generates additionalProperties: false

    table: str = Field(
        ...,
        description="Table name to query (e.g., 'product_families', 'products')"
    )
    filters: dict[str, Any] | None = Field(
        description=(
            "Exact match conditions for any field. "
            "Examples: {'id': '550e8400-e29b-41d4-a716-446655440000'}, "
            "{'is_active': True}, {'brand': 'Acme'}, "
            "{'family_id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'}. "
            "CRITICAL: Use filters when you have specific criteria. "
            "Pass None (or {{}}) for 'list all' queries - both treated as no filtering. "
            "For partial matches, use search_patterns instead."
        )
    )
    columns: list[str] | None = Field(
        default=None,
        description="Specific columns to return (e.g., ['id', 'name', 'sku_prefix']). If None, returns all columns"
    )
    relations: list[str] | None = Field(
        default=None,
        description="Related tables to include using PostgREST syntax (e.g., ['categories(*)', 'variant_axes(variant_values(*))'). Enables joining related data in single query"
    )
    search_patterns: dict[str, str] | None = Field(
        description=(
            "Case-insensitive partial text matching using SQL ILIKE with % wildcards. "
            "WHEN TO USE: When you need fuzzy/partial matches (user says 'bottles', 'jars', 'pet products'). "
            "NOT FOR: Exact lookups with known IDs - use filters instead. "
            "Wildcard patterns: "
            "'%bottle%' = contains 'bottle' anywhere (PET Bottle, Bottle Cap, bottled water), "
            "'bottle%' = starts with 'bottle' (Bottle Cap, Bottled Water), "
            "'%bottle' = ends with 'bottle' (PET Bottle, Glass Bottle). "
            "Examples: {'name': '%jar%'} finds 'PET Jars', 'Glass Jar', 'Mason Jars' | "
            "{'brand': '%acme%', 'material': '%pet%'} finds brands/materials containing those terms. "
            "CRITICAL: Pass None (or {{}}) when not searching - both treated as no pattern matching."
        )
    )
    count_only: bool = Field(
        default=False,
        description="If True, return count of matching rows instead of data"
    )
    limit: int | None = Field(
        default=None,
        description="Maximum number of rows to return"
    )


def create_query_database_tool(storage: StorageInterface) -> BaseTool:
    """
    Create query database tool for specialist data retrieval.

    Exposes advanced query capabilities to agents:
    - Exact match filtering
    - Case-insensitive pattern matching (ILIKE)
    - Relation includes (join data)
    - Count queries
    - Column selection

    Args:
        storage: Storage interface for database operations

    Returns:
        LangChain tool that executes advanced queries
    """

    async def _query_database_impl(
        table: str,
        filters: dict[str, Any] | None = None,
        columns: list[str] | None = None,
        relations: list[str] | None = None,
        search_patterns: dict[str, str] | None = None,
        count_only: bool = False,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """
        Query database with advanced filtering and relation support.

        Flexible data retrieval tool for specialists. Supports exact filters,
        pattern matching, relation includes, counting, and column projection.

        CRITICAL FILTER USAGE:
        - SPECIFIC LOOKUPS: Use filters with entity IDs (UUIDs) or exact values
          (e.g., filters={'id': '550e8400-e29b-41d4-a716-446655440000'}, filters={'brand': 'Acme'})
        - BROAD SEARCHES: Use search_patterns for partial matches (search_patterns={'name': '%bottle%'})
        - LIST ALL: Only use empty filters={} for "list all" queries - otherwise fetches ALL rows (inefficient)
        - UUID FORMAT: Standard 8-4-4-4-12 hex format (e.g., 'a1b2c3d4-e5f6-7890-abcd-ef1234567890')
        - When PM provides entity IDs in delegation → ALWAYS use them in filters

        EFFICIENCY BEST PRACTICES:
        - Always use filters when you have specific criteria
        - Always use UUIDs for filters when PM provides entity IDs in delegation
        - Always use search_patterns for partial matches
        - Count first: Use count_only=True before fetching rows
        - Limit always: Set limit parameter (default to 10 unless specific need)
        - Project columns: Specify columns for specific fields only

        Args:
            table: Table name to query (e.g., "product_families", "products")
            filters: Exact match conditions (e.g., {"is_active": True, "category_id": "uuid"})
            columns: Specific columns to return (e.g., ["id", "name", "sku_prefix"])
                     If None, returns all columns
            relations: Related tables to include using PostgREST syntax
                      (e.g., ["categories(*)", "variant_axes(variant_values(*))"])
                      Enables joining related data in single query
            search_patterns: Case-insensitive partial text matching with SQL ILIKE wildcards
                            Use % for wildcards: '%bottle%' (contains), 'bottle%' (starts with), '%bottle' (ends with)
                            Examples: {"name": "%jar%"} finds "PET Jars", "Glass Jar", "Mason Jars"
                            Multi-field: {"name": "%bottle%", "material": "%pet%"} combines conditions with AND
                            Use for discovery/browsing, NOT for exact ID lookups (use filters instead)
            count_only: If True, return count of matching rows instead of data
            limit: Maximum number of rows to return

        Returns:
            Dict with query results:
            - If count_only=False: {"success": True, "rows": [...], "count": N}
            - If count_only=True: {"success": True, "count": N}
            - On error: {"success": False, "error": "...", "error_type": "..."}

        Examples:
            # Find all active product families with their categories
            query_database(
                table="product_families",
                filters={"is_active": True},
                relations=["categories(*)"],
                limit=10
            )

            # SEARCH PATTERNS - Partial text matching with wildcards

            # Contains 'bottle' anywhere in name
            query_database(
                table="products",
                search_patterns={"name": "%bottle%"},  # Finds: PET Bottle, Bottle Cap, bottled water
                columns=["id", "name", "sku_code"],
                limit=20
            )

            # Starts with 'PET'
            query_database(
                table="product_families",
                search_patterns={"name": "PET%"},  # Finds: PET Bottles, PET Jars, PET Containers
                limit=10
            )

            # Ends with 'Jar'
            query_database(
                table="product_families",
                search_patterns={"name": "%Jar"},  # Finds: PET Jar, Glass Jar, Mason Jar
                limit=10
            )

            # Multi-field search (combines with AND)
            query_database(
                table="products",
                search_patterns={"name": "%bottle%", "material": "%pet%"},  # PET bottles only
                columns=["id", "name", "material"]
            )

            # Count products in a family (using UUID from PM delegation)
            query_database(
                table="products",
                filters={"product_family_id": "550e8400-e29b-41d4-a716-446655440000"},
                count_only=True
            )

            # Get variant axis with all its values (join)
            query_database(
                table="variant_axes",
                filters={"name": "Size"},
                relations=["variant_values(*)"]
            )

            # Get specific product family when PM provides ID (UUID format: 8-4-4-4-12)
            query_database(
                table="product_families",
                filters={"id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"},  # Actual UUID from PM
                relations=["variant_axes(variant_values(*))", "products(*)"]
            )

            # FILTERS vs SEARCH_PATTERNS - When to use which

            # ✓ CORRECT: Use filters when you have specific ID from PM
            query_database(
                table="product_families",
                filters={"id": "550e8400-e29b-41d4-a716-446655440000"},
                relations=["variant_axes(variant_values(*))"]
            )

            # ✓ CORRECT: Use search_patterns when user says "show me bottles"
            query_database(
                table="product_families",
                search_patterns={"name": "%bottle%"},
                limit=10
            )

            # ❌ BAD: Empty filters when you have specific criteria
            # query_database(table="product_families", filters={}, relations=["variant_axes(*)"])
            # This returns ALL families - inefficient!

            # ❌ BAD: Using search_patterns when you have exact UUID
            # query_database(table="product_families", search_patterns={"id": "%550e8400%"})
            # UUIDs are exact - use filters={"id": "..."} instead
        """
        try:
            # Normalize empty dicts to None to remove ambiguity
            # LLMs sometimes pass {} explicitly instead of omitting parameter
            if filters is not None and not filters:
                filters = None
            if search_patterns is not None and not search_patterns:
                search_patterns = None

            logger.info(
                f"Querying {table}",
                extra={
                    "table": table,
                    "has_filters": bool(filters),
                    "has_search": bool(search_patterns),
                    "has_relations": bool(relations),
                    "count_only": count_only,
                }
            )

            # Execute query through storage port
            result = await storage.query_advanced(
                table=table,
                filters=filters,
                columns=columns,
                relations=relations,
                search_patterns=search_patterns,
                count_only=count_only,
                limit=limit,
            )

            # Format response
            if count_only:
                return build_success_response({"count": result})
            else:
                return build_success_response({
                    "rows": result,
                    "count": len(result),
                })

        except Exception as e:
            logger.error(
                f"Query failed for {table}",
                exc_info=True,
                extra={
                    "table": table,
                    "filters": filters,
                    "search_patterns": search_patterns,
                }
            )
            return build_agent_error_response(
                exception=e,
                context={
                    "table": table,
                    "filters": filters,
                    "search_patterns": search_patterns,
                },
                fallback_type="QUERY_ERROR",
                fallback_action="Review query parameters. Simplify query by removing relations/filters. Check if table has data matching filters.",
            )

    return StructuredTool.from_function(
        coroutine=_query_database_impl,
        name="query_database",
        description=(
            "Query database with filters, search patterns, and relations. "
            "CRITICAL USAGE: "
            "1. SPECIFIC LOOKUPS: Use filters for exact matches with UUIDs or exact values "
            "(e.g., filters={'id': '550e8400-e29b-41d4-a716-446655440000'}, filters={'is_active': True, 'brand': 'Acme'}). "
            "2. BROAD SEARCHES: Use search_patterns for partial matches (e.g., search_patterns={'name': '%bottle%'}). "
            "3. LIST ALL: Only use empty filters={} for 'list all' queries - otherwise you'll fetch ALL rows (inefficient). "
            "EFFICIENCY: Count first (count_only=True), always set limit, use relations for joins. "
            "UUID Format: UUIDs are 8-4-4-4-12 hex digits (e.g., '550e8400-e29b-41d4-a716-446655440000'). "
            "When PM provides entity IDs in delegation, ALWAYS use them in filters."
        ),
        args_schema=QueryDatabaseInput,
    )
