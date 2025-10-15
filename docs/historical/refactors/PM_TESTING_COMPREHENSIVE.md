# PM-Only Architecture: Comprehensive Testing Plan

**Date:** 2025-10-14
**Goal:** Validate PM handles intent detection, batch approval, HITL interrupts, and multi-step workflows

---

## Test Environment Setup

```bash
# Ensure dependencies installed
cd C:\Abhi\personal\self\AutifyME
uv venv
.venv\Scripts\activate
uv pip install -e "agents[dev]"

# Set environment variables
# Ensure .env has:
# - DATABASE_URL
# - SUPABASE_URL, SUPABASE_ANON_KEY
# - OPENAI_API_KEY
# - LANGSMITH_API_KEY
```

---

## Test Suite Overview

| Category | Scenarios | Priority |
|----------|-----------|----------|
| Intent Detection | 6 scenarios | P0 |
| Media Handling | 3 scenarios | P0 |
| HITL Interrupts | 5 scenarios | P0 |
| Batch Approval | 4 scenarios | P0 |
| Multi-Product | 3 scenarios | P1 |
| Error Handling | 4 scenarios | P1 |
| Edge Cases | 3 scenarios | P2 |

**Total: 28 test scenarios**

---

## P0: Intent Detection (PM Internal)

### Test 1.1: New Product Request (Text + Media)
**Input:**
```json
{
  "platform": "whatsapp",
  "sender": "917258067800",
  "text": "catalog this jar 500ml 30rs",
  "media_id": "test_media_123",
  "timestamp": "2025-10-14T10:00:00"
}
```

**Expected PM Behavior:**
1. Detects `intent = new_request`
2. Extracts: `{product_text: "jar 500ml 30rs", media_id: "test_media_123"}`
3. Calls `download_whatsapp_media("test_media_123")`
4. Delegates to cataloging_department with media path

**Success Criteria:**
- ✓ PM classifies as new_request
- ✓ Media downloaded before delegation
- ✓ Task description includes media path
- ✓ No errors in trace

---

### Test 1.2: Text-Only Product Request
**Input:**
```json
{
  "platform": "whatsapp",
  "sender": "917258067800",
  "text": "add product: cotton shirt blue 299rs",
  "media_id": null,
  "timestamp": "2025-10-14T10:05:00"
}
```

**Expected PM Behavior:**
1. Detects `intent = new_request`
2. Extracts: `{product_text: "cotton shirt blue 299rs"}`
3. NO media download call
4. Delegates to cataloging_department with text only

**Success Criteria:**
- ✓ PM classifies as new_request
- ✓ No media download attempted
- ✓ Task description includes product text
- ✓ Department receives description

---

### Test 1.3: Resume Workflow (User Approval)
**State Setup:**
```python
pending_interrupts = [
    {
        "interrupt_id": "int_123",
        "tool_name": "create_product",
        "tool_args": {"name": "Jar 500ml", "price": 30},
        "description": "Product draft: Jar 500ml @ 30 Rs"
    }
]
```

**Input:**
```json
{
  "platform": "whatsapp",
  "sender": "917258067800",
  "text": "yes",
  "media_id": null,
  "timestamp": "2025-10-14T10:10:00"
}
```

**Expected PM Behavior:**
1. Checks `state["pending_interrupts"]` → found 1 interrupt
2. Detects `intent = resume_workflow`
3. Interprets "yes" → approve
4. Builds: `[{"type": "accept", "args": None}]`
5. Outputs: `COMMAND: {"resume": [{"type": "accept"}]}`

**Success Criteria:**
- ✓ PM detects pending interrupt
- ✓ PM classifies as resume_workflow
- ✓ PM builds correct Command structure
- ✓ Runner parses and resumes

---

### Test 1.4: Clarification Request
**Input:**
```json
{
  "platform": "whatsapp",
  "sender": "917258067800",
  "text": "what can you do?",
  "media_id": null,
  "timestamp": "2025-10-14T10:15:00"
}
```

**Expected PM Behavior:**
1. Detects `intent = clarification`
2. Responds with capability summary
3. No delegation to departments

**Success Criteria:**
- ✓ PM classifies as clarification
- ✓ PM responds directly (no task call)
- ✓ Response explains capabilities

---

### Test 1.5: Greeting
**Input:**
```json
{
  "platform": "whatsapp",
  "sender": "917258067800",
  "text": "namaste",
  "media_id": null,
  "timestamp": "2025-10-14T10:20:00"
}
```

**Expected PM Behavior:**
1. Detects `intent = greeting`
2. Responds warmly
3. No delegation

**Success Criteria:**
- ✓ PM classifies as greeting
- ✓ Warm acknowledgment
- ✓ No task calls

---

### Test 1.6: Off-Topic
**Input:**
```json
{
  "platform": "whatsapp",
  "sender": "917258067800",
  "text": "what's the weather today?",
  "media_id": null,
  "timestamp": "2025-10-14T10:25:00"
}
```

**Expected PM Behavior:**
1. Detects `intent = off_topic`
2. Politely redirects to cataloging

**Success Criteria:**
- ✓ PM classifies as off_topic
- ✓ Redirect message sent
- ✓ No task calls

---

## P0: HITL Interrupt Handling

### Test 2.1: Single Interrupt → Single Approval
**Flow:**
1. User sends: "catalog jar 500ml 30rs"
2. PM delegates to cataloging_department
3. Department creates product draft
4. HITL middleware calls `interrupt([request1])`
5. Runner sends approval request to user
6. User responds: "approve"
7. PM builds: `[{"type": "accept"}]`
8. Runner resumes with Command
9. Product saved

**Success Criteria:**
- ✓ Interrupt detected
- ✓ Approval request sent
- ✓ PM interprets "approve" correctly
- ✓ Command resume succeeds
- ✓ Product saved to DB

---

### Test 2.2: **CRITICAL** - Batch Approval (2 Interrupts)
**Flow:**
1. User sends: "Create two variants: 500ml @ 30 Rs, 1L @ 50 Rs"
2. PM creates write_todos with 2 tasks
3. PM delegates FIRST task only
4. Department creates product draft #1
5. HITL interrupt #1
6. User approves #1
7. PM delegates SECOND task
8. Department creates product draft #2
9. HITL interrupt #2
10. User approves #2

**Alternative (if PM makes parallel calls by mistake):**
1-2. Same
3. PM delegates TWO tasks in parallel
4. Department makes 2 create_product calls
5. HITL middleware sees 2 tool calls → `interrupt([req1, req2])`
6. Runner sends approval request showing BOTH products
7. User responds: "approve both"
8. PM sees: `pending_interrupts = [interrupt1, interrupt2]`
9. PM interprets "approve both" → accept ALL
10. PM builds: `[{"type": "accept"}, {"type": "accept"}]`
11. Runner resumes with Command(resume=[...])
12. HITL middleware receives len=2, expects len=2 ✓
13. Both products saved

**Success Criteria:**
- ✓ PM detects 2 pending interrupts
- ✓ PM interprets batch approval correctly
- ✓ PM builds list with 2 responses
- ✓ NO "1 != 2" ERROR
- ✓ Both products saved

---

### Test 2.3: Selective Approval (Accept First, Edit Second)
**State:**
```python
pending_interrupts = [
    {tool_name: "create_product", tool_args: {name: "Jar 500ml", price: 30}},
    {tool_name: "create_product", tool_args: {name: "Jar 1L", price: 50}}
]
```

**Input:** "approve first, change second to 45 Rs"

**Expected PM Behavior:**
1. Detects resume_workflow (2 interrupts)
2. Interprets: First=accept, Second=edit price to 45
3. Builds:
   ```python
   [
       {"type": "accept", "args": None},
       {"type": "edit", "args": {"price": 45}}
   ]
   ```
4. Outputs Command

**Success Criteria:**
- ✓ PM detects 2 interrupts
- ✓ PM interprets selective edit correctly
- ✓ First product saved as-is
- ✓ Second product saved with price=45

---

### Test 2.4: Rejection
**State:** 1 pending interrupt

**Input:** "no, don't save"

**Expected PM Behavior:**
1. Detects resume_workflow
2. Interprets rejection
3. Builds: `[{"type": "response", "args": "User rejected"}]`

**Success Criteria:**
- ✓ PM interprets rejection
- ✓ Product NOT saved
- ✓ User receives acknowledgment

---

### Test 2.5: Ambiguous Response → Clarification
**State:** 2 pending interrupts

**Input:** "maybe"

**Expected PM Behavior:**
1. Detects resume_workflow
2. Cannot interpret "maybe" clearly
3. Asks for clarification: "Please confirm: approve, edit, or reject?"
4. Does NOT build Command yet

**Success Criteria:**
- ✓ PM detects ambiguity
- ✓ Clarification sent to user
- ✓ Workflow paused (no Command built)
- ✓ User can respond with clear intent

---

## P0: Media Handling

### Test 3.1: Media Download Success
**Input:** `media_id = "valid_media_123"`

**Expected:**
1. PM calls `download_whatsapp_media("valid_media_123")`
2. Tool returns: `"/tmp/media_downloads/valid_media_123.jpg"`
3. PM includes path in task description

**Success Criteria:**
- ✓ Media downloaded
- ✓ Path passed to department
- ✓ No errors

---

### Test 3.2: Media Download Failure
**Input:** `media_id = "invalid_media_xyz"`

**Expected:**
1. PM calls download tool
2. Tool raises exception
3. PM handles gracefully
4. PM asks user to resend media

**Success Criteria:**
- ✓ Error handled
- ✓ User notified
- ✓ Workflow doesn't crash

---

### Test 3.3: No Media (Text-Only)
**Input:** `media_id = null`

**Expected:**
1. PM does NOT call download tool
2. PM proceeds with text-only delegation

**Success Criteria:**
- ✓ No download attempted
- ✓ Workflow proceeds
- ✓ Department receives text description

---

## P1: Multi-Product Decomposition

### Test 4.1: Two Products → Two Tasks
**Input:** "Create jar 500ml @ 30 Rs AND bottle 1L @ 50 Rs"

**Expected PM Strategy:**
```python
write_todos([
    {content: "Create jar 500ml @ 30 Rs", status: "in_progress"},
    {content: "Create bottle 1L @ 50 Rs", status: "pending"}
])

# Delegate FIRST task only
task(description="Create product: jar 500ml priced at 30 Rs", ...)

# After first completes and user approves, delegate second
```

**Success Criteria:**
- ✓ PM creates 2 todos
- ✓ PM delegates ONE task at a time
- ✓ No parallel interrupts (avoids "1 != 2" error)
- ✓ Both products saved sequentially

---

### Test 4.2: Variant Decomposition
**Input:** "Create two sizes: 500ml and 1L"

**Expected:**
1. PM decomposes into 2 separate products
2. Sequential delegation (one at a time)

**Success Criteria:**
- ✓ 2 separate products created
- ✓ No batch interrupt conflict

---

### Test 4.3: Complex Multi-Step
**Input:** "Catalog 3 products: jar, bottle, container"

**Expected:**
1. PM creates 3 todos
2. Delegates each sequentially
3. Tracks progress with todos

**Success Criteria:**
- ✓ 3 todos created
- ✓ Sequential execution
- ✓ All 3 products saved

---

## P1: Error Handling

### Test 5.1: Department Failure
**Scenario:** Department crashes during execution

**Expected:**
1. PM receives error from department
2. PM logs error
3. PM notifies user: "Product cataloging failed. Please try again."

**Success Criteria:**
- ✓ Error caught
- ✓ User notified
- ✓ No crash

---

### Test 5.2: Invalid Media ID
**Scenario:** User provides invalid media_id

**Expected:**
1. Download tool fails
2. PM handles exception
3. PM asks user to resend

**Success Criteria:**
- ✓ Exception handled
- ✓ User receives clear message

---

### Test 5.3: Malformed Input
**Scenario:** Runner sends malformed JSON to PM

**Expected:**
1. PM handles parsing error
2. PM asks for clarification

**Success Criteria:**
- ✓ No crash
- ✓ Graceful degradation

---

### Test 5.4: Recursion Limit
**Scenario:** PM hits recursion limit

**Expected:**
1. GraphRecursionError raised
2. Runner catches exception
3. User notified

**Success Criteria:**
- ✓ Error caught at runner level
- ✓ User receives friendly message

---

## P2: Edge Cases

### Test 6.1: Empty Message
**Input:** `{text: null, media_id: null}`

**Expected:**
1. PM detects insufficient information
2. PM asks: "What would you like to catalog?"

**Success Criteria:**
- ✓ No crash
- ✓ Clarification requested

---

### Test 6.2: Very Long Description
**Input:** 500-word product description

**Expected:**
1. PM handles large input
2. Extracts key details
3. Delegates successfully

**Success Criteria:**
- ✓ No token limit errors
- ✓ Product created

---

### Test 6.3: Special Characters
**Input:** "Product: Jalapeño Jar™ 500ml @ ₹30"

**Expected:**
1. PM handles Unicode
2. Product saved with special chars

**Success Criteria:**
- ✓ Unicode preserved
- ✓ Product saved correctly

---

## Test Execution Commands

### Quick PM Chat Test
```bash
uv run python -m autifyme_agents.cli.pm_chat

# Interactive testing - try these inputs:
# 1. "catalog jar 500ml 30rs"
# 2. "what can you do?"
# 3. "namaste"
# 4. (if pending interrupt) "yes"
```

### Full Workflow Simulation
```bash
uv run python -m autifyme_agents.cli.simulate

# Runs predefined scenarios including:
# - New product with media
# - HITL approval flow
# - Multi-step workflows
```

### Automated Test Suite
```bash
# Run pytest with coverage
uv run pytest agents/tests/integration/ --cov=autifyme_agents -v

# Focus on PM tests
uv run pytest agents/tests/integration/test_project_manager.py -v

# Focus on HITL tests
uv run pytest agents/tests/integration/test_workflow.py -v -k hitl
```

---

## Validation Checklist

After running tests, validate:

- [ ] **Token Usage:** Check LangSmith - should show ~1850 tokens/message (down from 4200)
- [ ] **Latency:** Single LLM call per message (PM only, no specialist)
- [ ] **Intent Accuracy:** PM correctly classifies all 6 intent types
- [ ] **Batch Approval:** No "1 != 2" errors on multi-interrupt scenarios
- [ ] **Media Download:** PM downloads media before delegation
- [ ] **Task Decomposition:** Multi-product requests handled sequentially
- [ ] **Error Handling:** All error scenarios handled gracefully
- [ ] **State Management:** `pending_interrupts` populated correctly
- [ ] **Command Structure:** PM outputs proper list format for batch resume
- [ ] **E2E Flow:** Complete workflow from user message → product saved

---

## LangSmith Trace Analysis

For each test, check LangSmith traces:

1. **Intent Detection:**
   - PM receives raw JSON message
   - PM classifies intent correctly
   - No specialist calls visible

2. **Media Download:**
   - `download_whatsapp_media` tool called
   - Returns local path
   - Path included in task description

3. **Batch Approval:**
   - PM sees `state["pending_interrupts"]`
   - PM builds list of responses
   - Command structure correct

4. **Error Paths:**
   - Errors logged clearly
   - User receives friendly messages
   - No stack traces leaked to user

---

## Success Metrics (Overall)

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Intent Accuracy | 95%+ | Manual review of 20 test runs |
| Batch Approval Success | 100% | No "1 != 2" errors |
| Token Reduction | 50%+ | LangSmith average tokens/message |
| Latency Improvement | 30%+ | LangSmith call duration |
| Error Recovery | 100% | All error scenarios handled |
| User Experience | Positive | No confusing error messages |

---

## Next Steps After Testing

1. **If all P0 tests pass:**
   - Move to P1 tests
   - Deploy to staging environment
   - Monitor for 48 hours

2. **If any P0 tests fail:**
   - Debug with LangSmith traces
   - Fix PM prompt or runner logic
   - Re-run failed tests

3. **After all tests pass:**
   - Update documentation
   - Create migration guide for production
   - Plan rollout strategy

---

## Test Log Template

Use this for each test run:

```markdown
## Test Run: [Date/Time]

**Environment:** Local / Staging / Production
**Branch:** InitialDesign
**Tester:** [Name]

### Results

| Test | Status | Notes |
|------|--------|-------|
| 1.1 New Product | ✓ PASS | Tokens: 1820 |
| 1.2 Text-Only | ✓ PASS | Tokens: 1650 |
| 1.3 Resume | ✓ PASS | Command structure correct |
| 2.2 Batch Approval | ✓ PASS | No "1!=2" error! |
| ... | | |

### Issues Found

1. [Issue description]
   - Severity: High/Medium/Low
   - Steps to reproduce
   - Fix applied

### Recommendations

- [Any improvements needed]
```

---

**Ready to start testing!** Begin with P0 scenarios using `pm_chat` for quick iteration.
