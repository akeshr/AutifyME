"""Factory for creating and configuring the LangGraph PostgresSaver."""

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from autifyme_agents.core.config import settings

_checkpointer_instance = None
_checkpointer_cm = None
_async_checkpointer_instance = None
_async_checkpointer_cm = None


def get_checkpointer(setup: bool = False) -> PostgresSaver:
    """Return a singleton PostgresSaver configured from the environment.

    Creates a single long-lived checkpointer instance for the application lifetime.
    PostgresSaver manages its own connection pool internally via context manager.

    Args:
        setup: When True, runs `checkpointer.setup()` before returning to ensure
            migrations are applied. Should only be needed once per environment.

    Returns:
        PostgresSaver instance configured with DATABASE_URL from settings.
    """
    global _checkpointer_instance, _checkpointer_cm

    if _checkpointer_instance is None:
        # from_conn_string returns context manager, enter it once for app lifetime
        _checkpointer_cm = PostgresSaver.from_conn_string(settings.DATABASE_URL)
        _checkpointer_instance = _checkpointer_cm.__enter__()
        if setup:
            _checkpointer_instance.setup()

    return _checkpointer_instance


async def get_async_checkpointer(setup: bool = False) -> AsyncPostgresSaver:
    """Return a singleton AsyncPostgresSaver configured from the environment.

    Creates a single long-lived async checkpointer instance for the application lifetime.
    AsyncPostgresSaver manages its own connection pool internally via async context manager.

    Args:
        setup: When True, runs `await checkpointer.setup()` before returning to ensure
            migrations are applied. Should only be needed once per environment.

    Returns:
        AsyncPostgresSaver instance configured with DATABASE_URL from settings.
    """
    global _async_checkpointer_instance, _async_checkpointer_cm

    if _async_checkpointer_instance is None:
        # from_conn_string returns async context manager, enter it once for app lifetime
        _async_checkpointer_cm = AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL)
        _async_checkpointer_instance = await _async_checkpointer_cm.__aenter__()
        if setup:
            await _async_checkpointer_instance.setup()

    return _async_checkpointer_instance
