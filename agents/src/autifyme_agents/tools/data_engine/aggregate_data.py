"""Read Engine - Aggregation queries for analytics.

Agent-centric tool for aggregations (count, sum, avg, min, max) with GROUP BY/HAVING.
Part of Universal Data Engine (Phase 1.2).
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


class AggregateDataInput(BaseModel):
    """Input schema for aggregate_data tool."""

    model_config = {"extra": "forbid"}

    table: str = Field(
        ...,
        description="Table name to aggregate (e.g., 'products', 'campaigns')"
    )
    aggregates: dict[str, str] = Field(
        ...,
        description=(
            "Aggregation operations as {alias: 'function(column)'}. "
            "Examples: "
            "{'total': 'count(*)'} - count all rows, "
            "{'avg_val': 'avg(amount)'} - average price, "
            "{'min_price': 'min(amount)', 'max_price': 'max(amount)'} - min/max. "
            "Supported functions: count, sum, avg, min, max"
        )
    )
    filters: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "[EXACT MATCH] Case-sensitive filters applied BEFORE aggregation.\n"
            "Use for: IDs, booleans, enums, status codes.\n"
            "Examples: {'is_active': True}, {'parent_id': 'uuid-123'}, {'status': ['active','draft']}.\n"
            "CRITICAL: For text/name filtering, use search_patterns instead (fuzzy match)."
        )
    )
    search_patterns: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "[FUZZY MATCH] Case-insensitive ILIKE patterns applied BEFORE aggregation.\n"
            "Use % as wildcard.\n"
            "Examples: {'name': '%jar%'} (contains), {'sku': 'PET-%'} (starts with), {'name': '%PET%bottle%'} (contains both).\n"
            "Use for: name searches, SKU patterns, description matching."
        )
    )
    group_by: list[str] | None = Field(
        default=None,
        description="Columns to group by (e.g., ['category_id', 'brand'])"
    )
    having: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Filters on aggregated results. "
            "Examples: "
            "{'total': {'gt': 10}} - groups with total > 10, "
            "{'avg_val': {'gte': 100, 'lte': 500}} - average price between 100-500. "
            "Operators: gt, gte, lt, lte, eq, neq"
        )
    )


def create_aggregate_data_tool(
    storage: StorageInterface,
    tables: list[str] | None = None,
) -> StructuredTool:
    """
    Create aggregate_data tool for analytics queries.

    Enables agents to perform aggregations like counting, summing, averaging
    with GROUP BY and HAVING clauses for analytical insights.

    Args:
        storage: Storage interface for database operations
        tables: Allowed tables (None = all tables accessible)

    Returns:
        StructuredTool configured for aggregation queries

    Examples:
        # Cataloging Specialist - Product analytics
        aggregate_tool = create_aggregate_data_tool(
            storage,
            tables=["products", "product_families"]
        )

        # Market Intelligence - Full analytics access
        aggregate_tool = create_aggregate_data_tool(storage)  # No restrictions
    """
    allowed_tables = tables

    async def _aggregate_data_impl(
        table: str,
        aggregates: dict[str, str],
        filters: dict[str, Any] | None = None,
        search_patterns: dict[str, str] | None = None,
        group_by: list[str] | None = None,
        having: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Perform aggregation query with GROUP BY and HAVING.

        USE WHEN:
        - Counting records by category/group
        - Calculating sums, averages, min/max
        - Analyzing data distributions
        - Getting statistical insights

        NOT FOR:
        - Fetching individual records (use read_data instead)
        - Simple counts without grouping (use read_data with count_only)

        Returns:
            Aggregated results with all group columns and computed aggregates

        Examples:
            # Count products per category
            aggregate_data(
                table="products",
                aggregates={"count": "count(*)"},
                group_by=["category_id"]
            )

            # Average price by brand, only active products
            aggregate_data(
                table="products",
                aggregates={"avg_val": "avg(amount)", "count": "count(*)"},
                filters={"is_active": True},
                group_by=["brand"],
                having={"count": {"gt": 5}}
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
                f"Aggregating data from {table}",
                extra={
                    "table": table,
                    "aggregates": list(aggregates.keys()),
                    "group_by": group_by
                }
            )

            # Execute aggregation query
            results = await storage.query_aggregate(
                table=table,
                aggregates=aggregates,
                filters=filters or {},
                search_patterns=search_patterns or {},
                group_by=group_by,
                having=having,
            )

            logger.info(
                f"Aggregation returned {len(results)} result(s)",
                extra={"table": table, "result_count": len(results)}
            )

            return build_success_response({
                "table": table,
                "aggregates": list(aggregates.keys()),
                "group_by": group_by or [],
                "results": results,
                "count": len(results),
            })

        except PermissionError:
            # Re-raise to avoid double-wrapping
            raise

        except Exception as e:
            logger.error(
                f"Aggregation failed for {table}",
                exc_info=True,
                extra={"table": table, "aggregates": aggregates}
            )
            return build_agent_error_response(
                exception=e,
                context={"table": table},
                fallback_type="QUERY_ERROR",
                fallback_action=(
                    f"Aggregation query failed for {table}. "
                    f"Verify aggregate syntax and try again. "
                    f"Supported functions: count, sum, avg, min, max."
                )
            )

    return StructuredTool.from_function(
        func=_aggregate_data_impl,
        name="aggregate_data",
        description=(
            "Perform analytics with aggregations (count, sum, avg, min, max) and GROUP BY/HAVING.\n\n"
            "AGGREGATES SYNTAX:\n"
            "- Format: {'alias': 'function(column)'}\n"
            "- Functions: count(*), sum(col), avg(col), min(col), max(col)\n"
            "- Multiple: {'total': 'count(*)', 'avg_val': 'avg(amount)', 'price_range': 'max(amount)-min(amount)'}\n\n"
            "SCENARIOS:\n"
            "- Count by category: aggregates={'count':'count(*)','avg_val':'avg(amount)'}, group_by=['parent_id'] - records per category\n"
            "- Find sparse groups: aggregates={'count':'count(*)'}, group_by=['parent_id'], having={'count':{'lt':5}} - groups with <5 records\n"
            "- Value variance: aggregates={'spread':'max(amount)-min(amount)'}, group_by=['parent_id'], having={'spread':{'gt':50}} - value variance\n"
            "- Child count: table='child_records', aggregates={'count':'count(*)'}, group_by=['group_id'] - children per parent\n"
            "- Dashboard totals: aggregates={'total':'count(*)','active':'sum(case when is_active then 1 else 0 end)','total_value':'sum(amount)'} - no group_by for totals\n\n"
            "HAVING OPERATORS:\n"
            "- {'alias': {'gt': N}} - greater than\n"
            "- {'alias': {'gte': N}} - greater than or equal\n"
            "- {'alias': {'lt': N}} - less than\n"
            "- {'alias': {'lte': N}} - less than or equal\n"
            "- Multiple: {'count': {'gte': 10}, 'total_value': {'gte': 1000}} - AND logic\n\n"
            "RETURNS: {results: [{group_col: val, alias: computed_val}, ...], count: N}\n\n"
            "NOT FOR: Fetching individual records (use read_data), simple counts without grouping (use read_data with count_only=True)."
        ),
        args_schema=AggregateDataInput,
        coroutine=_aggregate_data_impl,
    )
