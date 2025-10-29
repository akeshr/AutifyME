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

from autifyme_agents.core.business_rules import BusinessRuleHandlers
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.schemas.operation_intent import (
    ExecutionResult,
    ExecutionStep,
    Operation,
    OperationIntent,
)
from autifyme_agents.schemas.registry import (
    BusinessRuleTrigger,
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
        self.business_rules = BusinessRuleHandlers(storage, schema)

    async def execute_plan(
        self,
        steps: list[ExecutionStep],
        rollback_on_error: bool = True,
    ) -> ExecutionResult:
        """
        Execute multi-step plan with dependency resolution.

        Args:
            steps: List of execution steps
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
            sorted_steps = self._resolve_dependencies(steps)

            for step in sorted_steps:
                logger.info(
                    f"Executing step {step.step_number}: {step.description}",
                    extra={"step": step.step_number, "operation": step.operation.op_type}
                )

                # Execute operation
                result = await self._execute_operation(step.operation, created_ids)
                completed_steps.append((step, result))

                # Store created IDs for dependent operations
                if step.operation.op_type == "insert" and result.get("ids"):
                    created_ids[step.step_number] = result["ids"]

                logger.info(
                    f"Step {step.step_number} completed successfully",
                    extra={"affected_rows": result.get("count", 0)}
                )

            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)

            return ExecutionResult(
                success=True,
                affected_entities=self._count_affected(completed_steps),
                created_ids=created_ids,
                execution_time_ms=execution_time_ms,
                steps_completed=len(completed_steps),
                steps_total=len(sorted_steps),
            )

        except Exception as e:
            logger.error(
                "Operation execution failed",
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
                    await self._rollback(completed_steps)
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

    def _resolve_dependencies(self, steps: list[ExecutionStep]) -> list[ExecutionStep]:
        """
        Sort steps by dependencies (topological order).

        Args:
            steps: Unsorted execution steps

        Returns:
            Steps sorted by dependencies

        Raises:
            ToolException: If circular dependencies detected
        """
        # Build dependency graph
        step_map = {step.step_number: step for step in steps}
        in_degree = {step.step_number: 0 for step in steps}
        adjacency = defaultdict(list)

        for step in steps:
            for dep in step.operation.depends_on:
                if dep not in step_map:
                    raise ToolException(
                        f"Step {step.step_number} depends on non-existent step {dep}"
                    )
                adjacency[dep].append(step.step_number)
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

        created_ids = {}

        for entity in operation.new_entities:
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

            # BEFORE_INSERT business rules
            rule_context = {
                "operation": operation,
                "table": table_schema.name,
                "entities": [resolved_entity],
            }
            self.business_rules.execute_rules_for_trigger(
                table_schema.name,
                BusinessRuleTrigger.BEFORE_INSERT,
                rule_context,
            )

            # Insert entity
            result = await self._insert_entity(table_schema.name, resolved_entity)

            # AFTER_INSERT business rules
            rule_context["inserted_entity"] = result
            self.business_rules.execute_rules_for_trigger(
                table_schema.name,
                BusinessRuleTrigger.AFTER_INSERT,
                rule_context,
            )

            # Store the full inserted entity for reference resolution
            # This allows $step_N.id, $step_N.sku_prefix, etc.
            entity_id = result.get("id") or result.get(table_schema.primary_key)
            if entity_id:
                created_ids = result  # Store full entity with all fields
                # Note: For multi-entity inserts, this would need to be a list
                # Current design assumes single entity per step for dependency resolution

        return {"ids": created_ids, "count": len(operation.new_entities)}

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

        if operation.soft_delete:
            # Soft delete - mark as inactive
            count = await self._update_entities(
                table_schema.name,
                resolved_filter,
                {"is_active": False, "deleted_at": "now()"}
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

        Supports $step_N.field syntax for referencing created IDs:
        - "$step_1.family_id" → context[1]["family_id"]
        - "$step_2.axis_id" → context[2]["axis_id"]

        Args:
            data: Dict potentially containing references
            context: Map of step_number → {field: value}

        Returns:
            Data with references resolved to actual values
        """
        resolved = {}

        for key, value in data.items():
            if isinstance(value, str) and value.startswith("$step_"):
                # Parse reference: $step_1.family_id
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
        self, completed_steps: list[tuple[ExecutionStep, dict[str, Any]]]
    ) -> dict[str, int]:
        """
        Count affected entities by table.

        Args:
            completed_steps: List of (step, result) tuples

        Returns:
            Map of table_name → affected_count
        """
        affected = defaultdict(int)

        for step, result in completed_steps:
            table = step.operation.table
            count = result.get("count", 0)
            affected[table] += count

        return dict(affected)

    async def _rollback(
        self, completed_steps: list[tuple[ExecutionStep, dict[str, Any]]]
    ) -> None:
        """
        Rollback completed steps in reverse order.

        Args:
            completed_steps: Steps to rollback

        Note: This is a best-effort rollback. For true ACID transactions,
        database-level transaction support is needed.
        """
        logger.warning(
            f"Rolling back {len(completed_steps)} completed steps",
            extra={"steps_count": len(completed_steps)}
        )

        for step, result in reversed(completed_steps):
            try:
                if step.operation.op_type == "insert":
                    # Delete inserted entities
                    created_ids = result.get("ids", {})
                    if created_ids:
                        for entity_id in created_ids.values():
                            await self._delete_entities(
                                step.operation.table,
                                {"id": entity_id}
                            )
                        logger.info(
                            f"Rolled back INSERT for {step.operation.table}",
                            extra={"count": len(created_ids)}
                        )
                elif step.operation.op_type == "update":
                    # Cannot roll back updates without storing original values
                    logger.warning(
                        f"Cannot roll back UPDATE for {step.operation.table} (original values not stored)"
                    )
                elif step.operation.op_type == "delete":
                    # Cannot roll back hard deletes
                    if not result.get("soft_delete", False):
                        logger.warning(
                            f"Cannot roll back hard DELETE for {step.operation.table}"
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

        Args:
            table: Table name
            entity: Entity data to insert

        Returns:
            Inserted entity with generated ID

        Raises:
            ToolException: On insert failure
        """
        try:
            client = self.storage._ensure_client()
            result = client.table(table).insert(entity).execute()

            if not result.data or len(result.data) == 0:
                raise ToolException(f"Insert to {table} returned no data")

            return result.data[0]  # Return first inserted record
        except Exception as e:
            logger.error(f"Failed to insert into {table}", exc_info=True)
            raise ToolException(f"Insert failed for {table}: {str(e)}") from e

    async def _update_entities(
        self, table: str, filter: dict[str, Any], updates: dict[str, Any]
    ) -> int:
        """Update entities matching filter and return count.

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
            client = self.storage._ensure_client()
            query = client.table(table).update(updates)

            # Apply filters
            for key, value in filter.items():
                query = query.eq(key, value)

            result = query.execute()
            return len(result.data) if result.data else 0
        except Exception as e:
            logger.error(f"Failed to update {table}", exc_info=True)
            raise ToolException(f"Update failed for {table}: {str(e)}") from e

    async def _delete_entities(self, table: str, filter: dict[str, Any]) -> int:
        """Delete entities matching filter and return count.

        Args:
            table: Table name
            filter: WHERE conditions as dict

        Returns:
            Number of deleted entities

        Raises:
            ToolException: On delete failure
        """
        try:
            client = self.storage._ensure_client()
            query = client.table(table).delete()

            # Apply filters
            for key, value in filter.items():
                query = query.eq(key, value)

            result = query.execute()
            return len(result.data) if result.data else 0
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
        intent: dict[str, Any],
        schema_version: str = "v1",
    ) -> dict[str, Any]:
        """
        Universal database operation executor.

        Executes ANY operation on ANY table through schema-driven planning.
        Works with current 9 tables and future tables without code changes.

        Args:
            intent: OperationIntent serialized as dict
            schema_version: Schema version to validate against (default: v1)

        Returns:
            ExecutionResult with affected entities and created IDs

        Raises:
            ToolException: On validation or execution failure

        Examples:
            # Create product family
            intent = {
                "intent_type": "create",
                "change_spec": {
                    "operations": [
                        {"table": "product_families", "op_type": "insert", ...}
                    ]
                },
                ...
            }

            # Add variant value
            intent = {
                "intent_type": "create",
                "change_spec": {
                    "operations": [
                        {"table": "variant_values", "op_type": "insert", ...},
                        {"table": "products", "op_type": "insert", "depends_on": [0]}
                    ]
                },
                ...
            }
        """
        try:
            # Parse intent
            operation_intent = OperationIntent(**intent)

            logger.info(
                f"Executing database operation: {operation_intent.intent_type}",
                extra={
                    "intent_type": operation_intent.intent_type,
                    "operations_count": len(operation_intent.change_spec.operations),
                    "schema_version": schema_version,
                }
            )

            # Load schema
            schema = SchemaRegistry.get_version(
                version=schema_version,
                domain=operation_intent.change_spec.domain
            )

            # Auto-populate timestamp fields BEFORE validation
            from datetime import datetime, timezone
            for operation in operation_intent.change_spec.operations:
                table_schema = schema.get_table(operation.table)

                # For INSERT operations, populate created_at and updated_at
                if operation.op_type == "insert" and operation.new_entities:
                    for entity in operation.new_entities:
                        if 'created_at' in table_schema.columns and 'created_at' not in entity:
                            entity['created_at'] = datetime.now(timezone.utc).isoformat()
                        if 'updated_at' in table_schema.columns and 'updated_at' not in entity:
                            entity['updated_at'] = datetime.now(timezone.utc).isoformat()

                # For UPDATE operations, populate updated_at
                elif operation.op_type == "update" and operation.field_updates:
                    if 'updated_at' in table_schema.columns and 'updated_at' not in operation.field_updates:
                        operation.field_updates['updated_at'] = datetime.now(timezone.utc).isoformat()

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
            logger.error(
                "execute_database_operation failed",
                exc_info=True,
                extra={"error_type": type(e).__name__, "error_msg": str(e)}
            )
            raise ToolException(f"Database operation failed: {str(e)}") from e

    return execute_database_operation
