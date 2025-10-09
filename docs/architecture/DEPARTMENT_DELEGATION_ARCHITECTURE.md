# Department Delegation Architecture

**Date**: 2025-10-09
**Status**: Architectural Decision Record
**Purpose**: Explain why departments are wrapped as tools instead of DeepAgents SubAgents

---

## TL;DR

**Current Approach**: Departments wrapped as tools that PM calls
**Why**: DeepAgents SubAgent doesn't support full CompiledStateGraph agents
**Alternative Considered**: Direct SubAgent delegation (doesn't work with our architecture)

---

## The Question

**User asked**: "Why is the department sent as a tool to PM?"

**Valid concern**: Seems counterintuitive - shouldn't PM delegate directly to department agents using DeepAgents SubAgent feature?

---

## The Architecture Evolution

### Attempt 1: Department as SubAgent Model (FAILED)

**Initial approach**:
```python
# This was our first attempt
cataloging_dept = create_cataloging_department(...)  # Returns CompiledStateGraph

subagents = [
    SubAgent(
        name="cataloging_department",
        model=cataloging_dept,  # ❌ DOESN'T WORK
        description="Handles product cataloging"
    )
]
```

**Error encountered**:
```
AttributeError: 'CompiledStateGraph' object has no attribute 'bind_tools'
```

**Root cause**:
- DeepAgents SubAgent expects `model` parameter to be an LLM-like Runnable (has `.bind_tools()` method)
- Our department agents are full `CompiledStateGraph` from LangGraph
- CompiledStateGraph doesn't have `.bind_tools()` - it's a complete workflow, not just an LLM

**Evidence**: REPL testing confirmed this (conversation summary from previous session)

---

### Attempt 2: Lightweight SubAgent (INCOMPLETE)

**Considered approach**:
```python
# Use SubAgent with just the LLM, not full graph
subagents = [
    SubAgent(
        name="cataloging_department",
        model=get_llm(),  # Just the LLM
        description="Handles product cataloging",
        tools=[analyze_image, save_product]  # Department's tools
    )
]
```

**Problems with this approach**:
1. **Loses middleware**: Department-level context injection, error handling
2. **Loses HITL**: Department's approval flows managed by middleware
3. **Loses state management**: Department's own checkpointing for complex workflows
4. **Loses specialists**: Can't delegate to specialists within department

**Conclusion**: This makes departments "dumb" - just LLM + tools, not full agents

---

### Current Approach: Department as Tool (WORKING)

**Implementation**:
```python
def _create_department_tools(...) -> list:
    # Create FULL department agent with all capabilities
    cataloging_dept_agent = create_cataloging_department(
        checkpointer=checkpointer,
        storage=storage,
        enable_hitl=True,  # ✅ Department has HITL
    )

    @tool("cataloging_department")
    def invoke_cataloging_department(task_description: str) -> dict:
        """Handle product cataloging workflows."""
        result = cataloging_dept_agent.invoke(
            {"messages": [HumanMessage(content=task_description)]},
            config={"configurable": {"thread_id": f"dept_{hash(task_description) % 100000}"}},
        )
        # Return structured result to PM
        return {"success": True, "result": content}

    return [invoke_cataloging_department]
```

**How PM uses it**:
```python
# PM's perspective (from its prompt)
# "Call the cataloging_department tool with semantic task description"

project_manager = create_deep_agent(
    tools=[invoke_cataloging_department, ...],  # Department as tool
    subagents=[],  # No subagents
    ...
)
```

**What this preserves**:
- ✅ Full department agent capabilities (middleware, specialists, state)
- ✅ Department-level HITL approval flows
- ✅ Department's own checkpointing for complex tasks
- ✅ Specialist delegation within department
- ✅ Department-specific error handling and recovery
- ✅ Clean separation: PM doesn't know department internals

---

## Architectural Alignment

### Hierarchical Model: ✅ MAINTAINED

```
PM (DeepAgent)
 ↓ calls tool →
    Department Agent (CompiledStateGraph)
     ↓ delegates →
        Specialist Agent (CompiledStateGraph)
         ↓ uses →
            Tools (LangChain Tools)
```

**PM's role**: Intent classification, task description, routing
**Department's role**: Execute workflow using specialists and tools
**PM doesn't care HOW**: Department is black box with well-defined interface

### Tool Abstraction: ✅ CORRECT PATTERN

From LangChain perspective:
- Tools are functions the agent can call
- Tools can do ANYTHING - call APIs, run workflows, invoke other agents
- Department-as-tool wraps complex workflow in simple tool interface

**Analogy**: Like a microservice API
- PM calls department API (tool)
- Department does complex internal work
- Department returns structured result
- PM doesn't know or care about department's implementation

---

## Alternative: Direct Agent Invocation (Without DeepAgents)

**Could we skip DeepAgents entirely?**

```python
# Don't use create_deep_agent, just manual orchestration
def project_manager_manual(message: str):
    # PM uses LLM to classify intent
    intent = llm.classify(message)

    # PM manually routes to department
    if intent == "catalog":
        result = cataloging_dept.invoke(message)
    elif intent == "inquiry":
        result = inquiry_dept.invoke(message)

    return result
```

**Problems**:
- ❌ Loses DeepAgents planning capabilities
- ❌ Loses DeepAgents built-in orchestration features
- ❌ Manual routing logic instead of agentic decision-making
- ❌ Harder to add new departments (need code changes)

**Conclusion**: DeepAgents adds value, we should use it

---

## Is Current Approach a Compromise?

**Question**: Does wrapping departments as tools feel like a workaround?

**Answer**: No, it's the correct abstraction

**Reasoning**:
1. **Separation of Concerns**: PM shouldn't know department internals
2. **Interface Design**: Tool interface is clean semantic delegation
3. **Extensibility**: Add new departments by adding new tools
4. **Reusability**: Departments can be called from other PMs or contexts
5. **Testability**: Department can be tested independently as a tool

**Similar patterns in software**:
- REST APIs: Frontend calls backend API (doesn't know implementation)
- Microservices: Service A calls Service B's endpoint (doesn't know internals)
- Library functions: User calls function (doesn't know algorithm)

---

## Could DeepAgents Be Used Differently?

**Researched**: Is there a way to use SubAgent with CompiledStateGraph?

**Finding**: No, based on DeepAgents source code and REPL testing:
- SubAgent.model must have `.bind_tools()` method
- Only LLMs and Runnables with `.bind_tools()` work
- CompiledStateGraph doesn't implement this interface

**Potential future enhancement**:
- Open DeepAgents issue/PR to support CompiledStateGraph as SubAgent model
- Would require DeepAgents to handle graph invocation differently
- Out of our control for now

---

## Conclusion

**Current architecture is correct** for these reasons:

1. **Technical constraint**: DeepAgents SubAgent doesn't support CompiledStateGraph
2. **Architectural benefit**: Clean separation between PM and departments
3. **Functional preservation**: Departments keep all capabilities (middleware, HITL, state)
4. **Pattern alignment**: Tool abstraction is standard practice
5. **Future-proof**: Easy to add new departments as tools

**Recommendation**: Keep current approach

**Alternative considered**: Skip DeepAgents entirely and use manual routing
- **Trade-off**: Lose DeepAgents planning/orchestration features
- **Not recommended** unless DeepAgents proves problematic

---

## Code References

- `agents/src/autifyme_agents/workflows/project_manager.py:56-112` - Department tool creation
- `agents/src/autifyme_agents/departments/cataloging_department.py` - Full department agent
- `agents/src/autifyme_agents/prompts/project_manager.prompt` - PM delegation instructions

---

## Related Docs

- `AGENTS_DESIGN.md` - Hierarchical agent model
- `PROJECT_MANAGER_DESIGN.md` - PM role and responsibilities
- `WHATSAPP_CATALOGING_WORKFLOW.md` - End-to-end workflow

---

## Questions for Discussion

1. **Does this explanation make sense?**
2. **Should we reconsider the architecture?**
3. **Is there a better approach we haven't considered?**

**User feedback welcome** - this is a critical architectural decision worth getting right.
