# Lessons Learned: First Agent Implementation (October 2025)

## Overview
This document captures critical learnings from our first end-to-end agent implementation and debugging session. These insights have been codified into Cursor Rules to prevent future issues.

**Date:** October 1, 2025  
**Milestone:** Successfully implemented and tested the Cataloging Department agent  
**Duration:** ~4 hours of debugging  
**Outcome:** ✅ Production-ready hierarchical agent system

---

## 🎯 What We Built

### Successful Implementation:
1. **Cataloging Department Agent** (ReAct-style orchestrator)
2. **Image Analysis Specialist** (Vision LLM with structured output)
3. **Storage Tools** (Supabase integration with Pydantic models)
4. **Middleware System** (LangSmith tracing + context injection)
5. **End-to-End Test** (WhatsApp-style product cataloging workflow)

### Technology Stack Validated:
- ✅ LangChain v1 (`create_agent` API)
- ✅ LangGraph runtime (automatic checkpointing)
- ✅ LangSmith tracing (full observability)
- ✅ Supabase (PostgreSQL with Python SDK)
- ✅ GPT-4 Vision (multimodal image analysis)
- ✅ Pydantic v2 (type-safe data models)

---

## 🐛 Critical Issues Encountered & Resolved

### 1. LangChain v1 Migration (`create_agent` vs `create_react_agent`)

**Problem:**
```python
# Old (v0) - DEPRECATED
from langgraph.prebuilts import create_react_agent
from langchain.agents import AgentExecutor  # ← Doesn't exist in v1

agent = create_react_agent(model, tools)
agent = AgentExecutor(agent=agent, tools=tools)  # ← Old pattern
```

**Solution:**
```python
# New (v1) - CORRECT
from langchain.agents import create_agent

agent = create_agent(llm, tools, prompt=prompt)  # ← Single function, prompt as kwarg
```

**Root Cause:** LangChain v1 completely revamped the agent creation API. The old `AgentExecutor` wrapper is gone.

**Lesson:** Always verify the exact import paths and API signatures when using rapidly-evolving frameworks like LangChain.

**Codified in:** Rule #08 (LangChain Agent Creation Pattern)

---

### 2. Async/Sync Mismatch Between SDKs

**Problem:**
```python
# Supabase SDK is synchronous, but we marked methods as async
async def get_company_profile(self) -> CompanyProfile:
    return await self._client.table("companies").select("*").execute()  # ← TypeError!
```

**Error:** `TypeError: object SingleAPIResponse can't be used in 'await' expression`

**Solution:**
```python
# Match the SDK's actual behavior
def get_company_profile(self) -> CompanyProfile:  # ← Synchronous
    return self._client.table("companies").select("*").execute()  # ← No await
```

**Root Cause:** The Supabase Python SDK uses `requests` (synchronous HTTP client), not `httpx` (async). We can't force async on a sync library.

**Lesson:** 
- **Don't assume** based on general Python knowledge
- **Always check** if the SDK provides async methods before using `async def`
- **Async is NOT always better** - it depends on the underlying library

**Codified in:** Rule #07 (Async/Sync Best Practices)

---

### 3. Middleware Must Handle Both Sync and Async Tools

**Problem:**
```python
# Middleware was synchronous
def langsmith_tracing_middleware(workflow_name: str):
    def decorator(func):
        def wrapper(*args, **kwargs):  # ← Sync wrapper
            return func(*args, **kwargs)  # ← Can't await async tools!
        return wrapper
    return decorator
```

**Error:** `RuntimeWarning: coroutine 'analyze_product_image' was never awaited`

**Solution:**
```python
# Middleware detects and adapts to tool signature
def langsmith_tracing_middleware(workflow_name: str):
    def decorator(func):
        if asyncio.iscoroutinefunction(func):  # ← Detect async
            async def async_wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return sync_wrapper
    return decorator
```

**Root Cause:** Our middleware was hardcoded to one style. Since tools can be either sync (Supabase) or async (OpenAI), middleware must adapt.

**Lesson:** Middleware (decorators) that wrap arbitrary functions MUST inspect the function signature and match it.

**Codified in:** Rule #05 (Middleware for Tools) - Updated

---

### 4. LangChain Passes `config` to All Tools

**Problem:**
```python
@tool
def get_company_profile() -> CompanyProfile:  # ← No config parameter
    return storage.get_company_profile()
```

**Error:** `TypeError: get_company_profile() got an unexpected keyword argument 'config'`

**Solution:**
```python
# Middleware extracts config before calling the tool
def middleware(func):
    def wrapper(*args, **kwargs):
        config = kwargs.pop("config", {})  # ← Remove config from kwargs
        # Use config for middleware logic (tracing, context injection)
        return func(*args, **kwargs)  # ← Tool doesn't receive config
    return wrapper
```

**Root Cause:** LangChain's agent runtime automatically passes a `config` dictionary to all tool invocations for tracing/state management. Tools don't need it, so middleware must consume it.

**Lesson:** When building middleware for LangChain tools, **always** `pop("config")` from `kwargs` before calling the wrapped function.

**Codified in:** Rule #05 (Middleware for Tools)

---

### 5. Input Schema Changed from `input` to `messages`

**Problem:**
```python
# Old (v0) input format
result = await agent.ainvoke({"input": task}, config=run_config)

# Prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", "..."),
    ("human", "{input}"),  # ← Old placeholder
])
```

**Error:** `KeyError: Input to ChatPromptTemplate is missing variables {'input'}. Expected: ['input'] Received: ['messages', 'remaining_steps']`

**Solution:**
```python
# New (v1) input format
result = await agent.ainvoke(
    {"messages": [("human", task)]},  # ← messages key with list of tuples
    config=run_config
)

# Prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", "..."),
    ("human", "{messages}"),  # ← New placeholder
    ("placeholder", "{agent_scratchpad}"),  # ← Required for tool calls
])
```

**Root Cause:** LangChain v1 agents are backed by LangGraph, which uses a different state schema optimized for multi-turn conversations.

**Lesson:** When migrating to v1, update **both** the input format and the prompt template placeholders.

**Codified in:** Rule #08 (LangChain Agent Creation Pattern)

---

### 6. Multimodal Prompts Cannot Use Simple Templates

**Problem:**
```python
# Doesn't work - ChatPromptTemplate can't interpolate nested structures
prompt = ChatPromptTemplate.from_messages([
    ("system", "Analyze this image"),
    ("human", [
        {"type": "image_url", "image_url": "{image_url}"},  # ← Literal string sent to API
        {"type": "text", "text": "Describe it"}
    ])
])
```

**Error:** `BadRequestError: Failed to download image from {image_url}. Image URL is invalid.`

**Solution:**
```python
# Use RunnableLambda to construct messages dynamically
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import SystemMessage, HumanMessage

def format_messages(inputs: dict) -> list:
    return [
        SystemMessage(content="Analyze this image"),
        HumanMessage(content=[
            {"type": "image_url", "image_url": {"url": inputs["image_url"]}},  # ← Actual value
            {"type": "text", "text": "Describe it"}
        ])
    ]

chain = RunnableLambda(format_messages) | llm
```

**Root Cause:** `ChatPromptTemplate` is designed for simple string interpolation. It cannot interpolate variables inside complex nested data structures like multimodal content arrays.

**Lesson:** For vision/audio/multimodal tasks, use `RunnableLambda` to dynamically construct message objects.

**Codified in:** Rule #09 (Multimodal Prompt Patterns)

---

### 7. Prompt Management: File-Based is Production-Grade

**Decision Made:** Use file-based prompts (`.prompt` files) loaded via `load_prompt()` as our primary pattern.

**Why This is Correct:**
- ✅ **Version-controlled** in Git
- ✅ **Code-reviewable** in PRs
- ✅ **Offline-first** (no external dependencies)
- ✅ **LangSmith compatible** (can push to Hub later for A/B testing)

**Pattern:**
```python
from autifyme_agents.core.prompt_loader import load_prompt

SYSTEM_PROMPT = load_prompt("specialists/my_specialist.prompt")

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{input}"),
])
```

**Lesson:** Official LangChain guidance supports multiple patterns. We chose the one that aligns with our "Architecture-First" philosophy and production stability requirements.

**Codified in:** Rule #11 (Prompt Management)

---

## 🏆 Success Metrics

### What Worked Perfectly:
1. **Hexagonal Architecture** - Swapping Supabase for another DB would take <1 hour
2. **Pydantic Models** - Zero runtime type errors after fixing imports
3. **LangSmith Tracing** - Full observability from agent → tool → specialist
4. **Middleware Pattern** - Clean separation of concerns (Rule #05 validated)
5. **Prompt Files** - Easy to review, version, and modify

### Agent Execution Success:
- ✅ Agent fetched company profile from Supabase
- ✅ Agent analyzed product image using GPT-4 Vision
- ✅ Agent created comprehensive product entry
- ✅ Agent saved product to database with UUID
- ✅ Full trace available in LangSmith

---

## 📚 Documentation Created/Updated

### New Cursor Rules (5 new rules):
1. **Rule #07:** Async/Sync Best Practices
2. **Rule #08:** LangChain Agent Creation Pattern
3. **Rule #09:** Multimodal Prompt Patterns
4. **Rule #10:** Systematic Debugging Methodology
5. **Rule #11:** Prompt Management Best Practices

### Updated Rules:
- **Rule #05:** Middleware for Tools (added async/sync handling pattern)

### Architecture Documents:
- ✅ `LANGCHAIN_V1_FEATURES.md` - Comprehensive v1 feature guide
- ✅ `AGENTS_DESIGN.md` - Hierarchical agent architecture
- ✅ `PROJECT_STRUCTURE.md` - Hexagonal folder structure
- ✅ This document - Lessons learned

---

## 🎓 Key Takeaways for Future Development

### 1. Always Verify SDK Behavior First
**Don't assume** - **Always check**:
- Is the SDK async or sync?
- What import paths exist in the installed version?
- Has the API changed in the latest release?

**Action:** Use web search for official docs before writing code.

### 2. Read Full Error Tracebacks
- Don't jump to conclusions from error messages alone
- Trace the call stack from bottom to top
- Identify the exact failing line and error type

### 3. Fix Root Causes, Not Symptoms
**Bad:** Adding `config=None` parameters everywhere  
**Good:** Making middleware `pop("config")` before calling tools

### 4. One Change at a Time
- Change one thing
- Test immediately
- If it breaks, you know what caused it

### 5. Document Tricky Decisions
After resolving a non-obvious bug:
- Update relevant rules
- Add inline comments explaining "why"
- Update architecture docs if it revealed a design flaw

---

## 🚀 What's Next

With the core infrastructure now stable, we can proceed with:

1. **P0 Tasks:**
   - Database schema version control (0.5 days)
   - Error handling with tenacity (2-3 days)
   - Testing framework setup (2-3 days)

2. **P1 Tasks:**
   - Memory management for multi-turn conversations (1 day)
   - Structured logging with correlation IDs (1 day)

3. **Future Workflows:**
   - Marketing Department agents
   - Customer Support agents
   - Analytics & Reporting agents

---

## 💡 Final Thoughts

This debugging session was **not wasted time**. It was an investment in:
- ✅ **Robust infrastructure** - Won't break again
- ✅ **Team knowledge** - Codified as rules
- ✅ **Production readiness** - No shortcuts taken
- ✅ **Confidence** - We understand the stack deeply

**The core principle validated:** "Architecture-First" development takes longer upfront but pays massive dividends in stability, maintainability, and velocity for all future features.

---

**Status:** Infrastructure Phase Complete ✅  
**Next Phase:** Build remaining P0 tasks and deploy first workflow to production

