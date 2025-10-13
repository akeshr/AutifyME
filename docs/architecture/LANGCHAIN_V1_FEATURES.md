# LangChain v1 (Alpha) - New Features & Capabilities

**Installed Versions (Updated 2025-10-07):**
LangChain `1.0.0a12` (core `1.0.0a7`, community `0.3.30`, OpenAI `0.3.33`, Anthropic `1.0.0a2`)
LangGraph `1.0.0a4` (checkpoint-postgres `2.0.24`, prebuilt `0.7.0a2`, sdk `0.2.9`)
DeepAgents `0.0.11rc1` ✅ All features verified via REPL (see `LIBRARY_VERIFICATION_REPORT.md`)

**Reference Materials:**  
- LangChain OSS v1 release notes: https://docs.langchain.com/oss/python/releases/langchain-v1  
- LangGraph docs: https://langchain-ai.github.io/langgraph/  
- DeepAgents overview: https://blog.langchain.dev/deep-agents/

---

## Executive Summary

LangChain v1 represents a major evolution focusing on **production-grade agent systems**, **improved type safety**, and **tighter LangGraph integration**. Key themes:

1. **Agent-First Architecture** - Prebuilt agents moved from `langgraph.prebuilts` to `langchain.agents` with major improvements
2. **Multimodal & Reasoning Support** - New `.content_blocks` API for citations, reasoning traces, and complex content
3. **Enhanced Error Handling** - Built-in retry logic, structured exceptions, and HITL-friendly patterns
4. **Middleware System** ⭐️ NEW - Decorator-based cross-cutting concerns (auth, logging, tracing, rate limiting)
5. **Type Safety & Developer Experience** - Pydantic-first design, better IDE support, clearer APIs
6. **LangGraph Runtime Integration** - All agents now backed by LangGraph's stateful runtime

---

## 🚀 Major New Features

### 1. Package Restructuring & Modularization (LangChain 1.0.0a10)

**What it is:**  
LangChain has been refactored from a monolithic library into a set of smaller, more focused packages. This is a foundational change for v1.

**Key Packages:**
- **`langchain-core`**: The heart of the library, containing base abstractions, interfaces, and the LangChain Expression Language (LCEL). All other packages depend on this.
- **`langchain-community`**: Contains all third-party integrations (LLMs, vector stores, tools). This package is very large and will likely be broken up further.
- **`langchain`**: The "main" package. It contains high-level, chain-of-thought logic and orchestrators (agents, chains) that are provider-agnostic.
- **Partner Packages (`langchain-openai`, `langchain-anthropic`, etc.)**: Provider-specific SDKs that depend on `langchain-core`. This allows for smaller, more secure, and easier-to-manage dependencies.

**Why This Matters for AutifyME:**
- **Smaller Dependencies**: We can now install only the providers we need (e.g., `pip install langchain-openai langchain-anthropic`), reducing our dependency footprint.
- **Clearer Imports**: Imports now reflect the source of the component (e.g., `from langchain_openai import ChatOpenAI`), making the code easier to understand.
- **Stability**: Changes to a community integration in `langchain-community` won't affect the stability of `langchain-core`.
- **Backward Compatibility**: New `langchain-legacy` package available for deprecated code that hasn't been migrated yet.
- **Unified Documentation**: New docs site (docs.langchain.com) centralizes Python and JavaScript documentation in one place.

---

### 2. `.content_blocks` Property (LangChain Core 0.3.76)

**What it is:**  
A fully typed, structured view of LLM message content that standardizes modern features across providers.

**Key Capabilities:**
- **Reasoning Traces** - Access chain-of-thought from models like o1
- **Citations & Sources** - Extract grounding sources from responses
- **Server-Side Tool Calls** - Handle tool invocation metadata
- **Multimodal Content** - Images, PDFs, structured data in messages

**Example:**
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4.1-mini-2025-04-14")
response = llm.invoke("Analyze this image and cite sources")

# Old way (v0): response.content (plain string)
# New way (v1): response.content_blocks (structured list)

for block in response.content_blocks:
    if block.type == "text":
        print(block.text)
    elif block.type == "citation":
        print(f"Source: {block.source_url}")
    elif block.type == "reasoning":
        print(f"CoT: {block.reasoning_trace}")
```

**Why This Matters for AutifyME:**
- **Product Cataloging** - Extract image analysis results with confidence scores
- **Brand Voice** - Access reasoning traces to validate tone/style decisions
- **Multi-Department Context** - Pass structured citations between specialists
- **Transparency** - Show customers why a product was categorized a certain way

---

### 3. Prebuilt Agents & Middleware Pipeline

**What Changed:**
Agents moved from `langgraph.prebuilts` to `langchain.agents` with LangGraph-based implementation. The new `create_agent` function replaces the legacy `create_react_agent`.

**Important Distinction:**
- **Modern (Recommended):** `langchain.agents.create_agent` - LangGraph-based, production-ready, full middleware support
- **Legacy (Not Recommended):** `langchain.agents.react.agent.create_react_agent` - Older implementation based on ReAct paper, not suitable for production

**AutifyME uses the modern LangGraph-based version exclusively.**

```
langchain/
  agents/
    __init__.py            → exports create_agent (modern)
    react_agent.py         → core builder atop LangGraph
    middleware_agent.py    → middleware-aware agent graph
    middleware/            → HITL, summarization, prompt caching, logging, ...
```

**Deep Feature Highlights (package inspection):**
- Structured outputs handled via `ToolStrategy` (schema → tool binding) or `ProviderStrategy` (provider JSON schema).
- Middleware lifecycle (`before_model`, `modify_model_request`, `after_model`) allows prompt/context injection, HITL, logging.
- Automatic `ToolNode` creation merges regular tools, middleware tools, and structured-output tools. Supports parallel execution, `Command` updates, state/store injection (`InjectedState`, `InjectedStore`).
- State schema validation ensures TypedDict state includes `messages`, `remaining_steps`, and optionally `structured_response`.
- AI responses can emit `Command(update=..., goto=...)` to adjust state/flow without leaving the agent graph.

**Why This Matters for AutifyME:**
- Provides a production-ready scaffold for Department/PM agents with composable middleware (HITL, summarization, prompt caching).
- ToolNode semantics align with ports/adapters: deterministic tools, clear error semantics, structured outputs.
- Supports typed contracts between agents, matching our architecture requirements.

---

### 4. Enhanced Error Handling & Resilience

**New Capabilities:**

#### **Error Handling Patterns**
LangChain v1 centralises error handling at the tool boundary. Use these two tactics aligned with our Architecture-First rule:

1. Tool-level retries keep integration risk encapsulated:

```python
from tenacity import retry, stop_after_attempt, retry_if_exception_type
from langchain_core.tools import tool

@tool
@retry(
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(ExternalAPIError),
    reraise=True,
)
def my_tool(arg: str) -> str:
    return external_api_call(arg)
```

2. Structured output validation via `ToolStrategy` turns schema violations into ToolMessages that the agent can reason about:

```python
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

agent = create_agent(
    model=llm,
    tools=tools,
    response_format=ToolStrategy(
        schema=MyPydanticModel,
        handle_errors=True,
    ),
)
```

These approaches ensure tools remain deterministic while agents focus on reasoning.

---

### 5. State & Context Management (LangGraph 1.0.0a4 + Checkpoints)

**Key Pieces Observed:**
- `langgraph.runtime.Runtime`: run-scoped context (context, store, stream_writer, previous result) accessible inside nodes/middleware.
- `langgraph.checkpoint.postgres`: full Postgres saver with migrations, pipeline support, and pending send recovery.
- Channel abstractions (`langgraph.channels.*`): `AnyValue`, `LastValue`, `NamedBarrierValue`, etc., for message passing between nodes.
- Stores (`langgraph.store.*`): memory and Postgres-backed stores for embeddings/memories.

**Implications:**
- Supabase Postgres can host state checkpoints via bundled migrations (aligns with our persistence plan).
- Runtime enables typed dependency injection (user/company context, store handles) inside workflows.
- Channels/stores unlock advanced multi-node coordination when scaling beyond cataloging.

---

### 6. Middleware System (HITL, Summaries, Prompt Cache)

**Notable Middleware Implementations:**
- `HumanInTheLoopMiddleware`: constructs typed interrupt requests (allow_accept/edit/respond) and leverages `langgraph.types.interrupt` to pause/resume execution.
- `SummarizationMiddleware`: token-aware compaction that preserves AI/Tool message pairs; configurable prompt/messages-to-keep.
- `AnthropicPromptCachingMiddleware`: auto-injects prompt-caching headers for Claude models with TTL, fallback control.
- DeepAgents adds `PlanningMiddleware`, `FilesystemMiddleware`, `SubAgentMiddleware` for plan tracking, scratchpad file ops via `Command`, and sub-agent delegation.

**Why This Matters:**
- Supports our HITL architecture (approval/edit/reject flows before critical tools).
- Provides built-in context management (summaries) and cost optimization (prompt caching).
- DeepAgents middleware forms the basis for Project Manager planning workflows once cataloging validates the foundation.

---

### 7. LangGraph Runtime (1.0.0a4)

**Highlights:**
- `StateGraph` + Pregel executor powering compiled graphs from LangChain.
- Runtime context merge/override for dependency injection per run.
- `Command` objects let nodes update state or change flow programmatically.
- Managed helpers (`langgraph.managed`) such as `is_last_step` for cleanup logic.

**Implications for AutifyME:**
- All agents built with `create_agent` can tap into runtime (context, store) for dependency injection (company profile, tenant metadata).
- Pregel features (parallelism, retries) are available for future multi-department workflows.

---

### 8. Improved Type Safety & Developer Experience (LangChain Core 0.3.77)

#### **A. Message Type Updates**

**Breaking Change:**  
Chat model invocations now return `AIMessage` instead of `BaseMessage`.

```python
# V0: Generic BaseMessage
response: BaseMessage = llm.invoke("Hello")

# V1: Specific AIMessage (better IDE autocomplete)
response: AIMessage = llm.invoke("Hello")
print(response.content)  # IDE knows all AIMessage methods
```

#### **B. `.text()` → `.text` (Property)**

**Deprecation:**  
`.text()` method is now a property (backwards compatible with warning).

```python
# V0: Method call
text = message.text()

# V1: Property access
text = message.text  # Cleaner, more Pythonic
```

#### **C. Python 3.10+ Requirement**

**Breaking Change:**  
Python 3.9 support dropped. Requires **Python 3.10+**.

**Why:** Leverage modern Python features (match-case, better type hints, performance).

---

### 9. Anthropic & OpenAI Enhancements (Provider packages)

- `langchain_openai` 0.3.34: native `response_format` passthrough for GPT-5 family, SSE streaming, tool routing updates.
- `langchain_anthropic` 0.3.21: integrates prompt caching middleware, structured output hooks, and multimodal support.
- DeepAgents defaults to Claude Sonnet 4 (64k tokens) via `get_default_model()` ensuring planning headroom.

---

### 10. DeepAgents Stack (0.0.11rc1)

**Components:**
- `deepagents.graph.create_deep_agent`: wraps LangChain `create_agent` with default middleware (planning, filesystem, sub-agent routing, summarization, prompt caching, optional HITL tool configs).
- Built-in tools (`write_todos`, `ls`, `read_file`, `write_file`, `edit_file`) return LangGraph `Command` objects for stateful updates.
- `SubAgentMiddleware`: allows hierarchical agent delegation with shared tools and optional custom models per sub-agent.
- `filesystem` state reducer merges file changes; integrates with external long-term storage via environment-configured filesystem API.

**Why This Matters:**
- Acts as blueprint for Project Manager orchestration once cataloging workflow is validated.
- Planning middleware maintains TODOs and plan state without custom code.
- HITL configs integrate through middleware to enforce approval gates.

---

## 🔄 Breaking Changes Summary

| **Change** | **Impact** | **Migration** |
|------------|------------|---------------|
| Python 3.10+ required | Must upgrade Python | Update CI/CD, dev environments |
| `create_react_agent` → `create_agent` | Import and runtime errors | Update function calls and imports |
| Return type: `BaseMessage` → `AIMessage` | Type checker errors | Update type hints |
| `.text()` → `.text` property | Deprecation warnings | Remove parentheses |
| No pre-bound models | Runtime errors | Pass model + tools separately |
| Legacy code → `langchain-legacy` | Import errors | Update imports or install `langchain-legacy` |
| `max_tokens` defaults changed | Different output lengths | Explicitly set `max_tokens` if needed |
| Deprecated methods removed | Runtime errors | Use modern alternatives |

---

## ✅ Features We'll Leverage in AutifyME


---

## 🧠 `deepagents` Library Integration

**Package:** `deepagents` (LangChain's advanced agent framework)  
**Our Usage:** Project Manager Agent implementation

The `deepagents` library extends LangChain's base agents with **advanced planning, self-correction, and sub-agent orchestration**. It's designed for complex, multi-step workflows.

### **Key Features We're Leveraging:**

#### **1. `create_deep_agent()` - Enhanced Agent Creation**

**Capabilities:**
- **Dynamic Planning:** Agent creates multi-step plans before execution
- **Self-Correction:** Validates outputs and retries on failures
- **Sub-Agent Spawning:** Can delegate to specialized sub-agents (our Departments!)
- **Tool Configuration:** Per-tool HITL approval requirements

**Example (From Our PM Design):**
```python
from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

def create_project_manager(company_profile: dict):
    agent = create_deep_agent(
        tools=get_all_tools(),  # Registry of all department tools
        instructions=PROJECT_MANAGER_PROMPT.format(
            company_name=company_profile["name"],
            brand_voice=company_profile["brand_voice"],
        ),
        model=ChatOpenAI(model="gpt-4.1-mini-2025-04-14", temperature=0.2),
        tool_configs={
            "save_product": True,      # Require approval
            "publish_website": True,    # Require approval
            "post_to_social": False,    # No approval needed
        }
    )
    return agent
```

#### **2. Planning & Reasoning**

Unlike basic ReAct agents, `deepagents` agents:
- **Plan First:** Create a step-by-step execution plan
- **Validate:** Check if plan is feasible before execution
- **Adapt:** Replan if steps fail or context changes

**Why This Matters:**
- **Complex Workflows:** WhatsApp cataloging requires 5+ steps (receive → analyze → extract → save → confirm)
- **Error Recovery:** If image analysis fails, PM replans to request clearer photo
- **Multi-Department:** PM plans which departments to invoke in parallel vs. sequential

#### **3. Sub-Agent Architecture**

`deepagents` natively supports **hierarchical agent structures** (perfect for our PM → Dept → Specialist pattern).

**How It Works:**
```python
# Project Manager spawns Department sub-agents
pm_agent = create_deep_agent(
    tools=[cataloging_dept, marketing_dept, operations_dept],
    ...
)

# Each Department is itself a deep_agent
cataloging_dept = create_deep_agent(
    tools=[image_analysis_tool, text_analysis_tool],
    ...
)
```

**Benefits:**
- **Separation of Concerns:** Each agent has clear scope
- **Parallel Execution:** PM can invoke multiple departments simultaneously
- **Error Isolation:** Department failure doesn't crash entire workflow

#### **4. Human-in-the-Loop (HITL)**

`deepagents` has built-in HITL via `tool_configs`:

```python
tool_configs={
    "save_product": True,        # Interrupt before calling
    "send_invoice": True,         # Interrupt before calling
    "get_company_profile": False, # No approval needed
}
```

**When agent hits `save_product`:**
1. Execution pauses
2. State saved to checkpointer
3. Webhook/callback notifies human
4. Human approves/rejects via API
5. Execution resumes

**Why This Matters:**
- **Quality Gates:** Human reviews product data before saving
- **Compliance:** Approval trails for auditing
- **Trust:** Customers see what's happening before publication

### **v1 Compatibility:**

`deepagents` is **fully compatible with LangChain v1** and uses:
- `create_agent` under the hood (benefits from v1 improvements)
- `.content_blocks` for structured outputs
- LangGraph checkpointing for state management
- LangSmith tracing for observability

**Our Strategy:**
1. Use `deepagents` for **Project Manager** (complex orchestration)
2. Use `create_agent` for **Departments** (simpler delegation)
3. Use `@tool` functions for **Specialists** (focused tasks)

---

## 🌐 LangGraph Platform (Complementary Service)

While not part of the OSS v1 release, **LangGraph Platform** is LangChain's managed cloud offering for deploying agents:

### **Key Features:**

1. **Managed Deployments**
   - Deploy LangGraph agents as REST APIs
   - Auto-scaling, load balancing, monitoring included
   - Zero DevOps for agent hosting

2. **Built-in State Management**
   - Managed checkpointing (no need to set up PostgresSaver)
   - Durable execution across restarts
   - Thread management for multi-user conversations

3. **Human-in-the-Loop Infrastructure**
   - Built-in approval UIs
   - Webhook notifications for interrupts
   - Resume/reject workflows via API

4. **LangSmith Integration**
   - Auto-tracing of all deployed agents
   - Production monitoring dashboards
   - A/B testing infrastructure

**Why We're Not Using It (Yet):**
- **Cost:** Paid service (not free-tier first) [[memory:9447191]]
- **Control:** We need single-tenant deployments (LangGraph Platform is multi-tenant SaaS)
- **Flexibility:** We want custom hosting on our infrastructure

**Future Consideration:** Once we scale to 100+ customers, LangGraph Platform could simplify operations.

---

## 🔍 LangSmith Capabilities (Already Integrated)

We've set up LangSmith for observability. Here's what it provides:

### **1. Automatic Tracing**
- Every LLM call, tool invocation, agent step traced
- Full input/output visibility
- Token usage, cost, latency per request

### **2. Evaluation & Testing**
- **Datasets:** Export traces → test datasets
- **Evaluators:** Run assertions on agent outputs (correctness, relevance, tone)
- **Regression Testing:** Detect when changes break existing flows

### **3. Prompt Management**
- **Hub:** Version and share prompts
- **Playground:** Test prompt variations without code changes
- **A/B Testing:** Compare prompt versions in production

### **4. Monitoring & Alerts**
- **Dashboards:** Track agent success rates, costs, errors
- **Alerts:** Get notified on high error rates, cost spikes
- **User Feedback:** Thumbs up/down on agent responses

### **5. Debugging**
- **Replay:** Re-run failed traces with different inputs
- **Comparison:** Diff two traces side-by-side
- **Search:** Find all traces with specific errors/patterns

**How We'll Use It:**
- **Week 1:** Validate Project Manager logic via trace inspection
- **Week 2:** Build evaluation datasets from WhatsApp cataloging traces
- **Month 2:** Set up automated regression tests on prompt changes
- **Ongoing:** Monitor production agent performance, costs, errors

---

## 📚 Key Resources

- **Official v1 Release Notes:** https://docs.langchain.com/oss/python/releases/langchain-v1
- **GitHub Releases:** https://github.com/langchain-ai/langchain/releases
- **Migration Guide:** https://docs.langchain.com/oss/python/releases/langchain-v1#migration-guide
- **LangGraph Docs:** https://langchain-ai.github.io/langgraph/
- **LangGraph Platform:** https://www.langchain.com/langgraph-platform
- **LangSmith Platform:** https://smith.langchain.com
- **LangSmith Docs:** https://docs.smith.langchain.com

---

## 🎯 Next Steps for Implementation

1. **Update `pyproject.toml`** - Ensure we're using latest alpha versions ✅ (Already done)
2. **Build Middleware System** - Create `core/middleware.py` for company context, tracing, rate limiting (P0)
3. **Create Base Agent** - Implement `create_agent` wrapper in `workflows/project_manager.py`
4. **Implement Checkpointing** - Set up `PostgresSaver` for state persistence
5. **Add HITL Patterns** - Use `interrupt_before` for approval workflows
6. **Leverage `.content_blocks`** - Extract structured data from Vision API responses
7. **Set Up Pydantic Outputs** - Define schemas for all agent → agent communication

**Estimated Timeline:** These features integrate into our Week 1-2 roadmap without delays.

---

**Last Updated:** Oct 1, 2025  
**Author:** AutifyME Team  
**Status:** Production-Ready for Alpha Features

