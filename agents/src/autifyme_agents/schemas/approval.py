"""Approval state schemas for agentic approval workflows.

This module defines ALL state schemas for the agentic approval system,
handling multi-action queues, dependencies, temporal concerns, and edge cases.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class ApprovalStatus(str, Enum):
    """Lifecycle states for approval requests."""

    PENDING = "pending"  # Awaiting user decision
    EXPIRED = "expired"  # Timeout reached
    PARKED = "parked"  # Temporarily suspended
    RESOLVED = "resolved"  # User made decision
    EXECUTING = "executing"  # Currently executing approved action
    COMPLETED = "completed"  # Action executed successfully
    FAILED = "failed"  # Action execution failed


class ApprovalIntent(str, Enum):
    """User intent classification for approval messages."""

    APPROVE = "approve"  # Proceed as-is
    APPROVE_WITH_EDITS = "approve_with_edits"  # Proceed with modifications
    REJECT = "reject"  # Cancel action
    QUESTION = "question"  # Need clarification
    DEFER = "defer"  # Postpone decision
    PARK = "park"  # Temporarily suspend to handle new request
    ABANDON = "abandon"  # Cancel and clear all state


class RiskLevel(str, Enum):
    """Risk assessment for approval actions."""

    LOW = "low"  # Routine operations
    MEDIUM = "medium"  # Requires attention
    HIGH = "high"  # Critical, destructive, or high-value
    CRITICAL = "critical"  # Requires multi-level approval


class ApprovalDecision(BaseModel):
    """Structured decision from user message classification."""

    intent: ApprovalIntent
    confidence: float = Field(ge=0.0, le=1.0, description="LLM classification confidence")
    reasoning: str = Field(description="Why did LLM classify this way?")

    # For APPROVE_WITH_EDITS
    edited_fields: dict[str, Any] | None = Field(
        None,
        description="Field-level edits extracted from user message"
    )
    edit_instructions: str | None = Field(
        None,
        description="Natural language edit instructions if extraction failed"
    )

    # For QUESTION
    question_text: str | None = Field(None, description="Extracted question")
    clarification_needed: list[str] | None = Field(
        None,
        description="Specific aspects needing clarification"
    )

    # For DEFER
    defer_until: datetime | None = Field(None, description="When to retry approval")
    defer_reason: str | None = Field(None, description="Why user wants to defer")

    # For PARK
    park_reason: str | None = Field(None, description="Why parking (e.g., handle new request)")

    # For REJECT/ABANDON
    rejection_reason: str | None = Field(None, description="Why user rejected")

    # Metadata
    classified_at: datetime = Field(default_factory=datetime.now)
    original_message: str = Field(description="User's raw message")


class ApprovalCondition(BaseModel):
    """Conditional approval rules (e.g., 'approve if price < $100')."""

    condition_type: Literal["threshold", "time_window", "inventory", "custom"]
    field: str  # Field to evaluate
    operator: Literal["<", "<=", ">", ">=", "==", "!=", "in", "not_in"]
    value: Any  # Value to compare against
    description: str  # Human-readable: "Price must be less than $100"

    def evaluate(self, context: dict[str, Any]) -> bool:
        """Evaluate condition against runtime context."""
        field_value = context.get(self.field)

        if self.operator == "<":
            return field_value < self.value
        elif self.operator == "<=":
            return field_value <= self.value
        elif self.operator == ">":
            return field_value > self.value
        elif self.operator == ">=":
            return field_value >= self.value
        elif self.operator == "==":
            return field_value == self.value
        elif self.operator == "!=":
            return field_value != self.value
        elif self.operator == "in":
            return field_value in self.value
        elif self.operator == "not_in":
            return field_value not in self.value
        else:
            raise ValueError(f"Unknown operator: {self.operator}")


class ApprovalRequest(BaseModel):
    """Single pending approval with full context for agentic decision-making."""

    # ===== IDENTITY =====
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique approval ID (from LangGraph interrupt or generated)"
    )
    thread_id: str = Field(description="Conversation thread")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # ===== EXPIRATION =====
    expires_at: datetime | None = Field(
        None,
        description="Automatic expiration time (None = no expiration)"
    )
    expiration_policy: Literal["auto_approve", "auto_reject", "notify_only"] = "auto_reject"

    # ===== ACTION CONTEXT =====
    action: str = Field(description="Tool/action name (e.g., 'save_product')")
    action_description: str = Field(description="Human-readable action summary")
    action_args: dict[str, Any] = Field(description="Original tool arguments")

    # ===== AGENT CONTEXT =====
    agent_source: str = Field(description="Which agent triggered interrupt (e.g., 'cataloging_department')")
    checkpoint_ns: str = Field(description="Checkpoint namespace for resume (e.g., 'task:cataloging_department')")
    interrupt_node: str | None = Field(None, description="Graph node that interrupted (e.g., 'tools')")

    # ===== PREVIEW DATA =====
    preview_data: dict[str, Any] = Field(description="Structured data for user review")
    preview_message: str = Field(description="Formatted message for channel (WhatsApp, Slack, etc.)")
    media_path: str | None = Field(None, description="Path to visual preview (image, video, etc.)")

    # ===== WORKFLOW CONTEXT =====
    dependencies: list[str] = Field(
        default_factory=list,
        description="Approval IDs that must resolve before this one"
    )
    dependent_on_me: list[str] = Field(
        default_factory=list,
        description="Approval IDs waiting for this to resolve"
    )
    follow_up_actions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Actions that will execute after approval (for user visibility)"
    )
    parent_workflow_id: str | None = Field(
        None,
        description="Parent workflow for nested approvals"
    )

    # ===== RISK & POLICY =====
    risk_level: RiskLevel = Field(default=RiskLevel.LOW)
    requires_multi_level_approval: bool = Field(
        default=False,
        description="If True, needs manager/admin approval chain"
    )
    approval_chain: list[str] = Field(
        default_factory=list,
        description="User IDs in approval chain (for multi-level)"
    )
    current_approver_index: int = Field(
        default=0,
        description="Current position in approval chain"
    )

    # ===== EDIT CONFIGURATION =====
    editable_fields: list[str] = Field(description="Fields user can edit")
    validation_schema: dict[str, Any] = Field(description="JSON schema for validation")
    edit_suggestions: dict[str, list[Any]] | None = Field(
        None,
        description="Suggested values for editable fields (e.g., {price: [10, 15, 20]})"
    )

    # ===== CONDITIONAL APPROVAL =====
    conditions: list[ApprovalCondition] = Field(
        default_factory=list,
        description="Conditional approval rules"
    )

    # ===== STATE =====
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING)
    resolution: ApprovalDecision | None = Field(None, description="User's decision")
    execution_result: dict[str, Any] | None = Field(
        None,
        description="Result of executing approved action"
    )
    failure_reason: str | None = Field(None, description="Why execution failed")

    # ===== CONVERSATION CONTEXT =====
    approval_conversation_history: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Messages exchanged during approval (questions, edits, etc.)"
    )
    answered_questions: list[dict[str, str]] = Field(
        default_factory=list,
        description="Q&A pairs during approval for context"
    )

    # ===== AUDIT =====
    approved_by: str | None = Field(None, description="User ID who approved")
    approved_at: datetime | None = Field(None, description="When approved")
    approval_duration_seconds: float | None = Field(
        None,
        description="How long user took to approve"
    )

    @field_validator('expires_at', mode='before')
    @classmethod
    def set_default_expiration(cls, v):
        """Set default expiration to 24h if not provided."""
        if v is None:
            return datetime.now() + timedelta(hours=24)
        return v

    def is_expired(self) -> bool:
        """Check if approval has expired."""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at

    def is_approvable(self) -> bool:
        """Check if approval can be resolved (no blocking dependencies)."""
        return (
            self.status == ApprovalStatus.PENDING
            and not self.is_expired()
            and len(self.dependencies) == 0  # Dependencies already resolved
        )

    def can_user_edit_field(self, field_name: str) -> bool:
        """Check if field is editable."""
        return field_name in self.editable_fields

    def validate_edits(self, edited_fields: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate edited fields against schema.

        Returns:
            (is_valid, error_messages)
        """
        errors = []

        for field, value in edited_fields.items():
            if field not in self.editable_fields:
                errors.append(f"Field '{field}' is not editable")

            # TODO: Validate against validation_schema (Pydantic schema)

        return len(errors) == 0, errors

    def evaluate_conditions(self, runtime_context: dict[str, Any]) -> tuple[bool, list[str]]:
        """Evaluate all approval conditions.

        Returns:
            (all_conditions_met, failed_condition_descriptions)
        """
        failed = []

        for condition in self.conditions:
            if not condition.evaluate(runtime_context):
                failed.append(condition.description)

        return len(failed) == 0, failed

    def add_conversation_message(self, role: str, content: str) -> None:
        """Track approval conversation for context."""
        self.approval_conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        self.updated_at = datetime.now()

    def add_answered_question(self, question: str, answer: str) -> None:
        """Track Q&A during approval."""
        self.answered_questions.append({
            "question": question,
            "answer": answer,
            "timestamp": datetime.now().isoformat(),
        })
        self.updated_at = datetime.now()


class ApprovalQueue(BaseModel):
    """Queue of pending approvals with dependency tracking."""

    thread_id: str
    approvals: list[ApprovalRequest] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def add(self, request: ApprovalRequest) -> None:
        """Add approval to queue."""
        self.approvals.append(request)
        self.updated_at = datetime.now()

    def get_by_id(self, approval_id: str) -> ApprovalRequest | None:
        """Get approval by ID."""
        for approval in self.approvals:
            if approval.id == approval_id:
                return approval
        return None

    def get_next_pending(self) -> ApprovalRequest | None:
        """Get next approvable approval (no blocking dependencies).

        Returns first PENDING approval with no unresolved dependencies.
        """
        for approval in self.approvals:
            if approval.is_approvable():
                # Check if all dependencies are resolved
                if all(self._is_resolved(dep_id) for dep_id in approval.dependencies):
                    return approval

        return None

    def get_all_pending(self) -> list[ApprovalRequest]:
        """Get all pending approvals."""
        return [a for a in self.approvals if a.status == ApprovalStatus.PENDING]

    def resolve(self, approval_id: str, decision: ApprovalDecision) -> ApprovalRequest:
        """Mark approval as resolved and update dependent approvals."""
        approval = self.get_by_id(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")

        approval.status = ApprovalStatus.RESOLVED
        approval.resolution = decision
        approval.approved_at = datetime.now()
        approval.approval_duration_seconds = (
            approval.approved_at - approval.created_at
        ).total_seconds()

        # Remove this approval ID from dependencies of others
        for other in self.approvals:
            if approval_id in other.dependencies:
                other.dependencies.remove(approval_id)

        self.updated_at = datetime.now()

        return approval

    def park(self, approval_id: str) -> ApprovalRequest:
        """Park approval temporarily."""
        approval = self.get_by_id(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")

        approval.status = ApprovalStatus.PARKED
        self.updated_at = datetime.now()

        return approval

    def expire_old_approvals(self) -> list[ApprovalRequest]:
        """Expire approvals past their timeout. Returns list of expired."""
        expired = []

        for approval in self.approvals:
            if approval.status == ApprovalStatus.PENDING and approval.is_expired():
                approval.status = ApprovalStatus.EXPIRED
                expired.append(approval)

        if expired:
            self.updated_at = datetime.now()

        return expired

    def _is_resolved(self, approval_id: str) -> bool:
        """Check if approval is resolved."""
        approval = self.get_by_id(approval_id)
        return approval.status == ApprovalStatus.RESOLVED if approval else False

    def remove_completed(self) -> int:
        """Remove completed/failed approvals from queue. Returns count removed."""
        original_count = len(self.approvals)

        self.approvals = [
            a for a in self.approvals
            if a.status not in {ApprovalStatus.COMPLETED, ApprovalStatus.FAILED}
        ]

        removed_count = original_count - len(self.approvals)

        if removed_count > 0:
            self.updated_at = datetime.now()

        return removed_count


class ApprovalContext(BaseModel):
    """Approval context to inject into PM state for agentic handling."""

    has_pending_approvals: bool
    pending_count: int
    active_approval: ApprovalRequest | None
    recently_answered_questions: list[dict[str, str]] = Field(default_factory=list)
    approval_mode_active: bool = Field(
        default=False,
        description="Is PM currently in approval conversation?"
    )
    last_approval_interaction: datetime | None = None


# Serialization helpers for storage
def approval_request_to_dict(request: ApprovalRequest) -> dict[str, Any]:
    """Serialize ApprovalRequest for storage."""
    return request.model_dump(mode="json")


def approval_request_from_dict(data: dict[str, Any]) -> ApprovalRequest:
    """Deserialize ApprovalRequest from storage."""
    return ApprovalRequest.model_validate(data)


def approval_queue_to_dict(queue: ApprovalQueue) -> dict[str, Any]:
    """Serialize ApprovalQueue for storage."""
    return queue.model_dump(mode="json")


def approval_queue_from_dict(data: dict[str, Any]) -> ApprovalQueue:
    """Deserialize ApprovalQueue from storage."""
    return ApprovalQueue.model_validate(data)
