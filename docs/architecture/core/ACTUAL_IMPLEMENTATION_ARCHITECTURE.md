# Actual Implementation Architecture (As-Built Reference)

**Date:** January 22, 2025
**Status:** ✅ Verified (2-Level Architecture v1.0.0)
**Last Updated:** 2-Level refactoring complete - PM → Specialist → Tools
**Purpose:** Ground truth - actual implementation as coded
**Design Guidelines:** See [DOMAIN_DESIGN_GUIDELINES.md](./DOMAIN_DESIGN_GUIDELINES.md) for architectural standards when building new workflows

---

## Executive Summary

This document captures the **actual implemented architecture** verified from production code.

**Architecture:** 2-Level hierarchy using DeepAgents - **PM → Specialist → Tools** pattern. Departments removed for simplicity and direct specialist delegation.

**Key Changes from Previous 3-Level:**
- ❌ Removed Layer 2 (Departments)
- ✅ PM delegates directly to specialists via SubAgents
- ✅ Specialists configured at PM level
- ✅ Tools attached to specialists based on their needs
- ✅ HITL configured via `tool_configs` on specialist tools

---

## Architecture Layers

### Layer 1: Project Manager (Top-Level Orchestrator)

**Implementation:** `workflows/project_manager.py`

```python
# Actual code pattern:
project_manager = create_deep_agent(
    tools=[],  # PM has NO tools (specialists have the tools)
    system_prompt=load_prompt("project_manager.prompt"),
    subagents=[
        # Specialists as SubAgents
        cataloging_specialist_subagent,
    ],
    model=llm,
    checkpointer=checkpointer,
    store=store,
    use_longterm_memory=True,
    context_schema=CompanyContext,
)
```

**Subagents:**
- Specialists exposed as **SubAgents** (DeepAgents native pattern)
- PM delegates via automatic subagent invocation
- Each subagent: `name`, `description`, `system_prompt`, `tools`, `tool_configs`

**What PM Does NOT Have:**
- ❌ Direct tool access (specialists have the tools)
- ❌ Domain logic (specialists handle this)
- ❌ Tool configuration (configured on specialists)

**Data Flow:**
- Input: `{"messages": [HumanMessage(content)]}`
- Semantic message format from runner
- Delegates to specialists via subagent calls
- Output: Via messages in state

---

### Layer 2: Specialists (Domain Experts)

**Implementation:** `specialists/cataloging_specialist.py`

Specialists are **SubAgents** created via `create_agent()` and attached to PM:

```python
# Actual code pattern:
def create_cataloging_specialist(storage: StorageInterface) -> Any:
    """Create cataloging specialist with tools."""

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

**Current Specialists:**
- `cataloging_specialist` - Synthesizes Product models from user descriptions + image analysis

**Tools Available to Specialists:**
- `image_analysis_tool` - Analyzes product images via Vision API
- `save_product` - Persists products to database (HITL enabled)

**HITL Configuration:**
- Configured via `tool_configs` on specialist
- Triggers DeepAgents native interrupt
- Runner detects interrupt, sends approval request
- Resumes with Command

**Structured Outputs:**
- `Product` - Cataloging specialist output
- `ImageAnalysisResult` - Image analysis tool output

**How PM Invokes:**
- PM delegates to specialist by name (automatic via DeepAgents)
- Specialist receives focused input from PM
- Specialist uses tools to complete task
- Specialist returns structured Pydantic model or final response

---

### Layer 3: Tools (Utility Functions)

**Implementation:** `tools/image_analysis_tool.py`, `tools/storage_tools.py`

```python
# Actual code patterns:

# 1. Image Analysis Tool (Vision API)
@tool
def image_analysis_tool(image_path: str) -> ImageAnalysisResult:
    """Analyze product image using Vision API."""
    llm = get_llm(provider="openai", model="gpt-4.1-mini")
    image_uri = _encode_image_to_base64_uri(image_path)  # Resizes to 2048px max

    # Direct invoke with json_schema method for reliability
    structured_llm = llm.with_structured_output(
        ImageAnalysisResult,
        method="json_schema",  # More robust than function_calling
        include_raw=False,
    )

    result = structured_llm.invoke(messages)
    return result

# 2. Storage Tool with retry logic
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
```

**Key Patterns:**

**Image Analysis Tool:**
- Resizes images to 2048px max before Vision API call
- Uses `json_schema` method for structured output (more reliable than `function_calling`)
- Returns `ImageAnalysisResult` Pydantic model
- Token-optimized (target <50k tokens per image)

**save_product Tool:**
- Takes individual Product fields (not full Product object)
- Returns `CatalogingResult` (not Product!)
- Retry logic: 3 attempts for transient failures
- HITL: Configured at specialist level via tool_configs

**Image Optimization (Critical Fix):**
- `_resize_image_for_vision_api()` - Resizes to MAX_DIMENSION = 2048px
- `_encode_image_to_base64_uri()` - Converts to data URI
- JPEG quality 85, optimized compression
- Prevents Vision API timeout with large images

---

## HITL (Human-in-the-Loop) Flow

### Actual Implementation Pattern

**1. Configuration (Specialist Level):**
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
        interrupt_value = interrupts[0].value  # DeepAgents interrupt format
        # Extract draft, send approval request
```

**3. Interrupt Value Format (DeepAgents):**
```python
# HumanInTheLoopMiddleware format:
interrupt_value = {
    "action_request": {
        "action": "save_product",
        "args": {
            "name": "Product Name",
            "description": "...",
            "price": 29.99,
            "sizes": ["M", "L"],
            "colors": ["blue"],
            "image_urls": ["/path/to/image.jpg"]
        }
    }
}
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

**Critical:** PM does NOT handle HITL - runner orchestrates the flow.

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
    materials: List[str] = []
    style_tags: List[str] = []  # e.g., ['vintage', 'modern']
    estimated_dimensions: Optional[str] = None
```

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
"catalog this product for Rs 500"

Media Attachments:
1. [IMAGE] image/jpeg
   - Local path: /path/to/xyz123.jpg
   - Platform ID: xyz123
```

**4. PM processes:**
- Analyzes intent (cataloging request)
- Delegates to `cataloging_specialist` subagent
- Passes user message and context

**5. Specialist processes:**
- Calls `image_analysis_tool(image_path="/path/to/xyz123.jpg")`
- Synthesizes Product from user message + image insights
- Calls `save_product(name="...", price=500.0, ...)` → HITL interrupt

**6. Runner handles HITL:**
- Detects `__interrupt__` in stream
- Extracts draft from interrupt value
- Sends approval request via channel
- Waits for user response
- Resumes with Command

**7. save_product executes:**
- Persists to database
- Returns CatalogingResult
- Specialist completes
- PM relays result

---

## Architectural Alignment Status

✅ **2-LEVEL ARCHITECTURE**: Implementation complete!

| Layer | Pattern | Status |
|-------|---------|--------|
| **PM → Specialists** | SubAgents | ✅ Correct |
| **Specialists** | create_agent with tools | ✅ Correct |
| **Tools** | Utility functions | ✅ Correct |
| **HITL** | Specialist tool_configs | ✅ Correct |
| **Command Construction** | Runner handles | ✅ Correct |

---

## Prompt Writing Implications

### For PM Prompt:

**What PM Knows:**
- ✅ User sends structured messages (semantic descriptions)
- ✅ Can delegate to specialist subagents (mention available specialists)
- ✅ Specialists return results via messages
- ✅ Company context available via DeepAgents store

**What PM Does NOT Know:**
- ❌ HITL mechanics (runner handles this)
- ❌ How to build Commands (not PM's job)
- ❌ Individual specialist tools (specialists coordinate those)
- ❌ Tool implementation details (abstracted away)

**PM's Altitude:** High-level orchestration, intent classification, specialist delegation

---

### For Specialist Prompts:

**What Specialist Knows:**
- ✅ Has specific **tools** to accomplish tasks
- ✅ Calls `image_analysis_tool(image_path)` → returns ImageAnalysisResult
- ✅ Calls `save_product(name, price, ...)` → returns CatalogingResult
- ✅ save_product triggers HITL (framework handles automatically)
- ✅ Returns structured output or final response

**What Specialist Does NOT Know:**
- ❌ How HITL approval UI works (channel's job)
- ❌ Command construction (framework's job)
- ❌ PM's orchestration logic (separation of concerns)
- ❌ Other specialists (decoupled)

**Specialist's Altitude:** Domain workflow execution, tool usage, structured output generation

---

## Testing & Validation

**Local Testing Commands:**
```bash
# Direct PM invocation (interactive)
uv run python tests/cli/pm_chat.py --interactive

# Full workflow simulation with HITL
uv run python tests/cli/simulate.py "Catalog these sneakers"

# Autonomous testing framework
from tests.tools import execute_scenario, get_trace_overview
result = execute_scenario("Catalog Nike shoes Rs 1000", hitl_mode="auto_approve")
overview = get_trace_overview(result.trace_id)
```

**Key Files to Verify:**
- `workflows/project_manager.py` - PM construction
- `specialists/cataloging_specialist.py` - Specialist implementation
- `tools/image_analysis_tool.py` - Vision API wrapper
- `tools/storage_tools.py` - Database persistence
- `workflows/orchestration/runner.py` - HITL handling

---

## Performance & Resilience Optimizations

### Image Optimization (Critical Fix)

**Problem:** Large images (5MB phone photos) caused Vision API timeouts and excessive token usage (~300k tokens).

**Solution:** Resize and compress before Vision API call:

```python
# agents/src/autifyme_agents/tools/image_analysis_tool.py
MAX_DIMENSION = 2048  # OpenAI's high-detail threshold
JPEG_QUALITY = 85

def _resize_image_for_vision_api(image_path: str) -> bytes:
    """Resize to max 2048px, convert to optimized JPEG."""
    with Image.open(path) as img:
        # Convert RGBA to RGB
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1])
            img = rgb_img

        # Resize if needed (preserve aspect ratio)
        if max(img.size) > MAX_DIMENSION:
            img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)

        # Save as optimized JPEG
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=JPEG_QUALITY, optimize=True)
        return buffer.getvalue()
```

**Result:** Token usage reduced to ~50k tokens per image, Vision API reliability improved.

---

### Vision API Structured Output (Critical Fix)

**Problem:** Default `with_structured_output()` created unreliable RunnableSequence that hung with large images.

**Solution:** Use explicit `json_schema` method:

```python
# Before (unreliable):
structured_llm = llm.with_structured_output(ImageAnalysisResult)

# After (reliable):
structured_llm = llm.with_structured_output(
    ImageAnalysisResult,
    method="json_schema",  # More robust than function_calling
    include_raw=False,
)
```

**Why:** `json_schema` method provides better handling of large multimodal payloads than default `function_calling`.

---

### Centralized Error Classification

All external API errors flow through centralized classifier:

```python
# agents/src/autifyme_agents/core/exceptions.py
def classify_api_error(
    error: Exception,
    tool_name: str,
    api_name: str,
    fallback_error_class: type[AutifyMEError] = ToolExecutionError,
) -> AutifyMEError:
    """Classify API error and raise appropriate AutifyME exception.

    Transient indicators: timeout, connection, rate limit, 429, 503, 502, 504
    - Transient → ExternalAPIError(is_retryable=True)
    - Permanent → fallback_error_class
    """
```

**Benefits:**
- Retry logic applied consistently across all tools
- Tenacity respects `ExternalAPIError.is_retryable` flag
- Centralized maintenance point

---

### Storage Cleanup & Graceful Shutdown

Storage singleton registers atexit handler:

```python
# agents/src/autifyme_agents/integrations/storage/storage_factory.py
import atexit

def get_storage() -> StorageInterface:
    """Return singleton with cleanup handler."""
    global _storage_instance, _cleanup_registered

    if _storage_instance is None:
        _storage_instance = SupabaseStorageClient()

        if not _cleanup_registered:
            atexit.register(_cleanup_storage)
            _cleanup_registered = True

    return _storage_instance
```

**Why Important:** Graceful shutdowns prevent HTTP connection leaks in serverless/container environments.

---

## Summary: 2-Level Architecture Checklist

When refactoring or extending:

- [ ] PM delegates directly to specialists (no department layer)
- [ ] Specialists are SubAgents under PM
- [ ] Tools attached to specialists based on needs
- [ ] HITL configured via tool_configs on specialist tools
- [ ] PM does NOT handle HITL or Commands (runner does)
- [ ] Specialists return structured Pydantic models when appropriate
- [ ] Image analysis tool uses `json_schema` method
- [ ] Images resized to 2048px max before Vision API
- [ ] Platform tools omitted from PM (specialists don't need media download)
- [ ] No Python code in prompts (show patterns via examples)

---

**Last Updated:** January 22, 2025
**Verified Against:** Main branch (InitialDesign-2-level_v1.0.0)
**Next Review:** When adding new specialists or workflows
