# Media Download Architecture - Critical Issues & Fixes

**Date**: 2025-10-13
**Status**: CRITICAL - Production Impact
**Run Analyzed**: f10f60c8-46c6-4af6-81c8-eb767de1afef

---

## Executive Summary

Three critical issues discovered in media handling architecture:

1. **90% token waste** - Intent specialist consuming 165K of 183K tokens
2. **Wrong responsibility** - Intent specialist downloading media it doesn't need
3. **Validation errors** - MediaReference schema mismatch causing failures

**Impact**: Unnecessary costs, slower response times, occasional failures

---

## Issue #1: Massive Token Waste (90% of workflow)

### Evidence
```
Total workflow tokens: 183,517
Intent specialist tokens: 165,469 (90%!)
```

### Root Cause

**Intent specialist receives FULL conversation history every invocation:**
- Message 1: Greeting → 6K tokens
- Message 2: Media message + history (greeting) → 14K tokens
- Message 3: Status query + history (greeting + media) → 24K tokens
- Message 7: "Catalogue" + media + ALL HISTORY → 50K+ tokens

**Growth Pattern**: Linear message growth → Exponential token growth

### Why This Happens

PM invokes intent specialist on EVERY message:
```python
# PM receives message
interpret_incoming_message(raw_message)  # Gets full conv history from context

# Intent specialist sees:
messages = [
    HumanMessage(...),  # Original greeting
    AIMessage(...),     # PM response
    HumanMessage(...),  # Media message
    AIMessage(...),     # PM response
    ... [all conversation history]
    HumanMessage(...)   # Current message <-- Only this matters for intent!
]
```

**The Waste**: Intent detection doesn't need full conversation history to classify a single message.

---

## Issue #2: Media Download in Wrong Place

### Current (Broken) Architecture

```
User sends media_id="xyz"
    ↓
Runner → PM
    ↓
PM calls interpret_incoming_message(media_id="xyz")
    ↓
MessageIntentSpecialist calls download_whatsapp_media("xyz")
    ↓
Downloads to /tmp/media_downloads/xyz.jpg
    ↓
Returns: MessageInterpretation{
    media: [{local_path: "/tmp/...", original_id: "xyz"}],
    intent: "new_request"
}
    ↓
PM delegates to cataloging_department
    ↓
Department needs image for analysis
    ↓
❌ PROBLEM: Department doesn't have the downloaded path!
    ↓
Department downloads AGAIN (or fails because path isn't passed)
```

### Why This Is Wrong

**Intent Specialist Doesn't Need The File:**
- Intent classification: "User sent media" (yes/no) + "cataloging keywords"
- Doesn't need to open the file
- Doesn't analyze pixels
- Just needs to know `has_media: true`

**Agents Who DO Need The File:**
- ImageAnalysisSpecialist: Needs pixels to extract colors/style
- CatalogingSpecialist: Might need visual confirmation
- These agents currently don't get the downloaded path from intent specialist

### Token Waste From Media Passing

Intent specialist output with media:
```json
{
  "intent": "new_request",
  "media": [
    {
      "media_type": "image/jpeg",
      "local_path": "/tmp/media_downloads/20251013_113030_680196154682467.jpg",
      "original_id": "680196154682467",
      "mime_type": "image/jpeg",
      "size_bytes": 1070
    }
  ],
  "reasoning": "User sent media..."
}
```

**This gets serialized into PM's conversation history** → hundreds of extra tokens per message with media!

---

## Issue #3: Validation Error

### The Error
```
Failed to parse data to MessageIntentSpecialist failed to interpret message: Failed to parse data to MessageInterpretation:
1 validation error for MediaReference
media.0.original_id
  Field required [type=missing]
```

### Root Cause

**MediaReference schema** (message_intent.py:15):
```python
class MediaReference(BaseModel):
    media_type: str
    local_path: str
    original_id: str  # REQUIRED
    mime_type: str | None = None
    size_bytes: int | None = None
```

**download_media tool returns** (platform_tools.py:54):
```python
return str(media_path)  # Just the path string!
```

**MessageIntentSpecialist constructs**:
```python
{
    "media_type": "image/jpeg",
    "local_path": "/tmp/...",
    # Missing original_id!
}
```

**Result**: Pydantic validation fails because `original_id` is required but not populated.

---

## The Right Architecture

### Principle: **Download Where You Need It**

```
User sends media_id="xyz"
    ↓
Runner → PM
    ↓
PM calls interpret_incoming_message(media_id="xyz")
    ↓
MessageIntentSpecialist (NO DOWNLOAD):
    - Sees media_id in raw message
    - Classifies intent: "new_request"
    - Returns: {
        intent: "new_request",
        has_media: true,
        request_data: {media_id: "xyz"}  # Pass ID downstream
      }
    ↓
PM delegates to cataloging_department(media_id="xyz")
    ↓
Department calls image_analysis_specialist(media_id="xyz")
    ↓
ImageAnalysisSpecialist downloads when needed:
    - Has download tool
    - Downloads once
    - Uses immediately
    - No path passing through context
```

### Benefits

1. **90% token reduction** in intent classification
2. **Single download** per media item (not 2-3x)
3. **No path serialization** through conversation history
4. **Cleaner separation of concerns**
5. **Agents download only what they need**

---

## Implementation Plan

### Step 1: Remove Media Download from Intent Specialist

**File**: `agents/src/autifyme_agents/tools/message_intent_tool.py`

```python
# Before
platform_tools = create_platform_media_tools(channel)
message_intent_tool = create_message_intent_tool(channel, platform_tools)

# After
message_intent_tool = create_message_intent_tool(channel, platform_tools=[])
```

**File**: `agents/src/autifyme_agents/specialists/message_intent_specialist.py`

Update prompt to remove media download instructions.

### Step 2: Update MessageInterpretation Schema

**File**: `agents/src/autifyme_agents/schemas/message_intent.py`

```python
# Before
media: list[MediaReference] = Field(
    default_factory=list,
    description="Downloaded media files if present in message"
)

# After
media: list[MediaReference] = Field(
    default_factory=list,
    description="DEPRECATED - use media_id in request_data instead"
)

# Add
request_data: dict[str, Any] = Field(
    default_factory=dict,
    description="Extracted data including media_id if present"
)
```

### Step 3: Give Download Tools to Image Analysis Specialist

**File**: `agents/src/autifyme_agents/departments/cataloging_department.py`

```python
def create_cataloging_department(..., channel: MessagingChannel):
    # Create platform-specific download tools
    from autifyme_agents.tools.platform_tools import create_platform_media_tools
    platform_tools = create_platform_media_tools(channel)

    # Add to department tools
    department_tools = [
        ...existing tools...,
        *platform_tools  # Media download available to department
    ]
```

### Step 4: Update Image Analysis Specialist to Accept media_id

**File**: `agents/src/autifyme_agents/specialists/image_analysis_specialist.py`

```python
# Before
def image_analysis_specialist_invoke(
    image_url: str | None = None,
    image_bytes: bytes | None = None,
    ...
)

# After
def image_analysis_specialist_invoke(
    image_url: str | None = None,
    image_bytes: bytes | None = None,
    media_id: str | None = None,  # NEW
    channel: MessagingChannel | None = None,  # NEW
    ...
):
    # If media_id provided, download it
    if media_id and channel:
        image_path = channel.download_media(media_id)
        image_url = str(image_path)
```

### Step 5: Update Cataloging Department to Pass media_id

**File**: Department orchestration logic

```python
# Extract media_id from request_data
media_id = request_data.get("media_id")

if media_id:
    # Pass to image analysis
    image_analysis = image_analysis_specialist(
        media_id=media_id,
        channel=channel
    )
```

---

## Expected Impact

### Token Reduction
- **Before**: 165K tokens for intent classification (7 messages)
- **After**: ~15K tokens for intent classification (7 messages)
- **Savings**: 150K tokens (90% reduction)

### Download Efficiency
- **Before**: 2-3 downloads per media (intent + department + specialist)
- **After**: 1 download per media (only where needed)

### Cleaner Architecture
- Intent specialist: Pure classification (no side effects)
- Specialists: Download what they need, when they need it
- No path serialization through conversation history

---

## Testing Strategy

1. **Local test** with `simulate` CLI:
   - Media-only message
   - Text + media message
   - Verify single download
   - Check token usage in LangSmith

2. **WhatsApp integration test**:
   - Send image
   - Verify cataloging works
   - Check LangSmith tokens

3. **Regression test**:
   - Text-only messages (no media)
   - Multi-turn conversations
   - Approval workflows

---

## Rollback Plan

If issues arise:
1. Revert Step 1 (re-add platform_tools to intent specialist)
2. Keep other improvements (they're additive)
3. Media download temporarily duplicated but functional

---

## See Also

- `AGENTS_DESIGN.md` - Separation of concerns
- `PROMPT_DESIGN_PRINCIPLES.md` - Responsibility clarity
- `WHATSAPP_CATALOGING_WORKFLOW.md` - End-to-end flow
