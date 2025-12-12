"""Write Engine - Unified write_data tool for multi-operation atomic transactions.

Agent-centric tool for executing WriteIntent structures with dependencies and references.
Part of Universal Data Engine (Design implementation per UNIVERSAL_DATA_ENGINE_DESIGN.md).
"""

import logging
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import Field

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.tool_error_handler import (
    build_agent_error_response,
    build_success_response,
)
from autifyme_agents.schemas.write_intent import AssetUpload, Operation, WriteIntent
from autifyme_agents.tools.data_engine._executor import MultiOperationExecutor

logger = logging.getLogger(__name__)


class WriteDataInput(WriteIntent):
    """
    Tool input schema - extends WriteIntent with execution options.

    Inherits all WriteIntent fields (goal, reasoning, hitl_summary, etc.)
    and adds dry_run/validate_only modes for preview and validation.
    """

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
        - Operations requiring cross-table references (@parent.id)
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
                            {"name": "Size", "product_family_id": "@parent.id", "is_active": True},
                            {"name": "Color", "product_family_id": "@parent.id", "is_active": True}
                        ],
                        "dependencies": ["family"],
                        "returns": "axes_batch"
                    },
                    {
                        "action": "create",
                        "table": "variant_values",
                        "data": [
                            {"name": "500ml", "variant_axis_id": "@batch[0].id"},
                            {"name": "1L", "variant_axis_id": "@batch[0].id"},
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
                            {"product_family_id": "@parent.id", "sku": "JAR-PET-500ML-CLEAR", "name": "PET Food Jar 500ml Clear", "base_price": 30.0},
                            {"product_family_id": "@parent.id", "sku": "JAR-PET-500ML-AMBER", "name": "PET Food Jar 500ml Amber", "base_price": 32.0},
                            {"product_family_id": "@parent.id", "sku": "JAR-PET-1L-CLEAR", "name": "PET Food Jar 1L Clear", "base_price": 45.0},
                            {"product_family_id": "@parent.id", "sku": "JAR-PET-1L-AMBER", "name": "PET Food Jar 1L Amber", "base_price": 48.0}
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
                        "filters": {"product_family_id": "uuid-pet-123", "is_active": True, "id": {"in": ["uuid-500ml-1", "uuid-500ml-2"]}},
                        "updates": {"base_price": 35.0}
                    },
                    {
                        "action": "update",
                        "table": "products",
                        "filters": {"product_family_id": "uuid-pet-123", "is_active": True, "id": {"in": ["uuid-1l-1", "uuid-1l-2"]}},
                        "updates": {"base_price": 35.0}
                    },
                    {
                        "action": "update",
                        "table": "products",
                        "filters": {"product_family_id": "uuid-pet-123", "is_active": True, "id": {"in": ["uuid-2l-1", "uuid-2l-2"]}},
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
                        "filters": {"id": {"in": ["uuid-1", "uuid-2", "uuid-3"]}, "is_active": True},
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
            "PURPOSE: Execute atomic multi-table database transactions with HITL approval - ONLY way to create, update, or delete catalog data. All operations require user approval before execution.\n\n"
            "WRITEINTENT PATTERN (5 required fields):\n"
            "1. goal: What you're accomplishing (human-readable)\n"
            "2. reasoning: How you got here (duplicate checks, validation, research, foreign keys)\n"
            "3. hitl_summary: Business user approval message (<1500 chars, plain language, ends with 'Reply *approve* to proceed or *reject* to cancel.')\n"
            "4. operations: Array of database operations (create/update/delete/upsert) with dependencies\n"
            "5. impact: What changes (creates/updates/deletes counts, warnings, examples)\n\n"
            "USE WHEN:\n"
            "- Creating: Products, families, variants, pricing, images, BOM\n"
            "- Updating: Prices, statuses, descriptions, relationships\n"
            "- Deleting: Soft deletes (is_active=False), cleanup\n"
            "- Upserting: Idempotent create-or-update when you have conflict keys\n"
            "- Multi-table operations: Parent-child structures, junction tables\n"
            "- Asset uploads: Images from pending/ to permanent storage\n"
            "- Any database mutation: If it changes data, goes through write_data + HITL\n\n"
            "DON'T USE:\n"
            "- For reading (use read_data)\n"
            "- For schema inspection (use inspect_schema)\n"
            "- For analytics (use aggregate_data)\n"
            "- Without validation (ALWAYS inspect_schema + read_data BEFORE write_data)\n\n"
            "CRITICAL:\n"
            "- operations: Array of {action: 'create'/'update'/'delete'/'upsert', table: 'table_name', data: {...}, filters: {...}, updates: {...}, returns: 'ref_name', dependencies: ['parent_ref']}\n"
            "  * CREATE: {action: 'create', table: 'products', data: {sku: 'JAR-001', ...}, returns: 'product'}\n"
            "  * UPDATE: {action: 'update', table: 'products', filters: {id: 'uuid-123'}, updates: {base_price: 45.0}}\n"
            "  * DELETE: {action: 'delete', table: 'temp_records', filters: {id: 'uuid-123'}}\n"
            "  * UPSERT: {action: 'upsert', table: 'products', data: {...}, on_conflict: 'skip'|'update', conflict_fields: ['sku']}\n"
            "  * Batch: data can be array of dicts for multi-record creates\n"
            "- filters support equality / IN / numeric comparisons. Operator dicts supported: in, eq, neq, gt, gte, lt, lte (NO LIKE/ILIKE).\n"
            "  If you need fuzzy selection (e.g., SKU prefix), use read_data(search_patterns=...) first to get IDs, then update by id IN list.\n"
            "- Reference syntax: @name.field for dependencies\n"
            "  * Single: '@family.id' references family operation result\n"
            "  * Batch: '@axes_batch[0].id' references first result in batch\n"
            "  * dependencies: ['family'] ensures family created before products\n"
            "- Dependency resolution: Automatic topological sort, cyclic dependencies rejected\n"
            "- Atomic transaction: All-or-nothing, automatic rollback on any error (no partial commits)\n"
            "- HITL required: User must approve via hitl_summary (plain language for business users)\n"
            "- Validation: Always inspect_schema + read_data before write_data to verify structure and check duplicates\n\n"
            "OPTIONAL:\n"
            "- asset_uploads: [{storage_path: 'pending/thread_id/img.png', returns: 'asset'}] → reference '@asset.public_url' in operations\n"
            "- dry_run: Preview without executing (no HITL required)\n"
            "- validate_only: Check schemas without executing (no HITL required)\n\n"
            "EXAMPLES:\n"
            "# Multi-table create with dependencies\n"
            "write_data(\n"
            "    goal='Create PET Food Jars family with Size and Color variants (4 SKUs)',\n"
            "    reasoning='Duplicate check: 0 matches. Research (0.85): food-grade PET, Rs 30-50. inspect_schema: required fields verified.',\n"
            "    hitl_summary='Creating PET Food Jars family with 4 variants: JAR-PET-500ML-CLEAR (Rs 30), JAR-PET-500ML-AMBER (Rs 32), JAR-PET-1L-CLEAR (Rs 45), JAR-PET-1L-AMBER (Rs 48). Adds 1 family, 2 axes, 4 SKUs. Reply *approve* to proceed or *reject* to cancel.',\n"
            "    operations=[\n"
            "        {action: 'create', table: 'product_families', data: {name: 'PET Food Jars', sku_prefix: 'JAR-PET', base_price: 30.0}, returns: 'family'},\n"
            "        {action: 'create', table: 'variant_axes', data: [{name: 'Size', product_family_id: '@family.id'}, {name: 'Color', product_family_id: '@family.id'}], dependencies: ['family'], returns: 'axes'},\n"
            "        {action: 'create', table: 'variant_values', data: [{name: '500ml', variant_axis_id: '@axes[0].id'}, {name: '1L', variant_axis_id: '@axes[0].id'}, {name: 'Clear', variant_axis_id: '@axes[1].id'}, {name: 'Amber', variant_axis_id: '@axes[1].id'}], dependencies: ['axes']},\n"
            "        {action: 'create', table: 'products', data: [{product_family_id: '@family.id', sku: 'JAR-PET-500ML-CLEAR', name: 'PET Food Jar 500ml Clear', base_price: 30.0}, ...], dependencies: ['family']}\n"
            "    ],\n"
            "    impact={creates: {product_families: 1, variant_axes: 2, variant_values: 4, products: 4}, warnings: ['SKU count +4'], examples: ['JAR-PET-500ML-CLEAR']}\n"
            ")\n\n"
            "# Bulk update pattern (safe): query first, then update by IDs\n"
            "# 1) read_data(... search_patterns=...) to get product ids\n"
            "# 2) write_data update with filters={'id': ['id1','id2',...]}\n\n"
            "RETURNS: Always a structured dict with success flag.\n"
            "- success=True: {execution_time_ms, created_entities, updated_entities, deleted_entities, uploaded_assets?, summary, warnings?}\n"
            "  * created_entities maps table -> list of created rows (includes generated IDs)\n"
            "  * updated_entities/deleted_entities map table -> count\n"
            "- success=False: {error, error_type, goal, rollback_performed, Agent Action: ...}"
        ),
        args_schema=WriteDataInput,
        coroutine=_write_data_impl,
    )
