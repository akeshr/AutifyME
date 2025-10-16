# PM-Centric HITL Implementation Guide

**Pattern:** 2 (PM-Centric with Custom Tools)
**Scope:** Move approval orchestration logic INTO the PM agent
**Status:** Ready for Implementation
**Effort:** 1-2 days

---

## Architecture Overview

### Before (Current - Runner-Centric)

```
┌─────────────────────────────────────────────────────┐
│ WorkflowRunner                                      │
│  • Check checkpoint for interrupts                  │
│  • Call ApprovalAnalyzer (external)                 │
│  • Build Command from response                      │
│  • Execute Command to resume                        │
└─────────────────────────────────────────────────────┘
              ↓
       ┌──────────────┐
       │ PM Agent     │ (No HITL logic)
       │ (delegates)  │
       └──────────────┘
              ↓
       ┌──────────────┐
       │ Departments  │ (Raise interrupts)
       └──────────────┘
```

### After (Proposed - PM-Centric)

```
┌─────────────────────────────────────────────────────┐
│ WorkflowRunner                                      │
│  • Check checkpoint for interrupts                  │
│  • Forward to PM with pending_interrupts in state   │
│  • Intercept approval tool output                   │
│  • Build Command & execute                          │
└─────────────────────────────────────────────────────┘
              ↓
       ┌──────────────────────────┐
       │ PM Agent (+ HITL Tools)  │
       │  • Read pending_interrupts│
       │  • Reason about approvals │
       │  • Call approval tools    │
       └──────────────────────────┘
              ↓
       ┌──────────────┐
       │ Departments  │
       └──────────────┘
```

---

## Implementation Steps

### Step 1: Create PM HITL Middleware

**File:** `agents/src/autifyme_agents/workflows/middleware/pm_hitl.py`

```python
"""PM-level HITL middleware for approval context injection."""

from __future__ import annotations

import logging
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware

logger = logging.getLogger(__name__)


class PMHITLMiddleware(AgentMiddleware):
    """Injects pending approval context before PM reasoning.

    This middleware:
    1. Detects pending_interrupts in state
    2. Formats them as human-readable context
    3. Injects into model request (before PM reasons)
    4. Enables PM to reason about pending approvals

    Example state modification:
        Before: {"pending_interrupts": [...], "messages": [...]}
        After: {"pending_interrupts": [...], "messages": [...],
                "approval_context": "Waiting for: Product A (edit), Item B (accept)"}
    """

    def __init__(self, *, include_details: bool = True):
        """Initialize HITL middleware.

        Args:
            include_details: Include interrupt details in context
        """
        self.include_details = include_details
        logger.debug("PMHITLMiddleware initialized")

    @property
    def name(self) -> str:
        return "pm_hitl_context"

    def before_agent(self, state: dict[str, Any], runtime: Any) -> dict[str, Any] | None:
        """Inject pending approval context before PM reasoning.

        Args:
            state: Current agent state
            runtime: LangGraph runtime context

        Returns:
            State modifications (approval_context), or None if no pending interrupts
        """
        # Extract pending interrupts
        pending_interrupts = state.get("pending_interrupts", [])

        if not pending_interrupts:
            logger.debug("No pending interrupts - no context injection")
            return None

        logger.info(
            "Injecting approval context",
            extra={"interrupt_count": len(pending_interrupts)},
        )

        # Format interrupts as readable context
        context_lines = [
            "The following items are waiting for your approval decisions:"
        ]

        for idx, interrupt_info in enumerate(pending_interrupts, 1):
            description = interrupt_info.get("description", "Unknown action")
            interrupt_id = interrupt_info.get("interrupt_id", f"interrupt_{idx}")

            if self.include_details:
                tool_name = interrupt_info.get("tool_name", "unknown")
                context_lines.append(f"\n{idx}. [{interrupt_id}] {description}")
                context_lines.append(f"   Tool: {tool_name}")
            else:
                context_lines.append(f"\n{idx}. {description}")

        approval_context = "\n".join(context_lines)

        logger.debug(
            "Built approval context",
            extra={"context_length": len(approval_context)},
        )

        # Return state modifications that will be merged
        return {
            "approval_context": approval_context,
        }

    def after_agent(
        self, state: dict[str, Any], runtime: Any
    ) -> dict[str, Any] | None:
        """Optional: Post-processing after PM completes.

        Could be used to:
        - Track which approvals PM decided on
        - Validate approval decisions
        - Record reasoning

        Args:
            state: Current agent state after PM reasoning
            runtime: LangGraph runtime context

        Returns:
            State modifications, or None
        """
        # Current implementation: no post-processing needed
        return None
```

### Step 2: Add Approval Tools to PM

**File:** `agents/src/autifyme_agents/workflows/tools/pm_approval_tools.py`

```python
"""Tools for PM to make approval decisions.

These tools enable the PM to reason about and decide on pending approvals.
Runner intercepts the tool output and converts to Command objects.
"""

from __future__ import annotations

import logging
from typing import Literal

from deepagents.tools import tool
from langchain_core.tools import ToolException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ApprovalDecision(BaseModel):
    """Structured approval decision from PM.

    This Pydantic model ensures type-safe communication between PM and Runner.
    """

    interrupt_id: str = Field(
        description="Unique identifier for the interrupt to resume"
    )
    decision_type: Literal["accept", "reject", "edit", "clarify"] = Field(
        description="Type of decision: accept (proceed), reject (abort), "
        "edit (modify), clarify (need more info)"
    )
    edited_args: dict = Field(
        default_factory=dict,
        description="Modified arguments if decision is 'edit'",
    )
    reasoning: str = Field(
        default="",
        description="Brief reasoning for the decision",
    )


@tool
def propose_workflow_resumption(
    interrupt_id: str,
    decision: Literal["accept", "reject", "edit", "clarify"],
    edited_args: dict = None,
    reasoning: str = None,
) -> str:
    """Propose how to resume a paused approval workflow.

    This tool allows the PM to reason about and decide on pending approvals.
    The Runner intercepts this tool call and converts it to a LangGraph Command
    to resume the workflow.

    Args:
        interrupt_id: ID of the interrupt to resume (from pending_interrupts)
        decision: Type of decision
        edited_args: Modified data (if decision is 'edit')
        reasoning: Brief explanation of decision

    Returns:
        Confirmation message

    Example:
        PM: "The product price looks reasonable, I'll approve it"
        → Tool call: propose_workflow_resumption(
              interrupt_id="int_1",
              decision="accept",
              reasoning="Price within acceptable range"
          )
        → Tool output: "Approved interrupt int_1: accept"
        → Runner intercepts and builds:
            Command(resume={"int_1": [{"type": "accept", "args": None}]})
    """
    edited_args = edited_args or {}
    reasoning = reasoning or ""

    try:
        # Validate decision
        decision_obj = ApprovalDecision(
            interrupt_id=interrupt_id,
            decision_type=decision,
            edited_args=edited_args,
            reasoning=reasoning,
        )

        logger.info(
            "PM proposed workflow resumption",
            extra={
                "interrupt_id": interrupt_id,
                "decision": decision,
                "has_edits": len(edited_args) > 0,
            },
        )

        # Tool output format that Runner can intercept
        return f"APPROVAL_DECISION: {interrupt_id}:{decision}"

    except Exception as e:
        logger.warning(
            "Invalid approval decision",
            extra={"error": str(e), "interrupt_id": interrupt_id},
        )
        raise ToolException(f"Invalid approval decision: {str(e)}")


@tool
def reject_workflow_approval(interrupt_id: str, reason: str) -> str:
    """Explicitly reject an approval request.

    Shorthand for propose_workflow_resumption with decision='reject'.

    Args:
        interrupt_id: ID of interrupt to reject
        reason: Explanation for rejection

    Returns:
        Confirmation message
    """
    try:
        logger.info(
            "PM rejected workflow approval",
            extra={"interrupt_id": interrupt_id, "reason": reason[:100]},
        )
        return f"APPROVAL_DECISION: {interrupt_id}:reject"
    except Exception as e:
        raise ToolException(f"Rejection failed: {str(e)}")


@tool
def request_approval_clarification(interrupt_id: str, question: str) -> str:
    """Ask for clarification before making approval decision.

    This tool communicates back to the user via the Runner that PM needs
    more information before deciding.

    Args:
        interrupt_id: ID of interrupt needing clarification
        question: The clarification question

    Returns:
        Confirmation that question was sent
    """
    try:
        logger.info(
            "PM requested clarification",
            extra={"interrupt_id": interrupt_id, "question": question[:100]},
        )
        return f"CLARIFICATION_REQUESTED: {interrupt_id}"
    except Exception as e:
        raise ToolException(f"Clarification request failed: {str(e)}")
```

### Step 3: Update Project Manager

**File:** `agents/src/autifyme_agents/workflows/project_manager.py`

```python
# In create_project_manager() function

def create_project_manager(
    company_profile: CompanyProfile,
    *,
    model: BaseChatModel | None = None,
    checkpointer: Any,
    storage: StorageInterface,
    channel: MessagingChannel | None = None,
    tools: Sequence[Any] | None = None,
) -> Any:
    """Create the deepagents-powered Project Manager with HITL approval tools.

    ... existing docstring ...
    """

    # ... existing code ...

    # PM orchestration tools (including HITL)
    from autifyme_agents.workflows.tools.pm_approval_tools import (
        propose_workflow_resumption,
        reject_workflow_approval,
        request_approval_clarification,
    )

    pm_tools = [
        write_todos,
        propose_workflow_resumption,    # NEW: Approval decision
        reject_workflow_approval,        # NEW: Shorthand rejection
        request_approval_clarification,  # NEW: Ask for clarification
    ]

    # ... add explicit tools if needed ...
    if tools is not None:
        pm_tools.extend(tools)

    # HITL middleware for context injection
    from autifyme_agents.workflows.middleware.pm_hitl import PMHITLMiddleware

    middleware = [
        PMHITLMiddleware(include_details=True),  # NEW: Inject approval context
    ]

    # ... rest of create_deep_agent call ...

    project_manager = create_deep_agent(
        tools=pm_tools,
        instructions=instructions,
        model=llm,
        subagents=subagents,
        tool_configs={},  # Departments handle their own HITL
        checkpointer=checkpointer,
        middleware=middleware,  # NEW: Pass middleware
    )

    # ... rest of function ...
```

### Step 4: Update Runner to Intercept Approval Tool Output

**File:** `agents/src/autifyme_agents/workflows/orchestration/runner_v2.py`

```python
# In _invoke_pm() method

def _invoke_pm(
    self,
    thread_id: str,
    raw_payload: dict[str, Any],
) -> tuple[dict[str, Any] | None, Any | None]:
    """Invoke PM with raw message payload.

    Enhanced to handle PM approval tool output.
    """

    # ... existing code to check pending interrupts ...

    if pending_interrupts_list:
        # === NEW: PM-CENTRIC APPROVAL FLOW ===
        # Instead of ApprovalAnalyzer, let PM decide

        logger.info(
            "Routing to PM for approval decision",
            extra={
                "thread_id": thread_id,
                "interrupt_count": len(pending_interrupts_list),
            },
        )

        # Create payload with pending_interrupts in state
        payload = {
            "messages": [HumanMessage(content=json.dumps(raw_payload))],
            "pending_interrupts": pending_interrupts_list,  # NEW: For PM context
        }

        last_event = None
        interrupt_value = None
        approval_tool_output = None

        try:
            for event in pm.stream(payload, config=config, stream_mode="values"):
                last_event = event

                # NEW: Check for PM approval tool output
                if "messages" in event:
                    for msg in event["messages"]:
                        # Check for approval decision marker
                        msg_content = str(getattr(msg, "content", ""))
                        if "APPROVAL_DECISION:" in msg_content:
                            approval_tool_output = msg_content
                            logger.info(
                                "Captured PM approval decision",
                                extra={"thread_id": thread_id, "output": msg_content[:50]},
                            )

                # Check for new interrupts (nested workflows)
                if "__interrupt__" in event:
                    interrupts = event.get("__interrupt__") or []
                    if interrupts:
                        interrupt_value = interrupts[0].value

            # NEW: If PM made approval decision, build Command and resume
            if approval_tool_output:
                logger.info(
                    "Building Command from PM approval",
                    extra={"thread_id": thread_id},
                )

                # Parse approval output
                # Format: "APPROVAL_DECISION: interrupt_id:decision_type"
                approval_cmd = self._build_command_from_pm_approval(
                    approval_tool_output, pending_interrupts_list
                )

                # Execute Command to resume
                for resume_event in pm.stream(approval_cmd, config=config, stream_mode="values"):
                    last_event = resume_event

                    # Check for new interrupts (nested)
                    if "__interrupt__" in resume_event:
                        interrupts = resume_event.get("__interrupt__") or []
                        if interrupts:
                            interrupt_value = interrupts[0].value

                logger.info(
                    "PM-approved workflow resumed",
                    extra={"thread_id": thread_id},
                )

            return last_event, interrupt_value

        except Exception as e:
            logger.exception(
                "PM-centric approval flow error",
                extra={"thread_id": thread_id},
            )
            raise

    else:
        # ... existing code for no-interrupt path ...
        pass


def _build_command_from_pm_approval(
    self,
    approval_output: str,
    pending_interrupts: list[dict[str, Any]],
) -> Command[Any]:
    """Build Command from PM approval tool output.

    Args:
        approval_output: Output from propose_workflow_resumption tool
        pending_interrupts: List of pending interrupts

    Returns:
        Command object for resuming workflow

    Example:
        approval_output: "APPROVAL_DECISION: int_1:accept"
        → Command(resume={"int_1": [{"type": "accept"}]})
    """
    try:
        # Parse: "APPROVAL_DECISION: interrupt_id:decision_type"
        parts = approval_output.split(":")
        if len(parts) < 3:
            raise ValueError(f"Invalid format: {approval_output}")

        interrupt_id = parts[1].strip()
        decision_type = parts[2].strip()

        logger.debug(
            "Parsed PM approval",
            extra={"interrupt_id": interrupt_id, "decision": decision_type},
        )

        # Find original interrupt info for context
        matching_interrupt = None
        for interrupt_info in pending_interrupts:
            if interrupt_id in interrupt_info.get("interrupt_id", ""):
                matching_interrupt = interrupt_info
                break

        # Build resume data based on decision type
        if decision_type == "accept":
            resume_data = {"type": "accept", "args": None}
        elif decision_type == "reject":
            resume_data = {"type": "reject", "args": None}
        else:
            # Default to accept if unclear
            resume_data = {"type": "accept", "args": None}

        logger.info(
            "Built Command from PM approval",
            extra={
                "interrupt_id": interrupt_id,
                "decision": decision_type,
            },
        )

        return Command(resume={interrupt_id: [resume_data]})

    except Exception as e:
        logger.error(
            "Failed to build Command from PM approval",
            extra={"error": str(e), "output": approval_output},
        )
        raise
```

### Step 5: Update PM Instructions

**File:** `agents/src/autifyme_agents/prompts/project_manager.prompt`

Add section about approval handling:

```
## Approval Workflow

When the system detects pending approvals (shown in the context below):
1. Carefully analyze each pending item
2. Check if all required information is available
3. If you need clarification, use request_approval_clarification()
4. Make your decision using propose_workflow_resumption():
   - "accept": Item is ready, proceed with execution
   - "reject": Item has issues, abort workflow
   - "edit": Modifications needed, specify edited_args
   - "clarify": Need more information

Example:
- Pending: Product "Sneakers" with price $120
- Your reasoning: Price is within range, description is complete
- Action: propose_workflow_resumption(
    interrupt_id="int_1",
    decision="accept",
    reasoning="Price approved, all details provided"
  )

Always provide clear reasoning for your decisions.
```

---

## Testing Strategy

### Test 1: Middleware Injects Context

```python
# tests/unit/workflows/middleware/test_pm_hitl.py

def test_pm_hitl_middleware_injects_context():
    """Verify middleware injects approval context before PM reasoning"""
    middleware = PMHITLMiddleware()

    state = {
        "pending_interrupts": [
            {
                "interrupt_id": "int_1",
                "description": "Product approval",
                "tool_name": "save_product",
            }
        ],
        "messages": [],
    }

    result = middleware.before_agent(state, None)

    assert result is not None
    assert "approval_context" in result
    assert "Product approval" in result["approval_context"]
```

### Test 2: PM Calls Approval Tool

```python
# tests/integration/test_pm_approval_flow.py

def test_pm_makes_approval_decision():
    """Verify PM can call approval tools and Runner intercepts"""
    # Set up PM with pending interrupt
    state = {
        "messages": [HumanMessage(content="Approve this")],
        "pending_interrupts": [
            {
                "interrupt_id": "int_1",
                "description": "Product draft",
            }
        ],
    }

    # Run PM
    events = list(pm.stream(state, config=config))

    # Check that approval tool was called
    approval_outputs = [
        msg for msg in events if "APPROVAL_DECISION" in str(msg.get("messages", []))
    ]

    assert len(approval_outputs) > 0
```

### Test 3: Runner Builds Command from PM Decision

```python
# tests/integration/test_runner_approval_interception.py

def test_runner_intercepts_and_resumes():
    """Verify Runner intercepts PM approval and builds Command"""
    runner = WorkflowRunner(...)

    # Handle message with pending interrupt
    runner.handle_message(
        sender="test",
        text="Approve",
        pending_interrupts=[{"interrupt_id": "int_1", ...}],
    )

    # Verify Command was executed (via mocked stream)
    assert stream_called_with_command.called
```

---

## Rollout Plan

### Phase 1: Deploy & Monitor

1. Deploy middleware to staging
2. Deploy approval tools
3. Update PM instructions
4. Run integration tests
5. Monitor logs for approval flow

### Phase 2: Enable Gradually

1. Deploy to production
2. Enable for 10% of users (feature flag)
3. Monitor success rate
4. Increase to 100% over 2 days

### Phase 3: Optimize

1. Gather PM decision quality metrics
2. Fine-tune instructions if needed
3. Add more approval tools if needed

---

## Backwards Compatibility

**Current:** Runner → ApprovalAnalyzer → Command
**New:** Runner → PM (via tools) → Command

Can run both in parallel:
- If `pending_interrupts` present: Use new PM flow
- If not: Fall back to ApprovalAnalyzer (old flow)

```python
if pending_interrupts_list:
    # NEW: Use PM-centric flow
    approval_cmd = self._build_command_from_pm_approval(...)
else:
    # OLD: Use ApprovalAnalyzer (keeps working)
    approval_response = analyze_approval(...)
    approval_cmd = self._build_command_from_approval(...)
```

---

## Metrics to Track

1. **Approval Success Rate:** % of PM decisions that lead to successful workflow completion
2. **PM Decision Quality:** % of correct approve/reject/edit decisions
3. **Context Injection:** % of times middleware successfully injects context
4. **Tool Call Rate:** % of workflows where PM calls approval tools
5. **Latency:** Time from pending interrupt to PM decision

---

## Troubleshooting

### Issue: PM doesn't call approval tools

**Cause:** Middleware not injecting context properly

**Solution:**
1. Check PM instructions mention approval workflow
2. Verify middleware is in pipeline
3. Log approval_context in state

### Issue: Runner can't parse approval output

**Cause:** Tool output format changed

**Solution:**
1. Update tool output format specification
2. Update parser regex
3. Add validation in tool

### Issue: Command building fails

**Cause:** Interrupt ID mismatch

**Solution:**
1. Log interrupt_id from both sources
2. Verify matching logic
3. Check for ID format inconsistencies

---

## Future Enhancements

1. **Multi-step Approvals:** PM routes to specialist for detailed review
2. **Parallel Approvals:** PM makes multiple approval decisions in one turn
3. **Conditional Logic:** PM decides based on business rules
4. **Feedback Loop:** PM learns from past approval outcomes

