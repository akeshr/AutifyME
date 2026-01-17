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
        ..., description="Table name. Use inspect_schema to discover available tables."
    )
    filters: dict[str, Any] | None = Field(
        None,
        description=(
            "[EXACT MATCH] Equality / IN matching (no wildcards). "
            "Use when you have exact values (IDs, booleans, enums/status codes). "
            "Examples: "
            "{'is_active': True}, "
            "{'category_id': 'cat-123'}, "
            "{'status': ['draft', 'published']} (IN operator for lists). "
            "CRITICAL: Do NOT use '%' wildcards here. For text/name searching, use search_patterns."
        ),
    )
    search_patterns: dict[str, str | list[str]] | None = Field(
        None,
        description=(
            "[FUZZY MATCH] Case-insensitive ILIKE pattern matching. "
            "Use for searching TEXT columns (names, descriptions, codes). "
            "SYNTAX:\n"
            "- Single pattern (AND with other keys): {'name': '%keyword%'}\n"
            "- Multiple patterns (OR within same key): {'name': ['%term1%', '%term2%', '%term3%']}\n"
            "EXAMPLES:\n"
            "- {'name': '%keyword%'} - contains 'keyword' (single pattern)\n"
            "- {'name': ['%term1%', '%term2%']} - contains 'term1' OR 'term2' (1 query, not 2!)\n"
            "- {'name': '%word1%word2%'} - contains both word1 AND word2 (single pattern)\n"
            "Use % as wildcard. RECOMMENDED for all name/text searches. "
            "CRITICAL: Only works on TEXT columns, NOT on array columns (text[]). "
            "For array columns, use filters with exact array values or query differently. "
            "Use inspect_schema to check column types before querying."
        ),
    )
    columns: list[str] | None = Field(
        None, description="Columns to select (None = all columns). Example: ['id', 'name', 'price']"
    )
    relations: list[str] | None = Field(
        None,
        description=(
            "Related tables to include (PostgREST syntax).\n"
            "SYNTAX:\n"
            "- Basic: 'related_table(col1,col2)' or 'related_table(*)' for all columns\n"
            "- Nested: 'parent(*,child(*))' - parent with nested child (CORRECT)\n"
            "- WRONG: 'parent.child(*)' - dot notation does NOT work\n"
            "EXAMPLES:\n"
            "- ['categories(name,code)'] - single relation with specific columns\n"
            "- ['categories(*)', 'images(url,sort_order)'] - multiple relations\n"
            "- ['parent(*,children(*))'] - nested hierarchy (CORRECT)\n"
            "- ['junction(detail(name,parent(name)))'] - deep nesting through junction\n"
            "CRITICAL:\n"
            "- Nested relations: wrap child inside parent parentheses, NOT dot notation\n"
            "- Table names MUST match exactly (check singular vs plural with inspect_schema)\n"
            "- Use inspect_schema with details=['relationships'] to verify FK targets"
        ),
    )
    ids: list[str] | None = Field(
        None,
        description=(
            "Batch fetch by IDs. When provided, fetches only these IDs. "
            "Example: ['id1', 'id2', 'id3']"
        ),
    )
    limit: int | None = Field(
        50,
        description=(
            "Maximum rows to return (pagination). Default: 50 for safety/token efficiency. "
            "Increase only when needed; prefer columns=[...] to keep payload small."
        ),
        gt=0,
        le=1000,
    )
    offset: int | None = Field(
        None, description="Skip N rows (pagination). Use with limit for pages", ge=0
    )
    count_only: bool = Field(
        default=False, description="Return only count, not actual records. Useful for analytics"
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
        # Specialist - Domain-scoped access
        read_tool = create_read_data_tool(
            storage,
            tables=["entities", "parent_entities", "categories"]
        )

        # Analyst - Full read access
        read_tool = create_read_data_tool(storage)  # No restrictions
    """
    allowed_tables = tables

    async def _read_data_impl(
        table: str,
        filters: dict[str, Any] | None = None,
        search_patterns: dict[str, str | list[str]] | None = None,
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

        CRITICAL: filters vs search_patterns
        =====================================

        filters = EXACT MATCH (case-sensitive)
        - Use for: IDs, booleans, enums, status codes, foreign keys
        - Examples: {'is_active': True}, {'id': 'uuid-123'}
        - {'name': ['Name 1', 'Name 2']} → ONLY matches EXACT names
        - Returns 0 results if name doesn't match exactly (case, spacing, etc.)

        search_patterns = FUZZY MATCH (case-insensitive ILIKE)
        - Use for: Names, descriptions, codes, any text search
        - Examples: {'name': '%keyword%'}, {'name': '%term1%term2%'}
        - Matches partial strings, case-insensitive
        - RECOMMENDED for all name/text searches

        Common Mistake:
        filters={'name': ['Name A', 'Name B']}  # Returns 0 if exact name doesn't exist
        search_patterns={'name': '%keyword%'}  # Returns all records with 'keyword' in name

        Returns:
            Query results with metadata (count, pagination info)

        Examples:
            # CRITICAL: Exact vs Fuzzy Match - Understanding the difference

            # WRONG: Using filters for name search (returns 0 if names don't match exactly)
            read_data(
                table="parent_entities",
                filters={"name": ["Name A", "Name B"]},  # Requires EXACT match
                columns=["id", "name"]
            )
            # Returns: [] (empty) if actual names differ

            # CORRECT: Using search_patterns for name search (fuzzy match)
            read_data(
                table="parent_entities",
                search_patterns={"name": "%keyword%"},  # Matches any name containing keyword
                columns=["id", "name"]
            )
            # Returns: All matching records

            # CORRECT: Combining exact filters with fuzzy search
            read_data(
                table="entities",
                filters={"is_active": True, "parent_id": ["id-1", "id-2", "id-3"]},
                search_patterns={"code": "%pattern%"},
                columns=["id", "code", "name", "value", "parent_id"],
                relations=["parent_entities(name,code_prefix)"],
                limit=50
            )
            # Returns: Matching entities from 3 parents with parent metadata

            # Complex: Duplicate check across name variations with fuzzy matching
            read_data(
                table="parent_entities",
                search_patterns={
                    "name": "%keyword1%keyword2%",
                    "description": "%term1%term2%"
                },
                columns=["id", "name", "code_prefix", "value", "created_at"]
            )
            # Returns: Potential duplicates for deduplication workflow

            # Complex: Paginated data with full relationship graph
            read_data(
                table="entities",
                filters={"is_active": True},
                relations=[
                    "parent_entities(name,code_prefix,type)",
                    "entity_attributes(attribute(name,attribute_type(name)))",
                    "entity_assets(url,sort_order)"
                ],
                columns=["id", "code", "name", "value"],
                limit=25,
                offset=50
            )
            # Returns: Page 3 (items 51-75) with nested attribute data and assets

            # Complex: Junction table query for entity attributes
            read_data(
                table="entity_attributes",
                filters={"entity_id": "uuid-123"},
                relations=[
                    "attribute(name,attribute_type(name,parent_id))"
                ]
            )
            # Returns: All attribute dimensions for an entity

            # Complex: Analytics query
            read_data(
                table="entities",
                filters={"is_active": True, "parent_id": "parent-uuid"},
                columns=["id", "code", "value", "created_at"],
                relations=["parent_entities(name)"],
                count_only=False
            )
            # Returns: Full entity list with metadata for analysis

            # Complex: Batch fetch entities by ID for impact calculation
            read_data(
                table="entities",
                ids=["uuid-1", "uuid-2", "uuid-3", "uuid-4", "uuid-5", "uuid-6"],
                columns=["id", "code", "value", "is_active"],
                relations=["parent_entities(name)"]
            )
            # Returns: Specific entities for bulk update verification

            # Complex: Full parent with nested child structure
            read_data(
                table="parent_entities",
                ids=["uuid-parent"],
                relations=[
                    "entities(*)",
                    "attribute_types(*, attributes(*))"  # CORRECT nested syntax
                ]
            )
            # Returns: Parent with all children and complete attribute hierarchy
            # CRITICAL: Use parent(*, child(*)) NOT parent.child(*)
            )
        """
        try:
            # Access control: Verify table access
            if allowed_tables is not None and table not in allowed_tables:
                logger.warning(
                    f"Access denied to table: {table}",
                    extra={"requested": table, "allowed": allowed_tables},
                )
                return build_agent_error_response(
                    exception=PermissionError(f"Access denied to table: {table}"),
                    context={"table": table},
                    fallback_type="ACCESS_DENIED",
                    fallback_action=(
                        f"You don't have access to table '{table}'. "
                        f"Available tables: {allowed_tables}. "
                        f"Request access from system administrator if needed."
                    ),
                )

            logger.info(
                f"Reading data from {table}",
                extra={
                    "table": table,
                    "has_filters": filters is not None,
                    "has_search": search_patterns is not None,
                    "has_ids": ids is not None,
                    "count_only": count_only,
                    "limit": limit,
                },
            )

            # BATCH READ: Fetch by IDs
            if ids is not None:
                results = await storage.batch_read(table=table, ids=ids, relations=relations)

                logger.info(
                    f"Batch read returned {len(results)} record(s)",
                    extra={"table": table, "id_count": len(ids)},
                )

                return build_success_response(
                    {
                        "table": table,
                        "operation": "batch_read",
                        "results": results,
                        "count": len(results),
                        "requested_ids": len(ids),
                    }
                )

            # COUNT ONLY: Efficient counting
            if count_only:
                count = await storage.count_entities(table=table, filters=filters)

                logger.info(f"Count query returned {count}", extra={"table": table})

                return build_success_response(
                    {
                        "table": table,
                        "operation": "count",
                        "count": count,
                    }
                )

            # STANDARD QUERY: Filters, search, relations, pagination
            results = await storage.query_advanced(
                table=table,
                filters=filters,
                columns=columns,
                relations=relations,
                search_patterns=search_patterns,
                count_only=False,
                limit=limit,
            )

            # Apply offset if specified (query_advanced doesn't support offset directly)
            if offset is not None and offset > 0:
                results = results[offset:]

            logger.info(
                f"Query returned {len(results)} record(s)",
                extra={
                    "table": table,
                    "result_count": len(results),
                    "has_pagination": limit is not None or offset is not None,
                },
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
                    "has_more": len(results) == limit if limit else False,
                }

            return build_success_response(response_data)

        except PermissionError:
            # Re-raise to avoid double-wrapping
            raise

        except Exception as e:
            logger.error(
                f"Read operation failed for {table}",
                exc_info=True,
                extra={"table": table, "operation_type": "batch" if ids else "query"},
            )
            return build_agent_error_response(
                exception=e,
                context={"table": table},
                fallback_type="QUERY_ERROR",
                fallback_action=(
                    f"Query failed for {table}. "
                    f"Verify table name, filters, and search patterns. "
                    f"Check available tables with inspect_schema tool."
                ),
            )

    return StructuredTool.from_function(
        func=_read_data_impl,
        name="read_data",
        description=(
            "PURPOSE: Universal database read tool - fetch records, search text, apply exact filters, include relations, batch reads, pagination, and counts. Use this before write_data to (1) check duplicates and (2) look up foreign keys/IDs.\n\n"
            "CRITICAL DISTINCTION - filters vs search_patterns (most common source of errors):\n"
            "- filters: equality / IN matching (no wildcards) - use for IDs, booleans, enums/statuses\n"
            "  Example: {'id': 'uuid-123'}, {'is_active': True}, {'status': ['draft','published']}\n"
            "- search_patterns: wildcard patterns using % (case-insensitive ILIKE) - use for names, text, codes\n"
            "  * Single pattern (AND with other keys): {'name': '%keyword%'}\n"
            "  * Multiple patterns (OR within same key): {'name': ['%term1%', '%term2%', '%term3%']}\n"
            "  * EFFICIENCY: Use list for OR - 1 query instead of 15+ separate queries!\n"
            "RULE: If you're matching human text and you didn't include %, you probably meant search_patterns.\n\n"
            "USE WHEN:\n"
            "- Duplicate check (CRITICAL before create): Does this record/code/entity exist?\n"
            "- Foreign key lookup: Get IDs for relationships (parent_id, type_id, etc.)\n"
            "- Context gathering: Current state (records in parent, patterns)\n"
            "- Verification: Confirm assumptions (parent exists? record active?)\n"
            "- Batch fetch: Get multiple records by IDs\n"
            "- Relationship exploration: Load related data via joins (relations parameter)\n\n"
            "DON'T USE:\n"
            "- For schema/structure (use inspect_schema)\n"
            "- For analytics/GROUP BY (use aggregate_data)\n"
            "- For writes (use write_data)\n\n"
            "CRITICAL GOTCHAS:\n"
            "- search_patterns ONLY works on TEXT columns, NOT on array columns (text[])\n"
            "  * Columns like 'tags' are often arrays - check with inspect_schema first\n"
            "  * Using search_patterns on arrays causes: 'operator does not exist: text[] ~~* unknown'\n"
            "- relations syntax: Nested uses 'parent(*,child(*))' NOT 'parent.child(*)'\n"
            "- Use inspect_schema with details=['relationships'] to verify FK targets before using relations\n"
            "- ids parameter overrides filters/search_patterns (batch fetch mode)\n"
            "- count_only=True returns only count, no records (efficient for 'how many')\n"
            "- limit defaults to 50 for efficiency; increase only when needed\n"
            "- Use columns=['id',...] whenever possible to reduce payload\n\n"
            "EXAMPLES:\n"
            "# Duplicate check before create (CRITICAL workflow)\n"
            "read_data(table='entities', search_patterns={'code': '%KEYWORD%'}, columns=['id','code'])\n"
            "Returns: Any entities with 'KEYWORD' in code (case-insensitive)\n\n"
            "# EFFICIENT OR search (1 query instead of 15+ queries!)\n"
            "read_data(table='entities', search_patterns={'name': ['%term1%', '%term2%', '%term3%']}, columns=['id','name'])\n"
            "Returns: Entities with 'term1' OR 'term2' OR 'term3' in name - SINGLE query\n\n"
            "# Foreign key lookup for relationships\n"
            "read_data(table='parent_entities', search_patterns={'name': '%keyword%'}, columns=['id','name'])\n"
            "Returns: Parent IDs matching keyword (fuzzy match)\n\n"
            "# Combined: exact filters + fuzzy search + relations\n"
            "read_data(table='entities', filters={'is_active': True, 'parent_id': ['id-1','id-2']}, search_patterns={'code': '%pattern%'}, relations=['parent_entities(name)'], limit=50)\n"
            "Returns: Active entities from 2 parents with parent names\n\n"
            "ALSO CONSIDER:\n"
            "- inspect_schema: Need structure/columns/enums BEFORE querying? Use inspect_schema first\n"
            "- aggregate_data: Need GROUP BY, SUM, AVG, COUNT by category? Use aggregate_data\n"
            "- write_data: Ready to create/update? Use read_data first (duplicates + FKs), then write_data\n\n"
            "RETURNS: Always a structured dict with success flag.\n"
            "- success=True: {table, operation, results?, count, pagination?}\n"
            "  * operation='query'|'batch_read'|'count'\n"
            "  * results present for query/batch_read; count present for all\n"
            "- success=False: {error, error_type, table, Agent Action: ...}"
        ),
        args_schema=ReadDataInput,
        coroutine=_read_data_impl,
    )
