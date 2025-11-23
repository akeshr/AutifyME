"""Read Engine - Unified read_data tool for queries, batch reads, pagination.

Agent-centric tool for fetching data with filters, search patterns, joins, and counting.
Part of Universal Data Engine (Phase 1.6).
"""

import logging
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.tool_error_handler import (
    build_agent_error_response,
    build_success_response,
)

logger = logging.getLogger(__name__)


class ReadDataInput(BaseModel):
    """Input schema for unified read_data tool."""

    model_config = {"extra": "forbid"}

    table: str = Field(
        ...,
        description="Table name (e.g., 'products', 'product_families')"
    )
    filters: dict[str, Any] | None = Field(
        None,
        description=(
            "Exact match filters. Examples: "
            "{'is_active': True}, "
            "{'category_id': 'cat-123'}, "
            "{'status': ['draft', 'published']} - IN operator for lists"
        )
    )
    search_patterns: dict[str, str] | None = Field(
        None,
        description=(
            "Case-insensitive ILIKE patterns. Examples: "
            "{'name': '%bottle%'}, "
            "{'sku_code': 'SKU-%'} - Use % as wildcard"
        )
    )
    columns: list[str] | None = Field(
        None,
        description="Columns to select (None = all columns). Example: ['id', 'name', 'price']"
    )
    relations: list[str] | None = Field(
        None,
        description=(
            "Related tables to include. Use PostgREST syntax. "
            "Examples: ['category(id,name)', 'product_family(*)']"
        )
    )
    ids: list[str] | None = Field(
        None,
        description=(
            "Batch fetch by IDs. When provided, fetches only these IDs. "
            "Example: ['id1', 'id2', 'id3']"
        )
    )
    limit: int | None = Field(
        None,
        description="Maximum rows to return (pagination). Default: no limit",
        gt=0,
        le=1000
    )
    offset: int | None = Field(
        None,
        description="Skip N rows (pagination). Use with limit for pages",
        ge=0
    )
    count_only: bool = Field(
        default=False,
        description="Return only count, not actual records. Useful for analytics"
    )


def create_read_data_tool(
    storage: StorageInterface,
    tables: list[str] | None = None,
) -> StructuredTool:
    """
    Create unified read_data tool for all read operations.

    Universal Data Engine - Phase 1.6: Consolidates query, batch read, pagination.

    Enables agents to:
    - Query with filters and search patterns
    - Fetch related data (joins)
    - Batch read by IDs
    - Paginate large result sets
    - Count records efficiently

    Args:
        storage: Storage interface for database operations
        tables: Allowed tables (None = all tables accessible)

    Returns:
        StructuredTool configured for read operations

    Examples:
        # Cataloging Specialist - Product domain only
        read_tool = create_read_data_tool(
            storage,
            tables=["products", "product_families", "categories"]
        )

        # Market Intelligence - Full read access
        read_tool = create_read_data_tool(storage)  # No restrictions
    """
    allowed_tables = tables

    async def _read_data_impl(
        table: str,
        filters: dict[str, Any] | None = None,
        search_patterns: dict[str, str] | None = None,
        columns: list[str] | None = None,
        relations: list[str] | None = None,
        ids: list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        count_only: bool = False,
    ) -> dict[str, Any]:
        """
        Unified read operation for all query patterns.

        USE WHEN:
        - Fetching individual records or lists
        - Searching with filters or patterns
        - Loading related data (joins)
        - Batch fetching by IDs
        - Paginating through results
        - Counting records

        NOT FOR:
        - Aggregations with GROUP BY (use aggregate_data)
        - Writing/updating data (use write_data)

        Returns:
            Query results with metadata (count, pagination info)

        Examples:
            # Basic query with filter
            read_data(
                table="products",
                filters={"is_active": True},
                limit=10
            )

            # Search with pattern
            read_data(
                table="products",
                search_patterns={"name": "%bottle%"},
                columns=["id", "name", "price"]
            )

            # Fetch with relations
            read_data(
                table="products",
                filters={"id": "prod-123"},
                relations=["category(id,name)", "product_family(*)"]
            )

            # Batch fetch by IDs
            read_data(
                table="products",
                ids=["id1", "id2", "id3"]
            )

            # Count only
            read_data(
                table="products",
                filters={"is_active": True},
                count_only=True
            )
        """
        try:
            # Access control: Verify table access
            if allowed_tables is not None and table not in allowed_tables:
                logger.warning(
                    f"Access denied to table: {table}",
                    extra={"requested": table, "allowed": allowed_tables}
                )
                return build_agent_error_response(
                    exception=PermissionError(f"Access denied to table: {table}"),
                    context={"table": table},
                    fallback_type="ACCESS_DENIED",
                    fallback_action=(
                        f"You don't have access to table '{table}'. "
                        f"Available tables: {allowed_tables}. "
                        f"Request access from system administrator if needed."
                    )
                )

            logger.info(
                f"Reading data from {table}",
                extra={
                    "table": table,
                    "has_filters": filters is not None,
                    "has_search": search_patterns is not None,
                    "has_ids": ids is not None,
                    "count_only": count_only,
                    "limit": limit
                }
            )

            # BATCH READ: Fetch by IDs
            if ids is not None:
                results = await storage.batch_read(
                    table=table,
                    ids=ids,
                    relations=relations
                )

                logger.info(
                    f"Batch read returned {len(results)} record(s)",
                    extra={"table": table, "id_count": len(ids)}
                )

                return build_success_response({
                    "table": table,
                    "operation": "batch_read",
                    "results": results,
                    "count": len(results),
                    "requested_ids": len(ids),
                })

            # COUNT ONLY: Efficient counting
            if count_only:
                count = await storage.count_entities(
                    table=table,
                    filters=filters
                )

                logger.info(
                    f"Count query returned {count}",
                    extra={"table": table}
                )

                return build_success_response({
                    "table": table,
                    "operation": "count",
                    "count": count,
                })

            # STANDARD QUERY: Filters, search, relations, pagination
            results = await storage.query_advanced(
                table=table,
                filters=filters,
                columns=columns,
                relations=relations,
                search_patterns=search_patterns,
                count_only=False,
                limit=limit
            )

            # Apply offset if specified (query_advanced doesn't support offset directly)
            if offset is not None and offset > 0:
                results = results[offset:]

            logger.info(
                f"Query returned {len(results)} record(s)",
                extra={
                    "table": table,
                    "result_count": len(results),
                    "has_pagination": limit is not None or offset is not None
                }
            )

            response_data: dict[str, Any] = {
                "table": table,
                "operation": "query",
                "results": results,
                "count": len(results),
            }

            # Add pagination metadata if applicable
            if limit is not None or offset is not None:
                response_data["pagination"] = {
                    "limit": limit,
                    "offset": offset or 0,
                    "has_more": len(results) == limit if limit else False
                }

            return build_success_response(response_data)

        except PermissionError:
            # Re-raise to avoid double-wrapping
            raise

        except Exception as e:
            logger.error(
                f"Read operation failed for {table}",
                exc_info=True,
                extra={"table": table, "operation_type": "batch" if ids else "query"}
            )
            return build_agent_error_response(
                exception=e,
                context={"table": table},
                fallback_type="QUERY_ERROR",
                fallback_action=(
                    f"Query failed for {table}. "
                    f"Verify table name, filters, and search patterns. "
                    f"Check available tables with inspect_schema tool."
                )
            )

    return StructuredTool.from_function(
        func=_read_data_impl,
        name="read_data",
        description=(
            "Unified read operations: query with filters, search patterns, joins, batch fetch by IDs, pagination, and counting. "
            "USE WHEN: Fetching records, searching data, loading related entities, paginating results, counting. "
            "RETURNS: Records matching criteria with optional relations and pagination metadata. "
            "NOT FOR: Aggregations (use aggregate_data) or writing data (use write_data)."
        ),
        args_schema=ReadDataInput,
        coroutine=_read_data_impl,
    )
