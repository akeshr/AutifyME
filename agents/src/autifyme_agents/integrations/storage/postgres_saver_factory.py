"""Factory for creating and configuring the LangGraph PostgresSaver."""

from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy.ext.asyncio import create_async_engine

from autifyme_agents.core.config import settings


def get_checkpointer() -> PostgresSaver:
    """
    Creates and returns a PostgresSaver instance for checkpointing agent state.
    
    This checkpointer connects to the Supabase Postgres database and allows
    LangGraph agents to persist their state, enabling resilience and long-running,
    interruptible workflows.

    Returns:
        An instance of PostgresSaver configured with the application's database URL.
    """
    # Create an async SQLAlchemy engine
    engine = create_async_engine(settings.DATABASE_URL.get_secret_value())
    
    # PostgresSaver can be used to save all steps in the graph
    return PostgresSaver(engine)
