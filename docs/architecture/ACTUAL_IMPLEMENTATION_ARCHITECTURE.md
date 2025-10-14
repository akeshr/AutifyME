# Actual Implementation Architecture (As-Built Reference)

**Date:** January 2025
**Status:** ✅ Verified from Codebase
**Purpose:** Ground truth for prompt refactoring - actual implementation, not planned design

---

## Executive Summary

This document captures the **actual implemented architecture** by analyzing production code, not documentation. Use this as source of truth when writing/updating prompts.

**Critical Finding:** Current implementation uses DeepAgents with CustomSubAgents pattern - **NOT** the tools-as-subagents pattern described in some design docs.

---

## Architecture Layers

### Layer 1: Project Manager (Top-Level Orchestrator)

**Implementation:** `workflows/project_manager.py`

```python
# Actual code pattern:
project_manager = create_deep_agent(
    tools=[write_todos, download_{platform}_media],  # Coordination tools only
    instructions=load_prompt("project_manager.prompt"),
    subagents=[cataloging_department_spec],  # CustomSubAgent with pre-built graph
    tool_configs={},  # Empty - HITL handled by departments
    checkpointer=checkpointer,
)
```

**Tools Available:**
- `write_todos` - DeepAgents planning tool
- `download_{platform}_media` - Platform-specific media download (WhatsApp, Telegram, etc.)
  - **Dynamic naming**: `download_whatsapp_media`, `download_telegram_media`
  - Created via `create_platform_media_tools(channel)`
  - Takes `media_id`, returns local file path

**Subagents:**
- Departments exposed as **CustomSubAgents** (pre-built graphs)
- PM delegates via automatic "task" tool (DeepAgents built-in)
- Each subagent has: `name`, `description`, `graph` (compiled agent)

**What PM Does NOT Have:**
- ❌ Domain tools (image_analysis_specialist, save_product, etc.)
- ❌ tool_configs for HITL (departments handle this)
- ❌ Direct access to specialists
- ❌ Command construction logic (runner handles HITL)

**Data Flow:**
- Input: `{"messages": [HumanMessage(semantic_description)]}`
- Uses `IncomingMessage.to_semantic_description()` for structured message format
- Delegates to departments via `task` tool
- Output: Via messages in state

---

### Layer 2: Departments (Domain Orchestrators)

**Implementation:** `departments/cataloging_department.py`

```python
# Actual code pattern (CORRECTED):
department = create_deep_agent(
    model=llm,
    instructions=load_prompt("departments/cataloging_department.prompt"),
    tools=[
        write_todos,  # Planning tool
        create_save_product_tool(storage),  # Database persistence
        *platform_media_tools,  # Optional media download
    ],
    subagents=[  # ✅ Specialists as subagents (proper hierarchy)
        {
            "name": "image_analysis_specialist",
            "description": "Analyze product images...",
            "response_format": ImageAnalysisResult,
            "system_prompt": load_prompt("specialists/image_analysis_specialist.prompt"),
        },
        {
            "name": "cataloging_specialist",
            "description": "Transform user descriptions into Product models...",
            "response_format": Product,
            "system_prompt": load_prompt("specialists/cataloging_specialist.prompt"),
        },
    ],
    middleware=[CompanyContextMiddleware(storage)],
    checkpointer=checkpointer,
    tool_configs={
        "save_product": ToolConfig(
            allow_accept=True,
            allow_edit=True,
            allow_respond=True,
            description="Review product before saving"
        )
    },
)
```

**Tools Available:**
- `write_todos` - Planning tool
- `save_product` - Persists product (HITL enabled)
- `download_{platform}_media` - If channel provided

**Subagents Available:**
- `image_analysis_specialist` - SubAgent that returns `ImageAnalysisResult`
- `cataloging_specialist` - SubAgent that returns `Product`

**HITL Configuration:**
- Configured via `tool_configs` on `save_product`
- Triggers LangGraph native interrupt: `__interrupt__` in event stream
- Runner detects interrupt, sends approval request
- Resumes with `Command(resume={interrupt_id: {"type": "accept"}})`

**Middleware:**
- `CompanyContextMiddleware` - Injects company_profile into tool calls
- DeepAgents auto-adds: caching, summarization

**What Departments Do NOT Have:**
- ❌ Specialists as subagents (they're tools!)
- ❌ Direct database access (goes through tools)
- ❌ HITL logic (framework handles via tool_configs)

---

### Layer 3: Specialists (Transformation SubAgents)

**Implementation:** Defined as SubAgent specs in department configuration

**Pattern:** Specialists are **SubAgents** (not tools, not custom agents)

```python
# SubAgent specification in department:
{
    "name": "cataloging_specialist",
    "description": "Transform user descriptions into Product models...",
    "response_format": Product,  # Structured output
    "system_prompt": load_prompt("specialists/cataloging_specialist.prompt"),
}
```

**Key Pattern:** DeepAgents builds specialist agents automatically from SubAgent specs!

**Structured Outputs:**
- `ImageAnalysisResult` - Vision model output
- `Product` - Cataloging specialist output

**How Departments Invoke:**
- Department delegates to specialist by name (automatic via DeepAgents)
- Specialist receives focused input from department
- Specialist returns structured Pydantic model
- Department uses output for next step

**Why SubAgents, Not Tools:**
- Proper hierarchical delegation (PM → Dept → Specialist)
- Consistent with architectural design
- Clear separation of concerns
- Observability at each layer

---

### Layer 4: Tools (Utility Functions)

**Implementation:** `tools/storage_tools.py`, `tools/platform_tools.py`

```python
# Actual code patterns:

# 1. Storage Tool with retry logic
@tool(args_schema=SaveProductArgs)
@retry(stop=stop_after_attempt(3), ...)
def save_product(**kwargs) -> CatalogingResult:
    product = Product(**kwargs)
    saved = storage.save_product(product)
    return CatalogingResult(
        stage="saved",
        success=True,
        product_id=saved.id,
        ...
    )

# 2. Platform Tool with dynamic naming
def create_platform_media_tools(channel: MessagingChannel) -> list:
    @tool
    def download_media(media_id: str) -> str:
        return str(channel.download_media(media_id))

    # Dynamic naming based on platform
    download_media.name = f"download_{platform}_media"
    download_media.description = f"Download media from {platform}..."

    return [download_media]
```

**save_product Signature:**
- Args: `name`, `description`, `price`, `sizes`, `colors`, `image_urls` (individual fields)
- Returns: `CatalogingResult` (not Product!)
- Retry logic: 3 attempts for transient failures
- HITL: Configured at department level via tool_configs

**Platform Tools:**
- Dynamically named: `download_whatsapp_media`, `download_telegram_media`
- Takes: `media_id` (platform-specific identifier)
- Returns: Local file path as string
- Used by: PM and departments

---

## HITL (Human-in-the-Loop) Flow

### Actual Implementation Pattern

**1. Configuration (Department Level):**
```python
tool_configs = {
    "save_product": ToolConfig(
        allow_accept=True,    # User can approve as-is
        allow_edit=True,      # User can modify and approve
        allow_respond=True,   # User can reject with feedback
        description="Review product before saving"
    )
}
```

**2. Interrupt Detection (Runner):**
```python
for event in pm.stream(payload, config=config, stream_mode="values"):
    if "__interrupt__" in event:
        interrupts = event.get("__interrupt__", [])
        interrupt_value = interrupts[0].value  # Native LangGraph interrupt
        # Extract draft, send approval request
```

**3. Interrupt Value Format:**
```python
# HumanInTheLoopMiddleware format:
interrupt_value = [
    {
        "action_request": {
            "action": "save_product",
            "args": {
                "name": "Jar 500ml",
                "description": "...",
                "price": 30.0,
                "sizes": [],
                "colors": ["clear"],
                "image_urls": ["/path/to/image.jpg"]
            }
        }
    }
]
```

**4. Resumption (Runner):**
```python
# Extract interrupt_id from checkpoint
state = checkpointer.get_tuple(config)
interrupt_id = state.checkpoint["channel_values"]["__interrupt__"][0].id

# Resume with Command
command = Command(resume={interrupt_id: {"type": "accept"}})
for event in pm.stream(command, config=config, stream_mode="values"):
    # Tool executes, returns CatalogingResult
```

**Critical:** PM does NOT handle HITL - runner does. PM is unaware of interrupts.

---

## Data Models

### Core Models (`schemas/models.py`)

**Product:**
```python
class Product(BaseModel):
    id: Optional[UUID] = None  # Database-generated
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    sizes: Optional[List[str]] = Field(default_factory=list)
    colors: Optional[List[str]] = Field(default_factory=list)
    image_urls: Optional[List[str]] = Field(default_factory=list)
```

**CatalogingResult:**
```python
class CatalogingResult(BaseModel):
    stage: Literal["draft", "awaiting_approval", "saved", "failed"]
    success: bool
    product_id: Optional[UUID] = None
    product_name: Optional[str] = None
    message: str
    data: Optional[dict] = None  # Contains product details
```

**CompanyProfile:**
```python
class CompanyProfile(BaseModel):
    id: str
    name: str
    brand_voice: str
    target_audience: str
    style_preferences: Optional[List[str]] = []
    industry: Optional[str] = None
```

### Specialist Outputs (`schemas/agent_outputs.py`)

**ImageAnalysisResult:**
```python
class ImageAnalysisResult(BaseModel):
    visual_description: str  # min_length=20
    identified_colors: List[str] = []
    style_tags: List[str] = []  # e.g., ['vintage', 'modern']
```

---

## State Management

### ProjectManagerState (`schemas/state.py`)

```python
class ProjectManagerState(DeepAgentState):
    messages: Annotated[Sequence[MessageType], add_messages]
    company_profile: CompanyProfile
    plan: list[dict]
    current_step: int
    department_results: DepartmentResults
    status: Literal["idle", "planning", "awaiting_approval", "completed", "blocked"]
    last_error: Optional[str]
    metadata: ProjectMetadata
    pending_interrupts: list[InterruptInfo]  # HITL context (not used by PM directly)
```

**Note:** `pending_interrupts` exists in state but **PM does NOT use it** - runner extracts from checkpoint.

---

## Message Flow

### Incoming Message Processing

**1. Runner receives raw message:**
```python
runner.handle_message(sender, text, media_id)
```

**2. Runner builds semantic payload:**
```python
incoming_msg = IncomingMessage(
    text=text,
    media=[MediaReference(...)],
    platform="whatsapp",
    ...
)
content = incoming_msg.to_semantic_description()  # Structured description
messages = [HumanMessage(content=content)]
```

**3. PM receives structured description:**
```
User sent a message via WhatsApp.

Text Content:
"catalog this jar 500ml 30rs"

Media Attachments:
1. [IMAGE] image/jpeg
   - Local path: /path/to/xyz123.jpg
   - Platform ID: xyz123
```

**4. PM processes:**
- Analyzes intent (cataloging request)
- Downloads media if needed (via download_whatsapp_media tool)
- Delegates to cataloging_department (via task tool / subagent)

**5. Department processes:**
- Calls image_analysis_specialist(image_url="/path/to/xyz123.jpg")
- Calls cataloging_specialist(user_message="...", image_analysis={...})
- Calls save_product(name="...", price=30.0, ...) → HITL interrupt

**6. Runner handles HITL:**
- Detects `__interrupt__` in stream
- Extracts draft from interrupt value
- Sends approval request via channel
- Waits for user response
- Resumes with Command

**7. save_product executes:**
- Persists to database
- Returns CatalogingResult
- Department completes
- PM relays result

---

## Architectural Alignment Status

✅ **CORRECTED**: Implementation now matches design intent!

| Layer | Pattern | Status |
|-------|---------|--------|
| **PM → Departments** | CustomSubAgents | ✅ Correct |
| **Departments → Specialists** | SubAgents (not tools) | ✅ **FIXED** |
| **Specialists** | SubAgent specs with response_format | ✅ Correct |
| **Tools** | Utility functions only | ✅ Correct |
| **HITL** | Department tool_config | ✅ Correct |
| **Command Construction** | Runner handles | ✅ Correct |

---

## Prompt Writing Implications

### For PM Prompt:

**What PM Knows:**
- ✅ User sends structured messages (semantic descriptions)
- ✅ Has write_todos for planning
- ✅ Has download_{platform}_media for fetching attachments
- ✅ Can delegate to departments via "task" (mention as available departments, not tools)
- ✅ Departments return results via state/messages

**What PM Does NOT Know:**
- ❌ HITL mechanics (runner handles this)
- ❌ How to build Commands (not PM's job)
- ❌ pending_interrupts interpretation (runner's job)
- ❌ Individual specialist tools (departments coordinate those)
- ❌ save_product tool (department's tool)

**PM's Altitude:** High-level orchestration, intent classification, delegation strategy

---

### For Department Prompt:

**What Department Knows:**
- ✅ Has specialist **subagents** that return structured data
- ✅ Delegates to `image_analysis_specialist` subagent → returns ImageAnalysisResult
- ✅ Delegates to `cataloging_specialist` subagent → returns Product
- ✅ Calls `save_product` tool (takes Product fields, returns CatalogingResult)
- ✅ save_product triggers HITL (framework handles automatically)
- ✅ Has write_todos for multi-step coordination
- ✅ Can download media if needed

**What Department Does NOT Know:**
- ❌ How HITL approval UI works (channel's job)
- ❌ Command construction (framework's job)
- ❌ PM's orchestration logic (separation of concerns)
- ❌ Specialist implementation details (delegates via subagent name)

**Department's Altitude:** Domain workflow orchestration, subagent delegation, quality assurance

---

### For Specialist Prompts:

**What Specialist Knows:**
- ✅ Receives focused input (user_message + optional image_analysis)
- ✅ Company context injected via middleware
- ✅ Returns structured Pydantic model
- ✅ No tools available (pure transformation)

**What Specialist Does NOT Know:**
- ❌ Orchestration logic (department's job)
- ❌ Approval workflows (department + framework)
- ❌ Other specialists (decoupled)

**Specialist's Altitude:** Focused transformation, domain expertise, structured output generation

---

## Testing & Validation

**Local Testing Commands:**
```bash
# Direct PM invocation (interactive)
uv run python -m autifyme_agents.cli.pm_chat

# Full workflow simulation with HITL
uv run python -m autifyme_agents.cli.simulate

# Inspect traces
uv run python -m autifyme_agents.cli.inspect --thread-id <id>
```

**Key Files to Verify:**
- `workflows/project_manager.py` - PM construction
- `departments/cataloging_department.py` - Department construction
- `specialists/cataloging_specialist.py` - Specialist implementation
- `tools/cataloging_tools.py` - Tool wrappers
- `workflows/orchestration/runner.py` - HITL handling

---

## Summary: Prompt Refactoring Checklist

When refactoring prompts, ensure alignment with:

- [ ] PM only has coordination tools (write_todos, download_media)
- [ ] PM delegates to departments via CustomSubAgents
- [ ] PM does NOT handle HITL or Commands
- [ ] **Departments delegate to specialists AS SUBAGENTS** (not tools!)
- [ ] Departments call save_product tool with individual Product fields
- [ ] Specialists defined as SubAgent specs with response_format
- [ ] Specialists return Pydantic models (Product, ImageAnalysisResult)
- [ ] Specialists are context-light (company_profile from parent context)
- [ ] Platform tools have dynamic names (download_{platform}_media)
- [ ] HITL is transparent to PM and departments (framework handles)
- [ ] No Python code in prompts (show patterns via examples)

---

**Last Updated:** January 2025
**Verified Against:** Main branch (InitialDesign)
**Next Review:** When adding new departments or workflows

