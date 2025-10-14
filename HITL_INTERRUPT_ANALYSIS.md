# HITL Interrupt/Resume Error Analysis

**Date:** 2025-10-14
**Run IDs Analyzed:**
- Baseline (successful): `d20ea69d-da31-48a2-a887-4fd1f57af196`
- Error (failed): `2c6f672c-09b9-40b0-8aec-8ce3bbffdae3`

**Error Message:**
```
ValueError: Number of human responses (1) does not match number of hanging tool calls (2).
```

---

## Executive Summary

**Root Cause:** Architectural mismatch between HITL middleware's expectations and DeepAgents' nested interrupt handling when PM makes parallel task() calls.

**Impact:** Resume operations fail when cataloging department has pending interrupts and PM orchestration layer attempts to resume with a single human response.

**Severity:** High - Blocks multi-step workflows that leverage parallel task delegation with HITL safeguards.

---

## Detailed Analysis

### 1. Architecture Context

**PM Layer:**
- Makes parallel `task()` calls for independent operations
- Example: User says "Create two variants AND update size" → PM creates 2 tasks in parallel
- Each `task()` spawns a separate CatalogingDepartment subagent

**CatalogingDepartment Layer (via HITL Middleware):**
- Uses `HumanInTheLoopMiddleware` to gate `create_product` tool
- Calls `interrupt(interrupt_requests)` with list of tool calls needing approval
- Expects `len(responses) == len(interrupt_tool_calls)`

### 2. Interrupt/Resume Flow (LangGraph v1 alpha)

**From `langgraph._internal._constants` inspection:**

```python
def interrupt(value: Any) -> Any:
    """
    - First call raises GraphInterrupt (halts execution)
    - Resume uses Command primitive with resume value
    - Multiple interrupts in same node: matched by ORDER
    - Resume values scoped PER TASK (not shared across parallel tasks)
    """
```

**Key Insight:**
> "This list of resume values is scoped to the specific task executing the node and is not shared across tasks."

### 3. Error Scenario Breakdown

**Trace 2 (Error Flow):**

1. **User Request:**
   ```
   "Create two variants for 'pet can jar':
    - 500ml variant priced at 30 Rs
    - 1000ml variant priced at 50 Rs
    Media ID: 715785638197050"
   ```

2. **PM Interpretation:**
   - MessageIntentSpecialist returns `intent=resume_workflow`
   - Contains `command` object with `interrupt_id` and `resume_value`

3. **PM Delegation:**
   - PM makes **TWO** parallel `task()` calls (this is inferred behavior)
   - Task 1: Create first variant (500ml @ 30 Rs)
   - Task 2: Create second variant (1000ml @ 50 Rs)

4. **CatalogingDepartment Execution:**
   - Department agent decides to call `create_product` tool
   - HITL middleware intercepts
   - **Problem:** Middleware sees TWO `create_product` tool calls
   - Creates 2 `interrupt_requests`
   - Calls `interrupt(interrupt_requests)` → raises GraphInterrupt

5. **Resume Attempt:**
   - Runner builds Command with single `resume_value` from user response
   - Command is passed to graph.stream()
   - Graph resumes execution
   - **FAILURE POINT:** HumanInTheLoopMiddleware.after_model:255

   ```python
   responses: list[HumanInTheLoopResponse] = interrupt(interrupt_requests)

   # This validation FAILS:
   if len(responses) != len(interrupt_tool_calls):  # 1 != 2
       raise ValueError(
           f"Number of human responses ({len(responses)}) "
           f"does not match number of hanging tool calls "
           f"({len(interrupt_tool_calls)})."
       )
   ```

### 4. Why Trace 1 Succeeded (Hypothesis)

**User Request at line 638:**
```
"For pet jar create two variant with price 30 for 500ml and 50 for 1000ml
 and for bottle update the size to 1000ml"
```

**PM Behavior (from trace analysis):**
- Created todos for TWO separate tasks
- Made TWO parallel `task()` calls
- Task 1 → **interrupted** (line 643: `Status: interrupted`)
- Task 2 → **succeeded** (line 645: `Status: success`)

**Why it worked:**
- Only ONE task had an interrupt
- When user responded, Command resume matched 1:1 with single interrupted task
- No parallel interrupt conflict

**Critical Difference:**
- Trace 1: Two PM tasks, ONE interrupt
- Trace 2: Unknown PM delegation strategy, TWO interrupts in same department invocation

---

## Root Cause: Three Failure Modes

### Mode 1: PM Makes Single Task Call, Department Wants to Execute Multiple Creates

**Scenario:**
```python
# PM does this:
task("Create two variants for pet jar: 500ml @ 30 Rs, 1000ml @ 50 Rs")

# Department agent decides:
create_product(name="Pet Jar 500ml", price=30)  # Tool call 1
create_product(name="Pet Jar 1000ml", price=50)  # Tool call 2

# HITL sees: 2 tool calls
# User resume provides: 1 response
# ERROR: 1 != 2
```

**Why this happens:**
- Department agent interprets single task description as requiring multiple product creates
- Makes parallel tool calls in single agent invocation
- HITL middleware collects ALL tool calls at once
- Resume Command has single value (user's message), but middleware expects TWO HumanInTheLoopResponses

### Mode 2: Scratchpad Resume List Mismatch

**From `interrupt()` source:**
```python
if scratchpad.resume:
    if idx < len(scratchpad.resume):
        return scratchpad.resume[idx]
```

**Issue:**
- `scratchpad.resume` should be a LIST of responses (one per interrupt_request)
- Our Command construction may be providing a SINGLE resume value
- When HITL middleware calls `interrupt(interrupt_requests)` with 2 requests:
  - First call: `idx=0`, expects `scratchpad.resume[0]`
  - Second call: `idx=1`, expects `scratchpad.resume[1]`
  - But `scratchpad.resume` only has 1 element → validation fails BEFORE iteration

### Mode 3: Command Resume Structure Incorrect

**Current implementation assumption:**
```python
Command(resume=user_message_text, ...)  # Single value
```

**Required structure (hypothesis):**
```python
Command(resume=[response1, response2, ...], ...)  # List of HumanInTheLoopResponses
```

**Evidence:**
- HITL middleware expects `responses: list[HumanInTheLoopResponse]`
- `interrupt()` returns list from `scratchpad.resume`
- Validation checks `len(responses) == len(interrupt_tool_calls)`

---

## Pros & Cons Analysis

### Current Architecture (HITL Middleware + DeepAgents)

**Pros:**
1. ✅ **Clean separation:** PM orchestration vs. domain logic
2. ✅ **Middleware reusability:** HITL works across all departments
3. ✅ **Type safety:** Pydantic models ensure structured approvals
4. ✅ **Context-light tools:** Tools stay focused, middleware handles cross-cutting
5. ✅ **Works for simple cases:** Single interrupt per workflow succeeds

**Cons:**
1. ❌ **Parallel interrupt brittleness:** Fails when department makes multiple tool calls
2. ❌ **Opaque error:** ValueError doesn't explain architectural mismatch
3. ❌ **Resume API complexity:** Command structure not well-documented for nested interrupts
4. ❌ **Limited debuggability:** Scratchpad state not visible in traces
5. ❌ **Agent autonomy vs. HITL conflict:** Department agent decides tool call parallelism, but HITL needs 1:1 resume mapping

### Alternative: Decompose at PM Level

**Approach:** PM creates separate tasks for each variant

```python
# Instead of:
task("Create two variants: 500ml @ 30 Rs, 1000ml @ 50 Rs")

# Do this:
task("Create variant: pet jar 500ml @ 30 Rs")  # Task 1 → Interrupt 1
task("Create variant: pet jar 1000ml @ 50 Rs")  # Task 2 → Interrupt 2
```

**Pros:**
1. ✅ **1:1 mapping:** Each task has at most ONE interrupt
2. ✅ **Simpler resume:** Single response per interrupted task
3. ✅ **Better tracking:** Each variant cataloging gets own LangSmith trace
4. ✅ **Granular control:** User can approve/reject variants individually

**Cons:**
1. ❌ **PM complexity:** Requires PM to parse "two variants" and decompose
2. ❌ **Sequential execution:** Loses parallelism (unless DeepAgents supports parallel task())
3. ❌ **Token overhead:** More task() calls = more agent invocations
4. ❌ **User friction:** Two separate approval prompts instead of one

### Alternative: Batch HITL Responses

**Approach:** MessageIntentSpecialist constructs list of responses for all pending interrupts

```python
# Current:
Command(resume=user_message)

# Proposed:
Command(resume=[
    {"type": "accept", "args": None},  # For tool call 1
    {"type": "accept", "args": None},  # For tool call 2
])
```

**Pros:**
1. ✅ **Preserves parallelism:** Department can make multiple tool calls
2. ✅ **Matches HITL API:** List of responses for list of interrupt_requests
3. ✅ **Flexible:** Can accept some, edit others in same batch

**Cons:**
1. ❌ **Complex intent detection:** How does MessageIntentSpecialist know user approved BOTH?
2. ❌ **Ambiguous input:** User saying "yes" for 2 variants requires inference
3. ❌ **Checkpoint complexity:** Must store interrupt context to build response list
4. ❌ **Error-prone:** Mismatch between user's mental model and system's batch expectations

---

## Recommended Solutions

### SHORT TERM: Constrain Department to Single Tool Call

**Implementation:**
1. Add agent-level constraint in CatalogingDepartment prompt:
   ```
   IMPORTANT: Only call create_product ONCE per task delegation.
   If multiple products needed, return structured recommendation instead.
   ```

2. PM handles decomposition:
   ```python
   if "two variants" in request:
       task("Create variant 1: ...")
       task("Create variant 2: ...")
   ```

**Pros:**
- ✅ Quick fix, no middleware changes
- ✅ Aligns with DeepAgents' task-per-unit-of-work model
- ✅ Maintains HITL safeguards

**Cons:**
- ❌ Workaround, not architectural fix
- ❌ Relies on LLM following constraints

### MEDIUM TERM: Fix Command Resume Structure

**Investigation needed:**
1. Check checkpoint schema for interrupted state
2. Verify how DeepAgents' runner constructs Command
3. Test whether `Command(resume=[...])` is supported in LangGraph v1 alpha

**Implementation:**
```python
# In MessageIntentSpecialist or runner:
def build_resume_command(user_message, checkpoint_state):
    pending_interrupts = extract_interrupts(checkpoint_state)

    # Build one response per interrupt
    responses = []
    for interrupt in pending_interrupts:
        responses.append({
            "type": "accept",  # or parse user intent for edit/response
            "args": None,
        })

    return Command(resume=responses, ...)
```

**Pros:**
- ✅ Architectural fix matching LangGraph API
- ✅ Supports parallel tool calls
- ✅ Flexible (can handle accept/edit/response per interrupt)

**Cons:**
- ❌ Requires checkpoint introspection
- ❌ Unclear if LangGraph v1 alpha supports this
- ❌ May need MessageIntentSpecialist to understand batch approvals

### LONG TERM: Enhance HITL Middleware for Nested Agents

**Proposal:** Middleware detects nested task() calls and scopes interrupts appropriately

**Challenges:**
- Requires changes to `langchain.agents.middleware` (external lib)
- May conflict with DeepAgents' design assumptions
- Complex state tracking across hierarchy

**Verdict:** Not recommended. Work within LangGraph/DeepAgents primitives instead.

---

## Action Items

### Immediate (P0)
1. ✅ **Constrain CatalogingDepartment:** Update prompt to enforce single create_product per task
2. ✅ **Update PM delegation:** Decompose multi-variant requests into separate tasks
3. ⬜ **Add validation:** Detect multi-create scenarios and reject gracefully
4. ⬜ **Document constraint:** Update WHATSAPP_CATALOGING_WORKFLOW.md with limitation

### Short Term (P1)
5. ⬜ **Inspect checkpoint:** Use REPL to examine interrupted state structure
6. ⬜ **Test Command(resume=[...]):** Verify if list resume values work
7. ⬜ **Implement batch response builder:** If supported, enhance runner
8. ⬜ **Add interrupt count to logs:** Surface `len(interrupt_tool_calls)` for debugging

### Medium Term (P2)
9. ⬜ **Upstream feedback:** Report to LangChain team about nested interrupt UX
10. ⬜ **Enhance MessageIntentSpecialist:** Teach it to detect batch approval intent
11. ⬜ **Create test suite:** Cover single interrupt, parallel interrupts, nested task scenarios
12. ⬜ **Document nested interrupt patterns:** Add to LANGGRAPH_V1_FEATURES.md

---

## Technical Deep Dive: Command Resume API

### Current Understanding

**From LangGraph docs/source:**
```python
Command(
    resume=Any,  # Value to provide to interrupt() call
    graph=...,
    update=...,
)
```

**Hypothesis:**
- If node has single `interrupt(value)`: `resume=single_value`
- If node has multiple `interrupt()` calls: `resume=[value1, value2, ...]`
- List elements matched to interrupt calls BY ORDER

**Evidence from `interrupt()` source:**
```python
scratchpad.resume  # This is expected to be a list
if idx < len(scratchpad.resume):
    return scratchpad.resume[idx]
```

### Verification Needed

```python
# Test 1: Single interrupt
graph.stream(Command(resume="user input"), config)

# Test 2: Multiple interrupts (hypothesis)
graph.stream(Command(resume=["input1", "input2"]), config)

# Check: Does LangGraph accept list? Does middleware receive it correctly?
```

### If List Resume Not Supported

**Fallback:** Enforce 1 interrupt per task (Short Term solution becomes permanent)

---

## Conclusion

**The error is NOT a bug—it's an architectural constraint:**

HITL middleware expects:
```
1 task → N tool calls → N interrupts → N resume responses
```

But our flow was:
```
1 user message → 1 resume value → 2 tool calls → 2 interrupts → ERROR
```

**Best path forward:**
1. Immediate: Constrain to 1 tool call per task (PM decomposes)
2. Short term: Verify if Command(resume=[...]) is supported
3. Medium term: Enhance MessageIntentSpecialist for batch approvals IF resume list works

**Architectural principle:**
> Each unit of work (task delegation) should have at most ONE interrupt point. Multi-step operations requiring multiple approvals should be decomposed at the PM layer, not the department layer.

---

## Appendix: Trace Evidence

### Trace 1 (Successful) - Key Observations
- Line 642-643: `Run: task (...) Status: interrupted`
- Line 644-645: `Run: task (...) Status: success`
- Two PM task() calls, only ONE interrupted
- User resume succeeded because 1:1 mapping held

### Trace 2 (Failed) - Error Stack
```
File "/var/task/_vendor/langchain/agents/middleware/human_in_the_loop.py", line 255
    raise ValueError(msg)
ValueError: Number of human responses (1) does not match number of hanging tool calls (2).
```

**Call stack:**
1. `LangGraph.stream()` → runner.tick()
2. `tools` node → ToolNode._func()
3. `task` tool execution → DeepAgents.task()
4. `CatalogingDepartment.invoke()` → agent loop
5. `HumanInTheLoopMiddleware.after_model()` → validation FAILURE

**Key insight:** Error occurs INSIDE CatalogingDepartment subagent, not at PM level.

---

**End of Analysis**
