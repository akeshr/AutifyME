# Comprehensive CLI Testing Framework Design

**Date**: 2025-10-11
**Status**: 🔬 RESEARCH & DESIGN
**Purpose**: Make simulate CLI the ultimate testing partner for all permutations and combinations

---

## Critical Bug Discovered

### WhatsApp Caption Loss Bug 🐛

**Location**: `entrypoints/whatsapp_webhook.py:222, 266-267`

**Issue**: When user sends image with caption on WhatsApp, caption is lost.

```python
# Current code (BROKEN):
text = message.get("text", {}).get("body")  # ← Only gets text from text messages
if msg_type == "image":
    media_id = message.get("image", {}).get("id")  # ← Gets media_id but NO caption
```

**WhatsApp API Structure** (from Meta documentation):
```json
{
  "type": "image",
  "image": {
    "caption": "Catalog this product, price $79",  // ← LOST!
    "id": "592623615738103",
    "mime_type": "image/jpeg",
    "sha256": "..."
  }
}
```

**Impact**: Users cannot send image + description in one message (common real-world usage).

**Fix Required**:
```python
# Extract caption from media object based on message type
text = None
media_id = None

if msg_type == "text":
    text = message.get("text", {}).get("body")
elif msg_type == "image":
    media_id = message.get("image", {}).get("id")
    text = message.get("image", {}).get("caption")  # ← EXTRACT CAPTION
elif msg_type == "video":
    media_id = message.get("video", {}).get("id")
    text = message.get("video", {}).get("caption")
elif msg_type == "document":
    media_id = message.get("document", {}).get("id")
    text = message.get("document", {}).get("caption")
elif msg_type == "audio" or msg_type == "voice":
    media_id = message.get(msg_type, {}).get("id")
    # Audio/voice typically don't have captions
```

---

## Current CLI Capabilities vs. Gaps

### ✅ Current Capabilities

**simulate.py**:
- Text + image testing
- Auto-approve mode
- Predefined scenarios
- ConsoleChannel adapter
- Basic HITL approval (yes/no)
- Elapsed time tracking
- Windows emoji fallback

**pm_chat.py**:
- Direct PM testing
- Interactive mode
- Image support
- Fast iteration

### ❌ Critical Gaps

1. **No media+caption handling** - Can't simulate real WhatsApp usage
2. **No approval variations** - Only approve/reject, no edits/questions/defer/park
3. **No multi-turn conversations** - Can't test conversation continuity
4. **No error injection** - Can't test error recovery
5. **No state inspection** - Can't debug checkpoint state
6. **No checkpoint navigation** - Can't resume from specific states
7. **No permutation testing** - Can't systematically test all combinations
8. **No scenario recording** - Can't capture real WhatsApp flows for replay
9. **No performance testing** - Can't measure latency patterns
10. **No approval timeout testing** - Can't test 24h expiration

---

## Comprehensive Testing Framework Architecture

### Design Principles

1. **Exhaustive Coverage**: Test ALL permutations systematically
2. **Real-World Scenarios**: Simulate actual user behavior patterns
3. **Debugging-Friendly**: Inspect state at any point
4. **Reproducible**: Deterministic scenarios
5. **Fast**: Quick iteration for development
6. **Observable**: Rich logging and state inspection
7. **Extensible**: Easy to add new scenarios

---

## Part 1: Message Permutations Matrix

### Message Type Combinations (84 scenarios)

**Axes**:
- Message Type: text | image | video | audio | voice | document (6)
- With/Without Caption: 2 variants (only for image/video/document)
- Content Clarity: clear | ambiguous | minimal (3)
- HITL State: none | pending | expired (3)

**Matrix**:
```
Text Messages (12 scenarios):
1. text + clear + no_hitl
2. text + clear + pending_hitl
3. text + clear + expired_hitl
4. text + ambiguous + no_hitl
5. text + ambiguous + pending_hitl
6. text + ambiguous + expired_hitl
7. text + minimal + no_hitl
8. text + minimal + pending_hitl
9. text + minimal + expired_hitl
10. text + empty + no_hitl
11. text + empty + pending_hitl
12. text + empty + expired_hitl

Image Messages (36 scenarios):
13-24. image + no_caption + (clear/ambiguous/minimal/empty) × (no_hitl/pending/expired)
25-36. image + caption + (clear/ambiguous/minimal/empty) × (no_hitl/pending/expired)

Video Messages (36 scenarios):
37-48. video + no_caption + variations
49-60. video + caption + variations

Document Messages (18 scenarios):
61-72. document + no_caption + variations
73-84. document + caption + variations

Audio/Voice Messages (12 scenarios):
85-96. audio/voice + variations (no captions)
```

---

## Part 2: HITL Approval Permutations (56 scenarios)

### Approval Intent Matrix

**User Response Types**:
1. **Direct Approval**: "approve", "yes", "looks good", "perfect", "go ahead"
2. **Direct Rejection**: "reject", "no", "don't save", "cancel"
3. **Approval with Edits**: "approve but change price to $25", "yes, fix the color to blue"
4. **Questions**: "what's the sku?", "can you show me the image again?"
5. **Defer**: "remind me later", "not now", "let me check first"
6. **Park**: "save this for review", "park this"
7. **Abandon**: "forget it", "cancel everything", "start over"
8. **Ambiguous**: "maybe", "hmm", "not sure"

**Approval State Variations**:
- Fresh approval (< 1min old)
- Stale approval (> 1h old, < 24h)
- Expired approval (> 24h)
- No pending approval

**Combined Scenarios** (8 intents × 4 states = 32 base scenarios)

Plus variations:
- **Multi-field edits**: "change price to $25 and color to blue"
- **Partial edits**: "just fix the name"
- **Natural language**: "looks good to me!", "nah, skip it"
- **Follow-up questions**: After approval, user asks "did it save?"
- **Context switch**: During approval, user sends new catalog request

**Total HITL Scenarios**: ~56

---

## Part 3: Workflow Permutations (48 scenarios)

### Workflow Path Matrix

**Intents**:
1. Cataloging (24 scenarios)
2. Inquiry (8 scenarios)
3. Conversational (8 scenarios)
4. Unknown/Ambiguous (8 scenarios)

**Cataloging Variations**:
- text + image → HITL → approve → success
- text + image → HITL → reject → abandoned
- text + image → HITL → edit → success
- text only → HITL → approve → success
- image only → clarification → text → HITL → approve → success
- batch images → multi-HITL → approve all → success
- batch images → multi-HITL → approve some/reject some
- missing required fields → PM asks → user provides → HITL → approve
- (repeat for video, document, audio)

**Error Scenarios**:
- Media download failure
- Image analysis failure
- Specialist timeout
- PM recursion limit
- Database connection failure
- Checkpoint corruption
- Network timeout during HITL

---

## Part 4: State Management Permutations (24 scenarios)

### Checkpoint Navigation

**Test Scenarios**:
1. **Normal flow**: message → process → HITL → approve → complete
2. **Resume after timeout**: message → HITL → [timeout 10min] → approve → resume
3. **Resume after restart**: message → HITL → [server restart] → approve → resume
4. **Multi-user isolation**: user1 HITL, user2 message, user1 approve (no cross-contamination)
5. **Conversation continuity**: message1 → response1 → message2 (with context)
6. **Checkpoint rollback**: corrupt checkpoint → detect → recover
7. **Namespace isolation**: PM checkpoint vs. department checkpoint
8. **Concurrent workflows**: same user, multiple threads

---

## Part 5: Enhanced CLI Features Design

### Feature 1: Scenario Recording & Replay

**Purpose**: Capture real WhatsApp interactions for local replay

```bash
# Capture mode (from WhatsApp webhook events)
uv run python -m autifyme_agents.cli.capture --event /tmp/whatsapp_events/event_20251011T120000Z.json

# Replay mode
uv run python -m autifyme_agents.cli.simulate --replay scenarios/recorded/customer_123_cataloging.json

# Batch replay
uv run python -m autifyme_agents.cli.simulate --replay-all scenarios/recorded/
```

**Scenario JSON Format**:
```json
{
  "name": "Customer cataloging with edit",
  "description": "Real user flow: image+caption → HITL → edit → approve",
  "steps": [
    {
      "type": "message",
      "sender": "test_user_123",
      "text": "Catalog these sneakers, price $79",
      "media_id": "tests/fixtures/images/sneaker.jpg",
      "media_type": "image"
    },
    {
      "type": "await_approval",
      "timeout_seconds": 5
    },
    {
      "type": "approval_response",
      "decision": "approve_with_edits",
      "edits": {
        "price": 89.99
      }
    },
    {
      "type": "assert_completion",
      "expected_success": true
    }
  ]
}
```

### Feature 2: Interactive Debugger

**Purpose**: Step through workflow, inspect state at each step

```bash
# Debug mode
uv run python -m autifyme_agents.cli.simulate "Catalog sneakers" --debug

# Commands in debug mode:
# > step       - Execute next step
# > continue   - Run to next breakpoint
# > state      - Show current state
# > checkpoint - Show checkpoint data
# > messages   - Show message history
# > breakpoint on_hitl - Set breakpoint at HITL
# > inspect draft - Show approval draft
# > edit draft.price 99.99 - Modify state
# > resume     - Continue from current state
```

### Feature 3: Permutation Test Generator

**Purpose**: Systematically test all combinations

```bash
# Generate and run all permutation tests
uv run python -m autifyme_agents.cli.permutation_test \
  --message-types text,image,video \
  --content-clarity clear,ambiguous \
  --hitl-responses approve,reject,edit \
  --auto-run

# Output: Test report with pass/fail for each permutation
```

### Feature 4: HITL Variations Testing

**Purpose**: Test all approval response patterns

```bash
# Test specific HITL scenario
uv run python -m autifyme_agents.cli.simulate "Catalog sneakers" \
  --hitl-mode interactive_edit \
  --hitl-response "approve but change price to $25"

# Test all HITL variations
uv run python -m autifyme_agents.cli.simulate --scenario cataloging_basic \
  --test-all-hitl-variations
```

### Feature 5: Error Injection

**Purpose**: Test error recovery paths

```bash
# Inject errors at specific points
uv run python -m autifyme_agents.cli.simulate "Catalog sneakers" \
  --inject-error media_download_failure \
  --at-step 2

# Test error recovery
uv run python -m autifyme_agents.cli.simulate "Catalog sneakers" \
  --inject-error specialist_timeout \
  --expect-recovery
```

### Feature 6: Performance Testing

**Purpose**: Measure latency patterns

```bash
# Run with performance profiling
uv run python -m autifyme_agents.cli.simulate "Catalog sneakers" \
  --profile \
  --report performance_report.json

# Load testing
uv run python -m autifyme_agents.cli.load_test \
  --scenario cataloging_basic \
  --concurrent-users 10 \
  --duration 60s
```

### Feature 7: Multi-Turn Conversation Testing

**Purpose**: Test conversation continuity and context

```bash
# Multi-turn conversation script
uv run python -m autifyme_agents.cli.conversation \
  --script scenarios/conversation_cataloging_clarification.yaml

# YAML format:
# - user: "Catalog this"
#   media: tests/fixtures/images/product.jpg
#   expect: clarification_request
# - user: "It's a t-shirt, price $29"
#   expect: hitl_approval
# - user: "approve"
#   expect: cataloging_success
```

---

## Part 6: Implementation Plan

### Phase 1: Fix Critical Bug (Day 1) ⚡ URGENT

**Files**:
- `entrypoints/whatsapp_webhook.py` - Extract caption from all media types
- `workflows/orchestration/runner.py` - Ensure caption passed to PM

**Test**: Send WhatsApp image with caption → verify caption received

### Phase 2: Enhanced simulate CLI (Days 2-3)

**Files**:
- `cli/simulate.py` - Add features:
  - Media+caption support
  - Multi-turn conversations
  - HITL variations (approve/reject/edit/question/defer)
  - State inspection commands
  - Scenario recording/replay
  - Enhanced ConsoleChannel with caption support

**Test**: Run all existing scenarios + new variations

### Phase 3: Permutation Test Framework (Days 4-5)

**Files**:
- `cli/permutation_test.py` - Generate and run all permutations
- `tests/permutations/` - Test matrices
- `tests/permutations/message_matrix.py` - Message type combinations
- `tests/permutations/hitl_matrix.py` - HITL response combinations
- `tests/permutations/workflow_matrix.py` - Workflow path combinations

**Test**: Run full permutation suite → 100% pass rate

### Phase 4: Debug & Inspection Tools (Days 6-7)

**Files**:
- `cli/debug_simulator.py` - Interactive debugger
- `cli/checkpoint_inspector.py` - Checkpoint navigation tool
- `cli/state_viewer.py` - Visual state inspection

**Test**: Debug complex scenarios, inspect state at each step

### Phase 5: Performance & Load Testing (Days 8-9)

**Files**:
- `cli/performance_test.py` - Latency profiling
- `cli/load_test.py` - Concurrent user simulation

**Test**: Identify bottlenecks, optimize critical paths

### Phase 6: Scenario Library (Day 10)

**Files**:
- `scenarios/recorded/` - Real WhatsApp flows captured
- `scenarios/generated/` - Permutation-generated scenarios
- `scenarios/regression/` - Critical regression tests

**Test**: Replay all scenarios → validate no regressions

---

## Success Criteria

**Phase 1**:
- ✅ WhatsApp caption extraction works
- ✅ All media types (image/video/document) preserve captions
- ✅ Manual WhatsApp test: image+caption → cataloging with text

**Phase 2**:
- ✅ simulate CLI supports all media types + captions
- ✅ Multi-turn conversation testing works
- ✅ HITL variations (approve/reject/edit/question) all work
- ✅ State inspection shows checkpoint data

**Phase 3**:
- ✅ All 84 message permutations pass
- ✅ All 56 HITL permutations pass
- ✅ All 48 workflow permutations pass
- ✅ Automated test report generation

**Phase 4**:
- ✅ Can step through any workflow
- ✅ Can inspect state at any point
- ✅ Can resume from any checkpoint

**Phase 5**:
- ✅ Latency < 3s for 95th percentile
- ✅ Can handle 10 concurrent users
- ✅ No memory leaks in long-running tests

**Phase 6**:
- ✅ 50+ recorded real-world scenarios
- ✅ All scenarios replay successfully
- ✅ Regression suite runs in < 5min

---

## Key Architectural Decisions

1. **Scenario Format**: JSON for portability, YAML for human editing
2. **Channel Abstraction**: ConsoleChannel implements full MessagingChannel protocol
3. **State Inspection**: Direct checkpoint reading, not mocked
4. **Error Injection**: Middleware-based, not code modifications
5. **Permutation Generation**: Combinatorial, not manual enumeration
6. **Performance Testing**: Async concurrent execution, real checkpointer
7. **Replay Fidelity**: Byte-for-byte WhatsApp webhook structure

---

## Related Documents

- `LOCAL_TESTING_STRATEGY.md` - Current testing approach
- `APPROVAL_FIX_SUMMARY.md` - HITL bug fix
- `AGENTIC_APPROVAL_DESIGN.md` - Approval permutations
- `PM_INTENT_ANALYSIS_AND_MESSAGE_HANDLING.md` - Message handling
- `WHATSAPP_CATALOGING_WORKFLOW.md` - Current workflow

---

## Next Immediate Action

**Fix WhatsApp caption bug FIRST** - This is blocking real-world usage.

After that, implement enhanced CLI systematically through the phases above.
