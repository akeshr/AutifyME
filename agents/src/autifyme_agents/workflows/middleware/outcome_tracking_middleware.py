"""Outcome tracking middleware - wraps PM invocation with automatic tracking."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from autifyme_agents.workflows.handlers.protocol import WorkflowHandler
from autifyme_agents.workflows.outcome_tracker import IncomingMessage, OutcomeTracker

logger = logging.getLogger(__name__)


class OutcomeTrackingMiddleware:
    """Wraps PM invocation with automatic outcome tracking.

    Separates cross-cutting tracking concerns from core orchestration logic.
    Tracks workflow start, sets trace correlation, and tracks end based on result type.
    """

    def __init__(
        self,
        outcome_tracker: OutcomeTracker,
        workflow_handler: WorkflowHandler,
    ):
        """Initialize middleware.

        Args:
            outcome_tracker: Tracker for business outcomes
            workflow_handler: Handler for extracting workflow-specific results
        """
        self.tracker = outcome_tracker
        self.workflow_handler = workflow_handler

    async def execute_with_tracking(
        self,
        thread_id: str,
        incoming_message: IncomingMessage,
        pm_invoker: Callable[[str], tuple[dict[str, Any] | None, Any | None]],
    ) -> tuple[dict[str, Any] | None, Any | None, str]:
        """Execute PM invocation with automatic outcome tracking.

        Handles all tracking concerns:
        - Workflow start tracking
        - Trace ID correlation
        - Workflow end tracking based on result type
        - Error tracking

        Args:
            thread_id: Conversation thread ID
            incoming_message: Structured incoming message
            pm_invoker: Async callable that accepts tracking_id and returns (result, interrupt_value)

        Returns:
            Tuple of (result, interrupt_value, tracking_id)
        """
        # Track workflow start
        tracking_id = self.tracker.track_workflow_start(thread_id, incoming_message)
        logger.info("Workflow started", extra={"thread_id": thread_id, "tracking_id": tracking_id})

        try:
            # Invoke PM with tracking_id (passed as run_id)
            result, interrupt_value = await pm_invoker(tracking_id)

            # Set trace correlation (tracking_id = trace_id when passed as run_id)
            self.tracker.set_trace_id(tracking_id, tracking_id)

            # Track end based on result type
            self._track_result(tracking_id, result, interrupt_value)

            return result, interrupt_value, tracking_id

        except Exception as e:
            # Track error
            self.tracker.track_workflow_end(
                tracking_id=tracking_id,
                success=False,
                error=e,
                resolution_strategy="user_notified",
            )
            raise

    def _track_result(
        self,
        tracking_id: str,
        result: dict[str, Any] | None,
        interrupt_value: Any | None,
    ) -> None:
        """Track workflow end based on result type.

        Args:
            tracking_id: Workflow tracking ID
            result: PM result dict
            interrupt_value: Interrupt value if present
        """
        # Case 1: HITL interrupt
        if interrupt_value:
            # Infer workflow type from interrupt (execute_database_operation or save_campaign)
            intent, department = self._infer_workflow_from_interrupt(interrupt_value)
            if intent and department:
                self.tracker.track_routing_decision(
                    tracking_id=tracking_id,
                    intent=intent,
                    department=department,
                    reasoning=f"PM routed to {department} workflow (inferred from HITL interrupt)",
                    confidence=None,
                )

            self.tracker.track_workflow_end(
                tracking_id=tracking_id,
                success=True,
                result={"status": "pending_hitl", "tracking_id": tracking_id},
            )
            return

        # Case 2: No result
        if not result:
            logger.warning("PM returned no result")
            return

        messages = result.get("messages", [])

        # Case 3: Cataloging/workflow-specific result
        workflow_result = self.workflow_handler.extract_result(messages)
        if workflow_result:
            self.tracker.track_workflow_end(
                tracking_id=tracking_id,
                success=True,
                result=workflow_result.model_dump() if hasattr(workflow_result, 'model_dump') else workflow_result,
            )
            return

        # Case 4: Resume flow completion (string content tool message)
        if self._is_resume_completion(messages):
            self.tracker.track_workflow_end(
                tracking_id=tracking_id,
                success=True,
                result={"status": "completed", "note": "Resume flow"},
            )
            return

        # Case 5: Conversational response
        summary = self.workflow_handler.extract_summary(messages)
        if summary:
            self.tracker.track_workflow_end(
                tracking_id=tracking_id,
                success=True,
                result={"type": "conversational", "summary": summary},
            )
        else:
            # No extractable result
            self.tracker.track_workflow_end(
                tracking_id=tracking_id,
                success=True,
                result={"type": "conversational", "note": "No summary extracted"},
            )

    def _is_resume_completion(self, messages: list[Any]) -> bool:
        """Check if messages indicate resume workflow completion.

        Args:
            messages: PM output messages

        Returns:
            True if tool message with "successfully cataloged" found
        """
        return any(
            getattr(msg, "type", None) == "tool" and
            isinstance(getattr(msg, "content", None), str) and
            "successfully cataloged" in getattr(msg, "content", "").lower()
            for msg in messages
        )

    def _infer_workflow_from_interrupt(self, interrupt_value: Any) -> tuple[str | None, str | None]:
        """Infer workflow type from HITL interrupt.

        Pragmatic approach: Infer intent/department from which persistence tool triggered HITL.

        Args:
            interrupt_value: The interrupt value from LangGraph

        Returns:
            Tuple of (intent, department) or (None, None) if unable to infer
        """
        # Interrupt value structure: list of dicts with 'name' field for tool calls
        if not interrupt_value or not isinstance(interrupt_value, list):
            return None, None

        for item in interrupt_value:
            if not isinstance(item, dict):
                continue

            tool_name = item.get("name", "")

            # Product onboarding workflow (Phase 2C: universal execute_database_operation)
            if "execute_database_operation" in tool_name or "save_product_family" in tool_name:
                return "product_onboarding", "product"

            # Marketing campaign workflow
            if "save_campaign" in tool_name:
                return "marketing_campaign", "marketing"

        # Unable to infer
        return None, None
