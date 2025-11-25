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
