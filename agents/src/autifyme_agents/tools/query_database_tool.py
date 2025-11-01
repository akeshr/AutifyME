"""Query database tool - flexible data retrieval for specialists.

Gives specialists direct query access with advanced filtering, relations,
pattern matching, and counting capabilities.
"""

import logging
from typing import Any

from langchain.tools import tool
from langchain_core.tools import BaseTool

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.tool_error_handler import (
    build_agent_error_response,
    build_success_response,
)

logger = logging.getLogger(__name__)


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

    @tool("query_database")
    async def query_database(
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

        EFFICIENCY BEST PRACTICES:
        - Count first: Use count_only=True before fetching rows
        - Limit always: Set limit parameter (default to 10 unless specific need)
        - Project columns: Specify columns for specific fields only
        - Filter precisely: Use filters for exact match, search_patterns for LIKE

        Args:
            table: Table name to query (e.g., "product_families", "products")
            filters: Exact match conditions (e.g., {"is_active": True, "category_id": "uuid"})
            columns: Specific columns to return (e.g., ["id", "name", "sku_prefix"])
                     If None, returns all columns
            relations: Related tables to include using PostgREST syntax
                      (e.g., ["categories(*)", "variant_axes(variant_values(*))"])
                      Enables joining related data in single query
            search_patterns: Case-insensitive pattern matching
                            (e.g., {"name": "%bottle%", "brand": "%acme%"})
                            Use % as wildcards for LIKE queries
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

            # Search for products by name pattern
            query_database(
                table="products",
                search_patterns={"name": "%bottle%"},
                columns=["id", "name", "sku_code"]
            )

            # Count products in a family
            query_database(
                table="products",
                filters={"product_family_id": "uuid-123"},
                count_only=True
            )

            # Get variant axis with all its values (join)
            query_database(
                table="variant_axes",
                filters={"name": "Size"},
                relations=["variant_values(*)"]
            )
        """
        try:
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

    return query_database
