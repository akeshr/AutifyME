"""
Context management strategies for PM and agents.

Provides custom ContextEdit implementations for intelligent context pruning.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from langchain_core.messages import BaseMessage, ToolMessage


class TokenCounter(Protocol):
    """Protocol for counting tokens in messages."""

    def __call__(self, messages: Sequence[BaseMessage]) -> int:
        """Count tokens in message sequence."""
        ...


class ContextEdit(Protocol):
    """Protocol for context editing strategies."""

    def apply(
        self,
        messages: list[BaseMessage],
        *,
        count_tokens: TokenCounter,
    ) -> None:
        """Apply edit to messages in place."""
        ...


@dataclass
class TruncateToolResultsEdit:
    """
    Truncate tool results to preserve context while saving tokens.

    Unlike ClearToolUsesEdit which replaces results with placeholders,
    this strategy preserves the beginning of each result. This is more
    intelligent for PM workflows where:
    - Specialist results often have summaries at the top
    - PM reasoning references specific details from results
    - Complete loss of context forces re-calling specialists

    The truncation preserves enough context for PM to remember what
    happened while achieving significant token savings.
    """

    trigger: int = 30000
    """Token count that triggers truncation."""

    max_result_length: int = 500
    """Maximum characters to preserve per tool result."""

    keep_recent: int = 3
    """Number of most recent results to NOT truncate."""

    exclude_tools: tuple[str, ...] = ()
    """Tool names to never truncate."""

    truncation_marker: str = "\n\n...[truncated for context management]"
    """Marker appended to truncated results."""

    def apply(
        self,
        messages: list[BaseMessage],
        *,
        count_tokens: TokenCounter,
    ) -> None:
        """Truncate old tool results to save tokens."""
        token_count = count_tokens(messages)
        if token_count < self.trigger:
            return

        # Find all tool messages
        tool_messages = [
            (idx, msg)
            for idx, msg in enumerate(messages)
            if isinstance(msg, ToolMessage)
        ]

        # Exclude recent messages from truncation
        if self.keep_recent >= len(tool_messages):
            return

        candidates = tool_messages[: -self.keep_recent] if self.keep_recent > 0 else tool_messages

        # Truncate candidates
        excluded = set(self.exclude_tools)
        for _idx, msg in candidates:
            # Skip if already truncated or excluded
            if (
                msg.name in excluded
                or self.truncation_marker in msg.content
            ):
                continue

            # Truncate if over max length
            if isinstance(msg.content, str) and len(msg.content) > self.max_result_length:
                msg.content = (
                    msg.content[: self.max_result_length] + self.truncation_marker
                )


@dataclass
class GraduatedTruncationEdit:
    """
    Multi-stage truncation with progressive aggressiveness.

    Applies different truncation lengths based on token pressure:
    - Light truncation when first triggered
    - Aggressive truncation at higher token counts
    - Prevents hitting summarization threshold
    """

    trigger_light: int = 30000
    """Token count for light truncation."""

    trigger_aggressive: int = 60000
    """Token count for aggressive truncation."""

    max_length_light: int = 1000
    """Max chars per result in light mode."""

    max_length_aggressive: int = 300
    """Max chars per result in aggressive mode."""

    keep_recent: int = 3
    """Number of recent results to preserve fully."""

    exclude_tools: tuple[str, ...] = ()
    """Tool names to never truncate."""

    def apply(
        self,
        messages: list[BaseMessage],
        *,
        count_tokens: TokenCounter,
    ) -> None:
        """Apply graduated truncation based on token count."""
        token_count = count_tokens(messages)

        if token_count < self.trigger_light:
            return

        # Determine truncation aggressiveness
        if token_count >= self.trigger_aggressive:
            max_length = self.max_length_aggressive
            marker = "\n\n...[aggressively truncated]"
        else:
            max_length = self.max_length_light
            marker = "\n\n...[truncated]"

        # Find tool messages to truncate
        tool_messages = [
            (idx, msg)
            for idx, msg in enumerate(messages)
            if isinstance(msg, ToolMessage)
        ]

        if self.keep_recent >= len(tool_messages):
            return

        candidates = tool_messages[: -self.keep_recent] if self.keep_recent > 0 else tool_messages

        # Apply truncation
        excluded = set(self.exclude_tools)
        for _idx, msg in candidates:
            if msg.name in excluded:
                continue

            # Truncate if needed
            if isinstance(msg.content, str) and len(msg.content) > max_length:
                # Check if already truncated - adjust if needed
                if "[truncated" in msg.content:
                    # Already truncated, make more aggressive
                    base_content = msg.content.split("\n\n...[")[0]
                    if len(base_content) > max_length:
                        msg.content = base_content[:max_length] + marker
                else:
                    # First truncation
                    msg.content = msg.content[:max_length] + marker


@dataclass
class HybridTruncateThenClearEdit:
    """
    Hybrid strategy: truncate first, clear if still over budget.

    Two-phase approach:
    1. Truncate old results to preserve partial context
    2. If still over budget, clear oldest results completely

    Balances context preservation with aggressive token savings.
    """

    trigger_truncate: int = 30000
    """Token count to start truncation."""

    trigger_clear: int = 80000
    """Token count to start clearing (after truncation)."""

    max_truncate_length: int = 500
    """Max chars when truncating."""

    keep_recent_truncate: int = 3
    """Recent results to skip in truncation phase."""

    keep_recent_clear: int = 5
    """Recent results to skip in clearing phase."""

    exclude_tools: tuple[str, ...] = ()
    """Tool names to never modify."""

    def apply(
        self,
        messages: list[BaseMessage],
        *,
        count_tokens: TokenCounter,
    ) -> None:
        """Apply hybrid truncate-then-clear strategy."""
        token_count = count_tokens(messages)

        # Phase 1: Truncation
        if token_count >= self.trigger_truncate:
            self._truncate_phase(messages, count_tokens)

        # Phase 2: Clearing (only if still over threshold)
        token_count = count_tokens(messages)
        if token_count >= self.trigger_clear:
            self._clear_phase(messages, count_tokens)

    def _truncate_phase(
        self,
        messages: list[BaseMessage],
        count_tokens: TokenCounter,
    ) -> None:
        """Truncate old tool results."""
        tool_messages = [
            (idx, msg)
            for idx, msg in enumerate(messages)
            if isinstance(msg, ToolMessage)
        ]

        if self.keep_recent_truncate >= len(tool_messages):
            return

        candidates = (
            tool_messages[: -self.keep_recent_truncate]
            if self.keep_recent_truncate > 0
            else tool_messages
        )

        excluded = set(self.exclude_tools)
        for _idx, msg in candidates:
            if msg.name in excluded or "[truncated]" in msg.content:
                continue

            if isinstance(msg.content, str) and len(msg.content) > self.max_truncate_length:
                msg.content = (
                    msg.content[: self.max_truncate_length]
                    + "\n\n...[truncated for context management]"
                )

    def _clear_phase(
        self,
        messages: list[BaseMessage],
        count_tokens: TokenCounter,
    ) -> None:
        """Clear oldest tool results completely."""
        tool_messages = [
            (idx, msg)
            for idx, msg in enumerate(messages)
            if isinstance(msg, ToolMessage)
        ]

        if self.keep_recent_clear >= len(tool_messages):
            return

        candidates = (
            tool_messages[: -self.keep_recent_clear]
            if self.keep_recent_clear > 0
            else tool_messages
        )

        excluded = set(self.exclude_tools)
        for _idx, msg in candidates:
            if msg.name in excluded or msg.content == "[cleared]":
                continue

            msg.content = "[cleared]"
