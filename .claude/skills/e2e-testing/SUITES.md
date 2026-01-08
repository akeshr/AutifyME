# Test Suites

Defines collections of scenarios for different testing purposes.

**Last Updated:** 2025-01-08

---

## Suite Schema

```yaml
suite_id: string              # Unique identifier
name: string                  # Human-readable name
description: string           # Purpose of this suite
estimated_duration: string    # Approximate runtime
trigger: string               # When to run (manual, pre-commit, daily, etc.)
scenarios: list[string]       # Scenario IDs to include
data_query: string            # Optional: Dynamic scenarios from Supabase
stop_on_failure: boolean      # Stop suite on first failure
parallel: boolean             # Run scenarios in parallel (independent only)
```

---

## Core Suites

### smoke

```yaml
suite_id: smoke
name: Smoke Test
description: |
  Quick sanity check to verify basic functionality is working.
  Tests core PM analysis -> approval gate -> execution flow.
estimated_duration: 5-10 minutes
trigger: manual, post-deploy
stop_on_failure: true
parallel: false
scenarios:
  - PM-01      # Full analysis chain (V -> P || C)
  - GATE-01   # Approval gate synthesis
  - HITL-01   # Creative asset approval
  - HITL-03   # Catalog data approval
```

### regression

```yaml
suite_id: regression
name: Full Regression
description: |
  Complete regression suite. All scenarios marked with regression: true.
  Run after any prompt/protocol changes.
estimated_duration: 30-45 minutes
trigger: manual, pre-release
stop_on_failure: false
parallel: false
scenarios:
  # PM Analysis Phase
  - PM-01      # Full analysis chain
  - PM-02      # Known product optimization
  - PM-03      # Text-only catalog query
  - PM-04      # Text-only market research
  - PM-05      # Catalog-first verification
  - PM-06      # Multi-image relationship
  - PM-07      # Cold start query

  # PM Approval Gate
  - GATE-01   # Synthesis and presentation
  - GATE-02   # Conflict detection
  - GATE-03   # User context contradiction

  # PM Execution Phase
  - EXEC-01   # Flow E (images first)
  - EXEC-02   # Flow D (catalog first)
  - EXEC-03   # Flow A (catalog only)
  - EXEC-05   # Direct update

  # Analysts
  - ANALYST-01  # Visual protocol loading
  - ANALYST-02  # Catalog chain link
  - ANALYST-03  # Multi-item detection

  # Specialists
  - SPEC-01   # Catalog verification
  - SPEC-02   # Creative asset HITL

  # HITL Scenarios
  - HITL-01   # Creative approval
  - HITL-02   # Creative rejection
  - HITL-03   # Catalog approval
  - HITL-04   # Catalog rejection edit
  - HITL-05   # Bare cancellation

  # Edge Cases
  - EDGE-01   # Media download
  - EDGE-02   # Protocol skip detection
  - EDGE-03   # Ambiguous yes
  - EDGE-05   # Empty message
  - EDGE-06   # Conflicting input

  # Integration
  - INT-01    # Full image to catalog
  - INT-02    # Text-only update
```

### pm-analysis

```yaml
suite_id: pm-analysis
name: PM Analysis Phase Tests
description: |
  Tests PM's behavior during Phase 1 (Intelligence).
  Protocol loading, wave execution, analyst delegation.
estimated_duration: 15 minutes
trigger: manual
stop_on_failure: false
parallel: false
scenarios:
  - PM-01      # Full analysis chain
  - PM-02      # Known product optimization
  - PM-03      # Text-only catalog query
  - PM-04      # Text-only market research
  - PM-05      # Catalog-first verification
  - PM-06      # Multi-image relationship
  - PM-07      # Cold start query
```

### pm-gate

```yaml
suite_id: pm-gate
name: PM Approval Gate Tests
description: |
  Tests PM's behavior at the approval gate.
  File reading, synthesis, conflict detection, presentation.
estimated_duration: 10 minutes
trigger: manual
stop_on_failure: false
parallel: false
scenarios:
  - GATE-01   # Synthesis and presentation
  - GATE-02   # Conflict detection
  - GATE-03   # User context contradiction
```

### pm-execution

```yaml
suite_id: pm-execution
name: PM Execution Phase Tests
description: |
  Tests PM's behavior during Phase 2 (Execution).
  Flow selection, specialist delegation, ID tracking.
estimated_duration: 15 minutes
trigger: manual
stop_on_failure: false
parallel: false
scenarios:
  - EXEC-01   # Flow E (images first)
  - EXEC-02   # Flow D (catalog first)
  - EXEC-03   # Flow A (catalog only)
  - EXEC-04   # Flow B (asset only)
  - EXEC-05   # Direct update
```

### analyst-behaviors

```yaml
suite_id: analyst-behaviors
name: Analyst Behavior Tests
description: |
  Tests individual analyst behaviors.
  Protocol loading, file reading, output writing.
estimated_duration: 10 minutes
trigger: manual
stop_on_failure: false
parallel: false
scenarios:
  - ANALYST-01  # Visual protocol loading
  - ANALYST-02  # Catalog chain link behavior
  - ANALYST-03  # Multi-item detection
```

### specialist-behaviors

```yaml
suite_id: specialist-behaviors
name: Specialist Behavior Tests
description: |
  Tests individual specialist behaviors.
  Verification, schema discovery, HITL compliance.
estimated_duration: 10 minutes
trigger: manual
stop_on_failure: false
parallel: false
scenarios:
  - SPEC-01   # Catalog verification
  - SPEC-02   # Creative asset HITL
```

### hitl-workflows

```yaml
suite_id: hitl-workflows
name: HITL Workflow Tests
description: |
  Tests all human-in-the-loop approval workflows.
  Both creative (asset) and catalog (data) stages.
estimated_duration: 15 minutes
trigger: manual
stop_on_failure: false
parallel: false
scenarios:
  # Creative HITL
  - HITL-01   # Approve creative
  - HITL-02   # Reject creative

  # Catalog HITL
  - HITL-03   # Approve catalog
  - HITL-04   # Reject catalog with edit

  # Cancellation
  - HITL-05   # Bare cancel
notes: |
  Each HITL scenario requires setup.
  Run after triggering appropriate specialist.
```

### edge-cases

```yaml
suite_id: edge-cases
name: Edge Case Tests
description: |
  Tests unusual inputs and boundary conditions.
  Run periodically to ensure robustness.
estimated_duration: 10 minutes
trigger: manual, weekly
stop_on_failure: false
parallel: true
scenarios:
  - EDGE-01   # Media download
  - EDGE-02   # Protocol skip detection
  - EDGE-03   # Ambiguous yes
  - EDGE-04   # Large tool results
  - EDGE-05   # Empty message
  - EDGE-06   # Conflicting input
```

### protocol-compliance

```yaml
suite_id: protocol-compliance
name: Protocol Compliance Check
description: |
  Verifies all agents load protocols correctly.
  Critical for system integrity.
estimated_duration: 10 minutes
trigger: manual, post-deploy
stop_on_failure: true
parallel: false
scenarios:
  - EDGE-02     # Protocol skip detection
  - ANALYST-01  # Visual protocol loading
  - ANALYST-02  # Catalog protocol loading
  - SPEC-01     # Specialist protocol loading
```

---

## Dynamic Suites (Query-Based)

### failed-replays

```yaml
suite_id: failed-replays
name: Replay Recent Failures
description: |
  Dynamically fetches and replays recent production failures.
  Use to verify fixes or identify patterns.
estimated_duration: variable
trigger: manual
stop_on_failure: false
parallel: false
data_query: |
  SELECT
    'REPLAY-' || id::text as scenario_id,
    message_text as message,
    media_id,
    trace_id as original_trace,
    error_type,
    error_message
  FROM workflow_outcomes
  WHERE success = false
    AND created_at > NOW() - INTERVAL '7 days'
  ORDER BY created_at DESC
  LIMIT 10
notes: |
  Scenarios are generated at runtime from query results.
  Each replay attempts the same input that previously failed.
```

### high-latency

```yaml
suite_id: high-latency
name: High Latency Investigation
description: |
  Replays workflows that took unusually long.
  Use to identify performance bottlenecks.
estimated_duration: variable
trigger: manual
stop_on_failure: false
parallel: false
data_query: |
  SELECT
    'PERF-' || id::text as scenario_id,
    message_text as message,
    media_id,
    trace_id as original_trace,
    duration_seconds
  FROM workflow_outcomes
  WHERE duration_seconds > 60
    AND created_at > NOW() - INTERVAL '7 days'
  ORDER BY duration_seconds DESC
  LIMIT 5
```

### image-scenarios

```yaml
suite_id: image-scenarios
name: Image-Based Tests
description: |
  Tests using real images from product assets.
  Use to verify visual analysis pipeline.
estimated_duration: 15-20 minutes
trigger: manual
stop_on_failure: false
parallel: false
scenarios:
  - PM-01       # Full analysis with image
  - PM-05       # Catalog-first verification
  - PM-06       # Multi-image relationship
  - ANALYST-01  # Visual protocol loading
  - ANALYST-03  # Multi-item detection
  - INT-01      # Full image to catalog flow
data_query: |
  SELECT
    'IMG-' || pa.id::text as scenario_id,
    'Catalog this product' as message,
    pa.storage_path as media_path
  FROM product_assets pa
  WHERE pa.asset_type = 'image'
  ORDER BY RANDOM()
  LIMIT 3
```

---

## Special Suites

### single-scenario

```yaml
suite_id: single-scenario
name: Single Scenario Runner
description: |
  Wrapper for running a single scenario by ID.
  Usage: Run with scenario_id parameter.
estimated_duration: variable
trigger: manual
stop_on_failure: true
parallel: false
scenarios: []
usage: |
  run_suite("single-scenario", scenario_id="PM-01")
```

### new-scenarios

```yaml
suite_id: new-scenarios
name: New Scenario Verification
description: |
  Runs scenarios that haven't been marked as regression yet.
  Use to verify new scenarios work before promoting.
estimated_duration: variable
trigger: manual
stop_on_failure: false
parallel: false
data_query: |
  SELECT scenario_id
  FROM test_scenarios
  WHERE regression = false
    AND NOT retired
  ORDER BY created_at DESC
  LIMIT 20
```

### by-tag

```yaml
suite_id: by-tag
name: Run by Tag
description: |
  Runs all scenarios matching a specific tag.
  Usage: Run with tag parameter.
estimated_duration: variable
trigger: manual
stop_on_failure: false
parallel: true
scenarios: []
usage: |
  # Run all analysis scenarios
  run_suite("by-tag", tag="analysis")

  # Run all protocol-loading scenarios
  run_suite("by-tag", tag="protocol-loading")

  # Run all hitl scenarios
  run_suite("by-tag", tag="hitl")
```

### by-phase

```yaml
suite_id: by-phase
name: Run by Phase
description: |
  Runs all scenarios for a specific system phase.
  Usage: Run with phase parameter.
estimated_duration: variable
trigger: manual
stop_on_failure: false
parallel: false
scenarios: []
usage: |
  # Run all analysis phase scenarios
  run_suite("by-phase", phase="analysis")

  # Run all approval gate scenarios
  run_suite("by-phase", phase="approval_gate")

  # Run all execution phase scenarios
  run_suite("by-phase", phase="execution")
```

---

## Suite Execution

### Running a Suite

```python
from tests.tools import chat_with_pm

def run_suite(suite_id: str, **params) -> SuiteResult:
    suite = get_suite(suite_id)

    # Get scenarios (static + dynamic)
    scenarios = get_suite_scenarios(suite, **params)

    results = []
    for scenario in scenarios:
        # Fetch data if needed
        test_data = fetch_scenario_data(scenario)

        # Execute
        result = chat_with_pm(
            message=scenario.message.format(**test_data),
            media_path=test_data.get('media_path')
        )

        # Evaluate
        evaluation = evaluate_result(result, scenario.expected)
        results.append(evaluation)

        # Stop on failure if configured
        if suite.stop_on_failure and not evaluation.passed:
            break

    return SuiteResult(suite_id, results)
```

### Suite Result Format

```yaml
suite_id: regression
run_id: uuid
started_at: timestamp
completed_at: timestamp
duration_seconds: float
total_scenarios: int
passed: int
failed: int
errors: int
skipped: int
results:
  - scenario_id: PM-01
    status: PASS
    trace_id: uuid
    duration_seconds: float
    issues: []
  - scenario_id: GATE-01
    status: FAIL
    trace_id: uuid
    duration_seconds: float
    issues:
      - type: MISSING_FILE_READ
        description: "PM did not read analysis files"
```

---

## Suite Maintenance

### Adding Scenarios to Suites

1. Create scenario in SCENARIOS.md
2. Run scenario individually to verify
3. Add to appropriate suite(s) here
4. If verified, add to `regression` suite

### Creating New Suites

1. Define suite with clear purpose
2. Select relevant scenarios
3. Set appropriate trigger and stop_on_failure
4. Document in this file

### Suite Dependencies

Some suites have dependencies:

| Suite | Depends On | Notes |
|-------|------------|-------|
| hitl-workflows | Prior specialist trigger | HITL needs pending approval |
| failed-replays | Supabase | Requires workflow_outcomes data |
| image-scenarios | Supabase | Requires product_assets data |

---

## Recommended Usage

| Situation | Suite |
|-----------|-------|
| Quick check after changes | `smoke` |
| Before releasing | `regression` |
| After PM prompt change | `pm-analysis` + `pm-gate` + `pm-execution` |
| After analyst prompt change | `analyst-behaviors` |
| After specialist prompt change | `specialist-behaviors` |
| After HITL changes | `hitl-workflows` |
| After protocol changes | `protocol-compliance` |
| Investigating failures | `failed-replays` |
| Performance issues | `high-latency` |
| Visual pipeline issues | `image-scenarios` |
| Weekly health check | `regression` + `edge-cases` |
