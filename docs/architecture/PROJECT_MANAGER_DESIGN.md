# Project Manager Agent Design with `deepagents`

**Date:** September 30, 2025  
**Purpose:** Define how we use `deepagents` to implement our Project Manager Agent  
**Status:** Implementation Ready

---

## Overview

The Project Manager Agent is the top-level orchestrator in our hierarchical agentic system. We use the `deepagents` library to implement it, leveraging its built-in planning, sub-agent delegation, and HITL capabilities.

**Key Insight:** `deepagents` sub-agents = Our Department Heads

---

## Architecture Mapping

### Our Hierarchy → `deepagents` Components

```
Project Manager Agent (deepagents main agent)
    ├── Planning Tool (built-in)
    ├── Sub-agent: Cataloging Department (custom sub-agent)
    │   └── Tools: [image_analysis, text_analysis, save_product]
    ├── Sub-agent: Marketing Department (custom sub-agent)
    │   └── Tools: [copywriter, seo_analyzer, social_poster]
    └── Sub-agent: Operations Department (custom sub-agent)
        └── Tools: [billing, shipping, inventory]
```

**Implementation:**
- **Project Manager** = `deepagents` main agent with generic instructions
- **Department Heads** = Custom sub-agents with domain-specific instructions and tools
- **Specialists** = Tools within each department's toolset
- **HITL** = Built-in approval for critical operations

---

## Implementation Strategy

### Phase 1: Generic Project Manager (Week 1)

Build the Project Manager that can orchestrate ANY workflow.

```python
# agents/src/autifyme_agents/workflows/project_manager.py

from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres import PostgresSaver

from ..core.config import settings
from ..prompts.templates import PROJECT_MANAGER_PROMPT
from ..tools.registry import get_all_tools

def create_project_manager(company_profile: dict):
    """
    Creates the generic Project Manager agent.
    
    Args:
        company_profile: Company context (brand voice, target audience, etc.)
    
    Returns:
        Compiled LangGraph workflow
    """
    
    # Get all available tools (from all departments)
    tools = get_all_tools()
    
    # Create agent with company-specific context
    agent = create_deep_agent(
        tools=tools,
        instructions=PROJECT_MANAGER_PROMPT.format(
            company_name=company_profile["name"],
            brand_voice=company_profile["brand_voice"],
            target_audience=company_profile["target_audience"],
        ),
        model=ChatOpenAI(model="gpt-4o", temperature=0.2),
        tool_configs={
            # HITL for critical operations
            "save_product": True,
            "publish_website": True,
            "post_to_social": True,
            "send_invoice": True,
        }
    )
    
    # Add persistent checkpointing
    checkpointer = PostgresSaver.from_conn_string(settings.DATABASE_URL)
    agent.checkpointer = checkpointer
    
    return agent
```

**Key Features:**
- Generic instructions (handles any workflow type)
- All tools available (delegates to appropriate department via sub-agents)
- HITL for critical operations
- State persistence with PostgreSQL

---

### Phase 2: Department Sub-agents (Week 2)

Each department is a custom sub-agent with specific instructions and tools.

```python
# agents/src/autifyme_agents/departments/cataloging/instructions.py

CATALOGING_DEPT_INSTRUCTIONS = """
You are the Cataloging Department Head.

Your role is to transform raw product information (images, text from WhatsApp) 
into structured, high-quality product listings for the catalog.

Available specialists:
- image_analysis: Extract product info from images
- text_analysis: Extract product info from text messages
- save_product: Save product to database (requires approval)

Workflow:
1. Analyze input type (image, text, or both)
2. Delegate to appropriate specialist(s)
3. Combine results into complete product draft
4. Request approval for save_product
5. Save approved product

Brand Voice: {brand_voice}
Target Audience: {target_audience}
"""
```

```python
# The Project Manager will automatically create sub-agents
# when it needs to delegate to a specific department.
# We just need to provide department-specific tools.

# agents/src/autifyme_agents/tools/registry.py

def get_cataloging_tools():
    """Returns tools for Cataloging Department"""
    return [
        image_analysis_specialist,
        text_analysis_specialist,
        save_product,
        get_company_profile,
    ]

def get_all_tools():
    """Returns all tools for Project Manager"""
    return [
        *get_cataloging_tools(),
        *get_marketing_tools(),
        *get_operations_tools(),
    ]
```

**How Sub-agent Delegation Works:**

1. **User:** "Catalog this product from images"
2. **Project Manager:** Uses planning tool → "This is a cataloging task"
3. **Project Manager:** Creates custom sub-agent for Cataloging Department
4. **Sub-agent:** Gets only cataloging tools + department instructions
5. **Sub-agent:** Delegates to specialists (tools), assembles result
6. **Sub-agent:** Returns to Project Manager
7. **Project Manager:** Returns to user

**Benefit:** Context isolation - each department only sees relevant tools and context.

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

@tool
def image_analysis_specialist(image_url: str, company_context: dict) -> dict:
    """
    Analyzes a product image and extracts structured information.
    
    Use this tool when you need to understand what's in a product image.
    
    Args:
        image_url: URL to the product image
        company_context: Company brand voice and guidelines
    
    Returns:
        Dictionary with: category, color, pattern, description, confidence
    """
    # Implementation using multimodal LLM
    llm = ChatOpenAI(model="gpt-4o")
    
    prompt = f"""
    Analyze this product image for {company_context['company_name']}.
    
    Brand Voice: {company_context['brand_voice']}
    Target Audience: {company_context['target_audience']}
    
    Extract:
    - Product category
    - Colors
    - Patterns/designs
    - Key features
    - Description in brand voice
    
    Image: {image_url}
    """
    
    result = llm.invoke([
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": image_url}}
    ])
    
    return parse_structured_output(result)

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
    agent = create_project_manager(company_profile)
    
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

