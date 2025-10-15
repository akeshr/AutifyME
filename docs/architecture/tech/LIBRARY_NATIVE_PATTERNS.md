# Library-Native Patterns for AutifyME

**Created**: 2025-10-11
**Libraries**: LangChain v1, LangGraph v1, DeepAgents, LangSmith

---

## Principle

**Use library capabilities, don't fight them.** Custom solutions only when library doesn't support the use case.

---

## Pattern 1: Agent Hierarchy with `create_agent` ✅

**Rule**: All LLM interactions use `create_agent` (except PM which uses `create_deep_agent`).

**Benefits:**
- Automatic LangSmith tracing
- Middleware support (caching, HITL, summarization)
- Structured outputs via `response_format`
- Uniform observability

**Implementation:**

```python
# ✅ Specialist as create_agent
specialist = create_agent(
    model=llm,
    tools=[],
    system_prompt=prompt,
    response_format=Product,  # Structured output
    checkpointer=checkpointer,  # Optional
    name="CatalogingSpecialist",
)

# ❌ NOT this
llm_with_struct = llm.with_structured_output(Product)
chain = prompt | llm_with_struct  # Misses middleware, tracing
```

---

## Pattern 2: DeepAgents CustomSubAgent for Stateful Subagents ✅

**Discovery**: DeepAgents' `task` tool resets message history on every invocation:

```python
# deepagents/middleware.py:183
state["messages"] = [{"role": "user", "content": description}]  # ← Resets!
result = sub_agent.invoke(state)
```

**This breaks stateful subagents that need checkpointing** (e.g., for HITL interrupts).

**Solution**: Use **CustomSubAgent** with pre-built checkpointed graph.

**Implementation:**

```python
# Create department with its own checkpointer
dept_graph = create_agent(
    model=llm,
    tools=[...],
    system_prompt=prompt,
    checkpointer=checkpointer,  # ← Department's checkpointer
    middleware=[HumanInTheLoopMiddleware(...), ...],
)

# Pass as CustomSubAgent to PM
pm = create_deep_agent(
    model=llm,
    instructions=pm_prompt,
    subagents=[
        {
            "name": "cataloging_department",
            "description": "Handles product cataloging",
            "graph": dept_graph,  # ← CustomSubAgent with checkpoint
        }
    ],
    checkpointer=checkpointer,  # PM's checkpointer
)
```

**Key**: `"graph"` key makes DeepAgents use the graph directly, bypassing `task` tool's state reset.

---

## Pattern 3: Checkpoint Namespace for Nested Agents ✅

**Problem**: When department (subagent) interrupts, where does checkpoint live?

**Answer**: LangGraph creates nested checkpoint namespaces automatically.

**Structure:**
```
thread_id: "user_123"
├─ namespace: "" (root) → PM checkpoint
└─ namespace: "task:cataloging_department" → Department checkpoint
```

**Resume Pattern:**

```python
# ❌ Wrong: Resume at PM level
pm.stream(Command(resume={...}), config={"configurable": {"thread_id": thread_id}})
# Department re-invoked with reset state → corruption

# ✅ Right: Resume at department's checkpoint namespace
dept.stream(
    Command(resume={interrupt_id: {"type": "accept"}}),
    config={
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_ns": "task:cataloging_department",  # ← Target dept's checkpoint
        }
    }
)
```

**Rationale**: Direct namespace targeting ensures clean state resumption.

---

## Pattern 4: Command for Resumption (Not Messages) ✅

**Problem**: Approval messages polluting conversation history causes HITL validation errors.

**Library-Native Solution**: Use `Command` object, never add approval as message.

```python
# ❌ Wrong: Add approval as message
messages.append(HumanMessage(content="approve"))
agent.invoke({"messages": messages})  # Breaks HITL validation

# ✅ Right: Use Command
command = Command(
    resume={
        interrupt_id: {
            "type": "accept",  # or "edit"
            "args": edited_fields,  # Optional edits
        }
    }
)
agent.stream(command, config=config)  # Clean resumption
```

**Key**: Command is metadata, not conversation content. HITL middleware handles it correctly.

---

## Pattern 5: response_format for Structured Outputs ✅

**LangChain v1 Feature**: `response_format` in `create_agent` for structured outputs.

```python
# ✅ Library-native
agent = create_agent(
    model=llm,
    tools=[],
    response_format=ProductModel,  # Pydantic model
)
result = agent.invoke({"messages": [...]})
product = result["response"]  # ProductModel instance

# ❌ Old pattern (bypasses agent benefits)
llm_struct = llm.with_structured_output(ProductModel)
product = llm_struct.invoke([...])  # No middleware, no tracing as agent
```

---

## Pattern 6: HumanInTheLoopMiddleware with interrupt_on ✅

**LangChain v1 Native**: Middleware-based HITL, not manual interrupts.

```python
agent = create_agent(
    model=llm,
    tools=[save_product_tool, ...],
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "save_product": {
                    "allow_accept": True,
                    "allow_edit": True,
                    "allow_respond": True,
                }
            }
        )
    ],
    checkpointer=checkpointer,  # Required for interrupts
)
```

**Behavior:**
- Agent calls `save_product` → Middleware intercepts
- Creates LangGraph interrupt automatically
- Checkpoint persisted at interrupt point
- Resume with Command → Middleware validates and executes tool

**Key**: Don't manual interrupt logic. Let middleware handle it.

---

## Pattern 7: Checkpoint Isolation for Concurrent Workflows ✅

**Problem**: Multiple users, multiple workflows - how to isolate state?

**Library-Native Solution**: Use `thread_id` in config.

```python
# Each user/conversation gets unique thread_id
config = {
    "configurable": {
        "thread_id": f"{platform}:{user_id}",  # e.g., "whatsapp:+1234567890"
        "checkpoint_ns": "task:cataloging_department",  # For nested agents
    }
}

agent.stream(input, config=config)
```

**Isolation:**
- Each thread_id has independent checkpoint
- Nested agents use checkpoint_ns for sub-isolation
- No state bleeding between users

---

## Pattern 8: Middleware Composition ✅

**LangChain v1**: Middleware stack with automatic ordering.

```python
middleware = [
    CompanyContextMiddleware(storage),  # Inject company context first
    HumanInTheLoopMiddleware(...),  # HITL interrupts
    AnthropicPromptCachingMiddleware(...),  # Cache prompts
    SummarizationMiddleware(...),  # Summarize long conversations
]

agent = create_agent(
    model=llm,
    tools=[...],
    middleware=tuple(middleware),  # Applied in order
)
```

**Execution Order:**
1. before_model hooks (top to bottom)
2. Model invocation
3. after_model hooks (top to bottom)
4. Tool execution
5. Tool post-processing

---

## Pattern 9: LangSmith Auto-Tracing ✅

**Zero-Config Observability**: Just set env vars.

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=...
LANGCHAIN_PROJECT=autifyme-agents
```

**Automatic:**
- Agent runs traced as spans
- Tool calls traced with inputs/outputs
- Middleware hooks traced
- Errors captured with stack traces
- Nested agents show hierarchy

**Manual Enhancement:**

```python
agent.invoke(
    input,
    config={
        "tags": ["approval", "cataloging"],
        "metadata": {
            "user_id": sender,
            "workflow": "cataloging",
        }
    }
)
```

---

## Anti-Patterns (What NOT to Do) ❌

### 1. Direct LLM Calls for Agents
```python
# ❌ Bypasses middleware, tracing
llm.invoke([SystemMessage(...), HumanMessage(...)])

# ✅ Use create_agent
agent.invoke({"messages": [...]})
```

### 2. Manual State Management
```python
# ❌ Custom state persistence
save_to_db(thread_id, messages)

# ✅ Use checkpointer
create_agent(..., checkpointer=checkpointer)
```

### 3. String-Based Approval Parsing
```python
# ❌ Hardcoded keywords
if text.lower() == "approve": ...

# ✅ Use LLM classification
classifier = create_agent(..., response_format=ApprovalDecision)
```

### 4. Resuming Wrong Layer
```python
# ❌ Resume parent when child interrupted
pm.stream(Command(resume={...}), config={"thread_id": ...})

# ✅ Resume at correct checkpoint namespace
dept.stream(Command(resume={...}), config={
    "configurable": {"thread_id": ..., "checkpoint_ns": "task:dept"}
})
```

### 5. Adding Approval as Message
```python
# ❌ Pollutes conversation history
messages.append(HumanMessage(content="approve"))

# ✅ Use Command
Command(resume={interrupt_id: {"type": "accept"}})
```

---

## Complete Architecture

```
PM (create_deep_agent with checkpointer)
  └─> task tool → Cataloging Department (create_agent, CustomSubAgent)
        ├─> image_analysis_specialist tool → create_agent (response_format)
        ├─> cataloging_specialist tool → create_agent (response_format)
        └─> save_product tool → Deterministic (no LLM)

ApprovalIntentClassifier (create_agent with response_format)

Resumption: At department's checkpoint namespace directly
State: Command-based, no message pollution
Tracing: Automatic via LangSmith
Middleware: Native composition (HITL, caching, etc.)
```

---

## Key Takeaways

1. **create_agent everywhere** (except PM = create_deep_agent)
2. **CustomSubAgent for stateful subagents**
3. **Checkpoint namespaces for nested agents**
4. **Command for resumption, not messages**
5. **response_format for structured outputs**
6. **Native middleware, don't reinvent**
7. **Trust LangSmith auto-tracing**
8. **Resume at correct checkpoint layer**

---

## References

- LangChain v1: https://python.langchain.com/docs/langchain
- LangGraph v1: https://python.langchain.com/docs/langgraph
- DeepAgents: https://github.com/langchain-ai/deepagents
- LangSmith: https://smith.langchain.com/
