"""Universal Data Engine - Agent-centric tool factories with access control.

Three powerful engines for agent data operations:
- inspect_schema: Understand data structure (schema discovery, stats, samples)
- read_data: Fetch, search, analyze (coming in Phase 1.2-1.3)
- write_data: Create, update, delete (coming in Phase 1.4-1.5)

Built from scratch with intelligence-first design:
- Token-efficient (schema fetched on-demand, not in prompts)
- Specialist-scoped access control (table + operation restrictions)
- Agent-centric naming (what agents DO, not database mechanics)
"""

import logging
from typing import Any, Literal

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.tool_error_handler import (
    build_agent_error_response,
    build_success_response,
)
from autifyme_agents.schemas.registry import SchemaRegistry

logger = logging.getLogger(__name__)


# =============================================================================
# Phase 1.1: Schema Engine - inspect_schema tool
# =============================================================================


class InspectSchemaInput(BaseModel):
    """Input schema for inspect_schema tool."""

    model_config = {"extra": "forbid"}

    tables: list[str] = Field(
        ...,
        description="List of tables to inspect (e.g., ['products', 'product_families'])"
    )
    details: list[Literal["structure", "relationships", "stats", "samples"]] = Field(
        default=["structure"],
        description=(
            "What to include in response:\n"
            "- structure: Columns, types, constraints\n"
            "- relationships: Foreign keys, cascades\n"
            "- stats: Row counts, index info\n"
            "- samples: Real data examples"
        )
    )
    sample_limit: int = Field(
        default=3,
        description="How many sample rows per table (default: 3, max: 10)",
        ge=1,
        le=10
    )


class InspectSchemaToolConfig(BaseModel):
    """Configuration for inspect_schema tool with access control."""

    allowed_tables: list[str] | None = Field(
        None,
        description="Table restrictions (None = all tables accessible)"
    )
    version: str = Field(
        default="v1",
        description="Schema version to use"
    )
    domain: str = Field(
        default="product_catalog",
        description="Domain name (for multi-domain support)"
    )


def create_inspect_schema_tool(
    storage: StorageInterface,
    tables: list[str] | None = None,
    version: str = "v1",
    domain: str = "product_catalog",
) -> StructuredTool:
    """
    Create inspect_schema tool with specialist-scoped access control.

    Agent-centric tool for understanding database structure. Agents use this
    to discover tables, understand schemas, check statistics, and see sample data.

    Args:
        storage: Storage interface for stats/samples
        tables: Allowed tables (None = all tables accessible)
        version: Schema version (default: "v1")
        domain: Domain name (default: "product_catalog")

    Returns:
        StructuredTool configured for this specialist

    Examples:
        # Cataloging Specialist - Full access to product domain
        inspect_schema_tool = create_inspect_schema_tool(
            storage,
            tables=["product_families", "products", "variant_axes", "variant_values"]
        )

        # Market Intelligence - Read-only, all tables
        inspect_schema_tool = create_inspect_schema_tool(storage)  # No restrictions

        # Campaign Specialist - Campaign domain only
        inspect_schema_tool = create_inspect_schema_tool(
            storage,
            tables=["campaigns", "ad_copies"]
        )
    """
    config = InspectSchemaToolConfig(
        allowed_tables=tables,
        version=version,
        domain=domain
    )

    async def _inspect_schema_impl(
        tables: list[str],
        details: list[Literal["structure", "relationships", "stats", "samples"]] | None = None,
        sample_limit: int = 3,
    ) -> dict[str, Any]:
        """
        Inspect database schema with access control.

        USE WHEN:
        - Before complex operations to verify structure
        - Understanding relationships between tables
        - Checking if tables/columns exist
        - Seeing real data examples

        NOT NEEDED:
        - For routine operations (you know the schema)
        - Just fetching data (use read_data instead)

        Returns:
            Schema information for requested tables with requested details

        Examples:
            # Basic structure only
            inspect_schema(
                tables=["products"],
                details=["structure"]
            )

            # Full inspection with samples
            inspect_schema(
                tables=["product_families", "products"],
                details=["structure", "relationships", "stats", "samples"],
                sample_limit=5
            )
        """
        try:
            # Initialize default for mutable parameter
            if details is None:
                details = ["structure"]

            # Access control: Verify table access
            if config.allowed_tables is not None:
                unauthorized = [t for t in tables if t not in config.allowed_tables]
                if unauthorized:
                    logger.warning(
                        f"Access denied to tables: {unauthorized}",
                        extra={"requested": tables, "allowed": config.allowed_tables}
                    )
                    return build_agent_error_response(
                        exception=PermissionError(f"Access denied to tables: {unauthorized}"),
                        context={"unauthorized_tables": unauthorized},
                        fallback_type="ACCESS_DENIED",
                        fallback_action=(
                            f"You don't have access to tables: {unauthorized}. "
                            f"Available tables: {config.allowed_tables}. "
                            f"Request access from system administrator if needed."
                        )
                    )

            # Load schema from registry
            logger.info(
                f"Loading schema for tables: {tables}",
                extra={"tables": tables, "details": details, "version": config.version}
            )

            schema_registry = SchemaRegistry.get_version(
                version=config.version,
                domain=config.domain
            )

            result: dict[str, Any] = {
                "version": schema_registry.version,
                "domain": schema_registry.domain,
                "tables": {}
            }

            # Process each table
            for table_name in tables:
                try:
                    table_schema = schema_registry.get_table(table_name)
                    table_data: dict[str, Any] = {}

                    # Structure (columns, types, constraints)
                    if "structure" in details:
                        table_data["structure"] = {
                            "name": table_schema.name,
                            "description": table_schema.description,
                            "primary_key": table_schema.primary_key,
                            "columns": {
                                name: {
                                    "type": col.type,
                                    "nullable": col.nullable,
                                    "unique": col.unique,
                                    "default": col.default,
                                    "max_length": col.max_length,
                                    "description": col.description,
                                }
                                for name, col in table_schema.columns.items()
                            },
                            "required_columns": table_schema.get_required_columns(),
                            "unique_columns": table_schema.get_unique_columns(),
                            "indexes": table_schema.indexes,
                        }

                    # Relationships (foreign keys, cascades)
                    if "relationships" in details:
                        table_data["relationships"] = [
                            {
                                "type": rel.type,
                                "target_table": rel.target_table,
                                "foreign_key": rel.foreign_key,
                                "target_column": rel.target_column,
                                "cascade_delete": rel.cascade_delete,
                                "cascade_update": rel.cascade_update,
                                "description": rel.description,
                            }
                            for rel in table_schema.relationships
                        ]

                    # Statistics (row counts, index info)
                    if "stats" in details:
                        try:
                            stats = await storage.get_table_stats(table_name)
                            table_data["stats"] = stats
                        except Exception as e:
                            logger.warning(
                                f"Could not fetch stats for {table_name}",
                                exc_info=True
                            )
                            table_data["stats"] = {"error": str(e)}

                    # Samples (real data examples)
                    if "samples" in details:
                        try:
                            samples = await storage.sample_data(
                                table=table_name,
                                limit=sample_limit
                            )
                            table_data["samples"] = samples
                        except Exception as e:
                            logger.warning(
                                f"Could not fetch samples for {table_name}",
                                exc_info=True
                            )
                            table_data["samples"] = {"error": str(e)}

                    result["tables"][table_name] = table_data

                except ValueError:
                    logger.error(
                        f"Table not found: {table_name}",
                        exc_info=True
                    )
                    result["tables"][table_name] = {
                        "error": f"Table '{table_name}' not found in schema"
                    }

            logger.info(
                f"Schema inspection complete for {len(tables)} tables",
                extra={"tables": tables, "details": details}
            )

            return build_success_response(result)

        except FileNotFoundError as e:
            logger.error(
                f"Schema version not found: {config.version}",
                exc_info=True
            )
            return build_agent_error_response(
                exception=e,
                context={"version": config.version, "domain": config.domain},
                fallback_type="SCHEMA_ERROR",
                fallback_action=(
                    f"Schema version '{config.version}' not found for domain '{config.domain}'. "
                    f"Contact system administrator."
                )
            )

        except Exception as e:
            logger.error(
                "Schema inspection failed",
                exc_info=True,
                extra={"tables": tables, "error_type": type(e).__name__}
            )
            return build_agent_error_response(
                exception=e,
                context={"tables": tables},
                fallback_type="SCHEMA_ERROR",
                fallback_action=(
                    "Schema registry issue. Verify table names and try again. "
                    "Contact system administrator if persistent."
                )
            )

    return StructuredTool.from_function(
        func=_inspect_schema_impl,
        name="inspect_schema",
        description=(
            "Inspect database schema to understand data structure. "
            "USE WHEN: Before complex operations, verifying table structure, understanding relationships, seeing sample data. "
            "RETURNS: Schema metadata (columns, types, constraints, foreign keys, stats, samples). "
            "CRITICAL: Returns STRUCTURE, not actual data queries - use read_data for fetching data."
        ),
        args_schema=InspectSchemaInput,
        coroutine=_inspect_schema_impl,
    )


# =============================================================================
# Phase 1.2: Read Engine - Aggregations
# =============================================================================


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
            "{'avg_price': 'avg(base_price)'} - average price, "
            "{'min_price': 'min(base_price)', 'max_price': 'max(base_price)'} - min/max. "
            "Supported functions: count, sum, avg, min, max"
        )
    )
    filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Exact match filters applied before aggregation (e.g., {'is_active': True})"
    )
    search_patterns: dict[str, str] = Field(
        default_factory=dict,
        description="ILIKE patterns applied before aggregation (e.g., {'brand': '%acme%'})"
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
            "{'avg_price': {'gte': 100, 'lte': 500}} - average price between 100-500. "
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
                aggregates={"avg_price": "avg(base_price)", "count": "count(*)"},
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
            "Perform aggregation queries (count, sum, avg, min, max) with GROUP BY and HAVING. "
            "USE WHEN: Analyzing data, counting by category, calculating statistics, getting insights. "
            "RETURNS: Aggregated results with group columns and computed values. "
            "NOT FOR: Fetching individual records - use read_data for that."
        ),
        args_schema=AggregateDataInput,
        coroutine=_aggregate_data_impl,
    )


# =============================================================================
# Phase 1.3+: Read Engine - Additional Features (PLACEHOLDER)
# =============================================================================

# TODO: Implement create_read_data_tool in Phase 1.3+
# - Batch read (fetch multiple by ID)
# - Pagination (cursor + offset)
# - Full-text search (beyond ILIKE)


# =============================================================================
# Phase 1.4-1.5: Write Engine - write_data tool (PLACEHOLDER)
# =============================================================================

# TODO: Implement create_write_data_tool in Phase 1.4-1.5
# - Upsert (insert or update)
# - Partial update (PATCH)
# - Dry-run mode (preview without executing)
# - Validation preview
# - Streamlined WriteIntent with auto-execution plan
