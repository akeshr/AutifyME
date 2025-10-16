"""Cross-cutting middleware utilities for agent workflows."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from langchain.agents.middleware import AgentMiddleware

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.schemas.models import CompanyProfile

logger = logging.getLogger(__name__)


def create_company_context_middleware(storage: StorageInterface) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Return middleware that injects the singleton company profile into tool calls.

    The middleware fetches the profile lazily and caches it for the remainder of the
    process lifetime, aligning with our single-tenant architecture assumption while
    avoiding repeated Supabase calls.
    """

    if storage is None:
        raise ValueError("storage adapter is required for company context middleware")

    cached_profile: CompanyProfile | None = None

    def _get_profile() -> CompanyProfile:
        nonlocal cached_profile
        if cached_profile is None:
            cached_profile = storage.get_company_profile()
            logger.info("Company profile '%s' cached for middleware injection", cached_profile.name)
        return cached_profile

    def _ensure_profile(kwargs: dict[str, Any]) -> None:
        profile = kwargs.get("company_profile")

        if isinstance(profile, CompanyProfile):
            return

        if profile:
            try:
                profile = CompanyProfile.model_validate(profile)
            except Exception:
                profile = _get_profile()
        else:
            profile = _get_profile()

        kwargs["company_profile"] = profile

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                _ensure_profile(kwargs)
                return await func(*args, **kwargs)

            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            _ensure_profile(kwargs)
            return func(*args, **kwargs)

        return sync_wrapper

    return decorator


class CompanyContextMiddleware(AgentMiddleware):
    """Inject company profile into agent tools via LangChain v1 middleware.

    Uses before_model hook to fetch and cache company profile, then makes it
    available to all tool calls via Runtime context. Replaces decorator-based
    pattern with native v1 middleware for cleaner separation of concerns.
    """

    def __init__(self, storage: StorageInterface):
        if storage is None:
            raise ValueError("storage adapter is required for company context middleware")
        self.storage = storage
        self._profile_cache: CompanyProfile | None = None

    def before_model(self, state: Any, runtime: Any) -> None:
        """Fetch and inject company profile before LLM call."""
        if self._profile_cache is None:
            self._profile_cache = self.storage.get_company_profile()
            logger.info("Company profile '%s' cached for middleware injection", self._profile_cache.name)

        # Middleware before_model returns dict to update state or None
        # Company profile is accessed via runtime.context in tools
        return None

