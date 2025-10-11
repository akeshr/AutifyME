# AutifyME Testing Guide

**Complete testing strategy with three complementary approaches**

---

## Testing Philosophy

AutifyME provides three distinct testing modes that serve different purposes:

1. **Automated Testing** - Fast validation, CI/CD integration, regression detection
2. **Interactive Testing** - Structured test scenarios with real human approval
3. **Live Monitoring** - Freeform exploration, real-time analysis, debugging

Use all three together for comprehensive coverage.

---

## Method 1: Automated Testing (Fast & Complete)

**Purpose**: Validate complete workflows end-to-end with database verification

**File**: `agents/run_comprehensive_tests.py`

**How it works**:
- Runs predefined test scenarios automatically
- Uses `auto_approve` mode to complete full workflow
- Validates database records after each test
- Generates JSON report with results

**Use when**:
- Running regression tests
- Validating after code changes
- CI/CD pipeline integration
- Quick sanity checks

### Usage

```bash
cd agents
uv run python run_comprehensive_tests.py
```

### What it tests

**Phase 1**: Unit & Integration Tests (pytest)
**Phase 2**: Code Quality (ruff linting)
**Phase 3**: Single-Message Scenarios
- Text with clear cataloging details
- Text with minimal details

**Phase 4**: Multi-Turn Conversations
- Greeting to cataloging flow

**Phase 5**: Database Validation
- Product creation verification
- Checkpoint state validation

### Output

```
======================================================================
🚀 AUTIFYME COMPREHENSIVE TEST SUITE
======================================================================

✅ Passed: 6/6 (100.0%)
❌ Failed: 0/6

📄 Test report saved to: test_report_20251011_123456.json
```

### Limitations

- Uses `auto_approve` (no real human judgment)
- Fixed test scenarios (not exploratory)
- No real-time interaction

---

## Method 2: Interactive Testing (Human Approval)

**Purpose**: Structured testing where YOU provide approval at HITL prompts

**File**: `agents/run_interactive_tests.py`

**How it works**:
- Runs test scenarios sequentially
- Pauses for your input at HITL approval prompts
- You can approve/reject/edit proposals
- Validates database after each test
- Generates report with your decisions

**Use when**:
- Testing PM analysis quality
- Validating HITL UX flow
- Ensuring approval logic works correctly
- Testing edge cases with real judgment

### Usage

```bash
cd agents
uv run python run_interactive_tests.py
```

### Interactive Flow

```
======================================================================
🎮 AUTIFYME INTERACTIVE TEST SUITE
======================================================================

Press Enter to start interactive testing...

######################################################################
📨 TEST 1/4: Text-only cataloging (clear details)
######################################################################

▶️  Text-only cataloging (clear details)
======================================================================
⏸️  This test will pause for your input at HITL prompts
======================================================================

[PM Analysis shows...]
[HITL Request appears...]

Your choice:
  [a] Approve
  [r] Reject
  [e] Edit

Choice: a

✅ Approved - continuing...

🗄️  ✅ Database validated: 1 products in catalog

Test 1 complete. Press Enter to continue to next test...
```

### Test Scenarios

1. **Text-only cataloging (clear details)** - "Catalog these canvas sneakers: white, $79.99, sizes 7-11"
2. **Text-only cataloging (minimal)** - "Add sneakers"
3. **Image with caption** - Image + "Catalog these premium running shoes - Nike Air Max, $129.99"
4. **Multi-turn conversation** - Greeting → Cataloging flow

### Output

```
📊 INTERACTIVE TEST SUMMARY
✅ Passed: 4/4 (100.0%)

DETAILED RESULTS:
✅ Text-only cataloging (clear details): PASSED
   📦 Products in DB: 1
✅ Text-only cataloging (minimal): PASSED
   📦 Products in DB: 2
✅ Image with caption cataloging: PASSED
   📦 Products in DB: 3
✅ Multi-turn: Greeting to Cataloging: PASSED
   📦 Products in DB: 4

📄 Test report saved to: interactive_test_report_20251011_123456.json
```

### Advantages

- Real human judgment at HITL points
- Tests complete workflow including DB
- Validates UX flow
- Structured progression through scenarios

### Limitations

- Requires manual interaction
- Time-consuming for many scenarios
- Not suitable for CI/CD

---

## Method 3: Live Monitor (Real-Time Analysis)

**Purpose**: Freeform testing where you send messages/files and see complete analysis in real-time

**File**: `agents/run_live_monitor.py`

**How it works**:
- Interactive shell where you type messages
- Send images/files on demand
- See PM analysis, agent interactions, state changes in real-time
- Inspect database anytime
- Review conversation history
- Complete control over flow

**Use when**:
- Exploring edge cases
- Debugging specific issues
- Testing custom scenarios
- Understanding agent behavior
- Iterating on prompt engineering

### Usage

```bash
cd agents
uv run python run_live_monitor.py
```

### Interactive Commands

```
======================================================================
🔴 AUTIFYME LIVE MONITOR
======================================================================

📖 LIVE MONITOR COMMANDS
----------------------------------------------------------------------
  > Your message here          - Send text message
  > @image path/to/file.jpg    - Attach image
  > @file path/to/document.pdf - Attach document
  > @status                    - Show state and DB status
  > @history                   - Show conversation history
  > @db                        - Show database contents
  > @clear                     - Clear conversation state
  > @help                      - Show this help
  > @quit                      - Exit monitor

>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
📝 You: Catalog these running shoes
```

### Example Session

```
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
📝 You: Catalog these running shoes

======================================================================
📨 MESSAGE #1
======================================================================
Text: Catalog these running shoes
Time: 14:32:15
======================================================================

🤖 PROCESSING...
----------------------------------------------------------------------

📊 PM ANALYSIS:
   Intent: cataloging
   Confidence: 0.95
   Next action: collect_more_info
   Reasoning: Need price and image for cataloging

⏸️  HITL REQUEST:
   Could you provide: price, brand, sizes, and an image?
   Type: information_request

Your response:
  [a] Approve
  [r] Reject
  [e] Edit

Choice: e
Your edits: Nike Air Max, $129.99, sizes 8-12

✏️  Edits applied - continuing...

📦 PRODUCT CATALOGED:
   Product ID: prod_123
   Status: success

✅ WORKFLOW COMPLETE
======================================================================

🗄️  DATABASE STATUS
----------------------------------------------------------------------
Company: Test Company
Products in catalog: 1

Recent products:
  • Nike Air Max - $129.99
----------------------------------------------------------------------

>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
📝 You: @status

💬 CONVERSATION STATE
----------------------------------------------------------------------
Messages in state: 4
Checkpoint ID: abc123

Recent messages:
  • HumanMessage: Catalog these running shoes
  • AIMessage: Could you provide: price, brand...
  • HumanMessage: Nike Air Max, $129.99, sizes 8-12
  • AIMessage: Product cataloged successfully
----------------------------------------------------------------------

>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
📝 You: @image test_images/sneaker.jpg Another product to catalog

[PM analyzes image + caption in real-time...]

>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
📝 You: @quit

👋 Exiting live monitor...
```

### Advantages

- Complete flexibility
- Real-time visibility into all processing
- Natural conversation flow
- Can test any scenario on the fly
- Inspect state/DB anytime
- Perfect for debugging

### Limitations

- Not automated (manual only)
- No structured test reporting
- Session state is temporary

---

## Comparison Matrix

| Feature | Automated | Interactive | Live Monitor |
|---------|-----------|-------------|--------------|
| **Speed** | Fast | Medium | Slow |
| **Human Input** | None | Structured | Freeform |
| **DB Validation** | ✅ Yes | ✅ Yes | ✅ Yes |
| **CI/CD Ready** | ✅ Yes | ❌ No | ❌ No |
| **Real-time Analysis** | ❌ No | ⚠️ Limited | ✅ Yes |
| **State Inspection** | ❌ No | ❌ No | ✅ Yes |
| **Custom Scenarios** | ❌ No | ❌ No | ✅ Yes |
| **Test Reports** | ✅ JSON | ✅ JSON | ❌ No |
| **Image Testing** | ⚠️ Fixed | ⚠️ Fixed | ✅ Any |
| **HITL Testing** | Auto-approve | ✅ Real | ✅ Real |

---

## Recommended Workflow

### 1. Development Cycle
```bash
# Quick iteration on PM logic changes
cd agents
uv run python run_comprehensive_tests.py

# If failures, debug with live monitor
uv run python run_live_monitor.py
> [test specific scenario]
> @status
> @db
```

### 2. Before Committing
```bash
# Run automated tests
uv run python run_comprehensive_tests.py

# Run linting
uv run ruff check src/
```

### 3. Testing HITL UX Changes
```bash
# Use interactive runner to validate flow
uv run python run_interactive_tests.py
```

### 4. Exploring Edge Cases
```bash
# Use live monitor for freeform testing
uv run python run_live_monitor.py
> [try various edge cases]
> @status
> @db
> @history
```

### 5. Regression Testing
```bash
# Add new scenario to run_comprehensive_tests.py
# Run full suite
uv run python run_comprehensive_tests.py
```

---

## Manual Testing (Method 0)

For one-off testing of specific scenarios:

### Single Message Test
```bash
cd agents

# Text only
uv run python -m autifyme_agents.cli.simulate "Catalog these sneakers: $79.99" --hitl-mode interactive

# With image
uv run python -m autifyme_agents.cli.simulate --image "test_images/sneaker.jpg" --hitl-mode interactive "Catalog these Nike Air Max"
```

### Multi-Turn Conversation Test
```bash
# List available scenarios
uv run python -m autifyme_agents.cli.conversation --list

# Run specific scenario
uv run python -m autifyme_agents.cli.conversation --scenario greeting_to_cataloging --hitl-mode interactive
```

### Replay Captured Scenarios
```bash
# Capture from production webhook
uv run python -m autifyme_agents.cli.capture --event webhook_payload.json

# List captured scenarios
uv run python -m autifyme_agents.cli.capture --list

# Replay with validation
uv run python -m autifyme_agents.cli.replay --scenario scenario_001 --validate-db
```

---

## Summary

**Choose your testing method based on your goal:**

- **Fast validation** → `run_comprehensive_tests.py` (automated)
- **UX testing** → `run_interactive_tests.py` (structured approval)
- **Debugging/exploration** → `run_live_monitor.py` (real-time analysis)
- **One-off tests** → Direct CLI (`simulate`, `conversation`, `replay`)

**Best practice**: Use all three regularly for comprehensive coverage.
