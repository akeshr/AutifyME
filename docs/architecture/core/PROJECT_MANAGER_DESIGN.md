# Project Manager Agent Design with `deepagents`

> **Roadmap Document** – Timeless architecture reference. Implementation status is tracked in `../roadmap/IMPLEMENTATION_ROADMAP.md`. Production integration begins once WhatsApp PM readiness checklist is satisfied (currently pending automation and stability work).

**Created:** October 1, 2025
**Purpose:** Define how we use `deepagents` to implement our Project Manager Agent
**Status:** ✅ Implemented - 2-Level Architecture (PM → Specialist → Tools)

> **Status:** Current implementation uses 2-level hierarchy.
> PM delegates directly to specialists (no department layer).
> Cataloging specialist is production-ready.
> For implementation details, see [ACTUAL_IMPLEMENTATION_ARCHITECTURE.md](./ACTUAL_IMPLEMENTATION_ARCHITECTURE.md).

---

## Overview

The Project Manager Agent is the top-level orchestrator in our 2-level agentic system. We use the `deepagents` library to implement it, leveraging sub-agent delegation and HITL capabilities.

**Key Insight:** `deepagents` sub-agents = Our Specialists (with tools attached)

---

## Architecture Mapping

### 2-Level Hierarchy → `deepagents` Components

```
Project Manager Agent (create_deep_agent)
    └── Sub-agents: Specialists (create_agent with tools)
        ├── Cataloging Specialist - ✅ PRODUCTION
        │   └── Tools: [image_analysis_tool, save_product]
        ├── Marketing Specialist - 🔮 FUTURE
        │   └── Tools: [copywriter, seo_analyzer, social_poster]
        └── Operations Specialist - 🔮 FUTURE
            └── Tools: [billing, shipping, inventory]
```

**Implementation:**
- **Project Manager** = `create_deep_agent()` with minimal tools, delegates to specialists
- **Specialists** = `create_agent()` with domain-specific instructions and tools
- **Tools** = Utility functions attached to specialists (via tools parameter)
- **HITL** = Configured via `tool_configs` on specialist tools

---

## Implementation Status

**Current State:** ✅ 2-Level architecture implemented and production-ready

1. ✅ Cataloging specialist validated with real workflows (performance + usability confirmed)
2. ✅ HITL approval loop implemented and battle-tested via tool_configs
3. ✅ Structured outputs (`CatalogingResult` → PM) finalized via Pydantic models
4. ✅ Dependency injection for storage implemented via constructor parameters
5. ✅ Testing framework upgraded to autonomous testing with assertions
6. ✅ Using `deepagents` for 2-level hierarchy (PM → Specialist → Tools)

---

## Implementation Strategy (Post-MVP)

### Current Implementation: 2-Level Project Manager

PM delegates directly to specialists (no department layer).

```python
# agents/src/autifyme_agents/workflows/project_manager.py

from deepagents import create_deep_agent
from langchain.chat_models import BaseChatModel

from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.schemas.models import CompanyProfile

def create_project_manager(
    company_profile: CompanyProfile,
    *,
    model: BaseChatModel | None = None,
    checkpointer: Any,
    storage: StorageInterface,
    channel: MessagingChannel | None = None,
) -> Any:
    """Create Project Manager that delegates to specialists.

    Args:
        company_profile: Company context for brand voice and target audience
        model: Optional LLM override
        checkpointer: LangGraph checkpointer for state persistence (required)
        storage: Storage adapter for database operations (required)
        channel: Messaging channel for platform-specific media download tools

    Returns:
        Compiled DeepAgent with specialist delegation
    """

    llm = get_llm(model="gpt-4.1-mini", temperature=0.2)
    instructions = load_prompt("project_manager.prompt").format(
        company_name=company_profile.name,
        brand_voice=company_profile.brand_voice,
        target_audience=company_profile.target_audience,
    )

    # Platform tools (media download based on channel)
    pm_tools: list[Any] = []
    if channel is not None:
        from autifyme_agents.tools.platform_tools import create_platform_media_tools
        pm_tools.extend(create_platform_media_tools(channel))

    # Specialists as subagents
    from autifyme_agents.specialists.cataloging_specialist import create_cataloging_specialist

    subagents: list[Any] = [
        create_cataloging_specialist(storage),
        # Future specialists...
    ]

    project_manager = create_deep_agent(
        tools=pm_tools,  # PM has minimal tools (media download)
        system_prompt=instructions,
        model=llm,
        subagents=subagents,  # Specialists with their own tools
        checkpointer=checkpointer,
        store=get_store(),
        use_longterm_memory=True,
        context_schema=CompanyContext,
    )

    return project_manager.with_config({
        "metadata": {"workflow": "cataloging"},
        "initial_state": initial_state,
    })
```

**Key Features:**
- Generic orchestrator (not hardcoded to workflows)
- Specialists as SubAgents (tools attached at specialist level)
- HITL configured via tool_configs on specialist tools
- State persistence with PostgreSQL checkpointer

---

### Specialist Implementation Pattern

Specialists are created with `create_agent()` and attached to PM as SubAgents.

```python
# agents/src/autifyme_agents/specialists/cataloging_specialist.py

from deepagents import create_agent
from autifyme_agents.core.llm_factory import get_llm
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.tools.image_analysis_tool import image_analysis_tool
from autifyme_agents.tools.storage_tools import create_save_product_tool
from autifyme_agents.schemas.models import Product

def create_cataloging_specialist(storage: StorageInterface) -> Any:
    """Create cataloging specialist with tools.

    Args:
        storage: Storage adapter for database operations

    Returns:
        Specialist agent with image_analysis_tool and save_product tool
    """

    specialist = create_agent(
        model=get_llm(model="gpt-4.1-mini", temperature=0),
        system_prompt=load_prompt("specialists/cataloging_specialist.prompt"),
        tools=[
            image_analysis_tool,  # Vision API wrapper
            create_save_product_tool(storage),  # Database persistence
        ],
        tool_configs={
            "save_product": ToolConfig(
                allow_accept=True,
                allow_edit=True,
                allow_respond=True,
                description="Review product before saving"
            )
        },
        response_format=Product,  # Structured output
    )

    return specialist
```

**How Specialist Delegation Works:**

1. **User:** "Catalog this product from images"
2. **Project Manager:** Classifies as cataloging task
3. **Project Manager:** Delegates to `cataloging_specialist` subagent with complete context
4. **Specialist:** Calls `image_analysis_tool(image_path)` → gets ImageAnalysisResult
5. **Specialist:** Synthesizes Product model from user text + image insights
6. **Specialist:** Calls `save_product(...)` → triggers HITL interrupt
7. **Runner:** Handles approval workflow
8. **Tool:** Executes after approval → returns CatalogingResult
9. **Specialist:** Returns result to PM
10. **Project Manager:** Relays success to user

**Benefit:** Direct delegation, tools scoped to specialist, no unnecessary layers.

---

## Detailed Implementation

### 1. Project Manager Prompt

```python
# agents/src/autifyme_agents/prompts/templates.py

from langchain.prompts import ChatPromptTemplate

PROJECT_MANAGER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are the Project Manager for {company_name}.

Your role is to understand user requests, create multi-step plans, and orchestrate 
the execution by delegating to the appropriate departments.

Company Context:
- Brand Voice: {brand_voice}
- Target Audience: {target_audience}

Available Departments:
- Cataloging: Product ingestion and catalog management
- Marketing: Campaigns, content creation, social media
- Operations: Billing, shipping, inventory
- Website: Content updates, redesigns

Your Process:
1. Analyze the user's request to understand their goal
2. Use the planning tool to break it into steps
3. Identify which department(s) should handle each step
4. Create a sub-agent for each department with specific instructions
5. Orchestrate the execution, managing dependencies
6. Return the final result to the user

Key Principles:
- Always use the planning tool for complex requests
- Delegate to departments (sub-agents), don't do work yourself
- For multi-department tasks, coordinate the sequence
- Request human approval for critical operations
- Provide clear status updates to the user
"""),
    ("human", "{input}"),
])
```

---

### 2. Tool Organization

```python
# agents/src/autifyme_agents/tools/__init__.py

from .cataloging_tools import (
    image_analysis_specialist,
    text_analysis_specialist,
)
from .storage_tools import (
    save_product,
    get_company_profile,
)

__all__ = [
    "image_analysis_specialist",
    "text_analysis_specialist", 
    "save_product",
    "get_company_profile",
]
```

```python
# agents/src/autifyme_agents/tools/cataloging_tools.py

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

class ImageAnalysisResult(BaseModel):
    """Structured output from image analysis."""
    category: str = Field(description="Product category")
    color: str = Field(description="Primary color")
    pattern: str | None = Field(description="Pattern type")
    description: str = Field(description="Description in brand voice")
    confidence: float = Field(ge=0.0, le=1.0)

@tool
def image_analysis_specialist(image_url: str, company_context: dict) -> ImageAnalysisResult:
    """
    Analyzes a product image and extracts structured information.
    
    Returns:
        ImageAnalysisResult: Type-safe Pydantic model (v1 structured output)
    """
    llm = ChatOpenAI(model="gpt-4.1-mini-2025-04-14")
    
    # v1: .with_structured_output() guarantees schema compliance
    structured_llm = llm.with_structured_output(ImageAnalysisResult)
    
    prompt = f"""
    Analyze this product image for {company_context['company_name']}.
    Brand Voice: {company_context['brand_voice']}
    Image: {image_url}
    """
    
    # Returns ImageAnalysisResult object, not dict!
    return structured_llm.invoke([
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": image_url}}
    ])

@tool
def text_analysis_specialist(text: str, company_context: dict) -> dict:
    """
    Analyzes text message and extracts product information.
    
    Use this tool when you have text description of a product.
    
    Args:
        text: Text message from user
        company_context: Company context
    
    Returns:
        Dictionary with: price, sizes, colors, description, etc.
    """
    # Implementation using LLM with structured output
    pass
```

---

### 3. HITL Integration

```python
# Usage in entrypoint
from deepagents import Command

# Initial request
config = {"configurable": {"thread_id": workflow_id}}
for event in agent.stream(
    {"messages": [{"role": "user", "content": user_message}]},
    config=config
):
    print(event)
    
# When tool requires approval (e.g., save_product)
# The stream will yield an interrupt

# Streamlit UI shows draft product for approval
# User clicks: Approve / Edit / Reject

# Approve as-is
if user_action == "approve":
    for event in agent.stream(
        Command(resume=[{"type": "accept"}]),
        config=config
    ):
        print(event)

# Approve with edits
elif user_action == "edit":
    for event in agent.stream(
        Command(resume=[{
            "type": "edit",
            "args": {
                "action": "save_product",
                "args": edited_product_dict
            }
        }]),
        config=config
    ):
        print(event)

# Reject with feedback
elif user_action == "reject":
    for event in agent.stream(
        Command(resume=[{
            "type": "response",
            "args": "Please change the color to blue and reduce price by 10%"
        }]),
        config=config
    ):
        print(event)
```

**Three Approval Modes:**
1. **Accept:** Execute tool as-is
2. **Edit:** Execute tool with modified arguments
3. **Response:** Skip tool, send feedback to agent

---

### 4. State Management

```python
# agents/src/autifyme_agents/schemas/state.py

from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class ProjectManagerState(TypedDict):
    """State for Project Manager workflow"""
    
    # Messages (conversation history)
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # Company context (loaded at startup)
    company_profile: dict
    
    # Current workflow metadata
    workflow_id: str
    workflow_type: str  # "cataloging", "marketing", etc.
    
    # Virtual file system (from deepagents)
    files: dict[str, str]
    
    # Current plan (from planning tool)
    plan: list[dict]
    current_step: int
    
    # Results from departments
    department_results: dict[str, any]
```

---

### 5. Entrypoint (WhatsApp Webhook)

```python
# agents/src/autifyme_agents/entrypoints/whatsapp_webhook.py

from fastapi import FastAPI, Request
from ..workflows.project_manager import create_project_manager
from ..integrations.storage.supabase_client import SupabaseStorageClient

app = FastAPI()

storage = SupabaseStorageClient()

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Receives WhatsApp messages and routes to Project Manager.
    """
    data = await request.json()
    
    # Extract message
    message = data["entry"][0]["changes"][0]["value"]["messages"][0]
    phone_number = message["from"]
    
    # Load company profile (single-tenant)
    company_profile = storage.get_company_profile()
    
    # Create/get Project Manager for this company
    agent = create_project_manager(
        company_profile,
        storage=storage,
    )
    
    # Process message
    config = {
        "configurable": {
            "thread_id": f"whatsapp_{phone_number}",
            "checkpoint_ns": "cataloging"
        }
    }
    
    # Handle different message types
    if message.get("type") == "image":
        image_url = download_whatsapp_image(message["image"]["id"])
        user_message = f"Catalog this product: [IMAGE: {image_url}]"
    elif message.get("type") == "text":
        user_message = message["text"]["body"]
    
    # Stream to agent
    response_chunks = []
    for event in agent.stream(
        {"messages": [{"role": "user", "content": user_message}]},
        config=config,
        stream_mode="values"
    ):
        if "messages" in event:
            response_chunks.append(event["messages"][-1])
    
    # Check for HITL interrupt
    state = agent.get_state(config)
    if state.next == ("human_approval",):
        # Send draft to WhatsApp for approval
        draft = state.values["department_results"]["cataloging"]["product"]
        send_whatsapp_approval_request(phone_number, draft)
    else:
        # Send final response
        final_message = response_chunks[-1].content
        send_whatsapp_message(phone_number, final_message)
    
    return {"status": "ok"}

@app.post("/webhook/whatsapp/approval")
async def whatsapp_approval(request: Request):
    """
    Handles user approval responses.
    """
    data = await request.json()
    # Resume workflow with user's decision
    # ... (similar to HITL example above)
```

---

## Directory Structure

```
agents/src/autifyme_agents/
├── workflows/
│   └── project_manager.py          # Main Project Manager agent
│
├── departments/
│   ├── cataloging/
│   │   └── instructions.py         # Department-specific prompts
│   ├── marketing/
│   └── operations/
│
├── tools/
│   ├── __init__.py
│   ├── registry.py                 # Tool organization
│   ├── cataloging_tools.py         # Image/text analysis specialists
│   ├── storage_tools.py            # Database tools
│   └── communication_tools.py      # WhatsApp/email tools
│
├── prompts/
│   └── templates.py                # All prompt templates
│
├── schemas/
│   ├── state.py                    # State schemas
│   └── models.py                   # Pydantic models
│
└── entrypoints/
    ├── whatsapp_webhook.py         # WhatsApp entry
    └── streamlit_app.py            # UI for testing/HITL
```

---

## Implementation Order

### Week 1: Core Infrastructure
**Day 1:**
- Install `deepagents` and dependencies
- Create project structure
- Set up LangSmith tracing

**Day 2-3:**
- Implement PROJECT_MANAGER_PROMPT
- Create basic Project Manager (no tools yet)
- Test planning capabilities

**Day 4-5:**
- Implement tool registry
- Create first tools (get_company_profile, save_product)
- Test tool calling

### Week 2: Cataloging Workflow
**Day 1-2:**
- Implement image_analysis_specialist
- Implement text_analysis_specialist
- Test with sample images/text

**Day 3-4:**
- Implement HITL flow
- Build Streamlit approval UI
- Test end-to-end cataloging

**Day 5:**
- WhatsApp webhook integration
- Test with real WhatsApp messages
- Deploy to staging

---

## Testing Strategy

### Unit Tests
```python
# tests/unit/test_tools.py

def test_image_analysis_specialist():
    """Test image analysis tool"""
    result = image_analysis_specialist.invoke({
        "image_url": "https://example.com/test.jpg",
        "company_context": {"company_name": "TestCo", ...}
    })
    assert "category" in result
    assert "color" in result
```

### Integration Tests
```python
# tests/integration/test_project_manager.py

@pytest.mark.asyncio
async def test_cataloging_workflow():
    """Test full cataloging workflow"""
    agent = create_project_manager(test_company_profile)
    
    result = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": "Catalog this product: [IMAGE_URL]"
        }]
    })
    
    # Should use planning tool
    # Should delegate to cataloging
    # Should return product draft
    assert result["department_results"]["cataloging"]
```

### E2E Tests
```python
# e2e_tests/test_whatsapp_cataloging.py

def test_whatsapp_to_catalog():
    """Test WhatsApp message → Catalog entry"""
    # Send WhatsApp message
    # Verify agent response
    # Approve product
    # Verify in database
```

---

## LangSmith Integration

```python
# All functions automatically traced with @traceable

from langsmith import traceable

@traceable(
    name="Project Manager - Cataloging Workflow",
    tags=["project-manager", "cataloging"],
    metadata={"version": "1.0"}
)
def create_project_manager(...):
    # Automatically traced
    pass

# Sub-agents and tool calls also automatically traced
# View full workflow in LangSmith dashboard
```

---

## Success Criteria

Before moving to Phase 3 (additional workflows):

- ✅ Project Manager can understand natural language requests
- ✅ Planning tool breaks down complex tasks
- ✅ Can delegate to Cataloging department (sub-agent)
- ✅ Image and text analysis work correctly
- ✅ HITL approval flow works (accept/edit/reject)
- ✅ State persists across interrupts
- ✅ WhatsApp integration works end-to-end
- ✅ Product is saved to database after approval
- ✅ All operations are traced in LangSmith
- ✅ First customer successfully catalogs products

---

## Next Steps

1. **Start building** (today)
2. **Week 1:** Core Project Manager infrastructure
3. **Week 2:** Cataloging workflow + WhatsApp
4. **Week 3:** Deploy to first customer
5. **Week 4+:** Additional workflows (Marketing, Operations, etc.)

**Let's build.** 🚀

