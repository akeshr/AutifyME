# Agentic Approval Implementation Roadmap

**Status**: Implementation Plan
**Created**: 2025-10-11
**Related**: `AGENTIC_APPROVAL_DESIGN.md`, `schemas/approval.py`

---

## Executive Summary

This document provides step-by-step implementation guidance for the agentic approval system, including:
- Detailed code changes for each phase
- Migration strategy from current static approval
- Testing approach with all permutation scenarios
- Rollback plans for each phase

**Critical Fix**: Phase 1 resolves immediate production bug (Trace 2 ValueError).
**Agentic Evolution**: Phases 2-5 transform approval into intelligent conversation.

---

## Phase 1: Fix State Corruption (Days 1-2) 🚨

**Goal**: Resolve `ValueError: Number of human responses (2) does not match number of hanging tool calls (1)`

**Root Cause**: Resuming at PM level causes task tool to re-invoke department with corrupted message history.

**Solution**: Resume at department level using isolated checkpoint namespace.

### Changes Required

#### 1.1 Update `InterruptCoordinator.process_interrupt()`

**File**: `agents/src/autifyme_agents/workflows/orchestration/interrupt_coordinator.py`

```python
def process_interrupt(
    self,
    interrupt: Interrupt,
    thread_id: str,
    pm_state: dict[str, Any],
    media_path: Path | None = None,
    agent_source: str = "cataloging_department",  # NEW
    checkpoint_ns: str | None = None,  # NEW
) -> ApprovalRequest:
    """Extract tool calls and create approval request."""

    # Existing logic...
    tool_calls = self._extract_tool_calls(interrupt, pm_state)
    save_call = self._find_save_product(tool_calls)
    draft = self._parse_draft(save_call["args"])

    # NEW: Determine checkpoint namespace
    if checkpoint_ns is None:
        # Infer from agent_source
        checkpoint_ns = f"task:{agent_source}"

    approval_request = ApprovalRequest(
        thread_id=thread_id,
        interrupt_id=interrupt.id or save_call.get("id") or thread_id,
        tool_call=save_call,
        draft=draft,
        checkpoint_id=pm_state.get("checkpoint_id", "unknown") if pm_state else "unknown",
        ai_message=self._extract_ai_message(pm_state),
        agent_source=agent_source,  # NEW
        checkpoint_ns=checkpoint_ns,  # NEW
    )

    # Persist (existing logic)
    self.state.save_pending_approval(...)

    return approval_request
```

#### 1.2 Update `InterruptCoordinator.resume_workflow()`

**File**: `agents/src/autifyme_agents/workflows/orchestration/interrupt_coordinator.py`

```python
def resume_workflow(
    self,
    thread_id: str,
    decision: Literal["approve", "reject"],
    pm_factory: Callable,  # Keep for backward compat, but won't use
) -> CatalogingResult | None:
    """Resume workflow after approval decision."""

    logger.info("Resuming workflow", extra={"thread_id": thread_id, "decision": decision})

    # Retrieve pending approval
    approval = self.state.get_pending_approval(thread_id)
    if not approval:
        raise WorkflowError("No pending approval found for this thread")

    if decision == "reject":
        logger.info("User rejected approval", extra={"thread_id": thread_id})
        self.state.delete_pending_approval(thread_id)
        return None

    # NEW: Build resume command
    command: Command = Command(
        resume={
            approval["interrupt_id"]: {
                "type": "accept",
                "args": None,
            }
        }
    )

    # NEW: Delete approval BEFORE resuming to prevent corruption
    self.state.delete_pending_approval(thread_id)

    # NEW: Resume at DEPARTMENT level, not PM
    agent_source = approval.get("agent_source", "cataloging_department")
    checkpoint_ns = approval.get("checkpoint_ns", f"task:{agent_source}")

    dept = self._create_department(agent_source)

    config = {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_ns": checkpoint_ns,  # ✅ Isolated namespace
        }
    }

    logger.debug(
        "Streaming department for workflow resumption",
        extra={
            "thread_id": thread_id,
            "agent_source": agent_source,
            "checkpoint_ns": checkpoint_ns,
        }
    )

    last_event = None
    try:
        for event in dept.stream(command, config=config, stream_mode="values"):
            last_event = event

            # Check for nested interrupts (shouldn't happen, but handle gracefully)
            if "__interrupt__" in event:
                logger.warning(
                    "Nested interrupt during resumption",
                    extra={"thread_id": thread_id}
                )
                return None

    except GeneratorExit:
        logger.warning(
            "GeneratorExit during workflow resumption",
            extra={"thread_id": thread_id}
        )
        return None
    except BaseException as e:
        logger.exception(
            "Unexpected error during workflow resumption",
            extra={"thread_id": thread_id, "error_type": type(e).__name__}
        )
        raise

    # Extract result from final event
    if last_event:
        result = self._extract_result(last_event)
        logger.info(
            "Workflow resumed successfully",
            extra={"thread_id": thread_id, "has_result": result is not None}
        )
        return result

    logger.warning("No result after workflow resumption", extra={"thread_id": thread_id})
    return None

def _create_department(self, agent_source: str):
    """Factory to create department agent by source."""
    if agent_source == "cataloging_department":
        from autifyme_agents.departments.cataloging_department import create_cataloging_department
        from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
        from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient

        return create_cataloging_department(
            checkpointer=get_checkpointer(),
            storage=SupabaseStorageClient(),
            enable_hitl=True,
        )

    raise ValueError(f"Unknown agent source: {agent_source}")
```

#### 1.3 Update `WorkflowRunner._handle_interrupt()`

**File**: `agents/src/autifyme_agents/workflows/orchestration/runner.py`

```python
def _handle_interrupt(
    self,
    sender: str,
    thread_id: str,
    interrupt: Interrupt,
    media_path: Path | None,
) -> None:
    """Delegate interrupt handling to coordinator."""

    logger.debug("Handling interrupt", extra={"thread_id": thread_id})

    try:
        if self._last_pm_state is None:
            raise ValueError("Cannot process interrupt without PM state")

        interrupt_for_processing = interrupt or self._last_interrupt
        if interrupt_for_processing is None:
            raise ValueError("No interrupt available for processing")

        # NEW: Pass agent context for department-level resume
        approval_request = self.interrupt_coord.process_interrupt(
            interrupt=interrupt_for_processing,
            thread_id=thread_id,
            pm_state=self._last_pm_state,
            media_path=media_path,
            agent_source="cataloging_department",  # NEW
            checkpoint_ns="task:cataloging_department",  # NEW
        )

        # Send approval request via channel
        self.channel.send_approval_request(sender, approval_request.draft)

    except Exception as exc:
        logger.exception("Failed to handle interrupt", exc_info=exc, extra={"thread_id": thread_id})

        # Critical: clear checkpoint to prevent stuck state
        try:
            self.recovery.clear_orphaned_state(thread_id)
        except Exception as clear_exc:
            logger.exception("Failed to clear checkpoint after interrupt error", exc_info=clear_exc)

        self.channel.send_error(
            sender,
            "processing",
            "I encountered an unexpected issue. Please try resending your product details.",
        )
```

#### 1.4 Update Storage Schema

**File**: `agents/src/autifyme_agents/core/ports.py`

```python
class StorageInterface(Protocol):
    """Port for storage operations."""

    def save_pending_approval(
        self,
        thread_id: str,
        interrupt_id: str,
        checkpoint_id: str,
        tool_call: dict[str, Any],
        draft_summary: str,
        ai_message: dict[str, Any] | None = None,
        image_path: str | None = None,
        agent_source: str = "cataloging_department",  # NEW
        checkpoint_ns: str | None = None,  # NEW
    ) -> None:
        """Persist approval request."""
        ...
```

**File**: `agents/src/autifyme_agents/integrations/storage/supabase_client.py`

Update `save_pending_approval()` to store `agent_source` and `checkpoint_ns`.

### Testing Phase 1

**Test Case 1**: Reproduce Trace 2 error and verify fix

```bash
# Setup: Create product with image
cd agents
uv run python -m autifyme_agents.cli.simulate \
  --text "Catalog this product" \
  --image "./test_fixtures/product.jpg"

# Should interrupt for approval
# Send approval
uv run python -m autifyme_agents.cli.simulate \
  --text "approve" \
  --thread-id <thread_from_above>

# ✅ Expected: Product saved successfully
# ❌ Before fix: ValueError about human responses mismatch
```

**Test Case 2**: Multiple approval-reject cycles

```bash
# Create → Interrupt → Reject → Create → Interrupt → Approve
# Should handle state cleanup correctly
```

**Test Case 3**: Approval after timeout

```bash
# Create → Interrupt → Wait 2 minutes → Approve
# Should handle GeneratorExit gracefully
```

---

## Phase 2: Remove Static Routing (Days 3-4)

**Goal**: Unify message handling - all messages go to PM with approval context.

### Changes Required

#### 2.1 Remove `_is_approval_message()` from Webhook

**File**: `agents/src/autifyme_agents/entrypoints/whatsapp_webhook.py`

```python
# REMOVE THIS FUNCTION
def _is_approval_message(text: str | None) -> bool:
    if not text:
        return False
    lowered = text.strip().lower()
    return lowered in {"approve", "reject"}  # ❌ DELETE

# UPDATE receive() function
@app.post("/webhook")
async def receive(request: Request) -> Any:
    body = await request.json()
    event_path = _persist_event(body)

    try:
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages")

                if not messages:
                    continue

                for message in messages:
                    message_id = message.get("id")
                    sender = message.get("from")
                    msg_type = message.get("type")

                    if not message_id or not sender:
                        continue

                    if _is_duplicate_message(message_id):
                        continue

                    text = message.get("text", {}).get("body")
                    media_id = message.get("image", {}).get("id") if msg_type == "image" else None

                    try:
                        # ✅ UNIFIED ROUTING - no more special approval handling
                        _get_runner().handle_message(sender, text, media_id)
                        _mark_message_processed(message_id)

                    except GeneratorExit:
                        logger.warning("Workflow streaming timed out")
                        continue
                    except Exception as workflow_exc:
                        logger.exception("Workflow execution failed")
                        _mark_message_processed(message_id)
                        continue

        return {"status": "processed"}
    except Exception as exc:
        logger.exception("Failed to handle webhook")
        raise HTTPException(status_code=500, detail="Internal error") from exc
```

#### 2.2 Remove `handle_approval()` from WorkflowRunner

**File**: `agents/src/autifyme_agents/workflows/orchestration/runner.py`

```python
# DELETE THIS METHOD
def handle_approval(
    self,
    sender: str,
    decision: Literal["approve", "reject"],
) -> None:
    """Process approval/rejection from user."""
    ...  # ❌ DELETE ENTIRE METHOD
```

#### 2.3 Update PM State to Include Approval Context

**File**: `agents/src/autifyme_agents/workflows/project_manager.py`

```python
def create_project_manager(
    company_profile: CompanyProfile,
    *,
    model: BaseChatModel | None = None,
    checkpointer: Any,
    storage: StorageInterface,
    tools: Sequence | None = None,
) -> Any:
    """Create PM with approval context in state."""

    # ... existing setup ...

    initial_state = {
        "company_profile": company_profile.model_dump(),
        "status": "idle",
        "plan": [],
        "current_step": 0,
        "department_results": {},
        "todos": [],
        "remaining_steps": 8,

        # NEW: Approval context
        "approval_queue": [],  # List of pending approvals
        "approval_mode": False,  # Is PM discussing approvals?
        "last_approval_interaction": None,
    }

    return project_manager.with_config({...})
```

### Testing Phase 2

**Test Case 1**: Natural language approval

```bash
# Create product → Interrupt
# Send "looks good!" instead of "approve"
# ✅ Should work (PM classifies intent)
```

**Test Case 2**: Approval with question

```bash
# Create product → Interrupt
# Send "What category is this?"
# ✅ PM should answer without breaking approval
```

---

## Phase 3: Intent Classification (Days 5-7)

**Goal**: LLM classifies approval intent instead of hardcoded keywords.

### Changes Required

#### 3.1 Create `ApprovalIntentClassifier`

**File**: `agents/src/autifyme_agents/workflows/orchestration/approval_classifier.py` (NEW)

```python
"""LLM-powered approval intent classification."""

from __future__ import annotations

from langchain.chat_models import BaseChatModel
from langchain.messages import SystemMessage, HumanMessage

from autifyme_agents.schemas.approval import ApprovalRequest, ApprovalDecision
from autifyme_agents.core.llm_factory import get_llm


class ApprovalIntentClassifier:
    """Classifies user messages during approval conversations."""

    def __init__(self, llm: BaseChatModel | None = None):
        self.llm = llm or get_llm(model="gpt-4o", temperature=0.1)
        self.structured_llm = self.llm.with_structured_output(ApprovalDecision)

    def classify(
        self,
        user_message: str,
        approval_context: ApprovalRequest,
        recent_history: list[dict[str, str]] | None = None,
    ) -> ApprovalDecision:
        """Classify user's approval message intent.

        Args:
            user_message: User's raw message
            approval_context: Pending approval details
            recent_history: Recent conversation for context

        Returns:
            Structured approval decision with intent and extracted data
        """

        prompt = self._build_classification_prompt(
            user_message=user_message,
            approval=approval_context,
            history=recent_history or [],
        )

        decision = self.structured_llm.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content=user_message),
        ])

        return decision

    def _build_classification_prompt(
        self,
        user_message: str,
        approval: ApprovalRequest,
        history: list[dict[str, str]],
    ) -> str:
        """Build classification prompt with approval context."""

        editable_fields_str = ", ".join(approval.editable_fields)
        preview_str = self._format_preview(approval.preview_data)

        history_str = ""
        if history:
            history_str = "\n\nRECENT CONVERSATION:\n"
            for msg in history[-5:]:  # Last 5 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_str += f"{role}: {content}\n"

        prompt = f"""You are an approval intent classifier for a product cataloging system.

PENDING ACTION:
{approval.action_description}

PRODUCT PREVIEW:
{preview_str}

EDITABLE FIELDS: {editable_fields_str}
{history_str}

USER MESSAGE:
{user_message}

Classify the user's intent and extract relevant details:

INTENTS:
- approve: User wants to proceed as-is ("yes", "looks good", "go ahead", etc.)
- approve_with_edits: User wants to modify fields ("change price to $25")
- reject: User wants to cancel ("no", "never mind", "cancel")
- question: User needs clarification ("what category?", "show similar products")
- defer: User wants to postpone ("remind me later", "ask me tomorrow")
- park: User wants to handle something else first ("wait, catalog this other product")
- abandon: User wants to completely cancel and reset ("forget everything")

EXTRACTION RULES:
- For approve_with_edits: Extract field-level edits into edited_fields dict
- For question: Extract question_text and clarification_needed list
- For defer: Extract defer_until datetime if specified
- Provide confidence score (0.0-1.0) based on clarity
- Explain reasoning concisely

EXAMPLES:
- "looks good!" → approve (confidence: 0.95)
- "change the price to 25 dollars" → approve_with_edits (edited_fields: {{"price": 25}})
- "what's the category?" → question (question_text: "what's the category?")
- "no thanks" → reject (confidence: 0.9)
"""

        return prompt

    def _format_preview(self, preview_data: dict) -> str:
        """Format preview data for display."""
        lines = []
        for key, value in preview_data.items():
            if value is not None:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)
```

#### 3.2 Update `InterruptCoordinator` to Use Classifier

**File**: `agents/src/autifyme_agents/workflows/orchestration/interrupt_coordinator.py`

```python
from autifyme_agents.workflows.orchestration.approval_classifier import ApprovalIntentClassifier
from autifyme_agents.schemas.approval import ApprovalDecision

class InterruptCoordinator:
    def __init__(
        self,
        state_manager: StateManager,
        classifier: ApprovalIntentClassifier | None = None,  # NEW
    ):
        self.state = state_manager
        self.classifier = classifier or ApprovalIntentClassifier()  # NEW

    def classify_approval_message(
        self,
        thread_id: str,
        user_message: str,
    ) -> tuple[ApprovalDecision | None, ApprovalRequest | None]:
        """Classify user message against pending approval.

        Returns:
            (decision, approval) tuple, or (None, None) if no pending approval
        """

        approval_dict = self.state.get_pending_approval(thread_id)
        if not approval_dict:
            return None, None

        # Convert dict to ApprovalRequest (with new fields)
        approval = self._dict_to_approval_request(approval_dict)

        # Classify intent
        decision = self.classifier.classify(
            user_message=user_message,
            approval_context=approval,
            recent_history=approval.get("conversation_history", []),
        )

        return decision, approval

    def resume_workflow(
        self,
        thread_id: str,
        decision: ApprovalDecision,  # ✅ Now takes ApprovalDecision, not string
        pm_factory: Callable,
    ) -> CatalogingResult | None:
        """Resume workflow after approval decision."""

        approval = self.state.get_pending_approval(thread_id)
        if not approval:
            raise WorkflowError("No pending approval found")

        # Handle different intents
        if decision.intent in {"reject", "abandon"}:
            self.state.delete_pending_approval(thread_id)
            return None

        if decision.intent == "question":
            # Answer question, don't resume workflow
            answer = self._answer_question(approval, decision.question_text)
            # Add to conversation history
            self._add_conversation_message(thread_id, "assistant", answer)
            return {"type": "question_answer", "answer": answer}

        if decision.intent == "defer":
            # Update expiration time
            self._defer_approval(thread_id, decision.defer_until)
            return {"type": "deferred", "until": decision.defer_until}

        if decision.intent == "park":
            self._park_approval(thread_id)
            return {"type": "parked"}

        # approve or approve_with_edits
        edited_args = None
        if decision.intent == "approve_with_edits":
            edited_args = decision.edited_fields

        # Resume workflow
        command_type = "accept" if not edited_args else "edit"
        command = Command(
            resume={
                approval["interrupt_id"]: {
                    "type": command_type,
                    "args": edited_args,
                }
            }
        )

        # Delete approval BEFORE resuming
        self.state.delete_pending_approval(thread_id)

        # Resume at department level (Phase 1 logic)
        dept = self._create_department(approval.get("agent_source"))
        config = {...}

        for event in dept.stream(command, config=config):
            if result := self._extract_result(event):
                return result

        return None

    def _answer_question(self, approval: dict, question: str) -> str:
        """Answer user question about pending approval."""

        # Simple Q&A for now, can be enhanced with RAG later
        draft = approval.get("draft_summary", "")
        preview = approval.get("preview_data", {})

        # Use LLM to answer question about the draft
        prompt = f"""Answer the user's question about this product draft:

DRAFT:
{draft}

QUESTION:
{question}

Provide a clear, concise answer."""

        response = self.classifier.llm.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content=question),
        ])

        return response.content
```

#### 3.3 Update `WorkflowRunner` to Use Classification

**File**: `agents/src/autifyme_agents/workflows/orchestration/runner.py`

```python
def _execute_workflow(
    self,
    thread_id: str,
    sender: str,
    text: str | None,
    media_id: str | None,
) -> None:
    """Core workflow execution with approval awareness."""

    # NEW: Check for pending approval first
    decision, approval = self.interrupt_coord.classify_approval_message(
        thread_id=thread_id,
        user_message=text or "",
    )

    if decision and approval:
        # This message is about pending approval
        logger.info(
            "Message classified as approval-related",
            extra={
                "thread_id": thread_id,
                "intent": decision.intent,
                "confidence": decision.confidence,
            }
        )

        result = self.interrupt_coord.resume_workflow(
            thread_id=thread_id,
            decision=decision,
            pm_factory=lambda: self._create_project_manager(),
        )

        # Handle different result types
        if result and result.get("type") == "question_answer":
            self.channel.send_text(sender, result["answer"])
            return

        if result and result.get("type") == "deferred":
            self.channel.send_text(
                sender,
                f"I'll remind you about this approval later."
            )
            return

        if result and result.get("type") == "parked":
            self.channel.send_text(sender, "Got it. What would you like to do?")
            return

        if result:
            # Approval completed, workflow resumed
            self.channel.send_completion(sender, result)
            return

        # Rejection
        self.channel.send_text(sender, "Understood. No changes made.")
        return

    # No pending approval, proceed with normal workflow
    # ... existing PM invocation logic ...
```

### Testing Phase 3

**Comprehensive Intent Test Matrix**:

```python
# Create test file: agents/tests/integration/test_approval_intents.py

import pytest
from autifyme_agents.workflows.orchestration.approval_classifier import ApprovalIntentClassifier
from autifyme_agents.schemas.approval import ApprovalRequest, ApprovalIntent

@pytest.fixture
def classifier():
    return ApprovalIntentClassifier()

@pytest.fixture
def sample_approval():
    return ApprovalRequest(
        id="test_123",
        thread_id="thread_123",
        action="save_product",
        action_description="Save product to catalog",
        agent_source="cataloging_department",
        checkpoint_ns="task:cataloging_department",
        preview_data={"name": "Test Product", "price": 25.0},
        preview_message="Product: Test Product\nPrice: $25.00",
        editable_fields=["name", "description", "price", "sizes", "colors"],
        validation_schema={},
    )

# Test approve intent
@pytest.mark.parametrize("message", [
    "approve",
    "yes",
    "looks good",
    "go ahead",
    "perfect!",
    "that works",
])
def test_approve_intent(classifier, sample_approval, message):
    decision = classifier.classify(message, sample_approval)
    assert decision.intent == ApprovalIntent.APPROVE
    assert decision.confidence > 0.7

# Test approve_with_edits intent
@pytest.mark.parametrize("message,expected_edits", [
    ("change price to $30", {"price": 30.0}),
    ("name should be Blue Container", {"name": "Blue Container"}),
    ("set price to 25 and name to Red Box", {"price": 25.0, "name": "Red Box"}),
])
def test_approve_with_edits(classifier, sample_approval, message, expected_edits):
    decision = classifier.classify(message, sample_approval)
    assert decision.intent == ApprovalIntent.APPROVE_WITH_EDITS
    assert decision.edited_fields == expected_edits

# Test reject intent
@pytest.mark.parametrize("message", [
    "reject",
    "no",
    "cancel",
    "never mind",
    "not good",
])
def test_reject_intent(classifier, sample_approval, message):
    decision = classifier.classify(message, sample_approval)
    assert decision.intent == ApprovalIntent.REJECT

# Test question intent
@pytest.mark.parametrize("message", [
    "what category is this?",
    "can you show me similar products?",
    "what happens after I approve?",
])
def test_question_intent(classifier, sample_approval, message):
    decision = classifier.classify(message, sample_approval)
    assert decision.intent == ApprovalIntent.QUESTION
    assert decision.question_text is not None

# Test park intent
@pytest.mark.parametrize("message", [
    "wait, catalog this other product first",
    "hold on, let me think",
    "pause this",
])
def test_park_intent(classifier, sample_approval, message):
    decision = classifier.classify(message, sample_approval)
    assert decision.intent == ApprovalIntent.PARK
```

---

## Phase 4: Approval Queue (Days 8-10)

**Goal**: Support multiple pending approvals with dependencies.

See `schemas/approval.py` for `ApprovalQueue` implementation.

### Changes Required

#### 4.1 Create `ApprovalQueueManager`

**File**: `agents/src/autifyme_agents/workflows/orchestration/approval_queue_manager.py` (NEW)

```python
"""Manages approval queues with dependency tracking."""

from __future__ import annotations

from datetime import datetime

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.schemas.approval import (
    ApprovalQueue,
    ApprovalRequest,
    ApprovalDecision,
    approval_queue_to_dict,
    approval_queue_from_dict,
)
from autifyme_agents.core.logging_config import get_logger

logger = get_logger(__name__)


class ApprovalQueueManager:
    """Manages approval queues for threads."""

    def __init__(self, storage: StorageInterface):
        self.storage = storage

    def get_queue(self, thread_id: str) -> ApprovalQueue:
        """Get approval queue for thread."""
        queue_data = self.storage.get_approval_queue(thread_id)

        if queue_data:
            return approval_queue_from_dict(queue_data)

        # Create new empty queue
        return ApprovalQueue(thread_id=thread_id)

    def save_queue(self, queue: ApprovalQueue) -> None:
        """Persist approval queue."""
        queue_data = approval_queue_to_dict(queue)
        self.storage.save_approval_queue(queue.thread_id, queue_data)

    def enqueue(self, thread_id: str, request: ApprovalRequest) -> None:
        """Add approval to queue."""
        queue = self.get_queue(thread_id)
        queue.add(request)
        self.save_queue(queue)

        logger.info(
            "Approval enqueued",
            extra={
                "thread_id": thread_id,
                "approval_id": request.id,
                "action": request.action,
            }
        )

    def get_next_pending(self, thread_id: str) -> ApprovalRequest | None:
        """Get next approvable item."""
        queue = self.get_queue(thread_id)

        # Expire old approvals first
        expired = queue.expire_old_approvals()
        if expired:
            self.save_queue(queue)
            logger.info(f"Expired {len(expired)} old approvals", extra={"thread_id": thread_id})

        return queue.get_next_pending()

    def resolve(
        self,
        thread_id: str,
        approval_id: str,
        decision: ApprovalDecision,
    ) -> ApprovalRequest:
        """Mark approval as resolved."""
        queue = self.get_queue(thread_id)
        approval = queue.resolve(approval_id, decision)
        self.save_queue(queue)

        logger.info(
            "Approval resolved",
            extra={
                "thread_id": thread_id,
                "approval_id": approval_id,
                "intent": decision.intent,
            }
        )

        return approval

    def park(self, thread_id: str, approval_id: str) -> ApprovalRequest:
        """Park approval temporarily."""
        queue = self.get_queue(thread_id)
        approval = queue.park(approval_id)
        self.save_queue(queue)

        logger.info(
            "Approval parked",
            extra={"thread_id": thread_id, "approval_id": approval_id}
        )

        return approval
```

#### 4.2 Update Storage Interface

**File**: `agents/src/autifyme_agents/core/ports.py`

```python
class StorageInterface(Protocol):
    """Port for storage operations."""

    # ... existing methods ...

    def save_approval_queue(self, thread_id: str, queue_data: dict[str, Any]) -> None:
        """Persist approval queue for thread."""
        ...

    def get_approval_queue(self, thread_id: str) -> dict[str, Any] | None:
        """Retrieve approval queue for thread."""
        ...
```

#### 4.3 Implement in Supabase Client

**File**: `agents/src/autifyme_agents/integrations/storage/supabase_client.py`

```python
def save_approval_queue(self, thread_id: str, queue_data: dict[str, Any]) -> None:
    """Persist approval queue."""
    self.client.table("approval_queues").upsert({
        "thread_id": thread_id,
        "queue_data": queue_data,
        "updated_at": datetime.now().isoformat(),
    }).execute()

def get_approval_queue(self, thread_id: str) -> dict[str, Any] | None:
    """Retrieve approval queue."""
    result = self.client.table("approval_queues").select("*").eq("thread_id", thread_id).execute()

    if result.data:
        return result.data[0]["queue_data"]

    return None
```

**Database Migration**:

```sql
CREATE TABLE approval_queues (
    thread_id TEXT PRIMARY KEY,
    queue_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_approval_queues_updated ON approval_queues(updated_at);
```

### Testing Phase 4

**Test Case: Sequential Approvals**

```bash
# Workflow: Save Product → Post Instagram → Email Suppliers
# Should create 3 approval requests with dependencies

# Approve #1 (save) → Should trigger #2 (post)
# Approve #2 (post) → Should trigger #3 (email)
```

**Test Case: Out-of-Order Approval**

```bash
# Create 3 independent approvals (A, B, C)
# Approve B first → Should work
# Approve C → Should work
# Approve A → Should work
```

---

## Phase 5: Rich Preview & PM Tools (Days 11-14)

**Goal**: Give PM tools to manage approvals naturally.

### Changes Required

#### 5.1 Create PM Approval Tools

**File**: `agents/src/autifyme_agents/tools/approval_tools.py` (NEW)

```python
"""PM tools for managing approvals."""

from langchain.tools import tool

from autifyme_agents.workflows.orchestration.approval_queue_manager import ApprovalQueueManager
from autifyme_agents.schemas.approval import ApprovalRequest


def create_approval_tools(queue_manager: ApprovalQueueManager):
    """Factory for PM approval tools."""

    @tool
    def check_pending_approvals(thread_id: str) -> list[dict]:
        """Check if there are pending approvals for this conversation.

        Returns list of pending approvals with previews.
        Use this when user sends a message to see if they're responding to an approval.
        """
        queue = queue_manager.get_queue(thread_id)
        pending = queue.get_all_pending()

        return [
            {
                "id": approval.id,
                "action": approval.action_description,
                "preview": approval.preview_message,
                "editable_fields": approval.editable_fields,
                "created_ago_seconds": (datetime.now() - approval.created_at).total_seconds(),
            }
            for approval in pending
        ]

    @tool
    def resume_approved_action(
        thread_id: str,
        approval_id: str,
        edited_fields: dict[str, Any] | None = None,
    ) -> dict:
        """Resume a pending action after user approval.

        Use this when user approves an action, optionally with edits.

        Args:
            thread_id: Conversation thread
            approval_id: Which approval to resume
            edited_fields: Optional field edits (e.g., {"price": 25.0})

        Returns:
            Result of executing the approved action
        """
        # This will be called by InterruptCoordinator.resume_workflow()
        # Implementation delegates to coordinator
        ...

    @tool
    def answer_approval_question(
        thread_id: str,
        approval_id: str,
        question: str,
    ) -> str:
        """Answer user's question about a pending approval.

        Use this when user asks clarifying questions without approving yet.
        """
        ...

    @tool
    def park_approval_for_new_request(thread_id: str, approval_id: str) -> None:
        """Temporarily park an approval to handle a new user request.

        Use when user wants to do something else before deciding.
        """
        queue_manager.park(thread_id, approval_id)

    return [
        check_pending_approvals,
        resume_approved_action,
        answer_approval_question,
        park_approval_for_new_request,
    ]
```

#### 5.2 Update PM Creation with Approval Tools

**File**: `agents/src/autifyme_agents/workflows/project_manager.py`

```python
def create_project_manager(
    company_profile: CompanyProfile,
    *,
    model: BaseChatModel | None = None,
    checkpointer: Any,
    storage: StorageInterface,
    tools: Sequence | None = None,
    queue_manager: ApprovalQueueManager | None = None,  # NEW
) -> Any:
    """Create PM with approval tools."""

    if queue_manager is None:
        queue_manager = ApprovalQueueManager(storage)

    # PM tools include approval management
    pm_tools = list(tools) if tools is not None else []

    # Add approval tools
    approval_tools = create_approval_tools(queue_manager)
    pm_tools.extend(approval_tools)

    # ... rest of PM creation ...
```

#### 5.3 Update PM Prompt with Approval Guidance

**File**: `agents/prompts/project_manager.prompt`

```
You are the Project Manager for {company_name}.

...

## APPROVAL MANAGEMENT

Before processing any user message:
1. Check for pending approvals using check_pending_approvals tool
2. If approvals exist, analyze if user message relates to them:
   - Natural approval phrases: "yes", "looks good", "go ahead" → resume_approved_action
   - Edit requests: "change price to $25" → resume_approved_action with edited_fields
   - Questions: "what category?" → answer_approval_question
   - Context switch: "wait, do this instead" → park_approval_for_new_request
3. If no pending approvals OR message is clearly a new request, proceed with normal delegation

IMPORTANT:
- NEVER assume "approve"/"reject" keywords - understand natural language intent
- ALWAYS provide context when resuming: "I'll save the product with your changes"
- If user edits, validate edits match editable_fields before resuming
- If unclear, ask clarifying questions

...
```

---

## Migration Strategy

### Backward Compatibility

**Phase 1-2**: Keep old `handle_approval()` as deprecated wrapper:

```python
def handle_approval(self, sender: str, decision: str) -> None:
    """DEPRECATED: Use handle_message() instead.

    This method exists for backward compatibility during migration.
    """
    logger.warning("handle_approval() is deprecated, use handle_message()")

    # Convert to new decision format
    if decision.lower() == "approve":
        intent = ApprovalIntent.APPROVE
    elif decision.lower() == "reject":
        intent = ApprovalIntent.REJECT
    else:
        intent = ApprovalIntent.QUESTION

    decision_obj = ApprovalDecision(
        intent=intent,
        confidence=1.0,
        reasoning="Legacy approval handler",
        original_message=decision,
    )

    # Route through new system
    self.handle_message(sender, decision, None)
```

### Data Migration

**Existing pending approvals**: Migrate on first access

```python
def get_pending_approval(self, thread_id: str) -> dict[str, Any] | None:
    """Get pending approval with automatic schema upgrade."""

    data = self._raw_get_pending_approval(thread_id)

    if not data:
        return None

    # Upgrade old schema to new
    if "agent_source" not in data:
        data["agent_source"] = "cataloging_department"

    if "checkpoint_ns" not in data:
        data["checkpoint_ns"] = "task:cataloging_department"

    # Save upgraded schema
    self._raw_save_pending_approval(thread_id, data)

    return data
```

---

## Rollback Plans

### Phase 1 Rollback

If department-level resume causes issues:

1. Revert `InterruptCoordinator.resume_workflow()` to PM-level resume
2. Keep `agent_source`/`checkpoint_ns` fields for future attempts
3. Add feature flag: `ENABLE_DEPT_LEVEL_RESUME=false`

### Phase 2 Rollback

If unified routing breaks:

1. Re-add `_is_approval_message()` to webhook
2. Re-add `handle_approval()` to runner
3. Feature flag: `ENABLE_UNIFIED_ROUTING=false`

### Phase 3 Rollback

If LLM classification is unreliable:

1. Fallback to keyword matching for low-confidence classifications
2. Add confidence threshold: Only use LLM if confidence > 0.8
3. Feature flag: `ENABLE_LLM_CLASSIFICATION=false`

---

## Success Metrics

### Phase 1
- ✅ No ValueError exceptions in production
- ✅ Approval resume success rate > 95%

### Phase 2
- ✅ All messages route through single handler
- ✅ No approval-specific code in webhook

### Phase 3
- ✅ Natural language approval success rate > 90%
- ✅ Intent classification accuracy > 85%
- ✅ Edit extraction accuracy > 80%

### Phase 4
- ✅ Multi-action workflows complete successfully
- ✅ Out-of-order approvals work correctly
- ✅ Dependency resolution works

### Phase 5
- ✅ PM proactively manages approvals with tools
- ✅ Rich previews render correctly
- ✅ Edit validation prevents invalid data

---

## Related Documents

- `AGENTIC_APPROVAL_DESIGN.md` - Design principles and scenarios
- `schemas/approval.py` - State schemas
- `LANGCHAIN_V1_FEATURES.md` - HITL middleware reference
