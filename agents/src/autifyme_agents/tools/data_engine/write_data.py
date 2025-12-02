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
from autifyme_agents.schemas.write_intent import AssetUpload, Operation, WriteIntent
from autifyme_agents.tools.data_engine._executor import MultiOperationExecutor

logger = logging.getLogger(__name__)


class WriteDataInput(BaseModel):
    """
    Input schema for write_data tool - WriteIntent structure.

    As per UNIVERSAL_DATA_ENGINE_DESIGN.md (lines 722-745).
    Streamlined multi-operation write intent with auto-dependency resolution.

    Uses nested Pydantic models (Operation, AssetUpload) so specialists see
    the exact schema with all required/optional fields and validation.
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

    hitl_summary: str = Field(
        ...,
        description=(
            "REQUIRED: Human-readable approval summary for HITL (<1500 chars).\n"
            "Write for the BUSINESS USER who will approve/reject.\n\n"
            "MUST include:\n"
            "- What will be created/updated (plain language)\n"
            "- Key impacts (counts, SKUs, prices)\n"
            "- Any warnings or assumptions\n"
            "- End with: 'Reply *approve* to proceed or *reject* to cancel'\n\n"
            "Example:\n"
            "'Creating PET Jars family with 2 size variants.\n\n"
            "Products: JAR-PET-500ML (Rs 30), JAR-PET-1L (Rs 50)\n"
            "Images: 2 product photos attached\n\n"
            "This will add 1 product family and 2 new SKUs.\n\n"
            "Reply *approve* to proceed or *reject* to cancel.'"
        ),
    )

    asset_uploads: list[AssetUpload] = Field(
        default_factory=list,
        description=(
            "Files to persist BEFORE database operations (atomically).\n"
            "PREFERRED: Use storage_path from image_studio/download_media outputs.\n"
            "Example: asset_uploads=[AssetUpload(storage_path='pending/.../img.png', returns='hero')]\n"
            "Reference in operations: '@hero.public_url', '@hero.size_bytes'"
        ),
    )

    operations: list[Operation] = Field(
        ...,
        description=(
            "List of operations to execute atomically.\n"
            "Engine automatically orders by dependencies (topological sort).\n"
            "All operations execute in single transaction with automatic rollback.\n"
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
            "  'asset_uploads': count,\n"
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
        hitl_summary: str,
        operations: list[Operation],
        impact: dict[str, Any],
        asset_uploads: list[AssetUpload] | None = None,
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
            # Complex: Create product family with multi-axis variants and products
            write_data(
                goal="Create PET Food Jars family with Size and Color variants (6 SKUs)",
                reasoning="Duplicate check: 0 matches. Web research (confidence 0.85): food-grade PET, transparent/amber common. Creating 2 axes (Size, Color), 4 variant values (500ml, 1L, Clear, Amber), 4 product combinations.",
                hitl_summary="Creating PET Food Jars family with 4 product variants.\n\nProducts:\n- JAR-PET-500ML-CLEAR (Rs 30)\n- JAR-PET-500ML-AMBER (Rs 32)\n- JAR-PET-1L-CLEAR (Rs 45)\n- JAR-PET-1L-AMBER (Rs 48)\n\nThis will add 1 product family, 2 variant axes, and 4 new SKUs to your catalog.\n\nReply *approve* to proceed or *reject* to cancel.",
                operations=[
                    {
                        "action": "create",
                        "table": "product_families",
                        "data": {
                            "name": "PET Food Jars",
                            "sku_prefix": "JAR-PET",
                            "base_price": 30.0,
                            "material": "Polyethylene Terephthalate (PET)",
                            "is_active": True
                        },
                        "returns": "family"
                    },
                    {
                        "action": "create",
                        "table": "variant_axes",
                        "data": [
                            {"name": "Size", "product_family_id": "@family.id", "is_active": True},
                            {"name": "Color", "product_family_id": "@family.id", "is_active": True}
                        ],
                        "dependencies": ["family"],
                        "returns": "axes_batch"
                    },
                    {
                        "action": "create",
                        "table": "variant_values",
                        "data": [
                            {"name": "500ml", "variant_axis_id": "@axes_batch[0].id"},
                            {"name": "1L", "variant_axis_id": "@axes_batch[0].id"},
                            {"name": "Clear", "variant_axis_id": "@axes_batch[1].id"},
                            {"name": "Amber", "variant_axis_id": "@axes_batch[1].id"}
                        ],
                        "dependencies": ["axes_batch"],
                        "returns": "values_batch"
                    },
                    {
                        "action": "create",
                        "table": "products",
                        "data": [
                            {"product_family_id": "@family.id", "sku": "JAR-PET-500ML-CLEAR", "name": "PET Food Jar 500ml Clear", "base_price": 30.0},
                            {"product_family_id": "@family.id", "sku": "JAR-PET-500ML-AMBER", "name": "PET Food Jar 500ml Amber", "base_price": 32.0},
                            {"product_family_id": "@family.id", "sku": "JAR-PET-1L-CLEAR", "name": "PET Food Jar 1L Clear", "base_price": 45.0},
                            {"product_family_id": "@family.id", "sku": "JAR-PET-1L-AMBER", "name": "PET Food Jar 1L Amber", "base_price": 48.0}
                        ],
                        "dependencies": ["family"]
                    }
                ],
                impact={
                    "creates": {"product_families": 1, "variant_axes": 2, "variant_values": 4, "products": 4},
                    "warnings": ["SKU count +4 (current: 45 → new: 49)", "Amber variants +6% price premium"],
                    "examples": ["JAR-PET-500ML-CLEAR", "JAR-PET-1L-AMBER"]
                }
            )

            # Complex: Tiered bulk price update with conditional logic
            write_data(
                goal="Update PET Bottles pricing with size-based tiers (Rs 35 for small/medium, Rs 50 for large)",
                reasoning="User requests tiered pricing. Query shows 6 active products (2x 500ml, 2x 1L, 2x 2L). Current avg Rs 28.50. New tiered pricing reflects volume premium. Three separate operations for atomic consistency.",
                operations=[
                    {
                        "action": "update",
                        "table": "products",
                        "filters": {"product_family_id": "uuid-pet-123", "is_active": True, "sku": {"$like": "%-500ML%"}},
                        "updates": {"base_price": 35.0}
                    },
                    {
                        "action": "update",
                        "table": "products",
                        "filters": {"product_family_id": "uuid-pet-123", "is_active": True, "sku": {"$like": "%-1L%"}},
                        "updates": {"base_price": 35.0}
                    },
                    {
                        "action": "update",
                        "table": "products",
                        "filters": {"product_family_id": "uuid-pet-123", "is_active": True, "sku": {"$like": "%-2L%"}},
                        "updates": {"base_price": 50.0}
                    }
                ],
                impact={
                    "updates": {"products": 6},
                    "warnings": ["CRITICAL: 6 products affected", "2L products: +56% increase", "Avg price: Rs 28.50 → Rs 40.00 (+40%)"],
                    "examples": ["BOTTLE-PET-500ML: Rs 25→35 (+40%)", "BOTTLE-PET-2L: Rs 32→50 (+56%)"]
                }
            )

            # Complex: Soft delete with junction table cleanup
            write_data(
                goal="Remove 250ml size from PET Bottles (discontinued) with junction cleanup",
                reasoning="250ml discontinued per business decision. Found 3 products via product_variant_values junction. Soft deleting products, junction records, and variant value to preserve order history. No hard deletes.",
                operations=[
                    {
                        "action": "update",
                        "table": "products",
                        "filters": {"id": {"$in": ["uuid-1", "uuid-2", "uuid-3"]}, "is_active": True},
                        "updates": {"is_active": False, "discontinued_at": "2025-01-24T00:00:00Z"}
                    },
                    {
                        "action": "update",
                        "table": "product_variant_values",
                        "filters": {"variant_value_id": "uuid-250ml-val", "is_active": True},
                        "updates": {"is_active": False}
                    },
                    {
                        "action": "update",
                        "table": "variant_values",
                        "filters": {"id": "uuid-250ml-val"},
                        "updates": {"is_active": False}
                    }
                ],
                impact={
                    "updates": {"products": 3, "product_variant_values": 3, "variant_values": 1},
                    "warnings": ["CRITICAL: 3 products discontinued", "Soft delete preserves order history", "SKU count -3 (45 → 42)"],
                    "examples": ["BOTTLE-PET-250ML-CLEAR", "BOTTLE-PET-250ML-AMBER"]
                }
            )

            # Dry-run preview mode (validation without execution)
            write_data(goal="...", reasoning="...", operations=[...], impact={...}, dry_run=True)

            # Validation-only mode (schema checks without execution)
            write_data(goal="...", reasoning="...", operations=[...], impact={...}, validate_only=True)
        """
        try:
            # Build WriteIntent from typed inputs (already validated by Pydantic)
            write_intent = WriteIntent(
                goal=goal,
                reasoning=reasoning,
                hitl_summary=hitl_summary,
                asset_uploads=asset_uploads or [],
                operations=operations,
                impact=impact,
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
            "Execute atomic multi-table transactions with dependency resolution and cross-table references.\n\n"
            "REQUIRED FIELDS:\n"
            "- goal: Human-readable intent ('Create PET Bottles family with Size variants')\n"
            "- reasoning: Investigation results, duplicate checks, research findings, assumptions\n"
            "- hitl_summary: Business user approval message (<1500 chars) ending with 'Reply *approve* to proceed or *reject* to cancel'\n"
            "- operations: List of {action, table, data, returns?, dependencies?, filters?, updates?}\n"
            "- impact: {creates: {table: count}, updates: {table: count}, deletes: {table: count}, warnings: [], examples: []}\n\n"
            "REFERENCE SYNTAX (@name.field):\n"
            "- Single result: '@family.id' references operation with returns='family'\n"
            "- Batch result: '@axes_batch[0].id' references first item from batch operation\n"
            "- Engine auto-resolves dependencies via topological sort\n\n"
            "SCENARIOS:\n"
            "- Create product family with variants: operations=[{create product_families, returns='family'}, {create variant_axes with '@family.id', returns='axes'}, {create products with '@family.id'}]\n"
            "- Tiered bulk price update: Multiple update operations with different filters for size-based pricing\n"
            "- Soft delete with cleanup: Update products is_active=False, then update junction table, then variant_values\n"
            "- Asset upload + DB: asset_uploads=[{storage_path='pending/...', returns='hero', caption='...'}] then '@hero.public_url' in operations\n\n"
            "MODES:\n"
            "- dry_run=True: Validate and show impact without executing\n"
            "- validate_only=True: Schema/constraint checks only\n\n"
            "RETURNS: {success, operations_executed, results_by_name, execution_time_ms, rollback_performed?}\n\n"
            "NOT FOR: Reading data (use read_data) or schema discovery (use inspect_schema)."
        ),
        args_schema=WriteDataInput,
        coroutine=_write_data_impl,
    )
