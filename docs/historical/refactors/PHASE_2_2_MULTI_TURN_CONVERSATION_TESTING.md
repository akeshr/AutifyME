# Phase 2.2: Multi-Turn Conversation Testing

**Date**: 2025-10-11
**Status**: ✅ COMPLETE
**Implementation Time**: ~2 hours

---

## Executive Summary

Phase 2.2 delivers a comprehensive multi-turn conversation testing framework that validates:
- Conversation continuity across multiple message exchanges
- Context preservation between turns
- State management in complex conversation flows
- HITL approval handling in multi-turn scenarios
- PM's ability to maintain conversation coherence

**Key Deliverable**: YAML-driven conversation player with 6 predefined scenarios covering realistic conversation patterns.

---

## What Was Built

### 1. Conversation Player (`cli/conversation.py`)

**Core Features**:
- YAML-based conversation script execution
- Multi-turn conversation orchestration
- Context validation framework
- State inspection at each turn
- Comprehensive conversation reports
- Support for all message types (text, media, voice, documents)
- All HITL modes (approve/reject/edit/question)
- Debug mode for verbose state inspection

**Architecture**:
```python
ConversationPlayer
  ├── play_conversation()     # Main orchestration
  ├── _execute_turn()         # Single turn execution
  ├── _validate_context()     # Context validation
  ├── _generate_summary()     # Report generation
  └── _print_report()         # Console reporting

ConversationChannel
  ├── send_text()             # Track text messages
  ├── send_approval_request() # Track approval requests
  ├── send_completion()       # Track completions
  └── send_error()            # Track errors
```

**Key Innovation**: Turn-based state tracking with validation rules allowing declarative verification of conversation state.

---

### 2. Conversation Scenarios (YAML)

Created 6 comprehensive scenarios covering different conversation patterns:

#### 1. `greeting_to_cataloging.yaml`
**Flow**: User greets → PM responds → User catalogs product
**Tests**: Conversation continuity, context switching (conversational → cataloging)
**Turns**: 2

#### 2. `clarification_flow.yaml`
**Flow**: Ambiguous request → PM asks clarification → User provides details → User sends media
**Tests**: Multi-turn clarification handling, incremental context building
**Turns**: 3

#### 3. `approval_followup.yaml`
**Flow**: User catalogs → Approval → User asks follow-up question
**Tests**: Post-approval conversation continuity
**Turns**: 2

#### 4. `multi_product.yaml`
**Flow**: User catalogs product 1 → Approval → Product 2 → Product 3
**Tests**: Context isolation between products, conversation history preservation
**Turns**: 3

#### 5. `conversation_mixed.yaml`
**Flow**: Greeting → Inquiry → Cataloging → Follow-up inquiry
**Tests**: PM's ability to handle mixed intents while preserving context
**Turns**: 4

#### 6. `rejection_flow.yaml`
**Flow**: Catalog → Reject draft → Retry with corrections
**Tests**: Rejection handling, retry workflows
**Turns**: 2
**Note**: Uses `auto_reject` HITL mode for first turn

---

## YAML Conversation Script Format

### Schema

```yaml
name: "Conversation Name"
description: "What this conversation tests"
sender: "test_user_identifier"  # Unique sender ID
hitl_mode: "auto_approve"        # Optional, defaults to interactive

turns:
  - turn: 1
    text: "User's message"       # Optional if media-only
    media: "path/to/file.jpg"    # Optional
    media_type: "image"          # image/video/audio/voice/document
    wait: 0.5                    # Seconds to wait before next turn
    expected_intent: "cataloging" # Expected PM classification
    validate_context:            # Optional validation rules
      - conversation_history_length: 2
      - pending_approval: true
      - no_pending_approval: false
      - approval_has_image_data: true

  - turn: 2
    text: "Second message"
    # ... same structure
```

### Validation Rules

**conversation_history_length**: Verify message count
**pending_approval**: Check if approval is requested
**no_pending_approval**: Check if no approval pending
**approval_has_image_data**: Verify approval includes media

---

## Usage

### Basic Usage

```bash
# List available scenarios
uv run python -m autifyme_agents.cli.conversation --list

# Run single scenario
uv run python -m autifyme_agents.cli.conversation --scenario greeting_to_cataloging

# Run with specific HITL mode
uv run python -m autifyme_agents.cli.conversation --scenario clarification_flow --hitl-mode auto_approve

# Run all scenarios
uv run python -m autifyme_agents.cli.conversation --all

# Debug mode (verbose state inspection)
uv run python -m autifyme_agents.cli.conversation --scenario greeting_to_cataloging --debug
```

### Via CLI Entry Point

```bash
# Added to CLI entry point for easier access
python -m autifyme_agents.cli conversation --scenario greeting_to_cataloging
```

---

## Conversation Report Format

### Console Output

```
##############################################
🎭 CONVERSATION: Greeting to Cataloging Flow
📝 User greets PM, then requests product cataloging
👤 Sender: test_user_greeting_catalog
🔧 HITL Mode: auto_approve
🔄 Turns: 2
##############################################

──────────────────────────────────────────
🔵 TURN 1
──────────────────────────────────────────
👤 User: Hi, how are you?
🎯 Expected Intent: conversational

📤 PM: Hello! I'm here to help...

──────────────────────────────────────────
🔵 TURN 2
──────────────────────────────────────────
👤 User: Can you catalog these canvas sneakers...
📎 Media (image): tests/fixtures/images/sneaker.jpg
🎯 Expected Intent: cataloging

⏸️  [TURN 2] APPROVAL REQUEST TO test_user_greeting_catalog:
==================================
{
  "name": "Canvas Sneakers",
  "price": 79.99,
  ...
}
==================================

[AUTO-APPROVE MODE: Approving automatically]

✅ Workflow complete

##############################################
📊 CONVERSATION REPORT: Greeting to Cataloging Flow
##############################################

✅ Successful turns: 2/2
📨 Total messages: 4
⏸️  Total approvals: 1
🔍 Validations: 2/2 passed (100.0%)
⏱️  Total time: 5.23s

────────────────────────────────────────
📋 Turn-by-Turn Breakdown:
────────────────────────────────────────

✅ Turn 1: SUCCESS (2.15s)
     Validations: 1/1 passed
✅ Turn 2: SUCCESS (3.08s)
     Validations: 1/1 passed

##############################################
```

### Report Data Structure

```python
{
    "scenario": "Greeting to Cataloging Flow",
    "description": "...",
    "sender": "test_user_greeting_catalog",
    "hitl_mode": "auto_approve",
    "total_turns": 2,
    "elapsed_time": 5.23,
    "turns": [
        {
            "turn": 1,
            "text": "Hi, how are you?",
            "media": None,
            "expected_intent": "conversational",
            "status": "success",
            "error": None,
            "elapsed": 2.15,
            "messages_sent": 1,
            "approvals_requested": 0,
            "validations": [...]
        },
        # ... more turns
    ],
    "summary": {
        "total_turns": 2,
        "successful_turns": 2,
        "failed_turns": 0,
        "total_messages": 4,
        "total_approvals": 1,
        "total_validations": 2,
        "passed_validations": 2,
        "validation_pass_rate": "100.0%"
    }
}
```

---

## Design Decisions

### 1. YAML-Based Scenarios

**Why YAML?**
- Declarative and human-readable
- Easy for non-developers to create scenarios
- Clear separation of test data from test logic
- Supports complex nested structures (validations, metadata)

**Alternative Considered**: Python test functions
**Rationale**: YAML provides better reusability and non-programmer accessibility

---

### 2. Validation Framework

**Architecture**:
- Validation rules defined in YAML
- Executed after each turn
- Results tracked in turn report
- Failed validations highlighted but don't block execution

**Why Non-Blocking?**
- Allows complete conversation flow observation
- Useful for exploratory testing
- Can identify multiple issues in single run

**Future Enhancement**: Add `--strict` mode to fail fast on validation errors

---

### 3. Turn-Based State Tracking

**Tracked Metrics**:
- Messages sent by PM
- Approval requests issued
- Turn execution time
- Validation pass/fail status

**Benefit**: Enables detailed post-conversation analysis and debugging

---

### 4. Debug Mode

**Verbose Output Includes**:
- Full message content
- Complete approval drafts
- Detailed validation results
- Turn summaries

**Use Case**: Debugging complex conversation flows or validation failures

---

## Testing Verification

### Unit Tests
**Status**: ✅ All passing (56/56)
**Coverage**: Core workflows tested, CLI tools not directly tested (intended for manual use)

### Linting
**Status**: ✅ Zero errors
**Tool**: Ruff with project configuration

### Integration Verification
**Method**: Manual execution of all 6 scenarios
**Result**: All scenarios execute successfully with expected behavior

---

## Files Created

### Core Implementation
- `tests/cli/conversation.py` (739 lines)
  - ConversationPlayer class
  - ConversationChannel class
  - CLI entry point

### Conversation Scenarios
- `tests/cli/scenarios/greeting_to_cataloging.yaml`
- `tests/cli/scenarios/clarification_flow.yaml`
- `tests/cli/scenarios/approval_followup.yaml`
- `tests/cli/scenarios/multi_product.yaml`
- `tests/cli/scenarios/conversation_mixed.yaml`
- `tests/cli/scenarios/rejection_flow.yaml`

### Modified Files
- `tests/cli/__main__.py` - Added conversation command

### Documentation
- `docs/architecture/PHASE_2_2_MULTI_TURN_CONVERSATION_TESTING.md` (this document)

---

## Key Capabilities Delivered

### 1. Conversation Continuity Testing ✅
**What**: Verify PM maintains context across multiple turns
**How**: Declarative YAML scenarios with state validation
**Evidence**: `greeting_to_cataloging.yaml` executes cleanly

### 2. Context Preservation Validation ✅
**What**: Ensure conversation history and state persist correctly
**How**: Validation rules check message counts, approval state, data presence
**Evidence**: All 6 scenarios validate context correctly

### 3. Multi-Turn HITL Flows ✅
**What**: Test approval handling across conversation turns
**How**: Scenarios with pre-approval and post-approval turns
**Evidence**: `approval_followup.yaml` verifies post-approval continuity

### 4. Mixed Intent Handling ✅
**What**: Verify PM handles intent changes mid-conversation
**How**: Scenarios mixing conversational, inquiry, and cataloging intents
**Evidence**: `conversation_mixed.yaml` demonstrates smooth transitions

### 5. Rejection and Retry Workflows ✅
**What**: Test recovery from rejected approvals
**How**: `rejection_flow.yaml` with auto_reject mode
**Evidence**: Conversation continues after rejection

### 6. Debugging Support ✅
**What**: Verbose inspection for complex conversation debugging
**How**: `--debug` flag enables detailed turn-by-turn output
**Evidence**: Debug mode shows complete state at each turn

---

## Comparison with Phase 2.1 (simulate.py)

| Feature | Phase 2.1 (simulate.py) | Phase 2.2 (conversation.py) |
|---------|-------------------------|------------------------------|
| **Purpose** | Single-message workflow testing | Multi-turn conversation testing |
| **Scenarios** | 16 message type permutations | 6 conversation flow patterns |
| **State Tracking** | Messages sent (basic) | Turn-based state + validations |
| **Validation** | Manual observation | Automated validation rules |
| **Use Case** | Quick single-message testing | Complex conversation debugging |
| **Reports** | Basic success/failure | Comprehensive turn-by-turn reports |
| **Context Testing** | Not supported | Core feature |

**Complementary, Not Redundant**: simulate.py for quick iteration, conversation.py for comprehensive flows.

---

## Usage Recommendations

### When to Use Conversation Testing

**✅ Use For**:
- Testing multi-turn conversation flows
- Validating context preservation
- Debugging complex HITL scenarios
- Verifying PM intent classification across turns
- Testing conversation continuity after approvals/rejections

**❌ Don't Use For**:
- Quick single-message tests (use `simulate.py`)
- Systematic message type coverage (use `permutation_test.py`)
- Interactive PM debugging (use `pm_chat.py`)

---

## Extensibility

### Adding New Scenarios

**Steps**:
1. Create YAML file in `cli/scenarios/`
2. Define conversation turns with validations
3. Run with `--scenario <name>`

**Example**:
```bash
# Create new scenario
vi cli/scenarios/my_scenario.yaml

# Run it
uv run python -m autifyme_agents.cli.conversation --scenario my_scenario
```

### Adding New Validation Rules

**Location**: `ConversationPlayer._validate_context()` in `conversation.py`

**Pattern**:
```python
elif rule == "my_custom_rule":
    actual_value = ... # Calculate actual value
    passed = actual_value == expected_value
    message = f"My rule: {actual_value} (expected {expected_value})"
```

---

## Known Limitations

### 1. Validation Rules Limited to Channel State
**Current**: Can only validate message counts, approval presence
**Future**: Add checkpoint state inspection, PM internal state validation

### 2. No Timing Control for PM Responses
**Current**: Cannot inject delays or simulate slow responses
**Future**: Add response simulation controls

### 3. No Support for Parallel Conversations
**Current**: Single conversation at a time
**Future**: Multi-user concurrent conversation testing

### 4. Manual Media File Management
**Current**: Scenarios reference media files by path
**Future**: Media fixture management system

---

## Integration with Testing Stack

### Complete Testing Stack (After Phase 2.2)

```
┌─────────────────────────────────────────────────────┐
│ Phase 1: Core Testing (COMPLETE)                     │
├─────────────────────────────────────────────────────┤
│ • pytest (unit + integration tests)                  │
│ • 56 tests passing, 9 skipped                        │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Phase 2.1: Single-Message Testing (COMPLETE)         │
├─────────────────────────────────────────────────────┤
│ • simulate.py - 16 message scenarios                 │
│ • pm_chat.py - Interactive PM testing                │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Phase 2.2: Multi-Turn Testing (COMPLETE) ← THIS      │
├─────────────────────────────────────────────────────┤
│ • conversation.py - 6 conversation scenarios         │
│ • Context validation framework                       │
│ • Turn-based state tracking                          │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Phase 2.3: State Inspection (NEXT)                   │
├─────────────────────────────────────────────────────┤
│ • Interactive debugger                               │
│ • Checkpoint viewer                                  │
│ • State modification tools                           │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Phase 2.4: Scenario Recording/Replay (PLANNED)       │
├─────────────────────────────────────────────────────┤
│ • Webhook event capture                              │
│ • Local replay capability                            │
│ • Regression test library (50+ scenarios)            │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Phase 3: Systematic Coverage (COMPLETE)              │
├─────────────────────────────────────────────────────┤
│ • permutation_test.py - 188+ scenarios               │
└─────────────────────────────────────────────────────┘
```

---

## Success Criteria

| Criterion | Target | Achieved |
|-----------|--------|----------|
| Multi-turn conversation support | Yes | ✅ Yes |
| YAML-based scenarios | Yes | ✅ Yes (6 scenarios) |
| Context validation | Yes | ✅ Yes (4 validation rules) |
| State tracking | Yes | ✅ Yes (turn-based) |
| Comprehensive reports | Yes | ✅ Yes |
| HITL mode support | All modes | ✅ All 5 modes |
| Debug mode | Yes | ✅ Yes |
| Tests passing | 100% | ✅ 56/56 (100%) |
| Linting clean | Zero errors | ✅ Zero errors |
| Documentation | Complete | ✅ This document |

**Status**: ✅ **ALL CRITERIA MET**

---

## Lessons Learned

### Technical

1. **YAML Schema Flexibility**: YAML's flexibility allowed rapid scenario creation without code changes
2. **Turn-Based State Tracking**: Simplified debugging compared to monolithic state inspection
3. **Non-Blocking Validations**: Allow full conversation observation even when validations fail
4. **Channel Abstraction Reuse**: ConsoleChannel pattern from simulate.py extended cleanly

### Process

1. **Design First**: YAML schema designed before implementation prevented rework
2. **Incremental Testing**: Built scenarios incrementally, validating each
3. **Documentation Alongside**: Wrote docs as features were implemented
4. **Reuse Patterns**: Leveraged simulate.py patterns significantly accelerated development

---

## Next Steps

### Immediate (Phase 2.3)

1. **State Inspection Viewer**: Interactive debugger for workflow state
2. **Checkpoint Inspector**: View and modify LangGraph checkpoints
3. **Breakpoint Support**: Pause execution at specific turns/events

### Future Enhancements

1. **Advanced Validations**: Checkpoint state, PM internal state, database queries
2. **Timing Controls**: Simulate delays, timeouts, interruptions
3. **Multi-User Scenarios**: Concurrent conversations, handoff flows
4. **Media Fixture Management**: Organized media assets for scenarios
5. **Automated Regression Suite**: Run all scenarios on every commit

---

## Conclusion

**Phase 2.2 Successfully Delivers**:
- Comprehensive multi-turn conversation testing framework
- 6 realistic conversation scenarios covering key patterns
- Automated context validation with detailed reporting
- Clean integration with existing testing stack
- Extensible YAML-based scenario system

**Impact**:
- **Development Velocity**: Rapid iteration on conversation flows without WhatsApp
- **Quality Assurance**: Automated validation catches context preservation bugs
- **Debugging Efficiency**: Turn-by-turn reports simplify issue diagnosis
- **Regression Prevention**: Scenario library prevents known issues from recurring

**Ready For**: Phase 2.3 (State Inspection Viewer) implementation

---

**Phase 2.2 Completed By**: Development Team
**Date**: 2025-10-11
**Implementation Time**: ~2 hours
**Status**: ✅ COMPLETE, TESTED, DOCUMENTED
