"""
Multi-operation execution engine for Universal Data Engine.

Internal implementation module - use write_data tool for external access.

Executes WriteIntent structures with:
- Atomic multi-table transactions
- Dependency resolution (topological sorting)
- Reference resolution (@name.field syntax)
- Validation and dry-run modes
- Comprehensive error handling with rollback

Based on design from UNIVERSAL_DATA_ENGINE_DESIGN.md (lines 952-1047).
"""

import logging
import re
import time
from typing import Any

from langchain_core.tools import ToolException

from autifyme_agents.core.execution_context import to_storage_path
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
        uploaded_assets: list[dict[str, Any]] | None = None,
        execution_time_ms: int = 0,
        error_message: str | None = None,
        error_operation: str | None = None,
        rollback_performed: bool = False,
        warnings: list[str] | None = None,
    ):
        """Initialize execution result."""
        self.success = success
        self.created_entities = created_entities or {}
        self.updated_entities = updated_entities or {}
        self.deleted_entities = deleted_entities or {}
        self.uploaded_assets = uploaded_assets or []
        self.execution_time_ms = execution_time_ms
        self.error_message = error_message
        self.error_operation = error_operation
        self.rollback_performed = rollback_performed
        self.warnings = warnings or []

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

            # Include uploaded assets if any
            if self.uploaded_assets:
                result["uploaded_assets"] = self.uploaded_assets

            # Summary counts (handle both list[dict] and int values)
            total_created = sum(
                len(entities) if isinstance(entities, list) else entities
                for entities in self.created_entities.values()
            )
            total_updated = sum(self.updated_entities.values())
            total_deleted = sum(self.deleted_entities.values())

            result["summary"] = {
                "total_created": total_created,
                "total_updated": total_updated,
                "total_deleted": total_deleted,
                "assets_uploaded": len(self.uploaded_assets),
                "tables_affected": len(
                    set(
                        list(self.created_entities.keys())
                        + list(self.updated_entities.keys())
                        + list(self.deleted_entities.keys())
                    )
                ),
            }

            # Include warnings if any
            if self.warnings:
                result["warnings"] = self.warnings
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

        # Validate intent first (for all modes)
        validation_errors = await self._validate_intent(intent)

        if validation_errors:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                error_message="Validation failed:\n" + "\n".join(validation_errors),
                execution_time_ms=execution_time_ms,
            )

        # Validation mode - return after validation
        if validate_only:
            execution_time_ms = int((time.time() - start_time) * 1000)
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

        # Check operations list is not empty
        if not intent.operations or len(intent.operations) == 0:
            errors.append("WriteIntent must contain at least one operation")

        # Check operations have required data
        for i, op in enumerate(intent.operations):
            if op.action in ("create", "upsert") and op.data is None:
                errors.append(
                    f"Operation {i} ({op.action} on {op.table}): data is required for {op.action}"
                )

            if op.action == "update":
                if op.filters is None:
                    errors.append(f"Operation {i} (update on {op.table}): filters required")
                if op.updates is None and op.data is None:
                    errors.append(
                        f"Operation {i} (update on {op.table}): either updates or data required"
                    )

            if op.action == "delete" and op.filters is None:
                errors.append(f"Operation {i} (delete on {op.table}): filters required")

        # Check for circular dependencies
        try:
            self._resolve_dependencies(intent.operations)
        except ToolException as e:
            errors.append(f"Dependency error: {str(e)}")

        # Check for duplicate returns names
        returns_names_list = [op.returns for op in intent.operations if op.returns]
        returns_names = set(returns_names_list)
        if len(returns_names_list) != len(returns_names):
            # Find duplicates
            seen = set()
            duplicates = set()
            for name in returns_names_list:
                if name in seen:
                    duplicates.add(name)
                seen.add(name)
            errors.append(
                f"Duplicate returns names found: {', '.join(sorted(duplicates))}. "
                f"Each operation must have a unique returns name for cross-references."
            )

        # Check references are resolvable
        for i, op in enumerate(intent.operations):
            for dep in op.dependencies:
                if dep not in returns_names:
                    errors.append(
                        f"Operation {i} ({op.table}): dependency '{dep}' not found in returns names"
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
        Execute operations atomically via Postgres RPC.

        Provides true ACID transaction guarantees - all operations succeed
        together or fail together with automatic rollback.

        Execution order:
        1. Upload assets (if any) - store results in context
        2. Execute ALL database operations in single RPC call (atomic)
        3. On any error, Postgres rolls back automatically AND we delete uploaded assets
        """
        uploaded_assets: list[dict[str, Any]] = []  # Track for rollback

        try:
            # Resolve dependencies (topological sort)
            sorted_operations = self._resolve_dependencies(intent.operations)

            # Phase 1: Process assets BEFORE transaction
            # (uploads/moves are outside transaction since they're not DB ops)
            context: dict[str, Any] = {}  # Stores results by name for @ref resolution

            if intent.asset_uploads:
                for asset_upload in intent.asset_uploads:
                    # Two modes: storage_path (move) vs temp_path (upload)
                    if asset_upload.storage_path is not None:
                        # Mode 1: Move from pending/ to target folder (preferred)
                        # Convert user path to storage path (adds thread_id for pending/)
                        # User path: "pending/hero.png" -> Storage: "pending/{thread_id}/hero.png"
                        try:
                            internal_path = to_storage_path(asset_upload.storage_path)
                        except ValueError as e:
                            # If thread_id not available, try using path as-is (may already be internal)
                            logger.warning(f"Path conversion failed, using as-is: {e}")
                            internal_path = asset_upload.storage_path

                        logger.info(
                            f"Moving asset: {asset_upload.storage_path} -> {asset_upload.bucket}/{asset_upload.target_folder}",
                            extra={
                                "user_path": asset_upload.storage_path,
                                "internal_path": internal_path,
                                "bucket": asset_upload.bucket,
                                "target_folder": asset_upload.target_folder,
                                "returns": asset_upload.returns,
                            },
                        )

                        move_result = await self.storage.move_asset(
                            source_path=internal_path,
                            target_folder=asset_upload.target_folder,
                            bucket=asset_upload.bucket,
                        )

                        # Track for potential rollback
                        uploaded_assets.append(move_result)

                        # Store in context for reference resolution
                        # Include caption from AssetUpload for @name.caption reference
                        context[asset_upload.returns] = {
                            **move_result,
                            "caption": asset_upload.caption,
                        }

                        logger.info(
                            f"Asset moved: {move_result['public_url']}",
                            extra={
                                "returns": asset_upload.returns,
                                "public_url": move_result["public_url"],
                            },
                        )

                    elif asset_upload.temp_path is not None:
                        # Mode 2: Upload from local /tmp path (legacy, may fail on serverless)
                        logger.info(
                            f"Uploading asset: {asset_upload.temp_path} -> {asset_upload.bucket}/{asset_upload.folder}",
                            extra={
                                "temp_path": asset_upload.temp_path,
                                "bucket": asset_upload.bucket,
                                "folder": asset_upload.folder,
                                "returns": asset_upload.returns,
                            },
                        )

                        upload_result = await self.storage.upload_asset(
                            file_path=asset_upload.temp_path,
                            bucket=asset_upload.bucket,
                            folder=asset_upload.folder,
                        )

                        # Track for potential rollback
                        uploaded_assets.append(upload_result)

                        # Store in context for reference resolution
                        # Include caption from AssetUpload for @name.caption reference
                        context[asset_upload.returns] = {
                            **upload_result,
                            "caption": asset_upload.caption,
                        }

                        logger.info(
                            f"Asset uploaded: {upload_result['public_url']}",
                            extra={
                                "returns": asset_upload.returns,
                                "public_url": upload_result["public_url"],
                            },
                        )
                    else:
                        # Validation should have caught this, but defensive
                        raise ToolException(
                            f"AssetUpload '{asset_upload.returns}' has neither storage_path nor temp_path"
                        )

            # Phase 2: Execute ALL database operations atomically via RPC
            # Convert Operation objects to dicts for RPC
            operations_for_rpc = [
                {
                    "action": op.action,
                    "table": op.table,
                    "data": op.data,
                    "filters": op.filters,
                    "updates": op.updates,
                    "returns": op.returns,
                    "on_conflict": op.on_conflict,
                    "conflict_fields": op.conflict_fields,
                    "soft_delete": op.soft_delete,
                }
                for op in sorted_operations
            ]

            logger.info(
                f"Executing {len(operations_for_rpc)} operations via atomic RPC",
                extra={
                    "goal": intent.goal,
                    "operation_count": len(operations_for_rpc),
                    "context_keys": list(context.keys()),
                },
            )

            # Execute via RPC - true ACID transaction
            rpc_result = await self.storage.execute_write_intent_rpc(
                operations=operations_for_rpc,
                context=context,
            )

            execution_time_ms = int((time.time() - start_time) * 1000)

            if rpc_result.get("success"):
                # Parse RPC results into our format
                created_entities, updated_entities, deleted_entities, warnings = (
                    self._parse_rpc_results(rpc_result.get("results", []))
                )

                logger.info(
                    "WriteIntent execution successful (atomic RPC)",
                    extra={
                        "goal": intent.goal,
                        "execution_time_ms": execution_time_ms,
                        "assets_uploaded": len(uploaded_assets),
                        "operations_executed": rpc_result.get("operations_executed", 0),
                        "created_count": sum(
                            len(entities) if isinstance(entities, list) else entities
                            for entities in created_entities.values()
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
                    uploaded_assets=uploaded_assets,
                    execution_time_ms=execution_time_ms,
                    warnings=warnings,
                )
            else:
                # RPC returned failure - Postgres has already rolled back
                error_msg = self._build_error_message(
                    Exception(rpc_result.get("error", "Unknown RPC error"))
                )

                # Rollback uploaded assets since DB operations failed
                await self._rollback_assets(uploaded_assets)

                logger.error(
                    "WriteIntent RPC failed - Postgres rolled back automatically",
                    extra={
                        "goal": intent.goal,
                        "error": rpc_result.get("error"),
                        "error_code": rpc_result.get("error_code"),
                        "failed_operation_index": rpc_result.get("failed_operation_index"),
                        "execution_time_ms": execution_time_ms,
                        "assets_rolled_back": len(uploaded_assets),
                    },
                )

                return ExecutionResult(
                    success=False,
                    error_message=error_msg,
                    error_operation=str(rpc_result.get("failed_operation", {})),
                    execution_time_ms=execution_time_ms,
                    rollback_performed=True,
                )

        except Exception as e:
            # Network/auth error calling RPC
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_msg = self._build_error_message(e)

            # Rollback uploaded assets
            await self._rollback_assets(uploaded_assets)

            logger.error(
                "WriteIntent execution failed",
                exc_info=True,
                extra={
                    "goal": intent.goal,
                    "error": str(e),
                    "execution_time_ms": execution_time_ms,
                    "assets_rolled_back": len(uploaded_assets),
                },
            )

            return ExecutionResult(
                success=False,
                error_message=error_msg,
                execution_time_ms=execution_time_ms,
                rollback_performed=True,
            )

    def _parse_rpc_results(
        self, results: list[dict[str, Any]]
    ) -> tuple[
        dict[str, list[dict[str, Any]]],
        dict[str, int],
        dict[str, int],
        list[str],
    ]:
        """
        Parse RPC results array into executor result format.

        Returns:
            Tuple of (created_entities, updated_entities, deleted_entities, warnings)
        """
        created_entities: dict[str, list[dict[str, Any]]] = {}
        updated_entities: dict[str, int] = {}
        deleted_entities: dict[str, int] = {}
        warnings: list[str] = []

        for result in results:
            action = result.get("action")
            table = result.get("table")
            count = result.get("count", 0)
            data = result.get("data")

            # Skip if table is missing or not a string
            if not isinstance(table, str):
                continue

            if action == "create":
                if table not in created_entities:
                    created_entities[table] = []
                if isinstance(data, list):
                    created_entities[table].extend(data)
                elif data:
                    created_entities[table].append(data)

            elif action == "update":
                updated_entities[table] = updated_entities.get(table, 0) + count
                if count == 0:
                    warnings.append(
                        f"UPDATE on {table} matched 0 rows. "
                        f"Operation succeeded but no data was modified."
                    )

            elif action == "delete":
                deleted_entities[table] = deleted_entities.get(table, 0) + count
                if count == 0:
                    warnings.append(
                        f"DELETE on {table} matched 0 rows. "
                        f"Operation succeeded but no data was removed."
                    )

            elif action == "upsert":
                if table not in created_entities:
                    created_entities[table] = []
                if isinstance(data, list):
                    created_entities[table].extend(data)
                elif data:
                    created_entities[table].append(data)

        return created_entities, updated_entities, deleted_entities, warnings

    async def _rollback_assets(self, uploaded_assets: list[dict[str, Any]]) -> None:
        """Rollback uploaded assets on failure."""
        if not uploaded_assets:
            return

        logger.warning(
            f"Rolling back {len(uploaded_assets)} uploaded assets due to error",
            extra={"asset_count": len(uploaded_assets)},
        )

        for asset in uploaded_assets:
            try:
                await self.storage.delete_asset(
                    storage_path=asset["storage_path"],
                    bucket=asset["bucket"],
                )
                logger.info(f"Rolled back asset: {asset['storage_path']}")
            except Exception as rollback_error:
                logger.error(
                    f"Failed to rollback asset {asset['storage_path']}: {rollback_error}",
                    exc_info=True,
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
            # Each item in list is a dict, recursion returns dict
            resolved_list: list[dict[str, Any]] = []
            for item in data:
                resolved_item = self._resolve_references(item, context)
                # Type narrowing: when called with dict, returns dict
                assert isinstance(resolved_item, dict), "List items must be dicts"
                resolved_list.append(resolved_item)
            return resolved_list

        # data is dict (not list per above check)
        resolved: dict[str, Any] = {}

        for key, value in data.items():
            if isinstance(value, str) and value.startswith("@"):
                # Reference format: @name.field
                resolved[key] = self._resolve_reference_value(value, context)
            elif isinstance(value, dict):
                resolved[key] = self._resolve_references(value, context)
            elif isinstance(value, list):
                resolved[key] = [
                    self._resolve_references(item, context) if isinstance(item, dict) else item
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
                f"Reference '{ref_name}' not found in context. Available: {list(context.keys())}"
            )

        # Navigate nested field path (e.g., "id" or "nested.field")
        value = context[ref_name]
        for field in field_path.split("."):
            if not isinstance(value, dict) or field not in value:
                raise ToolException(f"Field '{field_path}' not found in '{ref_name}' context")
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
        return await self.storage.update_entities(table=table, filters=filters, updates=updates)

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
