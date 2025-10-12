# Project Manager: Intent Analysis & Universal Message Handling

**Date**: 2025-10-09
**Status**: Architectural Specification
**Purpose**: Define how PM handles all message types across all platforms with proper intent classification

---

## Executive Summary

This document addresses the architectural challenge: **How should the Project Manager handle diverse message types (text, images, videos, documents) from multiple platforms (WhatsApp, SMS, Telegram, Email, Web) while correctly classifying user intent?**

**Key Decision**: PM receives **semantic, normalized messages** (not raw platform payloads) and uses **LLM reasoning** (not tool-based analysis) for intent classification. Media is handled via **platform-specific strategies** (eager/lazy download) but PM only sees metadata, not actual files.

---

## 1. The Input Complexity Problem

### 1.1 Scale of Scenarios

**Total permutation space**: 3,520+ unique scenarios

- **8 platforms**: WhatsApp, SMS, Telegram, Email, Web, Slack, Voice, API
- **11 message types**: text-only, single image, single video, text+image, multiple images, mixed media, etc.
- **10 user intents**: catalog_new, catalog_update, inquiry_product, conversational, multi-step, etc.
- **4 context states**: fresh conversation, mid-conversation, awaiting approval, error recovery

### 1.2 Critical Scenarios (Representative Sample)

| # | Platform | Message Type | User Intent | Context State | PM Challenge |
|---|----------|--------------|-------------|---------------|--------------|
| 1 | WhatsApp | single_image | catalog_new | fresh | Is image a product or just sharing? |
| 2 | WhatsApp | text+image | catalog_new | fresh | Clear intent |
| 3 | WhatsApp | multiple_images | catalog_batch | fresh | Batch or single product with angles? |
| 4 | WhatsApp | text_only | conversational | fresh | Greeting vs actual request? |
| 5 | WhatsApp | single_image | ambiguous | fresh | Need clarification from user |
| 6 | Email | text+document | catalog_batch | fresh | PDF may contain many products |
| 7 | Web | mixed_media | catalog_new | mid_conversation | Context from previous messages |
| 8 | API | text_only | catalog_new | fresh | Structured input, clear intent |
| 9 | WhatsApp | text+image | catalog_update | awaiting_approval | User refining during HITL |

---

## 2. Platform-Specific Media Handling

### 2.1 Download Strategy by Platform

Different platforms have different media lifecycle constraints:

| Platform | Strategy | Rationale | Implementation |
|----------|----------|-----------|----------------|
| **WhatsApp** | EAGER | URLs expire in minutes despite 30-day storage | Runner downloads immediately, stores path |
| **SMS** | EAGER | MMS URLs expire in hours (Twilio: 4hrs) | Runner downloads immediately |
| **Telegram** | LAZY | file_id never expires, download on-demand | Store file_id, department downloads if needed |
| **Email** | LAZY | Attachments stored permanently with email | Store attachment reference, download if needed |
| **Web Upload** | NONE | File already on our filesystem | Direct path to file |
| **Slack** | LAZY | Files stored on Slack with OAuth access | Store file reference, download with token |

**Architectural Implication**: Runner must implement **platform-specific media strategies**. PM never implements download logic.

### 2.2 Canonical Media Reference Schema

```python
from typing import Literal, Optional
from pydantic import BaseModel
from pathlib import Path

class MediaReference(BaseModel):
    """Platform-agnostic media reference."""

    # Identity
    media_id: str  # Platform-specific identifier
    media_type: Literal["image", "video", "audio", "document", "voice"]
    mime_type: str  # e.g., "image/jpeg", "video/mp4"

    # Access
    platform: Literal["whatsapp", "telegram", "email", "web", "sms", "slack"]
    download_strategy: Literal["eager", "lazy", "none"]
    local_path: Optional[Path] = None  # Set if already downloaded (eager/none strategies)
    platform_url: Optional[str] = None  # Platform-specific URL (may expire)

    # Metadata
    size_bytes: Optional[int] = None
    caption: Optional[str] = None
    filename: Optional[str] = None
    expires_at: Optional[datetime] = None  # For eager platforms
```

---

## 3. Canonical Message Schema

### 3.1 IncomingMessage Structure

PM should receive **normalized, semantic messages** regardless of platform:

```python
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

class IncomingMessage(BaseModel):
    """Canonical message format for PM consumption."""

    # Core Content
    text: Optional[str] = None  # User's text message (if any)
    media: List[MediaReference] = []  # Media attachments (if any)

    # Context
    platform: str  # Source platform
    sender_id: str  # Platform-specific user ID
    thread_id: str  # Conversation thread (for checkpointer)
    timestamp: datetime

    # Advanced Context (optional)
    reply_to_message_id: Optional[str] = None  # If replying to previous message
    forwarded_from: Optional[str] = None  # If forwarded message
    conversation_history: Optional[List[Dict[str, Any]]] = None  # Recent messages for context

    # Platform-Specific Extras
    platform_metadata: Dict[str, Any] = {}  # Platform-specific fields

    def has_media(self) -> bool:
        return len(self.media) > 0

    def has_text(self) -> bool:
        return self.text is not None and len(self.text.strip()) > 0

    def is_empty(self) -> bool:
        return not self.has_text() and not self.has_media()

    def media_summary(self) -> str:
        """Human-readable summary of attached media."""
        if not self.media:
            return "No media"
        counts = {}
        for m in self.media:
            counts[m.media_type] = counts.get(m.media_type, 0) + 1
        parts = [f"{count} {mtype}(s)" for mtype, count in counts.items()]
        return ", ".join(parts)
```

### 3.2 Message Normalization Examples

**WhatsApp Image Message**:
```python
IncomingMessage(
    text="Catalog these sneakers",
    media=[
        MediaReference(
            media_id="whatsapp_media_123",
            media_type="image",
            mime_type="image/jpeg",
            platform="whatsapp",
            download_strategy="eager",
            local_path=Path("/tmp/media_123.jpg"),  # Already downloaded by runner
            size_bytes=245678,
        )
    ],
    platform="whatsapp",
    sender_id="+919876543210",
    thread_id="whatsapp:+919876543210",
    timestamp=datetime.now(),
)
```

**Email with PDF Attachment**:
```python
IncomingMessage(
    text="Please import all products from this catalog",
    media=[
        MediaReference(
            media_id="email_attachment_456",
            media_type="document",
            mime_type="application/pdf",
            platform="email",
            download_strategy="lazy",  # Can download later
            local_path=None,  # Not downloaded yet
            platform_url="imap://mailserver/inbox/message/456/attachment/1",
            filename="product_catalog_2025.pdf",
            size_bytes=1024000,
        )
    ],
    platform="email",
    sender_id="user@example.com",
    thread_id="email:user@example.com:thread123",
    timestamp=datetime.now(),
)
```

---

## 4. PM Intent Classification Strategy

### 4.1 Core Question: Tools vs LLM Reasoning?

**Question**: Should PM use tools to analyze user intent, or rely on LLM reasoning?

**Analysis**:

| Approach | Pros | Cons |
|----------|------|------|
| **Tool-based** (`analyze_intent` tool) | Explicit, traceable, can use specialized models | Adds latency, over-engineering for capable LLMs |
| **LLM reasoning** (gpt-4.1-nano-2025-04-14 native intelligence) | Fast, flexible, handles nuance well | Less explicit control, harder to debug |

**Decision**: **LLM reasoning** with structured prompts.

**Rationale**:
- gpt-4.1-nano-2025-04-14 is sophisticated enough to classify intents from semantic descriptions
- Adding an `analyze_intent` tool just wraps another LLM call (redundant)
- PM's prompt can be engineered to elicit correct classification
- Multi-step reasoning (chain-of-thought) can be prompted without tools

### 4.2 PM Reasoning Framework (Prompt-Based)

**PM Prompt Pattern** (intent classification section):

```
**Intent Classification Process**:

1. **Analyze the message**:
   - What is the user explicitly asking for?
   - What media did they provide (if any)?
   - What is the conversation context?

2. **Classify into primary intent**:
   - **catalog_new**: User wants to add new product(s) to catalog
     - Signals: "catalog", "add", "new product", image/video of product
   - **catalog_update**: User wants to modify existing product
     - Signals: "update", "change", references SKU/product ID
   - **inquiry**: User asking question about products/inventory/orders
     - Signals: "what", "how many", "check", "status"
   - **conversational**: Greetings, feedback, general chat
     - Signals: "hi", "hello", "thanks", no clear action request
   - **administrative**: Change settings, view history
     - Signals: "settings", "history", "cancel", "reset"
   - **ambiguous**: Unclear intent, need clarification
     - Signals: Media only with no context, vague text

3. **Handle by intent**:
   - **catalog_new/catalog_update**: Delegate to cataloging_department
   - **inquiry**: Delegate to appropriate department (operations/cataloging)
   - **conversational**: Respond directly with friendly message
   - **administrative**: Delegate to admin department or handle directly
   - **ambiguous**: Ask user for clarification before delegating
```

### 4.3 PM Tool Suite (Minimal)

**Tools PM SHOULD have**:

1. **`task`** (DeepAgents built-in): Delegate to departments
2. **`write_todos`** (DeepAgents built-in): Plan multi-step workflows
3. **That's it!**

**Tools PM should NOT have**:

- ❌ `analyze_user_intent` - LLM does this natively
- ❌ `image_analysis_specialist` - This is department/specialist concern
- ❌ `download_media` - This is channel/department concern
- ❌ `search_products` - This is domain knowledge, belongs in department
- ❌ `save_product` - This is domain execution, belongs in department

**Why minimal tools?**:
- PM's job is **routing**, not **execution**
- Domain knowledge belongs in departments
- PM stays clean, focused, and domain-agnostic
- Scales to new departments without PM changes

---

## 5. Message Flow Architecture

### 5.1 End-to-End Flow

```
Platform (WhatsApp, Email, etc.)
    ↓
    │ Platform-specific payload
    │
Runner (Channel Adapter)
    ↓
    │ 1. Apply platform media strategy (eager/lazy download)
    │ 2. Normalize to IncomingMessage schema
    │ 3. Pass to PM
    │
Project Manager (DeepAgent)
    ↓
    │ 1. Analyze IncomingMessage (text + media metadata)
    │ 2. Classify intent using LLM reasoning
    │ 3. Delegate via `task` tool with semantic description
    │
Department Agent (cataloging_department.py)
    ↓
    │ 1. Receive semantic task description
    │ 2. Access media if needed (already downloaded or via tool)
    │ 3. Delegate to specialists
    │ 4. Execute workflow with HITL
    │ 5. Return structured result
    │
Specialist Agents (image_analysis, cataloging)
    ↓
    │ Execute specific tasks using tools
    │
Tools (storage, LLM, external APIs)
```

### 5.2 Runner Responsibilities (Channel Adapter Layer)

**What Runner MUST do**:

1. **Receive platform-specific payload**
2. **Apply platform media strategy**:
   - WhatsApp/SMS: Download immediately (URLs expire)
   - Telegram/Email/Slack: Store reference only (lazy download)
   - Web: Already have file path
3. **Build IncomingMessage**:
   - Normalize text content
   - Create MediaReference objects with correct download strategy
   - Include platform context
4. **Pass to PM** (via orchestration layer)
5. **Handle PM response**:
   - Send messages back to user via platform
   - Present HITL approval requests
   - Handle errors with user-friendly messages

**What Runner must NOT do**:
- ❌ Tell PM which tools to use
- ❌ Encode domain logic
- ❌ Make routing decisions
- ❌ Analyze media content

**Example - Current Runner (INCORRECT)**:
```python
# runner.py:525 - TOO PRESCRIPTIVE
content = f"{text}\n\n[An image was provided - analyze it using the image_analysis_specialist tool with path: {media_path}]"
```

**Example - Correct Runner**:
```python
# Semantic message, PM decides how to handle
message = IncomingMessage(
    text=text or "",
    media=[MediaReference(
        media_id="whatsapp_123",
        media_type="image",
        local_path=media_path,
        platform="whatsapp",
        download_strategy="eager",
    )],
    platform="whatsapp",
    sender_id=sender,
    thread_id=thread_id,
)

payload = {"messages": [HumanMessage(content=json.dumps(message.model_dump()))]}
```

### 5.3 PM Delegation Examples

**Scenario 1: Image + Text (Clear Cataloging Intent)**

```
User: "Catalog these sneakers, price $79, sizes 7-11"
Media: 1 image

PM receives IncomingMessage:
  text: "Catalog these sneakers, price $79, sizes 7-11"
  media: [1 image reference]

PM reasoning:
  "User explicitly says 'catalog' + provides image → catalog_new intent"

PM action:
  task(
    description="User wants to catalog sneakers. Price: $79. Sizes: 7-11. Image reference: media_123",
    subagent_type="cataloging_department"
  )

Department action:
  1. Sees image reference in task description
  2. Accesses media via local_path (already downloaded)
  3. Calls image_analysis_specialist(image_url=local_path)
  4. Combines analysis with user text
  5. Calls cataloging_specialist → save_product (HITL)
  6. Returns CatalogingResult to PM

PM response to user:
  "Great! I've added 'Canvas Sneakers' to your catalog (ID: 123)."
```

**Scenario 2: Image Only (Ambiguous Intent)**

```
User: [sends image, no text]

PM receives IncomingMessage:
  text: None
  media: [1 image reference]

PM reasoning:
  "Image only, no text → Could be cataloging, inquiry, or just sharing → ambiguous"

PM action (Option A - Ask for clarification):
  Respond directly: "I see you sent an image. Would you like me to catalog this as a new product?"

PM action (Option B - Assume cataloging):
  task(
    description="User sent product image with no additional context. Likely wants to catalog.",
    subagent_type="cataloging_department"
  )

Department action:
  Proceeds with image analysis, may ask user for clarification if needed
```

**Scenario 3: Text Only (Product Inquiry)**

```
User: "What colors do we have for SKU-456?"

PM receives IncomingMessage:
  text: "What colors do we have for SKU-456?"
  media: []

PM reasoning:
  "Question format + 'what colors' + SKU reference → inquiry intent"

PM action:
  task(
    description="User inquiring about available colors for SKU-456",
    subagent_type="cataloging_department"  # Or operations_department
  )

Department action:
  Uses product_search tool to find SKU-456
  Extracts color variants
  Returns structured response

PM response to user:
  "SKU-456 is available in Blue, Red, and Black."
```

**Scenario 4: Multiple Images (Batch Cataloging)**

```
User: "Catalog all of these"
Media: 5 images

PM receives IncomingMessage:
  text: "Catalog all of these"
  media: [5 image references]

PM reasoning:
  "Multiple images + 'catalog all' → catalog_batch intent"

PM action (Option A - Single delegation):
  task(
    description="Batch catalog 5 products. Media references: media_1, media_2, media_3, media_4, media_5",
    subagent_type="cataloging_department"
  )

PM action (Option B - Plan with todos):
  1. write_todos: ["Catalog product 1", "Catalog product 2", ...]
  2. For each product:
     task(description="Catalog product from media_X", subagent_type="cataloging_department")

Department action:
  Handles batch processing internally or processes one at a time
```

---

## 6. Architectural Refinements

### 6.1 Fix: Wire Department as DeepAgents Subagent Model

**Current (INCORRECT)**:
```python
# project_manager.py:56-79
def _build_subagents(company_profile, storage):
    return [{
        "name": "cataloging_department",
        "description": "...",
        "prompt": cataloging_prompt,
        "tools": tools_registry.get_cataloging_tool_objects(storage),  # ← Lightweight bundle
    }]
```

**Problem**: Passing `tools` creates lightweight tool bundle without middleware/HITL. Your full department agent (`cataloging_department.py`) is never used.

**Fix (CORRECT)**:
```python
# project_manager.py
from autifyme_agents.departments.cataloging_department import create_cataloging_department

def _build_subagents(company_profile, storage, checkpointer):
    """Build subagents as FULL department agents."""

    # Create full department agent
    cataloging_dept_agent = create_cataloging_department(
        checkpointer=checkpointer,
        storage=storage,
        enable_hitl=True,
    )

    return [{
        "name": "cataloging_department",
        "description": "Handles product cataloging (images, text, batch). Delegate when user provides product information.",
        "prompt": "",  # Prompt already in agent
        "model": cataloging_dept_agent,  # ← Pass FULL agent as model
        "tools": [],  # Tools already in agent
    }]
```

**Key Discovery**: DeepAgents SubAgent `model` parameter accepts `CompiledStateGraph` (full LangChain agent). This preserves middleware, HITL, checkpointing.

### 6.2 Fix: Remove PM Direct Tool Access

**Current (INCORRECT)**:
```python
# project_manager.py:114
pm_tools = list(tools) if tools is not None else []
pm_tools.append(tools_registry.create_image_analysis_tool(storage))  # ← WRONG
```

**Problem**: PM has direct access to `image_analysis_specialist`, breaking hierarchy.

**Fix (CORRECT)**:
```python
# project_manager.py
def create_project_manager(...):
    # PM gets NO domain tools - only orchestration
    pm_tools = []  # Or: list(tools) if tools else [] for future orchestration tools

    # Subagents ARE the departments (full agents with all tools)
    subagents = _build_subagents(company_profile, storage, checkpointer)

    # No tool_configs needed - departments handle their own HITL

    project_manager = create_deep_agent(
        tools=pm_tools,
        instructions=instructions,
        model=llm,
        subagents=subagents,
        tool_configs={},  # Empty - HITL at department level
        checkpointer=checkpointer,
    )
```

### 6.3 Fix: Update Runner to Pass Semantic Messages

**Current (INCORRECT)**:
```python
# runner.py:_build_payload
content = f"{text}\n\n[An image was provided - analyze it using the image_analysis_specialist tool with path: {media_path}]"
```

**Problem**: Prescriptive instructions, tight coupling to cataloging workflow.

**Fix (CORRECT)**:
```python
# runner.py:_build_payload
def _build_payload(self, text: str | None, media_path: Path | None) -> dict[str, Any]:
    """Build semantic PM payload with IncomingMessage structure."""

    media_refs = []
    if media_path and media_path.exists():
        media_refs.append({
            "media_id": f"local_{media_path.stem}",
            "media_type": "image",  # Detect from extension
            "mime_type": "image/jpeg",  # Detect from file
            "platform": self.channel.__class__.__name__.lower().replace("adapter", ""),
            "download_strategy": "eager",
            "local_path": str(media_path),
        })

    incoming_msg = {
        "text": text or "",
        "media": media_refs,
        "platform": "whatsapp",  # Get from channel
        "sender_id": "...",
        "thread_id": "...",
        "timestamp": datetime.now().isoformat(),
    }

    # Option 1: Structured data in message
    content = f"User message: {text or '(no text)'}"
    if media_refs:
        content += f"\nMedia: {len(media_refs)} file(s) attached"

    return {
        "messages": [HumanMessage(
            content=content,
            additional_kwargs={"incoming_message": incoming_msg}
        )]
    }
```

### 6.4 PM Prompt Update (Intent-Focused)

See Section 4.2 for full prompt pattern. Key changes:

- Focus on **intent classification** (not tool prescription)
- Describe **what user wants** (not how to execute)
- Delegate with **semantic descriptions** (not tool instructions)
- Handle **ambiguity** explicitly (ask clarification)

---

## 7. Scaling to Future Platforms & Media Types

### 7.1 Adding New Platform (e.g., Telegram)

**Steps**:

1. Create channel adapter: `workflows/channels/telegram/adapter.py`
2. Implement `MessagingChannel` protocol
3. Apply platform media strategy (lazy for Telegram)
4. Normalize to `IncomingMessage` schema
5. Route through existing Runner → PM → Departments

**No PM changes needed** - PM already handles all message types via IncomingMessage.

### 7.2 Adding New Media Type (e.g., Voice Notes)

**Steps**:

1. Add `"voice"` to `MediaReference.media_type` enum
2. Update platform adapter to handle voice messages
3. Create specialist if needed: `audio_transcription_specialist`
4. Add specialist to cataloging department tools
5. Update department prompt to handle voice descriptions

**PM changes needed**: Minimal - PM already handles arbitrary media via MediaReference.

### 7.3 Adding New Intent (e.g., Marketing Campaign)

**Steps**:

1. Create `marketing_department.py` (similar to cataloging)
2. Add department as PM subagent in `_build_subagents`
3. Update PM prompt to recognize marketing intent
4. PM delegates: `task(description="...", subagent_type="marketing_department")`

**Scalability**: PM prompt can be extended with new intent patterns without code changes.

---

## 8. Implementation Checklist

### Phase 1: Core Fixes (Immediate)

- [ ] Fix logging date format bug (`logging_config.py:69`)
- [ ] Fix test context manager bug (`test_cataloging_workflow.py:66`)
- [ ] Wire cataloging_department as SubAgent `model` (`project_manager.py:_build_subagents`)
- [ ] Remove PM direct tool access (`project_manager.py:114`)
- [ ] Update PM prompt for intent classification (see Section 4.2)

### Phase 2: Message Normalization (Next Sprint)

- [ ] Define `IncomingMessage` and `MediaReference` schemas (`schemas/messages.py`)
- [ ] Update Runner to build `IncomingMessage` (`runner.py:_build_payload`)
- [ ] Update PM to parse `IncomingMessage` from payload
- [ ] Test end-to-end with WhatsApp

### Phase 3: Multi-Platform Support (Future)

- [ ] Implement Telegram adapter with lazy download
- [ ] Implement Email adapter with lazy download
- [ ] Implement Web adapter (no download needed)
- [ ] Test all platforms with same PM

### Phase 4: Advanced Intent Handling (Future)

- [ ] Add multi-step workflow support (PM uses `write_todos`)
- [ ] Add cross-department coordination (catalog + marketing)
- [ ] Add ambiguity handling (PM asks clarification)
- [ ] Add conversation context awareness

---

## 9. Testing Strategy

### Unit Tests

- `test_incoming_message_schema`: Validate IncomingMessage serialization
- `test_media_reference_schema`: Validate MediaReference for all platforms
- `test_runner_normalization`: Test runner converts platform payloads to IncomingMessage

### Integration Tests

- `test_pm_intent_classification`: Test PM correctly classifies all intent scenarios
- `test_pm_delegation`: Test PM delegates to correct departments
- `test_end_to_end_whatsapp`: Test WhatsApp → Runner → PM → Department
- `test_multi_platform`: Test same PM with different platform adapters

### Scenario Tests (Critical Scenarios from Section 1.2)

Each of the 9 critical scenarios should have an E2E test validating correct behavior.

---

## 10. Open Questions & Decisions Needed

1. **Ambiguous intent handling**: Should PM ask clarification or make best guess?
   - **Recommendation**: Ask clarification for truly ambiguous cases (e.g., image only)

2. **Batch processing strategy**: Should PM create todos for each item, or delegate batch to department?
   - **Recommendation**: Delegate batch to department - department knows how to handle efficiently

3. **Media preview for routing**: Should PM have `preview_media_content` tool to glance at media before routing?
   - **Recommendation**: No - routing based on media metadata is sufficient

4. **Conversation context**: Should `IncomingMessage` include recent conversation history?
   - **Recommendation**: Optional field, populate if available from checkpointer

---

## Summary

**Core Principles**:

1. **PM receives semantic, normalized messages** (IncomingMessage schema)
2. **PM uses LLM reasoning** for intent classification (no tool-based analysis)
3. **PM has minimal tools** (task, write_todos only)
4. **Media handling is platform-specific** (eager/lazy/none strategies)
5. **Departments are full agents** (wired as SubAgent `model`, not tools)
6. **HITL stays at department level** (PM never sees approval complexity)
7. **Architecture scales** to new platforms, media types, and departments

**Next Steps**: Implement Phase 1 fixes, validate with E2E test, document learnings.
