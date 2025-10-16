# DeepAgents HITL Orchestration Analysis

**Date:** 2025-10-16
**Status:** Research Complete - Ready for Implementation Decision
**Scope:** Can PM agent orchestrate HITL approval workflows using DeepAgents?

---

## Executive Summary

**Verdict: YES** - A PM agent CAN orchestrate HITL approval workflows using DeepAgents, with three viable architectural patterns. The current WorkflowRunner-centric approach is already proven, but migrating logic INTO the PM agent is technically feasible and architecturally superior.

**Recommendation:** Implement Pattern 2 (PM-Centric with Custom Tools) as the bridge between current Runner control and future fully-agentic workflows.

---

## Critical Findings

### 1. State Access Capabilities

| Method | Works? | Details | Use Case |
|--------|--------|---------|----------|
| `graph.get_state(config).values` | ✓ YES | Read-only checkpoint state | Runner reads pending_interrupts |
| `InjectedState` in tools | ✗ NO | JSON schema error (non-serializable) | Cannot use in LLM-called tools |
| Middleware hooks (`before_agent`, `after_agent`) | ✓ YES | Full state access in `state` param | Inject context before PM reasons |
| Initial state via `with_config()` | ✓ YES | Custom fields like `pending_interrupts` | Pass interrupt data to PM |

**Implication:** PM can access pending_interrupts via:
1. **Middleware injection** (context before reasoning)
2. **Initial state** (loaded at start)
3. **NOT directly via tools** (LLM can't receive InjectedState params)

---

### 2. Command Construction Capabilities

**Finding:** PM CAN construct Command objects, but not directly expose them to LLM.

```python
# WORKS: Tool constructs Command internally
@tool
def propose_workflow_resumption(interrupt_id: str, decision: str) -> str:
    """PM proposes approval - Runner converts to Command"""
    cmd = Command(resume={interrupt_id: [{'decision': decision}]})
    # Tool returns string output, Command is runner-side
    return f"Proposed {decision}"

# FAILS: InjectedState parameter
@tool
def check_interrupts(state: InjectedState) -> str:
    # PydanticInvalidForJsonSchema error
    # Cannot generate JSON schema for InjectedState
    pass
```

**Architecture Pattern:** Tool output → Runner intercepts → Builds Command → Executes

---

### 3. DeepAgentState & Interrupt Exposure

```python
# DeepAgentState annotations (from inspection):
DeepAgentState.__annotations__ = {
    'messages': Required[list[AnyMessage]],  # Message history
    'jump_to': NotRequired[JumpTo | None],    # Control flow
    'structured_response': NotRequired[...],  # LLM output format
    'thread_model_call_count': NotRequired[int],
    'run_model_call_count': NotRequired[int],
    'todos': NotRequired[list[Todo]],
    'files': NotRequired[dict[str, str]],
}

# MISSING: No built-in 'pending_interrupts' field
# IMPLICATION: Must add custom field to PM's initial_state
```

**Current Implementation Already Does This:**
```python
# From project_manager.py line 157-166
initial_state = {
    "company_profile": company_profile.model_dump(),
    "status": "idle",
    "plan": [],
    "current_step": 0,
    "department_results": {},
    "todos": [],
    "remaining_steps": 8,
    "pending_interrupts": [],  # <-- Custom field for HITL
}
```

---

### 4. Middleware Access Patterns

HumanInTheLoopMiddleware and custom middleware have full state access:

```python
class PMHITLMiddleware(AgentMiddleware):
    def before_agent(self, state, runtime):
        """FULL STATE ACCESS - called before PM reasoning"""
        pending = state.get('pending_interrupts', [])
        if pending:
            # Can inject context into model request
            return {"context": f"Waiting for user input on {len(pending)} items"}
        return None

    def after_agent(self, state, runtime):
        """FULL STATE ACCESS - called after PM completes"""
        # Can inspect what PM decided
        return None
```

**Middleware Hook Signature:**
```python
before_agent(self, state: StateT, runtime: Runtime[ContextT]) -> dict[str, Any] | None
after_agent(self, state: StateT, runtime: Runtime[ContextT]) -> dict[str, Any] | None
```

---

### 5. Tool Config / HITL Integration

DeepAgents + LangChain HITL via `tool_configs` parameter:

```python
# In create_deep_agent():
tool_configs = {
    'save_product': {
        'allow_accept': True,     # User can approve
        'allow_edit': True,       # User can edit
        'allow_respond': True,    # User can respond with text
        'description': 'Approve product save'
    },
    'cataloging_department': {    # SubAgent name
        'allow_accept': True,
        'description': 'Review cataloging decisions'
    }
}

agent = create_deep_agent(
    tools=pm_tools,
    subagents=subagents,
    tool_configs=tool_configs,  # <-- HITL configuration
    middleware=[HumanInTheLoopMiddleware(interrupt_on=tool_configs)]
)
```

**Current Status:** Not used by PM (departments handle their own HITL via middleware)

---

## Three Viable Architectures

### Pattern 1: Current (Working) - Runner-Centric HITL

```
User Message → Runner → PM (no HITL logic)
                      ↓
                   Department (raises interrupt)
                      ↓
Runner detects interrupt → ApprovalAnalyzer → Command → Resume
```

**Pros:**
- Currently implemented and tested
- Full Runner control over approval flow
- Can add custom approval rules at Runner level
- Clean separation: Runner orchestrates, PM delegates

**Cons:**
- HITL logic outside PM (not agentic)
- PM doesn't reason about approvals
- Runner becomes coordination bottleneck

**Implementation Status:** ✓ Production

---

### Pattern 2: Proposed - PM-Centric with Custom Tools

```
User Message → Runner → PM (WITH HITL TOOLS)
                    ↓
              Checks pending_interrupts
              (via middleware injection)
                    ↓
              Calls: propose_workflow_resumption()
                    ↓
Runner intercepts → Builds Command → Resume
```

**How it works:**

```python
# 1. PM's initial state includes pending_interrupts
initial_state = {
    "messages": [...],
    "pending_interrupts": [
        {
            "interrupt_id": "int_1",
            "tool_name": "save_product",
            "description": "Product waiting for approval"
        }
    ]
}

# 2. Middleware injects context before PM reasons
class PMHITLMiddleware(AgentMiddleware):
    def before_agent(self, state, runtime):
        pending = state.get('pending_interrupts', [])
        if pending:
            # Inject into instructions
            return {
                "system_context": f"User has pending approvals: {[p['description'] for p in pending]}"
            }
        return None

# 3. PM has approval tools
@tool
def propose_workflow_resumption(interrupt_id: str, decision: str) -> str:
    """PM decides on approval"""
    return f"Approved {interrupt_id}"

# 4. Runner intercepts tool output
if tool_output.startswith("Approved"):
    cmd = Command(resume={interrupt_id: [{'decision': 'accept'}]})
    pm.stream(cmd, config=config)
```

**Pros:**
- PM now REASONS about approvals
- True agentic orchestration
- Backward compatible with Runner control
- Clear tool interface for approval decisions

**Cons:**
- Requires custom middleware
- Runner still needed for Command construction
- Two-way coordination between PM and Runner

**Implementation Effort:** Medium (1-2 days)

---

### Pattern 3: Fully Agentic - DeepAgents Native HITL

```
User Message → Runner → PM with HITL Middleware
                      ↓
              PM calls tools/subagents
                      ↓
           DeepAgents auto-pauses on tool_configs
                      ↓
        HumanInTheLoopMiddleware surfaces interrupts
                      ↓
              Runner provides user response
                      ↓
        DeepAgents auto-resumes (Command internal)
```

**How it works:**

```python
# PM configured with HITL tools
tool_configs = {
    'cataloging_department': {
        'allow_accept': True,
        'allow_edit': True,
        'description': 'Review cataloging decisions'
    }
}

pm = create_deep_agent(
    tools=pm_tools,
    subagents=subagents,
    tool_configs=tool_configs,
    middleware=[HumanInTheLoopMiddleware(interrupt_on=tool_configs)]
)

# Execution:
# 1. PM reasons -> calls cataloging_department
# 2. Department executes -> returns data
# 3. DeepAgents middleware detects tool_configs match
# 4. Raises Interrupt automatically
# 5. Runner catches interrupt
# 6. User approves
# 7. DeepAgents resumes with approval

# DeepAgents handles Command construction internally
```

**Pros:**
- Cleanest architecture
- DeepAgents manages HITL completely
- No Runner-PM coordination
- Most "agentic"

**Cons:**
- Loses direct Runner control
- Less visibility into approval process
- HumanInTheLoopMiddleware adds complexity
- Potential for infinite loops if not careful
- Alpha library stability concerns

**Implementation Effort:** High (3-5 days, needs refactor)

---

## Technical Verification Results

### API Inspection Summary

```python
# 1. DeepAgentState fields
DeepAgentState.__annotations__ = {
    'messages': ...,
    'todos': ...,
    'files': ...,
    # NO built-in pending_interrupts
}
# Implication: Must add custom field

# 2. Command signature
Command(*, graph=None, update=None, resume=dict[str, Any], goto=())
# resume: Stores {interrupt_id: [responses]}

# 3. HumanInTheLoopMiddleware
HumanInTheLoopMiddleware(
    interrupt_on: dict[str, bool | ToolConfig],
    description_prefix: str = 'Tool execution requires approval'
)
# ToolConfig = TypedDict with allow_accept, allow_edit, allow_respond, description

# 4. Middleware hooks
before_agent(state: StateT, runtime: Runtime) -> dict[str, Any] | None
after_agent(state: StateT, runtime: Runtime) -> dict[str, Any] | None
# Full state access in both hooks

# 5. SubAgent & CustomSubAgent
SubAgent = TypedDict({
    'name': str,
    'description': str,
    'prompt': str,
    'tools': NotRequired[list[BaseTool]],
    'model': NotRequired[Runnable],
    'middleware': NotRequired[list[AgentMiddleware]]
})

CustomSubAgent = TypedDict({
    'name': str,
    'description': str,
    'graph': Runnable  # Pre-built LangGraph
})
```

---

## Blocker Analysis

### Finding 1: InjectedState Not JSON-Serializable

**Blocker:** Cannot use `InjectedState` in tool parameters exposed to LLM.

```python
@tool
def inspect_state(state: InjectedState) -> str:
    # Error: PydanticInvalidForJsonSchema
    # Cannot generate a JsonSchema for core_schema.IsInstanceSchema
    pass
```

**Why:** OpenAI API requires JSON schema for all tool parameters. `InjectedState` is not JSON-serializable.

**Workaround:** Use middleware to inject context, don't expose state to tools.

**Status:** Not a blocker (expected behavior)

---

### Finding 2: Injectable Types Limited

**Analysis:** Only 3 injectable types available:
- `InjectedState` - Not JSON-serializable
- `InjectedStore` - State store (for file-based state)
- `InjectedToolCallId` - Current tool call ID

**Implication:** Cannot access arbitrary state in tools. Must use middleware.

**Status:** Expected limitation, manageable

---

### Finding 3: DeepAgents Alpha Instability

**Finding:** Library is at v0.0.11 (alpha).

```python
# Version constraints
langchain==1.0.0a12         # Alpha
langgraph==1.0.0a4          # Alpha
deepagents==0.0.11          # Alpha
langchain-openai==0.2.8     # Stable
```

**Implication:** APIs may change. Need defensive code and feature flags.

**Status:** Known risk, manageable with version pinning

---

## Recommendations

### Phase 1: PM-Centric Tools (Pattern 2) - RECOMMENDED

**Why:**
- Minimal architectural change
- Backward compatible with current Runner
- Enables PM reasoning about approvals
- Low risk, high value

**Implementation:**

1. Create `PMHITLMiddleware` to inject pending_interrupts context
2. Add `propose_workflow_resumption` tool to PM
3. Update Runner to intercept tool output
4. Test with existing workflows

**Timeline:** 1-2 days

---

### Phase 2: Consider Full DeepAgents HITL (Pattern 3)

**Only if:**
- DeepAgents API stabilizes (v1.0+)
- Direct Runner control not needed
- Team comfortable with auto-pause/resume

**Timeline:** Post-v1.0 stabilization (Q1 2026+)

---

## Code Examples

### Example 1: Current State Access (Working)

```python
# In runner.py - CURRENT APPROACH
state_snapshot = pm.get_state(config)
pending_interrupts = state_snapshot.values.get('pending_interrupts', [])
# Works perfectly
```

### Example 2: Middleware State Access (Pattern 2)

```python
from langchain.agents.middleware.types import AgentMiddleware

class PMHITLMiddleware(AgentMiddleware):
    """Inject pending interrupts context to PM"""

    def before_agent(self, state, runtime):
        pending = state.get('pending_interrupts', [])
        if not pending:
            return None

        # Inject context before PM reasons
        context_str = "\n".join([
            f"- {p['description']} (ID: {p['interrupt_id']})"
            for p in pending
        ])

        return {
            "approval_context": f"Waiting for your decisions:\n{context_str}"
        }

# In project_manager.py
pm = create_deep_agent(
    tools=pm_tools,
    instructions=instructions,
    model=llm,
    subagents=subagents,
    middleware=[PMHITLMiddleware()],  # Add middleware
)
```

### Example 3: PM Approval Tool (Pattern 2)

```python
from deepagents.tools import tool
from pydantic import BaseModel, Field
from typing import Literal

class ApprovalDecision(BaseModel):
    interrupt_id: str = Field(description="ID to resume")
    decision: Literal["accept", "reject", "edit"] = Field()
    edited_data: dict = Field(default_factory=dict)

@tool
def propose_workflow_resumption(
    interrupt_id: str,
    decision: str,
    edited_data: dict = None
) -> str:
    """PM proposes approval decision.

    Runner intercepts this and converts to:
    Command(resume={interrupt_id: [{'decision': decision, 'args': edited_data}]})
    """
    if decision not in ["accept", "reject", "edit"]:
        raise ToolException(f"Invalid decision: {decision}")

    return f"Approved: {decision} for {interrupt_id}"
```

### Example 4: Runner Intercepts Tool Output (Pattern 2)

```python
# In runner.py
for event in pm.stream(payload, config=config):
    # Check for approval tool output
    if 'messages' in event:
        for msg in event['messages']:
            if hasattr(msg, 'content') and 'Approved:' in str(msg.content):
                # Parse PM's decision
                decision_text = msg.content
                # Build Command
                cmd = Command(resume={
                    interrupt_id: [{'decision': decision_type}]
                })
                # Resume workflow
                for resume_event in pm.stream(cmd, config=config):
                    ...
```

---

## Risk Assessment

| Risk | Likelihood | Severity | Mitigation |
|------|------------|----------|-----------|
| InjectedState JSON error | Certain | Low | Use middleware instead (designed workaround) |
| DeepAgents API change | High | Medium | Pin versions, add feature flags |
| Infinite HITL loop | Medium | High | Add recursion counter, timeout |
| Middleware state mutation | Low | High | Document immutability rules |
| PM gets confused by context | Medium | Medium | Add clear approval instructions |

---

## Conclusion

DeepAgents provides excellent infrastructure for PM-centric HITL orchestration:

1. **State Management:** Custom fields work perfectly (pending_interrupts)
2. **Command Construction:** Fully supported, easily extensible
3. **Tool Patterns:** Can create approval tools, structured outputs
4. **Middleware Integration:** Powerful context injection before PM reasons
5. **Interrupt Handling:** Both Runner-level and DeepAgents-level support

**Next Steps:**

1. Implement Pattern 2 (PM-Centric Tools) for immediate benefit
2. Monitor DeepAgents v1.0 release for Pattern 3 feasibility
3. Document approval decision logic in PM instructions
4. Add comprehensive approval test scenarios

---

## Appendix: API Reference

### DeepAgents Classes

- `create_deep_agent(tools, instructions, middleware, model, subagents, tool_configs, checkpointer)`
- `DeepAgentState` - Base state with messages, todos, files
- `SubAgent` - TypedDict for simple delegation
- `CustomSubAgent` - TypedDict for pre-built graphs
- `PlanningMiddleware` - Auto-generates plans
- `SubAgentMiddleware` - Handles subagent execution
- `FilesystemMiddleware` - File read/write tools

### LangChain HITL

- `HumanInTheLoopMiddleware(interrupt_on, description_prefix)`
- `ToolConfig` - TypedDict: allow_accept, allow_edit, allow_respond, description
- `Command(graph, update, resume, goto)` - Resumption instruction

### LangGraph State

- `StateSnapshot` - (values, next, config, metadata, interrupts)
- `Interrupt(value, id)` - Represents a paused execution point

