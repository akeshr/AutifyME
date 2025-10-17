# AutifyME Test Infrastructure

**Philosophy**: Autonomous testing via hierarchical trace analysis orchestrated by Claude's workflow-tester agent.

---

## Directory Structure

```
tests/
├── tools/              # ⭐ Autonomous Testing Framework (Core)
├── unit/               # Unit tests for production code
├── integration/        # Integration tests
├── cli/                # CLI tools for quick iteration
├── fixtures/           # Test data
├── synthesizer/        # Synthesizer component tests
└── archived/           # Historical test approaches (reference only)
```

---

## Autonomous Testing Framework (Primary)

**Location**: `tests/tools/`

**What**: 5-tool framework for systematic workflow testing with hierarchical trace analysis.

**Used by**: Claude's `workflow-tester` agent (`.claude/agents/workflow-tester.md`)

### Framework Tools

**1. execute_scenario(scenario_id, hitl_mode, media_path)**
- Execute workflows programmatically with HITL simulation
- Returns ExecutionResult with trace_id, success, products_created, errors

**2. get_trace_overview(trace_id)**
- Level 0 analysis (~500 tokens) - Metadata only
- Returns hierarchical run tree, identifies missing runs, errors, performance issues

**3. get_run_details(run_id)**
- Level 1 analysis (~1,500 tokens) - Inputs/outputs for specific run
- Drill into failures identified by Level 0

**4. get_run_messages(run_id)**
- Level 2 analysis (~5K+ tokens) - Full LLM conversation
- Use SPARINGLY for LLM reasoning issues only

**5. list_recent_tests(limit)**
- Get test execution history for progress tracking

### Usage

**Direct (Python)**:
```python
from tests.tools import execute_scenario, get_trace_overview, get_run_details

# Execute workflow
result = execute_scenario("Catalog Nike shoes Rs 1000", hitl_mode="auto_approve")

# Hierarchical analysis
overview = get_trace_overview(result.trace_id)
# Level 0: Identify anomalies (missing runs, errors, latency)

if anomaly_found:
    details = get_run_details(failed_run_id)
    # Level 1: Inspect inputs, outputs, errors
```

**Agent-Orchestrated**:
```
User: "Test the cataloging workflow and report issues"
Claude invokes workflow-tester agent
Agent uses 5 tools autonomously, documents findings in TESTING_FINDINGS.md
```

### Key Files

- `framework_validation.py` - Validates framework itself
- `TESTING_FINDINGS.md` - Findings log from autonomous testing
- `RECONSTRUCTION_ARCHITECTURE.md` - Production data → test scenario reconstruction
- `.test_history.json` - Test execution history

### Documentation

- **Methodology**: `.claude/skills/autonomous-testing.md`
- **Agent Definition**: `.claude/agents/workflow-tester.md`
- **Full Spec**: `docs/architecture/testing/AUTONOMOUS_TESTING_FRAMEWORK.md`

---

## Unit Tests

**Location**: `tests/unit/`

**Purpose**: Test production code in isolation (no LLM, no workflows)

**Run**:
```bash
uv run pytest tests/unit -v
```

**Examples**:
- `test_image_analysis_specialist.py` - Specialist logic
- `test_whatsapp_media_client.py` - Media client
- `test_cataloging_tools.py` - Tool functions

---

## Integration Tests

**Location**: `tests/integration/`

**Purpose**: Test component integration (department, PM, webhook)

**Run**:
```bash
uv run pytest tests/integration -v
```

**Key Tests**:
- `test_cataloging_department.py` - Department workflows
- `test_project_manager.py` - PM intent detection
- `test_whatsapp_webhook.py` - Webhook endpoint

---

## CLI Tools

**Location**: `tests/cli/`

**Purpose**: Quick iteration during development

### simulate.py
Full workflow simulation with HITL.

**Used by**: Autonomous framework's `execute_scenario()`

**Direct usage**:
```bash
uv run python tests/cli/simulate.py "Catalog Nike shoes Rs 1000"
```

### pm_chat.py
Direct PM agent testing for rapid iteration.

```bash
uv run python tests/cli/pm_chat.py --interactive
```

---

## Synthesizer Tests

**Location**: `tests/synthesizer/`

**Purpose**: Test synthesizer component

**Run**:
```bash
uv run pytest tests/synthesizer -v
```

---

## Archived Tests

**Location**: `tests/archived/`

**What**: Historical test approaches superseded by autonomous framework

**Contents**:
- `e2e/` - Old e2e test runners (run_*.py)
- `cli/` - Old debug tools (capture, replay, debug, inspect_state)
- `scripts/` - One-off debugging scripts
- `scenarios/` - YAML scenario files

**Status**: Reference only, not maintained

---

## Running Tests

### Autonomous Testing (Primary)

**Invoke workflow-tester agent**:
```
"Test the cataloging workflow and report issues"
```

**Direct framework validation**:
```bash
uv run python tests/tools/framework_validation.py
```

### Traditional Pytest

**All tests**:
```bash
uv run pytest tests --cov=autifyme_agents --cov-report=xml
```

**By category**:
```bash
uv run pytest tests/unit -v              # Unit tests
uv run pytest tests/integration -v       # Integration tests
uv run pytest tests/synthesizer -v       # Synthesizer tests
```

### Quick Iteration

**PM testing**:
```bash
uv run python tests/cli/pm_chat.py --interactive
```

**Workflow simulation**:
```bash
uv run python tests/cli/simulate.py "Your test message"
```

---

## Testing Philosophy

**Before**: Manual test scripts, fragmented approaches, no systematic observability

**After**: Autonomous agent-orchestrated testing with hierarchical trace analysis

**Benefits**:
- **Token efficient**: 25x savings (Level 0→1→2 vs full dump)
- **Systematic**: Consistent methodology, evidence-based findings
- **Autonomous**: Agent decides when to drill deeper
- **Maintainable**: 5 tools instead of 50+ test scripts
- **Observable**: Full LangSmith trace correlation

---

## Key Principles

1. **Autonomous framework first**: Use workflow-tester agent for systematic testing
2. **Unit/integration tests**: Test production code, not workflows
3. **CLI for iteration**: Quick PM/workflow testing during development
4. **Archive, don't delete**: Keep historical approaches for reference
5. **Evidence-based**: All findings backed by trace analysis and DB validation

---

## Documentation

- **Local Testing Strategy**: `docs/architecture/testing/LOCAL_TESTING_STRATEGY.md`
- **Autonomous Framework Spec**: `docs/architecture/testing/AUTONOMOUS_TESTING_FRAMEWORK.md`
- **Testing Skill**: `.claude/skills/autonomous-testing.md`
- **Workflow-Tester Agent**: `.claude/agents/workflow-tester.md`
