"""Runtime context schemas for type-safe agent invocation."""

from __future__ import annotations

from pydantic import BaseModel

from autifyme_agents.core.ports import StorageInterface


class AgentContext(BaseModel):
    """Type-safe runtime context for all agents.

    Replaces config["configurable"] pattern with Pydantic-validated context
    for IDE support, type checking, and clearer dependency injection.
    """

    class Config:
        arbitrary_types_allowed = True

    thread_id: str
    company_id: str
    storage: StorageInterface
