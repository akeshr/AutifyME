"""Gemini resilience handler for blank responses and timeouts.

Gemini has known issues:
1. Occasionally returns valid API responses with blank content
2. Native timeout parameter is not respected (hangs indefinitely)

This module provides a wrapper that:
- Detects blank responses and retries with exponential backoff + jitter
- Enforces request timeout using concurrent.futures (sync) / asyncio.timeout (async)
"""

import asyncio
import logging
import random
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)


class BlankResponseError(Exception):
    """Raised when Gemini returns a blank/empty response.

    This is a known Gemini bug where the model occasionally returns valid
    responses with empty content. Retry typically resolves the issue.
    """

    pass


class GeminiTimeoutError(Exception):
    """Raised when Gemini request times out.

    Gemini's native timeout parameter is broken (doesn't fail fast).
    This error is raised when our enforced timeout is exceeded.
    """

    pass


class GeminiWithRetry(ChatGoogleGenerativeAI):
    """ChatGoogleGenerativeAI with automatic retry on blank responses and enforced timeout.

    Gemini has known issues:
    1. Occasionally returns valid API responses with blank content
    2. Native timeout parameter is broken (doesn't fail fast)

    This wrapper:
    - Detects blank responses and retries with exponential backoff + jitter
    - Enforces request timeout since native timeout is unreliable
    - Maintains BaseChatModel interface for DeepAgents/LangChain compatibility

    Attributes:
        max_retries: Maximum retry attempts (default: 3)
        retry_base_delay: Base delay in seconds for exponential backoff (default: 1.0)
        request_timeout: Enforced timeout per request in seconds (default: 120.0)
    """

    max_retries: int = 3
    retry_base_delay: float = 1.0
    request_timeout: float = 120.0

    def _is_blank_response(self, message: AIMessage) -> bool:
        """Check if response is blank/empty.

        A response is considered VALID (not blank) if ANY of these are true:
        - Has tool_calls (primary format)
        - Has tool_calls in additional_kwargs (legacy format)
        - Has function_call in additional_kwargs (older format)
        - Has non-empty text content
        - Has multimodal content blocks (images, audio, etc.)

        A response is BLANK only if:
        - No tool calls AND no meaningful content

        Args:
            message: AI message to check

        Returns:
            True if response is blank, False otherwise
        """
        # Check 1: Tool calls (primary format) - valid response
        if message.tool_calls:
            return False

        # Check 2: Tool calls in additional_kwargs (legacy format) - valid response
        additional_kwargs = getattr(message, "additional_kwargs", {}) or {}
        if additional_kwargs.get("tool_calls"):
            return False

        # Check 3: Function call (older format) - valid response
        if additional_kwargs.get("function_call"):
            return False

        # Check 4: Content validation
        content = message.content

        # Empty content with no tool calls = blank
        if not content:
            return True

        # String content
        if isinstance(content, str):
            return not content.strip()

        # List content (multimodal format) - content is list at this point
        if len(content) == 0:
            return True

        # Check for any meaningful content in blocks
        for block in content:
            # String block with content
            if isinstance(block, str) and block.strip():
                return False

            # Dict block - check for various content types
            if isinstance(block, dict):
                # Text content
                if block.get("text", "").strip():
                    return False
                # Image content (base64 or URL)
                if block.get("image_url") or block.get("image"):
                    return False
                # Audio content
                if block.get("audio") or block.get("audio_url"):
                    return False
                # Any other type field indicates content
                if block.get("type") and block.get("type") != "text":
                    return False

        # All blocks were empty
        return True

    def _get_retry_delay(self, attempt: int) -> float:
        """Calculate retry delay with exponential backoff + jitter.

        Args:
            attempt: Current attempt number (1-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential backoff: base * 2^(attempt-1)
        delay: float = self.retry_base_delay * (2 ** (attempt - 1))
        # Add jitter (0-50% of delay)
        jitter: float = delay * random.uniform(0, 0.5)
        return delay + jitter

    def _invoke_with_timeout(
        self,
        input: Any,
        config: RunnableConfig | None,
        **kwargs: Any,
    ) -> AIMessage:
        """Execute parent invoke with enforced timeout.

        Uses ThreadPoolExecutor to enforce timeout since Gemini's native
        timeout parameter is broken.

        Args:
            input: Input to the model
            config: Runnable configuration
            **kwargs: Additional arguments

        Returns:
            AI message from parent invoke

        Raises:
            GeminiTimeoutError: If request exceeds timeout
        """
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(super().invoke, input, config, **kwargs)
            try:
                return future.result(timeout=self.request_timeout)
            except FuturesTimeoutError:
                raise GeminiTimeoutError(
                    f"Gemini request timed out after {self.request_timeout}s"
                ) from None

    def invoke(
        self,
        input: Any,
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> AIMessage:
        """Invoke with automatic retry on blank responses and timeouts.

        Args:
            input: Input to the model
            config: Runnable configuration
            **kwargs: Additional arguments

        Returns:
            Non-blank AI message

        Raises:
            BlankResponseError: If all retry attempts return blank responses
            GeminiTimeoutError: If all retry attempts time out
        """
        import time

        last_error: BlankResponseError | GeminiTimeoutError | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                result = self._invoke_with_timeout(input, config, **kwargs)

                if not self._is_blank_response(result):
                    if attempt > 1:
                        logger.info(
                            f"Gemini recovered on attempt {attempt}",
                            extra={"attempt": attempt, "model": self.model},
                        )
                    return result

                last_error = BlankResponseError(
                    f"Gemini returned blank response on attempt {attempt}/{self.max_retries}"
                )
                logger.warning(
                    f"Gemini blank response detected, attempt {attempt}/{self.max_retries}",
                    extra={"attempt": attempt, "max_retries": self.max_retries, "model": self.model},
                )

            except GeminiTimeoutError as e:
                last_error = e
                logger.warning(
                    f"Gemini timeout on attempt {attempt}/{self.max_retries}",
                    extra={
                        "attempt": attempt,
                        "max_retries": self.max_retries,
                        "timeout": self.request_timeout,
                        "model": self.model,
                    },
                )

            if attempt < self.max_retries:
                delay = self._get_retry_delay(attempt)
                logger.debug(f"Retrying in {delay:.2f}s", extra={"delay": delay})
                time.sleep(delay)

        logger.error(
            f"Gemini failed after {self.max_retries} attempts",
            extra={"max_retries": self.max_retries, "model": self.model, "last_error": str(last_error)},
        )
        raise last_error  # type: ignore[misc]

    async def _ainvoke_with_timeout(
        self,
        input: Any,
        config: RunnableConfig | None,
        **kwargs: Any,
    ) -> AIMessage:
        """Execute parent ainvoke with enforced timeout.

        Uses asyncio.timeout (Python 3.11+) to enforce timeout since
        Gemini's native timeout parameter is broken.

        Args:
            input: Input to the model
            config: Runnable configuration
            **kwargs: Additional arguments

        Returns:
            AI message from parent ainvoke

        Raises:
            GeminiTimeoutError: If request exceeds timeout
        """
        try:
            async with asyncio.timeout(self.request_timeout):
                return await super().ainvoke(input, config, **kwargs)
        except TimeoutError:
            raise GeminiTimeoutError(
                f"Gemini request timed out after {self.request_timeout}s"
            ) from None

    async def ainvoke(
        self,
        input: Any,
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> AIMessage:
        """Async invoke with automatic retry on blank responses and timeouts.

        Args:
            input: Input to the model
            config: Runnable configuration
            **kwargs: Additional arguments

        Returns:
            Non-blank AI message

        Raises:
            BlankResponseError: If all retry attempts return blank responses
            GeminiTimeoutError: If all retry attempts time out
        """
        last_error: BlankResponseError | GeminiTimeoutError | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                result = await self._ainvoke_with_timeout(input, config, **kwargs)

                if not self._is_blank_response(result):
                    if attempt > 1:
                        logger.info(
                            f"Gemini recovered on attempt {attempt}",
                            extra={"attempt": attempt, "model": self.model},
                        )
                    return result

                last_error = BlankResponseError(
                    f"Gemini returned blank response on attempt {attempt}/{self.max_retries}"
                )
                logger.warning(
                    f"Gemini blank response detected, attempt {attempt}/{self.max_retries}",
                    extra={"attempt": attempt, "max_retries": self.max_retries, "model": self.model},
                )

            except GeminiTimeoutError as e:
                last_error = e
                logger.warning(
                    f"Gemini timeout on attempt {attempt}/{self.max_retries}",
                    extra={
                        "attempt": attempt,
                        "max_retries": self.max_retries,
                        "timeout": self.request_timeout,
                        "model": self.model,
                    },
                )

            if attempt < self.max_retries:
                delay = self._get_retry_delay(attempt)
                logger.debug(f"Retrying in {delay:.2f}s", extra={"delay": delay})
                await asyncio.sleep(delay)

        logger.error(
            f"Gemini failed after {self.max_retries} attempts",
            extra={"max_retries": self.max_retries, "model": self.model, "last_error": str(last_error)},
        )
        raise last_error  # type: ignore[misc]
