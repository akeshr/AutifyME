"""Universal CRUD tool - schema-driven database operations.

Single tool that replaces all specialized persistence tools (save_product_family,
add_variant_values, update_product_fields, etc.). Handles ANY operation on ANY
table through runtime schema consultation and dynamic execution planning.

Key Features:
- Schema-driven validation and execution
- Dependency resolution (topological sorting)
- Foreign key reference resolution ($step_N.field syntax)
- Atomic transactions with rollback
- Business rule triggers
- Comprehensive error handling and logging
"""

import logging
import re
from collections import defaultdict
from typing import Any

from langchain.tools import tool
from langchain_core.tools import ToolException

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.schemas.operation_intent import (
    ExecutionResult,
    ExecutionStep,
    Operation,
    OperationIntent,
)
from autifyme_agents.schemas.registry import (
    SchemaRegistry,
    SchemaValidator,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Operation Executor - Core Execution Engine
# =============================================================================


class OperationExecutor:
    """
    Schema-aware operation executor.

    Executes multi-step operations with dependency resolution, foreign key
    reference resolution, and business rule triggers.
    """

    def __init__(self, storage: StorageInterface, schema: SchemaRegistry):
        """
        Initialize executor with storage and schema.

        Args:
            storage: Storage interface for database operations
            schema: Schema registry for validation and metadata
        """
        self.storage = storage
        self.schema = schema
        self.validator = SchemaValidator(schema)

    async def execute_plan(
        self,
        steps: list[ExecutionStep],
        operations: list[Operation],
        rollback_on_error: bool = True,
    ) -> ExecutionResult:
        """
        Execute multi-step plan with dependency resolution.

        Args:
            steps: List of execution steps (references operations by index)
            operations: List of operations to execute (from change_spec)
            rollback_on_error: Roll back completed steps if error occurs

        Returns:
            ExecutionResult with affected entities and created IDs

        Raises:
            ToolException: On validation or execution failure
        """
        import time

        start_time = time.time()
        completed_steps: list[tuple[ExecutionStep, dict[str, Any]]] = []
        created_ids: dict[int, dict[str, Any]] = {}

        try:
            # Sort steps by dependencies (topological order)
            sorted_steps = self._resolve_dependencies(steps, operations)

            for step in sorted_steps:
                # Resolve operation by index
                if step.operation_index < 0 or step.operation_index >= len(operations):
                    raise ToolException(
                        f"Invalid operation_index {step.operation_index} in step {step.step_number}. "
                        f"Must be 0-{len(operations)-1}"
                    )
                operation = operations[step.operation_index]

                logger.info(
                    f"Executing step {step.step_number}: {step.description}",
                    extra={"step": step.step_number, "operation": operation.op_type}
                )

                # Execute operation
                result = await self._execute_operation(operation, created_ids)
                completed_steps.append((step, result))

                # Store created IDs for dependent operations
                if operation.op_type == "insert" and result.get("ids"):
                    ids = result["ids"]
                    # Check if this is named refs or single entity
                    # Named refs: {"ref_name": {entity}, "ref_name2": {entity}}
                    # Single entity: {"id": "uuid", "name": "value", ...}
                    if isinstance(ids, dict) and "id" not in ids:
                        # No "id" field means this is a named refs dict, not an entity
                        created_ids[step.step_number] = {"_refs": ids}
                    else:
                        # Has "id" field or not a dict - single entity (legacy)
                        created_ids[step.step_number] = ids

                logger.info(
                    f"Step {step.step_number} completed successfully",
                    extra={"affected_rows": result.get("count", 0)}
                )

            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)

            return ExecutionResult(
                success=True,
                affected_entities=self._count_affected(completed_steps, operations),
                created_ids=created_ids,
                execution_time_ms=execution_time_ms,
                steps_completed=len(completed_steps),
                steps_total=len(sorted_steps),
            )

        except ToolException as e:
            # Tool-level errors (validation, schema, etc.) - already have good error messages
            logger.error(
                "Operation execution failed (ToolException)",
                exc_info=True,
                extra={
                    "error_type": "ToolException",
                    "error_message": str(e),
                    "steps_completed": len(completed_steps),
                    "steps_total": len(steps),
                }
            )

            # Rollback if requested
            rollback_performed = False
            if rollback_on_error and completed_steps:
                try:
                    await self._rollback(completed_steps, operations)
                    rollback_performed = True
                    logger.info("Rollback completed successfully")
                except Exception as rollback_error:
                    logger.error(
                        "Rollback failed",
                        exc_info=True,
                        extra={"rollback_error": str(rollback_error)}
                    )

            execution_time_ms = int((time.time() - start_time) * 1000)

            return ExecutionResult(
                success=False,
                error_message=str(e),
                error_step=len(completed_steps) + 1 if completed_steps else 1,
                rollback_performed=rollback_performed,
                execution_time_ms=execution_time_ms,
                steps_completed=len(completed_steps),
                steps_total=len(steps),
            )

        except Exception as e:
            # Unexpected errors (database down, network, etc.)
            logger.error(
                "Operation execution failed (unexpected error)",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "steps_completed": len(completed_steps),
                    "steps_total": len(steps),
                }
            )

            # Rollback if requested
            rollback_performed = False
            if rollback_on_error and completed_steps:
                try:
                    await self._rollback(completed_steps, operations)
                    rollback_performed = True
                    logger.info("Rollback completed successfully")
                except Exception as rollback_error:
                    logger.error(
                        "Rollback failed",
                        exc_info=True,
                        extra={"rollback_error": str(rollback_error)}
                    )

            execution_time_ms = int((time.time() - start_time) * 1000)

            return ExecutionResult(
                success=False,
                error_message=str(e),
                error_step=len(completed_steps) + 1 if completed_steps else 1,
                rollback_performed=rollback_performed,
                execution_time_ms=execution_time_ms,
                steps_completed=len(completed_steps),
                steps_total=len(steps),
            )

    def _resolve_dependencies(
        self, steps: list[ExecutionStep], operations: list[Operation]
    ) -> list[ExecutionStep]:
        """
        Sort steps by dependencies (topological order).

        Args:
            steps: Unsorted execution steps
            operations: Operations referenced by steps

        Returns:
            Steps sorted by dependencies

        Raises:
            ToolException: If circular dependencies detected
        """
        # Build mapping from operation_index to step_number
        op_index_to_step = {step.operation_index: step.step_number for step in steps}

        # Build dependency graph
        step_map = {step.step_number: step for step in steps}
        in_degree = {step.step_number: 0 for step in steps}
        adjacency = defaultdict(list)

        for step in steps:
            operation = operations[step.operation_index]
            for dep_op_index in operation.depends_on:
                # Convert operation index to step number
                if dep_op_index not in op_index_to_step:
                    raise ToolException(
                        f"Step {step.step_number} (operation {step.operation_index}) depends on "
                        f"operation {dep_op_index} which has no corresponding step"
                    )
                dep_step_num = op_index_to_step[dep_op_index]
                adjacency[dep_step_num].append(step.step_number)
                in_degree[step.step_number] += 1

        # Topological sort (Kahn's algorithm)
        queue = [num for num, degree in in_degree.items() if degree == 0]
        sorted_steps = []

        while queue:
            current = queue.pop(0)
            sorted_steps.append(step_map[current])

            for neighbor in adjacency[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Check for circular dependencies
        if len(sorted_steps) != len(steps):
            raise ToolException(
                "Circular dependencies detected in execution plan"
            )

        return sorted_steps

    async def _execute_operation(
        self, operation: Operation, context: dict[int, dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Execute single operation with schema validation.

        Args:
            operation: Operation to execute
            context: Context with created IDs from previous steps

        Returns:
            Operation result dict with affected counts and created IDs

        Raises:
            ToolException: On validation or execution failure
        """
        # Get table schema
        try:
            table_schema = self.schema.get_table(operation.table)
        except ValueError as e:
            raise ToolException(f"Invalid table: {str(e)}") from e

        # Route to appropriate handler
        handlers = {
            "insert": self._execute_insert,
            "update": self._execute_update,
            "delete": self._execute_delete,
            "query": self._execute_query,
        }

        handler = handlers.get(operation.op_type)
        if not handler:
            raise ToolException(f"Unsupported operation type: {operation.op_type}")

        return await handler(operation, table_schema, context)

    async def _execute_insert(
        self,
        operation: Operation,
        table_schema: Any,
        context: dict[int, dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Execute INSERT operation with reference resolution and business rules.

        Args:
            operation: Insert operation
            table_schema: Table schema metadata
            context: Created IDs from previous steps

        Returns:
            {"ids": {...}, "count": N}
        """
        if not operation.new_entities:
            return {"ids": {}, "count": 0}

        # Schema-driven validation: Auto-validate unique constraints from metadata
        logger.debug(f"Validating {len(operation.new_entities)} entities for {table_schema.name}")
        schema_validation = await table_schema.validate_before_insert(
            operation.new_entities,
            self.storage
        )
        if not schema_validation.valid:
            raise ToolException(
                f"Schema validation failed for {table_schema.name}: {schema_validation.errors}"
            )
        if schema_validation.warnings:
            logger.warning(
                f"Schema validation warnings for {table_schema.name}",
                extra={"warnings": schema_validation.warnings}
            )

        inserted_entities = {}
        last_result = None

        for idx, entity in enumerate(operation.new_entities):
            # Resolve foreign key references from context
            resolved_entity = self._resolve_references(entity, context)

            # Auto-populate timestamp fields (created_at, updated_at) if table has them
            resolved_entity = self._populate_timestamps(table_schema, resolved_entity, is_update=False)

            # Validate against schema
            validation = self.validator.validate_entity(table_schema.name, resolved_entity)
            if not validation.valid:
                raise ToolException(
                    f"Validation failed for {table_schema.name}: {validation.errors}"
                )

            # Insert entity
            result = await self._insert_entity(table_schema.name, resolved_entity)

            # Store result for tracking
            last_result = result

            # Store with named reference if provided
            if operation.entity_refs:
                for ref_name, entity_idx in operation.entity_refs.items():
                    if entity_idx == idx:
                        inserted_entities[ref_name] = result
                        break

        # Return named refs or single entity for backward compatibility
        if inserted_entities:
            # Multiple entities with named refs
            return {"ids": inserted_entities, "count": len(operation.new_entities)}
        elif last_result:
            # Single entity (legacy pattern)
            return {"ids": last_result, "count": len(operation.new_entities)}
        else:
            return {"ids": {}, "count": 0}

    async def _execute_update(
        self,
        operation: Operation,
        table_schema: Any,
        context: dict[int, dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Execute UPDATE operation.

        Args:
            operation: Update operation
            table_schema: Table schema metadata
            context: Created IDs from previous steps

        Returns:
            {"count": N}
        """
        if not operation.target_filter or not operation.field_updates:
            return {"count": 0}

        # Resolve references in filter and updates
        resolved_filter = self._resolve_references(operation.target_filter, context)
        resolved_updates = self._resolve_references(operation.field_updates, context)

        # Auto-populate updated_at timestamp if table has it
        resolved_updates = self._populate_timestamps(table_schema, resolved_updates, is_update=True)

        # Schema-driven validation: Validate unique constraints on updates
        schema_validation = await table_schema.validate_before_update(
            resolved_filter,
            resolved_updates,
            self.storage
        )
        if not schema_validation.valid:
            raise ToolException(
                f"Update validation failed for {table_schema.name}: {schema_validation.errors}"
            )
        if schema_validation.warnings:
            logger.warning(
                f"Update validation warnings for {table_schema.name}",
                extra={"warnings": schema_validation.warnings}
            )

        # Update entities
        count = await self._update_entities(
            table_schema.name, resolved_filter, resolved_updates
        )

        return {"count": count}

    async def _execute_delete(
        self,
        operation: Operation,
        table_schema: Any,
        context: dict[int, dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Execute DELETE operation.

        Args:
            operation: Delete operation
            table_schema: Table schema metadata
            context: Created IDs from previous steps

        Returns:
            {"count": N, "soft_delete": bool}
        """
        if not operation.delete_filter:
            return {"count": 0, "soft_delete": operation.soft_delete}

        resolved_filter = self._resolve_references(operation.delete_filter, context)

        # Schema-driven cascade impact calculation
        impact_result = await table_schema.calculate_cascade_impact(
            resolved_filter,
            self.storage,
            self.schema
        )
        if impact_result.get("status") == "calculated":
            logger.info(
                f"Cascade impact for {table_schema.name}",
                extra={
                    "impact": impact_result.get("impact", {}),
                    "total_affected": impact_result.get("total_affected", 0),
                    "is_destructive": impact_result.get("is_destructive", False)
                }
            )
        elif impact_result.get("status") == "calculation_failed":
            logger.warning(
                f"Cascade impact calculation failed for {table_schema.name}",
                extra={"error": impact_result.get("error")}
            )

        if operation.soft_delete:
            # Soft delete - mark as inactive (schema-aware)
            # Only set columns that exist in the table schema
            updates = {}

            # Check if table has is_active column
            if "is_active" in table_schema.columns:
                updates["is_active"] = False

            # Check if table has deleted_at column
            if "deleted_at" in table_schema.columns:
                # Use proper ISO timestamp instead of string literal "now()"
                from datetime import UTC, datetime
                updates["deleted_at"] = datetime.now(UTC).isoformat()

            # If no soft-delete columns exist, fall back to hard delete
            if not updates:
                logger.warning(
                    f"Table {table_schema.name} has no soft-delete columns (is_active, deleted_at). "
                    f"Performing hard delete instead."
                )
                count = await self._delete_entities(table_schema.name, resolved_filter)
            else:
                count = await self._update_entities(
                    table_schema.name,
                    resolved_filter,
                    updates
                )
        else:
            # Hard delete
            count = await self._delete_entities(table_schema.name, resolved_filter)

        return {"count": count, "soft_delete": operation.soft_delete}

    async def _execute_query(
        self,
        operation: Operation,
        table_schema: Any,
        context: dict[int, dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Execute READ operation.

        Args:
            operation: Query operation
            table_schema: Table schema metadata
            context: Created IDs from previous steps

        Returns:
            {"entities": [...], "count": N}
        """
        resolved_filter = self._resolve_references(operation.query_filter or {}, context)

        entities = await self._query_entities(
            table_schema.name,
            resolved_filter,
            operation.include_relations
        )

        return {"entities": entities, "count": len(entities)}

    def _resolve_references(
        self, data: dict[str, Any], context: dict[int, dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Resolve foreign key references from execution context.

        Supports two reference formats:
        1. Step field reference: "$step_1.family_id" → context[1]["family_id"]
        2. Named reference: "$ref:prod_500ml_clear" → context[N]["_refs"]["prod_500ml_clear"]["id"]

        Args:
            data: Dict potentially containing references
            context: Map of step_number → {field: value} or {_refs: {name: entity}}

        Returns:
            Data with references resolved to actual values
        """
        resolved = {}

        for key, value in data.items():
            if isinstance(value, str):
                # Named reference: $ref:entity_name
                if value.startswith("$ref:"):
                    ref_name = value[5:]  # Remove "$ref:" prefix
                    resolved[key] = self._resolve_named_ref(ref_name, context)
                # Step field reference: $step_N.field
                elif value.startswith("$step_"):
                    match = re.match(r"\$step_(\d+)\.(.+)", value)
                    if match:
                        step_num = int(match.group(1))
                        field_name = match.group(2)

                        if step_num not in context:
                            raise ToolException(
                                f"Reference to non-existent step {step_num} in '{value}'"
                            )

                        if field_name not in context[step_num]:
                            raise ToolException(
                                f"Field '{field_name}' not found in step {step_num} context"
                            )

                        resolved[key] = context[step_num][field_name]
                    else:
                        raise ToolException(f"Invalid reference syntax: '{value}'")
                else:
                    # Regular string value (not a reference)
                    resolved[key] = value
            elif isinstance(value, dict):
                # Recursively resolve nested dicts
                resolved[key] = self._resolve_references(value, context)
            elif isinstance(value, list):
                # Recursively resolve lists
                resolved[key] = [
                    self._resolve_references(item, context) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                resolved[key] = value

        return resolved

    def _resolve_named_ref(
        self, ref_name: str, context: dict[int, dict[str, Any]]
    ) -> str:
        """
        Resolve named entity reference to its ID.

        Searches through all steps for a named reference and returns the entity's ID.

        Context structure with named refs:
        {
            1: {
                "_refs": {
                    "prod_500ml_clear": {"id": "uuid-123", "sku": "PET-BTL-500ML-..."},
                    "prod_1l_amber": {"id": "uuid-456", ...}
                }
            }
        }

        Args:
            ref_name: Named reference (e.g., "prod_500ml_clear")
            context: Execution context with step results

        Returns:
            Entity ID (UUID string)

        Raises:
            ToolException: If reference not found
        """
        # Search all steps for named reference
        for step_num, step_context in context.items():
            if isinstance(step_context, dict) and "_refs" in step_context:
                refs = step_context["_refs"]
                if ref_name in refs:
                    entity = refs[ref_name]
                    if "id" in entity:
                        return entity["id"]
                    else:
                        raise ToolException(
                            f"Named reference '{ref_name}' found but entity has no 'id' field"
                        )

        # Reference not found - provide helpful error
        all_refs = []
        for step_context in context.values():
            if isinstance(step_context, dict) and "_refs" in step_context:
                all_refs.extend(step_context["_refs"].keys())

        if all_refs:
            raise ToolException(
                f"Named reference '{ref_name}' not found. "
                f"Available references: {', '.join(sorted(all_refs))}"
            )
        else:
            raise ToolException(
                f"Named reference '{ref_name}' not found. No named references available in context."
            )

    def _populate_timestamps(
        self, table_schema: Any, data: dict[str, Any], is_update: bool
    ) -> dict[str, Any]:
        """
        Auto-populate timestamp fields (created_at, updated_at) based on schema.

        Args:
            table_schema: Table schema metadata with column definitions
            data: Entity data dict
            is_update: If True, only populate updated_at; if False, populate both

        Returns:
            Data with timestamps populated
        """
        from datetime import datetime, timezone

        result = data.copy()

        # Check if table has timestamp columns
        columns = table_schema.columns if hasattr(table_schema, 'columns') else {}

        # Auto-populate created_at for INSERTs (if not already provided)
        if not is_update and 'created_at' in columns and 'created_at' not in result:
            result['created_at'] = datetime.now(timezone.utc).isoformat()

        # Auto-populate updated_at for both INSERTs and UPDATEs (if not already provided)
        if 'updated_at' in columns and 'updated_at' not in result:
            result['updated_at'] = datetime.now(timezone.utc).isoformat()

        return result

    def _count_affected(
        self,
        completed_steps: list[tuple[ExecutionStep, dict[str, Any]]],
        operations: list[Operation]
    ) -> dict[str, int]:
        """
        Count affected entities by table.

        Args:
            completed_steps: List of (step, result) tuples
            operations: Operations list for resolving step.operation_index

        Returns:
            Map of table_name → affected_count
        """
        affected = defaultdict(int)

        for step, result in completed_steps:
            operation = operations[step.operation_index]
            table = operation.table
            count = result.get("count", 0)
            affected[table] += count

        return dict(affected)

    async def _rollback(
        self,
        completed_steps: list[tuple[ExecutionStep, dict[str, Any]]],
        operations: list[Operation],
    ) -> None:
        """
        Rollback completed steps in reverse order.

        Args:
            completed_steps: Steps to rollback
            operations: Operations list for resolving step.operation_index

        Note: This is a best-effort rollback. For true ACID transactions,
        database-level transaction support is needed.
        """
        logger.warning(
            f"Rolling back {len(completed_steps)} completed steps",
            extra={"steps_count": len(completed_steps)}
        )

        for step, result in reversed(completed_steps):
            try:
                operation = operations[step.operation_index]
                if operation.op_type == "insert":
                    # Delete inserted entities
                    created_ids = result.get("ids", {})
                    if created_ids:
                        # Handle both named refs and direct IDs
                        if isinstance(created_ids, dict):
                            for entity_data in created_ids.values():
                                if isinstance(entity_data, dict) and "id" in entity_data:
                                    entity_id = entity_data["id"]
                                else:
                                    entity_id = entity_data
                                await self._delete_entities(
                                    operation.table,
                                    {"id": entity_id}
                                )
                        logger.info(
                            f"Rolled back INSERT for {operation.table}",
                            extra={"count": len(created_ids)}
                        )
                elif operation.op_type == "update":
                    # Cannot roll back updates without storing original values
                    logger.warning(
                        f"Cannot roll back UPDATE for {operation.table} (original values not stored)"
                    )
                elif operation.op_type == "delete":
                    # Cannot roll back hard deletes
                    if not result.get("soft_delete", False):
                        logger.warning(
                            f"Cannot roll back hard DELETE for {operation.table}"
                        )
            except Exception as e:
                logger.error(
                    f"Rollback failed for step {step.step_number}",
                    exc_info=True,
                    extra={"error": str(e)}
                )

    # =========================================================================
    # Storage Adapter Methods
    # =========================================================================

    async def _insert_entity(self, table: str, entity: dict[str, Any]) -> dict[str, Any]:
        """Insert single entity and return created record with ID.

        Uses storage port method (no direct adapter access).

        Args:
            table: Table name
            entity: Entity data to insert

        Returns:
            Inserted entity with generated ID

        Raises:
            ToolException: On insert failure
        """
        try:
            # Use port method instead of direct Supabase client access
            return await self.storage.insert_entity(table, entity)
        except Exception as e:
            logger.error(f"Failed to insert into {table}", exc_info=True)
            raise ToolException(f"Insert failed for {table}: {str(e)}") from e

    async def _update_entities(
        self, table: str, filter: dict[str, Any], updates: dict[str, Any]
    ) -> int:
        """Update entities matching filter and return count.

        Uses storage port method (no direct adapter access).

        Args:
            table: Table name
            filter: WHERE conditions as dict
            updates: Fields to update

        Returns:
            Number of updated entities

        Raises:
            ToolException: On update failure
        """
        try:
            # Use port method instead of direct Supabase client access
            return await self.storage.update_entities(table, filter, updates)
        except Exception as e:
            logger.error(f"Failed to update {table}", exc_info=True)
            raise ToolException(f"Update failed for {table}: {str(e)}") from e

    async def _delete_entities(self, table: str, filter: dict[str, Any]) -> int:
        """Delete entities matching filter and return count.

        Uses storage port method (no direct adapter access).

        Args:
            table: Table name
            filter: WHERE conditions as dict

        Returns:
            Number of deleted entities

        Raises:
            ToolException: On delete failure
        """
        try:
            # Use port method instead of direct Supabase client access
            return await self.storage.delete_entities(table, filter)
        except Exception as e:
            logger.error(f"Failed to delete from {table}", exc_info=True)
            raise ToolException(f"Delete failed for {table}: {str(e)}") from e

    async def _query_entities(
        self, table: str, filter: dict[str, Any], include_relations: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Query entities with optional relation includes.

        Args:
            table: Table name
            filter: WHERE conditions as dict
            include_relations: Related tables to include (Supabase foreign key syntax)

        Returns:
            List of matching entities

        Raises:
            ToolException: On query failure
        """
        try:
            client = self.storage._ensure_client()

            # Build select clause with relations
            select_clause = "*"
            if include_relations:
                # Supabase relation syntax: table(...) for foreign keys
                relation_selects = [f"{rel}(*)" for rel in include_relations]
                select_clause = f"*, {', '.join(relation_selects)}"

            query = client.table(table).select(select_clause)

            # Apply filters
            for key, value in filter.items():
                query = query.eq(key, value)

            result = query.execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Failed to query {table}", exc_info=True)
            raise ToolException(f"Query failed for {table}: {str(e)}") from e


# =============================================================================
# Universal CRUD Tool
# =============================================================================


def create_execute_database_operation_tool(storage: StorageInterface):
    """
    Create universal database operation tool.

    This single tool replaces all specialized persistence tools:
    - save_product_family
    - add_variant_values
    - add_variant_axis
    - update_product_fields
    - query_product_data
    - delete_product_data

    Args:
        storage: Storage interface for database operations

    Returns:
        LangChain tool that executes OperationIntent
    """

    @tool("execute_database_operation")
    async def execute_database_operation(
        intent_type: str,
        change_spec: dict[str, Any],
        user_request_summary: str,
        reasoning: str,
        impact_analysis: dict[str, Any],
        execution_plan: dict[str, Any],
        specialist_name: str | None = None,
        schema_version: str = "v1",
    ) -> dict[str, Any]:
        """
        Universal database operation executor.

        Executes ANY operation on ANY table through schema-driven planning.
        Works with current 9 tables and future tables without code changes.

        Args:
            intent_type: High-level intent classification (create/read/update/delete)
            change_spec: Specification of table operations
            user_request_summary: Summary of user's original request
            reasoning: Why specialist classified this way (for transparency)
            impact_analysis: Impact assessment for HITL
            execution_plan: Multi-step execution plan with dependencies
            specialist_name: Which specialist generated this intent (optional)
            schema_version: Schema version to validate against (default: v1)

        Returns:
            ExecutionResult with affected entities and created IDs

        Raises:
            ToolException: On validation or execution failure

        Examples:
            # Create product family
            execute_database_operation(
                intent_type="create",
                change_spec={
                    "operations": [
                        {"table": "product_families", "op_type": "insert", ...}
                    ]
                },
                user_request_summary="Create new product family",
                reasoning="User requested new family creation",
                impact_analysis={...},
                execution_plan={...}
            )

            # Add variant value
            execute_database_operation(
                intent_type="create",
                change_spec={
                    "operations": [
                        {"table": "variant_values", "op_type": "insert", ...},
                        {"table": "products", "op_type": "insert", "depends_on": [0]}
                    ]
                },
                user_request_summary="Add new variant value",
                reasoning="User requested new color option",
                impact_analysis={...},
                execution_plan={...}
            )
        """
        try:
            # Load schema first (needed for timestamp auto-population)
            schema = SchemaRegistry.get_version(
                version=schema_version,
                domain=change_spec.get("domain", "product_catalog")
            )

            # Auto-populate timestamp fields in change_spec BEFORE constructing OperationIntent
            from datetime import datetime, timezone
            for operation_dict in change_spec.get("operations", []):
                table_name = operation_dict.get("table")
                if not table_name:
                    continue

                table_schema = schema.get_table(table_name)
                op_type = operation_dict.get("op_type")

                # For INSERT operations, populate created_at and updated_at
                if op_type == "insert" and operation_dict.get("new_entities"):
                    for entity in operation_dict["new_entities"]:
                        if 'created_at' in table_schema.columns and 'created_at' not in entity:
                            entity['created_at'] = datetime.now(timezone.utc).isoformat()
                        if 'updated_at' in table_schema.columns and 'updated_at' not in entity:
                            entity['updated_at'] = datetime.now(timezone.utc).isoformat()

                # For UPDATE operations, populate updated_at
                elif op_type == "update" and operation_dict.get("field_updates"):
                    if 'updated_at' in table_schema.columns and 'updated_at' not in operation_dict["field_updates"]:
                        operation_dict["field_updates"]['updated_at'] = datetime.now(timezone.utc).isoformat()

            # Construct OperationIntent from flat parameters (timestamps now populated in change_spec)
            operation_intent = OperationIntent(
                intent_type=intent_type,
                change_spec=change_spec,
                user_request_summary=user_request_summary,
                reasoning=reasoning,
                impact_analysis=impact_analysis,
                execution_plan=execution_plan,
                specialist_name=specialist_name,
                schema_version=schema_version,
            )

            logger.info(
                f"Executing database operation: {operation_intent.intent_type}",
                extra={
                    "intent_type": operation_intent.intent_type,
                    "operations_count": len(operation_intent.change_spec.operations),
                    "schema_version": schema_version,
                }
            )

            # Validate against schema
            validator = SchemaValidator(schema)
            for operation in operation_intent.change_spec.operations:
                validation = validator.validate_operation(operation.model_dump())
                if not validation.valid:
                    raise ToolException(
                        f"Schema validation failed: {validation.errors}"
                    )

            # Execute plan
            executor = OperationExecutor(storage, schema)
            result = await executor.execute_plan(
                steps=operation_intent.execution_plan.steps,
                operations=operation_intent.change_spec.operations,
                rollback_on_error=True,
            )

            if result.success:
                logger.info(
                    "Operation executed successfully",
                    extra={
                        "affected_entities": result.affected_entities,
                        "execution_time_ms": result.execution_time_ms,
                    }
                )
            else:
                logger.error(
                    "Operation failed",
                    extra={
                        "error_message": result.error_message,
                        "error_step": result.error_step,
                        "rollback_performed": result.rollback_performed,
                    }
                )

            return result.model_dump()

        except Exception as e:
            # Catch errors that occur before execute_plan (schema validation, etc.)
            # Return ExecutionResult instead of re-raising to allow PM to handle gracefully
            logger.error(
                "execute_database_operation failed before execution",
                exc_info=True,
                extra={"error_type": type(e).__name__, "error_msg": str(e)}
            )

            # Return error result instead of throwing
            error_result = ExecutionResult(
                success=False,
                error_message=f"{type(e).__name__}: {str(e)}",
                error_step=0,  # Error before any steps executed
                rollback_performed=False,
                execution_time_ms=0,
                steps_completed=0,
                steps_total=0,
            )
            return error_result.model_dump()

    return execute_database_operation
