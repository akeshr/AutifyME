"""Middleware layer for cross-cutting concerns."""

from autifyme_agents.middleware.context_middleware import load_base_context
from autifyme_agents.middleware.multimodal_injection import (
    MultimodalInjectionMiddleware,
)

__all__ = ["load_base_context", "MultimodalInjectionMiddleware"]
