"""Execution limit middleware for controlling agent iterations.

Provides configurable limits on model calls and tool calls to prevent
runaway agent loops. Each agent configures its own limits based on its role.

Usage:
    from autifyme_agents.middleware.execution_limits import create_execution_limits

    # Simple: uniform limit for all tools (2 middlewares total)
    middleware = create_execution_limits(
        model_call_limit=15,
        tool_call_limit=10,
    )

    # Granular: different limits per tool (N+1 middlewares)
    middleware = create_execution_limits(
        model_call_limit=15,
        tool_limits={"write_data": 5, "read_data": 20},
    )
"""

from typing import Any, Literal

from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware

ExitBehavior = Literal["end", "error"]


def create_execution_limits(
    model_call_limit: int | None = None,
    tool_call_limit: int | None = None,
    tool_limits: dict[str, int] | None = None,
    exit_behavior: ExitBehavior = "end",
) -> list[Any]:
    """Create execution limit middleware.

    Args:
        model_call_limit: Max LLM calls per run.
        tool_call_limit: Uniform limit for ALL tools (single middleware).
        tool_limits: Per-tool limits (creates one middleware per tool).
            Use only when different tools need different limits.
        exit_behavior: "end" (graceful) or "error" (exception).

    Returns:
        List of middleware (typically 1-2 entries).

    Note:
        Prefer tool_call_limit over tool_limits for cleaner traces.
        Only use tool_limits when granular control is needed.
    """
    middleware: list[Any] = []

    if model_call_limit is not None:
        middleware.append(
            ModelCallLimitMiddleware(
                run_limit=model_call_limit,
                exit_behavior=exit_behavior,
            )
        )

    # Uniform tool limit (single middleware for all tools)
    if tool_call_limit is not None:
        middleware.append(
            ToolCallLimitMiddleware(
                run_limit=tool_call_limit,
                exit_behavior=exit_behavior,
            )
        )

    # Per-tool limits (one middleware per tool - use sparingly)
    if tool_limits:
        for tool_name, limit in tool_limits.items():
            middleware.append(
                ToolCallLimitMiddleware(
                    tool_name=tool_name,
                    run_limit=limit,
                    exit_behavior=exit_behavior,
                )
            )

    return middleware
