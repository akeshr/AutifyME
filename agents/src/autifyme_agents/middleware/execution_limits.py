"""Execution limit middleware for controlling agent iterations.

Provides configurable limits on model calls and tool calls to prevent
runaway agent loops. Returns structured errors matching tool_error_handler
pattern so agents can reason about limits consistently.

Usage:
    from autifyme_agents.middleware.execution_limits import create_execution_limits

    middleware = create_execution_limits(
        model_call_limit=15,
        tool_call_limit=20,
    )
"""

import json
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage


def _build_structured_error(
    limit_type: str,
    current: int,
    limit: int,
    tool_name: str | None = None,
) -> str:
    """Build structured error matching tool_error_handler pattern."""
    if tool_name:
        context = f"Tool '{tool_name}' call limit"
    elif limit_type == "model":
        context = "Model call limit"
    else:
        context = "Total tool call limit"

    error_response = {
        "success": False,
        "error": f"LIMIT_EXCEEDED: {context} reached ({current}/{limit}).\n\n"
                 f"Agent Action: Prioritize remaining work. Synthesize findings and "
                 f"provide final response with what you have. Flag any incomplete items.",
        "error_type": "LIMIT_EXCEEDED",
        "limit_type": limit_type,
        "current": current,
        "limit": limit,
    }
    if tool_name:
        error_response["tool_name"] = tool_name

    return json.dumps(error_response, indent=2)


class ModelCallLimitMiddleware:
    """Model call limit with structured error responses.

    Single hook (before_model) - checks limit and increments count.
    """

    def __init__(self, run_limit: int) -> None:
        self.run_limit = run_limit

    @property
    def name(self) -> str:
        return "ModelCallLimitMiddleware"

    def before_model(
        self,
        state: Any,
        runtime: Any,
    ) -> dict[str, Any] | None:
        """Check limit before model call. Increment count if proceeding."""
        run_count = state.get("run_model_call_count", 0)

        # Check if limit reached
        if run_count >= self.run_limit:
            error_content = _build_structured_error(
                limit_type="model",
                current=run_count,
                limit=self.run_limit,
            )
            return {
                "jump_to": "end",
                "messages": [AIMessage(content=error_content)],
            }

        # Increment count and proceed
        return {"run_model_call_count": run_count + 1}


class ToolCallLimitMiddleware:
    """Tool call limit with structured error responses.

    Single hook (after_model) - counts tool calls and enforces limit.
    """

    def __init__(self, run_limit: int, tool_name: str | None = None) -> None:
        self.run_limit = run_limit
        self.tool_name = tool_name

    @property
    def name(self) -> str:
        if self.tool_name:
            return f"ToolCallLimitMiddleware[{self.tool_name}]"
        return "ToolCallLimitMiddleware"

    def after_model(
        self,
        state: Any,
        runtime: Any,
    ) -> dict[str, Any] | None:
        """Count tool calls after model response. Block if limit exceeded."""
        messages = state.get("messages", [])
        if not messages:
            return None

        # Find last AI message
        last_ai_message = None
        for message in reversed(messages):
            if isinstance(message, AIMessage):
                last_ai_message = message
                break

        if not last_ai_message or not last_ai_message.tool_calls:
            return None

        # Get count key and current counts
        count_key = self.tool_name if self.tool_name else "__all__"
        run_counts = state.get("run_tool_call_count", {}).copy()
        current_run_count = run_counts.get(count_key, 0)

        # Count matching tool calls
        if self.tool_name:
            matching_calls = [tc for tc in last_ai_message.tool_calls if tc["name"] == self.tool_name]
        else:
            matching_calls = last_ai_message.tool_calls

        if not matching_calls:
            return None

        new_count = current_run_count + len(matching_calls)

        # Check if limit exceeded
        if new_count > self.run_limit:
            error_content = _build_structured_error(
                limit_type="tool",
                current=new_count,
                limit=self.run_limit,
                tool_name=self.tool_name,
            )

            # Create error tool messages for blocked calls
            blocked_calls = matching_calls[max(0, self.run_limit - current_run_count):]
            error_messages: list[ToolMessage | AIMessage] = [
                ToolMessage(
                    content=error_content,
                    tool_call_id=tc["id"],
                    name=tc.get("name"),
                    status="error",
                )
                for tc in blocked_calls
            ]

            # Add final AI message for graceful termination
            error_messages.append(AIMessage(content=error_content))

            run_counts[count_key] = new_count
            return {
                "run_tool_call_count": run_counts,
                "jump_to": "end",
                "messages": error_messages,
            }

        # Update count, no limit hit
        run_counts[count_key] = new_count
        return {"run_tool_call_count": run_counts}


def create_execution_limits(
    model_call_limit: int | None = None,
    tool_call_limit: int | None = None,
    tool_limits: dict[str, int] | None = None,
) -> list[Any]:
    """Create execution limit middleware with structured error responses.

    Args:
        model_call_limit: Max LLM calls per run.
        tool_call_limit: Uniform limit for ALL tools (single middleware).
        tool_limits: Per-tool limits (creates one middleware per tool).

    Returns:
        List of middleware (typically 1-2 entries).

    Error Response Format (matches tool_error_handler pattern):
        {
            "success": false,
            "error": "LIMIT_EXCEEDED: ... Agent Action: ...",
            "error_type": "LIMIT_EXCEEDED",
            "limit_type": "model" | "tool",
            "current": 15,
            "limit": 15
        }
    """
    middleware: list[Any] = []

    if model_call_limit is not None:
        middleware.append(ModelCallLimitMiddleware(run_limit=model_call_limit))

    if tool_call_limit is not None:
        middleware.append(ToolCallLimitMiddleware(run_limit=tool_call_limit))

    if tool_limits:
        for tool_name, limit in tool_limits.items():
            middleware.append(ToolCallLimitMiddleware(run_limit=limit, tool_name=tool_name))

    return middleware
