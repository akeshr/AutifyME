"""Custom ChatOpenAI wrapper that enforces strict mode for tool binding.

When using OpenAI's response_format (structured outputs), all tool schemas must
have strict validation enabled AND additionalProperties: false in parameters.
This wrapper ensures bind_tools always uses strict=True and injects additionalProperties.
"""

from collections.abc import Callable, Sequence
from typing import Any, cast

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.prompt_values import PromptValue
from langchain_core.runnables.base import Runnable, RunnableBinding
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI


class StrictChatOpenAI(ChatOpenAI):
    """ChatOpenAI that automatically enables strict mode when binding tools.

    This is required when using response_format (structured outputs) with OpenAI,
    which enforces strict schema validation on all tool parameters.

    OpenAI Requirement: When using structured outputs (response_format), ALL schemas
    in the request must have 'additionalProperties: false' explicitly set in nested
    objects. The 'strict: true' flag alone is insufficient.

    Usage:
        model = StrictChatOpenAI(model="gpt-4o-mini", temperature=0.2)
        # When DeepAgents or other code calls model.bind_tools(),
        # it will automatically use strict=True and inject additionalProperties
    """

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Callable[..., Any] | BaseTool],
        *,
        tool_choice: dict[Any, Any] | str | bool | None = None,
        strict: bool | None = None,
        parallel_tool_calls: bool | None = None,
        **kwargs: Any,
    ) -> Runnable[PromptValue | str | Sequence[BaseMessage | list[str] | tuple[str, str] | str | dict[str, Any]], AIMessage]:
        """Override bind_tools to enforce strict mode and inject additionalProperties.

        Args:
            tools: List of tools to bind
            tool_choice: Optional tool choice parameter
            strict: Strict mode (forced to True if None)
            parallel_tool_calls: Whether to allow parallel tool calls
            **kwargs: Additional arguments

        Returns:
            Bound model instance with strict=True and proper schemas
        """
        # Force strict=True unless explicitly set to False
        if strict is None:
            strict = True

        # Call parent to get bound model with tools converted to OpenAI format
        bound_model = super().bind_tools(
            tools,
            tool_choice=tool_choice,
            strict=strict,
            parallel_tool_calls=parallel_tool_calls,
            **kwargs
        )

        # Cast to RunnableBinding to access kwargs (mypy type stubs incomplete)
        bound_binding = cast(RunnableBinding[Any, Any], bound_model)

        # Inject additionalProperties: false into all tool schemas
        # This is required by OpenAI when using response_format
        if "tools" in bound_binding.kwargs:
            for tool_def in bound_binding.kwargs["tools"]:
                if "function" in tool_def and "parameters" in tool_def["function"]:
                    params = tool_def["function"]["parameters"]
                    # Inject additionalProperties: false if not present
                    if "additionalProperties" not in params:
                        params["additionalProperties"] = False
                    # Also ensure nested objects have it
                    if "properties" in params:
                        self._inject_additional_properties(params["properties"])

        return bound_model

    def _inject_additional_properties(self, properties: dict[str, Any]) -> None:
        """Recursively inject additionalProperties: false into nested objects.

        Args:
            properties: Dictionary of property schemas to process
        """
        for prop_schema in properties.values():
            if isinstance(prop_schema, dict):
                # If this is an object type, ensure additionalProperties: false
                if prop_schema.get("type") == "object":
                    if "additionalProperties" not in prop_schema:
                        prop_schema["additionalProperties"] = False
                    # Recurse into nested properties
                    if "properties" in prop_schema:
                        self._inject_additional_properties(prop_schema["properties"])
                # Handle arrays of objects
                elif prop_schema.get("type") == "array" and "items" in prop_schema:
                    items = prop_schema["items"]
                    if isinstance(items, dict) and items.get("type") == "object":
                        if "additionalProperties" not in items:
                            items["additionalProperties"] = False
                        if "properties" in items:
                            self._inject_additional_properties(items["properties"])
