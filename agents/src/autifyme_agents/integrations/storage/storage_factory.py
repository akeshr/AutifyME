"""Factory for creating storage adapter instances (Hexagonal Architecture - Adapter layer)."""

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient


_storage_instance: StorageInterface | None = None


def get_storage() -> StorageInterface:
    """Return singleton storage adapter configured from environment.

    Creates a single long-lived storage instance for the application lifetime.
    Depends on StorageInterface (port), not concrete implementation.

    Returns:
        StorageInterface implementation (currently SupabaseStorageClient)
    """
    global _storage_instance

    if _storage_instance is None:
        # Instantiate concrete adapter (hexagonal architecture - adapter at edge)
        # Core logic depends on StorageInterface port, not this concrete class
        _storage_instance = SupabaseStorageClient()

    return _storage_instance
