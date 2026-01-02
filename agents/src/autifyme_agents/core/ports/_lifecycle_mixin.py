"""Lifecycle mixin for transaction and cleanup operations."""

from abc import ABC, abstractmethod
from typing import Any


class LifecycleMixin(ABC):
    """Transaction support and lifecycle management."""

    @abstractmethod
    def transaction(self) -> Any:
        """
        Create a transaction context manager for atomic operations.

        Usage:
            async with storage.transaction():
                family = await storage.insert_entity("product_families", data)
                axes = await storage.insert_entities("variant_axes", axes_data)
                # Auto-rollback on any exception

        Returns:
            Async context manager for transaction handling

        Notes:
            - All operations within the context are atomic (all-or-nothing)
            - Exceptions trigger automatic rollback
            - Nested transactions may not be supported (adapter-specific)

        DEPRECATED: For multi-operation writes, use execute_write_intent_rpc()
        which provides true ACID guarantees via database RPC.
        """
        pass

    @abstractmethod
    async def execute_write_intent_rpc(
        self,
        operations: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute multi-operation write intent atomically via database RPC.

        Provides true ACID transaction guarantees - all operations succeed
        together or fail together with automatic rollback.

        Args:
            operations: List of operations (pre-sorted by dependencies).
                Each operation is a dict with:
                - action: 'create', 'update', 'delete', or 'upsert'
                - table: Target table name
                - data: Record data (for create/upsert)
                - filters: WHERE conditions (for update/delete)
                - updates: SET values (for update)
                - returns: Name to store result for @references
                - on_conflict: 'error', 'skip', 'update' (for create/upsert)
                - conflict_fields: Columns for ON CONFLICT (for upsert)
                - soft_delete: true/false (for delete)

            context: Pre-populated context (e.g., from asset uploads).
                Keys can be referenced in operations using @name.field syntax.

        Returns:
            On success: {
                'success': True,
                'results': [...],
                'context': {...},
                'operations_executed': int
            }
            On failure: {
                'success': False,
                'error': str,
                'error_code': str,
                'failed_operation_index': int,
                'failed_operation': {...}
            }

        Raises:
            StorageError: On RPC call failure
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """
        Cleanup resources on shutdown (connections, file handles, etc.).

        This method is called during application shutdown via atexit handlers.
        Implementations should:
        - Close database connections gracefully
        - Release file handles and network resources
        - Be idempotent (safe to call multiple times)
        - Not raise exceptions (log errors instead)
        """
        pass

    @abstractmethod
    async def cleanup_subagent_checkpoints(self, thread_id: str) -> dict[str, int]:
        """
        Delete subagent checkpoints for a thread after workflow completion.

        Subagents (specialists) are stateless - their checkpoints (tools:* namespace)
        are only needed during HITL interrupts for resume. Once PM completes without
        interrupt, all subagent checkpoints can be safely deleted to reclaim storage.

        Args:
            thread_id: Conversation thread ID to cleanup checkpoints for

        Returns:
            Dict with deletion counts:
            {
                'deleted_checkpoints': int,
                'deleted_blobs': int,
                'deleted_writes': int
            }

        Notes:
            - Only deletes checkpoints in 'tools:%' namespace (subagents)
            - PM checkpoints (root namespace) are preserved
            - Safe to call even if no subagent checkpoints exist
            - Does not raise on failure (logs warning instead)
        """
        pass
