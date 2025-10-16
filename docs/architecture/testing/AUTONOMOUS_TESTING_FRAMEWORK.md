# Autonomous Testing Framework - Claude-Orchestrated Test-Analyze-Improve Loop

**Date**: 2025-01-16
**Status**: 🔬 DESIGN
**Purpose**: Enable Claude (Jarvis) to autonomously test, analyze, and improve the AutifyME agentic system through intelligent tool orchestration

---

## Executive Summary

The Autonomous Testing Framework equips Claude (Jarvis) with tools to execute test scenarios, analyze execution traces hierarchically, validate database state, identify issues, generate improvements, and validate fixes in a continuous test-analyze-improve loop. Unlike traditional autonomous testing systems, **Claude is the intelligent orchestrator**—using tools as extensions to reason about system behavior, diagnose root causes, and propose targeted improvements. This conversational, collaborative approach combines human judgment with automated execution for rapid iteration and systematic quality improvement.

**Core Innovation**: Hierarchical lazy-loading trace analysis reduces token costs by 25x (50K → 2K tokens per iteration) by fetching trace structure first, then drilling down only where issues are detected.

**Key Difference**: This is not another autonomous agent system running in the background—it's a suite of tools for Claude to manually orchestrate testing workflows, with you (the user) guiding priorities and approving improvements.

---

## Table of Contents

1. [Architectural Context](#architectural-context)
2. [Core Architecture](#core-architecture)
3. [Tool Specifications](#tool-specifications)
4. [Hierarchical Analysis Strategy](#hierarchical-analysis-strategy)
5. [LangSmith Integration](#langsmith-integration)
6. [Supabase MCP Integration](#supabase-mcp-integration)
7. [Workflow Patterns](#workflow-patterns)
8. [Issue Diagnosis Framework](#issue-diagnosis-framework)
9. [Improvement Generation](#improvement-generation)
10. [Reporting Templates](#reporting-templates)
11. [Implementation Phases](#implementation-phases)
12. [Success Criteria](#success-criteria)
13. [Complete Usage Example](#complete-usage-example)
14. [Technical Specifications](#technical-specifications)
15. [Best Practices](#best-practices)

---

## Architectural Context

### Current Testing Infrastructure

**Existing Tools**:
- **`simulate.py`**: Full workflow simulation with HITL support via ConsoleChannel
- **`conversation.py`**: Multi-turn scenario testing from YAML definitions
- **`pm_chat.py`**: Direct PM invocation for fast iteration
- **Pytest suite**: Unit, integration, and E2E tests

**Current Workflow**:
1. Developer runs `simulate.py` or `conversation.py` manually
2. Observes console output for errors/issues
3. Manually inspects LangSmith traces if needed
4. Manually queries Supabase to validate DB state
5. Identifies issues through manual analysis
6. Fixes prompts/code manually
7. Re-runs tests to validate

**Gaps**:
- ❌ No systematic improvement loop
- ❌ Manual trace analysis is slow and error-prone
- ❌ No automated root cause identification
- ❌ No improvement validation workflow
- ❌ No regression test generation from production failures
- ❌ Expensive LangSmith trace fetching (full dumps = 50K+ tokens)

### Solution: Claude-Orchestrated Testing

**Vision**: Equip Claude with intelligent tools to automate the test-analyze-improve cycle while maintaining human oversight.

**Architecture**:
```
User (You)
    ↓
    "Jarvis, test cataloging_with_image and find issues"
    ↓
Claude (Jarvis) - Intelligent Orchestrator
    ↓
    Uses Tools:
    - execute_scenario() → Run workflow
    - get_trace_structure() → Lightweight analysis
    - analyze_failure_chain() → Focused investigation
    - quick_db_check() → Validate DB state
    - generate_improvement() → Propose fixes
    - apply_improvement() → Apply with backup
    ↓
    Reports findings with evidence and reasoning
    ↓
User approves/rejects improvements
    ↓
Claude validates improvements and continues
```

**Key Principles**:
1. **Claude is the orchestrator**: No autonomous background agent—Claude reasons, decides, explains
2. **Conversational collaboration**: User guides priorities, Claude executes and reports
3. **Hierarchical analysis**: Start lightweight, drill down only where needed
4. **Evidence-based**: Every finding backed by trace data, DB state, or output analysis
5. **Human-in-the-loop**: Improvements require user approval (except auto-approved prompt changes)

---

## Core Architecture

### Claude as Orchestrator

**Role**: Claude (Jarvis) serves as the intelligent testing orchestrator, using tools to:
- Execute test scenarios via `simulate.py`
- Analyze execution traces from LangSmith
- Validate database state via Supabase MCP
- Identify root causes of failures
- Generate improvement proposals
- Validate fixes through re-testing
- Report findings with clear evidence

**NOT an Autonomous Agent**: Claude doesn't run in the background. You invoke Claude with testing requests, Claude executes and reports, you provide guidance.

### Tool Categories

```
┌─────────────────────────────────────────────────────────────┐
│  CLAUDE (JARVIS) - Intelligent Testing Orchestrator        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [EXECUTION TOOLS]                                          │
│    → execute_scenario(scenario_id, hitl_mode)              │
│    → execute_conversation(scenario_yaml)                    │
│                                                             │
│  [ANALYSIS TOOLS - Level 0: Overview]                       │
│    → get_trace_structure(trace_id) - 500 tokens            │
│    → get_scenario_outcome(thread_id)                        │
│    → quick_db_check(scenario_id) - via MCP                  │
│                                                             │
│  [ANALYSIS TOOLS - Level 1: Focused]                        │
│    → analyze_failure_chain(run_id) - 1,500 tokens          │
│    → analyze_decision_point(run_id)                         │
│    → validate_structured_output(run_id, schema)             │
│    → get_product_record(product_id) - via MCP               │
│                                                             │
│  [ANALYSIS TOOLS - Level 2: Deep Dive]                      │
│    → get_full_run_details(run_id) - expensive, rare        │
│    → trace_data_lineage(field, run_id)                      │
│    → compare_traces(run_id_1, run_id_2)                     │
│                                                             │
│  [IMPROVEMENT TOOLS]                                        │
│    → generate_prompt_improvement(issue, prompt, examples)   │
│    → generate_code_fix(issue, file, context)                │
│    → apply_improvement(type, file, changes)                 │
│    → create_regression_test(scenario, trace, issue)         │
│                                                             │
│  [HELPER TOOLS]                                             │
│    → load_scenario_list(pattern)                            │
│    → select_next_scenario(queue, history)                   │
│    → compare_execution_metrics(baseline, new)               │
│    → generate_iteration_report(execution, issues, fixes)    │
│                                                             │
│  [SUPABASE MCP TOOLS]                                       │
│    → mcp__supabase__execute_sql(query)                      │
│    → mcp__supabase__list_tables(schemas)                    │
│    → mcp__supabase__get_advisors(type)                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Hierarchical Analysis Strategy

**Core Innovation**: Fetch trace structure first (metadata only), then drill down selectively.

**Traditional Approach** (Naive):
```python
# ❌ Expensive and wasteful
trace_dump = langsmith_client.get_full_trace(trace_id)  # 50K+ tokens
# Parse everything (most irrelevant)
# Analyze entire tree
```

**Hierarchical Approach** (Intelligent):
```python
# ✅ Efficient and targeted
# Level 0: Overview (500 tokens)
structure = get_trace_structure(trace_id)
# Returns: {run_hierarchy, run_metadata, failed_runs, slow_runs}

if structure.failed_runs:
    # Level 1: Focused (1,500 tokens)
    for failed_run in structure.failed_runs:
        analysis = analyze_failure_chain(failed_run)
        # Only fetches failed run + immediate context

    if not analysis.root_cause_clear:
        # Level 2: Deep dive (rare, variable tokens)
        details = get_full_run_details(failed_run)
```

**Token Savings**: 25x reduction (50,000 → 2,000 tokens per iteration)

---

## Tool Specifications

### Execution Tools

#### `execute_scenario`

```python
@tool
def execute_scenario(
    scenario_id: str,
    hitl_mode: str = "auto_approve",
    media_path: Optional[str] = None
) -> ExecutionResult:
    """Execute test scenario via simulate.py and return execution summary.

    This is Claude's primary execution tool. Runs a full workflow including
    Runner → PM → Department → Specialists → Tools → HITL (if configured).

    Args:
        scenario_id: Scenario identifier (e.g., "cataloging_with_image")
        hitl_mode: HITL behavior - "auto_approve" | "auto_reject" | "auto_edit" | "interactive"
        media_path: Optional path to media file for testing

    Returns:
        ExecutionResult: {
            trace_id: str,           # LangSmith root trace ID
            run_id: str,             # Top-level PM run ID
            thread_id: str,          # LangGraph thread ID
            success: bool,           # Did scenario succeed?
            duration: float,         # Total execution time (seconds)
            cost: float,             # Total cost ($)
            error: Optional[str],    # Error message if failed
            messages_sent: List[dict], # All messages sent via channel
            approval_triggered: bool   # Was HITL approval triggered?
        }

    Implementation:
        Programmatically invokes simulate.py:
        - Sets up ConsoleChannel with specified hitl_mode
        - Creates WorkflowRunner with checkpointer
        - Calls runner.handle_message(sender, text, media_id)
        - Captures trace_id from LangSmith context
        - Captures execution metadata
        - Returns structured result

    Usage Example:
        result = execute_scenario("cataloging_with_image", "auto_approve")
        if not result.success:
            # Analyze failure
            trace = get_trace_structure(result.trace_id)
    """
```

#### `execute_conversation`

```python
@tool
def execute_conversation(
    scenario_yaml: str
) -> ConversationResult:
    """Execute multi-turn conversation scenario from YAML definition.

    Args:
        scenario_yaml: Path to YAML scenario file (e.g., "tests/scenarios/greeting_to_cataloging.yaml")

    Returns:
        ConversationResult: {
            success: bool,
            turns: int,
            trace_ids: List[str],    # One per turn
            thread_id: str,
            total_duration: float,
            total_cost: float,
            failed_turn: Optional[int]  # Which turn failed (if any)
        }

    Implementation:
        Uses conversation.py infrastructure:
        - Loads YAML scenario
        - Executes each turn sequentially
        - Validates conversation history preservation
        - Captures trace IDs for each turn

    Usage Example:
        result = execute_conversation("tests/scenarios/greeting_to_cataloging.yaml")
        if not result.success:
            # Analyze failed turn
            failed_trace = result.trace_ids[result.failed_turn]
    """
```

### Analysis Tools - Level 0 (Overview)

#### `get_trace_structure`

```python
@tool
def get_trace_structure(
    trace_id: str
) -> TraceStructure:
    """Get lightweight trace structure - Claude's first analysis step.

    Fetches ONLY metadata, not full inputs/outputs. This is the foundation
    of hierarchical analysis - provides overview so Claude can decide where
    to drill down.

    Args:
        trace_id: LangSmith trace ID

    Returns:
        TraceStructure: {
            run_hierarchy: Dict[str, List[str]],  # {parent_run_id: [child_run_ids]}
            run_metadata: Dict[str, RunMetadata], # {run_id: {name, status, duration, cost, error_type}}
            failed_runs: List[str],               # Run IDs with errors
            slow_runs: List[str],                 # Runs above p95 latency
            expensive_runs: List[str],            # Runs above cost threshold
            total_runs: int,
            total_duration: float,
            total_cost: float
        }

    RunMetadata: {
        name: str,               # "PM" | "CatalogingDept" | "ImageAnalysisSpecialist" | "save_product"
        run_type: str,           # "chain" | "llm" | "tool" | "agent"
        status: str,             # "success" | "error"
        duration: float,
        cost: float,
        error_type: Optional[str],  # e.g., "ValidationError", "ToolException"
        inputs_summary: str,     # Brief summary, not full content
        outputs_summary: str
    }

    Token Cost: ~500 tokens (vs 50K+ for full dump)

    Implementation:
        Uses LangSmith API:
        - langsmith_client.list_runs(trace_id=trace_id)
        - Fetches metadata only (exclude inputs/outputs)
        - Builds hierarchy from parent_run_id references
        - Identifies failed/slow/expensive runs

    Usage Example:
        structure = get_trace_structure(trace_id)

        if structure.failed_runs:
            print(f"Found {len(structure.failed_runs)} failures")
            for run_id in structure.failed_runs:
                # Drill down with Level 1 analysis
                failure_analysis = analyze_failure_chain(run_id)
        else:
            print("All runs succeeded - quick validation only")
    """
```

#### `get_scenario_outcome`

```python
@tool
def get_scenario_outcome(
    thread_id: str
) -> ScenarioOutcome:
    """Get high-level scenario result from LangGraph thread.

    Args:
        thread_id: LangGraph thread ID (format: "whatsapp:user_123" or "console:test_abc")

    Returns:
        ScenarioOutcome: {
            success: bool,
            duration: float,
            total_cost: float,
            message_count: int,
            approval_triggered: bool,
            final_state: str,           # "completed" | "failed" | "awaiting_approval"
            error_summary: Optional[str]
        }

    Implementation:
        Queries LangGraph checkpointer:
        - Get final state for thread
        - Extract outcome metadata
        - Summarize execution

    Usage Example:
        outcome = get_scenario_outcome(thread_id)
        if not outcome.success:
            print(f"Scenario failed: {outcome.error_summary}")
    """
```

#### `quick_db_check`

```python
@tool
def quick_db_check(
    scenario_id: str,
    expected_count: int = 1
) -> QuickCheck:
    """Quick DB existence check via Supabase MCP - Claude's first DB validation.

    Fast COUNT query to verify expected records exist. Used before
    fetching full record details.

    Args:
        scenario_id: Scenario identifier (stored in product metadata)
        expected_count: How many records should exist (default: 1)

    Returns:
        QuickCheck: {
            exists: bool,
            count: int,
            matches_expected: bool,
            table: str               # "products"
        }

    Implementation:
        Uses Supabase MCP:
        mcp__supabase__execute_sql(
            f"SELECT COUNT(*) FROM products WHERE metadata->>'scenario_id' = '{scenario_id}'"
        )

    Token Cost: Minimal (single COUNT query)

    Usage Example:
        check = quick_db_check("cataloging_with_image", expected_count=1)

        if not check.matches_expected:
            # Fetch details only if check failed
            records = get_product_record(scenario_id=scenario_id)
        else:
            print("✅ DB record exists as expected")
    """
```

### Analysis Tools - Level 1 (Focused)

#### `analyze_failure_chain`

```python
@tool
def analyze_failure_chain(
    failed_run_id: str
) -> FailureAnalysis:
    """Analyze specific failure - Claude uses this for failed runs only.

    Fetches failure context (inputs, outputs, error) and traces back through
    parent runs to understand what led to the failure.

    Args:
        failed_run_id: Run ID that failed

    Returns:
        FailureAnalysis: {
            error_type: str,                    # "ValidationError", "ToolException", "LLMException"
            error_message: str,                 # Full error message
            stack_trace: Optional[str],         # If available
            root_cause_hypothesis: str,         # Claude-friendly explanation
            affected_component: str,            # "PM" | "CatalogingDept" | "Specialist" | "Tool"
            component_file: Optional[str],      # File path if code issue
            related_run_ids: List[str],         # Parent/sibling runs to investigate
            inputs_snapshot: dict,              # What the component received
            outputs_snapshot: Optional[dict],   # What it tried to return (if available)
            parent_run_name: str                # Context: where was this called from?
        }

    Token Cost: ~1,000 tokens (failed run + immediate context)

    Implementation:
        Uses LangSmith API:
        - Fetch failed run with inputs/outputs
        - Fetch parent run for context
        - Extract error details
        - Hypothesize root cause based on error type

    Usage Example:
        structure = get_trace_structure(trace_id)

        for failed_run in structure.failed_runs:
            analysis = analyze_failure_chain(failed_run)

            print(f"Root cause: {analysis.root_cause_hypothesis}")
            print(f"Component: {analysis.affected_component}")

            if analysis.error_type == "ValidationError":
                # Check specialist output
                validate_structured_output(analysis.related_run_ids[0], "Product")
    """
```

#### `validate_structured_output`

```python
@tool
def validate_structured_output(
    run_id: str,
    expected_schema: str  # "Product" | "ImageAnalysisResult" | "CatalogingResult"
) -> ValidationResult:
    """Check if component returned correct Pydantic model.

    Claude uses this to verify data quality issues (type mismatches,
    missing fields, schema violations).

    Args:
        run_id: Run ID to validate (typically a specialist)
        expected_schema: Name of Pydantic model expected

    Returns:
        ValidationResult: {
            schema_valid: bool,
            violations: List[FieldViolation],
            type_mismatches: List[TypeMismatch],
            missing_fields: List[str],
            extra_fields: List[str]
        }

        FieldViolation: {
            field: str,
            expected: str,    # Expected type/constraint
            actual: Any,      # Actual value
            message: str      # Human-readable error
        }

    Token Cost: ~500 tokens (output only)

    Implementation:
        - Fetch run output
        - Load expected Pydantic schema
        - Validate output against schema
        - Collect all violations

    Usage Example:
        # After finding ValidationError in save_product
        specialist_run = find_parent_run(failed_run_id)

        validation = validate_structured_output(specialist_run, "Product")

        if not validation.schema_valid:
            for violation in validation.violations:
                print(f"Field '{violation.field}': expected {violation.expected}, got {violation.actual}")

            # This is a prompt issue - specialist not returning correct types
            improvement = generate_prompt_improvement(
                issue=f"Specialist returns {violation.field} as wrong type",
                current_prompt=load_prompt("specialists/cataloging_specialist.prompt"),
                trace_examples=[specialist_run]
            )
    """
```

#### `get_product_record`

```python
@tool
def get_product_record(
    product_id: Optional[str] = None,
    scenario_id: Optional[str] = None,
    filters: Optional[Dict] = None
) -> ProductRecordResult:
    """Get product record(s) from Supabase via MCP.

    Claude uses this for detailed DB validation after quick_db_check
    identifies an issue.

    Args:
        product_id: Specific product UUID
        scenario_id: Get products for this scenario
        filters: Additional WHERE clause filters

    Returns:
        ProductRecordResult: {
            found: bool,
            count: int,
            records: List[ProductRecord]
        }

        ProductRecord: {
            id: str,
            name: Optional[str],
            description: Optional[str],
            price: Optional[float],
            sizes: List[str],
            colors: List[str],
            image_urls: List[str],
            created_at: str,
            metadata: dict
        }

    Implementation:
        Uses Supabase MCP:
        mcp__supabase__execute_sql(
            "SELECT * FROM products WHERE ..."
        )

    Usage Example:
        check = quick_db_check("cataloging_with_image")

        if check.exists:
            # Get full record for validation
            result = get_product_record(scenario_id="cataloging_with_image")
            record = result.records[0]

            # Validate fields
            if not record.image_urls:
                print("Issue: Image URLs not saved")

            if isinstance(record.price, str):
                print("Issue: Price saved as string instead of float")
    """
```

### Analysis Tools - Level 2 (Deep Dive)

#### `get_full_run_details`

```python
@tool
def get_full_run_details(
    run_id: str
) -> FullRunDetails:
    """Fetch complete run details - Claude uses this sparingly!

    Only use when root cause is unclear from metadata and focused analysis.
    Expensive in tokens.

    Args:
        run_id: Run ID to fetch

    Returns:
        FullRunDetails: {
            run_id: str,
            name: str,
            run_type: str,
            status: str,
            duration: float,
            cost: float,
            inputs: dict,            # FULL inputs (large)
            outputs: dict,           # FULL outputs (large)
            error: Optional[dict],
            metadata: dict,
            children: List[str],     # Child run IDs
            parent: Optional[str]
        }

    Token Cost: 5,000-10,000 tokens (context dependent)

    Usage Criteria:
        - Root cause unclear from failure_chain
        - Need to see exact prompt/response
        - Debugging complex multi-step reasoning
        - Investigating context leakage

    Usage Example:
        # Only after Level 0 and Level 1 analysis fail to identify root cause
        failure = analyze_failure_chain(failed_run)

        if not failure.root_cause_hypothesis:
            # Still unclear - need full details
            details = get_full_run_details(failed_run)

            # Manual inspection of inputs/outputs
            print(f"Full inputs: {details.inputs}")
            print(f"Full outputs: {details.outputs}")
    """
```

#### `trace_data_lineage`

```python
@tool
def trace_data_lineage(
    field: str,
    final_run_id: str
) -> DataLineage:
    """Trace where specific data came from through execution hierarchy.

    Claude uses this to understand data transformations and find where
    incorrect values originated.

    Args:
        field: Field name to trace (e.g., "price", "image_urls")
        final_run_id: Run where field appears (typically save_product)

    Returns:
        DataLineage: {
            field: str,
            transformations: List[Transformation],
            origin_run_id: str,
            origin_run_name: str
        }

        Transformation: {
            run_id: str,
            run_name: str,
            input_value: Any,
            output_value: Any,
            transformation_type: str  # "coercion" | "extraction" | "passthrough" | "generation"
        }

    Usage Example:
        # After finding price saved as string
        lineage = trace_data_lineage("price", "save_product_run_id")

        # Prints:
        # price="79.99" (str) at save_product
        #   ← price="79.99" (str) from cataloging_specialist
        #   ← price="Rs 79" (str) from user_message
        #
        # Issue: Cataloging specialist didn't coerce "79.99" → 79.99 (float)
    """
```

### Improvement Tools

#### `generate_prompt_improvement`

```python
@tool
def generate_prompt_improvement(
    issue_description: str,
    current_prompt: str,
    trace_examples: List[str]  # List of run IDs showing the issue
) -> PromptImprovement:
    """Generate improved prompt using LLM analysis.

    Claude uses this to fix prompt issues (missing instructions, ambiguous
    wording, incorrect examples, type emphasis).

    Args:
        issue_description: Human-readable issue (e.g., "Specialist returns price as string")
        current_prompt: Full current prompt text
        trace_examples: Run IDs demonstrating the issue

    Returns:
        PromptImprovement: {
            proposed_prompt: str,        # New prompt text
            reasoning: str,              # Why this fixes the issue
            expected_impact: str,        # What should improve
            diff: str,                   # Highlighted changes
            confidence: float,           # 0-1 confidence score
            affected_scenarios: List[str] # Scenarios this might affect
        }

    Implementation:
        Uses LLM with specialized prompt:
        - Analyzes current prompt
        - Reviews trace examples
        - Identifies missing/unclear instructions
        - Generates improved version
        - Highlights changes

    Usage Example:
        # After identifying prompt issue
        current_prompt = read_file("agents/src/.../cataloging_specialist.prompt")

        improvement = generate_prompt_improvement(
            issue_description="Specialist returns price as string instead of float",
            current_prompt=current_prompt,
            trace_examples=["run_abc123", "run_def456"]
        )

        print(f"Proposed fix:\n{improvement.diff}")
        print(f"Reasoning: {improvement.reasoning}")

        # Present to user for approval
    """
```

#### `generate_code_fix`

```python
@tool
def generate_code_fix(
    issue_description: str,
    file_path: str,
    error_context: str
) -> CodeFix:
    """Generate code fix using LLM analysis.

    Claude uses this for code bugs (missing error handling, wrong logic,
    type issues, missing validations).

    Args:
        issue_description: Issue description
        file_path: File to fix
        error_context: Error message/stack trace

    Returns:
        CodeFix: {
            proposed_changes: str,       # Unified diff format
            reasoning: str,              # Why this fixes the issue
            files_affected: List[str],
            risk_level: str,             # "low" | "medium" | "high"
            confidence: float,
            test_recommendations: List[str]  # What to test after applying
        }

    Implementation:
        Uses LLM with code analysis:
        - Reads current file
        - Analyzes error context
        - Generates fix
        - Produces diff
        - Assesses risk

    Usage Example:
        # After identifying code bug
        fix = generate_code_fix(
            issue_description="save_product doesn't extract image_urls",
            file_path="agents/src/.../cataloging_tools.py",
            error_context=trace_analysis
        )

        if fix.risk_level == "low" and fix.confidence > 0.8:
            print("Safe to apply")
        else:
            print("Requires careful review")
    """
```

#### `apply_improvement`

```python
@tool
def apply_improvement(
    improvement_type: str,  # "prompt" | "code"
    target_file: str,
    changes: str,           # Diff or full new content
    backup: bool = True
) -> ApplyResult:
    """Apply improvement with backup.

    Claude uses this after user approves improvement.

    Args:
        improvement_type: Type of change
        target_file: File to modify
        changes: Changes to apply
        backup: Create backup before modifying (default: True)

    Returns:
        ApplyResult: {
            success: bool,
            backup_path: Optional[str],
            files_modified: List[str],
            error: Optional[str]
        }

    Implementation:
        - Creates backup with timestamp
        - Applies changes using Edit tool
        - Validates syntax (for code files)
        - Logs change to improvement history

    Usage Example:
        # After user approves
        result = apply_improvement(
            improvement_type="prompt",
            target_file="agents/src/.../cataloging_specialist.prompt",
            changes=improvement.proposed_prompt
        )

        if result.success:
            print(f"✅ Applied. Backup: {result.backup_path}")

            # Re-test to validate
            validation = execute_scenario("cataloging_with_image")
        else:
            print(f"❌ Failed: {result.error}")
    """
```

### Helper Tools

#### `compare_execution_metrics`

```python
@tool
def compare_execution_metrics(
    baseline_result: ExecutionResult,
    new_result: ExecutionResult
) -> MetricsComparison:
    """Compare metrics before/after improvement.

    Claude uses this to validate improvements.

    Returns:
        MetricsComparison: {
            improved: bool,              # Overall improvement?
            success_rate_delta: float,   # Change in success rate
            latency_delta: float,        # Change in duration
            cost_delta: float,           # Change in cost
            quality_delta: Optional[float],  # If evaluators run
            recommendation: str          # "KEEP" | "REVERT" | "ITERATE"
        }

    Usage Example:
        baseline = execute_scenario("cataloging_with_image")
        # Apply improvement
        new = execute_scenario("cataloging_with_image")

        comparison = compare_execution_metrics(baseline, new)

        if comparison.improved:
            print(f"✅ Improvement validated: {comparison.recommendation}")
        else:
            print(f"❌ No improvement: {comparison.recommendation}")
    """
```

---

## Hierarchical Analysis Strategy

### Decision Tree

```
execute_scenario()
    ↓
get_scenario_outcome() + get_trace_structure()
    ↓
Check: Success?
    ↓
    ├─ YES → Quick Validation
    │         ↓
    │     quick_db_check()
    │         ↓
    │     All pass? → ✅ DONE
    │     Issues? → Level 1 Analysis
    │
    └─ NO → Level 1 Analysis
              ↓
        For each failed_run:
            analyze_failure_chain()
                ↓
            Root cause clear?
                ↓
                ├─ YES → Generate improvement → DONE
                │
                └─ NO → Level 2 Deep Dive
                          ↓
                      get_full_run_details()
                      trace_data_lineage()
                          ↓
                      Manual inspection → Generate improvement
```

### Token Budget Guidelines

| Analysis Level | Token Cost | When to Use |
|----------------|------------|-------------|
| Level 0: Overview | 500 tokens | Always - first step |
| Level 1: Focused | 1,500 tokens | If issues detected |
| Level 2: Deep Dive | 5,000+ tokens | If root cause unclear |

**Target**: 90% of analyses stay at Level 0-1 (< 2,000 tokens)

### Claude's Reasoning Patterns

**Pattern 1: Clear Failure**
```
"Trace shows save_product failed with ValidationError: 'price must be float'.
Only save_product failed - all upstream succeeded. I'll analyze just the
failure and its immediate parent (cataloging_specialist). No need to fetch
PM or department details since they worked correctly."

Tools used:
1. get_trace_structure() - identified save_product failure
2. analyze_failure_chain() - got error details
3. validate_structured_output() - confirmed specialist type issue

Token cost: ~1,200 (vs 50K for full dump)
```

**Pattern 2: Subtle Issue**
```
"All runs succeeded but DB record is missing. Let me trace the execution
path to see if save_product was actually called."

Tools used:
1. get_trace_structure() - all runs show success
2. quick_db_check() - no record found
3. analyze_decision_point() - check if department called save_product
4. get_full_run_details() - investigate department logic

Token cost: ~3,000 (targeted investigation)
```

**Pattern 3: Performance Issue**
```
"Scenario succeeded but took 5s (usually 2s). Let me find the slow component."

Tools used:
1. get_trace_structure() - identify slow_runs
2. For each slow run: analyze performance (tool calls, token usage)
3. Compare vs baseline metrics

Token cost: ~1,500
```

---

## LangSmith Integration

### API Patterns

**Trace Structure Fetch**:
```python
# Lightweight metadata fetch
runs = langsmith_client.list_runs(
    trace_id=trace_id,
    select=["id", "name", "run_type", "status", "start_time", "end_time",
            "error", "parent_run_id", "total_tokens"]
)
# Excludes inputs/outputs → saves 98% of tokens
```

**Focused Run Fetch**:
```python
# Fetch specific run with full details
run = langsmith_client.read_run(
    run_id=run_id,
    select=["inputs", "outputs", "error"]
)
# Only when needed
```

### Trace Structure Example

Input: `get_trace_structure("trace_abc123")`

Output:
```python
{
    "run_hierarchy": {
        "pm_run_1": ["dept_run_2"],
        "dept_run_2": ["img_spec_3", "cat_spec_4", "save_prod_5"]
    },
    "run_metadata": {
        "pm_run_1": {
            "name": "PM",
            "run_type": "chain",
            "status": "success",
            "duration": 1.2,
            "cost": 0.03,
            "error_type": None
        },
        "dept_run_2": {
            "name": "CatalogingDept",
            "run_type": "chain",
            "status": "success",
            "duration": 2.1,
            "cost": 0.05
        },
        "img_spec_3": {
            "name": "ImageAnalysisSpecialist",
            "run_type": "llm",
            "status": "success",
            "duration": 0.8,
            "cost": 0.02
        },
        "cat_spec_4": {
            "name": "CatalogingSpecialist",
            "run_type": "llm",
            "status": "success",
            "duration": 0.5,
            "cost": 0.01
        },
        "save_prod_5": {
            "name": "save_product",
            "run_type": "tool",
            "status": "error",
            "duration": 0.1,
            "cost": 0,
            "error_type": "ValidationError"
        }
    },
    "failed_runs": ["save_prod_5"],
    "slow_runs": [],
    "expensive_runs": [],
    "total_runs": 5,
    "total_duration": 2.5,
    "total_cost": 0.08
}
```

Claude's Analysis:
```
"Clear picture: only save_product failed. All upstream components succeeded.
I should focus on save_product failure and the specialist that provided its
input (cat_spec_4). No need to fetch PM or department details."
```

---

## Supabase MCP Integration

### MCP Tool Wrappers

All DB validation uses Supabase MCP tools (never raw SQL strings):

```python
# Quick existence check
def quick_db_check(scenario_id: str) -> QuickCheck:
    result = mcp__supabase__execute_sql(
        f"SELECT COUNT(*) as count FROM products WHERE metadata->>'scenario_id' = '{scenario_id}'"
    )
    count = result[0]['count']
    return QuickCheck(exists=count > 0, count=count, matches_expected=count == 1)

# Schema validation
def validate_product_schema(product_id: str) -> SchemaValidation:
    result = mcp__supabase__execute_sql(
        f"SELECT name, description, price, sizes, colors, image_urls FROM products WHERE id = '{product_id}'"
    )
    record = result[0]

    violations = []
    if not record['name']:
        violations.append(FieldViolation(field='name', message='Missing required field'))
    if isinstance(record['price'], str):
        violations.append(FieldViolation(field='price', expected='float', actual='str'))

    return SchemaValidation(valid=len(violations) == 0, violations=violations)

# Idempotency check
def check_duplicate_products(scenario_id: str) -> DuplicateCheck:
    result = mcp__supabase__execute_sql(
        f"""SELECT COUNT(*) as count, array_agg(id) as ids
            FROM products
            WHERE metadata->>'scenario_id' = '{scenario_id}'
            AND created_at > NOW() - INTERVAL '5 minutes'"""
    )
    return DuplicateCheck(
        count=result[0]['count'],
        is_duplicate=result[0]['count'] > 1,
        product_ids=result[0]['ids']
    )
```

### MCP Security Benefits

- ✅ Type-safe queries
- ✅ Automatic parameter sanitization
- ✅ Built-in error handling
- ✅ Connection pooling
- ✅ Audit logging

---

## Workflow Patterns

### Pattern 1: Single Scenario Analysis

**User Request**: "Jarvis, test cataloging_with_image and find issues"

**Claude's Workflow**:
```
1. execute_scenario("cataloging_with_image", "auto_approve")
   → Returns: {success: false, error: "ValidationError", trace_id: "abc123"}

2. Analysis: "Scenario failed. Let me get trace structure..."

3. get_trace_structure("abc123")
   → Returns: {failed_runs: ["save_product_5"], run_metadata: {...}}

4. Reasoning: "Only save_product failed. All upstream succeeded.
   Let me analyze that specific failure..."

5. analyze_failure_chain("save_product_5")
   → Returns: {error: "price must be float", root_cause: "specialist type issue"}

6. Reasoning: "This looks like cataloging specialist output issue.
   Let me validate..."

7. validate_structured_output("cat_specialist_4", "Product")
   → Returns: {violations: [{field: "price", expected: "float", actual: "str"}]}

8. Reasoning: "Confirmed. Cataloging specialist prompt needs type emphasis."

9. Report to user:
   "Found the issue! The cataloging specialist is returning price as
   string instead of float. This is a prompt issue - the specialist
   prompt doesn't emphasize numeric type coercion. Should I generate
   the improvement?"
```

**User**: "Yes, show me the proposed change"

```
10. generate_prompt_improvement(
     issue="Specialist returns price as string",
     current_prompt=read_file("..."),
     trace_examples=["cat_specialist_4"]
   )

11. Present diff and reasoning to user
```

**User**: "Apply it and retest"

```
12. apply_improvement("prompt", file, changes)

13. execute_scenario("cataloging_with_image", "auto_approve")
    → Returns: {success: true}

14. compare_execution_metrics(baseline, new)
    → Returns: {improved: true, success_rate: 0% → 100%}

15. Report: "✅ Fixed! Success rate improved from 0% to 100%."
```

### Pattern 2: Multi-Scenario Testing

**User Request**: "Test all cataloging scenarios and report issues"

**Claude's Workflow**:
```
1. load_scenario_list("cataloging_*")
   → Returns: ["cataloging_with_image", "cataloging_text_only", ...]

2. For each scenario:
   a. execute_scenario(scenario_id, "auto_approve")
   b. get_trace_structure(trace_id)
   c. quick_db_check(scenario_id)
   d. Flag if issues found

3. Aggregate findings:
   - 5 scenarios: 3 passed, 2 failed
   - Common issue: price type error
   - Affects: cataloging_with_image, cataloging_with_caption

4. Prioritize: "Price type issue affects 2/5 scenarios - fix this first"

5. Deep analysis on first failure:
   [Same as Pattern 1]

6. Report summary:
   "Tested 5 cataloging scenarios. Found 1 critical issue affecting 2 scenarios:
   Cataloging specialist returns price as string instead of float.

   Passing scenarios: cataloging_text_only, inquiry_product, conversational
   Failing scenarios: cataloging_with_image, cataloging_with_caption

   I can fix this with a prompt improvement. Shall I proceed?"
```

### Pattern 3: Improvement Validation

**User Request**: "Apply the prompt fix and validate it works"

**Claude's Workflow**:
```
1. apply_improvement(improvement)
   → Returns: {success: true, backup: "..."}

2. Re-test affected scenarios:
   For each in ["cataloging_with_image", "cataloging_with_caption"]:
       execute_scenario(scenario_id, "auto_approve")

3. compare_execution_metrics(before, after) for each

4. Report:
   "✅ Improvement validated:

   cataloging_with_image: 0% → 100% success
   cataloging_with_caption: 0% → 100% success

   No regressions in passing scenarios:
   cataloging_text_only: 100% → 100% (stable)
   inquiry_product: 100% → 100% (stable)

   Recommendation: KEEP improvement.

   Should I generate regression tests for these fixes?"
```

### Pattern 4: Continuous Iteration

**User Request**: "Keep testing scenarios and improving until all pass"

**Claude's Workflow**:
```
ITERATION 1:
1. select_next_scenario(queue, history)
   → "cataloging_with_image" (high priority, failed recently)

2. [Execute, analyze, identify issue, propose fix]

3. User approves → apply → validate → ✅

4. Report: "Fixed cataloging_with_image. Continue? (8 scenarios remaining)"

ITERATION 2:
User: "Continue"

5. select_next_scenario(queue, history)
   → "multi_turn_clarification" (medium priority, not tested recently)

6. [Execute, analyze]

7. Result: SUCCESS, no issues

8. Report: "✅ multi_turn_clarification passed. Continue? (7 remaining)"

[Continues until all pass or user stops]

FINAL REPORT:
"Testing session complete:
- 15 scenarios tested
- 8 issues found and fixed
- 7 already passing
- Success rate: 73% → 100%
- 6 improvements applied
- 8 regression tests generated

All scenarios now passing. System quality significantly improved."
```

---

## Issue Diagnosis Framework

### Issue Categories

1. **Prompt Issues** (40% of issues)
   - Missing instructions
   - Ambiguous wording
   - Incorrect examples
   - Missing type emphasis
   - Context not clear

2. **Code Issues** (30% of issues)
   - Missing error handling
   - Wrong logic
   - Type coercion bugs
   - Missing validations
   - Tool parameter errors

3. **Architecture Issues** (20% of issues)
   - Context leakage
   - Wrong delegation
   - Missing middleware
   - State management bugs
   - HITL configuration errors

4. **Data Quality Issues** (10% of issues)
   - Schema violations
   - Missing fields
   - Type mismatches
   - Incomplete records

### Root Cause Identification Patterns

#### Pattern: ValidationError

```
Error: "price must be float, got <class 'str'>"

Root Cause Analysis:
1. Where did error occur? → save_product tool
2. What input caused it? → price="79.99" (string)
3. Where did that come from? → cataloging_specialist output
4. Why wrong type? → Specialist prompt doesn't emphasize types

Issue Category: PROMPT_ISSUE
Component: cataloging_specialist
Severity: CRITICAL (blocks all cataloging)
```

#### Pattern: Missing DB Record

```
Error: quick_db_check shows count=0, expected=1

Root Cause Analysis:
1. Was save_product called? → Check trace structure
2. If called: Did it succeed? → Check run status
3. If succeeded: Query DB directly → Verify record
4. If not found: DB transaction issue or wrong scenario_id

Issue Category: CODE_ISSUE or ARCHITECTURE_ISSUE
Component: save_product tool or DB client
Severity: CRITICAL
```

#### Pattern: Context Leakage

```
Observation: Token usage excessive (10K tokens for simple specialist call)

Root Cause Analysis:
1. Check specialist input → Full conversation history passed
2. Expected: Only user_message + image_analysis
3. Root cause: Department not using context engineering

Issue Category: ARCHITECTURE_ISSUE
Component: Department delegation logic
Severity: MEDIUM (performance impact)
```

---

## Improvement Generation

### Prompt Improvement Patterns

#### Pattern 1: Add Type Emphasis

**Issue**: Specialist returns wrong types

**Fix Template**:
```markdown
Add section to prompt:

## Output Type Requirements

CRITICAL: Ensure all fields match their type specifications:
- **price**: MUST be numeric (float), not string. Convert "79.99" → 79.99
- **sizes**: MUST be list of strings, even if single item. Convert "M" → ["M"]
- **colors**: MUST be list of strings

Examples:
❌ Incorrect: {"price": "79.99", "sizes": "M"}
✅ Correct: {"price": 79.99, "sizes": ["M"]}
```

#### Pattern 2: Add Clarification Instructions

**Issue**: Specialist doesn't ask for missing info

**Fix Template**:
```markdown
Add to prompt:

## Handling Missing Information

If critical fields are missing:
1. Identify what's missing
2. Ask user for clarification
3. Be specific: "What's the price for this product?" not "More info please?"
4. Don't proceed without required fields
```

#### Pattern 3: Add Context Engineering

**Issue**: Department passes full context

**Fix Template**:
```markdown
Add to department prompt:

## Specialist Delegation

When delegating to specialists:
- Pass ONLY what they need
- Extract relevant user_message content
- Include image_analysis if available
- DO NOT pass full conversation history
- DO NOT pass system messages

Example:
❌ Pass: {messages: [all 50 messages]}
✅ Pass: {user_message: "catalog sneakers $79", image_analysis: {...}}
```

### Code Fix Patterns

#### Pattern 1: Add Error Handling

**Issue**: Tool crashes on unexpected input

**Fix**:
```python
# Before
def save_product(price: float, **kwargs):
    product = Product(price=price, **kwargs)
    storage.save_product(product)

# After
def save_product(price: float, **kwargs):
    try:
        # Coerce types
        if isinstance(price, str):
            price = float(price.replace('$', '').replace('Rs', ''))

        product = Product(price=price, **kwargs)
        storage.save_product(product)

    except ValueError as e:
        raise ToolException(f"Invalid price format: {e}")
    except ValidationError as e:
        raise ToolException(f"Product validation failed: {e}")
```

#### Pattern 2: Add Missing Field

**Issue**: Field not extracted

**Fix**:
```python
# Before (in department)
result = cataloging_specialist(user_message=text)
save_product(**result.model_dump())

# After
result = cataloging_specialist(user_message=text, image_analysis=img_result)
product_data = result.model_dump()

# Extract image_urls from image_analysis
if img_result:
    product_data['image_urls'] = [img_result.image_path]

save_product(**product_data)
```

### Validation Criteria

**Apply if**:
- ✅ Confidence > 0.7
- ✅ Risk level: low or medium
- ✅ No breaking changes
- ✅ Affects localized component

**Require review if**:
- ⚠️ Confidence < 0.7
- ⚠️ Risk level: high
- ⚠️ Touches multiple components
- ⚠️ Changes architecture

**Always require approval for**:
- ❗ Code changes (all risk levels)
- ❗ Architecture changes
- ❗ Database schema changes

**Can auto-apply**:
- ✅ Prompt improvements (confidence > 0.8, isolated prompts)
- ✅ Documentation updates
- ✅ Test additions

---

## Reporting Templates

### Finding Report

```markdown
## ISSUE FOUND: [Issue Title]

**📍 Location**: [file path or component]
**🔍 Severity**: CRITICAL | HIGH | MEDIUM | LOW
**📊 Trace**: [run_id or trace_id link]
**🎯 Category**: PROMPT_ISSUE | CODE_ISSUE | ARCHITECTURE_ISSUE | DATA_QUALITY

### Root Cause
[1-2 sentence explanation]

### Evidence
1. [Evidence point 1 with data]
2. [Evidence point 2 with data]
3. [Evidence point 3 with data]

### Impact
- [Impact point 1]
- [Impact point 2]

### Proposed Fix
[Description of fix]

[Optional: Code diff or prompt change]

### Expected Improvement
- [Metric 1]: [baseline] → [expected]
- [Metric 2]: [baseline] → [expected]

**Shall I generate the [prompt|code] improvement?**
```

**Example**:

```markdown
## ISSUE FOUND: Cataloging Specialist Type Error

**📍 Location**: agents/src/autifyme_agents/specialists/cataloging_specialist.py
**🔍 Severity**: CRITICAL (blocks all cataloging)
**📊 Trace**: run_abc123def456
**🎯 Category**: PROMPT_ISSUE

### Root Cause
Cataloging specialist returns price as string instead of float, causing ValidationError in save_product tool.

### Evidence
1. Trace shows ValidationError: "price must be float, got <class 'str'>"
2. Specialist output: `{"price": "79.99"}` (string)
3. Expected: `{"price": 79.99}` (float)
4. Save_product tool rejected input due to Pydantic validation

### Impact
- 100% of cataloging scenarios fail
- Database records not created
- User sees generic error message
- Affects 5 scenarios: cataloging_with_image, cataloging_text_only, etc.

### Proposed Fix
Update cataloging_specialist.prompt line 45-50 to emphasize numeric type requirements:

```diff
+ ## Output Type Requirements
+
+ **price**: MUST be numeric (float), not string.
+ Convert "79.99" → 79.99 (no quotes)
```

### Expected Improvement
- Success rate: 0% → 100%
- Validation errors: 5/5 scenarios → 0/5 scenarios

**Shall I generate the prompt improvement?**
```

### Iteration Summary

```markdown
## TESTING ITERATION #[N] COMPLETE

**Scenario**: [scenario_id]
**Result**: ✅ SUCCESS | ❌ FAILURE (after [N] attempts)
**Duration**: [duration]s
**Cost**: $[cost]

### Changes Applied
[If any]
✅ [Change type]: [file] ([description])
✅ Validated: [metric improvement]

### Findings
- [Finding 1]
- [Finding 2]

### DB Validation
✅ Record created: [product_id]
✅ All fields populated
✅ No duplicates

### Performance
- Latency: [value]s (p50: [baseline]s)
- Cost: $[value] (avg: $[baseline])
- Token usage: [value] tokens

**Next Scenario**: [next_scenario_id] ([priority reason])

**Continue?** (yes | select different scenario | stop)
```

### Progress Report

```markdown
## TESTING SESSION SUMMARY
========================

**Duration**: [duration]
**Scenarios Tested**: [count]
**Issues Found**: [count]
**Improvements Applied**: [count]
**Success Rate**: [baseline]% → [current]% ([delta]%)

### TOP ISSUES RESOLVED

1. ✅ [Issue 1 title] (affected [N] scenarios)
   - Fix: [fix description]
   - Impact: [metric improvement]

2. ✅ [Issue 2 title] (affected [N] scenarios)
   - Fix: [fix description]
   - Impact: [metric improvement]

### REMAINING ISSUES

1. ⚠️ [Issue 1 title] ([N] scenarios)
   - Priority: [high|medium|low]
   - Estimated effort: [small|medium|large]

### METRICS

| Metric | Baseline | Current | Delta |
|--------|----------|---------|-------|
| Success Rate | [%] | [%] | [+/-]% |
| Avg Latency | [s] | [s] | [+/-]s |
| Avg Cost | $[x] | $[x] | [+/-]$ |
| Quality Score | [x] | [x] | [+/-] |

### RECOMMENDATIONS

- [Recommendation 1]
- [Recommendation 2]

**Continue testing?** Focus on remaining issues? Move to production validation?
```

---

## Implementation Phases

### Phase 1: Core Tools (Week 1)

**Goal**: Build foundational tools for execution and lightweight analysis

**Deliverables**:
1. `execute_scenario(scenario_id, hitl_mode, media_path)` → ExecutionResult
2. `get_trace_structure(trace_id)` → TraceStructure (hierarchical, metadata only)
3. `get_scenario_outcome(thread_id)` → ScenarioOutcome
4. `quick_db_check(scenario_id, expected_count)` → QuickCheck (via MCP)
5. Test manually with Claude on 5-10 scenarios

**Files**:
- `tests/tools/execution_tools.py` - execute_scenario, execute_conversation
- `tests/tools/trace_analysis_tools.py` - get_trace_structure, get_scenario_outcome
- `tests/tools/database_validation_tools.py` - quick_db_check, MCP wrappers

**Success Criteria**:
- ✅ Claude can execute scenarios programmatically
- ✅ Claude can fetch trace structure (< 1,000 tokens per fetch)
- ✅ Claude can validate DB records exist
- ✅ 5 scenarios analyzed successfully
- ✅ Token usage: < 2,500 per scenario analysis

### Phase 2: Focused Analysis Tools (Week 2)

**Goal**: Build Level 1 analysis for detailed investigation

**Deliverables**:
1. `analyze_failure_chain(run_id)` → FailureAnalysis
2. `analyze_decision_point(run_id)` → DecisionAnalysis
3. `validate_structured_output(run_id, schema)` → ValidationResult
4. `get_product_record(product_id, scenario_id, filters)` → ProductRecordResult
5. Test failure analysis on 10 failed scenarios

**Files**:
- `tests/tools/trace_analysis_tools.py` - add focused analysis functions
- `tests/tools/database_validation_tools.py` - add detailed query functions

**Success Criteria**:
- ✅ Claude can identify root causes of failures
- ✅ Claude can validate Pydantic schema compliance
- ✅ Claude can query DB records with filters
- ✅ 10 failures analyzed with root causes identified
- ✅ Token usage: < 3,000 per failure analysis

### Phase 3: Improvement Tools (Week 2-3)

**Goal**: Enable improvement generation and application

**Deliverables**:
1. `generate_prompt_improvement(issue, prompt, examples)` → PromptImprovement
2. `generate_code_fix(issue, file, context)` → CodeFix
3. `apply_improvement(type, file, changes, backup)` → ApplyResult
4. `compare_execution_metrics(baseline, new)` → MetricsComparison
5. Test improvement cycle on 5 issues

**Files**:
- `tests/tools/improvement_tools.py` - generation and application functions
- `tests/tools/validation_tools.py` - metrics comparison

**Success Criteria**:
- ✅ Claude can generate prompt improvements
- ✅ Claude can generate code fixes (low-risk)
- ✅ Claude can apply improvements with backups
- ✅ Claude can validate improvements via re-testing
- ✅ 5 improvements applied and validated

### Phase 4: Workflow Helpers (Week 3)

**Goal**: Streamline multi-scenario testing

**Deliverables**:
1. `load_scenario_list(pattern)` → List[str]
2. `select_next_scenario(queue, history, strategy)` → str
3. `generate_iteration_report(execution, issues, fixes)` → str
4. `track_improvement_history(improvement, result)` → HistoryEntry
5. Test batch scenario testing

**Files**:
- `tests/tools/workflow_tools.py` - scenario management, reporting
- `tests/data/improvement_history.json` - improvement log

**Success Criteria**:
- ✅ Claude can test multiple scenarios efficiently
- ✅ Claude can prioritize scenarios intelligently
- ✅ Claude can generate formatted reports
- ✅ Improvement history tracked
- ✅ 20+ scenarios tested in single session

### Phase 5: Advanced Analysis (Week 4+)

**Goal**: Enable deep investigation for complex issues

**Deliverables**:
1. `get_full_run_details(run_id)` → FullRunDetails
2. `trace_data_lineage(field, run_id)` → DataLineage
3. `compare_traces(run_id_1, run_id_2)` → TraceComparison
4. `detect_patterns(history)` → List[Pattern]
5. `create_regression_test(scenario, trace, issue)` → TestCode

**Files**:
- `tests/tools/trace_analysis_tools.py` - add deep dive functions
- `tests/tools/pattern_detection_tools.py` - pattern analysis
- `tests/tools/test_generation_tools.py` - regression test creation

**Success Criteria**:
- ✅ Claude can investigate complex failures
- ✅ Claude can trace data transformations
- ✅ Claude can detect recurring patterns
- ✅ Claude can generate regression tests
- ✅ Pattern detection operational

---

## Success Criteria

### Week 1-2 (Foundation)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Token cost per analysis | < 2,500 | Avg across 10 scenarios |
| Analysis time | < 10s | From execution to report |
| Tool reliability | > 95% | Successful tool calls |
| Root cause accuracy | > 80% | Human validation |

### Week 3-4 (Improvement Loop)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Improvements generated | 10+ | Count |
| Improvement success rate | > 70% | Applied & validated |
| Regression tests generated | 5+ | Count |
| Full iteration time | < 2min | Execute → analyze → fix → validate |

### Week 5-6 (Batch Testing)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Scenarios tested | 50+ | Count |
| Issues identified | 20+ | Count |
| Multi-scenario efficiency | < 3min | Avg per scenario |
| Reporting quality | User satisfaction | Qualitative |

### Week 7-8 (Advanced)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Pattern detection | 5+ patterns | Recurring issues |
| Deep dive accuracy | > 90% | Complex failures |
| Overall system improvement | +15-20% | Success rate delta |
| Test coverage | 90%+ | Critical paths |

---

## Complete Usage Example

### Scenario: Cataloging With Image Failure

**Setup**:
- Scenario: cataloging_with_image
- Issue: Cataloging specialist returns price as string
- User doesn't know this yet

---

**User**: "Jarvis, test cataloging_with_image and find any issues"

**Claude**:

"I'll test that scenario now."

```python
# Tool: execute_scenario
result = execute_scenario("cataloging_with_image", "auto_approve")
```

"The scenario failed with a ValidationError. Let me analyze the execution trace to identify the root cause."

```python
# Tool: get_trace_structure
structure = get_trace_structure(result.trace_id)
```

"I can see the trace structure now. The issue is localized:"

```
PM → CatalogingDept → ImageAnalysisSpecialist ✅
                    → CatalogingSpecialist ✅
                    → save_product ❌ ValidationError
```

"Only save_product failed while all upstream components succeeded. Let me analyze that specific failure."

```python
# Tool: analyze_failure_chain
failure = analyze_failure_chain("save_product_run_id")
```

"The error is clear: `ValidationError: price must be float, got <class 'str'>`. This means save_product received a string when it expected a float. Let me check the cataloging specialist's output to see if that's where the type error originated."

```python
# Tool: validate_structured_output
validation = validate_structured_output("cat_specialist_run_id", "Product")
```

"Confirmed! The cataloging specialist returned:"
```json
{
  "name": "Canvas Sneakers",
  "price": "79.99",  ← STRING (should be float)
  "colors": ["white"],
  "sizes": ["7", "8", "9"]
}
```

"Let me also verify the database state."

```python
# Tool: quick_db_check
db_check = quick_db_check("cataloging_with_image")
```

"As expected, no product record was created (count: 0) because save_product failed validation."

---

**Claude's Report**:

```markdown
## ISSUE FOUND: Cataloging Specialist Type Error

📍 **Location**: agents/src/autifyme_agents/specialists/cataloging_specialist.py
🔍 **Severity**: CRITICAL (blocks all cataloging scenarios)
📊 **Trace**: run_abc123 (LangSmith)

### Root Cause
The cataloging specialist returns the `price` field as a string instead of a float, causing Pydantic validation to fail in the save_product tool.

### Evidence
1. ValidationError: "price must be float, got <class 'str'>"
2. Specialist output: `{"price": "79.99"}` (string with quotes)
3. Expected: `{"price": 79.99}` (numeric float)
4. Database: No record created (validation failed before save)

### Impact
- 100% of cataloging scenarios fail at save_product
- Database records not created
- User sees generic error message
- Likely affects: cataloging_with_image, cataloging_text_only, cataloging_with_caption

### Proposed Fix
Update the cataloging specialist prompt to emphasize numeric type requirements.

The current prompt doesn't specify that numeric fields must be actual numbers, not strings.

### Expected Improvement
- Success rate: 0% → 100%
- All cataloging scenarios should work
- Validation errors eliminated

**Shall I generate the prompt improvement?**
```

---

**User**: "Yes, generate the improvement"

**Claude**:

"I'll generate a prompt improvement now."

```python
# Tool: generate_prompt_improvement
current_prompt = read_file("agents/src/.../cataloging_specialist.prompt")

improvement = generate_prompt_improvement(
    issue_description="Specialist returns price as string instead of float",
    current_prompt=current_prompt,
    trace_examples=["cat_specialist_run_id"]
)
```

"Here's the proposed improvement:"

```diff
## Proposed Prompt Change

File: agents/src/autifyme_agents/prompts/specialists/cataloging_specialist.prompt

+ ## Output Type Requirements (NEW SECTION)
+
+ CRITICAL: Ensure all fields match their type specifications:
+
+ - **price**: MUST be numeric (float), not string
+   - Convert "79.99" → 79.99 (no quotes)
+   - Convert "Rs 79" → 79.0
+
+ - **sizes**: MUST be list of strings, even if single item
+   - Convert "M" → ["M"]
+
+ - **colors**: MUST be list of strings
+   - Convert "blue" → ["blue"]
+
+ Examples:
+ ❌ Incorrect: {"price": "79.99", "sizes": "M", "colors": "blue"}
+ ✅ Correct: {"price": 79.99, "sizes": ["M"], "colors": ["blue"]}
```

**Reasoning**:
The current prompt defines the Product schema but doesn't emphasize that numeric fields must be actual numbers. LLMs often return quoted numbers as strings ("79.99") which pass as valid JSON but fail Pydantic validation. Adding explicit type requirements with examples will ensure the specialist returns correctly typed data.

**Confidence**: 0.9 (high)
**Risk**: Low (prompt-only change, doesn't affect logic)

**Shall I apply this improvement?**

---

**User**: "Yes, apply it and retest"

**Claude**:

"I'll apply the improvement now."

```python
# Tool: apply_improvement
result = apply_improvement(
    improvement_type="prompt",
    target_file="agents/src/.../cataloging_specialist.prompt",
    changes=improvement.proposed_prompt,
    backup=True
)
```

"✅ Applied successfully. Backup created at: `...prompt.backup.20250116_143022`"

"Now let me retest the scenario to validate the fix."

```python
# Tool: execute_scenario
new_result = execute_scenario("cataloging_with_image", "auto_approve")
```

"✅ Success! The scenario now passes. Let me verify the database record was created."

```python
# Tool: get_product_record
record = get_product_record(scenario_id="cataloging_with_image")
```

"Perfect! The product record exists with correct types:"
```json
{
  "id": "uuid-here",
  "name": "Canvas Sneakers",
  "price": 79.99,  ← FLOAT (correct!)
  "colors": ["white"],
  "sizes": ["7", "8", "9"],
  "image_urls": ["..."],
  "created_at": "2025-01-16T14:30:45Z"
}
```

"Let me compare the metrics before and after the fix."

```python
# Tool: compare_execution_metrics
comparison = compare_execution_metrics(baseline=result, new=new_result)
```

---

**Claude's Final Report**:

```markdown
## ✅ IMPROVEMENT VALIDATED

### Scenario: cataloging_with_image
**Status**: FIXED

### Changes Applied
✅ Prompt: cataloging_specialist.prompt (added type requirements)
✅ Backup created: ...prompt.backup.20250116_143022

### Results
| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Success | ❌ Failure | ✅ Success | +100% |
| Duration | 2.3s | 2.1s | -0.2s |
| Cost | $0.08 | $0.07 | -$0.01 |
| DB Record | ❌ Not created | ✅ Created | Fixed |

### Validation
✅ Scenario now passes
✅ Product record created in database
✅ All fields have correct types
✅ No validation errors

### Impact Assessment
This fix likely resolves the issue for all cataloging scenarios that use the cataloging specialist:
- cataloging_with_image ✅ (tested)
- cataloging_text_only (likely fixed)
- cataloging_with_caption (likely fixed)

### Recommendation
**KEEP** this improvement. Consider testing other cataloging scenarios to confirm they also benefit from this fix.

**Shall I:**
1. Test other cataloging scenarios to validate broader impact?
2. Generate a regression test for this fix?
3. Move to next scenario?
```

---

**User**: "Test the other cataloging scenarios to confirm"

**Claude**:

"I'll test the other cataloging scenarios now to validate the fix applies broadly."

```python
# Tool: load_scenario_list
scenarios = load_scenario_list("cataloging_*")
# Returns: ["cataloging_with_image", "cataloging_text_only", "cataloging_with_caption"]

for scenario in scenarios[1:]:  # Skip first (already tested)
    result = execute_scenario(scenario, "auto_approve")
    # Quick validation
```

"Testing complete! Here are the results:"

```markdown
## BATCH TESTING RESULTS

All cataloging scenarios now pass:

1. ✅ cataloging_with_image (previously tested)
2. ✅ cataloging_text_only - FIXED (was failing, now passes)
3. ✅ cataloging_with_caption - FIXED (was failing, now passes)

### Summary
- **Impact**: 3/3 cataloging scenarios fixed by single prompt improvement
- **Success Rate**: 0% → 100% across all cataloging scenarios
- **Root Cause**: Confirmed as cataloging specialist type issue

### Database Validation
All scenarios created correct product records:
✅ cataloging_with_image: product_id_1
✅ cataloging_text_only: product_id_2
✅ cataloging_with_caption: product_id_3

**Recommendation**: Generate regression tests for these fixes to prevent future regressions.

**Shall I generate regression tests?**
```

---

**Total Time**: ~3 minutes
**Total Cost**: $0.25
**Token Usage**: ~3,000 tokens (vs 150K+ for naive full dump approach)
**Issues Fixed**: 3 scenarios with single prompt improvement

---

## Technical Specifications

### Tool Return Types (Pydantic Models)

```python
class ExecutionResult(BaseModel):
    trace_id: str
    run_id: str
    thread_id: str
    success: bool
    duration: float
    cost: float
    error: Optional[str]
    messages_sent: List[dict]
    approval_triggered: bool

class TraceStructure(BaseModel):
    run_hierarchy: Dict[str, List[str]]
    run_metadata: Dict[str, RunMetadata]
    failed_runs: List[str]
    slow_runs: List[str]
    expensive_runs: List[str]
    total_runs: int
    total_duration: float
    total_cost: float

class RunMetadata(BaseModel):
    name: str
    run_type: str
    status: str
    duration: float
    cost: float
    error_type: Optional[str]
    inputs_summary: str
    outputs_summary: str

class FailureAnalysis(BaseModel):
    error_type: str
    error_message: str
    stack_trace: Optional[str]
    root_cause_hypothesis: str
    affected_component: str
    component_file: Optional[str]
    related_run_ids: List[str]
    inputs_snapshot: dict
    outputs_snapshot: Optional[dict]
    parent_run_name: str

class ValidationResult(BaseModel):
    schema_valid: bool
    violations: List[FieldViolation]
    type_mismatches: List[TypeMismatch]
    missing_fields: List[str]
    extra_fields: List[str]

class FieldViolation(BaseModel):
    field: str
    expected: str
    actual: Any
    message: str

class PromptImprovement(BaseModel):
    proposed_prompt: str
    reasoning: str
    expected_impact: str
    diff: str
    confidence: float
    affected_scenarios: List[str]

class CodeFix(BaseModel):
    proposed_changes: str
    reasoning: str
    files_affected: List[str]
    risk_level: str
    confidence: float
    test_recommendations: List[str]

class MetricsComparison(BaseModel):
    improved: bool
    success_rate_delta: float
    latency_delta: float
    cost_delta: float
    quality_delta: Optional[float]
    recommendation: str  # "KEEP" | "REVERT" | "ITERATE"
```

### Error Handling

All tools should:
1. Return structured errors, not raise exceptions
2. Include error context for debugging
3. Log to improvement history
4. Provide actionable error messages

```python
class ToolError(BaseModel):
    tool_name: str
    error_type: str
    error_message: str
    context: dict
    recoverable: bool
    suggested_action: str
```

### API Rate Limiting

LangSmith API:
- Rate limit: 100 requests/minute
- Implement exponential backoff
- Cache trace structures (5min TTL)

Supabase MCP:
- No explicit rate limits
- Connection pooling via MCP
- Query timeout: 30s

### State Management

Improvement History:
```json
{
  "improvements": [
    {
      "timestamp": "2025-01-16T14:30:45Z",
      "improvement_id": "uuid",
      "type": "prompt",
      "target_file": "...",
      "issue_description": "...",
      "applied": true,
      "validated": true,
      "metrics": {
        "success_rate_delta": 1.0,
        "latency_delta": -0.2,
        "cost_delta": -0.01
      },
      "affected_scenarios": ["..."],
      "regression_test_generated": true
    }
  ]
}
```

---

## Best Practices

### For Claude (Jarvis)

1. **Always start with Level 0** (get_trace_structure)
   - Get overview before drilling down
   - Identify failed/slow/expensive runs
   - Decide where to focus

2. **Fetch details only when needed**
   - If all runs succeeded: quick validation only
   - If single failure: analyze that failure only
   - Avoid fetching successful runs unless investigating context

3. **Use MCP for all DB operations**
   - Never write raw SQL strings
   - Use wrapper functions (quick_db_check, get_product_record)
   - Leverage MCP security and type safety

4. **Explain your reasoning**
   - Show what you found in traces
   - Explain why you're drilling down
   - Present evidence for root causes

5. **Validate improvements**
   - Always retest after applying
   - Compare metrics before/after
   - Report improvements with data

6. **Track token usage**
   - Monitor your analysis token cost
   - If exceeding 3,000 tokens, explain why
   - Optimize by fetching less

### For Users

1. **Guide Claude's priorities**
   - Tell Claude which scenarios are most important
   - Provide business context for prioritization
   - Override Claude's recommendations when needed

2. **Review improvements before applying**
   - Check Claude's reasoning
   - Verify proposed changes make sense
   - Approve or request modifications

3. **Use batch testing for efficiency**
   - "Test all cataloging scenarios"
   - "Test scenarios that failed last time"
   - "Focus on high-priority workflows"

4. **Leverage improvement history**
   - Review what's been fixed
   - Identify patterns in issues
   - Track quality improvements over time

5. **Provide feedback on analysis quality**
   - If Claude missed something, point it out
   - If analysis was too shallow, ask for deeper investigation
   - If too detailed, ask for high-level summary

---

## Related Documents

- **[HIERARCHICAL_TRACE_ANALYSIS.md](./HIERARCHICAL_TRACE_ANALYSIS.md)** - Deep dive on trace fetching strategy
- **[TOOL_SPECIFICATIONS.md](./TOOL_SPECIFICATIONS.md)** - Complete API reference for all tools
- **[WORKFLOW_PATTERNS.md](./WORKFLOW_PATTERNS.md)** - Detailed workflow examples
- **[IMPROVEMENT_METHODOLOGY.md](./IMPROVEMENT_METHODOLOGY.md)** - Fix generation strategies
- **[LOCAL_TESTING_STRATEGY.md](./LOCAL_TESTING_STRATEGY.md)** - Current testing infrastructure
- **[LANGSMITH_FEATURES.md](../tech/LANGSMITH_FEATURES.md)** - LangSmith platform capabilities

---

## Implementation Checklist

### Phase 1: Core Tools
- [ ] Implement `execute_scenario()`
- [ ] Implement `get_trace_structure()`
- [ ] Implement `get_scenario_outcome()`
- [ ] Implement `quick_db_check()` via MCP
- [ ] Test manually with Claude on 5 scenarios
- [ ] Validate token efficiency (< 2,500 per analysis)

### Phase 2: Focused Analysis
- [ ] Implement `analyze_failure_chain()`
- [ ] Implement `validate_structured_output()`
- [ ] Implement `get_product_record()` via MCP
- [ ] Test failure analysis on 10 scenarios
- [ ] Validate root cause identification accuracy

### Phase 3: Improvement Tools
- [ ] Implement `generate_prompt_improvement()`
- [ ] Implement `generate_code_fix()`
- [ ] Implement `apply_improvement()`
- [ ] Implement `compare_execution_metrics()`
- [ ] Test improvement cycle on 5 issues
- [ ] Validate improvement success rate (> 70%)

### Phase 4: Workflow Helpers
- [ ] Implement `load_scenario_list()`
- [ ] Implement `select_next_scenario()`
- [ ] Implement `generate_iteration_report()`
- [ ] Implement `track_improvement_history()`
- [ ] Test batch scenario testing (20+ scenarios)

### Phase 5: Advanced Analysis
- [ ] Implement `get_full_run_details()`
- [ ] Implement `trace_data_lineage()`
- [ ] Implement `compare_traces()`
- [ ] Implement `detect_patterns()`
- [ ] Implement `create_regression_test()`
- [ ] Test complex failure investigation

### Documentation
- [ ] Create HIERARCHICAL_TRACE_ANALYSIS.md
- [ ] Create TOOL_SPECIFICATIONS.md
- [ ] Create WORKFLOW_PATTERNS.md
- [ ] Create IMPROVEMENT_METHODOLOGY.md
- [ ] Update docs/architecture/README.md
- [ ] Update CLAUDE.md

---

**Last Updated**: 2025-01-16
**Next Review**: After Phase 1 implementation
**Status**: 🔬 DESIGN - Ready for implementation
