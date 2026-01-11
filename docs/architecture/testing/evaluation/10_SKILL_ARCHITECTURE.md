# Skill Architecture for Evaluation Framework

**Part of**: [Universal Evaluation Framework](00_INDEX.md)

**Version**: 4.0 - LLM as Judge & Eval Writer

**Status**: Design - Requires Full Skill Rewrite

---

## Overview

This document defines how Claude Code skills implement the **LLM as Judge** paradigm for the evaluation framework. Skills ARE the intelligence layer - they contain domain expertise, process knowledge, and decision criteria. No additional tooling layer required.

---

## Core Principle: Skills ARE the Interface

```text
WRONG MENTAL MODEL:
  Skill --> MCP Tool --> Python utility --> Result
  (Unnecessary indirection, loses agency)

CORRECT MENTAL MODEL:
  Skill (with complete instructions) --> Claude reasons --> Uses existing tools
  (Skills contain ALL the intelligence needed)
```

**Key insight**: Claude already knows when to invoke skills. The skills themselves contain:
- Domain expertise (what to look for)
- Process knowledge (how to investigate)
- Decision criteria (when to propose fixes)
- Output format (structured findings per 08_SCHEMAS.md)

---

## LLM as Judge: Two Modes

| Mode | Location | Purpose | Implementation |
|------|----------|---------|----------------|
| **Automated** | Model Graders in GradingOrchestrator | Per-scenario judging | Rubric-based, semantic similarity |
| **Deep Analysis** | Claude Code Skills | Cross-scenario investigation | /workflow-evaluation, /agent-improvement |

```text
+=========================================================================+
|                        LLM AS JUDGE LAYER                               |
+=========================================================================+
|                                                                         |
|  MODE 1: AUTOMATED JUDGING (per-scenario, in pipeline)                  |
|  +-------------------------------------------------------------------+  |
|  | Model Graders (03_GRADER_ARCHITECTURE.md)                         |  |
|  | - Runs during EvaluationPipeline._grade_batch()                   |  |
|  | - Rubric-based scoring                                            |  |
|  | - Semantic similarity checking                                    |  |
|  | - Fast, parallel execution                                        |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  MODE 2: DEEP INVESTIGATION (cross-scenario, on failures)               |
|  +-------------------------------------------------------------------+  |
|  | Claude Code Skills                                                |  |
|  |                                                                   |  |
|  | /workflow-evaluation                                              |  |
|  |   - Load traces hierarchically (L0 -> L1 -> L2)                   |  |
|  |   - Multi-track parallel investigation                            |  |
|  |   - Pattern matching against known failures                       |  |
|  |   - Root cause determination                                      |  |
|  |   - Generate fix proposals with confidence scores                 |  |
|  |                                                                   |  |
|  | /agent-improvement                                                |  |
|  |   - Implement approved fix proposals                              |  |
|  |   - Run k-out-of-n validation                                     |  |
|  |   - Update baselines on success                                   |  |
|  |   - Document patterns for reuse                                   |  |
|  |   - Create regression scenarios                                   |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+=========================================================================+
```

---

## Complete Skill Ecosystem

### Skill Dependency Graph

```text
                    TRIGGER
                       |
                       v
              +------------------+
              |  /e2e-testing    |  <-- Entry Point
              +------------------+
                       |
         +-------------+-------------+
         |                           |
         v                           v
+------------------+        +------------------+
| /workflow-       |        | /eval-coverage   |
| evaluation       |        | (gap analysis)   |
+------------------+        +------------------+
         |                           |
         v                           |
+------------------+                 |
| /agent-          |                 |
| improvement      |                 |
+------------------+                 |
         |                           |
         +-------------+-------------+
                       |
                       v
              +------------------+
              |  /eval-writer    |  <-- Scenario Generation
              +------------------+
```

### Skill Summary Table

| Skill | Purpose | Triggers | Outputs | Invokes |
|-------|---------|----------|---------|---------|
| `/e2e-testing` | Orchestrate evaluation cycle | Manual, CI/CD, scheduled | EvaluationReport | /workflow-evaluation, /eval-coverage |
| `/workflow-evaluation` | Deep failure investigation | Called by /e2e-testing | InvestigationSession | /agent-improvement |
| `/agent-improvement` | Implement and validate fixes | Called by /workflow-evaluation | ImprovementResult | /eval-writer |
| `/eval-writer` | Create evaluation scenarios | Multiple modes | Scenario | None |
| `/eval-coverage` | Identify coverage gaps | Scheduled, manual | CoverageReport | /eval-writer |

---

## Skill Specifications

### /e2e-testing (Entry Point)

**Status**: REWRITE REQUIRED

**Purpose**: Orchestrate the complete evaluation cycle from scenario loading through reporting.

**Triggers**:
- Manual invocation: `/e2e-testing --suite regression`
- CI/CD: On commit, on PR
- Scheduled: Daily regression runs

**Behavior**:

```text
PHASE 1: PREPARATION
- Load scenarios from LangSmith dataset (specified suite)
- Apply tag filters if provided
- Separate HITL scenarios from regular scenarios
- Initialize cost tracking

PHASE 2: EXECUTION
- Regular scenarios: Execute via chat_with_pm with hitl_mode="auto_approve"
- HITL scenarios: Execute via StatefulHITLTestHarness (actual blocking/approval)
- Respect parallelism limits (default: 5 concurrent)
- Capture all traces in LangSmith

PHASE 3: GRADING
- For each result, invoke GradingOrchestrator.grade()
- Aggregate judgments into EvaluationReport
- Calculate pass rates, pass@k, pass^k metrics

PHASE 4: ANALYSIS
- Compare to baseline (with smoothing for noise)
- Detect regressions (>5% drop triggers alert)
- Identify patterns in failures

PHASE 5: DOWNSTREAM TRIGGERS
- IF failures exist AND auto_investigate=true:
    Invoke /workflow-evaluation with failed scenario IDs
- IF coverage_check=true:
    Invoke /eval-coverage

PHASE 6: REPORTING
- Store report in Supabase
- Output summary to user
- Return EvaluationReport
```

**Schema Dependencies** (from 08_SCHEMAS.md):
- Input: `PipelineOptions`
- Output: `EvaluationReport`, `Judgment[]`
- Uses: `Scenario`, `RolloutResult`, `TraceForEval`

**Tools Used**:
- `mcp__supabase__execute_sql` - Load/store reports
- `Read` - Access scenario definitions
- `Bash` - Execute chat_with_pm via CLI

---

### /workflow-evaluation (LLM as Judge - Investigation)

**Status**: REWRITE REQUIRED

**Purpose**: Deep investigation of evaluation failures to determine root cause and propose fixes.

**Triggers**:
- Called by /e2e-testing on failures
- Manual invocation with report ID or trace IDs

**Behavior**:

```text
PHASE 1: CONTEXT LOADING
- Load EvaluationReport (if report_id provided)
- OR load specific traces (if trace_ids provided)
- Initialize token budget tracking (50,000 total)

PHASE 2: HIERARCHICAL TRACE ANALYSIS
- Load L0 (overview) for ALL failed traces
  - Agent names, tool names, pass/fail, tokens, latency
  - ~750 tokens per trace
  - Track remaining budget

- Prioritize traces by severity:
  1. HITL violations (highest)
  2. State corruption
  3. Schema violations
  4. Semantic failures

- Load L1 (focused) for TOP 3 traces
  - Focus areas: agent:pm, tool:X, error
  - ~2,250 tokens per focus area
  - Max 2 focus areas per trace

- Load L2 (deep) ONLY IF:
  - Budget remaining > 7,500 tokens
  - L1 analysis inconclusive
  - Single best candidate trace

PHASE 3: PATTERN MATCHING
- Compare failure signatures to known patterns:
  - Check docs/architecture/testing/evaluation/patterns/
  - Match on: error type, agent involved, tool involved
  - If match found: reuse known fix approach

PHASE 4: ROOT CAUSE ANALYSIS
- For each failure cluster:
  - Identify common thread
  - Trace back to source (prompt? tool? context?)
  - Determine if systemic or edge case

PHASE 5: FIX PROPOSAL GENERATION
- For each root cause:
  - Generate fix hypothesis
  - Estimate confidence (0.0-1.0)
  - Identify validation scenarios
  - Estimate effort/risk

PHASE 6: OUTPUT
- Present findings to user
- IF confidence > 0.7 AND user approves:
    Invoke /agent-improvement with fix proposal
- ELSE:
    Request human guidance
```

**Schema Dependencies** (from 08_SCHEMAS.md):
- Input: `InvestigationTrigger`, `Judgment[]`
- Output: `InvestigationSession`, `FindingWithFix[]`
- Uses: `TraceOverview`, `TraceFocus`, `TraceDeep`, `TokenBudget`

**Tools Used**:
- `Read` - Load traces from LangSmith exports
- `Grep` - Search for patterns in trace data
- `mcp__supabase__execute_sql` - Query pattern library

**Token Budget Enforcement**:

```text
Budget: 50,000 tokens total

Allocation:
- L0 for all failures: N * 750 tokens
- L1 for top 3: 3 * 2 * 2,250 = 13,500 tokens
- L2 for 1 trace: 7,500 tokens
- Analysis overhead: ~5,000 tokens

Example with 10 failures:
- L0: 10 * 750 = 7,500
- L1: 13,500
- L2: 7,500
- Overhead: 5,000
- Total: 33,500 (within budget)

If budget exceeded:
- Skip L2 entirely
- Reduce L1 focus areas
- Produce shallow analysis with recommendation for manual review
```

---

### /agent-improvement (Fix Implementation)

**Status**: REWRITE REQUIRED

**Purpose**: Implement approved fix proposals and validate they resolve the issue without regression.

**Triggers**:
- Called by /workflow-evaluation on fix approval
- Manual invocation with fix proposal

**Behavior**:

```text
PHASE 1: FIX UNDERSTANDING
- Load fix proposal from /workflow-evaluation
- Identify target files and changes
- Assess risk level (low/medium/high)

PHASE 2: IMPLEMENTATION
- Apply fix to codebase
- For prompt changes: Edit prompt files
- For tool changes: Edit tool implementations
- For schema changes: Edit schema definitions
- Preserve existing tests

PHASE 3: VALIDATION (k-out-of-n)
- Run the SPECIFIC failing scenario k times (default k=3)
- From a larger sample n (default n=5)
- Pass criteria: k successes out of n runs
- This validates the fix actually works

PHASE 4: REGRESSION CHECK
- Run FULL regression suite
- Compare to pre-fix baseline
- Alert if any NEW failures introduced

PHASE 5: BASELINE UPDATE
- IF validation passes AND no regressions:
    Update baseline scores
    Mark improvement as "validated"
- ELSE:
    Revert changes
    Report failure to user

PHASE 6: DOCUMENTATION
- Add pattern to pattern library:
  - Failure signature
  - Root cause
  - Fix approach
  - Validation results
- Create regression scenario via /eval-writer

PHASE 7: OUTPUT
- Report improvement result
- Invoke /eval-writer (from-failure mode) to create regression scenario
```

**Schema Dependencies** (from 08_SCHEMAS.md):
- Input: `FixProposal`
- Output: `ImprovementResult`
- Uses: `Scenario`, `Judgment`, `Pattern`

**Tools Used**:
- `Edit` - Apply code changes
- `Bash` - Run validation suite
- `Write` - Create pattern documentation
- `mcp__supabase__execute_sql` - Update baselines

**k-out-of-n Validation**:

```text
Why k-out-of-n instead of simple pass/fail?
- Agent behavior has variance
- Single pass might be luck
- Single fail might be flaky

Default: k=3, n=5
- Run scenario 5 times
- Require 3+ passes
- Handles ~40% flake rate

For critical fixes (HITL, security):
- Use k=5, n=5 (must pass ALL)
- Zero tolerance for failures
```

---

### /eval-writer (Scenario Generation)

**Status**: NEW SKILL

**Purpose**: Create high-quality evaluation scenarios from various sources with quality gates.

**Triggers**:
- `from-trace`: Production trace ID
- `from-failure`: After /agent-improvement creates a fix
- `from-spec`: Feature specification document path
- `from-gap`: Coverage gap identified by /eval-coverage
- `adversarial`: Security audit requirement
- `mutate`: Existing scenario ID for variation generation

**Mode Specifications**:

#### Mode: from-trace

```text
INPUT: trace_id, trace_type ("success" | "failure" | "interesting")

STEP 1: Load Trace
- Read trace at L1 level (focused detail)
- Extract: input message, media paths, context
- Extract: routing chain, tools called
- Extract: final output, state changes
- Determine trace outcome

STEP 2: Analyze Testable Behavior
- What capability does this demonstrate?
- What could go wrong?
- Is this common pattern or edge case?
- Which of 7 categories does this fit?

STEP 3: Abstract Data
- Replace specific values with [placeholders]:
  - "iPhone 15 Pro" --> "[product_name]"
  - "john@example.com" --> "[user_email]"
  - "2024-01-15" --> "[date]"
  - "$999.00" --> "[price]"
  - "ord_123abc" --> "[order_id]"
- Preserve structure and relationships
- Keep edge case characteristics

STEP 4: Select Graders
- Output contains schema? --> schema_compliance (code)
- Tests semantic quality? --> response_quality (model)
- Changes database state? --> state_verification (code)
- HITL scenario? --> Add PATH_STRICT mode

STEP 5: Set Expectations
- expected.output: What patterns should response contain?
- expected.behavior: What actions required?
- expected.state_changes: What DB changes?
- expected.routing: What delegation path? (null for output-only)

STEP 6: Run Quality Gates (see below)

STEP 7: Add to Dataset
- Assign to appropriate LangSmith dataset
- Tag with source trace ID
- Return scenario_id
```

#### Mode: from-failure

```text
INPUT: investigation_session_id, fix_proposal_id

STEP 1: Load Investigation Context
- Root cause identified
- Fix that was applied
- Original failing trace
- Pattern documented

STEP 2: Create Minimal Reproducing Case
- What input triggered the failure?
- What context was necessary?
- Strip unnecessary complexity
- Keep ONLY what's needed to trigger the bug

STEP 3: Define Expected Behavior
- What SHOULD have happened (positive assertion)
- What MUST NOT happen (negative assertion - the bug)
- Both assertions in grading config

STEP 4: Select Strict Graders
- Regression tests need high precision
- Code graders preferred (deterministic)
- Lower thresholds (strict pass/fail)
- pass_threshold: 0.95 (near-perfect required)

STEP 5: Link to Pattern
- Reference pattern ID in metadata
- Enable pattern reuse tracking
- Support pattern evolution

STEP 6: Run Quality Gates

STEP 7: Add to Regression Dataset
- Tag: "regression", "from_failure", pattern_id
- Priority: HIGH (run in every CI)
```

#### Mode: from-spec

```text
INPUT: spec_file_path (markdown feature specification)

STEP 1: Parse Specification
- Extract "The system should..." statements
- Extract "When X, then Y" conditions
- Extract acceptance criteria
- Identify edge cases mentioned

STEP 2: Generate Scenario Pairs
For each testable claim:
- POSITIVE scenario: Test that it works as specified
- NEGATIVE scenario: Test graceful handling when preconditions not met

STEP 3: Map to Existing Capabilities
- Check if scenario overlaps with existing
- If overlap: suggest enhancement, not duplicate
- If novel: proceed with creation

STEP 4: Select Appropriate Graders
- Based on claim type (schema, state, semantic)

STEP 5: Run Quality Gates

STEP 6: Add to Capability Dataset
- Tag: "capability", "from_spec", feature_name
- Link back to spec document
```

#### Mode: adversarial

```text
INPUT: security_category, attack_type

CATEGORIES:
- prompt_injection: Direct, indirect, encoded
- data_leak: Cross-tenant, sensitive field, PII
- boundary_violation: HITL bypass, unauthorized actions
- resource_abuse: Token exhaustion, loops

STEP 1: Generate Attack Scenario
- Craft malicious input for attack type
- Include context that enables the attack
- Define what successful attack looks like

STEP 2: Define Defense Expectations
- expected.output: Rejection message (NOT leaked data)
- expected.behavior: ["MUST_NOT_LEAK", "MUST_REJECT"]
- expected.state_changes: None (attack should be blocked)

STEP 3: Select Security Graders
- security_boundary (code): Check no leak occurred
- rejection_detection (code): Check proper rejection
- NO model graders (must be deterministic)

STEP 4: Safety Validation
- Ensure scenario doesn't actually cause harm in testing
- Sandboxed execution only
- No persistent malicious state

STEP 5: Run Quality Gates

STEP 6: Add to Security Dataset
- Tag: "security", "adversarial", attack_type
- Priority: HIGH
```

#### Mode: mutate

```text
INPUT: existing_scenario_id

STEP 1: Load Existing Scenario
- Get full scenario definition
- Understand what it tests

STEP 2: Generate Meaningful Variations
- Boundary values (empty, max length, special chars)
- Missing required fields
- Malformed inputs (wrong types, invalid formats)
- Context variations (missing context, extra context)
- Timing variations (concurrent requests)

STEP 3: Predict Expected Behavior
- For each variation, determine:
  - Should it pass? With what score?
  - Should it fail gracefully?
  - What error is expected?

STEP 4: Filter Meaningful Mutations
- Skip mutations that test same thing as original
- Skip mutations that are noise (random changes)
- Keep mutations that test distinct edge cases

STEP 5: Run Quality Gates

STEP 6: Add to Edge Case Dataset
- Tag: "edge_case", "mutation", source_scenario_id
- Link to parent scenario
```

**Quality Gates** (All Modes):

```text
GATE 1: SCHEMA VALIDATION
- Scenario conforms to Scenario schema (08_SCHEMAS.md)
- All required fields present
- Types correct
- FAIL: Reject scenario, report schema errors

GATE 2: GRADER APPROPRIATENESS
- Schema check --> Code grader (not model)
- Semantic quality --> Model grader (not code)
- State changes --> Code grader with SQL
- MISMATCH: Reject scenario, suggest correct graders

GATE 3: DRY RUN (pass@1)
- Execute scenario once
- Verify graders produce meaningful output
- Catch: grader errors, impossible expectations
- FAIL: Reject scenario, report execution errors

GATE 4: CONSISTENCY CHECK (pass^3)
- Execute scenario 3 times
- For deterministic checks: must pass all 3
- For semantic checks: allow variance but flag high variance
- FLAKY: Warn user, suggest investigation or rejection

GATE 5: BALANCE CHECK
- Query current dataset balance (positive/negative ratio)
- Target: ~50/50
- IMBALANCED: Warn user, suggest counterpart scenario

GATE 6: DUPLICATE CHECK
- Compute semantic similarity to existing scenarios
- Threshold: 90% similarity = duplicate
- DUPLICATE: Reject scenario, point to existing

GATE 7: ABSTRACTION VALIDATION
- No hardcoded real data (names, prices, IDs, emails)
- Proper [placeholder] usage
- Reusable across contexts
- CONCRETE DATA: Warn user, auto-abstract if possible
```

**Schema Dependencies** (from 08_SCHEMAS.md):
- Output: `Scenario`
- Uses: `ScenarioInput`, `Expected`, `GradingConfig`, `ScenarioMetadata`

**Tools Used**:
- `Read` - Load traces, specs, existing scenarios
- `Grep` - Search for similar scenarios
- `Write` - Create scenario files (if file-based)
- `mcp__supabase__execute_sql` - Add to LangSmith datasets
- `Bash` - Execute dry run validation

---

### /eval-coverage (Gap Analysis)

**Status**: NEW SKILL

**Purpose**: Identify coverage gaps in evaluation scenarios and trigger scenario generation.

**Triggers**:
- Scheduled: Weekly
- Post-release: After major deployments
- Manual: On demand

**Behavior**:

```text
PHASE 1: LOAD CURRENT STATE
- Query all scenarios from LangSmith datasets
- Load failure taxonomy (02_FAILURE_TAXONOMY.md)
- Load 7 scenario categories (04_SCENARIO_FRAMEWORK.md)

PHASE 2: MAP TO FAILURE PILLARS
For each of 5 pillars:
- Intent Understanding
- Routing & Delegation
- Context Utilization
- State Management
- Output Quality

Count scenarios testing each pillar.
Calculate coverage percentage.

PHASE 3: MAP TO SCENARIO CATEGORIES
For each of 7 categories:
1. Happy Path
2. Edge Cases
3. Error Recovery
4. Multi-turn
5. HITL Compliance
6. Performance
7. Security

Count scenarios in each category.
Calculate coverage percentage.

PHASE 4: IDENTIFY GAPS
- Pillars with <10% of total scenarios = CRITICAL GAP
- Categories with <5% of total scenarios = CRITICAL GAP
- Missing combinations (e.g., "Intent + Security") = GAP

PHASE 5: PRIORITIZE GAPS
Priority scoring:
- HITL/Security gaps: +10 priority
- Recent failure cluster in area: +5 priority
- No scenarios at all: +3 priority
- Below target coverage: +1 priority

PHASE 6: GENERATE GAP-FILLING SCENARIOS
For top N gaps (default N=5):
- Invoke /eval-writer (from-gap mode)
- Provide: pillar, category, context

PHASE 7: OUTPUT
- CoverageReport with percentages
- Gap list with priorities
- Scenarios created (IDs)
```

**Schema Dependencies**:
- Output: `CoverageReport` (new schema)
- Uses: `Scenario`, `ScenarioMetadata`

---

## Skill Invocation Contracts

### Contract: /e2e-testing --> /workflow-evaluation

```yaml
trigger_condition:
  - report.failures.length > 0
  - options.auto_investigate == true

input_passed:
  investigation_trigger:
    type: "eval_failure"
    eval_report_id: report.id
    scenario_ids: [failed_judgment.scenario_id for each failure]

  failed_judgments: [Judgment objects for failures]

expected_output:
  investigation_session:
    id: string
    findings: FindingWithFix[]
    budget_status: { used: int, remaining: int }
```

### Contract: /workflow-evaluation --> /agent-improvement

```yaml
trigger_condition:
  - finding.confidence > 0.7
  - user_approved == true

input_passed:
  fix_proposal:
    id: string
    finding_id: string
    target_files: string[]
    changes: ChangeSpec[]
    validation_scenarios: string[]
    confidence: float

expected_output:
  improvement_result:
    success: boolean
    validation_passed: boolean
    regression_check_passed: boolean
    baseline_updated: boolean
    pattern_id: string | null
```

### Contract: /agent-improvement --> /eval-writer

```yaml
trigger_condition:
  - improvement_result.success == true

input_passed:
  mode: "from-failure"
  investigation_session_id: string
  fix_proposal_id: string
  pattern_id: string

expected_output:
  scenario:
    id: string
    quality_gate_results: GateResult[]
    added_to_dataset: string
```

### Contract: /eval-coverage --> /eval-writer

```yaml
trigger_condition:
  - gap.priority > threshold

input_passed:
  mode: "from-gap"
  gap:
    pillar: string
    category: string
    priority: int
    context: string

expected_output:
  scenario:
    id: string
    quality_gate_results: GateResult[]
    added_to_dataset: string
```

---

## Rewrite Requirements

### Existing Skills to Rewrite

| Skill | Current State | Required Changes |
|-------|---------------|------------------|
| `workflow-evaluation` | Generic investigation | Add hierarchical trace loading, token budgeting, pattern matching |
| `agent-improvement` | Generic fixes | Add k-out-of-n validation, baseline updates, pattern documentation |
| `autonomous-testing` | Separate framework | Merge into /e2e-testing, deprecate |

### New Skills to Create

| Skill | Priority | Complexity |
|-------|----------|------------|
| `/eval-writer` | P0 - Critical | High (6 modes, 7 gates) |
| `/eval-coverage` | P1 - Important | Medium |

### Shared Utilities (Embedded in Skills)

These are NOT separate Python modules - they are knowledge/instructions embedded in skill prompts:

| Utility | Description | Used By |
|---------|-------------|---------|
| Hierarchical Trace Loading | L0/L1/L2 pattern | /workflow-evaluation |
| Token Budget Management | Track and enforce | /workflow-evaluation |
| Quality Gates | 7 validation gates | /eval-writer |
| Pattern Matching | Compare to known patterns | /workflow-evaluation |
| k-out-of-n Validation | Statistical validation | /agent-improvement |

---

## Integration Flow

```text
                              CONTINUOUS IMPROVEMENT LOOP
                              ============================

                     +--------------------------------------+
                     |         PRODUCTION                   |
                     |   User --> PM --> Specialists        |
                     |              |                       |
                     |        [LangSmith Trace]             |
                     +--------------------------------------+
                                    |
           +------------------------+------------------------+
           |                        |                        |
           v                        v                        v
    +-------------+         +-------------+         +-------------+
    | Success     |         | Failure     |         | Interesting |
    | trace       |         | trace       |         | edge case   |
    +-------------+         +-------------+         +-------------+
           |                        |                        |
           +------------------------+------------------------+
                                    |
                                    v
                     +--------------------------------------+
                     |          /eval-writer                |
                     |          (from-trace mode)           |
                     |                                      |
                     |   Analyze --> Abstract --> Scenario  |
                     +--------------------------------------+
                                    |
                                    v
                     +--------------------------------------+
                     |       LangSmith Datasets             |
                     |   +----------------------------+     |
                     |   | Capability | Regression   |     |
                     |   | Security   | Edge Cases   |     |
                     |   +----------------------------+     |
                     +--------------------------------------+
                                    |
                        +-----------+-----------+
                        | Scheduled / CI / Manual|
                        +-----------------------+
                                    |
                                    v
                     +--------------------------------------+
                     |           /e2e-testing               |
                     |                                      |
                     |   Load --> Execute --> Grade         |
                     +--------------------------------------+
                                    |
                    +---------------+---------------+
                    |                               |
                    v                               v
             +-------------+                +-------------+
             |    PASS     |                |    FAIL     |
             |             |                |             |
             |  Update     |                |  Trigger    |
             |  baseline   |                |  /workflow- |
             |             |                |  evaluation |
             +-------------+                +-------------+
                                                   |
                                                   v
                                    +--------------------------------------+
                                    |       /workflow-evaluation           |
                                    |                                      |
                                    |   Load Traces --> Investigate -->    |
                                    |   Root Cause --> Fix Proposal        |
                                    +--------------------------------------+
                                                   |
                                                   v (approved)
                                    +--------------------------------------+
                                    |       /agent-improvement             |
                                    |                                      |
                                    |   Apply Fix --> Validate k/n -->     |
                                    |   Update Baseline --> Document       |
                                    +--------------------------------------+
                                                   |
                                                   v
                                    +--------------------------------------+
                                    |          /eval-writer                |
                                    |          (from-failure mode)         |
                                    |                                      |
                                    |   Create regression scenario         |
                                    +--------------------------------------+
                                                   |
                                                   v
                                            [Back to Datasets]


                     PARALLEL: COVERAGE ANALYSIS
                     ===========================

                     +--------------------------------------+
                     |         /eval-coverage               |
                     |         (weekly schedule)            |
                     |                                      |
                     |   Analyze --> Find Gaps --> Prioritize|
                     +--------------------------------------+
                                    |
                                    v
                     +--------------------------------------+
                     |          /eval-writer                |
                     |          (from-gap mode)             |
                     |                                      |
                     |   Generate gap-filling scenarios     |
                     +--------------------------------------+
```

---

## Implementation Order

1. **Phase 1**: Create `/eval-writer` skill (foundation for all scenario creation)
2. **Phase 2**: Rewrite `/workflow-evaluation` with hierarchical loading + patterns
3. **Phase 3**: Rewrite `/agent-improvement` with k-out-of-n + baseline updates
4. **Phase 4**: Rewrite `/e2e-testing` as orchestrator
5. **Phase 5**: Create `/eval-coverage` skill
6. **Phase 6**: Deprecate `autonomous-testing` (merged into /e2e-testing)

---

## Related Documents

- [00_INDEX.md](00_INDEX.md) - Framework overview
- [03_GRADER_ARCHITECTURE.md](03_GRADER_ARCHITECTURE.md) - Model Graders (automated LLM as Judge)
- [05_INTELLIGENCE_LAYER.md](05_INTELLIGENCE_LAYER.md) - Investigation concepts
- [08_SCHEMAS.md](08_SCHEMAS.md) - All data models used by skills
- [09_IMPLEMENTATION_GUIDE.md](09_IMPLEMENTATION_GUIDE.md) - Python implementation bootstrap
