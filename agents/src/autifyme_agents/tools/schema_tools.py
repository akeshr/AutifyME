"""Schema query tools for dynamic schema-driven planning.

Allows specialists to query database schema at runtime for intelligent
operation planning and validation.
"""

import logging
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from autifyme_agents.core.tool_error_handler import (
    build_agent_error_response,
    build_success_response,
)
from autifyme_agents.schemas.registry import SchemaRegistry

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models (OpenAI requires additionalProperties: false)
# =============================================================================


class GetProductSchemaInput(BaseModel):
    """Input schema for get_product_schema tool."""

    model_config = {"extra": "forbid"}  # Generates additionalProperties: false

    version: str = Field(
        default="latest",
        description="Schema version to retrieve ('latest', 'v1', 'v2', etc.)"
    )
    include_business_rules: bool = Field(
        default=False,
        description="Include business rule metadata (default: False)"
    )


class GetTableSchemaInput(BaseModel):
    """Input schema for get_table_schema tool."""

    model_config = {"extra": "forbid"}

    table_name: str = Field(
        ...,
        description="Name of the table to query"
    )
    version: str = Field(
        default="latest",
        description="Schema version (default: 'latest')"
    )


class ListAvailableTablesInput(BaseModel):
    """Input schema for list_available_tables tool."""

    model_config = {"extra": "forbid"}

    version: str = Field(
        default="latest",
        description="Schema version (default: 'latest')"
    )


# =============================================================================
# Tool Implementation Functions
# =============================================================================


def _get_product_schema_impl(
    version: str = "latest",
    include_business_rules: bool = False,
) -> dict[str, Any]:
    """
    Retrieve product catalog schema for dynamic operation planning.

    Use this tool to understand:
    - Available tables and their columns
    - Data types and constraints
    - Relationships (foreign keys, cascades)
    - Business rules (if included)

    This enables schema-driven operation planning where you generate
    operations based on actual database structure rather than hard-coded
    knowledge.

    Args:
        version: Schema version to retrieve ('latest', 'v1', 'v2', etc.)
        include_business_rules: Include business rule metadata (default: False)

    Returns:
        Dict with schema or error:
        - On success: {"success": True, "version": str, "domain": str, "tables": {...}}
        - On error: {"success": False, "error": str, "error_type": str}

    Examples:
        # Get latest schema
        schema = get_product_schema()

        # Get specific version
        schema = get_product_schema(version="v1")

        # Include business rules
        schema = get_product_schema(include_business_rules=True)

    Example Response:
        {
            "version": "v1",
            "domain": "product_catalog",
            "tables": {
                "product_families": {
                    "name": "product_families",
                    "columns": {
                        "id": {"name": "id", "type": "uuid", "nullable": false},
                        "name": {"name": "name", "type": "varchar", "nullable": false},
                        ...
                    },
                    "relationships": [...],
                    "indexes": ["product_group_id", "sku_prefix"]
                },
                "variant_axes": {
                    "name": "variant_axes",
                    "columns": {...},
                    "relationships": [
                        {
                            "type": "parent",
                            "target_table": "product_families",
                            "foreign_key": "product_family_id",
                            "cascade_delete": true
                        }
                    ]
                },
                ...
            }
        }
    """
    try:
        logger.info(
            f"Loading product schema version: {version}",
            extra={"version": version, "include_business_rules": include_business_rules}
        )

        # Load schema from registry
        schema = SchemaRegistry.get_version(
            version=version,
            domain="product_catalog"
        )

        # Convert to dict
        schema_dict = schema.to_dict()

        # Optionally filter out business rules
        if not include_business_rules:
            for _table_name, table_data in schema_dict["tables"].items():
                if "business_rules" in table_data:
                    table_data["business_rules"] = []

        logger.info(
            "Schema loaded successfully",
            extra={
                "version": schema.version,
                "tables_count": len(schema.tables)
            }
        )

        return build_success_response(schema_dict)

    except FileNotFoundError as e:
        logger.error(
            f"Schema version not found: {version}",
            exc_info=True,
            extra={"version": version}
        )
        return build_agent_error_response(
            exception=e,
            context={},
            fallback_type="SCHEMA_ERROR",
            fallback_action=(
                f"Schema version '{version}' does not exist. "
                f"Use version='latest' or 'v1'. If persistent, contact system administrator."
            ),
        )

    except Exception as e:
        logger.error(
            "Failed to load product schema",
            exc_info=True,
            extra={"error_type": type(e).__name__, "error_msg": str(e)}
        )
        return build_agent_error_response(
            exception=e,
            context={},
            fallback_type="SCHEMA_ERROR",
            fallback_action=(
                "Schema registry issue. Try version='latest'. "
                "If persistent, contact system administrator."
            ),
        )


def _get_table_schema_impl(
    table_name: str,
    version: str = "latest",
) -> dict[str, Any]:
    """
    Retrieve schema for a specific table.

    Use this for focused queries when you need details about a single table
    rather than the entire schema.

    Args:
        table_name: Name of the table to query
        version: Schema version (default: 'latest')

    Returns:
        Dict with table schema or error:
        - On success: {"success": True, "name": str, "columns": {...}, "relationships": [...], ...}
        - On error: {"success": False, "error": str, "error_type": str, "table_name": str}

    Examples:
        # Get product_families table schema
        table = get_table_schema("product_families")

        # Get variant_axes table schema
        table = get_table_schema("variant_axes")
    """
    try:
        logger.info(
            f"Loading table schema: {table_name}",
            extra={"table": table_name, "version": version}
        )

        # Load schema
        schema = SchemaRegistry.get_version(
            version=version,
            domain="product_catalog"
        )

        # Get table
        table_schema = schema.get_table(table_name)

        logger.info(
            f"Table schema loaded: {table_name}",
            extra={
                "columns_count": len(table_schema.columns),
                "relationships_count": len(table_schema.relationships)
            }
        )

        return build_success_response(table_schema.model_dump())

    except ValueError as e:
        logger.error(
            f"Table not found: {table_name}",
            exc_info=True,
            extra={"table": table_name, "version": version}
        )
        return build_agent_error_response(
            exception=e,
            context={"table_name": table_name},
            fallback_type="SCHEMA_ERROR",
            fallback_action=(
                f"Table '{table_name}' does not exist in schema. "
                f"Use list_available_tables to see all tables. Check table name spelling and try again."
            ),
        )

    except Exception as e:
        logger.error(
            "Failed to load table schema",
            exc_info=True,
            extra={"error_type": type(e).__name__, "error_msg": str(e)}
        )
        return build_agent_error_response(
            exception=e,
            context={"table_name": table_name},
            fallback_type="SCHEMA_ERROR",
            fallback_action=(
                "Schema registry issue. Try get_product_schema instead "
                "to get all tables, or contact system administrator."
            ),
        )


def _list_available_tables_impl(version: str = "latest") -> dict[str, Any]:
    """
    List all available tables in the product catalog schema.

    Quick way to see what tables exist without retrieving full schema.

    Args:
        version: Schema version (default: 'latest')

    Returns:
        Dict with table list or error:
        - On success: {"success": True, "version": str, "domain": str, "tables": [...], "count": int}
        - On error: {"success": False, "error": str, "error_type": str}

    Example Response:
        {
            "version": "v1",
            "domain": "product_catalog",
            "tables": [
                "product_families",
                "variant_axes",
                "variant_values",
                "products",
                "product_variant_values",
                "product_family_industries",
                "customer_segments",
                "product_images",
                "marketing_content"
            ],
            "count": 9
        }
    """
    try:
        logger.info(f"Listing available tables for version: {version}")

        schema = SchemaRegistry.get_version(
            version=version,
            domain="product_catalog"
        )

        table_names = schema.get_table_names()

        result = {
            "version": schema.version,
            "domain": schema.domain,
            "tables": sorted(table_names),
            "count": len(table_names)
        }

        logger.info(
            f"Listed {len(table_names)} tables",
            extra={"version": version, "count": len(table_names)}
        )

        return build_success_response(result)

    except Exception as e:
        logger.error(
            "Failed to list tables",
            exc_info=True,
            extra={"error_type": type(e).__name__, "error_msg": str(e)}
        )
        return build_agent_error_response(
            exception=e,
            context={},
            fallback_type="SCHEMA_ERROR",
            fallback_action=(
                "Schema registry issue. Try get_product_schema to access tables directly. "
                "If persistent, contact system administrator."
            ),
        )


# =============================================================================
# Tool Instances (OpenAI-compatible with additionalProperties: false)
# =============================================================================

get_product_schema = StructuredTool.from_function(
    func=_get_product_schema_impl,
    name="get_product_schema",
    description=(
        "Retrieve complete product catalog database schema (structure, not data). "
        "WHEN TO USE: Before complex CREATE/UPDATE/DELETE operations when you need to verify table structure, relationships, or constraints. "
        "NOT NEEDED: For routine operations - most standard tables are known (product_families, products, variant_axes, variant_values). "
        "Returns: Tables with columns (types, nullability), foreign key relationships, cascade delete rules, indexes. "
        "CRITICAL: This returns SCHEMA (database structure), NOT actual product data. Use query_database to fetch product data."
    ),
    args_schema=GetProductSchemaInput,
)

get_table_schema = StructuredTool.from_function(
    func=_get_table_schema_impl,
    name="get_table_schema",
    description=(
        "Retrieve schema for a specific table (focused query for single table structure). "
        "WHEN TO USE: When you need column details, types, or relationships for ONE table without loading entire schema. "
        "More efficient than get_product_schema when you know which table you need. "
        "CRITICAL: Returns table STRUCTURE only - use query_database for actual data from that table."
    ),
    args_schema=GetTableSchemaInput,
)

list_available_tables = StructuredTool.from_function(
    func=_list_available_tables_impl,
    name="list_available_tables",
    description=(
        "List all table names in product catalog schema (lightweight discovery). "
        "WHEN TO USE: When you need to see what tables exist without loading full schema or specific table details. "
        "Returns: Just table names - use get_table_schema or get_product_schema for structure details."
    ),
    args_schema=ListAvailableTablesInput,
)
