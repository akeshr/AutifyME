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
        description="Table name to aggregate (e.g., 'table_a', 'table_b')"
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
            "Examples: {'name': '%keyword%'} (contains), {'code': 'PREFIX-%'} (starts with), {'name': '%term1%term2%'} (contains both).\n"
            "Use for: name searches, code patterns, description matching."
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
        # Specialist - Domain-scoped analytics
        aggregate_tool = create_aggregate_data_tool(
            storage,
            tables=["table_a", "table_b"]
        )

        # Analyst - Full analytics access
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
            # Count records per group column
            aggregate_data(
                table="table_a",
                aggregates={"count": "count(*)"},
                group_by=["column_1"]
            )

            # Average value by grouping column, only active records
            aggregate_data(
                table="table_a",
                aggregates={"avg_val": "avg(column_2)", "count": "count(*)"},
                filters={"is_active": True},
                group_by=["column_1"],
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
            "PURPOSE: Analytics and statistics - count, sum, avg, min, max with GROUP BY and HAVING. Transform raw data into insights: record counts by group, value patterns, distributions.\n\n"
            "USE WHEN:\n"
            "- Distribution analysis: Records per group, items per category, orders per customer\n"
            "- Statistical calculations: Average values, value ranges, total sums\n"
            "- Quality audits: Empty groups, sparse data, outliers\n"
            "- Business intelligence: Totals by category, counts by type\n"
            "- Planning decisions: Which groups need attention?\n"
            "- Dashboard metrics: Total counts, averages, sums for reporting\n\n"
            "DON'T USE:\n"
            "- For individual records (use read_data - aggregate returns summaries, not rows)\n"
            "- Simple total counts without grouping (use read_data count_only=True - more efficient)\n"
            "- When you need actual data (aggregate returns computed values, not records)\n"
            "- Schema discovery (use inspect_schema)\n\n"
            "CRITICAL:\n"
            "- aggregates parameter: {alias: 'function(column)'} - alias becomes result key, use descriptive names\n"
            "  Functions: count(*), sum(col), avg(col), min(col), max(col)\n"
            "- group_by: Columns to group by - null/empty returns single row with overall totals\n"
            "- filters/search_patterns: Applied BEFORE grouping (reduces dataset)\n"
            "- having: Applied AFTER grouping (filters computed aggregates) - alias must match aggregates key\n"
            "  Operators: gt, gte, lt, lte, eq, neq\n"
            "- Multiple aggregates in one query: {'count': 'count(*)', 'avg_val': 'avg(column_1)', 'min_val': 'min(column_1)'}\n\n"
            "EXAMPLES:\n"
            "# Distribution: Count records per group\n"
            "aggregate_data(table='table_a', aggregates={'record_count': 'count(*)', 'avg_val': 'avg(column_1)'}, filters={'is_active': True}, group_by=['parent_id'])\n"
            "Returns: [{parent_id: 'id-1', record_count: 12, avg_val: 35.5}, {parent_id: 'id-2', record_count: 8, avg_val: 28.0}, ...]\n\n"
            "# Quality audit: Find groups with sparse records\n"
            "aggregate_data(table='table_a', aggregates={'item_count': 'count(*)'}, filters={'is_active': True}, group_by=['parent_id'], having={'item_count': {'lt': 3}})\n"
            "Returns: Only groups with <3 active records - [{parent_id: 'id-5', item_count: 1}, ...]\n\n"
            "ALSO CONSIDER:\n"
            "- read_data: Need actual records, not summaries? Use read_data\n"
            "- read_data count_only=True: Simple total count without grouping? More efficient\n"
            "- inspect_schema: Unsure what columns to aggregate? Discover structure first\n\n"
            "RETURNS: Always a structured dict with success flag.\n"
            "- success=True: {table, aggregates, group_by, results, count}\n"
            "  * results is an array of rows with group_by columns + aggregate aliases\n"
            "- success=False: {error, error_type, table, Agent Action: ...}"
        ),
        args_schema=AggregateDataInput,
        coroutine=_aggregate_data_impl,
    )
