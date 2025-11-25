# LangGraph v1 (Alpha) - Production Agent Runtime

**Created:** October 7, 2025
**Installed Version:** `langgraph==1.0.0a4`
**Related Packages:** `langgraph-checkpoint-postgres==2.0.24`, `langgraph-prebuilt==0.7.0a2`
**Release Date:** September 29, 2025
**Stable Release:** Expected late October 2025

**Reference Materials:**
- Official Docs: https://langchain-ai.github.io/langgraph/
- Release Announcement: https://blog.langchain.com/langchain-langchain-1-0-alpha-releases/
- GitHub Repo: https://github.com/langchain-ai/langgraph

---

## Executive Summary

LangGraph v1 is a **low-level agent orchestration framework** for building stateful, long-running agents with production-grade reliability. Unlike high-level abstractions, it provides fine-grained control over agent execution, state management, and workflow composition.

**Core Philosophy:** Inspired by Pregel and Apache Beam distributed systems, LangGraph treats agent workflows as **graphs** where nodes are computation steps and edges define execution flow. The Pregel-inspired executor enables parallel execution, fault tolerance, and resumability.

**Key Capabilities:**
1. **Durable Execution** - Persist and resume workflows from any point, survive crashes
2. **Human-in-the-Loop (HITL)** - Pause, inspect, modify agent state with interrupt primitives
3. **Comprehensive Memory** - Short-term (checkpoints) and long-term (Store) persistence
4. **Flexible Orchestration** - Cycles, conditionals, map-reduce, subgraphs, dynamic routing
5. **Production Observability** - Streaming modes, debug traces, LangSmith integration

**Migration Note:** No breaking changes from v0.6.6 to v1.0, making upgrades seamless.

---

## 🏗️ Core Architecture

### StateGraph & Pregel Executor

**StateGraph** is the primary graph abstraction parameterized by a user-defined state schema.

**Pregel-Inspired Execution:**
- Programs execute in discrete "super-steps" (iterations over nodes)
- Nodes running in parallel belong to the same super-step
- Sequential nodes belong to separate super-steps
- Updates from all parallel nodes are applied sequentially once the superstep completes
- State keys with multiple updates use **reducer functions** to merge values (e.g., `add` operator for lists)
- Enables distributed execution patterns (fan-out, fan-in, map-reduce)

**Benefits for AutifyME:**
- Specialist agents can execute in parallel when independent
- PM can orchestrate multi-step workflows with dependency management
- Checkpoints captured after each super-step for crash recovery
- Multiple specialists can update shared state safely via reducers

---

## 🔄 Persistence & Checkpointing

### Built-in Persistence Layer

LangGraph persists graph state at every super-step via **checkpointers**, enabling restart-safe execution.

**Available Implementations:**
- **InMemorySaver** - For experimentation and testing
- **SqliteSaver** - Local development workflows
- **PostgresSaver** - Production deployment (included in `langgraph-checkpoint-postgres`)

**Checkpoint Metadata:**
- **Source types:** `input` (from invoke), `loop` (from Pregel), `update` (manual state update), `fork` (copied checkpoint)
- **Thread-scoped:** Each conversation/workflow has its own checkpoint thread
- **Time-travel capable:** Navigate to any historical checkpoint

**Why This Matters:**
- WhatsApp webhook crashes don't lose cataloging progress
- HITL approval flows resume exactly where they paused
- Debugging via checkpoint replay without re-running LLM calls

### Threads

**Threads** represent conversation sessions or workflow instances. Each thread maintains its own checkpoint history, enabling:
- Multi-user conversations (one thread per user)
- Isolated state per workflow execution
- Historical conversation replay

---

## 🧠 Memory System

### Short-Term Memory (Checkpoints)

Thread-scoped state stored in checkpoints, accessible within the current workflow execution. Automatically managed by LangGraph's persistence layer.

### Long-Term Memory (Store)

**Cross-thread persistent storage** for information that spans conversations or workflows.

**Key Features:**
- **Namespace-based organization:** `("user", user_id)`, `("company", company_id)`
- **JSON document storage:** Flexible schema-less data
- **Content-based search:** Query across namespaces
- **Hierarchical namespaces:** `("org", org_id, "team", team_id)`

**Available Implementations:**
- **InMemoryStore** - Testing
- **PostgresStore** - Production (Supabase-compatible)
- **MongoDB Store** - Scalable long-term memory (August 2025)
- **Redis Store** - With vector search capabilities

**Why This Matters:**
- Store company profile once, access across all workflow threads
- Remember product preferences across catalog sessions
- Build user profiles that persist beyond single conversations

---

## 🎛️ Runtime & Context Management

### Runtime Object (Added v0.6.0)

**Replaces** `config["configurable"]` with cleaner dependency injection pattern.

**Capabilities:**
- **Static runtime context:** Immutable data (user metadata, DB connections, tools) passed at invocation
- **context_schema:** Type-safe context definition (replaces deprecated `config_schema`)
- **Accessible via Runtime object:** Clean typed access to user data without deep nesting

**Why This Matters:**
- Inject company profile, storage adapters, tenant metadata into workflows
- Type-safe context access in nodes and middleware
- Aligns with hexagonal architecture (dependencies injected, not hardcoded)

### Dependency Injection for Tools

**InjectedState & InjectedStore annotations** mark tool parameters for automatic injection.

**Pattern:**
Tools declare they need state/store without the LLM knowing about it. LangGraph injects values automatically at runtime.

**Why This Matters:**
- Tools access company context without it being part of the LLM's tool schema
- Keeps tool signatures clean and focused
- Storage adapters injected without polluting agent prompts

---

## 🚦 Human-in-the-Loop (HITL) Patterns

### Interrupt Primitives

**Two Types:**

**1. Static Interrupts:**
- `interrupt_before`: Pause before specific nodes execute
- `interrupt_after`: Pause after specific nodes complete
- Configured at graph compile time

**2. Dynamic Interrupts:**
- `interrupt()`: Pause from inside a node based on runtime state
- Allows conditional HITL (e.g., pause only if confidence < 0.8)

**Resume with Command:**
Execution resumes via `Command(resume=...)` which can inject human input and continue.

**Common HITL Patterns:**
- **Approve/Reject:** Review critical actions before execution (e.g., `save_product`)
- **Edit State:** Modify draft data before proceeding (e.g., fix product name)
- **Review Tool Calls:** Inspect and modify LLM tool invocations
- **Wait for Input:** Collect user input mid-workflow

**Why This Matters:**
- Implements our approval workflow for cataloging (review before save)
- Quality gates for PM decisions
- Human oversight without custom interrupt infrastructure

---

### ⚠️ CRITICAL: Interrupt Detection in Subgraphs

**Problem Discovered:** October 13, 2025 (3-day debugging effort)

When interrupts occur in **subgraphs** (e.g., DeepAgents HITL middleware in department), the interrupt state is NOT accessible via `checkpointer.get_tuple(config).checkpoint`.

**WRONG APPROACH (causes bugs):**
```python
# ❌ DOES NOT WORK - checkpoint dict has no __interrupt__ field!
state = checkpointer.get_tuple(config)
checkpoint = state.checkpoint
interrupts = checkpoint.get("__interrupt__", [])  # Always returns []
```

**Correct Checkpoint Structure:**
The `Checkpoint` TypedDict has these fields:
- `v`, `id`, `ts` (metadata)
- `channel_values` (state data)
- `channel_versions`, `versions_seen` (internal tracking)

**NO `__interrupt__` field exists in checkpoint!**

---

**CORRECT APPROACH:**
```python
# ✅ Use graph.get_state() to access StateSnapshot
state_snapshot = graph.get_state(config)

if state_snapshot and state_snapshot.interrupts:
    pending_interrupt = state_snapshot.interrupts[0]
    interrupt_id = pending_interrupt.id
    # Resume with Command
    command = Command(resume={interrupt_id: resume_value})
```

**StateSnapshot Structure (langgraph.types):**
```python
class StateSnapshot(NamedTuple):
    values: dict[str, Any]           # Current state
    next: tuple[str, ...]            # Next nodes to execute
    config: RunnableConfig           # Graph config
    metadata: CheckpointMetadata     # Checkpoint metadata
    created_at: str | None           # Timestamp
    parent_config: RunnableConfig    # Parent checkpoint
    tasks: tuple[PregelTask, ...]    # Pending tasks
    interrupts: tuple[Interrupt, ...] # ✅ INTERRUPTS HERE!
```

---

**Resume Value Format:**

For LangChain's `HumanInTheLoopMiddleware` (DeepAgents HITL):
```python
# ❌ WRONG - middleware expects a LIST
resume_value = {"type": "accept"}

# ✅ CORRECT - must be list of HumanInTheLoopResponse
resume_value = [{"type": "accept"}]
# Or: [{"type": "response", "args": "User rejected"}]
# Or: [{"type": "edit", "args": {"action": "save_product", "args": {...}}}]
```

**Why:** Middleware may handle multiple tool call interrupts simultaneously, so it expects `list[HumanInTheLoopResponse]`.

---

**Error Symptoms:**

If you detect interrupts incorrectly:
1. No pending interrupt found when there should be one
2. User approval treated as new message
3. OpenAI error: `"An assistant message with 'tool_calls' must be followed by tool messages"`
4. State becomes corrupted with dangling tool calls

**Fix Applied:** `runner_v2.py:286-304`, October 13, 2025

---

**Key Learnings:**

1. **Never inspect checkpoint dict directly for interrupts** - use `graph.get_state().interrupts`
2. **StateSnapshot is the API** - checkpoint dict is internal structure
3. **Subgraph interrupts propagate** - parent can detect child interrupts via `get_state()`
4. **Resume values must match middleware expectations** - check middleware source for correct format
5. **Test HITL flows end-to-end** - interrupt handling is complex and easy to break

**Documentation:**
- API Reference: https://langchain-ai.github.io/langgraph/reference/types/#statesnapshot
- HITL Guide: https://langchain-ai.github.io/langgraph/concepts/agentic_concepts/#human-in-the-loop

---

## 🎯 Dynamic Control Flow

### Command API

**Command objects** allow nodes to both update state **and** control flow in a single operation.

**Capabilities:**
- `Command(update={...})`: Update specific state keys
- `Command(goto="node_name")`: Jump to specific node
- `Command(update={...}, goto=...)`: Combined state update + routing

**Why This Matters:**
- Specialist can update state and signal completion in one step
- Department can decide routing based on results without separate conditional edge
- Reduces graph complexity (logic inside nodes vs. edge functions)

### Send API (Map-Reduce)

**Distribute state to multiple node instances dynamically.**

**Use Cases:**
- Unknown number of parallel tasks (e.g., analyze N images)
- Each instance receives different state (not broadcast)
- Results aggregated via reduce node or state reducer functions

**Pattern:**
Node returns `[Send("processor", state1), Send("processor", state2), ...]` to spawn parallel executions.

**State Aggregation:**
- Parallel nodes execute in the same superstep
- Updates to shared state keys use reducer functions (e.g., `add` operator to collect results in list)
- Explicit reduce node can perform custom aggregation logic after all parallel branches complete

**Why This Matters:**
- Future: Analyze multiple product images in parallel
- Process batch cataloging requests concurrently
- Future: Marketing specialist generates content for multiple platforms simultaneously
- Results automatically merged via state reducers without custom aggregation code

---

## 🔀 Graph Composition Patterns

### Conditional Edges

**Dynamic routing based on state.**

**Pattern:**
Define a routing function that examines state and returns the next node name. Enables branching logic, error routing, and termination conditions.

**Built-in Helper:**
`tools_condition` from `langgraph.prebuilt` routes to `ToolNode` if LLM made tool calls, else to `END`.

**Why This Matters:**
- Route to approval node only if product needs review
- Handle errors by routing to recovery node
- Terminate loops when max iterations reached

### Subgraphs

**Nest complete graphs as nodes within parent graphs.**

**Two Patterns:**
1. **Shared state keys:** Parent and child communicate via common state channels (e.g., `messages`)
2. **Different schemas:** Transform parent state → child state in node function

**Benefits:**
- Modular workflow composition
- Specialist agents as subgraphs of PM
- Checkpointer propagates automatically to subgraphs

**Why This Matters:**
- Each specialist is a subgraph with its own state schema
- PM orchestrates subgraphs without managing their internal state
- Catalog workflow can be reused in batch processing subgraph

### Cycles & Loops

**LangGraph natively supports cyclic workflows.**

**Recursion Limit:**
- Default: 25 steps
- Configurable per invocation: `graph.invoke({...}, {"recursion_limit": 100})`
- Prevents infinite loops while allowing long workflows

**Termination Patterns:**
- Conditional edge to `END` node when condition met
- Track `remaining_steps` in state and decrement per iteration

**Why This Matters:**
- Specialist agent loops (think → act → observe) until task complete
- Retry logic with bounded attempts
- Multi-round approval workflows (reject → revise → re-approve)

---

## 📡 Streaming Modes

**Five streaming modes for real-time output:**

### 1. Values Mode
Stream full state after each node execution. Shows complete conversation state at each step.

### 2. Updates Mode
Stream only state deltas (what changed). More efficient for large states.

### 3. Messages Mode
Stream LLM tokens as they're generated + metadata (node name, model info). Essential for real-time chat UX.

**Returns:** `(message_chunk, metadata)` tuples

### 4. Custom Mode
Emit arbitrary user-defined data from nodes via `get_stream_writer()`. Use for progress indicators, intermediate results, custom UI updates.

### 5. Debug Mode
Detailed trace of graph execution including node transitions, state snapshots, error details. For debugging complex workflows.

**Multi-Mode Streaming:**
Pass list as `stream_mode` parameter: `stream_mode=["values", "messages"]`

**Why This Matters:**
- WhatsApp users see typing indicators and token-by-token responses
- Frontend shows cataloging progress (analyzing image → extracting data → saving)
- Debugging in development with full traces

---

## 🛠️ Prebuilt Components

### ToolNode

**Executes tools in parallel with automatic error handling.**

**Features:**
- Supports sync and async tools concurrently
- Returns `ToolMessage` objects (success or error status)
- Configurable error handling (return errors vs. raise exceptions)
- Integrates with `messages` state key or custom key

**Why This Matters:**
- Standard pattern for tool-calling agents (no custom tool execution logic)
- Parallel tool execution improves performance
- Error handling built-in (tools can fail without crashing workflow)

### tools_condition

**Standard conditional logic for tool-calling agents.**

Routes to `ToolNode` if last AI message contains tool calls, else to `END`.

**Why This Matters:**
- Eliminates boilerplate routing logic in every agent
- Standard pattern across all specialist agents
- Compatible with LangChain v1 `create_agent`

### InjectedState & InjectedStore

**Annotations for dependency injection into tools.**

**Pattern:**
Mark tool parameters with `InjectedState` or `InjectedStore` to receive runtime values without LLM awareness.

**Why This Matters:**
- Tools access company profile without it being in tool schema
- Storage adapters injected without exposing to LLM
- Cleaner tool signatures focused on business logic

---

## 🆕 June 2025 Feature Updates

### Node Caching

**Cache results of individual nodes to skip redundant computation.**

**Use Cases:**
- Expensive operations (image analysis, embeddings generation)
- Deterministic nodes with same inputs
- Development iteration (don't re-run LLM calls)

**Why This Matters:**
- Save costs by caching image analysis results
- Faster development cycles (reuse previous LLM responses)
- Performance optimization for repeated operations

### Deferred Nodes

**Delay node execution until all upstream paths complete.**

**Use Cases:**
- Map-reduce patterns (wait for all map nodes before reduce)
- Consensus algorithms (collect all votes before deciding)
- Collaborative agents (wait for all specialists before synthesis)

**Why This Matters:**
- PM waits for all specialists before final decision (if multiple specialists invoked in parallel)
- Aggregate results from parallel specialist invocations
- Synchronization point in complex workflows

### Pre/Post Model Hooks

**Custom logic before/after LLM calls.**

**Use Cases:**
- **Pre-hooks:** Control context bloat (summarize messages), inject system prompts, rate limiting
- **Post-hooks:** Guardrails (filter toxic content), HITL checks (pause if unsure), response modification

**Why This Matters:**
- Implement cost controls (summarize context before expensive calls)
- Add compliance checks without changing agent logic
- Insert approval gates dynamically based on model output

---

## 🔗 LangChain Integration

LangGraph powers LangChain v1 agents under the hood:

**Integration Points:**
- `create_agent` from `langchain.agents` builds LangGraph `StateGraph`
- Middleware system runs on LangGraph middleware hooks
- `ToolNode` handles tool execution automatically
- Checkpointing enables HITL and recovery in agents

**Why This Matters:**
- Our specialist agents benefit from LangGraph features without direct usage
- Upgrading to explicit LangGraph gives more control when needed
- PM can use DeepAgents (which wraps LangGraph) for advanced orchestration

---

## 🎯 AutifyME Usage Strategy

### Current Implementation (2-Level Architecture)
- **Specialists:** Use `create_agent` with tools (LangGraph under hood)
- **PM:** Use `create_deep_agent` with specialist subagents
- **Checkpointing:** `PostgresSaver` for HITL approval persistence
- **HITL:** Configured via `tool_configs` on specialist tools
- **Streaming:** `messages` mode for WhatsApp token-by-token responses

### Future Expansion
- **Parallel Specialists:** Multiple specialists executing in same super-step
- **Store:** Company profile and user preferences across threads
- **Map-Reduce:** Batch cataloging via `Send` API
- **Additional Specialists:** Marketing, Operations, Inventory specialists as subagents

### When to Use Direct LangGraph
- **Complex orchestration:** PM coordinating multiple specialists with custom flow
- **Custom state schemas:** Specialist-specific state beyond messages
- **Advanced patterns:** Map-reduce, consensus, multi-stage approvals
- **Fine-grained control:** Need explicit control over execution flow

### When LangChain Agents Suffice
- **Simple delegation:** Specialist with tools executing workflows
- **Standard tool-calling:** Tool-calling loop with structured output
- **Middleware-driven:** Cross-cutting concerns handled by middleware

---

## 📊 Comparison: LangGraph vs. LangChain Agents

| Feature | LangChain Agents | LangGraph |
|---------|-----------------|-----------|
| **Abstraction Level** | High (opinionated patterns) | Low (full control) |
| **State Management** | Messages-only | Custom state schemas |
| **Cycles** | Fixed tool-calling loop | Arbitrary cycles |
| **Parallel Execution** | Limited | Native (super-steps) |
| **Subgraphs** | Not supported | First-class |
| **Custom Routing** | Middleware-based | Conditional edges + Command |
| **Use Case** | Specialists (domain experts) | Project Manager, complex workflows |

---

## 🚀 Key Takeaways

**For AutifyME Architecture (2-Level):**

1. **Specialists = LangChain Agents (LangGraph under hood)**
   - Benefit from LangGraph features without complexity
   - Middleware, HITL, checkpointing all available
   - Created via `create_agent` with tools parameter
   - Attached to PM as SubAgents

2. **Project Manager = DeepAgents (wraps LangGraph)**
   - Created via `create_deep_agent` with specialist subagents
   - Direct delegation without intermediate layer
   - Benefits from planning middleware and orchestration

3. **Persistence Strategy:**
   - Checkpointing (PostgresSaver) for workflow state
   - Store (PostgresStore) for company profile and long-term memory
   - Both Supabase-compatible

4. **HITL Implementation:**
   - Configured via `tool_configs` on specialist tools
   - `Command(resume=...)` for user input injection
   - Checkpoints preserve state during interrupts

5. **Scalability Path:**
   - Start with single specialist (cataloging)
   - Add more specialists as SubAgents (marketing, inventory, operations)
   - Use parallel specialist invocation for efficiency
   - Keep 2-level architecture for simplicity

---

## 📚 Key Resources

- **Official Docs:** https://langchain-ai.github.io/langgraph/
- **Conceptual Guides:** https://langchain-ai.github.io/langgraph/concepts/
- **How-To Guides:** https://langchain-ai.github.io/langgraph/how-tos/
- **API Reference:** https://langchain-ai.github.io/langgraph/reference/
- **Release Notes:** https://github.com/langchain-ai/langgraph/releases

---

## 📝 Changelog

**2025-10-13:** Added critical section on interrupt detection in subgraphs after 3-day debugging effort. Documents correct usage of `graph.get_state().interrupts` vs incorrect `checkpoint.get("__interrupt__")`.

**2025-10-07:** Initial comprehensive documentation of LangGraph v1 features and AutifyME usage strategy.

---

**Last Updated:** 2025-10-13
**Author:** AutifyME Team
**Status:** Production-Ready for v1 Alpha Features
