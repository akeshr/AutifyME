# LangChain v1 (Alpha) - New Features & Capabilities

**Version:** 1.0.0-alpha.9 (as of Oct 2025)  
**Status:** Alpha Release  
**Official Docs:** https://docs.langchain.com/oss/python/releases/langchain-v1

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

### 1. Package Restructuring & Modularization

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

---

### 2. `.content_blocks` Property - Multimodal & Reasoning Support

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

llm = ChatOpenAI(model="gpt-4o")
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

### 3. Prebuilt Agents in `langchain.agents`

**What Changed:**  
Agent creation APIs moved from `langgraph.prebuilts` to `langchain.agents` with **major enhancements**.

#### **`create_agent` - The Modern Agent Constructor**

**New Features:**
- **Structured Output Enforcement** - Pydantic models guarantee output schema
- **Advanced Error Handling** - `handle_errors` argument for custom retry/fallback logic
- **Tool Configuration** - Per-tool settings (timeouts, retries, approval requirements)
- **HITL Integration** - Built-in human approval checkpoints via `interrupt_before`/`interrupt_after`

**Migration:**
```python
# OLD (v0 - langgraph.prebuilts)
from langgraph.prebuilts import create_react_agent

agent = create_react_agent(model, tools)

# NEW (v1 - langchain.agents)
from langchain.agents import create_agent

agent = create_agent(
    model=model,
    tools=tools,
    handle_errors=True,  # Simplified error handling flag
    interrupt_before=["save_product"],  # NEW: HITL approval
    state_modifier="You are an expert cataloging agent",  # NEW: Dynamic prompts
)
```

**Breaking Changes:**
- **No Pre-Bound Models** - Can't pass `model.bind_tools(tools)` anymore; pass model and tools separately
- **Return Type** - Now returns `AIMessage` instead of `BaseMessage` (better type hints)
- **Import Path** - Must update imports from `langgraph.prebuilts` → `langchain.agents`

**Why This Matters for AutifyME:**
- **Project Manager Agent** - Use `create_agent` as base for our PM implementation
- **HITL Workflows** - `interrupt_before` perfect for "approve before publishing" flows
- **Error Resilience** - `handle_errors=True` enables robust, configurable error handling.
- **Structured Outputs** - Guarantee `Product` schema compliance via Pydantic

---

### 4. Enhanced Error Handling & Resilience

**New Capabilities:**

#### **A. Structured Output Error Control**

```python
from langchain.agents import create_agent

# Strategy 1: Raise exceptions immediately (fail-fast)
agent = create_agent(
    model=llm,
    tools=tools,
    handle_errors=False # Default behavior
)

# Strategy 2: Retry with LLM feedback (self-correction)
# The `handle_errors` parameter can be configured with more complex strategies
# for retries, but the simple boolean is the most common use case.
agent = create_agent(
    model=llm,
    tools=tools,
    handle_errors=True 
)

# Strategy 3: Continue with error message (best-effort)
# This would require a custom error handler function passed to `handle_errors`
agent = create_agent(
    model=llm,
    tools=tools,
    handle_errors=True # Simplified for documentation
)
```

#### **B. Tool Exception Handling**

**Before (v0):** Agents would retry failed tools indefinitely, risking infinite loops.

**After (v1):** Agents raise `ToolException` by default, preventing loops.

```python
from langchain.tools import tool, ToolException

@tool
def risky_api_call(query: str) -> str:
    """Calls external API that might fail."""
    try:
        result = call_external_api(query)
        return result
    except APIError as e:
        # V1: Raise ToolException to halt gracefully
        raise ToolException(
            f"API failed: {e}",
            tool_name="risky_api_call",
            original_error=e
        )
```

**Why This Matters for AutifyME:**
- **WhatsApp Integration** - Prevent retry storms on network failures
- **Image Analysis** - Gracefully handle Vision API quota errors
- **Data Integrity** - Fail fast on critical errors (e.g., DB write failures)

---

### 5. State & Context Management ⭐️ NEW

LangChain v1 introduces powerful, native features for managing conversation history and state, which are critical for our context engineering strategy.

#### **A. Conversation Summarization Middleware**

**What it is:**
A middleware that automatically manages and compacts conversation history to prevent exceeding the context window. It replaces our previous plan of building a custom compaction node in LangGraph.

**Key Capabilities:**
- **Automatic Compaction:** Monitors token count and summarizes the oldest messages when a threshold is reached.
- **Configurable:** Allows setting token limits and providing custom summarization prompts.
- **Preserves Context:** Replaces old messages with a concise `SystemMessage` containing the summary, maintaining context for long-running conversations.

**Example:**
```python
from langchain.memory import ConversationBufferMemory
from langchain.chains.conversation.base import SummarizationMiddleware
from langchain_openai import ChatOpenAI

# The LLM to use for summarizing
summarizer_llm = ChatOpenAI(model="gpt-4o", temperature=0)

# The middleware to attach to the memory
summarization_middleware = SummarizationMiddleware(
    llm=summarizer_llm,
    memory_key="chat_history",
    prompt="Summarize the key decisions and unresolved questions from this conversation.",
    max_tokens=8000 # Trigger summarization when history exceeds this many tokens
)

# The memory object used by the agent
memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)
memory.add_middleware(summarization_middleware)

# This memory object can now be used in an agent or chain, and it will
# automatically handle compaction.
```

**Why This Matters for AutifyME:**
- **Long-Horizon Tasks:** Essential for any future complex workflows that might exceed the context window.
- **Reduced Development:** We can leverage a native, battle-tested feature instead of building our own compaction logic. [[memory:9501042]]
- **Cost & Performance:** Prevents sending excessively large histories to the LLM, saving costs and reducing latency.

---

### 6. Middleware System - Cross-Cutting Concerns ⭐️ NEW in v1.0.0a8

**What it is:**  
A **decorator-based middleware system** for injecting custom logic into agent/tool execution pipelines without modifying core code.

**Key Capabilities:**
- **State Injection** - Dynamically inject context (user_id, company_profile, request_id) into tools
- **Cross-Cutting Concerns** - Logging, authentication, rate limiting, monitoring
- **Dynamic Tool Behavior** - Modify tool inputs/outputs at runtime
- **Composable Decorators** - Stack multiple middleware layers

**Example - Authentication & Logging Middleware:**
```python
from langchain_core.tools import tool
from functools import wraps

def company_context_middleware(func):
    """Auto-inject company profile into every tool call"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get company context from request
        config = kwargs.get("config", {})
        company_id = config.get("configurable", {}).get("company_id")
        
        # Inject into tool
        kwargs["company_profile"] = get_company_profile(company_id)
        
        # Log execution
        logger.info(f"Tool {func.__name__} called for company {company_id}")
        
        # Execute with enriched context
        result = func(*args, **kwargs)
        
        # Trace completion
        logger.info(f"Tool {func.__name__} completed successfully")
        return result
    return wrapper

def rate_limit_middleware(func):
    """Apply rate limiting to expensive tools"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        config = kwargs.get("config", {})
        user_id = config.get("configurable", {}).get("user_id")
        
        if not check_rate_limit(user_id, func.__name__):
            raise RateLimitError(f"Rate limit exceeded for {func.__name__}")
        
        return func(*args, **kwargs)
    return wrapper

# Apply middleware via decorators
@company_context_middleware
@rate_limit_middleware
@tool
def analyze_product_image(image_url: str, company_profile: dict = None) -> dict:
    """Analyze product image with company context"""
    # company_profile automatically injected by middleware!
    return vision_llm.invoke([
        {"type": "text", "text": f"Analyze for {company_profile['name']}"},
        {"type": "image_url", "image_url": image_url}
    ])
```

**Advanced: Tool Registration Middleware**
```python
from langchain.agents import create_agent

def langsmith_tracing_middleware(tools, workflow_id: str, department: str):
    """Enrich all tool traces with workflow context"""
    wrapped_tools = []
    
    for tool in tools:
        original_func = tool.func
        
        @wraps(original_func)
        def traced_wrapper(*args, **kwargs):
            # Inject LangSmith metadata
            kwargs.setdefault("config", {})
            kwargs["config"]["metadata"] = {
                "workflow_id": workflow_id,
                "department": department,
                "specialist": tool.name,
                "timestamp": datetime.now().isoformat()
            }
            return original_func(*args, **kwargs)
        
        tool.func = traced_wrapper
        wrapped_tools.append(tool)
    
    return wrapped_tools

# Apply to all department tools
cataloging_tools = get_cataloging_tools()
traced_tools = langsmith_tracing_middleware(
    cataloging_tools,
    workflow_id="whatsapp_catalog_123",
    department="cataloging"
)

agent = create_agent(model, traced_tools)
```

**Why This Matters for AutifyME:**

1. **Company Context Injection** - Every tool automatically gets company profile without manual passing
2. **Distributed Tracing** - Auto-inject correlation IDs for LangSmith trace grouping
3. **Security & Multi-Tenancy** - Centralized auth/isolation checks (future-proofing)
4. **Cost Control** - Rate limiting for expensive Vision API/LLM calls
5. **Audit Logging** - Track every DB write/publish action in one place
6. **Error Enrichment** - Add workflow context to all exceptions automatically

**Our Use Cases:**
- ✅ Auto-inject `company_profile` into all 20+ cataloging tools (DRY principle)
- ✅ LangSmith trace tagging (workflow_id, department, specialist) for filtering
- ✅ Rate limiting Image Analysis Specialist (max 100 images/hour)
- ✅ Audit middleware for `save_product`, `publish_website` tools
- ✅ Error context middleware (adds request_id, user_id to all exceptions)

**Implementation Priority:** P0 - Build this in `core/middleware.py` during foundation phase

---

### 7. LangGraph Runtime Integration

**What it means:**  
All `langchain.agents` are now **backed by LangGraph's stateful runtime**, giving you:

- **Automatic Checkpointing** - State persists across interruptions
- **Human-in-the-Loop** - Built-in approval flows via `interrupt_before`/`interrupt_after`
- **Streaming Support** - Real-time updates via `astream_events`
- **Time-Travel Debugging** - Replay/fork execution from any checkpoint

**Example:**
```python
from langchain.agents import create_agent
from langgraph.checkpoint.postgres import PostgresSaver

# Create agent with checkpointing
checkpointer = PostgresSaver.from_conn_string(settings.DATABASE_URL)
agent = create_agent(model, tools, checkpointer=checkpointer)

# HITL: Interrupt before dangerous actions
agent = create_agent(
    model,
    tools,
    checkpointer=checkpointer,
    interrupt_before=["publish_to_website", "send_invoice"]
)

# User approves via:
agent.update_state(thread_id, {"approved": True})
```

**Why This Matters for AutifyME:**
- **WhatsApp Conversations** - Persist state across multi-turn chats
- **Approval Workflows** - PM can pause for human review before publishing
- **Crash Recovery** - Resume cataloging workflow from last checkpoint
- **Debugging** - Replay failed workflows in LangSmith with full state

---

### 8. Improved Type Safety & Developer Experience

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

### 9. Anthropic & OpenAI Enhancements

#### **A. Anthropic Prompt Caching**

**New:** Automatic prompt caching for Claude models (reduces costs & latency).

```python
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(
    model="claude-3-5-sonnet-20240620",
    enable_prompt_caching=True  # NEW: Cache system prompts
)

# First call: Full prompt processing
response1 = llm.invoke([system_message, user_message])

# Subsequent calls: Cached system prompt (90% cost reduction)
response2 = llm.invoke([system_message, user_message_2])
```

**Why This Matters for AutifyME:**
- **Cost Optimization** - Our PM prompt is ~2K tokens; caching saves 90% on repeated calls
- **Latency Reduction** - Faster responses for multi-turn WhatsApp chats

#### **B. OpenAI Responses API**

**Breaking Change:**  
`langchain-openai` now defaults to storing responses in `message.content` instead of custom fields.

**Migration:**
```python
# To restore v0 behavior (if needed):
llm = ChatOpenAI(
    model="gpt-4o",
    output_version="v0"  # or set LC_OUTPUT_VERSION=v0 env var
)
```

---

### 10. LangSmith Deep Integration

While not specific to v1, **LangChain v1 + LangSmith** work seamlessly together:

#### **A. Automatic Tracing**
- Every agent call, tool invocation, and LLM request auto-traced
- No manual instrumentation needed

#### **B. Evaluation Datasets**
- Export LangSmith traces → test datasets
- Run regression tests on agent changes

#### **C. Prompt Versioning**
- Experiment with prompts in LangSmith Hub
- Pull specific versions in code via `hub.pull("username/prompt-name:v3")`

**Example:**
```python
from langchain import hub

# Pull versioned prompt from LangSmith
project_manager_prompt = hub.pull("autifyme/project-manager:v2")

agent = create_agent(
    model=llm,
    tools=tools,
    prompt=project_manager_prompt # Prompts are now passed directly
)
```

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

### **Immediate Use (Week 1-2)**

1. **`create_agent`** - Base for Project Manager Agent
   - Use `interrupt_before` for HITL approval on product publishing
   - Use `handle_errors=True` for self-correction and resilience.
   - Use the `prompt` parameter for dynamic prompt injection (company profile)

2. **PostgresSaver Checkpointing** - Multi-turn WhatsApp conversations
   - Persist conversation state across messages
   - Resume interrupted workflows

3. **Structured Outputs** - Pydantic validation for all agent responses
   - Guarantee `Product` schema compliance
   - Type-safe department → PM communication

4. **`.content_blocks`** - Image analysis results
   - Extract Vision API confidence scores
   - Pass structured image metadata between specialists

5. **LangSmith Auto-Tracing** - Observability from day 1
   - Debug agent decisions in real-time
   - Build evaluation datasets from production traces

### **Phase 2 (Month 2+)**

6. **Anthropic Prompt Caching** - Cost optimization
   - Cache long system prompts for PM, Dept Heads
   - Reduce per-request costs by 90%

7. **SummarizationMiddleware** - Long-running task support
   - Automatically compact conversation history for complex, multi-day workflows.
   - Prevents context window overruns and reduces token costs.

8. **LangSmith Prompt Hub** - Collaborative prompt engineering
   - Version and test prompts independently of code
   - A/B test different agent instructions

9. **Multi-Provider Support** - Redundancy via `.content_blocks`
   - Fallback: OpenAI → Anthropic using same API
   - Avoid vendor lock-in

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
        model=ChatOpenAI(model="gpt-4o", temperature=0.2),
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

