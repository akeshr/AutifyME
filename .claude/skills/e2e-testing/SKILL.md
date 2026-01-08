---
name: e2e-testing
description: End-to-end testing and evaluation with real Supabase data. Execute scenarios, evaluate traces, track findings. Orchestrates autonomous-testing, workflow-evaluation, and agent-improvement skills.
---

# E2E Testing & Evaluation Skill

## Your Role

**You ARE the testing orchestrator.** You execute test scenarios against the PM using real production data from Supabase, evaluate results, track findings via GitHub issues, and coordinate fixes across specialized skills.

This skill ORCHESTRATES:
- `autonomous-testing` - For PM interaction and trace collection
- `workflow-evaluation` - For systematic trace analysis
- `agent-improvement` - For diagnosing and fixing identified issues

---

## System Architecture (CRITICAL CONTEXT)

**Understand the actual system before evaluating:**

### Two-Phase Architecture

```
PHASE 1: INTELLIGENCE (Wave-based, can be parallel)
  PM loads discovery_mindset protocol
  PM downloads media if present
  PM delegates to analysts based on dependency graph:
    - visual_analyst (always first when image present)
    - product_analyst (external/market research)
    - catalog_analyst (internal catalog verification)
  Analysts write findings to files

APPROVAL GATE:
  PM reads analysis files (read_file)
  PM loads synthesis protocol
  PM synthesizes findings, detects conflicts
  PM presents to user with open-ended question

PHASE 2: EXECUTION (Serial, after user approval)
  PM loads execution_flows protocol
  PM delegates to specialists:
    - creative_specialist -> asset creation with HITL
    - catalog_specialist -> record creation with HITL
  Specialists verify analyst work, then execute
```

### Key Behaviors to Evaluate

| Behavior | What to Check |
|----------|---------------|
| Protocol Loading | Did PM/agents load protocols FIRST before any action? |
| Wave Execution | Did PM build dependency graph, execute in waves? |
| File Communication | Did PM pass file paths to downstream agents? |
| Approval Gate | Did PM read files, synthesize, present to user? |
| Two-Stage HITL | Creative HITL (image) -> Catalog HITL (data)? |
| Verification Pivot | When findings contradict user, did PM ask? |

### LangSmith Trace Structure (CRITICAL)

**Understanding agent attribution in traces:**

```
LangGraph (PM)                    <-- Root = PM
  |-- tools
       |-- load_protocol          <-- PM called this
       |-- task                   <-- PM delegated (subagent_type in args)
            |-- LangGraph         <-- Nested = Subagent
                 |-- tools
                      |-- load_protocol   <-- Subagent called this
                      |-- view_image      <-- Subagent called this
```

**Agent attribution logic:**
- `LangGraph > tools > X` = PM called tool X
- `LangGraph > tools > task > LangGraph > tools > X` = Subagent called tool X
- Subagent identity comes from `task` tool's `subagent_type` argument

**Actual tool names (not assumptions!):**

| Tool | Purpose |
|------|---------|
| `task` | PM delegates to subagent (contains `subagent_type`) |
| `load_protocol` | Agent loads a protocol (contains `protocol_names`, `domain`) |
| `read_data` | Agent queries data (contains `table`, `search_patterns`) |
| `write_file` | Agent writes output file |
| `view_image` | Agent analyzes image |
| `image_studio` | Agent generates/edits image |

---

## Quick Start

### Run a Specific Scenario

```python
from tests.tools import chat_with_pm

# 1. Execute scenario (scenario_id enables history queries)
result = chat_with_pm(
    "Catalog this product",
    media_path="path/to/image.jpg",
    scenario_id="PM-01"  # Stored in LangSmith metadata for get_scenario_history()
)

# 2. Get trace data for evaluation
from tests.tools import (
    get_tool_call_sequence,
    get_delegation_graph,
    get_protocol_loads,
    get_agent_final_message,
)

seq = get_tool_call_sequence(result.trace_id)
graph = get_delegation_graph(result.trace_id)
protocols = get_protocol_loads(result.trace_id)
final_msg = get_agent_final_message(result.trace_id, "PM")

# 3. Evaluate against success criteria (YOU are the evaluator)
# Check: protocols.pm_first_action_was_protocol == True
# Check: graph.delegation_order matches expected agents
# Check: graph.waves structure (e.g., {1: ['visual_analyst']})
# Check: final_msg.has_open_question == True
```

### Evaluate and Record Results

```python
from tests.tools import record_evaluation, EvaluationResult, EvaluationCriterion
from datetime import datetime

# Build evaluation result
result = EvaluationResult(
    scenario_id="PM-01",
    trace_id=trace_id,
    thread_id=thread_id,
    status="PASS",  # or "FAIL", "PARTIAL", "ERROR"
    overall_score=1.0,
    criteria_results=[
        EvaluationCriterion(
            criterion="protocol_loading",
            passed=True,
            score=1.0,
            reasoning="PM loaded discovery_mindset protocol as first action"
        ),
        # ... more criteria
    ],
    passed_criteria=5,
    failed_criteria=0,
    evaluated_at=datetime.now()
)

# Store in LangSmith for history
record_evaluation(trace_id, "PM-01", result)
```

### Check Historical Patterns

```python
from tests.tools import get_scenario_history

# Get past 30 days of PM-01 runs
history = get_scenario_history("PM-01", days=30)
print(f"Pass rate: {history.pass_rate:.1%}")
print(f"Most common failure: {history.most_common_failure}")
print(f"Trend: {history.recent_trend}")
```

### Replay Production Failures

```sql
SELECT trace_id, message_text, error_message
FROM workflow_outcomes
WHERE success = false
ORDER BY created_at DESC
LIMIT 10;
```

---

## Evaluation Tools Reference

### Data Extraction Functions

These functions extract structured data from LangSmith traces for evaluation:

| Function | Purpose | Key Fields |
|----------|---------|------------|
| `get_tool_call_sequence(trace_id)` | Ordered tool calls with agent attribution | `tool_calls`, `first_tool_call`, `delegation_calls`, `file_read_calls` |
| `get_delegation_graph(trace_id)` | Agent delegation hierarchy and waves | `delegations`, `waves`, `delegation_order`, `agents_involved` |
| `get_file_io_trace(trace_id)` | File read/write operations | `operations`, `analysis_files_written`, `analysis_files_read_by_pm` |
| `get_protocol_loads(trace_id)` | Protocol loading by agent | `protocol_loads`, `pm_first_action_was_protocol`, `agent_protocols` |
| `get_agent_final_message(trace_id, agent)` | Final message analysis | `message`, `has_open_question`, `has_numbered_options` |

### LangSmith Feedback Integration

These functions store and retrieve evaluation data for continuous improvement:

| Function | Purpose |
|----------|---------|
| `record_evaluation(trace_id, scenario_id, result)` | Store evaluation in LangSmith feedback |
| `get_scenario_history(scenario_id, days)` | Query past runs and failure patterns |
| `get_baseline(scenario_id)` | Get known-good trace for comparison |
| `store_baseline(trace_id, scenario_id)` | Save trace as reference baseline |
| `compare_to_baseline(trace_id, scenario_id)` | Compare trace to baseline (matches/deviations/metrics) |

### Evaluation Criteria

When evaluating a trace, check these criteria:

| Criterion | How to Check | Pass Condition |
|-----------|--------------|----------------|
| `protocol_loading` | `get_protocol_loads()` | `pm_first_action_was_protocol == True` |
| `wave_execution` | `get_delegation_graph()` | `waves[1] == ['visual_analyst']` and `waves[2]` contains P+C |
| `approval_gate` | `get_file_io_trace()` | `analysis_files_read_by_pm` is non-empty |
| `open_question` | `get_agent_final_message()` | `has_open_question == True` and `has_numbered_options == False` |
| `hitl_sequence` | Multi-trace analysis | Creative HITL before Catalog HITL |

---

## Workflow

```
+------------------+     +------------------+     +------------------+
|  1. SCENARIOS    | --> |  2. EXECUTE      | --> |  3. EVALUATE     |
|  (SCENARIOS.md)  |     |  (autonomous-    |     |  (Claude uses    |
|  + Supabase data |     |   testing)       |     |   extraction     |
|                  |     |                  |     |   functions)     |
+------------------+     +------------------+     +------------------+
                                                          |
                                                          v
+------------------+     +------------------+     +------------------+
|  6. TRACK        | <-- |  5. VERIFY       | <-- |  4. FIX          |
|  (LangSmith +    |     |  (re-run +       |     |  (agent-         |
|   GitHub Issues) |     |   compare)       |     |   improvement)   |
+------------------+     +------------------+     +------------------+
```

### Continuous Improvement Loop

```
                    +------------------+
                    |  Run Scenario    |
                    +--------+---------+
                             |
                             v
                    +------------------+
                    |  Extract Data    |
                    |  (tool sequence, |
                    |   delegation,    |
                    |   file I/O)      |
                    +--------+---------+
                             |
                             v
                    +------------------+
                    |  Evaluate        |
                    |  (Claude checks  |
                    |   criteria)      |
                    +--------+---------+
                             |
              +--------------+--------------+
              |                             |
              v                             v
     +--------+--------+           +--------+--------+
     |  PASS           |           |  FAIL           |
     |  - Record       |           |  - Record       |
     |  - Store as     |           |  - Deep dive    |
     |    baseline?    |           |  - Fix          |
     +-----------------+           |  - Re-run       |
                                   +-----------------+
                                            |
                                            v
                                   +------------------+
                                   |  Query History   |
                                   |  - Pattern?      |
                                   |  - Regression?   |
                                   |  - Trend?        |
                                   +------------------+
```

---

## Execution Protocol

### Phase 1: Scenario Selection

**Option A: From SCENARIOS.md**
```yaml
scenario: PM-01
```

**Option B: From Supabase Query**
```sql
SELECT p.*, pa.storage_path
FROM products p
JOIN product_assets pa ON pa.product_id = p.id
WHERE pa.asset_type = 'image'
LIMIT 1;
```

**Option C: Replay Failure**
```sql
SELECT trace_id, message_text, media_id
FROM workflow_outcomes
WHERE success = false
ORDER BY created_at DESC
LIMIT 1;
```

### Phase 2: Data Preparation

For data-driven scenarios, fetch from Supabase:
- Use `mcp__supabase__execute_sql` for queries
- Get product data, images, categories as needed

**Image Handling:**
- Query `product_assets` for real images
- Download from Supabase storage if needed
- Pass path to `chat_with_pm(media_path=...)`

### Phase 3: Execution

```python
from tests.tools import chat_with_pm

result = chat_with_pm(
    message=scenario.message,
    media_path=scenario.media_path,
    thread_id=scenario.thread_id,
    scenario_id=scenario.id  # Enables get_scenario_history() queries
)

trace_id = result.trace_id
thread_id = result.thread_id  # For multi-turn continuation
```

### Phase 4: Evaluation

**Quick Check (Every Scenario):**
- Did PM load protocols first?
- Did PM build correct dependency graph?
- Did PM delegate to analysts in correct waves?
- Did PM read analysis files at approval gate?
- Did PM synthesize and present to user?
- Did PM wait for approval before execution phase?
- Was HITL two-stage (creative then catalog)?

**Deep Analysis (When Issues Detected):**
```
Invoke: workflow-evaluation skill
- Phase 1: Build context (show_tree)
- Phase 2: Level-by-level analysis (PM first)
- Phase 3: Protocol verification
- Phase 4: Context handoff analysis
- Phase 5: Diagnosis
```

### Phase 5: Fix (If Needed)

When root cause identified:
```
Invoke: agent-improvement skill
- Gap analysis checklist
- Cognitive load analysis
- Protocol-based decomposition if needed
- Fix implementation
```

**The agent-improvement skill handles ALL fixes:**
- Protocol gaps -> create/update protocols
- Prompt issues -> update prompts
- Tool issues -> fix tool definitions
- Cognitive overload -> decompose via protocols

### Phase 6: Verification & Tracking

**Re-run scenario:**
```python
from tests.tools import compare_to_baseline, store_baseline

result_after = chat_with_pm(
    scenario.message,
    media_path=scenario.media_path,
    scenario_id=scenario.id
)

# Compare against known-good baseline
comparison = compare_to_baseline(result_after.trace_id, scenario.id)
if comparison["has_baseline"]:
    print(f"Matches: {comparison['matches']}")
    print(f"Deviations: {comparison['deviations']}")
    print(f"Metrics: {comparison['metrics']}")

# If this run is correct, store as new baseline
if all_criteria_passed:
    store_baseline(result_after.trace_id, scenario.id, notes="Verified correct behavior")
```

**Record findings:**
1. Create GitHub issue for tracking (if not already exists)
2. Use `record_evaluation()` to store in LangSmith
3. Update FINDINGS.md with evaluation summary
4. Mark scenario as regression test if fix verified

---

## GitHub Issue Tracking

### Creating Issues for Findings

When evaluation identifies issues, create GitHub issues for tracking:

```bash
# Create issue for identified problem
gh issue create \
  --title "[E2E] PM-01: Protocol not loaded before delegation" \
  --body "## Scenario
PM-01: Basic Catalog Request with Image

## Trace
trace_id: abc123

## Issue
PM delegated to visual_analyst without loading discovery_mindset protocol first.

## Expected
PM should load discovery_mindset protocol as FIRST action.

## Root Cause
[To be determined via workflow-evaluation]

## Labels
e2e-testing, pm, protocol-loading" \
  --label "e2e-testing" \
  --label "bug"
```

### Issue Labels

| Label | When to Use |
|-------|-------------|
| `e2e-testing` | All issues from this skill |
| `pm` | PM behavior issues |
| `analyst` | Analyst behavior issues |
| `specialist` | Specialist behavior issues |
| `protocol-loading` | Protocol not loaded or wrong protocol |
| `context-handoff` | Context not passed correctly |
| `hitl` | HITL flow issues |
| `regression` | Issue caused regression |

### Linking Issues to Scenarios

```bash
# List open e2e issues
gh issue list --label "e2e-testing" --state open

# Close issue when fix verified
gh issue close <issue_number> --comment "Fixed in commit abc123. Verified with trace xyz789."
```

### Issue Template

```markdown
## Scenario
[Scenario ID]: [Name]

## Trace
trace_id: [trace_id from LangSmith]

## Issue
[What went wrong - be specific]

## Expected Behavior
[What should have happened per system architecture]

## Actual Behavior
[What actually happened]

## Root Cause
[From workflow-evaluation analysis]

## Fix
[From agent-improvement - file and change]

## Verification
- [ ] Re-ran scenario
- [ ] Issue no longer reproduces
- [ ] No regressions
- Verification trace: [trace_id]
```

---

## Evaluation Criteria

### Per-Scenario Criteria

| Criterion | Check |
|-----------|-------|
| Protocol Loading | PM/agents loaded correct protocols FIRST |
| Dependency Graph | PM identified needed agents, mapped dependencies |
| Wave Execution | Analysts executed in correct waves (parallel when safe) |
| File Communication | PM passed all file paths to downstream agents |
| Approval Gate | PM read files, synthesized, presented to user |
| Execution Order | Creative before Catalog (when both needed) |
| HITL Compliance | Two-stage HITL (asset then data) |
| Verification Pivot | Asked user when findings contradicted context |

### Scoring

```
PASS: All criteria met
PARTIAL: Minor issues, workflow completed
FAIL: Critical criteria failed
ERROR: Execution error (trace incomplete)
```

---

## Test Suites

Defined in [SUITES.md](./SUITES.md). Common suites:

| Suite | Purpose | Duration |
|-------|---------|----------|
| `smoke` | Quick sanity check | ~5 min |
| `regression` | Full regression | ~30 min |
| `pm-analysis` | PM analysis phase | ~10 min |
| `pm-execution` | PM execution phase | ~10 min |
| `hitl` | Approval workflows | ~10 min |
| `failed-replays` | Re-run production failures | Variable |

---

## Supabase Integration

### Key Tables

| Table | Purpose |
|-------|---------|
| `products` | Real product data for scenarios |
| `product_assets` | Product images |
| `workflow_outcomes` | Production execution history |

**Note:** Test results are stored in LangSmith (via `record_evaluation`), not Supabase.

See [DATA_QUERIES.md](./DATA_QUERIES.md) for comprehensive query library.

---

## Anti-Patterns

| Don't | Why | Instead |
|-------|-----|---------|
| Skip protocol verification | Protocol loading is MANDATORY | Always check PM/agents loaded protocols |
| Assume routing without trace | Can't verify dependency graph | Use workflow-evaluation to check waves |
| Fix without GitHub issue | Lose tracking | Create issue first, close when verified |
| Ignore approval gate | Two-phase architecture is critical | Verify PM read files before presenting |
| Test execution without analysis | Misses Phase 1 issues | Test full flow including analysis |

---

## Related Files

| File | Purpose |
|------|---------|
| [SCENARIOS.md](./SCENARIOS.md) | Test scenario catalog |
| [SUITES.md](./SUITES.md) | Test suite definitions |
| [DATA_QUERIES.md](./DATA_QUERIES.md) | Supabase query library |
| [FINDINGS.md](./FINDINGS.md) | Evaluation findings log |

---

## Related Skills

| Skill | When to Invoke |
|-------|----------------|
| `autonomous-testing` | PM interaction, trace collection |
| `workflow-evaluation` | Deep trace analysis |
| `agent-improvement` | Diagnosing and fixing ALL issues |
