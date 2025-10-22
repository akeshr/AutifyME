"""Approval coordinator - handles approval analyzer invocation with tracking and error handling."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from langgraph.types import Command

from autifyme_agents.schemas.approval import BatchApprovalResponse
from autifyme_agents.schemas.interrupt import InterruptInfo
from autifyme_agents.workflows.approval_analyzer import analyze_approval
from autifyme_agents.workflows.channels.protocol import MessagingChannel
from autifyme_agents.workflows.outcome_tracker import IncomingMessage, OutcomeTracker

logger = logging.getLogger(__name__)


class ApprovalCoordinator:
    """Coordinates approval analyzer invocation with tracking and error handling.

    Separates approval-specific logic from core orchestration.
    Handles: run_id generation, tracking start/end, analyzer invocation, Command building, error handling.
    """

    def __init__(
        self,
        outcome_tracker: OutcomeTracker,
        channel: MessagingChannel,
    ):
        """Initialize approval coordinator.

        Args:
            outcome_tracker: Tracker for business outcomes
            channel: Messaging channel for user communication
        """
        self.outcome_tracker = outcome_tracker
        self.channel = channel

    def analyze_and_build_command(
        self,
        thread_id: str,
        user_message: str,
        pending_interrupts: list[InterruptInfo],
        conversation_history: list[Any],
        raw_payload: dict[str, Any],
    ) -> tuple[Command[Any] | None, str | None]:
        """Invoke approval analyzer and build Command from response.

        Handles complete approval analysis workflow:
        - Generate run_id for trace correlation
        - Track workflow start
        - Invoke analyzer with full context
        - Track workflow end (success or error)
        - Build Command from structured response
        - Handle errors (send user messages, track failures)

        Args:
            thread_id: Conversation thread ID
            user_message: User's approval response message
            pending_interrupts: List of normalized interrupt dicts
            conversation_history: Full conversation history for context
            raw_payload: Raw message payload (for sender info)

        Returns:
            Tuple of (Command object if successful else None, approval_tracking_id or None)
            If Command is None, error message already sent to user
        """
        logger.info(
            "Analyzing approval with conversation history",
            extra={
                "thread_id": thread_id,
                "interrupt_count": len(pending_interrupts),
                "user_message": user_message[:50],
                "has_history": len(conversation_history) > 0,
            }
        )

        # Generate unique run_id for approval analyzer trace
        approval_run_id = str(uuid4())

        # Track approval analyzer start
        approval_message = IncomingMessage(
            sender_id=raw_payload.get("sender", ""),
            sender_name=raw_payload.get("sender_name"),
            text=f"[Approval Analysis] {user_message}",
            platform="internal",
        )
        approval_tracking_id = self.outcome_tracker.track_workflow_start(thread_id, approval_message)
        self.outcome_tracker.set_trace_id(approval_tracking_id, approval_run_id)

        try:
            # Invoke approval analyzer with full conversation context
            approval_response: BatchApprovalResponse = analyze_approval(
                pending_interrupts=pending_interrupts,
                user_message=user_message,
                conversation_history=conversation_history,
                run_id=approval_run_id,
            )

            # Track successful completion
            self.outcome_tracker.track_workflow_end(
                tracking_id=approval_tracking_id,
                success=True,
                result={
                    "type": "approval_analysis",
                    "interrupt_count": len(pending_interrupts),
                    "response_count": len(approval_response.responses),
                    "reasoning": approval_response.reasoning,
                }
            )

            logger.info(
                "Approval analysis complete",
                extra={
                    "thread_id": thread_id,
                    "response_count": len(approval_response.responses),
                    "reasoning": approval_response.reasoning,
                }
            )

            # Build Command from structured approval response
            command_obj = self._build_command_from_approval(
                approval_response, pending_interrupts
            )

            return command_obj, approval_tracking_id

        except ValueError as e:
            # Validation error (malformed approval response)
            logger.error(
                "Approval analysis validation failed",
                extra={"thread_id": thread_id, "error": str(e)}
            )
            self.outcome_tracker.track_workflow_end(
                tracking_id=approval_tracking_id,
                success=False,
                error=e,
                resolution_strategy="user_notified"
            )
            self.channel.send_text(
                raw_payload.get("sender", ""),
                "I had trouble processing your response. Please try: 'approve' or 'reject'"
            )
            return None, None

        except Exception as e:
            # Generic error
            logger.exception(
                "Approval analysis failed",
                extra={"thread_id": thread_id, "error_type": type(e).__name__}
            )
            self.outcome_tracker.track_workflow_end(
                tracking_id=approval_tracking_id,
                success=False,
                error=e,
                resolution_strategy="user_notified"
            )
            self.channel.send_text(
                raw_payload.get("sender", ""),
                "I encountered an error processing your response. Please try again."
            )
            return None, None

    def _build_command_from_approval(
        self,
        approval_response: BatchApprovalResponse,
        pending_interrupts: list[InterruptInfo],
    ) -> Command[Any]:
        """Build LangGraph Command from structured approval response.

        Takes the Pydantic BatchApprovalResponse from approval analyzer and
        constructs a LangGraph Command object for resuming interrupted workflows.

        IMPORTANT: Uses original_interrupt_id (WITHOUT suffix) to match checkpoint format.
        Each interrupt gets its own entry in Command.resume with its response.

        Args:
            approval_response: Structured approval response from analyzer
            pending_interrupts: List of normalized interrupt dicts

        Returns:
            Command object ready for execution
        """
        from collections import defaultdict
        interrupt_responses = defaultdict(list)

        for idx, interrupt_info in enumerate(pending_interrupts):
            # Use original_interrupt_id (WITHOUT suffix) to match checkpoint format
            interrupt_id_for_command = interrupt_info.original_interrupt_id or interrupt_info.interrupt_id

            response = approval_response.responses[idx]
            tool_name = interrupt_info.tool_name
            tool_args = interrupt_info.tool_args

            # Format response based on type for v1.0 HITL middleware compatibility
            if response.type == "edit":
                # v1.0 HITL middleware expects: {"type": "edit", "edited_action": {"name": "tool_name", "args": {...}}}
                merged_args = {**tool_args, **response.args} if isinstance(response.args, dict) else tool_args
                hitl_response = {
                    "type": "edit",
                    "edited_action": {
                        "name": tool_name,
                        "args": merged_args
                    }
                }
                logger.debug(
                    f"Built edit response for {interrupt_id_for_command}",
                    extra={
                        "tool_name": tool_name,
                        "edited_fields": list(response.args.keys()) if isinstance(response.args, dict) else [],
                    }
                )
            elif response.type == "accept":
                # v1.0: "accept" → "approve"
                hitl_response = {"type": "approve"}
            elif response.type == "response":
                # v1.0: "response" → "reject" with "message" field
                message = response.args if isinstance(response.args, str) else str(response.args or "")
                hitl_response = {
                    "type": "reject",
                    "message": message
                }

            interrupt_responses[interrupt_id_for_command].append(hitl_response)

        # Build HITLResponse for LangGraph Command
        # IMPORTANT: Command.resume should contain the value that interrupt() returns, NOT a dict keyed by interrupt_id
        # HumanInTheLoopMiddleware calls: hitl_response = interrupt(hitl_request)
        # So we pass {"decisions": [...]} directly, not {interrupt_id: {"decisions": [...]}}

        # Verify we have exactly ONE interrupt (batch HITL = multiple action_requests under ONE interrupt)
        if len(interrupt_responses) != 1:
            raise ValueError(
                f"Expected single interrupt for batch HITL, got {len(interrupt_responses)}. "
                f"Multiple separate interrupts not yet supported."
            )

        # Extract the HITLResponse value (decisions list)
        interrupt_id = list(interrupt_responses.keys())[0]
        decisions = interrupt_responses[interrupt_id]

        # Build HITLResponse format: {"decisions": [...]}
        hitl_response_value = {"decisions": decisions}

        logger.info(
            "Built Command from structured approval",
            extra={
                "total_responses": len(pending_interrupts),
                "interrupt_id": interrupt_id,
                "decision_count": len(decisions),
                "edit_count": sum(1 for resp in approval_response.responses if resp.type == "edit"),
            }
        )

        # Pass HITLResponse directly to Command.resume (NOT wrapped in dict with interrupt_id)
        return Command(resume=hitl_response_value)
