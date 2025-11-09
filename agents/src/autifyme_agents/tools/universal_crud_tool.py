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
import time
from collections import defaultdict
from datetime import UTC
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool, ToolException
from pydantic import BaseModel, ConfigDict, Field, create_model

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.schemas.operation_intent import (
    CreatedEntity,
    DeletedEntity,
    ExecutionResult,
    ExecutionStep,
    Operation,
    OperationIntent,
    TableCount,
    UpdatedEntity,
)
from autifyme_agents.schemas.registry import (
    SchemaRegistry,
    SchemaValidator,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Validation Helpers
# =============================================================================


def _validate_operation_completeness(
    operations: list[Operation],
    impact_analysis: dict[str, Any],
) -> None:
    """
    Validate that operations contain complete data matching impact analysis.

    Checks that entity counts in operations match the counts claimed in impact_analysis.
    Prevents partial data from reaching database (e.g., 18 entities when impact says 36).

    Aggregates counts across ALL operations for same table before comparing to impact_analysis.
    Multiple operations can target the same table (e.g., operation 3 and 5 both insert into product_variant_values).

    Args:
        operations: List of Operation objects
        impact_analysis: ImpactAnalysis dict with entity counts

    Raises:
        ToolException: If operation data is incomplete or mismatched with impact
    """
    # Get impact counts in list[TableCount] format (per schema)
    new_entities_count = impact_analysis.get("new_entities_count", [])
    updated_entities_count = impact_analysis.get("updated_entities_count", [])
    deleted_entities_count = impact_analysis.get("deleted_entities_count", [])

    # Aggregate actual counts across all operations per table
    actual_new_counts: dict[str, int] = defaultdict(int)
    actual_updated_counts: dict[str, int] = defaultdict(int)
    actual_deleted_counts: dict[str, int] = defaultdict(int)

    for operation in operations:
        op_type = operation.op_type
        table = operation.table

        # Count INSERT operations
        if op_type == "insert" and hasattr(operation, "new_entities") and operation.new_entities:
            actual_new_counts[table] += len(operation.new_entities)

        # Count UPDATE operations (both single-entity and bulk entity-specific updates)
        if op_type == "update" and hasattr(operation, "field_updates") and operation.field_updates:
            # Check if this is bulk entity-specific update (field values are dicts)
            has_entity_specific_updates = False
            for field_value in operation.field_updates.values():
                if isinstance(field_value, dict):
                    # Bulk update: field maps UUID -> value
                    actual_updated_counts[table] = max(
                        actual_updated_counts[table],
                        len(field_value)
                    )
                    has_entity_specific_updates = True
                    break  # Only need to count once per operation

            # If no entity-specific dict found, this is a single-entity update with target_filter
            if not has_entity_specific_updates and hasattr(operation, "target_filter") and operation.target_filter:
                # Single-entity update: count as 1
                actual_updated_counts[table] += 1

        # Count DELETE operations (ID list deletions)
        if op_type == "delete" and hasattr(operation, "delete_filter") and operation.delete_filter and "id" in operation.delete_filter:
            filter_value = operation.delete_filter["id"]
            if isinstance(filter_value, list):
                actual_deleted_counts[table] += len(filter_value)

    # Validate aggregated counts against impact_analysis (list[TableCount] format)
    for table_count in new_entities_count:
        table = table_count["table"]
        expected_count = table_count["count"]
        actual_count = actual_new_counts.get(table, 0)
        if expected_count > 0 and actual_count != expected_count:
            raise ToolException(
                f"INSERT count mismatch for {table}: operations provide {actual_count} entities "
                f"but impact_analysis claims {expected_count}. "
                f"Specialist must provide ALL entities - partial lists are FORBIDDEN. "
                f"Expected {expected_count} total entities across all operations for {table}."
            )

    for table_count in updated_entities_count:
        table = table_count["table"]
        expected_count = table_count["count"]
        actual_count = actual_updated_counts.get(table, 0)
        if expected_count > 0 and actual_count != expected_count:
            raise ToolException(
                f"UPDATE count mismatch for {table}: operations provide {actual_count} entity-specific updates "
                f"but impact_analysis claims {expected_count}. "
                f"All {expected_count} entities must have values specified."
            )

    for table_count in deleted_entities_count:
        table = table_count["table"]
        expected_count = table_count["count"]
        actual_count = actual_deleted_counts.get(table, 0)
        if expected_count > 0 and actual_count != expected_count:
            raise ToolException(
                f"DELETE count mismatch for {table}: operations target {actual_count} entities "
                f"but impact_analysis claims {expected_count}. "
                f"Delete filter must include all {expected_count} entity IDs."
            )


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
    ) -> ExecutionResult:
        """
        Execute multi-step plan with ACID guarantees.

        All operations execute within a database transaction for atomicity.
        Database automatically rolls back on any error.

        Args:
            steps: List of execution steps (references operations by index)
            operations: List of operations to execute (from change_spec)

        Returns:
            ExecutionResult with affected entities and created IDs

        Raises:
            ToolException: On validation or execution failure (DB auto-rolls back)
        """
        start_time = time.time()

        # Validate entire plan upfront (before transaction)
        self._validate_plan(steps, operations)

        # Execute all operations in database transaction
        try:
            async with self.storage.transaction():
                return await self._execute_plan_internal(steps, operations, start_time)
        except Exception as e:
            # Transaction auto-rolled back by database
            execution_time_ms = int((time.time() - start_time) * 1000)

            # Build actionable error message for agents
            error_type = type(e).__name__
            error_msg = str(e)

            # Extract step number from error message if available
            step_match = re.match(r"Step (\d+) failed", error_msg)
            failed_step = int(step_match.group(1)) if step_match else None

            # Enhance error message with context
            if "unique constraint" in error_msg.lower() or "already exists" in error_msg.lower():
                actionable_msg = f"CONSTRAINT_VIOLATION: {error_msg}\n\nAgent Action: Check for duplicate values in unique fields (sku, email, etc.). Query existing data first or use different values."
            elif "foreign key" in error_msg.lower() or "not found" in error_msg.lower():
                actionable_msg = f"MISSING_REFERENCE: {error_msg}\n\nAgent Action: Ensure referenced entities exist. Create parent entities first (e.g., product_family before products)."
            elif "validation failed" in error_msg.lower():
                actionable_msg = f"VALIDATION_ERROR: {error_msg}\n\nAgent Action: Fix data format/values. Check schema requirements (required fields, data types, value ranges)."
            elif "circular dependencies" in error_msg.lower():
                actionable_msg = f"DEPENDENCY_ERROR: {error_msg}\n\nAgent Action: Reorder operations to resolve dependencies. Create parent entities before children."
            else:
                actionable_msg = f"{error_type}: {error_msg}\n\nAgent Action: Review operation structure and retry with corrections."

            logger.error(
                "Execution failed - transaction rolled back",
                exc_info=True,
                extra={"error_type": error_type, "error": error_msg, "failed_step": failed_step}
            )

            return ExecutionResult(
                success=False,
                error_message=actionable_msg,
                error_step=failed_step,
                rollback_performed=True,
                execution_time_ms=execution_time_ms,
                steps_completed=0,
                steps_total=len(steps),
            )

    def _validate_plan(
        self,
        steps: list[ExecutionStep],
        operations: list[Operation],
    ) -> None:
        """
        Validate entire plan before execution (fail-fast).

        Checks:
        - All operation indices are valid
        - All referenced tables exist in schema
        - No circular dependencies

        Raises:
            ToolException: On validation failure
        """
        # Validate operation indices
        for step in steps:
            if step.operation_index < 0 or step.operation_index >= len(operations):
                raise ToolException(
                    f"Invalid operation_index {step.operation_index} in step {step.step_number}. "
                    f"Must be 0-{len(operations)-1}"
                )

        # Validate all tables exist in schema
        for operation in operations:
            try:
                self.schema.get_table(operation.table)
            except ValueError as e:
                raise ToolException(f"Invalid table in plan: {str(e)}") from e

        # Validate no circular dependencies
        try:
            self._resolve_dependencies(steps, operations)
        except ToolException:
            # Re-raise with context
            raise

    async def _execute_plan_internal(
        self,
        steps: list[ExecutionStep],
        operations: list[Operation],
        start_time: float,
    ) -> ExecutionResult:
        """Execute plan within transaction (all validation already done)."""
        completed_steps: list[tuple[ExecutionStep, dict[str, Any]]] = []
        # Strongly typed entity tracking
        created_entities: list[CreatedEntity] = []
        updated_entities_list: list[UpdatedEntity] = []
        deleted_entities_list: list[DeletedEntity] = []
        # Keep created_ids dict for backward compatibility with $step_N.field references
        created_ids: dict[int, dict[str, Any]] = {}

        # Sort steps by dependencies (already validated in _validate_plan)
        sorted_steps = self._resolve_dependencies(steps, operations)

        current_step = None
        try:
            for step in sorted_steps:
                current_step = step
                operation = operations[step.operation_index]

                logger.info(
                    f"Executing step {step.step_number}: {step.description}",
                    extra={"step": step.step_number, "operation": operation.op_type}
                )

                # Execute operation
                result = await self._execute_operation(operation, created_ids)
                completed_steps.append((step, result))

                # Store created IDs for dependent operations + structured tracking
                if operation.op_type == "insert" and result.get("ids"):
                    ids = result["ids"]
                    # Check if this is named refs or single entity
                    if isinstance(ids, dict) and "id" not in ids:
                        # Named refs dict - track each named entity
                        created_ids[step.step_number] = {"_refs": ids}
                        for ref_name, entity_id in ids.items():
                            created_entities.append(CreatedEntity(
                                entity_id=str(entity_id),
                                entity_name=ref_name,
                                table=operation.table,
                                step_number=step.step_number
                            ))
                    else:
                        # Single entity
                        created_ids[step.step_number] = ids
                        created_entities.append(CreatedEntity(
                            entity_id=str(ids.get("id", ids)),
                            entity_name=None,
                            table=operation.table,
                            step_number=step.step_number
                        ))

                # Track updated entities (structured)
                if operation.op_type == "update" and result.get("updated_details"):
                    for detail in result["updated_details"]:
                        updated_entities_list.append(UpdatedEntity(
                            entity_id=str(detail.get("id", "")),
                            table=operation.table,
                            updated_fields=detail.get("updated_fields", [])
                        ))

                # Track deleted entities (structured)
                if operation.op_type == "delete" and result.get("deleted_ids"):
                    for entity_id in result["deleted_ids"]:
                        deleted_entities_list.append(DeletedEntity(
                            entity_id=str(entity_id),
                            table=operation.table,
                            soft_delete=operation.soft_delete
                        ))

                logger.info(
                    f"Step {step.step_number} completed",
                    extra={"affected_rows": result.get("count", 0)}
                )

        except Exception as e:
            # Capture which step failed for detailed error reporting
            execution_time_ms = int((time.time() - start_time) * 1000)

            # Re-raise with step context attached
            error_with_context = ToolException(
                f"Step {current_step.step_number if current_step else 0} failed "
                f"({current_step.description if current_step else 'unknown'}): {str(e)}"
            )
            # Preserve original exception type info
            raise error_with_context from e

        # Success - calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)

        return ExecutionResult(
            success=True,
            affected_entities=self._count_affected(completed_steps, operations),
            created_ids=created_entities,
            updated_entities=updated_entities_list,
            deleted_entities=deleted_entities_list,
            execution_time_ms=execution_time_ms,
            steps_completed=len(completed_steps),
            steps_total=len(sorted_steps),
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

        Optimizes bulk inserts by batching when entities have no cross-references.

        Args:
            operation: Insert operation
            table_schema: Table schema metadata
            context: Created IDs from previous steps

        Returns:
            {"ids": {...}, "count": N}
        """
        if not operation.new_entities:
            return {"ids": {}, "count": 0}

        # Type narrowing: mypy now knows new_entities is not None
        entities = operation.new_entities

        # Schema-driven validation: Auto-validate unique constraints from metadata
        logger.debug(f"Validating {len(entities)} entities for {table_schema.name}")
        schema_validation = await table_schema.validate_before_insert(
            entities,
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

        # Check if entities can be batch inserted (no cross-references)
        can_batch = self._can_batch_insert(entities)

        if can_batch and len(entities) > 1:
            # Batch insert: All entities in single DB call (optimization)
            logger.debug(f"Batch inserting {len(entities)} independent entities")
            return await self._batch_insert_entities(
                operation, table_schema, context, entities
            )
        else:
            # Sequential insert: One at a time (required for cross-references or single entity)
            if not can_batch:
                logger.debug("Using sequential insert (entities have cross-references)")
            return await self._sequential_insert_entities(
                operation, table_schema, context, entities
            )

    async def _sequential_insert_entities(
        self,
        operation: Operation,
        table_schema: Any,
        context: dict[int, dict[str, Any]],
        entities: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Sequential entity insertion (required for entities with cross-references)."""
        inserted_entities = {}
        last_result = None

        for idx, entity in enumerate(entities):
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

        # Return appropriate format based on entity refs
        if inserted_entities:
            # Named entity references provided
            return {"ids": inserted_entities, "count": len(entities)}
        elif last_result:
            # No named refs, return last inserted ID
            return {"ids": last_result, "count": len(entities)}
        else:
            return {"ids": {}, "count": 0}

    async def _batch_insert_entities(
        self,
        operation: Operation,
        table_schema: Any,
        context: dict[int, dict[str, Any]],
        entities: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Batch entity insertion (OPTIMIZED - for independent entities)."""
        # Prepare all entities
        resolved_entities = []
        for entity in entities:
            # Resolve foreign key references from context
            resolved_entity = self._resolve_references(entity, context)

            # Auto-populate timestamp fields
            resolved_entity = self._populate_timestamps(table_schema, resolved_entity, is_update=False)

            # Validate against schema
            validation = self.validator.validate_entity(table_schema.name, resolved_entity)
            if not validation.valid:
                raise ToolException(
                    f"Validation failed for {table_schema.name}: {validation.errors}"
                )

            resolved_entities.append(resolved_entity)

        # Batch insert all entities in single DB call
        results = await self.storage.insert_entities(table_schema.name, resolved_entities)

        # Map results to named refs if provided
        inserted_entities = {}
        if operation.entity_refs:
            for ref_name, entity_idx in operation.entity_refs.items():
                if entity_idx < len(results):
                    inserted_entities[ref_name] = results[entity_idx]

        # Return named refs or all entities
        if inserted_entities:
            return {"ids": inserted_entities, "count": len(results)}
        elif results:
            return {"ids": results, "count": len(results)}
        else:
            return {"ids": {}, "count": 0}

    def _can_batch_insert(self, entities: list[dict[str, Any]]) -> bool:
        """
        Check if entities can be batch inserted (no cross-references).

        Entities CAN be batched if:
        - No entity references another entity in same batch via $ref:

        Args:
            entities: List of entities to insert

        Returns:
            True if entities can be batch inserted, False if sequential insertion needed
        """
        # Scan all entities for $ref: references to other entities in same batch
        for entity in entities:
            for value in entity.values():
                if isinstance(value, str) and value.startswith("$ref:"):
                    # Found cross-reference - cannot batch
                    return False
                elif isinstance(value, dict):
                    # Recursively check nested dicts
                    if not self._can_batch_insert([value]):
                        return False
                elif isinstance(value, list):
                    # Check list items
                    for item in value:
                        if isinstance(item, dict) and not self._can_batch_insert([item]) or isinstance(item, str) and item.startswith("$ref:"):
                            return False

        # No cross-references found - can batch
        return True

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

        # Build updated entity details for result tracking
        updated_details = []
        if count > 0:
            # Extract entity IDs from filter (if available)
            entity_id = resolved_filter.get("id")
            if entity_id:
                updated_details.append({
                    "id": entity_id,
                    "updated_fields": list(resolved_updates.keys())
                })

        return {"count": count, "updated_details": updated_details}

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

        # Extract deleted entity IDs for result tracking
        deleted_ids = []
        if count > 0:
            # Extract entity ID(s) from filter
            entity_id = resolved_filter.get("id")
            if entity_id:
                deleted_ids = entity_id if isinstance(entity_id, list) else [entity_id]

        return {"count": count, "soft_delete": operation.soft_delete, "deleted_ids": deleted_ids}

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
        for _step_num, step_context in context.items():
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
        from datetime import datetime

        result = data.copy()

        # Check if table has timestamp columns
        columns = table_schema.columns if hasattr(table_schema, 'columns') else {}

        # Auto-populate created_at for INSERTs (if not already provided)
        if not is_update and 'created_at' in columns and 'created_at' not in result:
            result['created_at'] = datetime.now(UTC).isoformat()

        # Auto-populate updated_at for both INSERTs and UPDATEs (if not already provided)
        if 'updated_at' in columns and 'updated_at' not in result:
            result['updated_at'] = datetime.now(UTC).isoformat()

        return result

    def _count_affected(
        self,
        completed_steps: list[tuple[ExecutionStep, dict[str, Any]]],
        operations: list[Operation]
    ) -> list[TableCount]:
        """
        Count affected entities by table.

        Args:
            completed_steps: List of (step, result) tuples
            operations: Operations list for resolving step.operation_index

        Returns:
            List of TableCount objects with table names and counts
        """
        affected: dict[str, int] = defaultdict(int)

        for step, result in completed_steps:
            operation = operations[step.operation_index]
            table = operation.table
            count = result.get("count", 0)
            affected[table] += count

        return [TableCount(table=table, count=count) for table, count in affected.items()]

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

        Uses storage port method (no direct adapter access).

        Args:
            table: Table name
            filter: WHERE conditions as dict
            include_relations: Related tables to include (PostgREST foreign key syntax)

        Returns:
            List of matching entities

        Raises:
            ToolException: On query failure
        """
        try:
            # Format relations for PostgREST (e.g., "categories(*)")
            formatted_relations = None
            if include_relations:
                formatted_relations = [f"{rel}(*)" for rel in include_relations]

            # Use port method with relation support
            return await self.storage.query_advanced(
                table=table,
                filters=filter,
                relations=formatted_relations
            )
        except Exception as e:
            logger.error(f"Failed to query {table}", exc_info=True)
            raise ToolException(f"Query failed for {table}: {str(e)}") from e


# =============================================================================
# Dynamic Schema Generation for Access Control
# =============================================================================


def _create_operation_input_schema(
    operations: list[str],
) -> type[BaseModel]:
    """
    Generate Pydantic input schema for specific database operations.

    Creates operation-scoped schemas with only relevant fields:
    - Read-only: query_filter (no change_spec, no impact_analysis)
    - Mutations: change_spec + impact_analysis (for HITL)

    Args:
        operations: Allowed operations (e.g., ["read"] or ["create", "update"])

    Returns:
        Dynamically generated Pydantic BaseModel class

    Examples:
        >>> ReadSchema = _create_operation_input_schema(["read"])
        >>> ReadSchema.model_fields.keys()
        dict_keys(['user_request_summary', 'reasoning', 'intent_type',
                   'query_filter', 'execution_plan', 'specialist_name', 'schema_version'])

        >>> CrudSchema = _create_operation_input_schema(["create", "read", "update", "delete"])
        >>> "change_spec" in CrudSchema.model_fields
        True
    """
    # Common fields for all operations
    fields: dict[str, Any] = {
        'user_request_summary': (
            str,
            Field(..., description='Summary of user original request')
        ),
        'reasoning': (
            str,
            Field(..., description='Why specialist classified this way (for transparency)')
        ),
    }

    # intent_type with operation-specific description
    allowed_ops = ', '.join(operations)
    if len(operations) == 1:
        intent_desc = f'Intent type. Must be "{operations[0]}". This tool handles {operations[0]} operations only.'
    else:
        intent_desc = f'Intent type. Allowed operations: {allowed_ops}'

    fields['intent_type'] = (
        str,
        Field(..., description=intent_desc)
    )

    # Operation-specific fields
    if operations == ["read"]:
        # Read-only: simplified query structure (no mutations)
        fields['query_filter'] = (
            dict[str, Any],
            Field(
                default={},
                description='Filter conditions for querying entities. '
                'Examples: {"id": "uuid-123"}, {"category": "electronics"}, '
                '{"is_active": true}. Used for WHERE clauses in SELECT operations.'
            )
        )
        fields['execution_plan'] = (
            dict[str, Any],
            Field(
                ...,
                description='Query execution plan. Define steps to fetch data from tables. '
                'READ-ONLY: no insert/update/delete operations allowed in this plan.'
            )
        )
    else:
        # Mutations need full spec
        fields['change_spec'] = (
            dict[str, Any],
            Field(
                ...,
                description='Specification of table operations. '
                'Contains operations array with insert/update/delete/query operation definitions.'
            )
        )
        fields['impact_analysis'] = (
            dict[str, Any],
            Field(
                ...,
                description='REQUIRED for HITL approval. Specifies new/updated/deleted entity counts per table. '
                'Example: {"new_entities_count": {"products": 5}, "updated_entities_count": {"products": 2}}'
            )
        )
        fields['execution_plan'] = (
            dict[str, Any],
            Field(
                ...,
                description='Multi-step execution plan with dependencies. '
                'Defines atomic steps with rollback support and dependency ordering.'
            )
        )

    # Common optional fields
    fields['specialist_name'] = (
        str | None,
        Field(default=None, description='Which specialist generated this intent (optional)')
    )
    fields['schema_version'] = (
        str,
        Field(default='v1', description='Schema version to validate against (default: v1)')
    )

    # Generate model name
    if operations == ["read"]:
        model_name = 'ReadOperationInput'
    elif set(operations) == {"create", "read", "update", "delete"}:
        model_name = 'FullCrudOperationInput'
    else:
        model_name = f"{''.join([op.title() for op in operations])}OperationInput"

    # Create dynamic model with config
    return create_model(
        model_name,
        __config__=ConfigDict(extra='forbid'),  # additionalProperties: false
        **fields
    )


def _generate_tool_description(
    operations: list[str],
    tables: list[str] | None = None,
) -> str:
    """
    Generate operation-specific tool description for LLM context.

    Args:
        operations: Allowed operations for this tool
        tables: Optional whitelist of accessible tables

    Returns:
        Human-readable tool description

    Examples:
        >>> _generate_tool_description(["read"])
        'Read-only database access. Query entities without modifications. ...'

        >>> _generate_tool_description(["create", "read", "update", "delete"])
        'Full CRUD database access. Create, read, update, and delete entities. ...'
    """
    # Operation description
    if operations == ["read"]:
        op_desc = "Read-only database access. Query entities without modifications."
    elif set(operations) == {"create", "read", "update", "delete"}:
        op_desc = "Full CRUD database access. Create, read, update, and delete entities."
    elif set(operations) == {"read", "update"}:
        op_desc = "Database query and update access. Read existing data and modify entities."
    elif set(operations) == {"read", "create"}:
        op_desc = "Database query and create access. Read existing data and insert new entities."
    elif set(operations) == {"read", "create", "update"}:
        op_desc = "Database read, create, and update access. Query and modify data (no delete)."
    else:
        op_list = ', '.join(operations)
        op_desc = f"Database operations: {op_list}."

    # Table scope
    if tables:
        if len(tables) <= 5:
            table_list = ', '.join(tables)
            scope_desc = f" Scoped to tables: {table_list}."
        else:
            scope_desc = f" Scoped to {len(tables)} specific tables."
    else:
        scope_desc = " Works across all schema tables."

    # Core capabilities
    capabilities = (
        " Schema-driven execution with dependency resolution, "
        "foreign key reference resolution, and atomic transactions with rollback."
    )

    return op_desc + scope_desc + capabilities


def _generate_tool_name(suffix: str | None = None) -> str:
    """
    Generate tool name with optional suffix.

    Args:
        suffix: Optional suffix for tool name specialization

    Returns:
        Tool name string

    Examples:
        >>> _generate_tool_name()
        'execute_database_operation'

        >>> _generate_tool_name('read_only')
        'execute_database_operation_read_only'

        >>> _generate_tool_name('products')
        'execute_database_operation_products'
    """
    base_name = "execute_database_operation"
    if suffix:
        return f"{base_name}_{suffix}"
    return base_name


# =============================================================================
# Dynamic CRUD Tool Factory (Operation-Scoped Access Control)
# =============================================================================


def create_database_tool(
    storage: StorageInterface,
    operations: list[str],
    tables: list[str] | None = None,
    tool_name_suffix: str | None = None,
) -> BaseTool:
    """
    Create operation-scoped database tool with dynamic schema and access control.

    This factory creates database tools with specific operation permissions:
    - Read-only tools: Only query operations, no mutations
    - Full CRUD tools: All operations (create, read, update, delete)
    - Mixed tools: Custom operation combinations (e.g., read + update)

    The generated tool has:
    - Dynamic Pydantic schema with only relevant fields
    - Context-aware field descriptions per operation type
    - Runtime validation of operations and table access
    - Clean JSON Schema for LLM function calling

    Args:
        storage: Storage interface for database operations (REQUIRED)
        operations: List of allowed operations. Valid values: "read", "create", "update", "delete"
        tables: Optional whitelist of accessible tables. None = all tables allowed
        tool_name_suffix: Optional suffix for tool name (e.g., "read_only", "products")

    Returns:
        StructuredTool configured for specified operations and tables

    Raises:
        ValueError: If operations list is empty or contains invalid operations

    Examples:
        # Read-only tool for market intelligence specialist
        >>> read_tool = create_database_tool(
        ...     storage=storage,
        ...     operations=["read"]
        ... )
        >>> # Tool has 6-field schema (no change_spec, no impact_analysis)
        >>> # Description: "Read-only database access..."

        # Full CRUD tool for product architecture specialist
        >>> crud_tool = create_database_tool(
        ...     storage=storage,
        ...     operations=["create", "read", "update", "delete"]
        ... )
        >>> # Tool has 8-field schema (full mutation support)
        >>> # Description: "Full CRUD database access..."

        # Domain-scoped tool for taxonomy specialist
        >>> taxonomy_tool = create_database_tool(
        ...     storage=storage,
        ...     operations=["read", "create", "update"],
        ...     tables=["categories", "category_product_mappings"],
        ...     tool_name_suffix="taxonomy"
        ... )
        >>> # Tool name: "execute_database_operation_taxonomy"
        >>> # Description: "...Scoped to tables: categories, category_product_mappings"

        # Read + update tool for campaign optimization
        >>> campaign_tool = create_database_tool(
        ...     storage=storage,
        ...     operations=["read", "update"],
        ...     tables=["campaigns", "ad_copies"],
        ...     tool_name_suffix="campaigns"
        ... )
        >>> # Tool has 8-field schema (mutations allowed, but not create/delete)

    Architecture:
        - Uses dynamic Pydantic schema generation (pydantic.create_model)
        - Closure captures access control parameters (operations, tables)
        - Runtime validation before execution
        - Single implementation for all operation combinations

    Related:
        - _create_operation_input_schema(): Dynamic schema generator
        - _generate_tool_description(): Description generator
        - _generate_tool_name(): Tool naming with optional suffixes
    """
    # Validate operations
    valid_operations = {"read", "create", "update", "delete"}
    if not operations:
        raise ValueError("operations list cannot be empty")

    invalid_ops = set(operations) - valid_operations
    if invalid_ops:
        raise ValueError(
            f"Invalid operations: {invalid_ops}. "
            f"Valid operations: {valid_operations}"
        )

    # Generate dynamic schema for validation (kept for internal validation)
    expected_schema = _create_operation_input_schema(operations)

    # Generate tool name and description
    tool_name = _generate_tool_name(tool_name_suffix)
    tool_description = _generate_tool_description(operations, tables)

    # Create simple input schema: single operation_intent parameter
    from pydantic import create_model
    SimpleInputSchema = create_model(
        'OperationIntentInput',
        operation_intent=(
            dict[str, Any],
            Field(
                ...,
                description=(
                    'Complete OperationIntent from specialist. '
                    'Extract the full JSON object from specialist\'s <operation_intent> tags and pass it here. '
                    'Required fields: user_request_summary, reasoning, intent_type, change_spec (or query_filter for reads), '
                    'impact_analysis, execution_plan. '
                    'DO NOT extract individual fields - pass the entire OperationIntent object.'
                )
            )
        )
    )

    # Create implementation with access control closure
    async def _execute_database_operation_impl(
        operation_intent: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Operation-scoped database executor with runtime validation.

        Validates operations and table access before execution.

        Args:
            operation_intent: Complete OperationIntent dict from specialist
        """
        # Validate operation_intent against expected schema
        try:
            validated = expected_schema.model_validate(operation_intent)
        except Exception as e:
            raise ToolException(
                f"Invalid OperationIntent structure: {str(e)}\n\n"
                f"Expected fields for {operations} operations: {list(expected_schema.model_fields.keys())}\n"
                f"Received: {list(operation_intent.keys())}"
            ) from e

        # Extract validated fields
        intent_type = validated.intent_type
        user_request_summary = validated.user_request_summary
        reasoning = validated.reasoning
        specialist_name = validated.specialist_name
        schema_version = validated.schema_version

        # Handle read-only vs mutation parameter differences
        if hasattr(validated, 'query_filter'):
            # Read-only operation
            query_filter = validated.query_filter
            execution_plan = validated.execution_plan

            # Build minimal change_spec for read operations
            change_spec = {
                'domain': 'product_catalog',  # Default domain
                'operations': [
                    {
                        'op_type': 'query',
                        'table': 'products',  # Will be overridden by execution plan
                        'query_filter': query_filter,
                        'include_relations': [],
                        'depends_on': []
                    }
                ]
            }
            # Minimal impact for read operations
            impact_analysis = {
                'affected_tables': {},
                'new_entities_count': {},
                'updated_entities_count': {},
                'deleted_entities_count': {},
                'business_impact_summary': 'Read-only query operation',
                'warnings': [],
                'examples': []
            }
        else:
            # Mutation operation
            change_spec = validated.change_spec
            impact_analysis = validated.impact_analysis
            execution_plan = validated.execution_plan

        # Validate operation is allowed
        if intent_type not in operations:
            raise ToolException(
                f"Operation '{intent_type}' not allowed for this tool. "
                f"Allowed operations: {', '.join(operations)}. "
                f"This tool is configured for: {', '.join(operations)} only."
            )

        # Validate table access if restricted
        if tables is not None and change_spec:
            ops_list = change_spec.get('operations', [])
            for operation in ops_list:
                table = operation.get('table')
                if table and table not in tables:
                    raise ToolException(
                        f"Table '{table}' not accessible by this tool. "
                        f"Allowed tables: {', '.join(tables)}. "
                        f"This tool is scoped to specific tables only."
                    )

        # Execute using shared implementation logic
        try:
            # Load schema for validation
            schema = SchemaRegistry.get_version(
                version=schema_version,
                domain=change_spec.get("domain", "product_catalog")
            )

            # Construct OperationIntent from parameters
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
                    "allowed_operations": operations,
                    "allowed_tables": tables,
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

            # Validate completeness (operations match impact_analysis counts)
            _validate_operation_completeness(
                operations=operation_intent.change_spec.operations,
                impact_analysis=operation_intent.impact_analysis.model_dump()
            )

            # Execute plan
            executor = OperationExecutor(storage, schema)
            result = await executor.execute_plan(
                steps=operation_intent.execution_plan.steps,
                operations=operation_intent.change_spec.operations,
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
            error_type = type(e).__name__
            error_msg = str(e)

            # Build actionable error message
            if "schema validation" in error_msg.lower():
                actionable_msg = f"SCHEMA_ERROR: {error_msg}\n\nAgent Action: Review change_spec structure. Ensure all required fields present and types correct."
            elif "invalid table" in error_msg.lower():
                actionable_msg = f"SCHEMA_ERROR: {error_msg}\n\nAgent Action: Use only valid table names from schema. Check available tables in schema registry."
            elif "incomplete" in error_msg.lower():
                actionable_msg = f"INCOMPLETE_DATA: {error_msg}\n\nAgent Action: Provide ALL entities claimed in impact_analysis. Partial data is forbidden."
            elif "not allowed" in error_msg.lower() or "not accessible" in error_msg.lower():
                actionable_msg = f"ACCESS_DENIED: {error_msg}\n\nAgent Action: This tool has restricted permissions. Use appropriate tool for this operation/table."
            else:
                actionable_msg = f"{error_type}: {error_msg}\n\nAgent Action: Review operation structure and fix validation errors before retrying."

            logger.error(
                "execute_database_operation failed before execution",
                exc_info=True,
                extra={"error_type": error_type, "error_msg": error_msg}
            )

            # Return error result instead of throwing
            error_result = ExecutionResult(
                success=False,
                error_message=actionable_msg,
                error_step=0,  # Error before any steps executed
                rollback_performed=False,
                execution_time_ms=0,
                steps_completed=0,
                steps_total=0,
            )
            return error_result.model_dump()

    # Create and return StructuredTool with simple single-parameter schema
    return StructuredTool.from_function(
        coroutine=_execute_database_operation_impl,
        name=tool_name,
        description=tool_description,
        args_schema=SimpleInputSchema,
    )
