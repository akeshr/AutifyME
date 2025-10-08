"""Interrupt coordinator for HITL workflow management.

Handles LangGraph interrupts for human approval workflows.

Design Principle: Single Responsibility - only handles interrupt logic, not workflow execution or channel communication.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal

from langgraph.types import Interrupt, Command

from autifyme_agents.core.logging_config import get_logger
from autifyme_agents.workflows.orchestration.state_manager import StateManager
from autifyme_agents.schemas.models import Product, CatalogingResult
from autifyme_agents.schemas.agent_outputs import CatalogingToolOutput

logger = get_logger(__name__)


class WorkflowError(Exception):
    """Raised when workflow encounters an error that prevents continuation."""

    pass


@dataclass
class ApprovalRequest:
    """Structured approval request for HITL workflows.

    Attributes:
        thread_id: Conversation thread ID
        interrupt_id: LangGraph interrupt identifier
        tool_call: The tool call requiring approval (typically save_product)
        draft: Product draft to be approved
        checkpoint_id: Optional checkpoint ID for resumption
        ai_message: Optional AI message that triggered the tool call
    """

    thread_id: str
    interrupt_id: str
    tool_call: dict[str, Any]
    draft: Product
    checkpoint_id: str | None = None
    ai_message: dict[str, Any] | None = None


class InterruptCoordinator:
    """Handles HITL interrupts for workflow approval.

    Responsibilities:
    - Extract tool calls from LangGraph interrupts
    - Validate approval requirements (e.g., find save_product)
    - Generate approval requests
    - Resume workflows after approval/rejection

    NOT responsible for:
    - Sending messages to users (delegates to channel)
    - State persistence (delegates to StateManager)
    - Workflow execution (delegates to PM)
    """

    def __init__(self, state_manager: StateManager):
        """Initialize interrupt coordinator.

        Args:
            state_manager: State manager for approval persistence
        """
        self.state = state_manager

    def process_interrupt(
        self,
        interrupt: Interrupt,
        thread_id: str,
        pm_state: dict[str, Any],
        media_path: Path | None = None,
    ) -> ApprovalRequest:
        """Extract tool calls and create approval request.

        Args:
            interrupt: LangGraph interrupt object from PM stream
            thread_id: Conversation thread ID
            pm_state: Last PM state from stream (contains messages)
            media_path: Optional media file to preserve until approval/rejection

        Returns:
            Structured approval request ready to send to user

        Raises:
            WorkflowError: If no save_product tool call found in interrupt
        """
        logger.debug(
            "Processing interrupt",
            extra={
                "thread_id": thread_id,
                "interrupt_id": interrupt.id,
                "has_pm_state": pm_state is not None,
            },
        )

        # Extract tool calls from interrupt
        tool_calls = self._extract_tool_calls(interrupt, pm_state)

        # Find save_product tool call
        save_call = self._find_save_product(tool_calls)
        if not save_call:
            logger.error(
                "No save_product tool call found in interrupt",
                extra={
                    "thread_id": thread_id,
                    "tool_calls": [tc.get("name") for tc in tool_calls],
                },
            )
            raise WorkflowError("No save_product found in interrupt - workflow design error")

        # Parse draft product from tool args
        draft = self._parse_draft(save_call["args"])

        # Extract AI message for context
        ai_message_data = self._extract_ai_message(pm_state)

        # Get checkpoint ID if available
        checkpoint_id = pm_state.get("checkpoint_id", "unknown") if pm_state else "unknown"

        # Create approval request
        request = ApprovalRequest(
            thread_id=thread_id,
            interrupt_id=interrupt.id or save_call.get("id") or thread_id,
            tool_call=save_call,
            draft=draft,
            checkpoint_id=checkpoint_id,
            ai_message=ai_message_data,
        )

        # Persist for restart resilience
        try:
            self.state.save_pending_approval(
                thread_id=thread_id,
                approval_data=request,
                media_path=str(media_path) if media_path else None,
            )
            logger.info(
                "Persisted pending approval to storage",
                extra={
                    "thread_id": thread_id,
                    "interrupt_id": request.interrupt_id,
                    "has_media": media_path is not None,
                },
            )
        except Exception as exc:
            logger.exception(
                "Failed to persist pending approval",
                exc_info=exc,
                extra={"thread_id": thread_id},
            )
            # Re-raise - we cannot proceed without persisting approval
            raise WorkflowError("Failed to persist approval request") from exc

        return request

    def resume_workflow(
        self,
        thread_id: str,
        decision: Literal["approve", "reject"],
        pm_factory: Callable,
    ) -> CatalogingResult | None:
        """Resume workflow after approval decision.

        Args:
            thread_id: Conversation thread ID
            decision: User's decision (approve or reject)
            pm_factory: Factory function to create PM instance

        Returns:
            Cataloging result if completed (approval), None if rejected

        Raises:
            WorkflowError: If no pending approval found or resumption fails
        """
        logger.info(
            "Resuming workflow after approval decision",
            extra={"thread_id": thread_id, "decision": decision},
        )

        # Retrieve pending approval
        approval = self.state.get_pending_approval(thread_id)
        if not approval:
            raise WorkflowError("No pending approval found for this thread")

        if decision == "reject":
            logger.info("User rejected approval", extra={"thread_id": thread_id})
            self.state.delete_pending_approval(thread_id)
            return None

        # Build resume command for LangGraph
        command = Command(
            resume={
                approval.get("interrupt_id"): {
                    "type": "accept",
                    "args": None,
                }
            }
        )

        # Delete approval before resuming (prevent re-processing)
        self.state.delete_pending_approval(thread_id)

        # Resume PM
        pm = pm_factory()
        config = {
            "configurable": {
                "thread_id": thread_id,
                "company_id": "default",  # Single-tenant for now
            }
        }

        logger.debug("Streaming PM for workflow resumption", extra={"thread_id": thread_id})
        last_event = None
        for event in pm.stream(command, config=config, stream_mode="values"):
            last_event = event

            # Check for nested interrupts (shouldn't happen for save_product, but handle gracefully)
            if "__interrupt__" in event:
                logger.warning(
                    "Nested interrupt detected during resumption",
                    extra={"thread_id": thread_id},
                )
                # Return None - caller should handle as incomplete workflow
                return None

        # Extract result from final event
        if last_event:
            result = self._extract_result(last_event)
            logger.info(
                "Workflow resumed successfully",
                extra={"thread_id": thread_id, "has_result": result is not None},
            )
            return result

        logger.warning("No result after workflow resumption", extra={"thread_id": thread_id})
        return None

    def _extract_tool_calls(
        self,
        interrupt: Interrupt,
        pm_state: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extract tool calls from interrupt payload or PM state.

        Args:
            interrupt: LangGraph interrupt object
            pm_state: Last PM state from stream

        Returns:
            List of tool call dicts
        """
        if not pm_state:
            logger.debug("No PM state available to extract tool calls")
            return []

        messages = pm_state.get("messages") or []

        # Find last AIMessage with tool_calls
        for message in reversed(messages):
            message_type = getattr(message, "type", None)
            if not message_type and hasattr(message, "__class__"):
                message_type = message.__class__.__name__.replace("Message", "").lower()

            if message_type == "ai":
                tool_calls = getattr(message, "tool_calls", []) or []
                if tool_calls:
                    logger.debug(
                        "Extracted tool calls from AIMessage",
                        extra={
                            "tool_call_count": len(tool_calls),
                            "tool_names": [tc.get("name") for tc in tool_calls],
                        },
                    )
                    return tool_calls

        logger.warning("No AIMessage with tool_calls found in PM state")
        return []

    def _find_save_product(self, tool_calls: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Find save_product tool call in list.

        Args:
            tool_calls: List of tool call dicts

        Returns:
            save_product tool call dict, or None if not found
        """
        for call in tool_calls:
            if call.get("name") == "save_product":
                return call
        return None

    def _parse_draft(self, tool_args: dict[str, Any]) -> Product:
        """Parse Product from save_product tool arguments.

        Args:
            tool_args: Tool arguments dict

        Returns:
            Product instance
        """
        return Product(
            id=tool_args.get("id", "draft"),
            name=tool_args.get("name", "Unnamed Product"),
            description=tool_args.get("description"),
            price=tool_args.get("price"),
            sizes=tool_args.get("sizes"),
            colors=tool_args.get("colors"),
            image_urls=tool_args.get("image_urls"),
        )

    def _extract_ai_message(self, pm_state: dict[str, Any]) -> dict[str, Any] | None:
        """Extract AIMessage data from PM state.

        Args:
            pm_state: Last PM state from stream

        Returns:
            Serialized AIMessage dict, or None if not found
        """
        if not pm_state:
            return None

        messages = pm_state.get("messages", [])
        for message in reversed(messages):
            message_type = getattr(message, "type", None)
            if not message_type and hasattr(message, "__class__"):
                message_type = message.__class__.__name__.replace("Message", "").lower()

            if message_type == "ai":
                return {
                    "type": "ai",
                    "content": getattr(message, "content", ""),
                    "tool_calls": getattr(message, "tool_calls", []),
                }

        return None

    def _extract_result(self, last_event: dict[str, Any]) -> CatalogingResult | None:
        """Extract CatalogingResult from PM final event.

        Args:
            last_event: Final event from PM stream

        Returns:
            CatalogingResult if found, None otherwise
        """
        messages = last_event.get("messages") or []

        # Look for ToolMessage from save_product
        for message in messages:
            message_type = getattr(message, "type", None)
            if not message_type and hasattr(message, "__class__"):
                message_type = message.__class__.__name__.replace("Message", "").lower()

            if message_type != "tool":
                continue

            content = getattr(message, "content", None)
            if not isinstance(content, dict):
                continue

            if content.get("tool_name") != "save_product":
                continue

            # Parse as CatalogingToolOutput
            try:
                tool_output = CatalogingToolOutput.model_validate(content)
                return tool_output.result
            except ValueError as exc:
                logger.debug("Failed to parse tool output", exc_info=exc)
                continue

        return None
