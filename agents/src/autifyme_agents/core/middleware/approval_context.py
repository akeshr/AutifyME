"""Approval context middleware using standard LangGraph AgentMiddleware.

This middleware injects pending approval context into the PM's state before reasoning,
enabling the PM to see and decide on pending tool calls that require human approval.

Architecture:
- Uses standard LangGraph v1 AgentMiddleware API
- Runs after HumanInTheLoopMiddleware populates __interrupt__
- Injects approval context as SystemMessage before PM reasoning
- No custom base classes - pure LangGraph v1 pattern
"""

from __future__ import annotations

import logging
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import SystemMessage

logger = logging.getLogger(__name__)


class ApprovalContextMiddleware(AgentMiddleware):
    """Standard LangGraph middleware for injecting approval context.

    This middleware detects pending interrupts (from HumanInTheLoopMiddleware)
    and formats them into human-readable approval context that gets injected
    into the PM's message stream before reasoning.

    Design:
    - Subclasses standard LangGraph AgentMiddleware
    - Uses before_agent() hook (runs before PM reasoning)
    - Injects SystemMessage with approval context
    - Only activates when __interrupt__ field is non-empty

    Integration:
        pm = create_deep_agent(
            middleware=[ApprovalContextMiddleware()],
            tool_configs={"save_product": True},
            ...
        )
    """

    def __init__(self, *, include_tool_details: bool = True):
        """Initialize approval context middleware.

        Args:
            include_tool_details: Include tool names and args in context
        """
        self.include_tool_details = include_tool_details
        logger.debug("ApprovalContextMiddleware initialized")

    @property
    def name(self) -> str:
        """Middleware name for debugging."""
        return "ApprovalContextMiddleware"

    def before_agent(
        self, state: dict[str, Any], runtime: Any
    ) -> dict[str, Any] | None:
        """Inject approval context before PM reasoning.

        This hook runs before each PM agent loop iteration. If there are pending
        interrupts (from HITL middleware), we format them into readable context
        and inject as a SystemMessage.

        Args:
            state: Current agent state (includes __interrupt__ from HITL)
            runtime: LangGraph runtime context

        Returns:
            State modifications (messages to inject), or None if no changes needed
        """
        # Check for pending interrupts from HumanInTheLoopMiddleware
        interrupts = state.get("__interrupt__", [])

        if not interrupts:
            logger.debug("No pending interrupts - skipping context injection")
            return None

        logger.info(
            "Injecting approval context for pending interrupts",
            extra={"interrupt_count": len(interrupts)},
        )

        # Format approval context
        context_message = self._format_approval_context(interrupts)

        # Inject as SystemMessage (doesn't pollute conversation history)
        return {"messages": [SystemMessage(content=context_message)]}

    def _format_approval_context(self, interrupts: list[dict]) -> str:
        """Format interrupts into structured approval context.

        Args:
            interrupts: List of interrupt objects from HITL middleware

        Returns:
            Formatted approval context string
        """
        items = []

        for i, interrupt in enumerate(interrupts, 1):
            # Extract interrupt metadata
            value = interrupt.get("value", {})

            if isinstance(value, list):
                # Parallel tool calls (multiple actions in one interrupt)
                for j, action in enumerate(value):
                    action_request = action.get("action_request", {})
                    tool_name = action_request.get("action", "unknown_tool")
                    tool_args = action_request.get("args", {})
                    description = action.get("description", "")

                    items.append(
                        self._format_action_item(
                            f"{i}.{j + 1}", tool_name, tool_args, description
                        )
                    )
            else:
                # Single action
                tool_name = value.get("tool_name", "unknown_tool")
                tool_args = value.get("tool_args", {})
                description = value.get("description", "")

                items.append(
                    self._format_action_item(str(i), tool_name, tool_args, description)
                )

        context = f"""<approval_context>
## Pending Approvals ({len(items)} action(s))

The following tool calls are awaiting your approval decision:

{chr(10).join(items)}

**Your role:** Review each action and decide whether to approve, reject, or modify.
Use your approval tools to communicate your decisions.
</approval_context>"""

        logger.debug(
            "Built approval context",
            extra={"context_length": len(context), "action_count": len(items)},
        )

        return context

    def _format_action_item(
        self, index: str, tool_name: str, tool_args: dict, description: str
    ) -> str:
        """Format a single action into readable item.

        Args:
            index: Item number (e.g., "1" or "1.2")
            tool_name: Name of the tool being called
            tool_args: Arguments to the tool
            description: Human-readable description

        Returns:
            Formatted action item string
        """
        if self.include_tool_details:
            # Include tool signature for debugging
            args_str = ", ".join(f"{k}={repr(v)[:50]}" for k, v in tool_args.items())
            return f"""
{index}. **{tool_name}({args_str})**
   Description: {description or 'No description'}"""
        else:
            # Simplified format
            return f"{index}. {description or tool_name}"

    def after_agent(
        self, state: dict[str, Any], runtime: Any
    ) -> dict[str, Any] | None:
        """Optional: Post-processing after PM completes.

        Currently not used, but could be extended to:
        - Track which approvals PM decided on
        - Validate approval decisions
        - Record reasoning for analytics

        Args:
            state: Agent state after PM reasoning
            runtime: LangGraph runtime context

        Returns:
            State modifications, or None
        """
        # No post-processing needed in initial implementation
        return None
