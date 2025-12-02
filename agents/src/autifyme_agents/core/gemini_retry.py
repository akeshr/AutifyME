"""Gemini blank response retry handler.

Gemini occasionally returns valid API responses with blank content.
This module provides a wrapper that detects blank responses and retries
with exponential backoff + jitter.
"""

import asyncio
import logging
import random
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


class GeminiWithRetry(ChatGoogleGenerativeAI):
    """ChatGoogleGenerativeAI with automatic retry on blank responses.

    Gemini occasionally returns valid API responses with blank content.
    This wrapper detects blank responses and retries with exponential
    backoff + jitter, maintaining the BaseChatModel interface for
    compatibility with DeepAgents and other LangChain components.

    Attributes:
        max_retries: Maximum retry attempts (default: 3)
        retry_base_delay: Base delay in seconds for exponential backoff (default: 1.0)
    """

    max_retries: int = 3
    retry_base_delay: float = 1.0

    def _is_blank_response(self, message: AIMessage) -> bool:
        """Check if response is blank/empty.

        Handles both string content (OpenAI format) and list content
        (Gemini multimodal format).

        Args:
            message: AI message to check

        Returns:
            True if response is blank, False otherwise
        """
        content = message.content
        if not content:
            return True
        if isinstance(content, str) and not content.strip():
            return True
        if isinstance(content, list) and len(content) == 0:
            return True
        # Check for list with only empty text blocks
        if isinstance(content, list):
            has_content = any(
                (isinstance(block, dict) and block.get("text", "").strip())
                or (isinstance(block, str) and block.strip())
                for block in content
            )
            if not has_content:
                return True
        return False

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

    def invoke(
        self,
        input: Any,
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> AIMessage:
        """Invoke with automatic retry on blank responses.

        Args:
            input: Input to the model
            config: Runnable configuration
            **kwargs: Additional arguments

        Returns:
            Non-blank AI message

        Raises:
            BlankResponseError: If all retry attempts return blank responses
        """
        import time

        last_error: BlankResponseError | None = None

        for attempt in range(1, self.max_retries + 1):
            result = super().invoke(input, config, **kwargs)

            if not self._is_blank_response(result):
                if attempt > 1:
                    logger.info(
                        f"Gemini blank response recovered on attempt {attempt}",
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

            if attempt < self.max_retries:
                delay = self._get_retry_delay(attempt)
                logger.debug(f"Retrying in {delay:.2f}s", extra={"delay": delay})
                time.sleep(delay)

        logger.error(
            f"Gemini blank response persisted after {self.max_retries} attempts",
            extra={"max_retries": self.max_retries, "model": self.model},
        )
        raise last_error  # type: ignore[misc]

    async def ainvoke(
        self,
        input: Any,
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> AIMessage:
        """Async invoke with automatic retry on blank responses.

        Args:
            input: Input to the model
            config: Runnable configuration
            **kwargs: Additional arguments

        Returns:
            Non-blank AI message

        Raises:
            BlankResponseError: If all retry attempts return blank responses
        """
        last_error: BlankResponseError | None = None

        for attempt in range(1, self.max_retries + 1):
            result = await super().ainvoke(input, config, **kwargs)

            if not self._is_blank_response(result):
                if attempt > 1:
                    logger.info(
                        f"Gemini blank response recovered on attempt {attempt}",
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

            if attempt < self.max_retries:
                delay = self._get_retry_delay(attempt)
                logger.debug(f"Retrying in {delay:.2f}s", extra={"delay": delay})
                await asyncio.sleep(delay)

        logger.error(
            f"Gemini blank response persisted after {self.max_retries} attempts",
            extra={"max_retries": self.max_retries, "model": self.model},
        )
        raise last_error  # type: ignore[misc]
