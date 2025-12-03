"""Factory for creating and configuring the LangGraph PostgresStore for long-term memory."""

import atexit
import contextlib

from langgraph.store.postgres import PostgresStore

from autifyme_agents.core.config import settings

_store_instance = None
_store_cm = None


def _cleanup_store() -> None:
    """Clean up PostgresStore context manager on process exit."""
    global _store_cm, _store_instance
    if _store_cm is not None:
        # Suppress errors during cleanup - process is exiting anyway
        with contextlib.suppress(Exception):
            _store_cm.__exit__(None, None, None)
        _store_cm = None
        _store_instance = None


def get_store(setup: bool = False) -> PostgresStore:
    """Return a singleton PostgresStore configured from the environment.

    Creates a single long-lived store instance for the application lifetime.
    PostgresStore provides persistent cross-session memory for agents.

    Args:
        setup: When True, runs `store.setup()` before returning to ensure
            migrations are applied. Should only be needed once per environment.

    Returns:
        PostgresStore instance configured with DATABASE_URL from settings.
    """
    global _store_instance, _store_cm

    if _store_instance is None:
        # from_conn_string returns context manager, enter it once for app lifetime
        _store_cm = PostgresStore.from_conn_string(settings.DATABASE_URL)
        _store_instance = _store_cm.__enter__()

        # Register cleanup handler to properly close connections on exit
        atexit.register(_cleanup_store)

        if setup:
            _store_instance.setup()

    return _store_instance
