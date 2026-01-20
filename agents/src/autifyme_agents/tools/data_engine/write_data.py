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
        # Specialist - Domain-scoped CRUD
        write_tool = create_write_data_tool(
            storage,
            tables=["entities", "parent_entities", "categories", "attribute_types", "attributes"]
        )

        # Specialist - Alternate domain
        write_tool = create_write_data_tool(
            storage,
            tables=["records", "metadata"]
        )

        # Manager - All tables
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
        - Creating multi-table entities (parent + children)
        - Atomic operations with dependencies (create parent, then children)
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
            # Complex: Create parent entity with multi-axis attributes and children
            write_data(
                goal="Create parent entity with Axis A and Axis B attributes (6 children)",
                reasoning="Duplicate check: 0 matches. Research complete. Creating 2 axes, 4 attribute values, 4 child combinations.",
                hitl_summary="Creating parent entity with 4 child entities.\n\nEntities:\n- CODE-A1-B1 (value 30)\n- CODE-A1-B2 (value 32)\n- CODE-A2-B1 (value 45)\n- CODE-A2-B2 (value 48)\n\nThis will add 1 parent, 2 attribute axes, and 4 new children.\n\nReply *approve* to proceed or *reject* to cancel.",
                operations=[
                    {
                        "action": "create",
                        "table": "parent_entities",
                        "data": {
                            "name": "Parent Entity A",
                            "code_prefix": "CODE-A",
                            "base_value": 30.0,
                            "type": "Type A",
                            "is_active": True
                        },
                        "returns": "parent"
                    },
                    {
                        "action": "create",
                        "table": "attribute_types",
                        "data": [
                            {"name": "Axis A", "parent_id": "@parent.id", "is_active": True},
                            {"name": "Axis B", "parent_id": "@parent.id", "is_active": True}
                        ],
                        "dependencies": ["parent"],
                        "returns": "axes_batch"
                    },
                    {
                        "action": "create",
                        "table": "attributes",
                        "data": [
                            {"name": "Value A1", "type_id": "@batch[0].id"},
                            {"name": "Value A2", "type_id": "@batch[0].id"},
                            {"name": "Value B1", "type_id": "@axes_batch[1].id"},
                            {"name": "Value B2", "type_id": "@axes_batch[1].id"}
                        ],
                        "dependencies": ["axes_batch"],
                        "returns": "values_batch"
                    },
                    {
                        "action": "create",
                        "table": "entities",
                        "data": [
                            {"parent_id": "@parent.id", "code": "CODE-A1-B1", "name": "Entity A1 B1", "value": 30.0},
                            {"parent_id": "@parent.id", "code": "CODE-A1-B2", "name": "Entity A1 B2", "value": 32.0},
                            {"parent_id": "@parent.id", "code": "CODE-A2-B1", "name": "Entity A2 B1", "value": 45.0},
                            {"parent_id": "@parent.id", "code": "CODE-A2-B2", "name": "Entity A2 B2", "value": 48.0}
                        ],
                        "dependencies": ["parent"]
                    }
                ],
                impact={
                    "creates": {"parent_entities": 1, "attribute_types": 2, "attributes": 4, "entities": 4},
                    "warnings": ["Entity count +4 (current: 45 - new: 49)", "B2 variants +6% value premium"],
                    "examples": ["CODE-A1-B1", "CODE-A2-B2"]
                }
            )

            # Complex: Tiered bulk value update with conditional logic
            write_data(
                goal="Update entities with tier-based values (35 for tier 1, 50 for tier 2)",
                reasoning="User requests tiered values. Query shows 6 active entities. Three separate operations for atomic consistency.",
                operations=[
                    {
                        "action": "update",
                        "table": "entities",
                        "filters": {"parent_id": "uuid-parent", "is_active": True, "id": {"in": ["uuid-1", "uuid-2"]}},
                        "updates": {"value": 35.0}
                    },
                    {
                        "action": "update",
                        "table": "entities",
                        "filters": {"parent_id": "uuid-parent", "is_active": True, "id": {"in": ["uuid-3", "uuid-4"]}},
                        "updates": {"value": 35.0}
                    },
                    {
                        "action": "update",
                        "table": "entities",
                        "filters": {"parent_id": "uuid-parent", "is_active": True, "id": {"in": ["uuid-5", "uuid-6"]}},
                        "updates": {"value": 50.0}
                    }
                ],
                impact={
                    "updates": {"entities": 6},
                    "warnings": ["CRITICAL: 6 entities affected", "Tier 2: +56% increase", "Avg value: 28.50 - 40.00 (+40%)"],
                    "examples": ["CODE-T1-A: 25-35 (+40%)", "CODE-T2-A: 32-50 (+56%)"]
                }
            )

            # Complex: Soft delete with junction table cleanup
            write_data(
                goal="Remove attribute value (discontinued) with junction cleanup",
                reasoning="Value discontinued per business decision. Found 3 entities via entity_attributes junction. Soft deleting entities, junction records, and attribute to preserve history. No hard deletes.",
                operations=[
                    {
                        "action": "update",
                        "table": "entities",
                        "filters": {"id": {"in": ["uuid-1", "uuid-2", "uuid-3"]}, "is_active": True},
                        "updates": {"is_active": False, "discontinued_at": "2025-01-24T00:00:00Z"}
                    },
                    {
                        "action": "update",
                        "table": "entity_attributes",
                        "filters": {"attribute_id": "uuid-attr", "is_active": True},
                        "updates": {"is_active": False}
                    },
                    {
                        "action": "update",
                        "table": "attributes",
                        "filters": {"id": "uuid-attr"},
                        "updates": {"is_active": False}
                    }
                ],
                impact={
                    "updates": {"entities": 3, "entity_attributes": 3, "attributes": 1},
                    "warnings": ["CRITICAL: 3 entities discontinued", "Soft delete preserves history", "Entity count -3 (45 - 42)"],
                    "examples": ["CODE-A-1", "CODE-A-2"]
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
                            extra={"requested": op.table, "allowed": allowed_tables},
                        )
                        return build_agent_error_response(
                            exception=PermissionError(f"Access denied to table: {op.table}"),
                            context={"table": op.table, "goal": goal},
                            fallback_type="ACCESS_DENIED",
                            fallback_action=(
                                f"You don't have access to table '{op.table}'. "
                                f"Available tables: {allowed_tables}. "
                                f"Request access from system administrator if needed."
                            ),
                        )

            # Execute with MultiOperationExecutor
            executor = MultiOperationExecutor(storage)
            result = await executor.execute_intent(
                intent=write_intent, dry_run=dry_run, validate_only=validate_only
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
                    fallback_action=result.error_message or "Review operation structure and retry.",
                )

        except Exception as e:
            logger.error(
                f"WriteIntent execution error: {goal}", exc_info=True, extra={"goal": goal}
            )
            return build_agent_error_response(
                exception=e,
                context={"goal": goal},
                fallback_type="WRITE_ERROR",
                fallback_action=(
                    f"WriteIntent execution failed: {str(e)}. "
                    f"Review operations, dependencies, and data format."
                ),
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
            "- Creating: Entities, parents, children, attributes, assets\n"
            "- Updating: Values, statuses, descriptions, relationships\n"
            "- Deleting: Soft deletes (is_active=False), cleanup\n"
            "- Upserting: Idempotent create-or-update when you have conflict keys\n"
            "- Multi-table operations: Parent-child structures, junction tables\n"
            "- Asset uploads: Files from pending/ to permanent storage\n"
            "- Any database mutation: If it changes data, goes through write_data + HITL\n\n"
            "DON'T USE:\n"
            "- For reading (use read_data)\n"
            "- For schema inspection (use inspect_schema)\n"
            "- For analytics (use aggregate_data)\n"
            "- Without validation (ALWAYS inspect_schema + read_data BEFORE write_data)\n\n"
            "CRITICAL:\n"
            "- operations: Array of {action: 'create'/'update'/'delete'/'upsert', table: 'table_name', data: {...}, filters: {...}, updates: {...}, returns: 'ref_name', dependencies: ['parent_ref']}\n"
            "  * CREATE: {action: 'create', table: 'entities', data: {code: 'CODE-001', ...}, returns: 'entity'}\n"
            "  * UPDATE: {action: 'update', table: 'entities', filters: {id: 'uuid-123'}, updates: {value: 45.0}}\n"
            "  * DELETE: {action: 'delete', table: 'temp_records', filters: {id: 'uuid-123'}}\n"
            "  * UPSERT: {action: 'upsert', table: 'entities', data: {...}, on_conflict: 'skip'|'update', conflict_fields: ['code']}\n"
            "  * Batch: data can be array of dicts for multi-record creates\n"
            "- filters support equality / IN / numeric comparisons. Operator dicts supported: in, eq, neq, gt, gte, lt, lte (NO LIKE/ILIKE).\n"
            "  If you need fuzzy selection (e.g., code prefix), use read_data(search_patterns=...) first to get IDs, then update by id IN list.\n"
            "- Reference syntax: @name.field for dependencies\n"
            "  * Single: '@parent.id' references parent operation result\n"
            "  * Batch: '@types_batch[0].id' references first result in batch\n"
            "  * dependencies: ['parent'] ensures parent created before children\n"
            "- Dependency resolution: Automatic topological sort, cyclic dependencies rejected\n"
            "- Atomic transaction: All-or-nothing, automatic rollback on any error (no partial commits)\n"
            "- HITL required: User must approve via hitl_summary (plain language for business users)\n"
            "- Validation: Always inspect_schema + read_data before write_data to verify structure and check duplicates\n\n"
            "OPTIONAL:\n"
            "- asset_uploads: [{storage_path: 'pending/file.png', returns: 'asset'}] - reference '@asset.public_url' in operations\n"
            "- dry_run: Preview without executing (no HITL required)\n"
            "- validate_only: Check schemas without executing (no HITL required)\n\n"
            "EXAMPLES:\n"
            "# Multi-table create with dependencies\n"
            "write_data(\n"
            "    goal='Create parent entity with Axis A and Axis B attributes (4 children)',\n"
            "    reasoning='Duplicate check: 0 matches. Research complete. inspect_schema: required fields verified.',\n"
            "    hitl_summary='Creating parent entity with 4 children: CODE-A1-B1 (30), CODE-A1-B2 (32), CODE-A2-B1 (45), CODE-A2-B2 (48). Adds 1 parent, 2 axes, 4 children. Reply *approve* to proceed or *reject* to cancel.',\n"
            "    operations=[\n"
            "        {action: 'create', table: 'parent_entities', data: {name: 'Parent A', code_prefix: 'CODE-A', value: 30.0}, returns: 'parent'},\n"
            "        {action: 'create', table: 'attribute_types', data: [{name: 'Axis A', parent_id: '@parent.id'}, {name: 'Axis B', parent_id: '@parent.id'}], dependencies: ['parent'], returns: 'axes'},\n"
            "        {action: 'create', table: 'attributes', data: [{name: 'A1', type_id: '@axes[0].id'}, {name: 'A2', type_id: '@axes[0].id'}, {name: 'B1', type_id: '@axes[1].id'}, {name: 'B2', type_id: '@axes[1].id'}], dependencies: ['axes']},\n"
            "        {action: 'create', table: 'entities', data: [{parent_id: '@parent.id', code: 'CODE-A1-B1', name: 'Entity A1 B1', value: 30.0}, ...], dependencies: ['parent']}\n"
            "    ],\n"
            "    impact={creates: {parent_entities: 1, attribute_types: 2, attributes: 4, entities: 4}, warnings: ['Entity count +4'], examples: ['CODE-A1-B1']}\n"
            ")\n\n"
            "# Bulk update pattern (safe): query first, then update by IDs\n"
            "# 1) read_data(... search_patterns=...) to get entity ids\n"
            "# 2) write_data update with filters={'id': ['id1','id2',...]}\n\n"
            "ALSO CONSIDER:\n"
            "- inspect_schema: BEFORE write_data - verify required fields, enum values, constraints\n"
            "- read_data: BEFORE write_data - check duplicates, lookup foreign key IDs\n"
            "- Pattern: inspect_schema (structure) -> read_data (duplicates + FKs) -> write_data (execute)\n\n"
            "RETURNS: Always a structured dict with success flag.\n"
            "- success=True: {execution_time_ms, created_entities, updated_entities, deleted_entities, uploaded_assets?, summary, warnings?}\n"
            "  * created_entities maps table -> list of created rows (includes generated IDs)\n"
            "  * updated_entities/deleted_entities map table -> count\n"
            "- success=False: {error, error_type, goal, rollback_performed, Agent Action: ...}"
        ),
        args_schema=WriteDataInput,
        coroutine=_write_data_impl,
    )
