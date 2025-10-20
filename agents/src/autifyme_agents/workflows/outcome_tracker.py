"""Outcome Tracking Infrastructure - Capture BUSINESS outcomes for learning.

**Design**:
- LangSmith: Technical observability (traces, latency, errors, tokens)
- OutcomeTracker: Business metrics (approval rates, user patterns, product categories)
- Correlation: `trace_id = tracking_id` (via `run_id` in config)

**Tracking Model**:
- One `workflow_outcomes` record per workflow execution (not per thread)
- HITL workflows create 3 records: initial (pending_hitl) + approval_analyzer + resume (completed)
- Each record has unique `tracking_id` (UUID) used as `trace_id` in LangSmith

**Integration**:
- WorkflowRunner: Sets `run_id` in config → becomes `trace_id` in LangSmith
- Database: Query by `thread_id` (all phases) or `trace_id` (specific execution)
- LangSmith: Query by `trace_id` to link business + technical metrics
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from autifyme_agents.core.ports import StorageInterface

logger = logging.getLogger(__name__)


class IncomingMessage(BaseModel):
    """Structured representation of incoming user message."""

    sender_id: str = Field(description="User/sender identifier")
    sender_name: str | None = Field(
        default=None, description="User display name for personalization (e.g., WhatsApp profile name)"
    )
    text: str | None = Field(default=None, description="Message text content")
    media_id: str | None = Field(default=None, description="Media attachment ID")
    media_type: str | None = Field(default=None, description="Media MIME type")
    platform: str = Field(default="whatsapp", description="Source platform")
    received_at: datetime = Field(default_factory=datetime.now)

    def to_hash(self) -> str:
        """Generate content hash for similarity detection."""
        content = f"{self.text or ''}:{self.media_type or ''}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class RoutingDecision(BaseModel):
    """PM's routing decision with reasoning."""

    intent: str = Field(description="Classified user intent")
    department: str = Field(description="Department selected")
    reasoning: str = Field(description="PM's reasoning for this choice")
    confidence: float | None = Field(
        default=None, description="Confidence score (0-1) if available"
    )
    alternative_departments: list[str] = Field(
        default_factory=list, description="Fallback options considered"
    )
    decided_at: datetime = Field(default_factory=datetime.now)


class WorkflowResult(BaseModel):
    """Final workflow outcome."""

    success: bool = Field(description="Whether workflow completed successfully")
    result_data: dict[str, Any] | None = Field(
        default=None, description="Structured result if successful"
    )
    error_type: str | None = Field(default=None, description="Error class if failed")
    error_message: str | None = Field(
        default=None, description="Error details if failed"
    )
    resolution_strategy: str | None = Field(
        default=None, description="How error was resolved (auto/manual/escalated)"
    )
    completed_at: datetime = Field(default_factory=datetime.now)


class TrackedWorkflow(BaseModel):
    """Complete workflow tracking record."""

    tracking_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique tracking ID"
    )
    thread_id: str = Field(description="LangGraph thread ID")
    trace_id: str | None = Field(
        default=None, description="LangSmith trace ID for observability correlation"
    )
    message: IncomingMessage
    message_hash: str = Field(description="Content hash for similarity")
    routing: RoutingDecision | None = None
    result: WorkflowResult | None = None
    duration_seconds: float | None = None
    started_at: datetime
    ended_at: datetime | None = None

    # Future: Vector embedding for similarity search (Phase 2)
    # message_embedding: list[float] | None = None


class OutcomeTracker:
    """Tracks BUSINESS-SPECIFIC workflow outcomes for learning.

    **Simplified Post-Refactor**:
    - Business metrics ONLY (approval rates, user patterns, categories)
    - Technical observability delegated to LangSmith
    - Lightweight, focused on domain-specific signals

    **Design Principles**:
    - Non-blocking: Tracking failures don't crash workflows
    - Business-focused: No technical metrics (LangSmith has those)
    - Structured: Pydantic models for type safety
    - Integration-ready: Combines with LangSmith data for Phase 2 learning
    """

    def __init__(self, storage: StorageInterface):
        """Initialize outcome tracker.

        Args:
            storage: Storage adapter for persistence
        """
        self.storage = storage
        # Key by tracking_id (not thread_id) to support multiple workflow phases per thread
        # This allows HITL workflows to create separate records for: initial → resume → complete
        self._active_workflows: dict[str, TrackedWorkflow] = {}

    def track_workflow_start(
        self,
        thread_id: str,
        message: IncomingMessage,
    ) -> str:
        """Record workflow initiation.

        Args:
            thread_id: LangGraph thread ID
            message: Incoming user message

        Returns:
            Tracking ID for this workflow
        """
        workflow = TrackedWorkflow(
            thread_id=thread_id,
            message=message,
            message_hash=message.to_hash(),
            started_at=datetime.now(),
        )

        # Store by tracking_id (not thread_id) to allow multiple workflow phases
        self._active_workflows[workflow.tracking_id] = workflow

        logger.info(
            "Workflow started",
            extra={
                "tracking_id": workflow.tracking_id,
                "thread_id": thread_id,
                "has_text": message.text is not None,
                "has_media": message.media_id is not None,
            },
        )

        return workflow.tracking_id

    def track_routing_decision(
        self,
        tracking_id: str,
        intent: str,
        department: str,
        reasoning: str,
        confidence: float | None = None,
        alternatives: list[str] | None = None,
    ) -> None:
        """Record PM routing decision.

        Args:
            tracking_id: Workflow tracking ID (returned from track_workflow_start)
            intent: Classified user intent
            department: Department selected
            reasoning: PM's reasoning
            confidence: Optional confidence score
            alternatives: Optional fallback departments
        """
        workflow = self._active_workflows.get(tracking_id)
        if not workflow:
            logger.warning(f"Routing tracked for unknown workflow: {tracking_id}")
            return

        workflow.routing = RoutingDecision(
            intent=intent,
            department=department,
            reasoning=reasoning,
            confidence=confidence,
            alternative_departments=alternatives or [],
        )

        logger.info(
            "Routing decision tracked",
            extra={
                "tracking_id": workflow.tracking_id,
                "thread_id": workflow.thread_id,
                "intent": intent,
                "department": department,
                "confidence": confidence,
            },
        )

    def set_trace_id(self, tracking_id: str, trace_id: str) -> None:
        """Set LangSmith trace ID for observability correlation.

        Called after PM invocation when trace_id becomes available.

        Args:
            tracking_id: Workflow tracking ID (returned from track_workflow_start)
            trace_id: LangSmith trace ID from PM execution
        """
        workflow = self._active_workflows.get(tracking_id)
        if not workflow:
            logger.warning(f"Trace ID set for unknown workflow: {tracking_id}")
            return

        workflow.trace_id = trace_id

        logger.debug(
            "Trace ID linked to workflow",
            extra={
                "tracking_id": workflow.tracking_id,
                "thread_id": workflow.thread_id,
                "trace_id": trace_id,
            },
        )

    def track_workflow_end(
        self,
        tracking_id: str,
        success: bool,
        result: dict[str, Any] | None = None,
        error: Exception | None = None,
        resolution_strategy: str | None = None,
    ) -> None:
        """Record workflow completion and trigger learning.

        Args:
            tracking_id: Workflow tracking ID (returned from track_workflow_start)
            success: Whether workflow succeeded
            result: Structured result data if successful
            error: Exception if failed
            resolution_strategy: How error was resolved (if applicable)
        """
        workflow = self._active_workflows.get(tracking_id)
        if not workflow:
            logger.warning(f"Workflow end tracked for unknown tracking_id: {tracking_id}")
            return

        workflow.ended_at = datetime.now()
        workflow.duration_seconds = (
            workflow.ended_at - workflow.started_at
        ).total_seconds()

        workflow.result = WorkflowResult(
            success=success,
            result_data=result,
            error_type=type(error).__name__ if error else None,
            error_message=str(error) if error else None,
            resolution_strategy=resolution_strategy,
        )

        logger.info(
            "Workflow completed",
            extra={
                "tracking_id": workflow.tracking_id,
                "thread_id": workflow.thread_id,
                "success": success,
                "duration_seconds": workflow.duration_seconds,
                "error_type": workflow.result.error_type,
            },
        )

        # Persist to storage (Phase 1.2 extension - needs database table)
        self._persist_outcome(workflow)

        # Trigger learning (Phase 2 - routing optimization)
        # self._trigger_learning(workflow)

        # Cleanup - remove from active workflows
        del self._active_workflows[tracking_id]

    def get_workflow_metrics(
        self,
        time_window_hours: int = 24,
    ) -> dict[str, Any]:
        """Get aggregate metrics for monitoring.

        Args:
            time_window_hours: Hours of history to analyze

        Returns:
            Metrics dictionary with success rates, avg duration, etc.
        """
        # Phase 2: Implement full aggregate metrics from workflow_outcomes table
        # Current: Returns minimal runtime metrics (non-blocking placeholder)
        # Future: Query Supabase for success rates, avg duration, category breakdown
        return {
            "active_workflows": len(self._active_workflows),
            "note": "Full aggregate metrics available in Phase 2 analytics",
        }

    # --- Internal Methods ---

    def _persist_outcome(self, workflow: TrackedWorkflow) -> None:
        """Persist BUSINESS-SPECIFIC workflow outcome.

        **Note**: Technical metrics (duration, errors, traces) are in LangSmith.
        This persists only business-relevant data for domain learning.

        Args:
            workflow: Complete workflow record
        """
        # Extract business-relevant result data
        result_data = None
        if workflow.result and workflow.result.result_data:
            result_data = self._make_json_serializable(workflow.result.result_data)

        # Build lightweight business outcome payload
        outcome_payload: dict[str, Any] = {
            "tracking_id": workflow.tracking_id,
            "thread_id": workflow.thread_id,
            "trace_id": workflow.trace_id,  # LangSmith trace ID for observability correlation
            # Business context
            "sender_id": workflow.message.sender_id,
            "platform": workflow.message.platform,
            "message_hash": workflow.message_hash,  # For similarity matching
            "received_at": workflow.message.received_at,  # Message timestamp
            # Routing decision (business logic)
            "intent": workflow.routing.intent if workflow.routing else None,
            "department": workflow.routing.department if workflow.routing else None,
            # Outcome (business success/failure)
            "success": workflow.result.success if workflow.result else False,
            "result_data": result_data,  # Cataloging result with product details
            # Timestamps (reference for joining with LangSmith)
            "started_at": workflow.started_at,
            "ended_at": workflow.ended_at,
            # Phase 2: Learning metadata
            "learned_patterns": [],
            "applied_strategies": [],
        }

        try:
            outcome_id = self.storage.save_workflow_outcome(outcome_payload)
            status = outcome_payload.get("result_data", {}).get("status") if isinstance(outcome_payload.get("result_data"), dict) else "completed"
            logger.info(
                "Workflow outcome persisted",
                extra={
                    "tracking_id": workflow.tracking_id,
                    "thread_id": workflow.thread_id,
                    "outcome_id": outcome_id,
                    "success": workflow.result.success if workflow.result else None,
                    "status": status,
                },
            )
        except Exception as e:
            # Non-blocking: Don't crash workflow if persistence fails
            logger.error(
                "Failed to persist business outcome",
                extra={
                    "tracking_id": workflow.tracking_id,
                    "error": str(e),
                },
                exc_info=True,
            )

    def _make_json_serializable(self, data: Any) -> Any:
        """Convert data to JSON-serializable format.

        Args:
            data: Data to serialize (can be dict, list, Pydantic models, etc.)

        Returns:
            JSON-serializable representation
        """
        # Handle None
        if data is None:
            return None

        # Handle primitives
        if isinstance(data, (str, int, float, bool)):
            return data

        # Handle Pydantic models
        if hasattr(data, "model_dump"):
            return data.model_dump(mode="json")

        # Handle dataclasses
        if hasattr(data, "__dataclass_fields__"):
            from dataclasses import asdict
            return asdict(data)

        # Handle dicts
        if isinstance(data, dict):
            return {
                key: self._make_json_serializable(value)
                for key, value in data.items()
            }

        # Handle lists/tuples
        if isinstance(data, (list, tuple)):
            return [self._make_json_serializable(item) for item in data]

        # Handle datetime
        if isinstance(data, datetime):
            return data.isoformat()

        # Fallback: convert to string representation
        logger.warning(
            f"Non-serializable type {type(data).__name__} converted to string",
            extra={"type": type(data).__name__},
        )
        return str(data)

    def _trigger_learning(self, workflow: TrackedWorkflow) -> None:
        """Trigger learning from workflow outcome.

        NOTE: Phase 2 feature - connects to AdaptiveRouter, ContextualMemory.

        Args:
            workflow: Complete workflow record
        """
        # Phase 2: Update adaptive routing model
        # Phase 2: Store in contextual memory with embeddings
        # Phase 2: Update prompt manager with patterns
        pass
