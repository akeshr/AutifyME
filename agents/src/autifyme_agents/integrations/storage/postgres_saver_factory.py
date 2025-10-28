"""Factory for creating and configuring the LangGraph PostgresSaver."""

import logging

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from autifyme_agents.core.config import settings

logger = logging.getLogger(__name__)

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


async def _is_connection_healthy(checkpointer: AsyncPostgresSaver) -> bool:
    """Check if checkpointer connection is healthy.

    Args:
        checkpointer: AsyncPostgresSaver instance to check

    Returns:
        True if connection is healthy, False otherwise
    """
    try:
        # Try to get a cursor - this will fail if connection is closed
        async with checkpointer._cursor() as cur:
            await cur.execute("SELECT 1")
        return True
    except Exception as e:
        logger.warning(f"Checkpointer connection health check failed: {e}")
        return False


async def get_async_checkpointer(setup: bool = False, force_reconnect: bool = False) -> AsyncPostgresSaver:
    """Return AsyncPostgresSaver with connection health checks for serverless environments.

    In serverless environments (AWS Lambda), connections can be closed between invocations.
    This function checks connection health and recreates if necessary.

    Args:
        setup: When True, runs `await checkpointer.setup()` before returning
        force_reconnect: Force recreation of checkpointer instance

    Returns:
        AsyncPostgresSaver instance configured with DATABASE_URL from settings.
    """
    global _async_checkpointer_instance, _async_checkpointer_cm

    # Check if we need to recreate the checkpointer
    should_recreate = (
        _async_checkpointer_instance is None  # Never created
        or force_reconnect  # Forced recreation
        or not await _is_connection_healthy(_async_checkpointer_instance)  # Connection dead
    )

    if should_recreate:
        logger.info("Creating new AsyncPostgresSaver instance")

        # Clean up old instance if exists
        if _async_checkpointer_cm is not None:
            try:
                await _async_checkpointer_cm.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error cleaning up old checkpointer: {e}")

        # Create new instance
        _async_checkpointer_cm = AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL)
        _async_checkpointer_instance = await _async_checkpointer_cm.__aenter__()

        if setup:
            logger.info("Running checkpointer setup (migrations)")
            await _async_checkpointer_instance.setup()

        logger.info("AsyncPostgresSaver instance created successfully")

    return _async_checkpointer_instance
