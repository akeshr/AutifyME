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
        description="Table name. Use inspect_schema to discover available tables."
    )
    filters: dict[str, Any] | None = Field(
        None,
        description=(
            "[EXACT MATCH] Case-sensitive exact value matching. "
            "Use when you have exact values (IDs, booleans, status codes). "
            "Examples: "
            "{'is_active': True}, "
            "{'category_id': 'cat-123'}, "
            "{'status': ['draft', 'published']} (IN operator for lists), "
            "{'name': {'$in': ['Exact Name 1', 'Exact Name 2']}} (requires EXACT match). "
            "CRITICAL: For name searches, use search_patterns instead (fuzzy match)."
        )
    )
    search_patterns: dict[str, str] | None = Field(
        None,
        description=(
            "[FUZZY MATCH] Case-insensitive ILIKE pattern matching. "
            "Use for searching text fields (names, descriptions, codes). "
            "Examples: "
            "{'name': '%search%'} (contains), "
            "{'code': 'PREFIX-%'} (starts with), "
            "{'name': '%term1%term2%'} (contains both). "
            "Use % as wildcard. RECOMMENDED for all name/text searches."
        )
    )
    columns: list[str] | None = Field(
        None,
        description="Columns to select (None = all columns). Example: ['id', 'name', 'price']"
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

        CRITICAL: filters vs search_patterns
        =====================================

        filters = EXACT MATCH (case-sensitive)
        - Use for: IDs, booleans, enums, status codes, foreign keys
        - Examples: {'is_active': True}, {'id': 'uuid-123'}
        - {'name': {'$in': ['Name 1', 'Name 2']}} → ONLY matches EXACT names
        - Returns 0 results if name doesn't match exactly (case, spacing, etc.)

        search_patterns = FUZZY MATCH (case-insensitive ILIKE)
        - Use for: Names, descriptions, SKUs, any text search
        - Examples: {'name': '%jar%'}, {'name': '%PET%bottle%'}
        - Matches partial strings, case-insensitive
        - RECOMMENDED for all name/text searches

        Common Mistake:
        ❌ filters={'name': {'$in': ['PET Jar', 'PET Bottles']}}  # Returns 0 if exact name doesn't exist
        ✅ search_patterns={'name': '%PET%'}  # Returns all products with 'PET' in name

        Returns:
            Query results with metadata (count, pagination info)

        Examples:
            # CRITICAL: Exact vs Fuzzy Match - Understanding the difference

            # ❌ WRONG: Using filters for name search (returns 0 if names don't match exactly)
            read_data(
                table="product_families",
                filters={"name": {"$in": ["PET Jar", "PET Bottles"]}},  # Requires EXACT match
                columns=["id", "name"]
            )
            # Returns: [] (empty) if actual names are "PET Food Jars" or "PET Water Bottles"

            # ✅ CORRECT: Using search_patterns for name search (fuzzy match)
            read_data(
                table="product_families",
                search_patterns={"name": "%PET%"},  # Matches any name containing "PET"
                columns=["id", "name"]
            )
            # Returns: ["PET Food Jars", "PET Water Bottles", "PET Containers", etc.]

            # ✅ CORRECT: Combining exact filters with fuzzy search
            read_data(
                table="products",
                filters={"is_active": True, "product_family_id": ["fam-1", "fam-2", "fam-3"]},
                search_patterns={"sku": "%500ML%"},
                columns=["id", "sku", "name", "base_price", "product_family_id"],
                relations=["product_families(name,sku_prefix)"],
                limit=50
            )
            # Returns: 500ml products from 3 families with family metadata

            # Complex: Duplicate check across name variations with fuzzy matching
            read_data(
                table="product_families",
                search_patterns={
                    "name": "%PET%bottle%",
                    "description": "%polyethylene%terephthalate%"
                },
                columns=["id", "name", "sku_prefix", "base_price", "created_at"]
            )
            # Returns: Potential duplicate families for deduplication workflow

            # Complex: Paginated product catalog with full relationship graph
            read_data(
                table="products",
                filters={"is_active": True},
                relations=[
                    "product_families(name,sku_prefix,material)",
                    "product_variant_values(variant_value(name,variant_axis(name)))",
                    "product_images(image_url,display_order)"
                ],
                columns=["id", "sku", "name", "base_price"],
                limit=25,
                offset=50
            )
            # Returns: Page 3 (items 51-75) with nested variant data and images

            # Complex: Junction table query for multi-axis product variants
            read_data(
                table="product_variant_values",
                filters={"product_id": "prod-uuid-123"},
                relations=[
                    "variant_value(name,variant_axis(name,product_family_id))"
                ]
            )
            # Returns: All variant dimensions for a product (e.g., Size=500ml, Color=Clear)

            # Complex: Analytics query for inventory planning
            read_data(
                table="products",
                filters={"is_active": True, "product_family_id": "fam-pet-bottles"},
                columns=["id", "sku", "base_price", "created_at"],
                relations=["product_families(name)"],
                count_only=False
            )
            # Returns: Full product list with metadata for SKU count analysis

            # Complex: Batch fetch products by ID for impact calculation
            read_data(
                table="products",
                ids=["uuid-1", "uuid-2", "uuid-3", "uuid-4", "uuid-5", "uuid-6"],
                columns=["id", "sku", "base_price", "is_active"],
                relations=["product_families(name)"]
            )
            # Returns: Specific products for bulk price update verification

            # Complex: Full product family with nested variant structure
            read_data(
                table="product_families",
                ids=["uuid-pet-jars"],
                relations=[
                    "products(*)",
                    "variant_axes(*, variant_values(*))"  # CORRECT nested syntax
                ]
            )
            # Returns: Product family with all products and complete variant axis hierarchy
            # CRITICAL: Use variant_axes(*, variant_values(*)) NOT variant_axes.variant_values(*)
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
            "PURPOSE: Universal database read tool - get all data you need. Fetch records, search, filter, join relationships, batch reads, pagination. CRITICAL before write_data to check duplicates and lookup foreign keys.\n\n"
            "CRITICAL DISTINCTION - filters vs search_patterns (most common source of errors):\n"
            "- filters: EXACT match, case-sensitive - use for IDs, booleans, enums\n"
            "  Example: {'id': 'uuid-123'}, {'is_active': True}, {'status': ['draft','published']}\n"
            "- search_patterns: FUZZY match, case-insensitive ILIKE - use for names, text, SKUs\n"
            "  Example: {'name': '%PET%'}, {'sku': 'JAR-%'}, {'name': '%PET%500ML%'}\n"
            "COMMON MISTAKE: filters={'name': 'PET Jars'} returns NOTHING unless EXACTLY 'PET Jars'\n"
            "  -> Use search_patterns={'name': '%PET%Jars%'} for fuzzy match instead!\n\n"
            "USE WHEN:\n"
            "- Duplicate check (CRITICAL before create): Does this product/SKU/entity exist?\n"
            "- Foreign key lookup: Get IDs for relationships (family_id, uom_id, price_list_id)\n"
            "- Context gathering: Current state (products in family, pricing patterns)\n"
            "- Verification: Confirm assumptions (family exists? product active?)\n"
            "- Batch fetch: Get multiple records by IDs\n"
            "- Relationship exploration: Load related data via joins (relations parameter)\n\n"
            "DON'T USE:\n"
            "- For schema/structure (use inspect_schema)\n"
            "- For analytics/GROUP BY (use aggregate_data)\n"
            "- For writes (use write_data)\n\n"
            "CRITICAL GOTCHAS:\n"
            "- relations syntax: Nested uses 'parent(*,child(*))' NOT 'parent.child(*)'\n"
            "- Use inspect_schema with details=['relationships'] to verify FK targets before using relations\n"
            "- ids parameter overrides filters/search_patterns (batch fetch mode)\n"
            "- count_only=True returns only count, no records (efficient for 'how many')\n\n"
            "EXAMPLES:\n"
            "# Duplicate check before create (CRITICAL workflow)\n"
            "read_data(table='products', search_patterns={'sku': '%HONEYCOMB%'}, columns=['id','sku'])\n"
            "Returns: Any products with 'HONEYCOMB' in SKU (case-insensitive)\n\n"
            "# Foreign key lookup for relationships\n"
            "read_data(table='product_families', search_patterns={'name': '%PET%Jars%'}, columns=['id','name'])\n"
            "Returns: Family IDs matching 'PET Jars' (fuzzy match)\n\n"
            "# Combined: exact filters + fuzzy search + relations\n"
            "read_data(table='products', filters={'is_active': True, 'product_family_id': ['fam-1','fam-2']}, search_patterns={'sku': '%500ML%'}, relations=['product_families(name)'], limit=50)\n"
            "Returns: Active 500ml products from 2 families with family names\n\n"
            "RETURNS: Array of records matching criteria, or {count: N} if count_only=True"
        ),
        args_schema=ReadDataInput,
        coroutine=_read_data_impl,
    )
