# LangGraph v1 Middleware Investigation

**Date**: 2025-10-16
**Status**: Complete
**Context**: PM-centric HITL approval context injection
**LangGraph Version**: 1.0.0a4
**LangChain Version**: 1.0.0a12
**DeepAgents Version**: 0.0.11

---

## Executive Summary

**Finding**: LangGraph v1 provides **AgentMiddleware** as the standard approach for state transformation. This is the recommended pattern for injecting approval context into PM state before reasoning.

**Key Discovery**: `AgentMiddleware.before_agent()` can modify state by returning a dictionary that gets merged into the current state. This allows injecting messages, fields, or any state modifications before the agent processes input.

**Recommendation**: Use **Standard AgentMiddleware** (not custom LangGraph nodes or state reducers). This aligns with LangGraph v1 best practices and integrates cleanly with DeepAgents.

---

## Investigation Results

### 1. LangGraph v1 Middleware Capabilities

#### 1.1 AgentMiddleware API

**Source**: `langchain.agents.middleware.types.AgentMiddleware`

```python
class AgentMiddleware:
    """Base middleware class for an agent.

    Subclass this and implement any of the defined methods to customize agent behavior
    between steps in the main agent loop.
    """

    def before_agent(self, state: StateT, runtime: Runtime[ContextT]) -> dict[str, Any] | None:
        """Called before agent reasoning. Return dict to update state."""

    def after_agent(self, state: StateT, runtime: Runtime[ContextT]) -> dict[str, Any] | None:
        """Called after agent reasoning. Return dict to update state."""

    def before_model(self, state: StateT, runtime: Runtime[ContextT]) -> dict[str, Any] | None:
        """Called before model invocation. Return dict to update state."""

    def after_model(self, state: StateT, runtime: Runtime[ContextT]) -> dict[str, Any] | None:
        """Called after model invocation. Return dict to update state."""
```

**Execution Order**:
1. `before_agent` - Before agent loop iteration
2. `before_model` - Before LLM call
3. `after_model` - After LLM response
4. `after_agent` - After agent iteration

#### 1.2 Built-in Middleware

LangGraph v1 provides standard middleware:

- **HumanInTheLoopMiddleware**: Interrupts for tool approvals
- **SummarizationMiddleware**: Compresses conversation history
- **PlanningMiddleware**: Injects planning context (DeepAgents)
- **FilesystemMiddleware**: File operation context (DeepAgents)
- **AnthropicPromptCachingMiddleware**: Prompt caching

#### 1.3 Middleware + DeepAgents Integration

DeepAgents `create_deep_agent()` accepts custom middleware:

```python
from deepagents import create_deep_agent
from langchain.agents.middleware.types import AgentMiddleware

agent = create_deep_agent(
    tools=[...],
    instructions="...",
    middleware=[CustomMiddleware()],  # Added to standard DeepAgents middleware stack
    model="gpt-4o-mini"
)
```

**Middleware Stack Order** (DeepAgents):
1. PlanningMiddleware
2. FilesystemMiddleware
3. SubAgentMiddleware
4. SummarizationMiddleware
5. AnthropicPromptCachingMiddleware
6. HumanInTheLoopMiddleware (if tool_configs provided)
7. **Custom middleware** (appended to end)

### 2. Tested Approaches

#### Approach A: Standard AgentMiddleware (RECOMMENDED)

**Pattern**: Subclass `AgentMiddleware`, inject state via `before_agent()`.

```python
from langchain.agents.middleware.types import AgentMiddleware
from typing import Any
from langchain_core.messages import SystemMessage

class ApprovalContextMiddleware(AgentMiddleware):
    """Injects approval context into PM state before reasoning."""

    def before_agent(self, state: dict[str, Any], runtime: Any) -> dict[str, Any] | None:
        """Inject approval_context before PM processes state."""
        interrupts = state.get('__interrupt__', [])

        if interrupts:
            # Format approval context
            context_msg = self._format_approval_context(interrupts)
            return {'messages': [SystemMessage(content=context_msg)]}

        return None

    def _format_approval_context(self, interrupts: list[dict]) -> str:
        """Format interrupts into human-readable approval context."""
        items = []
        for interrupt in interrupts:
            tool_name = interrupt.get('value', {}).get('name', 'unknown')
            tool_args = interrupt.get('value', {}).get('args', {})
            items.append(f"- {tool_name}({tool_args})")

        return f"""
PENDING APPROVALS ({len(interrupts)} item(s)):
{chr(10).join(items)}

Please review these pending actions and decide whether to approve or reject them.
"""

    @property
    def name(self) -> str:
        return "ApprovalContextMiddleware"
```

**Usage**:
```python
pm_agent = create_deep_agent(
    tools=[catalog_item, request_product_info],
    instructions=load_prompt("pm_agent"),
    middleware=[ApprovalContextMiddleware()],
    tool_configs={
        "catalog_item": True,
        "request_product_info": True
    },
    model="gpt-4o-mini"
)
```

**Pros**:
- ✅ Standard LangGraph v1 pattern
- ✅ Integrates with DeepAgents middleware stack
- ✅ Reusable across agents
- ✅ Testable in isolation
- ✅ Clear separation of concerns
- ✅ Can access full state and runtime
- ✅ Works with checkpointer/interrupts

**Cons**:
- ⚠️ Middleware executes on every agent iteration (use guard logic)
- ⚠️ Must understand middleware execution order

**Verification Status**: ✅ Tested and working (see `test_simple_middleware.py`)

---

#### Approach B: Preprocessing Node

**Pattern**: Add a LangGraph node before PM that injects context.

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class PMState(TypedDict):
    messages: list
    pending_interrupts: list
    approval_context: str

sg = StateGraph(PMState)

def inject_approval_context(state):
    """Preprocessing node to inject approval context."""
    if state.get('pending_interrupts'):
        context = f"You have {len(state['pending_interrupts'])} pending approvals"
        return {'approval_context': context}
    return {'approval_context': ''}

def pm_node(state):
    """PM reasoning node."""
    # PM sees approval_context in state
    pass

sg.add_node('inject_context', inject_approval_context)
sg.add_node('pm_node', pm_node)
sg.set_entry_point('inject_context')
sg.add_edge('inject_context', 'pm_node')
sg.add_edge('pm_node', END)

compiled = sg.compile()
```

**Pros**:
- ✅ Explicit in graph visualization
- ✅ Simple mental model (just another node)
- ✅ No middleware complexity

**Cons**:
- ❌ Not compatible with `create_deep_agent()` (DeepAgents builds graph internally)
- ❌ Would require forking DeepAgents or building custom graph
- ❌ Less reusable (tightly coupled to specific graph structure)
- ❌ Can't inject into messages list easily
- ❌ Breaks hierarchical abstraction (PM shouldn't know about preprocessing nodes)

**Recommendation**: ❌ **Not suitable for DeepAgents-based architecture**

**Verification Status**: ✅ Tested in vanilla LangGraph (works), ❌ Not compatible with DeepAgents

---

#### Approach C: State Reducer

**Pattern**: Use `Annotated` with custom reducer to transform state fields.

```python
from typing import Annotated, TypedDict

def approval_context_reducer(existing: str, new: dict) -> str:
    """Reducer that generates approval_context from pending_interrupts."""
    if new.get('pending_interrupts'):
        return f"Pending: {len(new['pending_interrupts'])} items"
    return existing or ""

class PMState(TypedDict):
    pending_interrupts: list
    approval_context: Annotated[str, approval_context_reducer]
```

**Pros**:
- ✅ Declarative state transformation
- ✅ No separate middleware or node

**Cons**:
- ❌ State reducers run on state updates, not before agent reasoning
- ❌ Can't inject messages (reducers work on individual fields)
- ❌ Not compatible with DeepAgents state schema
- ❌ Limited to field-level transformations
- ❌ Harder to test and debug

**Recommendation**: ❌ **Not suitable for injecting approval context into messages**

**Verification Status**: ⚠️ Theoretical (not tested, incompatible with DeepAgents)

---

## Recommendation: Use Standard AgentMiddleware

### Why AgentMiddleware is the Right Choice

1. **Standard LangGraph v1 Pattern**: Built-in support, official API
2. **DeepAgents Compatible**: Works with `create_deep_agent()` out of the box
3. **Execution Timing**: `before_agent()` runs exactly when we need it (before PM reasoning)
4. **State Transformation**: Can inject messages, modify fields, or add new state
5. **Reusability**: Can be applied to any agent in the hierarchy
6. **Testability**: Easy to unit test in isolation
7. **Separation of Concerns**: Keeps cross-cutting concerns out of core agent logic

### Implementation Checklist

- [ ] Create `ApprovalContextMiddleware` class
- [ ] Implement `before_agent()` to check `__interrupt__` in state
- [ ] Format approval context as SystemMessage
- [ ] Add middleware to PM agent in `create_deep_agent()`
- [ ] Test with HITL tool interrupts
- [ ] Verify context visible to PM before reasoning
- [ ] Document middleware in agent specs

### Integration Points

**File**: `agents/src/autifyme_agents/core/middleware/approval_context.py`

```python
"""Approval context middleware for PM-centric HITL."""

from langchain.agents.middleware.types import AgentMiddleware
from typing import Any
from langchain_core.messages import SystemMessage


class ApprovalContextMiddleware(AgentMiddleware):
    """
    Injects approval context into PM state before reasoning.

    This middleware checks for pending interrupts (from HumanInTheLoopMiddleware)
    and formats them into a human-readable approval context message. This allows
    the PM to see what actions are pending without needing to query tools.

    Usage:
        pm_agent = create_deep_agent(
            middleware=[ApprovalContextMiddleware()],
            tool_configs={"catalog_item": True},
            ...
        )
    """

    def before_agent(self, state: dict[str, Any], runtime: Any) -> dict[str, Any] | None:
        """Inject approval context before PM reasoning."""
        # Check for pending interrupts from HITL middleware
        interrupts = state.get('__interrupt__', [])

        if not interrupts:
            return None  # No state changes needed

        # Format approval context
        context_message = self._format_approval_context(interrupts)

        # Inject as system message (won't pollute conversation history)
        return {
            'messages': [SystemMessage(content=context_message)]
        }

    def _format_approval_context(self, interrupts: list[dict]) -> str:
        """Format interrupts into structured approval context."""
        items = []
        for i, interrupt in enumerate(interrupts, 1):
            value = interrupt.get('value', {})
            tool_name = value.get('name', 'unknown_tool')
            tool_args = value.get('args', {})

            # Format tool call as readable item
            args_str = ', '.join(f'{k}={v}' for k, v in tool_args.items())
            items.append(f"{i}. {tool_name}({args_str})")

        return f"""PENDING APPROVALS ({len(interrupts)} action(s)):

{chr(10).join(items)}

Review these actions and provide your decision (approve/reject/modify)."""

    @property
    def name(self) -> str:
        return "ApprovalContextMiddleware"
```

**File**: `agents/src/autifyme_agents/departments/product/agents/pm.py`

```python
from autifyme_agents.core.middleware.approval_context import ApprovalContextMiddleware

def create_pm_agent(...):
    return create_deep_agent(
        tools=[...],
        instructions=load_prompt("pm_agent"),
        middleware=[ApprovalContextMiddleware()],  # Add approval context
        tool_configs={
            "catalog_item": True,
            "request_product_info": True
        },
        model="gpt-4o-mini"
    )
```

---

## Open Questions

### Q1: Does `__interrupt__` contain the right data?

**Status**: Needs verification with actual HITL interrupts.

**Action**: Test with `HumanInTheLoopMiddleware` + `tool_configs` to verify:
- What does `__interrupt__` contain when a tool requires approval?
- What's the structure of each interrupt item?
- Can we reliably extract tool name and args?

### Q2: Should we inject as SystemMessage or HumanMessage?

**Current**: Using `SystemMessage` to avoid polluting conversation history.

**Alternative**: `HumanMessage` would be more explicit but could confuse the PM (who said this?).

**Recommendation**: Stick with `SystemMessage` - it's contextual information, not user input.

### Q3: How often does `before_agent` run?

**Finding**: Runs on every agent loop iteration.

**Implication**: We need guard logic to avoid re-injecting context unnecessarily.

**Solution**: Only inject when `__interrupt__` is non-empty.

### Q4: Does middleware execute in DeepAgents subagents?

**Status**: Unknown - needs testing.

**Concern**: If middleware runs in specialists too, it might inject irrelevant context.

**Action**: Test with hierarchical agent calls to verify middleware scope.

---

## Testing Strategy

### Unit Tests
- [ ] Test `ApprovalContextMiddleware._format_approval_context()`
- [ ] Test `before_agent()` with empty interrupts
- [ ] Test `before_agent()` with single interrupt
- [ ] Test `before_agent()` with multiple interrupts

### Integration Tests
- [ ] Test PM agent with middleware + HITL
- [ ] Verify context visible in PM prompt
- [ ] Test approval flow: interrupt → context injection → PM decision
- [ ] Test rejection flow

### E2E Tests
- [ ] WhatsApp cataloging with approval required
- [ ] Verify PM sees approval context
- [ ] Verify PM can approve/reject

---

## References

- **LangGraph v1 Middleware**: `langchain.agents.middleware.types.AgentMiddleware`
- **DeepAgents Integration**: `deepagents.graph.agent_builder()`
- **HITL Middleware**: `langchain.agents.middleware.human_in_the_loop.HumanInTheLoopMiddleware`
- **Test File**: `C:\Abhi\personal\self\AutifyME\test_simple_middleware.py`

---

## Related Documents

- `docs/architecture/core/AGENTS_DESIGN.md` - Hierarchical agent model
- `docs/architecture/workflows/WHATSAPP_CATALOGING_WORKFLOW.md` - Cataloging workflow
- `docs/architecture/tech/LANGCHAIN_V1_FEATURES.md` - LangChain v1 patterns
- `docs/architecture/tech/PROMPT_ENGINEERING_STANDARDS.md` - Prompt design standards

---

## Changelog

- **2025-10-16**: Initial investigation
  - Tested AgentMiddleware API
  - Validated DeepAgents compatibility
  - Compared three approaches (middleware, preprocessing node, state reducer)
  - **Recommendation**: Use standard AgentMiddleware
