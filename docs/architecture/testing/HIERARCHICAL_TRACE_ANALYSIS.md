# Hierarchical Trace Analysis - Lazy-Loading Strategy for LangSmith

**Date**: 2025-01-16
**Status**: 🔬 DESIGN
**Purpose**: Detailed guide on hierarchical trace fetching for 25x token reduction

---

## Executive Summary

Traditional trace analysis fetches entire execution trees upfront (50K+ tokens), which is expensive, slow, and often unnecessary. **Hierarchical Trace Analysis** uses a lazy-loading strategy: fetch trace structure first (metadata only, ~500 tokens), identify issues, then drill down selectively only where needed (~1,500 tokens for focused analysis). This reduces token costs by **25x** while maintaining full investigative capability.

**Key Innovation**: Most issues can be identified from metadata alone. Full trace details are only needed for 5-10% of analyses.

---

## Table of Contents

1. [Problem: Naive Full Dump Approach](#problem-naive-full-dump-approach)
2. [Solution: Three-Level Hierarchy](#solution-three-level-hierarchy)
3. [Level 0: Structure Overview](#level-0-structure-overview)
4. [Level 1: Focused Investigation](#level-1-focused-investigation)
5. [Level 2: Deep Dive](#level-2-deep-dive)
6. [Decision Logic](#decision-logic)
7. [Implementation Details](#implementation-details)
8. [Performance Benchmarks](#performance-benchmarks)
9. [Real-World Examples](#real-world-examples)
10. [Best Practices](#best-practices)

---

## Problem: Naive Full Dump Approach

### Traditional Method

```python
# ❌ Expensive and wasteful
trace_dump = langsmith_client.read_run_tree(trace_id, include_io=True)

# Returns:
# - All runs (100+)
# - Full inputs for each run (prompts, context, messages)
# - Full outputs for each run (responses, structured outputs)
# - Full metadata
# - Child relationships
```

### Costs

| Metric | Value |
|--------|-------|
| API Calls | 1 (but large payload) |
| Token Cost | 50,000+ tokens |
| Transfer Time | 5-10 seconds |
| Context Window | Often exceeded |
| Relevance | 90% irrelevant data |

### Why It's Wasteful

**Example Scenario**: cataloging_with_image fails at save_product

**What we need**:
- save_product run (error details)
- cataloging_specialist run (what it returned)
- Total: 2 runs, ~1,000 tokens

**What full dump gives us**:
- PM run + all child runs (20+)
- Full conversation history
- All tool inputs/outputs
- Department reasoning
- Specialist prompts/responses
- Total: 20+ runs, 50,000+ tokens

**Waste**: 98% of data is irrelevant to the issue

---

## Solution: Three-Level Hierarchy

### Overview

```
Level 0: STRUCTURE OVERVIEW (~500 tokens)
    ↓
    Fetch metadata only: run IDs, statuses, durations, costs
    Identify: failed runs, slow runs, expensive runs
    ↓
    Decision: Is issue clear from metadata?
    ↓
    ├─ YES → Report findings (90% of cases)
    │
    └─ NO → Drill down to Level 1
            ↓
            Level 1: FOCUSED INVESTIGATION (~1,500 tokens)
            ↓
            Fetch details for: failed run + immediate context
            Analyze: error messages, inputs/outputs
            ↓
            Decision: Is root cause clear?
            ↓
            ├─ YES → Report findings (95% of cases)
            │
            └─ NO → Drill down to Level 2
                    ↓
                    Level 2: DEEP DIVE (5,000+ tokens)
                    ↓
                    Fetch: Full run details, parent context, data lineage
                    Manual inspection for complex issues
```

### Token Efficiency

| Level | When to Use | Token Cost | Coverage |
|-------|-------------|------------|----------|
| Level 0 | Always (first step) | ~500 | 90% of issues |
| Level 1 | If issues detected | +1,500 | 95% of issues |
| Level 2 | If root cause unclear | +5,000 | 100% of issues |

**Average**: 2,000 tokens per analysis (vs 50,000 traditional)

---

## Level 0: Structure Overview

### Purpose

Get lightweight overview of execution hierarchy to identify:
- Which runs failed (errors)
- Which runs were slow (performance issues)
- Which runs were expensive (cost optimization)
- Execution flow (delegation patterns)

### API Call

```python
# LangSmith SDK
runs = langsmith_client.list_runs(
    trace_id=trace_id,
    select=[
        "id",                 # Run ID
        "name",               # Component name
        "run_type",           # "chain" | "llm" | "tool"
        "status",             # "success" | "error"
        "start_time",
        "end_time",
        "error",              # Error message if failed
        "parent_run_id",      # Parent relationship
        "total_tokens",       # Token usage
        "total_cost"          # Cost
    ]
)
# Excludes: inputs, outputs (saves 98% of tokens)
```

### Data Structure

```python
class TraceStructure(BaseModel):
    """Lightweight trace overview."""

    # Hierarchy: {parent_id: [child_ids]}
    run_hierarchy: Dict[str, List[str]]

    # Metadata for each run
    run_metadata: Dict[str, RunMetadata]

    # Quick access lists
    failed_runs: List[str]
    slow_runs: List[str]
    expensive_runs: List[str]

    # Summary stats
    total_runs: int
    total_duration: float
    total_cost: float

class RunMetadata(BaseModel):
    """Per-run metadata (no inputs/outputs)."""

    name: str                    # "PM" | "CatalogingDept" | "save_product"
    run_type: str                # "chain" | "llm" | "tool"
    status: str                  # "success" | "error"
    duration: float              # Seconds
    cost: float                  # Dollars
    error_type: Optional[str]    # "ValidationError" | "ToolException"
    token_usage: Optional[int]   # If LLM call
```

### Example Output

Input: `get_trace_structure("trace_abc123")`

Output:
```python
TraceStructure(
    run_hierarchy={
        "pm_1": ["dept_2"],
        "dept_2": ["img_3", "cat_4", "save_5"]
    },
    run_metadata={
        "pm_1": RunMetadata(
            name="ProjectManager",
            run_type="chain",
            status="success",
            duration=1.2,
            cost=0.03,
            error_type=None
        ),
        "dept_2": RunMetadata(
            name="CatalogingDepartment",
            run_type="chain",
            status="success",
            duration=2.1,
            cost=0.05
        ),
        "img_3": RunMetadata(
            name="ImageAnalysisSpecialist",
            run_type="llm",
            status="success",
            duration=0.8,
            cost=0.02,
            token_usage=1500
        ),
        "cat_4": RunMetadata(
            name="CatalogingSpecialist",
            run_type="llm",
            status="success",
            duration=0.5,
            cost=0.01,
            token_usage=800
        ),
        "save_5": RunMetadata(
            name="save_product",
            run_type="tool",
            status="error",
            duration=0.1,
            cost=0,
            error_type="ValidationError"
        )
    },
    failed_runs=["save_5"],
    slow_runs=[],
    expensive_runs=[],
    total_runs=5,
    total_duration=2.5,
    total_cost=0.08
)
```

### Analysis from Level 0

**Claude's Reasoning**:
```
"I can see from the trace structure that only save_product failed.
All upstream components (PM, Department, Specialists) succeeded.
This tells me:
1. The issue is isolated to save_product tool
2. The inputs to save_product came from cataloging_specialist
3. I should focus on those 2 runs only
4. No need to fetch PM or department details"
```

**Decision**: Move to Level 1 for `save_5` and `cat_4`

**Token Usage**: 500 tokens (vs 50,000 for full dump)

---

## Level 1: Focused Investigation

### Purpose

Fetch full details for specific runs identified as problematic in Level 0:
- Failed runs (error details, inputs, outputs)
- Slow runs (identify bottlenecks)
- Parent/child context (what led to failure)

### API Call

```python
# Fetch specific run with full details
run = langsmith_client.read_run(
    run_id=run_id,
    load_child_runs=False  # Don't fetch children yet
)

# Returns:
# - Full inputs (what component received)
# - Full outputs (what component returned)
# - Error details (message, stack trace)
# - Metadata
```

### Focused Fetching Pattern

**Scenario**: save_product failed

```python
# Step 1: Fetch failed run
failed_run = langsmith_client.read_run("save_5")
# → Get error details, inputs

# Step 2: Fetch immediate parent (who called save_product?)
parent_run = langsmith_client.read_run(failed_run.parent_run_id)
# → Get context: what was department doing?

# Step 3: Fetch data source (where did inputs come from?)
specialist_run = langsmith_client.read_run("cat_4")
# → Get specialist output (likely source of bad data)

# Total: 3 runs, ~1,500 tokens
```

### Data Structure

```python
class FailureAnalysis(BaseModel):
    """Focused failure analysis."""

    # Error details
    error_type: str              # "ValidationError"
    error_message: str           # "price must be float, got str"
    stack_trace: Optional[str]

    # Root cause (hypothesis)
    root_cause_hypothesis: str   # "Specialist output type mismatch"

    # Component info
    affected_component: str      # "save_product"
    component_file: Optional[str]  # File path if known

    # Investigation leads
    related_run_ids: List[str]   # Runs to investigate further

    # Context snapshots
    inputs_snapshot: dict        # What failed component received
    outputs_snapshot: Optional[dict]  # What it tried to return

    # Parent context
    parent_run_name: str         # "CatalogingDepartment"
```

### Example Output

Input: `analyze_failure_chain("save_5")`

Process:
1. Fetch save_5 run
2. Extract error: "ValidationError: price must be float, got <class 'str'>"
3. Extract inputs: `{"price": "79.99", "name": "Sneakers", ...}`
4. Identify issue: price is string, should be float
5. Trace back: inputs came from cataloging_specialist (cat_4)
6. Hypothesize: specialist returned wrong type

Output:
```python
FailureAnalysis(
    error_type="ValidationError",
    error_message="price must be float, got <class 'str'>",
    root_cause_hypothesis="Cataloging specialist returned price as string instead of float",
    affected_component="save_product",
    component_file="agents/src/.../cataloging_tools.py",
    related_run_ids=["cat_4"],  # Check this specialist
    inputs_snapshot={
        "price": "79.99",  # STRING (wrong!)
        "name": "Canvas Sneakers",
        "colors": ["white"]
    },
    outputs_snapshot=None,  # Tool crashed before returning
    parent_run_name="CatalogingDepartment"
)
```

### Analysis from Level 1

**Claude's Reasoning**:
```
"The error is clear: save_product received price as string '79.99'
but Pydantic expects float. The inputs came from cataloging_specialist
(run cat_4). Let me validate that specialist's output to confirm
it's the source of the type error."
```

**Next Step**: Validate specialist output

```python
validation = validate_structured_output("cat_4", "Product")
# Returns: {violations: [{field: "price", expected: "float", actual: "str"}]}
```

**Decision**: Root cause confirmed. No need for Level 2.

**Token Usage**: 500 (Level 0) + 1,500 (Level 1) = 2,000 tokens total

---

## Level 2: Deep Dive

### Purpose

Only use when root cause is unclear after Level 0 and Level 1:
- Complex multi-component interactions
- Context leakage investigations
- Data lineage tracing
- Manual inspection needed

### When to Use

Use Level 2 if:
- Error message is vague ("Something went wrong")
- Multiple components failed
- Issue appears to be architectural (context, delegation)
- Data transformations unclear
- Intermittent failures (need full context)

**Frequency**: <5% of analyses

### API Calls

```python
# Full run details
run = langsmith_client.read_run(
    run_id=run_id,
    load_child_runs=True  # Fetch full subtree
)

# Data lineage (custom logic)
def trace_data_lineage(field: str, final_run_id: str):
    # Trace field value back through execution hierarchy
    # Show transformations at each step
```

### Data Structure

```python
class FullRunDetails(BaseModel):
    """Complete run information."""

    run_id: str
    name: str
    run_type: str
    status: str
    duration: float
    cost: float

    # FULL CONTENT (expensive)
    inputs: dict          # Complete inputs
    outputs: dict         # Complete outputs
    error: Optional[dict]
    metadata: dict

    # Relationships
    children: List[str]   # Child run IDs
    parent: Optional[str]

class DataLineage(BaseModel):
    """Track field transformations through execution."""

    field: str  # e.g., "price"
    transformations: List[Transformation]
    origin_run_id: str
    origin_run_name: str

class Transformation(BaseModel):
    run_id: str
    run_name: str
    input_value: Any
    output_value: Any
    transformation_type: str  # "coercion" | "extraction" | "generation"
```

### Example: Data Lineage Tracing

**Problem**: Price is wrong type, but unclear where transformation happened

```python
lineage = trace_data_lineage("price", "save_5")
```

**Process**:
1. Start at save_5: `price="79.99"` (string)
2. Trace back to parent (dept_2): passed `price="79.99"` from specialist
3. Trace back to specialist (cat_4): generated `price="79.99"` from user text
4. Trace back to user input: "catalog sneakers $79"

**Output**:
```python
DataLineage(
    field="price",
    transformations=[
        Transformation(
            run_name="user_input",
            input_value="catalog sneakers $79",
            output_value="catalog sneakers $79",
            transformation_type="passthrough"
        ),
        Transformation(
            run_name="CatalogingSpecialist",
            input_value="$79" (extracted from text),
            output_value="79.99" (string),
            transformation_type="extraction"  # Extracted but didn't coerce type!
        ),
        Transformation(
            run_name="CatalogingDepartment",
            input_value="79.99" (string),
            output_value="79.99" (string),
            transformation_type="passthrough"
        ),
        Transformation(
            run_name="save_product",
            input_value="79.99" (string),
            output_value=None (crashed),
            transformation_type="validation_failed"
        )
    ],
    origin_run_id="cat_4",
    origin_run_name="CatalogingSpecialist"
)
```

**Analysis**:
```
"The issue originated in CatalogingSpecialist (cat_4). It extracted
the price correctly ('79' from '$79') but returned it as a string '79.99'
instead of coercing to float 79.99. This is a prompt issue - the specialist
prompt doesn't emphasize type requirements."
```

**Token Usage**: 500 (L0) + 1,500 (L1) + 5,000 (L2) = 7,000 tokens

Still 7x cheaper than full dump!

---

## Decision Logic

### Decision Tree for Claude

```
START: execute_scenario()
    ↓
Level 0: get_trace_structure()
    ↓
Check failed_runs
    ↓
    ├─ No failures → Quick validation
    │      ↓
    │  quick_db_check()
    │      ↓
    │  Check: DB records exist?
    │      ↓
    │      ├─ YES → ✅ DONE (scenario passed)
    │      │
    │      └─ NO → Level 1 (investigate why no record)
    │
    └─ Has failures → Level 1
           ↓
       For each failed_run:
           analyze_failure_chain()
               ↓
           Check: Error message clear?
               ↓
               ├─ YES → Identify root cause
               │         ↓
               │     Check: Root cause in specialist output?
               │         ↓
               │         ├─ YES → validate_structured_output()
               │         │         ↓
               │         │     ✅ DONE (issue identified)
               │         │
               │         └─ NO → Check: Root cause in DB?
               │                   ↓
               │               get_product_record()
               │                   ↓
               │               ✅ DONE (issue identified)
               │
               └─ NO → Level 2
                       ↓
                   get_full_run_details()
                       ↓
                   trace_data_lineage()
                       ↓
                   Manual inspection
                       ↓
                   ✅ DONE (deep analysis)
```

### When to Stop at Each Level

**Stop at Level 0 if**:
- All runs succeeded
- Quick DB validation passes
- No slow/expensive runs flagged

**Stop at Level 1 if**:
- Error message is clear ("ValidationError: price must be float")
- Failed component is isolated (only 1 failure)
- Root cause hypothesis is strong (>80% confidence)
- Related runs identified (know what to fix)

**Go to Level 2 if**:
- Error message vague ("Unknown error")
- Multiple components failed
- Root cause unclear after Level 1
- Architectural issue suspected (context leakage, wrong delegation)
- Data transformations complex

---

## Implementation Details

### LangSmith API Patterns

#### Pattern 1: Metadata-Only Fetch

```python
def get_trace_structure(trace_id: str) -> TraceStructure:
    """Fetch structure without inputs/outputs."""

    # Fetch all runs for this trace, metadata only
    runs = langsmith_client.list_runs(
        trace_id=trace_id,
        select=[
            "id", "name", "run_type", "status",
            "start_time", "end_time", "error",
            "parent_run_id", "total_tokens", "total_cost"
        ]
    )

    # Build hierarchy
    hierarchy = {}
    metadata = {}

    for run in runs:
        # Store metadata
        metadata[run.id] = RunMetadata(
            name=run.name,
            run_type=run.run_type,
            status=run.status,
            duration=(run.end_time - run.start_time).total_seconds(),
            cost=run.total_cost or 0,
            error_type=run.error.split(":")[0] if run.error else None,
            token_usage=run.total_tokens
        )

        # Build hierarchy
        if run.parent_run_id:
            if run.parent_run_id not in hierarchy:
                hierarchy[run.parent_run_id] = []
            hierarchy[run.parent_run_id].append(run.id)

    # Identify problematic runs
    failed_runs = [r.id for r in runs if r.status == "error"]
    slow_runs = [r.id for r in runs if r.duration > SLOW_THRESHOLD]
    expensive_runs = [r.id for r in runs if r.cost > COST_THRESHOLD]

    return TraceStructure(
        run_hierarchy=hierarchy,
        run_metadata=metadata,
        failed_runs=failed_runs,
        slow_runs=slow_runs,
        expensive_runs=expensive_runs,
        total_runs=len(runs),
        total_duration=sum(r.duration for r in runs),
        total_cost=sum(r.cost for r in runs)
    )
```

#### Pattern 2: Focused Details Fetch

```python
def analyze_failure_chain(failed_run_id: str) -> FailureAnalysis:
    """Fetch details for failed run only."""

    # Fetch failed run with full details
    failed_run = langsmith_client.read_run(
        run_id=failed_run_id,
        load_child_runs=False
    )

    # Extract error info
    error_type = type(failed_run.error).__name__ if failed_run.error else "Unknown"
    error_message = str(failed_run.error) if failed_run.error else ""

    # Fetch parent for context (optional, only if needed)
    parent_run = None
    if failed_run.parent_run_id:
        parent_run = langsmith_client.read_run(
            failed_run.parent_run_id,
            load_child_runs=False
        )

    # Hypothesize root cause based on error type
    hypothesis = generate_hypothesis(error_type, error_message, failed_run.inputs)

    return FailureAnalysis(
        error_type=error_type,
        error_message=error_message,
        root_cause_hypothesis=hypothesis,
        affected_component=failed_run.name,
        related_run_ids=identify_related_runs(failed_run),
        inputs_snapshot=failed_run.inputs,
        outputs_snapshot=failed_run.outputs,
        parent_run_name=parent_run.name if parent_run else None
    )
```

### Caching Strategy

**Cache trace structures** (5-minute TTL):
- Once fetched, cache for quick re-access
- Invalidate on new runs in same trace
- Reduces redundant API calls

```python
trace_structure_cache: Dict[str, TraceStructure] = {}
cache_ttl = 300  # 5 minutes

def get_trace_structure_cached(trace_id: str) -> TraceStructure:
    if trace_id in trace_structure_cache:
        cached = trace_structure_cache[trace_id]
        if time.time() - cached.timestamp < cache_ttl:
            return cached.structure

    # Fetch fresh
    structure = get_trace_structure(trace_id)
    trace_structure_cache[trace_id] = {
        "structure": structure,
        "timestamp": time.time()
    }
    return structure
```

---

## Performance Benchmarks

### Scenario: cataloging_with_image (5 runs total)

| Approach | API Calls | Token Cost | Time | Data Relevance |
|----------|-----------|------------|------|----------------|
| Full Dump | 1 | 50,000 | 10s | 2% (only 1 run matters) |
| Level 0 Only | 1 | 500 | 1s | 100% (metadata shows issue) |
| Level 0 + Level 1 | 3 | 2,000 | 2s | 100% (full context) |
| Level 0 + Level 1 + Level 2 | 6 | 7,000 | 4s | 100% (deep dive) |

**Typical Distribution**:
- 90% of analyses: Level 0 + Level 1 (2,000 tokens)
- 5% of analyses: Level 0 only (500 tokens)
- 5% of analyses: Level 0 + Level 1 + Level 2 (7,000 tokens)

**Average**: 2,100 tokens per analysis (24x cheaper than full dump)

---

## Real-World Examples

### Example 1: Clear Failure (Level 0 + Level 1)

**Scenario**: cataloging_with_image fails

**Level 0 Analysis**:
```
get_trace_structure("trace_123")
→ failed_runs: ["save_product_5"]
→ All other runs succeeded

Reasoning: "Only save_product failed. Issue is isolated."
```

**Level 1 Analysis**:
```
analyze_failure_chain("save_product_5")
→ error: "ValidationError: price must be float"
→ inputs: {"price": "79.99"}

Reasoning: "Price is string, should be float. Came from specialist."
```

**Validation**:
```
validate_structured_output("cataloging_specialist_4", "Product")
→ violations: [{field: "price", expected: "float", actual: "str"}]

Conclusion: "Specialist prompt issue - doesn't emphasize types."
```

**Token Usage**: 2,000 tokens
**Time**: 2 seconds
**Outcome**: Root cause identified, improvement proposal ready

### Example 2: Subtle Issue (Level 0 + Level 1)

**Scenario**: cataloging_text_only succeeds but DB record missing

**Level 0 Analysis**:
```
get_trace_structure("trace_456")
→ failed_runs: []
→ All runs succeeded

Reasoning: "No failures, but user reports DB issue. Check database."
```

**Database Check**:
```
quick_db_check("cataloging_text_only")
→ exists: false, count: 0

Reasoning: "Record missing despite success. Check if save_product was called."
```

**Level 1 Analysis**:
```
get_trace_structure() → Check run hierarchy
→ dept_2: [img_3, cat_4]  # No save_product!

Reasoning: "Department never called save_product. Logic issue."
```

**Investigation**:
```
analyze_decision_point("dept_2")
→ Department decided not to call save_product
→ Reason: Missing required field

Conclusion: "Department skipped save due to validation. Should have asked user."
```

**Token Usage**: 1,500 tokens
**Time**: 2 seconds
**Outcome**: Architecture issue identified

### Example 3: Complex Issue (All Levels)

**Scenario**: Multi-product batch cataloging - partial failures

**Level 0 Analysis**:
```
get_trace_structure("trace_789")
→ failed_runs: ["save_product_10", "save_product_12"]
→ 2 out of 5 products failed

Reasoning: "Partial failure. Need to understand pattern."
```

**Level 1 Analysis**:
```
For each failed run:
    analyze_failure_chain()

→ save_product_10: ValidationError (price type)
→ save_product_12: ValidationError (price type)

Reasoning: "Same error for both. Common root cause likely."
```

**Level 2 Analysis**:
```
trace_data_lineage("price", "save_product_10")
trace_data_lineage("price", "save_product_12")

→ Product 1: price="99" (string) from specialist_8
→ Product 2: price="149" (string) from specialist_9

Reasoning: "Both specialists returned string prices. Systematic prompt issue."
```

**Token Usage**: 7,000 tokens
**Time**: 4 seconds
**Outcome**: Pattern identified across multiple failures

---

## Best Practices

### For Tool Implementers

1. **Always fetch metadata first**
   - Never fetch full details without structure overview
   - Structure guides where to drill down

2. **Use selective fetching**
   - Only fetch failed/slow/expensive runs
   - Don't fetch successful runs unless investigating context

3. **Cache aggressively**
   - Cache trace structures (5min TTL)
   - Avoid redundant API calls

4. **Implement timeouts**
   - LangSmith API can be slow
   - Set 30s timeout for API calls

5. **Handle rate limits**
   - LangSmith: 100 requests/minute
   - Implement exponential backoff

### For Claude (Analysis)

1. **Start lightweight**
   - Always begin with Level 0
   - Most issues visible in metadata

2. **Explain your reasoning**
   - Show what you found in structure
   - Explain why drilling down
   - Or why stopping at Level 0

3. **Be surgical**
   - "I need to check save_product and cataloging_specialist"
   - Not: "Let me fetch everything"

4. **Know when to stop**
   - Clear error + isolated failure → Stop at Level 1
   - Vague error + multiple failures → Go to Level 2

5. **Track token usage**
   - If exceeding 3,000 tokens, explain why
   - Most analyses should be < 2,000 tokens

### For Users

1. **Trust the hierarchy**
   - Level 0 is usually sufficient
   - Deep dives are rare

2. **Provide context**
   - Tell Claude if issue is subtle
   - Mention if architecture-related

3. **Review token costs**
   - Check analysis efficiency
   - Question if consistently high (>5,000)

---

## Related Documents

- **[AUTONOMOUS_TESTING_FRAMEWORK.md](./AUTONOMOUS_TESTING_FRAMEWORK.md)** - Main framework overview
- **[TOOL_SPECIFICATIONS.md](./TOOL_SPECIFICATIONS.md)** - Complete tool API reference
- **[LANGSMITH_FEATURES.md](../tech/LANGSMITH_FEATURES.md)** - LangSmith capabilities

---

**Last Updated**: 2025-01-16
**Next Review**: After Phase 1 implementation
