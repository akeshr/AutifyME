"""
Multi-operation execution engine for Universal Data Engine.

Executes WriteIntent structures with:
- Atomic multi-table transactions
- Dependency resolution (topological sorting)
- Reference resolution (@name.field syntax)
- Validation and dry-run modes
- Comprehensive error handling with rollback

Based on design from UNIVERSAL_DATA_ENGINE_DESIGN.md (lines 952-1047).
Extracted and enhanced from universal_crud_tool.py OperationExecutor.
"""

import logging
import re
import time
from typing import Any

from langchain_core.tools import ToolException

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.schemas.write_intent import Operation, WriteIntent

logger = logging.getLogger(__name__)


class ExecutionResult:
    """Result of multi-operation execution."""

    def __init__(
        self,
        success: bool,
        created_entities: dict[str, list[dict[str, Any]]] | None = None,
        updated_entities: dict[str, int] | None = None,
        deleted_entities: dict[str, int] | None = None,
        execution_time_ms: int = 0,
        error_message: str | None = None,
        error_operation: str | None = None,
        rollback_performed: bool = False,
    ):
        """Initialize execution result."""
        self.success = success
        self.created_entities = created_entities or {}
        self.updated_entities = updated_entities or {}
        self.deleted_entities = deleted_entities or {}
        self.execution_time_ms = execution_time_ms
        self.error_message = error_message
        self.error_operation = error_operation
        self.rollback_performed = rollback_performed

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for agent response."""
        result: dict[str, Any] = {
            "success": self.success,
            "execution_time_ms": self.execution_time_ms,
        }

        if self.success:
            result["created_entities"] = self.created_entities
            result["updated_entities"] = self.updated_entities
            result["deleted_entities"] = self.deleted_entities

            # Summary counts
            total_created = sum(len(entities) for entities in self.created_entities.values())
            total_updated = sum(self.updated_entities.values())
            total_deleted = sum(self.deleted_entities.values())

            result["summary"] = {
                "total_created": total_created,
                "total_updated": total_updated,
                "total_deleted": total_deleted,
                "tables_affected": len(
                    set(
                        list(self.created_entities.keys())
                        + list(self.updated_entities.keys())
                        + list(self.deleted_entities.keys())
                    )
                ),
            }
        else:
            result["error"] = self.error_message
            result["error_operation"] = self.error_operation
            result["rollback_performed"] = self.rollback_performed

        return result


class MultiOperationExecutor:
    """
    Execute multi-operation write intents with ACID guarantees.

    Features:
    - Atomic transactions (all-or-nothing)
    - Dependency resolution (topological sorting)
    - Reference resolution (@name.field)
    - Validation before execution
    - Dry-run preview mode
    - Comprehensive error handling
    """

    def __init__(self, storage: StorageInterface):
        """
        Initialize executor.

        Args:
            storage: Storage interface for database operations
        """
        self.storage = storage

    async def execute_intent(
        self,
        intent: WriteIntent,
        dry_run: bool = False,
        validate_only: bool = False,
    ) -> ExecutionResult:
        """
        Execute multi-operation write intent.

        Args:
            intent: WriteIntent with goal, reasoning, operations, impact
            dry_run: Preview mode (validate + show impact without executing)
            validate_only: Validation mode (check schema/constraints only)

        Returns:
            ExecutionResult with created/updated/deleted entities or error

        Raises:
            ToolException: On validation failure (if validate_only=False)
        """
        start_time = time.time()

        logger.info(
            f"Executing WriteIntent: {intent.goal}",
            extra={
                "goal": intent.goal,
                "operation_count": len(intent.operations),
                "dry_run": dry_run,
                "validate_only": validate_only,
            },
        )

        # Validation mode
        if validate_only:
            validation_errors = await self._validate_intent(intent)
            execution_time_ms = int((time.time() - start_time) * 1000)

            if validation_errors:
                return ExecutionResult(
                    success=False,
                    error_message=f"Validation failed:\n" + "\n".join(validation_errors),
                    execution_time_ms=execution_time_ms,
                )
            else:
                return ExecutionResult(
                    success=True,
                    execution_time_ms=execution_time_ms,
                )

        # Dry-run mode
        if dry_run:
            preview = await self._preview_impact(intent)
            execution_time_ms = int((time.time() - start_time) * 1000)
            preview["execution_time_ms"] = execution_time_ms
            preview["dry_run"] = True

            return ExecutionResult(
                success=True,
                created_entities=preview.get("creates", {}),
                execution_time_ms=execution_time_ms,
            )

        # Execute with transaction
        return await self._execute_with_transaction(intent, start_time)

    async def _validate_intent(self, intent: WriteIntent) -> list[str]:
        """
        Validate WriteIntent before execution.

        Checks:
        - Operations have required fields
        - No circular dependencies
        - References are resolvable
        - Data matches schema (if available)

        Returns:
            List of validation error messages (empty if valid)
        """
        errors: list[str] = []

        # Check operations have required data
        for i, op in enumerate(intent.operations):
            if op.action in ("create", "upsert") and op.data is None:
                errors.append(
                    f"Operation {i} ({op.action} on {op.table}): "
                    f"data is required for {op.action}"
                )

            if op.action == "update":
                if op.filters is None:
                    errors.append(
                        f"Operation {i} (update on {op.table}): filters required"
                    )
                if op.updates is None and op.data is None:
                    errors.append(
                        f"Operation {i} (update on {op.table}): "
                        f"either updates or data required"
                    )

            if op.action == "delete" and op.filters is None:
                errors.append(
                    f"Operation {i} (delete on {op.table}): filters required"
                )

        # Check for circular dependencies
        try:
            self._resolve_dependencies(intent.operations)
        except ToolException as e:
            errors.append(f"Dependency error: {str(e)}")

        # Check references are resolvable
        returns_names = {op.returns for op in intent.operations if op.returns}
        for i, op in enumerate(intent.operations):
            for dep in op.dependencies:
                if dep not in returns_names:
                    errors.append(
                        f"Operation {i} ({op.table}): "
                        f"dependency '{dep}' not found in returns names"
                    )

        return errors

    async def _preview_impact(self, intent: WriteIntent) -> dict[str, Any]:
        """
        Preview impact of WriteIntent without executing.

        Returns:
            Impact summary with entity counts, warnings, validation status
        """
        preview: dict[str, Any] = {
            "goal": intent.goal,
            "operations_count": len(intent.operations),
            "creates": {},
            "updates": {},
            "deletes": {},
            "warnings": [],
            "safe_to_execute": True,
        }

        # Aggregate from intent.impact
        if "creates" in intent.impact:
            preview["creates"] = intent.impact["creates"]

        if "updates" in intent.impact:
            preview["updates"] = intent.impact["updates"]

        if "deletes" in intent.impact:
            preview["deletes"] = intent.impact["deletes"]

        if "warnings" in intent.impact:
            preview["warnings"] = intent.impact["warnings"]

        # Validate operations
        validation_errors = await self._validate_intent(intent)
        if validation_errors:
            preview["safe_to_execute"] = False
            preview["validation_errors"] = validation_errors

        return preview

    async def _execute_with_transaction(
        self, intent: WriteIntent, start_time: float
    ) -> ExecutionResult:
        """
        Execute operations atomically with transaction.

        All operations execute in single transaction. On any error,
        transaction is rolled back automatically.
        """
        try:
            # Resolve dependencies (topological sort)
            sorted_operations = self._resolve_dependencies(intent.operations)

            # Execute in transaction
            async with self.storage.transaction():
                context: dict[str, Any] = {}  # Stores results by name for @ref resolution
                created_entities: dict[str, list[dict[str, Any]]] = {}
                updated_entities: dict[str, int] = {}
                deleted_entities: dict[str, int] = {}

                for op in sorted_operations:
                    logger.info(
                        f"Executing operation: {op.action} on {op.table}",
                        extra={"action": op.action, "table": op.table},
                    )

                    # Resolve references in data
                    resolved_data = (
                        self._resolve_references(op.data, context) if op.data else None
                    )

                    # Execute operation
                    if op.action == "create":
                        result = await self._execute_create(
                            op.table, resolved_data, op.on_conflict, op.conflict_fields
                        )

                        # Track created entities
                        if op.table not in created_entities:
                            created_entities[op.table] = []

                        if isinstance(result, list):
                            created_entities[op.table].extend(result)
                        else:
                            created_entities[op.table].append(result)

                        # Store in context for reference resolution
                        if op.returns:
                            if isinstance(result, list):
                                context[op.returns] = result[0]  # First result
                            else:
                                context[op.returns] = result

                    elif op.action == "update":
                        count = await self._execute_update(
                            op.table,
                            op.filters,
                            op.updates or resolved_data,
                        )
                        updated_entities[op.table] = updated_entities.get(op.table, 0) + count

                    elif op.action == "delete":
                        count = await self._execute_delete(
                            op.table, op.filters, op.soft_delete, op.cascade
                        )
                        deleted_entities[op.table] = deleted_entities.get(op.table, 0) + count

                    elif op.action == "upsert":
                        result = await self._execute_upsert(
                            op.table, resolved_data, op.conflict_fields
                        )

                        # Track created entities (upsert returns list)
                        if op.table not in created_entities:
                            created_entities[op.table] = []
                        created_entities[op.table].extend(result)

                        # Store in context
                        if op.returns:
                            context[op.returns] = result[0] if result else None

                execution_time_ms = int((time.time() - start_time) * 1000)

                logger.info(
                    "WriteIntent execution successful",
                    extra={
                        "goal": intent.goal,
                        "execution_time_ms": execution_time_ms,
                        "created_count": sum(
                            len(entities) for entities in created_entities.values()
                        ),
                        "updated_count": sum(updated_entities.values()),
                        "deleted_count": sum(deleted_entities.values()),
                    },
                )

                return ExecutionResult(
                    success=True,
                    created_entities=created_entities,
                    updated_entities=updated_entities,
                    deleted_entities=deleted_entities,
                    execution_time_ms=execution_time_ms,
                )

        except Exception as e:
            # Transaction automatically rolled back
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_msg = self._build_error_message(e)

            logger.error(
                "WriteIntent execution failed - transaction rolled back",
                exc_info=True,
                extra={
                    "goal": intent.goal,
                    "error": str(e),
                    "execution_time_ms": execution_time_ms,
                },
            )

            return ExecutionResult(
                success=False,
                error_message=error_msg,
                execution_time_ms=execution_time_ms,
                rollback_performed=True,
            )

    def _resolve_dependencies(self, operations: list[Operation]) -> list[Operation]:
        """
        Sort operations by dependencies using topological sort.

        Args:
            operations: List of operations with named dependencies

        Returns:
            Operations sorted in execution order

        Raises:
            ToolException: On circular dependencies
        """
        # Build dependency graph
        graph: dict[int, list[int]] = {i: [] for i in range(len(operations))}
        returns_map: dict[str, int] = {}  # Map returns name to operation index

        # Build returns map
        for i, op in enumerate(operations):
            if op.returns:
                returns_map[op.returns] = i

        # Build dependency edges
        for i, op in enumerate(operations):
            for dep_name in op.dependencies:
                if dep_name in returns_map:
                    dep_idx = returns_map[dep_name]
                    graph[dep_idx].append(i)  # dep_idx must execute before i

        # Topological sort using Kahn's algorithm
        in_degree = [0] * len(operations)
        for edges in graph.values():
            for node in edges:
                in_degree[node] += 1

        queue = [i for i in range(len(operations)) if in_degree[i] == 0]
        sorted_indices = []

        while queue:
            node = queue.pop(0)
            sorted_indices.append(node)

            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Check for circular dependencies
        if len(sorted_indices) != len(operations):
            raise ToolException(
                "Circular dependencies detected in operations. "
                "Check dependencies and returns fields."
            )

        return [operations[i] for i in sorted_indices]

    def _resolve_references(
        self,
        data: dict[str, Any] | list[dict[str, Any]],
        context: dict[str, Any],
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """
        Resolve @name.field references in data using context.

        Reference syntax:
        - @family.id -> context["family"]["id"]
        - @size_axis.id -> context["size_axis"]["id"]

        Args:
            data: Data potentially containing references
            context: Map of returns_name -> entity data

        Returns:
            Data with references resolved to actual values

        Raises:
            ToolException: If reference cannot be resolved
        """
        if isinstance(data, list):
            return [self._resolve_references(item, context) for item in data]

        if not isinstance(data, dict):
            return data

        resolved: dict[str, Any] = {}

        for key, value in data.items():
            if isinstance(value, str) and value.startswith("@"):
                # Reference format: @name.field
                resolved[key] = self._resolve_reference_value(value, context)
            elif isinstance(value, dict):
                resolved[key] = self._resolve_references(value, context)
            elif isinstance(value, list):
                resolved[key] = [
                    self._resolve_references(item, context)
                    if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                resolved[key] = value

        return resolved

    def _resolve_reference_value(self, ref: str, context: dict[str, Any]) -> Any:
        """
        Resolve single reference string.

        Args:
            ref: Reference string like "@family.id"
            context: Context map

        Returns:
            Resolved value

        Raises:
            ToolException: If reference invalid or not found
        """
        # Parse @name.field
        match = re.match(r"@([^.]+)\.(.+)", ref)
        if not match:
            raise ToolException(
                f"Invalid reference syntax: '{ref}'. "
                f"Expected format: @name.field (e.g., @family.id)"
            )

        ref_name = match.group(1)
        field_path = match.group(2)

        if ref_name not in context:
            raise ToolException(
                f"Reference '{ref_name}' not found in context. "
                f"Available: {list(context.keys())}"
            )

        # Navigate nested field path (e.g., "id" or "nested.field")
        value = context[ref_name]
        for field in field_path.split("."):
            if not isinstance(value, dict) or field not in value:
                raise ToolException(
                    f"Field '{field_path}' not found in '{ref_name}' context"
                )
            value = value[field]

        return value

    async def _execute_create(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        on_conflict: str,
        conflict_fields: list[str] | None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Execute create operation (single or bulk)."""
        if isinstance(data, list):
            # Bulk insert
            if on_conflict == "skip" or on_conflict == "update":
                # Use upsert for conflict handling
                return await self.storage.bulk_upsert(
                    table=table, data=data, conflict_fields=conflict_fields
                )
            else:
                # Simple bulk insert (will fail on conflict)
                return await self.storage.bulk_upsert(table=table, data=data)
        else:
            # Single insert
            result = await self.storage.insert_entity(table=table, data=data)
            return result

    async def _execute_update(
        self,
        table: str,
        filters: dict[str, Any],
        updates: dict[str, Any],
    ) -> int:
        """Execute update operation."""
        return await self.storage.update_entities(
            table=table, filters=filters, updates=updates
        )

    async def _execute_delete(
        self,
        table: str,
        filters: dict[str, Any],
        soft_delete: bool,
        cascade: bool,
    ) -> int:
        """Execute delete operation."""
        # Note: cascade handling would require schema analysis
        # For now, rely on database CASCADE constraints
        return await self.storage.delete_entities(
            table=table, filters=filters, soft_delete=soft_delete
        )

    async def _execute_upsert(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        conflict_fields: list[str] | None,
    ) -> list[dict[str, Any]]:
        """Execute upsert operation."""
        if isinstance(data, list):
            return await self.storage.bulk_upsert(
                table=table, data=data, conflict_fields=conflict_fields
            )
        else:
            result = await self.storage.upsert_entity(
                table=table, data=data, conflict_fields=conflict_fields
            )
            return [result]

    def _build_error_message(self, exception: Exception) -> str:
        """Build actionable error message for agents."""
        error_msg = str(exception)

        if "unique constraint" in error_msg.lower() or "already exists" in error_msg.lower():
            return (
                f"CONSTRAINT_VIOLATION: {error_msg}\n\n"
                f"Agent Action: Check for duplicate values in unique fields (sku, email, etc.). "
                f"Query existing data first or use different values."
            )
        elif "foreign key" in error_msg.lower() or "not found" in error_msg.lower():
            return (
                f"MISSING_REFERENCE: {error_msg}\n\n"
                f"Agent Action: Ensure referenced entities exist. "
                f"Create parent entities first (e.g., product_family before products)."
            )
        elif "validation failed" in error_msg.lower():
            return (
                f"VALIDATION_ERROR: {error_msg}\n\n"
                f"Agent Action: Fix data format/values. "
                f"Check schema requirements (required fields, data types, value ranges)."
            )
        elif "circular dependencies" in error_msg.lower():
            return (
                f"DEPENDENCY_ERROR: {error_msg}\n\n"
                f"Agent Action: Reorder operations to resolve dependencies. "
                f"Create parent entities before children."
            )
        else:
            return (
                f"{type(exception).__name__}: {error_msg}\n\n"
                f"Agent Action: Review operation structure and retry with corrections."
            )
