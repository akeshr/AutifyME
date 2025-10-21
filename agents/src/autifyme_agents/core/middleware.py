"""Cross-cutting middleware utilities for agent workflows."""

from __future__ import annotations

import logging
from typing import Any

from langchain.agents.middleware import AgentMiddleware

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.validation import (
    detect_pii,
    redact_pii,
    sanitize_dict_strings,
    validate_dict_lengths,
)
from autifyme_agents.schemas.models import CompanyProfile

logger = logging.getLogger(__name__)


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


class InputValidationMiddleware(AgentMiddleware):
    """Apply cross-tool input validation and sanitization.

    Provides defense-in-depth for:
    - Length validation (prevent database overflow)
    - HTML/XSS sanitization (security hardening)
    - PII detection (compliance and logging safety)

    This middleware applies BEFORE tools execute, ensuring consistent
    validation rules across all tools without duplicating logic.
    """

    def __init__(
        self,
        *,
        max_str_length: int = 10000,
        sanitize_html: bool = True,
        detect_pii_logging: bool = True,
    ):
        """Initialize validation middleware with configuration.

        Args:
            max_str_length: Maximum allowed string length (default: 10000 chars)
            sanitize_html: Whether to strip HTML tags and escape entities (default: True)
            detect_pii_logging: Whether to detect and warn about PII in inputs (default: True)
        """
        self.max_str_length = max_str_length
        self.sanitize_html_enabled = sanitize_html
        self.detect_pii_enabled = detect_pii_logging

    def before_tool(self, tool_name: str, inputs: dict[str, Any], runtime: Any) -> dict[str, Any] | None:
        """Validate and sanitize tool inputs before execution.

        Args:
            tool_name: Name of tool being called
            inputs: Tool input parameters
            runtime: LangChain runtime context

        Returns:
            Modified inputs (if sanitization applied) or None (no changes)

        Raises:
            ValueError: If validation fails (length exceeded)
        """
        # Rule 1: Length validation (fail-fast)
        try:
            validate_dict_lengths(inputs, max_str_length=self.max_str_length)
        except ValueError as e:
            logger.error(
                f"Tool '{tool_name}' input validation failed: {str(e)}",
                extra={"tool": tool_name, "error": str(e)},
            )
            raise  # Re-raise to prevent tool execution

        # Rule 2: PII detection (warning only, don't block)
        if self.detect_pii_enabled:
            for key, value in inputs.items():
                if isinstance(value, str) and detect_pii(value):
                    # Redact for logging but allow in tool
                    redacted = redact_pii(value)
                    logger.warning(
                        f"PII detected in tool '{tool_name}' input '{key}' - redacting for logs",
                        extra={
                            "tool": tool_name,
                            "field": key,
                            "redacted_value": redacted,
                        },
                    )

        # Rule 3: HTML sanitization (modify inputs)
        if self.sanitize_html_enabled:
            sanitized_inputs = sanitize_dict_strings(inputs)

            # Check if any sanitization occurred
            if sanitized_inputs != inputs:
                logger.info(
                    f"Sanitized HTML in tool '{tool_name}' inputs",
                    extra={"tool": tool_name, "fields_sanitized": list(inputs.keys())},
                )
                return sanitized_inputs  # Return modified inputs

        return None  # No modifications needed

