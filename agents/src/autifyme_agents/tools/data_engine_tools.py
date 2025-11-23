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
# Phase 1.6: Read Engine - Unified read_data tool
# =============================================================================


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


# =============================================================================
# Phase 1.6: Write Engine - Unified write_data tool
# =============================================================================


class WriteDataInput(BaseModel):
    """Input schema for unified write_data tool."""

    model_config = {"extra": "forbid"}

    operation: Literal["insert", "update", "delete", "upsert", "patch"] = Field(
        ...,
        description=(
            "Write operation type:\n"
            "- insert: Create new record(s)\n"
            "- update: Update existing record(s) matching filters\n"
            "- delete: Delete record(s) matching filters\n"
            "- upsert: Insert or update (idempotent, requires conflict_fields)\n"
            "- patch: Partial update of specific fields"
        )
    )
    table: str = Field(
        ...,
        description="Table name (e.g., 'products', 'categories')"
    )
    data: dict[str, Any] | list[dict[str, Any]] | None = Field(
        None,
        description=(
            "Data to write. Single dict or list of dicts. "
            "Required for: insert, upsert, patch. "
            "Optional for: update (uses updates field instead), delete (ignored)"
        )
    )
    filters: dict[str, Any] | None = Field(
        None,
        description=(
            "Filter conditions for update/delete operations. "
            "Example: {'is_active': False}, {'status': 'draft'}. "
            "Required for: update, delete. Ignored for: insert, upsert, patch"
        )
    )
    updates: dict[str, Any] | None = Field(
        None,
        description=(
            "Field updates for update operation. "
            "Example: {'status': 'published', 'updated_at': 'now()'}. "
            "Used with filters to update multiple records. "
            "For single-record updates, use patch instead"
        )
    )
    id: str | None = Field(
        None,
        description="Entity ID for patch operation. Required for: patch"
    )
    conflict_fields: list[str] | None = Field(
        None,
        description=(
            "Fields to check for conflicts in upsert operation. "
            "Example: ['sku_code'], ['tenant_id', 'slug']. "
            "Defaults to 'id' if not specified. "
            "Required for: upsert with non-ID conflicts"
        )
    )
    dry_run: bool = Field(
        default=False,
        description=(
            "Preview mode: validate and show impact without executing. "
            "Returns validation results, constraint violations, and affected count"
        )
    )
    validate_only: bool = Field(
        default=False,
        description=(
            "Validation mode: check schema and constraints without executing. "
            "Returns validation errors and warnings"
        )
    )


def create_write_data_tool(
    storage: StorageInterface,
    tables: list[str] | None = None,
    operations: list[str] | None = None,
) -> StructuredTool:
    """
    Create unified write_data tool for all write operations.

    Universal Data Engine - Phase 1.6: Consolidates insert, update, delete, upsert, patch,
    validation, and dry-run capabilities.

    Enables agents to:
    - Insert new records (single or bulk)
    - Update existing records (filtered or by ID)
    - Delete records (with safety checks)
    - Upsert for idempotent operations
    - Patch for partial field updates
    - Validate before writing
    - Preview write impact (dry-run)

    Args:
        storage: Storage interface for database operations
        tables: Allowed tables (None = all tables accessible)
        operations: Allowed operations (None = all operations allowed)
                   Options: ["insert", "update", "delete", "upsert", "patch"]

    Returns:
        StructuredTool configured for write operations

    Examples:
        # Cataloging Specialist - Full CRUD on product domain
        write_tool = create_write_data_tool(
            storage,
            tables=["products", "product_families", "categories"],
            operations=["insert", "update", "upsert", "patch"]  # No delete
        )

        # Campaign Specialist - Create and update only
        write_tool = create_write_data_tool(
            storage,
            tables=["campaigns", "ad_copies"],
            operations=["insert", "update"]  # No delete, upsert, or patch
        )
    """
    allowed_tables = tables
    allowed_operations = operations

    async def _write_data_impl(
        operation: Literal["insert", "update", "delete", "upsert", "patch"],
        table: str,
        data: dict[str, Any] | list[dict[str, Any]] | None = None,
        filters: dict[str, Any] | None = None,
        updates: dict[str, Any] | None = None,
        id: str | None = None,
        conflict_fields: list[str] | None = None,
        dry_run: bool = False,
        validate_only: bool = False,
    ) -> dict[str, Any]:
        """
        Unified write operation for all mutation patterns.

        USE WHEN:
        - Creating new records
        - Updating existing records
        - Deleting records
        - Idempotent upserts
        - Partial field updates (patch)
        - Validating before writing
        - Previewing write impact

        NOT FOR:
        - Reading data (use read_data)
        - Aggregations (use aggregate_data)

        Returns:
            Operation result with affected records, counts, and validation info

        Examples:
            # Insert single record
            write_data(
                operation="insert",
                table="products",
                data={"sku_code": "SKU-001", "name": "Product A", "price": 100}
            )

            # Bulk insert
            write_data(
                operation="insert",
                table="products",
                data=[
                    {"sku_code": "SKU-001", "name": "Product A"},
                    {"sku_code": "SKU-002", "name": "Product B"}
                ]
            )

            # Update with filter
            write_data(
                operation="update",
                table="products",
                filters={"status": "draft"},
                updates={"status": "published"}
            )

            # Upsert (idempotent)
            write_data(
                operation="upsert",
                table="products",
                data={"sku_code": "SKU-001", "name": "Product A Updated"},
                conflict_fields=["sku_code"]
            )

            # Patch (partial update)
            write_data(
                operation="patch",
                table="products",
                id="prod-123",
                data={"price": 150.0}
            )

            # Dry-run preview
            write_data(
                operation="delete",
                table="products",
                filters={"is_active": False},
                dry_run=True
            )

            # Validation only
            write_data(
                operation="insert",
                table="products",
                data={"sku_code": "SKU-001"},  # Missing required fields
                validate_only=True
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

            # Access control: Verify operation access
            if allowed_operations is not None and operation not in allowed_operations:
                logger.warning(
                    f"Access denied to operation: {operation}",
                    extra={"requested": operation, "allowed": allowed_operations}
                )
                return build_agent_error_response(
                    exception=PermissionError(f"Access denied to operation: {operation}"),
                    context={"operation": operation, "table": table},
                    fallback_type="ACCESS_DENIED",
                    fallback_action=(
                        f"You don't have permission for '{operation}' operation. "
                        f"Allowed operations: {allowed_operations}. "
                        f"Request access from system administrator if needed."
                    )
                )

            logger.info(
                f"Write operation: {operation} on {table}",
                extra={
                    "operation": operation,
                    "table": table,
                    "dry_run": dry_run,
                    "validate_only": validate_only
                }
            )

            # VALIDATION ONLY MODE
            if validate_only:
                if data is None:
                    return build_agent_error_response(
                        exception=ValueError("data is required for validation"),
                        context={"operation": operation},
                        fallback_type="VALIDATION_ERROR",
                        fallback_action="Provide data to validate"
                    )

                validation_result = await storage.validate_entity_data(
                    table=table,
                    data=data,
                    operation=operation  # type: ignore
                )

                # Also check constraints if not upsert
                if operation != "upsert":
                    constraint_result = await storage.check_constraint_violations(
                        table=table,
                        data=data,
                        operation=operation  # type: ignore
                    )
                    validation_result["constraint_violations"] = constraint_result["violations"]
                    validation_result["safe_to_proceed"] = (
                        validation_result["valid"] and constraint_result["safe_to_proceed"]
                    )
                else:
                    validation_result["safe_to_proceed"] = validation_result["valid"]

                logger.info(
                    f"Validation complete for {table}",
                    extra={"valid": validation_result["valid"]}
                )

                return build_success_response({
                    "table": table,
                    "operation": "validate",
                    "validation": validation_result,
                })

            # DRY-RUN MODE
            if dry_run:
                if operation in ("update", "delete"):
                    # Preview impact
                    preview = await storage.preview_write_impact(
                        table=table,
                        filters=filters,
                        operation=operation  # type: ignore
                    )

                    logger.info(
                        f"Dry-run preview for {operation} on {table}",
                        extra={"affected_count": preview["affected_count"]}
                    )

                    return build_success_response({
                        "table": table,
                        "operation": f"dry_run_{operation}",
                        "preview": preview,
                    })
                elif data is not None:
                    # Validate data
                    validation_result = await storage.validate_entity_data(
                        table=table,
                        data=data,
                        operation=operation  # type: ignore
                    )

                    # Check constraints if not upsert
                    if operation != "upsert":
                        constraint_result = await storage.check_constraint_violations(
                            table=table,
                            data=data,
                            operation=operation  # type: ignore
                        )
                        validation_result["constraint_violations"] = constraint_result["violations"]
                        validation_result["safe_to_proceed"] = (
                            validation_result["valid"] and constraint_result["safe_to_proceed"]
                        )
                    else:
                        validation_result["safe_to_proceed"] = validation_result["valid"]

                    logger.info(
                        f"Dry-run validation for {operation} on {table}",
                        extra={"valid": validation_result["valid"]}
                    )

                    return build_success_response({
                        "table": table,
                        "operation": f"dry_run_{operation}",
                        "validation": validation_result,
                    })

            # EXECUTE OPERATION
            result_data: dict[str, Any] = {
                "table": table,
                "operation": operation,
            }

            if operation == "insert":
                if data is None:
                    return build_agent_error_response(
                        exception=ValueError("data is required for insert"),
                        context={"operation": operation},
                        fallback_type="VALIDATION_ERROR",
                        fallback_action="Provide data to insert"
                    )

                # Handle single vs bulk insert
                if isinstance(data, list):
                    # Use bulk_upsert for efficient bulk insert
                    # (without conflict_fields, new records are simply inserted)
                    results = await storage.bulk_upsert(table=table, data=data)
                    result_data["results"] = results
                    result_data["count"] = len(results)
                else:
                    result = await storage.insert_entity(table=table, data=data)
                    result_data["result"] = result
                    result_data["count"] = 1

            elif operation == "update":
                if filters is None or updates is None:
                    return build_agent_error_response(
                        exception=ValueError("filters and updates are required for update"),
                        context={"operation": operation},
                        fallback_type="VALIDATION_ERROR",
                        fallback_action="Provide filters and updates"
                    )

                count = await storage.update_entities(
                    table=table,
                    filters=filters,
                    updates=updates
                )
                result_data["affected_count"] = count

            elif operation == "delete":
                if filters is None:
                    return build_agent_error_response(
                        exception=ValueError("filters are required for delete"),
                        context={"operation": operation},
                        fallback_type="VALIDATION_ERROR",
                        fallback_action="Provide filters for delete operation"
                    )

                count = await storage.delete_entities(table=table, filters=filters)
                result_data["deleted_count"] = count

            elif operation == "upsert":
                if data is None:
                    return build_agent_error_response(
                        exception=ValueError("data is required for upsert"),
                        context={"operation": operation},
                        fallback_type="VALIDATION_ERROR",
                        fallback_action="Provide data to upsert"
                    )

                # Handle single vs bulk upsert
                if isinstance(data, list):
                    results = await storage.bulk_upsert(
                        table=table,
                        data=data,
                        conflict_fields=conflict_fields
                    )
                    result_data["results"] = results
                    result_data["count"] = len(results)
                else:
                    result = await storage.upsert_entity(
                        table=table,
                        data=data,
                        conflict_fields=conflict_fields
                    )
                    result_data["result"] = result
                    result_data["count"] = 1

            elif operation == "patch":
                if id is None or data is None:
                    return build_agent_error_response(
                        exception=ValueError("id and data are required for patch"),
                        context={"operation": operation},
                        fallback_type="VALIDATION_ERROR",
                        fallback_action="Provide id and data (fields to update)"
                    )

                if isinstance(data, list):
                    return build_agent_error_response(
                        exception=ValueError("patch does not support bulk operations"),
                        context={"operation": operation},
                        fallback_type="VALIDATION_ERROR",
                        fallback_action="Use single dict for patch, or use upsert for bulk"
                    )

                result = await storage.patch_entity(
                    table=table,
                    id=id,
                    updates=data
                )
                result_data["result"] = result
                result_data["count"] = 1

            logger.info(
                f"{operation.capitalize()} operation completed on {table}",
                extra=result_data
            )

            return build_success_response(result_data)

        except PermissionError:
            # Re-raise to avoid double-wrapping
            raise

        except Exception as e:
            logger.error(
                f"Write operation failed: {operation} on {table}",
                exc_info=True,
                extra={"operation": operation, "table": table}
            )
            return build_agent_error_response(
                exception=e,
                context={"operation": operation, "table": table},
                fallback_type="WRITE_ERROR",
                fallback_action=(
                    f"{operation.capitalize()} operation failed for {table}. "
                    f"Verify data format, filters, and constraints. "
                    f"Use dry_run=True to preview before executing."
                )
            )

    return StructuredTool.from_function(
        func=_write_data_impl,
        name="write_data",
        description=(
            "Unified write operations: insert, update, delete, upsert (idempotent), patch (partial update), "
            "with validation and dry-run modes. "
            "USE WHEN: Creating, updating, or deleting records. Supports bulk operations and safety checks. "
            "RETURNS: Operation results with affected records/counts. Validation and preview modes available. "
            "NOT FOR: Reading data (use read_data)."
        ),
        args_schema=WriteDataInput,
        coroutine=_write_data_impl,
    )
