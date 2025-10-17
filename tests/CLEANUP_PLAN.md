# Tests Directory Cleanup Plan

**Current State**: 52 Python files, 12,524 total lines
**Goal**: Clean, simple, reusable, maintainable test infrastructure

---

## Analysis

### Core Philosophy Change

**Before**: Manual test scripts, CLI tools, one-off debugging
**After**: Autonomous testing framework with workflow-tester agent

**The autonomous framework (5 tools in tests/tools/) supersedes**:
- All e2e test runners (run_*.py)
- CLI conversation testing (conversation.py, permutation_test.py)
- Debug scripts (capture, replay, debug, inspect_state)
- Manual HITL validation scripts

---

## Cleanup Strategy

### KEEP (Essential)

**1. tests/tools/** - Autonomous Testing Framework
```
tests/tools/
├── __init__.py              # Package exports
├── models.py                # Pydantic models
├── execution.py             # execute_scenario()
├── trace_analysis.py        # 3-level analysis
├── test_history.py          # History tracking
├── framework_validation.py  # Framework self-test
├── TESTING_FINDINGS.md      # Findings log
└── .test_history.json       # History persistence
```
**Reason**: Core autonomous testing infrastructure

**2. tests/unit/** - Unit Tests
```
tests/unit/
├── test_image_analysis_specialist.py
├── test_whatsapp_media_client.py
└── ... (all unit tests)
```
**Reason**: Test actual production code, not workflows

**3. tests/integration/** - Integration Tests (AUDIT)
```
tests/integration/
├── test_cataloging_department.py  # Keep if testing dept in isolation
├── test_project_manager.py        # Keep if testing PM in isolation
├── test_whatsapp_webhook.py       # Keep - tests webhook endpoint
└── test_workflow.py                # Audit - may be redundant
```
**Reason**: Test integration points, not full workflows

**4. tests/cli/simulate.py** - Workflow Execution
**Reason**: Used by execute_scenario(), core infrastructure

**5. tests/conftest.py** - Pytest Configuration
**Reason**: Shared fixtures

**6. tests/fixtures/** - Test Data
**Reason**: Used by unit/integration tests

---

### ARCHIVE (Superseded by Autonomous Framework)

**Move to tests/archived/** for reference:

**1. tests/e2e/** (13 files, ~3000 lines)
```
run_comprehensive_tests.py
run_hitl_comprehensive.py
run_hitl_extended.py
run_hitl_simple.py
run_hitl_with_db_validation.py
run_hitl_with_images.py
run_interactive_tests.py
run_live_monitor.py
test_batch_approval.py
test_department_parallel_interrupts.py
test_e2e_batch.py
test_runner_parallel_extraction.py
```
**Reason**: Autonomous framework handles all e2e testing with better observability

**2. tests/cli/** (7 files, ~3500 lines)
```
capture.py           # One-off debugging
replay.py            # One-off debugging
debug.py             # One-off debugging
inspect_state.py     # One-off debugging
conversation.py      # Superseded by execute_scenario()
permutation_test.py  # Superseded by framework
pm_chat.py           # May keep for quick PM iteration
```
**Reason**: Framework provides better testing methodology

**3. tests/scripts/** (6 files, ~800 lines)
```
clear_corrupted_state.py
debug_whatsapp_event.py
debug_whatsapp_payload.py
dump_langsmith_thread.py
run_whatsapp_server.py
test_mixed_batch_approval.py
```
**Reason**: One-off debugging, not systematic testing

**4. tests/scenarios/** (YAML files)
```
approval_followup.yaml
clarification_flow.yaml
conversation_mixed.yaml
greeting_to_cataloging.yaml
multi_product.yaml
rejection_flow.yaml
```
**Reason**: Used by conversation.py which is being archived

---

### DELETE (Temporary Test Files)

```
tests/tools/test_trace_analysis.py  # Was for validation, framework_validation.py covers it
tests/tools/analyze_trace.py        # One-off debug script
```

---

## Final Structure

```
tests/
├── __init__.py
├── conftest.py                     # Pytest config
├── README.md                       # Updated with new structure
│
├── tools/                          # Autonomous Testing Framework ⭐
│   ├── __init__.py
│   ├── models.py
│   ├── execution.py
│   ├── trace_analysis.py
│   ├── test_history.py
│   ├── framework_validation.py
│   ├── TESTING_FINDINGS.md
│   └── .test_history.json
│
├── unit/                           # Unit tests for production code
│   ├── test_image_analysis_specialist.py
│   ├── test_whatsapp_media_client.py
│   └── ...
│
├── integration/                    # Integration tests
│   ├── test_cataloging_department.py
│   ├── test_project_manager.py
│   └── test_whatsapp_webhook.py
│
├── fixtures/                       # Test data
│   └── ...
│
├── cli/                            # Minimal CLI for quick iteration
│   ├── __init__.py
│   └── simulate.py                # Core - used by framework
│
└── archived/                       # Historical reference
    ├── e2e/                       # Old e2e tests
    ├── cli/                       # Old CLI tools
    ├── scripts/                   # Old debug scripts
    └── scenarios/                 # Old YAML scenarios
```

---

## Metrics

**Before**:
- 52 Python files
- 12,524 lines of code
- Fragmented testing approaches
- Manual test execution
- No systematic observability

**After**:
- ~25 Python files (52% reduction)
- ~6,000 lines of code (52% reduction)
- Single autonomous testing approach
- Agent-orchestrated execution
- Hierarchical trace analysis (25x token efficiency)

---

## Migration Path

1. **Create archive directory**: `tests/archived/`
2. **Move superseded code**: e2e/, scripts/, scenarios/, most of cli/
3. **Delete temporary files**: test_trace_analysis.py, analyze_trace.py
4. **Update tests/README.md**: Document new structure
5. **Validate**: Run framework_validation.py to ensure nothing broken

---

## Justification

**Why archive instead of delete?**
- Historical reference for test scenarios
- May contain edge cases worth porting to autonomous framework
- Allows easy rollback if needed

**Why keep unit/integration tests?**
- Test production code directly (not workflows)
- Fast, focused, no LLM dependency
- Complement autonomous framework (not replace)

**Why simulate.py stays?**
- Core infrastructure used by execute_scenario()
- Handles WorkflowRunner setup, HITL simulation
- No duplication - framework wraps it

---

## Next Steps

1. Review and approve plan
2. Execute archive migration
3. Update documentation
4. Validate framework still works
5. Update workflow-tester agent if needed
