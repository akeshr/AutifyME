# PM Structured Output Architecture - Production Design

**Date:** 2025-10-14
**Status:** Design Phase → Implementation

---

## Executive Summary

**Problem:** Current PM-only architecture uses text parsing for Commands ("COMMAND: {json}"), which is brittle and unprofessional.

**Solution:** Use Pydantic structured outputs everywhere. PM returns typed responses, runner handles based on type.

**Benefits:**
- ✅ Type safety throughout stack
- ✅ No text parsing brittleness
- ✅ Clear contracts between PM and runner
- ✅ Production-grade architecture
- ✅ Easier testing and validation

---

## Current Architecture Problems

### 1. **Text-Based Command Communication**
```python
# Current (BAD):
PM outputs: "COMMAND: {\"resume\": [{\"type\": \"accept\"}]}"
Runner parses: extract JSON from text
```

**Issues:**
- Brittle text parsing
- No type safety
- COMMAND text exposed to user
- Easy to break with prompt changes

### 2. **Mixed Response Types**
PM outputs AIMessages for:
- User-facing messages
- System commands
- Delegation instructions

Runner can't distinguish intent without text parsing.

### 3. **Inconsistent Structured Output Usage**

**Current State:**
- ✅ Tools use Pydantic (save_product → CatalogingResult)
- ✅ Specialists use Pydantic (was MessageIntent)
- ❌ **PM uses text AIMessages** ← Gap!
- ✅ Departments use Pydantic (CatalogingResult)

---

## Production Architecture: Structured Outputs Everywhere

### Core Principle
> **Every agent output should be a Pydantic model, not unstructured text.**

### Architecture Overview

```
User Message
    ↓
Runner (orchestrator)
    ↓
[Check for pending interrupts]
    ↓
IF interrupts exist:
    ↓
    Approval Analyzer (LLM with structured output)
    ↓
    BatchApprovalResponse (Pydantic)
    ↓
    Runner builds Command
    ↓
    Execute Command → HITL middleware receives responses
    ↓
    Workflow resumes

IF no interrupts (new request):
    ↓
    PM (DeepAgent)
    ↓
    PM delegates to departments
    ↓
    Departments execute and return structured results
    ↓
    PM relays results to user
```

### Key Insight: Two Distinct Flows

**Flow 1: HITL Approval (Structured Analysis)**
- User responding to pending interrupts
- Needs: Intent interpretation + batch response construction
- **Use: Approval Analyzer** (LLM with structured output)
- Output: `BatchApprovalResponse` (Pydantic)

**Flow 2: New Requests (Orchestration)**
- User requesting new work
- Needs: Intent detection + task delegation
- **Use: PM (DeepAgent)**
- Output: State updates + messages (handled by runner)

---

## Pydantic Schema Design

### 1. Approval Response Schemas

```python
from typing import Literal, Any
from pydantic import BaseModel, Field

class HumanInTheLoopResponse(BaseModel):
    """Single response for one interrupt.

    Matches langchain.agents.middleware.human_in_the_loop expectations.
    """
    type: Literal["accept", "edit", "response"]
    args: dict[str, Any] | str | None = None

    class Config:
        json_schema_extra = {
            "examples": [
                {"type": "accept", "args": None},
                {"type": "edit", "args": {"price": 45.0}},
                {"type": "response", "args": "User wants to review this later"},
            ]
        }


class InterruptContext(BaseModel):
    """Context about a pending interrupt for analysis."""
    interrupt_id: str
    tool_name: str
    tool_args: dict[str, Any]
    description: str = ""


class BatchApprovalResponse(BaseModel):
    """Batch approval response for multiple interrupts.

    This is what the approval analyzer returns.
    """
    responses: list[HumanInTheLoopResponse] = Field(
        description="List of responses, one per pending interrupt. MUST match interrupt count."
    )
    reasoning: str = Field(
        description="Brief explanation of how user input was interpreted"
    )

    def validate_count(self, expected: int) -> None:
        """Validate response count matches expected interrupts."""
        if len(self.responses) != expected:
            raise ValueError(
                f"Response count mismatch: got {len(self.responses)}, expected {expected}"
            )
```

### 2. PM Intent Schemas (Future Enhancement)

For true structured PM outputs:

```python
class TaskDelegation(BaseModel):
    """PM delegates task to department."""
    department: str
    description: str
    context: dict[str, Any]


class UserClarification(BaseModel):
    """PM asks user for clarification."""
    message: str
    missing_fields: list[str]


class PMResponse(BaseModel):
    """Union of PM response types."""
    type: Literal["delegate", "clarify", "acknowledge"]
    delegation: TaskDelegation | None = None
    clarification: UserClarification | None = None
    acknowledgment: str | None = None
```

---

## Implementation Strategy

### Phase 1: Approval Analyzer (Priority P0)

**Goal:** Fix HITL resume flow with structured outputs.

**Create:** `agents/src/autifyme_agents/workflows/approval_analyzer.py`

```python
def create_approval_analyzer(llm: BaseChatModel | None = None):
    """Create approval analyzer with structured output.

    This is a LIGHTWEIGHT function (not full agent) that:
    1. Takes pending interrupts + user message
    2. Returns BatchApprovalResponse (structured)
    3. No state, no tools, no delegation - pure analysis

    Args:
        llm: Optional LLM override

    Returns:
        LLM chain configured with structured output
    """
    from autifyme_agents.core.llm_factory import get_llm
    from autifyme_agents.core.prompt_loader import load_prompt

    if llm is None:
        llm = get_llm(model="gpt-4.1-mini-2025-04-14", temperature=0.2)

    # Configure LLM for structured output
    structured_llm = llm.with_structured_output(BatchApprovalResponse)

    # Load approval analysis prompt
    prompt_template = load_prompt("approval_analyzer.prompt")

    # Build chain: prompt → structured LLM → BatchApprovalResponse
    chain = prompt_template | structured_llm

    return chain
```

**Prompt:** `agents/src/autifyme_agents/prompts/approval_analyzer.prompt`

```
You are an approval response analyzer for HITL workflows.

Your job: Interpret user's approval response and construct structured batch responses.

**Input:**
- pending_interrupts: List of pending tool calls awaiting approval
- user_message: User's response (e.g., "approve both", "edit price to 45")

**Output:**
BatchApprovalResponse with:
- responses: List of HumanInTheLoopResponse (one per interrupt)
- reasoning: How you interpreted the user's intent

**Rules:**
1. len(responses) MUST EQUAL len(pending_interrupts)
2. Order matters - responses[i] applies to pending_interrupts[i]
3. Response types:
   - "accept": Approve as-is (args: null)
   - "edit": Approve with modifications (args: {field: value})
   - "response": Reject or ask for clarification (args: string message)

**Examples:**

User: "approve both"
Interrupts: 2
Output:
{{
  "responses": [
    {{"type": "accept", "args": null}},
    {{"type": "accept", "args": null}}
  ],
  "reasoning": "User approved all pending items"
}}

User: "approve first, change second to 45 Rs"
Interrupts: 2
Output:
{{
  "responses": [
    {{"type": "accept", "args": null}},
    {{"type": "edit", "args": {{"price": 45.0}}}}
  ],
  "reasoning": "User approved first item as-is, requested price edit for second item"
}}

User: "reject all"
Interrupts: 2
Output:
{{
  "responses": [
    {{"type": "response", "args": "User rejected"}},
    {{"type": "response", "args": "User rejected"}}
  ],
  "reasoning": "User rejected all pending items"
}}

**CRITICAL:**
- If user intent is ambiguous, use "response" type with clarification request
- NEVER guess - ask for clarification if unclear
- Always return EXACTLY the right number of responses
```

### Phase 2: Runner Integration (Priority P0)

**Update:** `agents/src/autifyme_agents/workflows/orchestration/runner_v2.py`

**Key Changes:**

1. **Import approval analyzer:**
```python
from autifyme_agents.workflows.approval_analyzer import create_approval_analyzer
```

2. **Replace HITL resume flow:**
```python
def _invoke_pm(self, thread_id: str, raw_payload: dict[str, Any]):
    # ... check for pending interrupts ...

    if pending_interrupts_list:
        # === NEW: Use structured approval analyzer ===
        user_message = raw_payload.get("text", "")

        # Build input for analyzer
        analyzer_input = {
            "pending_interrupts": pending_interrupts_list,
            "user_message": user_message,
        }

        # Invoke approval analyzer (structured output!)
        try:
            approval_response: BatchApprovalResponse = self._analyze_approval(
                analyzer_input, pending_interrupts_list
            )

            logger.info(
                "Approval analysis complete",
                extra={
                    "thread_id": thread_id,
                    "response_count": len(approval_response.responses),
                    "reasoning": approval_response.reasoning,
                }
            )

        except Exception as e:
            logger.error(
                "Approval analysis failed",
                extra={"thread_id": thread_id, "error": str(e)}
            )
            self.channel.send_text(
                raw_payload.get("sender", ""),
                "I had trouble understanding your response. Please try: 'approve' or 'reject'"
            )
            return None, None

        # Build Command from structured response
        command_obj = self._build_command_from_approval(
            approval_response, pending_interrupts_list
        )

        # Execute Command
        last_event = None
        interrupt_value = None
        for event in pm.stream(command_obj, config=config, stream_mode="values"):
            last_event = event
            if "__interrupt__" in event:
                interrupts = event.get("__interrupt__") or []
                if interrupts:
                    interrupt_value = interrupts[0].value

        return last_event, interrupt_value

    else:
        # Normal flow - no interrupts
        # ...existing code...
```

3. **Add helper methods:**
```python
def _analyze_approval(
    self,
    analyzer_input: dict,
    pending_interrupts: list[dict],
) -> BatchApprovalResponse:
    """Analyze user approval using structured output."""
    analyzer = create_approval_analyzer()

    approval_response = analyzer.invoke(analyzer_input)

    # Validate count
    approval_response.validate_count(len(pending_interrupts))

    return approval_response


def _build_command_from_approval(
    self,
    approval_response: BatchApprovalResponse,
    pending_interrupts: list[dict],
) -> Command:
    """Build LangGraph Command from structured approval response."""
    resume_dict = {}

    for idx, interrupt_info in enumerate(pending_interrupts):
        interrupt_id = interrupt_info["interrupt_id"]
        response = approval_response.responses[idx]

        # HITL middleware expects list of responses per interrupt
        resume_dict[interrupt_id] = [response.model_dump()]

    return Command(resume=resume_dict)
```

4. **Remove old text parsing:**
```python
# DELETE: _parse_command_from_pm() method
# No longer needed - we have structured outputs!
```

### Phase 3: Update PM (Priority P1)

**Changes to PM:**

1. **Remove COMMAND text instructions** from `project_manager.prompt`
   - Delete all "COMMAND: {json}" examples
   - PM focuses on orchestration, not approval interpretation

2. **Simplify PM prompt:**
   - Remove batch approval interpretation section
   - PM delegates to departments
   - PM relays results to users
   - PM asks clarifications

**Rationale:** PM should orchestrate, not interpret approvals. That's the approval analyzer's job.

### Phase 4: Testing (Priority P0)

**Test Scenarios:**

1. **Single Product + HITL**
   ```bash
   uv run python -m autifyme_agents.cli.simulate "Catalog jar 30 Rs" --hitl-mode auto_approve
   ```
   - Verify: BatchApprovalResponse with 1 response
   - Verify: Command executed correctly
   - Verify: Product saved

2. **Batch Approval (2 Interrupts)**
   ```bash
   # This is THE critical test
   User: "Create two variants: 500ml @ 30 Rs, 1L @ 50 Rs"
   (2 interrupts occur)
   User: "approve both"
   ```
   - Verify: BatchApprovalResponse with 2 responses
   - Verify: len(responses) == len(interrupts)
   - Verify: Both products saved
   - Verify: NO "1 != 2" error

3. **Selective Approval**
   ```bash
   User: "approve first, change second price to 45"
   ```
   - Verify: responses[0] = {"type": "accept"}
   - Verify: responses[1] = {"type": "edit", "args": {"price": 45}}
   - Verify: First product saved as-is
   - Verify: Second product saved with edited price

---

## Benefits Over Text Parsing

| Aspect | Text Parsing | Structured Output |
|--------|--------------|-------------------|
| Type Safety | ❌ None | ✅ Pydantic validation |
| Brittleness | ❌ Breaks with prompt changes | ✅ Stable schema |
| Testing | ❌ Hard to mock | ✅ Easy to test |
| Debugging | ❌ Parse errors opaque | ✅ Clear validation errors |
| User Exposure | ❌ COMMAND text leaks | ✅ Never exposed |
| Production Ready | ❌ No | ✅ Yes |

---

## Migration Path

### Step 1: Create Schemas ✅ NEXT
- Define BatchApprovalResponse
- Define HumanInTheLoopResponse
- Add validation methods

### Step 2: Create Approval Analyzer
- Build approval_analyzer.py
- Create approval_analyzer.prompt
- Test structured output with sample inputs

### Step 3: Update Runner
- Import approval analyzer
- Replace text parsing with structured analysis
- Add helper methods
- Remove _parse_command_from_pm

### Step 4: Update PM Prompt
- Remove COMMAND instructions
- Simplify to orchestration-only

### Step 5: Test End-to-End
- All scenarios from Phase 4
- Validate no regressions
- Measure token usage

---

## Success Criteria

1. ✅ No text parsing in codebase
2. ✅ All PM outputs are Pydantic models
3. ✅ Batch approval works (no "1 != 2" error)
4. ✅ Type safety validated by mypy
5. ✅ Unit tests pass for approval analyzer
6. ✅ Integration tests pass for full workflow
7. ✅ Token usage ≤ 1850/message (PM-only target)

---

## Timeline Estimate

- **Step 1 (Schemas):** 15 min
- **Step 2 (Approval Analyzer):** 30 min
- **Step 3 (Runner Update):** 45 min
- **Step 4 (PM Prompt):** 15 min
- **Step 5 (Testing):** 30 min

**Total:** ~2.5 hours for production-grade structured output architecture

---

## Conclusion

**This is the RIGHT way to build production systems:**
- Type-safe contracts
- No brittle text parsing
- Clear separation of concerns (PM = orchestration, Analyzer = approval interpretation)
- Pydantic validation throughout

**No shortcuts. Production-level architecture.**
