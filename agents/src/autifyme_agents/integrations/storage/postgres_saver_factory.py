"""Factory for creating and configuring the LangGraph PostgresSaver."""

from contextlib import contextmanager

from langgraph.checkpoint.postgres import PostgresSaver

from autifyme_agents.core.config import settings


@contextmanager
def get_checkpointer(setup: bool = False):
    """Yield a PostgresSaver configured from the environment.

    Args:
        setup: When True, runs `checkpointer.setup()` before yielding to ensure
            migrations are applied. Should only be needed once per environment.
    """
    with PostgresSaver.from_conn_string(settings.DATABASE_URL) as saver:
        if setup:
            saver.setup()
        yield saver
