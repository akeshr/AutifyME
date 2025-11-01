"""Custom ChatOpenAI wrapper that enforces strict mode for tool binding.

When using OpenAI's response_format (structured outputs), all tool schemas must
have strict validation enabled. This wrapper ensures bind_tools always uses strict=True.
"""

from typing import Any, Sequence

from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI


class StrictChatOpenAI(ChatOpenAI):
    """ChatOpenAI that automatically enables strict mode when binding tools.

    This is required when using response_format (structured outputs) with OpenAI,
    as it enforces strict schema validation on all tool parameters.

    Usage:
        model = StrictChatOpenAI(model="gpt-4o-mini", temperature=0.2)
        # When DeepAgents or other code calls model.bind_tools(),
        # it will automatically use strict=True
    """

    def bind_tools(
        self,
        tools: Sequence[BaseTool | dict[str, Any]],
        *,
        tool_choice: Any | None = None,
        strict: bool | None = None,
        **kwargs: Any,
    ) -> "StrictChatOpenAI":
        """Override bind_tools to always use strict=True.

        Args:
            tools: List of tools to bind
            tool_choice: Optional tool choice parameter
            strict: Strict mode (forced to True if None)
            **kwargs: Additional arguments

        Returns:
            Bound model instance with strict=True
        """
        # Force strict=True unless explicitly set to False
        if strict is None:
            strict = True

        return super().bind_tools(
            tools,
            tool_choice=tool_choice,
            strict=strict,
            **kwargs
        )
