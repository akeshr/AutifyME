"""Schema Engine - inspect_schema tool for database schema discovery.

Agent-centric tool for understanding database structure without fetching actual data.
Part of Universal Data Engine (Phase 1.1).
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
