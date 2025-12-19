"""Execution limit middleware for controlling agent iterations.

Provides configurable limits on model calls and tool calls to prevent
runaway agent loops. Each agent configures its own limits based on its role.

Usage:
    from autifyme_agents.middleware.execution_limits import create_execution_limits

    # PM - orchestrator with task tool limit
    pm_middleware = create_execution_limits(
        model_call_limit=100,
        tool_limits={"task": 15},
    )

    # Catalog specialist - granular CRUD limits
    spec_middleware = create_execution_limits(
        model_call_limit=50,
        tool_limits={
            "write_data": 15,
            "read_data": 100,
        },
    )

    # Analyst - tight limits for research
    analyst_middleware = create_execution_limits(
        model_call_limit=30,
        total_tool_limit=50,
    )
"""

from typing import Any, Literal

from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware

ExitBehavior = Literal["end", "error"]


def create_execution_limits(
    model_call_limit: int | None = None,
    tool_limits: dict[str, int] | None = None,
    total_tool_limit: int | None = None,
    exit_behavior: ExitBehavior = "end",
) -> list[Any]:
    """Create execution limit middleware with granular per-tool control.

    Args:
        model_call_limit: Max LLM calls per run. None to disable.
        tool_limits: Dict mapping tool_name -> max_calls. Each tool gets its
            own limit. Example: {"write_data": 10, "task": 15}
        total_tool_limit: Global tool call limit (applies to ALL tools,
            including those in tool_limits). None to disable.
        exit_behavior: How to handle limit exceeded:
            - "end": Graceful termination with message (default)
            - "error": Raise exception

    Returns:
        List of middleware to add to agent's middleware stack.

    Examples:
        # PM - limit specialist spawns
        create_execution_limits(
            model_call_limit=100,
            tool_limits={"task": 15},
        )

        # Specialist - limit writes, generous reads
        create_execution_limits(
            model_call_limit=50,
            tool_limits={
                "write_data": 15,
                "read_data": 100,
                "image_studio": 10,
            },
        )

        # Analyst - simple global limits
        create_execution_limits(
            model_call_limit=30,
            total_tool_limit=50,
        )
    """
    middleware: list[Any] = []

    # Model call limit
    if model_call_limit is not None:
        middleware.append(
            ModelCallLimitMiddleware(
                run_limit=model_call_limit,
                exit_behavior=exit_behavior,
            )
        )

    # Per-tool limits
    if tool_limits:
        for tool_name, limit in tool_limits.items():
            middleware.append(
                ToolCallLimitMiddleware(
                    tool_name=tool_name,
                    run_limit=limit,
                    exit_behavior=exit_behavior,
                )
            )

    # Global tool limit
    if total_tool_limit is not None:
        middleware.append(
            ToolCallLimitMiddleware(
                run_limit=total_tool_limit,
                exit_behavior=exit_behavior,
            )
        )

    return middleware
