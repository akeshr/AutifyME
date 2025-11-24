"""Write Engine - Unified write_data tool for multi-operation atomic transactions.

Agent-centric tool for executing WriteIntent structures with dependencies and references.
Part of Universal Data Engine (Design implementation per UNIVERSAL_DATA_ENGINE_DESIGN.md).
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
from autifyme_agents.schemas.write_intent import Operation, WriteIntent
from autifyme_agents.tools.operation_executor import MultiOperationExecutor

logger = logging.getLogger(__name__)


class WriteDataInput(BaseModel):
    """
    Input schema for write_data tool - WriteIntent structure.

    As per UNIVERSAL_DATA_ENGINE_DESIGN.md (lines 722-745).
    Streamlined multi-operation write intent with auto-dependency resolution.
    """

    model_config = {"extra": "forbid"}

    goal: str = Field(
        ...,
        description=(
            "Human-readable goal of this write intent.\n"
            "Example: 'Create PET Bottles product family with Size and Color variants'"
        ),
    )

    reasoning: str = Field(
        ...,
        description=(
            "Reasoning and context for this operation.\n"
            "Includes: classification rationale, duplicate check results, "
            "research findings, warnings, assumptions."
        ),
    )

    operations: list[dict[str, Any]] = Field(
        ...,
        description=(
            "List of operations to execute atomically.\n"
            "Each operation has:\n"
            "- action: 'create'|'update'|'delete'|'upsert'\n"
            "- table: table name\n"
            "- data: dict or list of dicts (for create/upsert)\n"
            "- filters: dict (for update/delete)\n"
            "- updates: dict (for update)\n"
            "- dependencies: list of operation names (optional)\n"
            "- returns: name for this operation's result (optional)\n"
            "- on_conflict: 'error'|'skip'|'update' (optional)\n"
            "- conflict_fields: list of fields (for upsert, optional)\n"
            "- cascade: bool (for delete, optional)\n"
            "- soft_delete: bool (for delete, default True)\n\n"
            "Engine automatically orders by dependencies (topological sort).\n"
            "All operations execute in single transaction with automatic rollback.\n\n"
            "Reference syntax: Use @name.field to reference previous operations.\n"
            "Example: 'family_id': '@family.id' references operation with returns='family'"
        ),
    )

    impact: dict[str, Any] = Field(
        ...,
        description=(
            "Simplified impact analysis.\n"
            "Format: {\n"
            "  'creates': {'table_name': count, ...},\n"
            "  'updates': {'table_name': count, ...},\n"
            "  'deletes': {'table_name': count, ...},\n"
            "  'warnings': ['warning1', 'warning2'],\n"
            "  'examples': ['example SKU 1', 'example SKU 2']\n"
            "}"
        ),
    )

    dry_run: bool = Field(
        default=False,
        description=(
            "Preview mode: validate and show impact without executing. "
            "Returns validation results and affected counts."
        ),
    )

    validate_only: bool = Field(
        default=False,
        description=(
            "Validation mode: check schema and constraints without executing. "
            "Returns validation errors and warnings."
        ),
    )


def create_write_data_tool(
    storage: StorageInterface,
    tables: list[str] | None = None,
) -> StructuredTool:
    """
    Create unified write_data tool for multi-operation write intents.

    Universal Data Engine - Design implementation (UNIVERSAL_DATA_ENGINE_DESIGN.md).
    Executes WriteIntent structures with atomic multi-table operations.

    Capabilities:
    - Multi-table atomic transactions
    - Dependency resolution (topological sorting)
    - Reference resolution (@name.field syntax)
    - Validation and dry-run modes
    - Automatic rollback on errors

    Args:
        storage: Storage interface for database operations
        tables: Allowed tables (None = all tables accessible)

    Returns:
        StructuredTool configured for multi-operation write intents

    Examples:
        # Cataloging Specialist - Full CRUD on product domain
        write_tool = create_write_data_tool(
            storage,
            tables=["products", "product_families", "categories", "variant_axes", "variant_values"]
        )

        # Campaign Specialist - Campaign tables only
        write_tool = create_write_data_tool(
            storage,
            tables=["campaigns", "ad_copies"]
        )

        # Project Manager - All tables
        write_tool = create_write_data_tool(storage)  # No restrictions
    """
    allowed_tables = tables

    async def _write_data_impl(
        goal: str,
        reasoning: str,
        operations: list[dict[str, Any]],
        impact: dict[str, Any],
        dry_run: bool = False,
        validate_only: bool = False,
    ) -> dict[str, Any]:
        """
        Execute multi-operation write intent atomically.

        USE WHEN:
        - Creating multi-table entities (product family + variants)
        - Atomic operations with dependencies (create family, then products)
        - Operations requiring cross-table references (@family.id)
        - Complex database mutations with ACID guarantees

        NOT FOR:
        - Reading data (use read_data)
        - Schema inspection (use inspect_schema)

        Features:
        - Atomic transactions (all-or-nothing)
        - Auto-dependency resolution (topological sort)
        - Reference resolution (@name.field)
        - Validation and dry-run modes

        Returns:
            Execution result with created/updated/deleted entities

        Examples:
            # Multi-table create with dependencies
            write_data(
                goal="Create PET Bottles product family with Size variant",
                reasoning="No duplicates found. Creating family with variant axis.",
                operations=[
                    {
                        "action": "create",
                        "table": "product_families",
                        "data": {"name": "PET Bottles", "sku_prefix": "PET-BTL"},
                        "returns": "family"
                    },
                    {
                        "action": "create",
                        "table": "variant_axes",
                        "data": {"axis_name": "Size", "family_id": "@family.id"},
                        "dependencies": ["family"]
                    }
                ],
                impact={"creates": {"product_families": 1, "variant_axes": 1}}
            )

            # Dry-run preview
            write_data(
                goal="...",
                reasoning="...",
                operations=[...],
                impact={...},
                dry_run=True
            )

            # Validation only
            write_data(
                goal="...",
                reasoning="...",
                operations=[...],
                impact={...},
                validate_only=True
            )
        """
        try:
            # Parse WriteIntent from dict inputs
            write_intent = WriteIntent(
                goal=goal,
                reasoning=reasoning,
                operations=[Operation(**op) for op in operations],
                impact=impact
            )

            # Access control: Verify all tables in operations
            if allowed_tables is not None:
                for op in write_intent.operations:
                    if op.table not in allowed_tables:
                        logger.warning(
                            f"Access denied to table: {op.table}",
                            extra={"requested": op.table, "allowed": allowed_tables}
                        )
                        return build_agent_error_response(
                            exception=PermissionError(f"Access denied to table: {op.table}"),
                            context={"table": op.table, "goal": goal},
                            fallback_type="ACCESS_DENIED",
                            fallback_action=(
                                f"You don't have access to table '{op.table}'. "
                                f"Available tables: {allowed_tables}. "
                                f"Request access from system administrator if needed."
                            )
                        )

            # Execute with MultiOperationExecutor
            executor = MultiOperationExecutor(storage)
            result = await executor.execute_intent(
                intent=write_intent,
                dry_run=dry_run,
                validate_only=validate_only
            )

            # Return result
            if result.success:
                return build_success_response(result.to_dict())
            else:
                return build_agent_error_response(
                    exception=Exception(result.error_message or "Unknown error"),
                    context={
                        "goal": goal,
                        "execution_time_ms": result.execution_time_ms,
                        "rollback_performed": result.rollback_performed,
                    },
                    fallback_type="EXECUTION_ERROR",
                    fallback_action=result.error_message or "Review operation structure and retry."
                )

        except Exception as e:
            logger.error(
                f"WriteIntent execution error: {goal}",
                exc_info=True,
                extra={"goal": goal}
            )
            return build_agent_error_response(
                exception=e,
                context={"goal": goal},
                fallback_type="WRITE_ERROR",
                fallback_action=(
                    f"WriteIntent execution failed: {str(e)}. "
                    f"Review operations, dependencies, and data format."
                )
            )

    return StructuredTool.from_function(
        func=_write_data_impl,
        name="write_data",
        description=(
            "Execute multi-operation write intent with atomic transactions and dependency resolution. "
            "USE WHEN: Creating multi-table entities, operations with dependencies, cross-table references. "
            "SUPPORTS: Atomic ACID transactions, topological dependency sorting, @name.field references, "
            "validation and dry-run modes. "
            "RETURNS: Execution result with created/updated/deleted entities, or errors with rollback. "
            "NOT FOR: Reading data (use read_data) or schema inspection (use inspect_schema)."
        ),
        args_schema=WriteDataInput,
        coroutine=_write_data_impl,
    )
