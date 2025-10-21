"""Factory for creating storage adapter instances (Hexagonal Architecture - Adapter layer)."""

import atexit
import logging

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient

logger = logging.getLogger(__name__)

_storage_instance: StorageInterface | None = None
_cleanup_registered = False


def get_storage() -> StorageInterface:
    """Return singleton storage adapter configured from environment.

    Creates a single long-lived storage instance for the application lifetime.
    Depends on StorageInterface (port), not concrete implementation.

    Returns:
        StorageInterface implementation (currently SupabaseStorageClient)
    """
    global _storage_instance, _cleanup_registered

    if _storage_instance is None:
        # Instantiate concrete adapter (hexagonal architecture - adapter at edge)
        # Core logic depends on StorageInterface port, not this concrete class
        _storage_instance = SupabaseStorageClient()

        # Register cleanup handler on first instantiation
        if not _cleanup_registered:
            atexit.register(_cleanup_storage)
            _cleanup_registered = True
            logger.debug("Registered storage cleanup handler for application shutdown")

    return _storage_instance


def _cleanup_storage() -> None:
    """Cleanup storage connections on application shutdown.

    Called automatically via atexit when the Python interpreter terminates.
    Closes internal HTTP connections to prevent resource leaks.
    """
    global _storage_instance

    if _storage_instance is not None:
        try:
            if hasattr(_storage_instance, 'cleanup'):
                _storage_instance.cleanup()
                logger.info("Storage singleton cleanup completed")
        except Exception as e:
            # Non-blocking: Log but don't crash shutdown
            logger.error(f"Error during storage cleanup: {e}", exc_info=True)
