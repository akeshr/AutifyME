"""Tool call limit middleware for controlling agent execution.

Enforces per-agent tool call limits. Each agent (PM, specialists) gets
independent limits - subagent counts don't pollute parent state.

Usage:
    from autifyme_agents.middleware.execution_limits import create_execution_limits

    middleware = create_execution_limits(tool_call_limit=30)
"""

import json
from collections.abc import Awaitable, Callable
from typing import Any, NotRequired

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ToolCallRequest,
)
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.types import Command


class ToolLimitState(AgentState[Any]):
    """State extension for tool counting."""

    tool_call_count: NotRequired[int]


class ToolCallLimitMiddleware(AgentMiddleware):
    """Simple tool call limit with subagent state isolation.

    Hooks:
    - before_agent: Reset count
    - after_model: Count and enforce limit
    - wrap_tool_call: Filter count from subagent returns
    """

    state_schema = ToolLimitState

    def __init__(self, limit: int) -> None:
        super().__init__()
        self.limit = limit

    @property
    def name(self) -> str:
        return "ToolCallLimitMiddleware"

    def before_agent(self, state: Any, runtime: Any) -> dict[str, Any]:
        """Reset count at agent start."""
        return {"tool_call_count": 0}

    def after_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        """Count tool calls and enforce limit."""
        messages = state.get("messages", [])
        if not messages:
            return None

        # Find last AI message
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.tool_calls:
                break
        else:
            return None

        count = state.get("tool_call_count", 0)
        new_count = count + len(msg.tool_calls)

        if new_count > self.limit:
            error = json.dumps({
                "success": False,
                "error": f"LIMIT_EXCEEDED: Tool limit reached ({new_count}/{self.limit}). "
                         "Synthesize findings and respond with what you have.",
                "error_type": "LIMIT_EXCEEDED",
            })
            # Error messages for blocked calls
            blocked = msg.tool_calls[max(0, self.limit - count):]
            error_msgs: list[ToolMessage | AIMessage] = [
                ToolMessage(content=error, tool_call_id=tc["id"], status="error")
                for tc in blocked
            ]
            error_msgs.append(AIMessage(content=error))
            return {
                "tool_call_count": new_count,
                "jump_to": "end",
                "messages": error_msgs,
            }

        return {"tool_call_count": new_count}

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        """Filter our count from subagent returns."""
        result = handler(request)

        # Only filter task tool (subagent invocation)
        if request.tool_call.get("name") != "task":
            return result

        # Filter our key from Command updates
        if isinstance(result, Command) and isinstance(result.update, dict):
            filtered = {k: v for k, v in result.update.items() if k != "tool_call_count"}
            return Command(
                graph=result.graph,
                update=filtered,
                resume=result.resume,
                goto=result.goto,
            )

        return result

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        """Async version."""
        result = await handler(request)

        if request.tool_call.get("name") != "task":
            return result

        if isinstance(result, Command) and isinstance(result.update, dict):
            filtered = {k: v for k, v in result.update.items() if k != "tool_call_count"}
            return Command(
                graph=result.graph,
                update=filtered,
                resume=result.resume,
                goto=result.goto,
            )

        return result


def create_execution_limits(limit: int = 30) -> list[ToolCallLimitMiddleware]:
    """Create tool limit middleware.

    Args:
        limit: Max tool calls per agent run.

    Returns:
        List with single ToolCallLimitMiddleware.
    """
    return [ToolCallLimitMiddleware(limit=limit)]
