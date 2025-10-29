"""Schema query tools for dynamic schema-driven planning.

Allows specialists to query database schema at runtime for intelligent
operation planning and validation.
"""

import logging
from typing import Any

from langchain.tools import tool
from langchain_core.tools import ToolException

from autifyme_agents.schemas.registry import SchemaRegistry

logger = logging.getLogger(__name__)


# =============================================================================
# Schema Query Tool
# =============================================================================


@tool("get_product_schema")
def get_product_schema(
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
        Schema dictionary with:
        - version: Schema version identifier
        - domain: Domain name (e.g., 'product_catalog')
        - tables: Map of table_name -> table_schema
        - Each table includes: columns, relationships, indexes

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
            for table_name, table_data in schema_dict["tables"].items():
                if "business_rules" in table_data:
                    table_data["business_rules"] = []

        logger.info(
            f"Schema loaded successfully",
            extra={
                "version": schema.version,
                "tables_count": len(schema.tables)
            }
        )

        return schema_dict

    except FileNotFoundError as e:
        logger.error(
            f"Schema version not found: {version}",
            exc_info=True,
            extra={"version": version}
        )
        raise ToolException(
            f"Schema version '{version}' not found. Available versions: v1"
        ) from e

    except Exception as e:
        logger.error(
            "Failed to load product schema",
            exc_info=True,
            extra={"error_type": type(e).__name__, "error_msg": str(e)}
        )
        raise ToolException(f"Failed to load schema: {str(e)}") from e


@tool("get_table_schema")
def get_table_schema(
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
        Table schema dictionary with columns, relationships, and indexes

    Raises:
        ToolException: If table not found in schema

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

        return table_schema.model_dump()

    except ValueError as e:
        logger.error(
            f"Table not found: {table_name}",
            exc_info=True,
            extra={"table": table_name, "version": version}
        )
        raise ToolException(
            f"Table '{table_name}' not found in schema. "
            f"Available tables: {', '.join(SchemaRegistry.get_version(version).get_table_names())}"
        ) from e

    except Exception as e:
        logger.error(
            "Failed to load table schema",
            exc_info=True,
            extra={"error_type": type(e).__name__, "error_msg": str(e)}
        )
        raise ToolException(f"Failed to load table schema: {str(e)}") from e


@tool("list_available_tables")
def list_available_tables(version: str = "latest") -> dict[str, Any]:
    """
    List all available tables in the product catalog schema.

    Quick way to see what tables exist without retrieving full schema.

    Args:
        version: Schema version (default: 'latest')

    Returns:
        Dictionary with:
        - version: Schema version
        - domain: Domain name
        - tables: List of table names
        - count: Number of tables

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

        return result

    except Exception as e:
        logger.error(
            "Failed to list tables",
            exc_info=True,
            extra={"error_type": type(e).__name__, "error_msg": str(e)}
        )
        raise ToolException(f"Failed to list tables: {str(e)}") from e
