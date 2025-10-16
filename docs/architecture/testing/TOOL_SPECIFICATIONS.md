# Tool Specifications - Complete API Reference

**Date**: 2025-01-16
**Status**: 🔬 DESIGN
**Purpose**: Complete API reference for all Autonomous Testing Framework tools

---

## Executive Summary

This document provides complete API specifications for all tools used in the Autonomous Testing Framework. Each tool includes: function signature, parameters, return types (Pydantic models), usage examples, implementation notes, and error handling patterns.

**Tool Categories**:
- **Execution Tools** (2): Run scenarios and conversations
- **Analysis Tools - Level 0** (3): Lightweight overview
- **Analysis Tools - Level 1** (4): Focused investigation
- **Analysis Tools - Level 2** (3): Deep dive
- **Improvement Tools** (4): Generate and apply fixes
- **Helper Tools** (4): Workflow management
- **Supabase MCP Tools** (3): Database validation

**Total**: 23 tools

---

## Table of Contents

1. [Execution Tools](#execution-tools)
2. [Analysis Tools - Level 0](#analysis-tools---level-0)
3. [Analysis Tools - Level 1](#analysis-tools---level-1)
4. [Analysis Tools - Level 2](#analysis-tools---level-2)
5. [Improvement Tools](#improvement-tools)
6. [Helper Tools](#helper-tools)
7. [Supabase MCP Tools](#supabase-mcp-tools)
8. [Pydantic Models](#pydantic-models)
9. [Error Handling](#error-handling)
10. [Usage Patterns](#usage-patterns)

---

## Execution Tools

### `execute_scenario`

**Purpose**: Execute test scenario via simulate.py programmatically

**Signature**:
```python
def execute_scenario(
    scenario_id: str,
    hitl_mode: str = "auto_approve",
    media_path: Optional[str] = None
) -> ExecutionResult:
    """Execute test scenario and return execution summary."""
```

**Parameters**:
- `scenario_id` (str, required): Scenario identifier
  - Examples: "cataloging_with_image", "text_clear", "greeting_to_cataloging"
  - Must match predefined scenario in simulate.py or be custom message
- `hitl_mode` (str, default="auto_approve"): HITL behavior
  - Options: "auto_approve" | "auto_reject" | "auto_edit" | "interactive"
- `media_path` (Optional[str]): Path to media file for testing
  - Examples: "tests/fixtures/images/sneaker.jpg"
  - Supports: images, audio, video, documents

**Returns**: `ExecutionResult`
```python
class ExecutionResult(BaseModel):
    trace_id: str           # LangSmith root trace ID
    run_id: str             # Top-level PM run ID
    thread_id: str          # LangGraph thread ID (format: "console:user_abc")
    success: bool           # Did scenario succeed?
    duration: float         # Total execution time (seconds)
    cost: float             # Total cost (dollars)
    error: Optional[str]    # Error message if failed
    messages_sent: List[dict]  # All messages sent via ConsoleChannel
    approval_triggered: bool   # Was HITL approval triggered?
```

**Implementation**:
```python
def execute_scenario(scenario_id, hitl_mode="auto_approve", media_path=None):
    # Import simulate infrastructure
    from tests.cli.simulate import run_scenario, ConsoleChannel
    from autifyme_agents.integrations.storage.storage_factory import get_storage
    from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
    from autifyme_agents.workflows.orchestration.runner_v2 import WorkflowRunner

    # Setup
    storage = get_storage()
    channel = ConsoleChannel(hitl_mode=hitl_mode)
    checkpointer = get_checkpointer()
    runner = WorkflowRunner(channel=channel, storage=storage, checkpointer=checkpointer)

    # Generate unique sender to avoid checkpoint pollution
    import uuid
    sender = f"test_{uuid.uuid4().hex[:8]}"

    # Capture trace_id from LangSmith context
    from langsmith import get_current_run_tree

    start_time = time.time()
    try:
        runner.handle_message(sender=sender, text=scenario_id, media_id=media_path)

        # Get trace_id
        run_tree = get_current_run_tree()
        trace_id = run_tree.trace_id if run_tree else None
        run_id = run_tree.id if run_tree else None

        duration = time.time() - start_time

        return ExecutionResult(
            trace_id=trace_id,
            run_id=run_id,
            thread_id=channel.format_thread_id(sender),
            success=True,
            duration=duration,
            cost=estimate_cost(trace_id),  # Calculate from trace
            error=None,
            messages_sent=channel.messages_sent,
            approval_triggered=any(m["type"] == "approval" for m in channel.messages_sent)
        )
    except Exception as e:
        duration = time.time() - start_time
        return ExecutionResult(
            trace_id=None,
            run_id=None,
            thread_id=channel.format_thread_id(sender),
            success=False,
            duration=duration,
            cost=0,
            error=str(e),
            messages_sent=channel.messages_sent,
            approval_triggered=False
        )
```

**Usage Example**:
```python
# Execute scenario
result = execute_scenario("cataloging_with_image", "auto_approve")

if result.success:
    print(f"✅ Scenario passed in {result.duration:.1f}s")
    print(f"Trace: {result.trace_id}")
else:
    print(f"❌ Scenario failed: {result.error}")
    # Analyze failure
    structure = get_trace_structure(result.trace_id)
```

---

### `execute_conversation`

**Purpose**: Execute multi-turn conversation scenario from YAML definition

**Signature**:
```python
def execute_conversation(scenario_yaml: str) -> ConversationResult:
    """Execute multi-turn conversation and return results."""
```

**Parameters**:
- `scenario_yaml` (str, required): Path to YAML scenario file
  - Examples: "tests/scenarios/greeting_to_cataloging.yaml"
  - Must be valid conversation scenario YAML

**Returns**: `ConversationResult`
```python
class ConversationResult(BaseModel):
    success: bool
    turns: int               # Number of conversation turns
    trace_ids: List[str]     # One trace_id per turn
    thread_id: str           # Shared thread across turns
    total_duration: float
    total_cost: float
    failed_turn: Optional[int]  # Which turn failed (if any)
```

**Implementation**:
```python
def execute_conversation(scenario_yaml):
    from tests.cli.conversation import load_scenario, execute_turns

    # Load YAML scenario
    scenario = load_scenario(scenario_yaml)

    # Execute each turn
    results = execute_turns(scenario, hitl_mode="auto_approve")

    return ConversationResult(
        success=all(r.success for r in results),
        turns=len(results),
        trace_ids=[r.trace_id for r in results],
        thread_id=results[0].thread_id,
        total_duration=sum(r.duration for r in results),
        total_cost=sum(r.cost for r in results),
        failed_turn=next((i for i, r in enumerate(results) if not r.success), None)
    )
```

**Usage Example**:
```python
result = execute_conversation("tests/scenarios/greeting_to_cataloging.yaml")

if result.success:
    print(f"✅ All {result.turns} turns succeeded")
else:
    print(f"❌ Turn {result.failed_turn} failed")
    # Analyze failed turn
    failed_trace = result.trace_ids[result.failed_turn]
```

---

## Analysis Tools - Level 0

### `get_trace_structure`

**Purpose**: Get lightweight trace structure (metadata only)

**Signature**:
```python
def get_trace_structure(trace_id: str) -> TraceStructure:
    """Fetch trace structure without inputs/outputs."""
```

**Parameters**:
- `trace_id` (str, required): LangSmith trace ID

**Returns**: `TraceStructure`
```python
class TraceStructure(BaseModel):
    run_hierarchy: Dict[str, List[str]]  # {parent_id: [child_ids]}
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
    token_usage: Optional[int]
```

**Token Cost**: ~500 tokens

**Usage Example**: See HIERARCHICAL_TRACE_ANALYSIS.md

---

### `get_scenario_outcome`

**Purpose**: Get high-level scenario result

**Signature**:
```python
def get_scenario_outcome(thread_id: str) -> ScenarioOutcome:
    """Get scenario outcome from LangGraph thread."""
```

**Parameters**:
- `thread_id` (str, required): LangGraph thread ID

**Returns**: `ScenarioOutcome`
```python
class ScenarioOutcome(BaseModel):
    success: bool
    duration: float
    total_cost: float
    message_count: int
    approval_triggered: bool
    final_state: str        # "completed" | "failed" | "awaiting_approval"
    error_summary: Optional[str]
```

**Implementation**:
```python
def get_scenario_outcome(thread_id):
    from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer

    checkpointer = get_checkpointer()
    config = {"configurable": {"thread_id": thread_id}}

    # Get final state
    state_tuple = checkpointer.get_tuple(config)
    if not state_tuple:
        return ScenarioOutcome(success=False, error_summary="No state found")

    state = state_tuple.checkpoint
    return ScenarioOutcome(
        success=state.get("status") == "completed",
        duration=calculate_duration(state),
        total_cost=state.get("total_cost", 0),
        message_count=len(state.get("messages", [])),
        approval_triggered=bool(state.get("pending_interrupts")),
        final_state=state.get("status", "unknown"),
        error_summary=state.get("last_error")
    )
```

**Usage Example**:
```python
outcome = get_scenario_outcome("console:test_abc123")
if not outcome.success:
    print(f"Scenario failed: {outcome.error_summary}")
```

---

### `quick_db_check`

**Purpose**: Quick DB existence check via Supabase MCP

**Signature**:
```python
def quick_db_check(
    scenario_id: str,
    expected_count: int = 1
) -> QuickCheck:
    """Quick COUNT query to verify records exist."""
```

**Parameters**:
- `scenario_id` (str, required): Scenario identifier (stored in product metadata)
- `expected_count` (int, default=1): Expected number of records

**Returns**: `QuickCheck`
```python
class QuickCheck(BaseModel):
    exists: bool
    count: int
    matches_expected: bool
    table: str
```

**Implementation**:
```python
def quick_db_check(scenario_id, expected_count=1):
    result = mcp__supabase__execute_sql(
        f"SELECT COUNT(*) as count FROM products WHERE metadata->>'scenario_id' = '{scenario_id}'"
    )
    count = result[0]['count']

    return QuickCheck(
        exists=count > 0,
        count=count,
        matches_expected=(count == expected_count),
        table="products"
    )
```

**Usage Example**:
```python
check = quick_db_check("cataloging_with_image")
if not check.matches_expected:
    print(f"Expected {check.expected_count}, found {check.count}")
    # Fetch details
    records = get_product_record(scenario_id="cataloging_with_image")
```

---

## Analysis Tools - Level 1

### `analyze_failure_chain`

**Purpose**: Analyze specific failure with context

**Signature**:
```python
def analyze_failure_chain(failed_run_id: str) -> FailureAnalysis:
    """Fetch failure details and trace root cause."""
```

**Parameters**:
- `failed_run_id` (str, required): Run ID that failed

**Returns**: `FailureAnalysis`
```python
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
```

**Token Cost**: ~1,000 tokens

**Usage Example**: See HIERARCHICAL_TRACE_ANALYSIS.md

---

### `validate_structured_output`

**Purpose**: Check if component returned correct Pydantic model

**Signature**:
```python
def validate_structured_output(
    run_id: str,
    expected_schema: str
) -> ValidationResult:
    """Validate output against Pydantic schema."""
```

**Parameters**:
- `run_id` (str, required): Run ID to validate
- `expected_schema` (str, required): Schema name
  - Options: "Product" | "ImageAnalysisResult" | "CatalogingResult"

**Returns**: `ValidationResult`
```python
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
```

**Implementation**:
```python
def validate_structured_output(run_id, expected_schema):
    from langsmith import Client
    from autifyme_agents.schemas.models import Product, ImageAnalysisResult, CatalogingResult

    schemas = {
        "Product": Product,
        "ImageAnalysisResult": ImageAnalysisResult,
        "CatalogingResult": CatalogingResult
    }

    schema_class = schemas.get(expected_schema)
    if not schema_class:
        raise ValueError(f"Unknown schema: {expected_schema}")

    # Fetch run output
    client = Client()
    run = client.read_run(run_id)
    output = run.outputs

    # Validate against schema
    violations = []
    type_mismatches = []

    try:
        validated = schema_class(**output)
    except ValidationError as e:
        for error in e.errors():
            field = error['loc'][0] if error['loc'] else 'unknown'
            violations.append(FieldViolation(
                field=field,
                expected=error['type'],
                actual=output.get(field),
                message=error['msg']
            ))

    return ValidationResult(
        schema_valid=len(violations) == 0,
        violations=violations,
        type_mismatches=type_mismatches,
        missing_fields=[],
        extra_fields=[]
    )
```

**Usage Example**:
```python
validation = validate_structured_output("specialist_run_id", "Product")
if not validation.schema_valid:
    for v in validation.violations:
        print(f"Field '{v.field}': {v.message}")
```

---

### `get_product_record`

**Purpose**: Get product record from Supabase via MCP

**Signature**:
```python
def get_product_record(
    product_id: Optional[str] = None,
    scenario_id: Optional[str] = None,
    filters: Optional[Dict] = None
) -> ProductRecordResult:
    """Query products from Supabase."""
```

**Parameters**:
- `product_id` (Optional[str]): Specific product UUID
- `scenario_id` (Optional[str]): Get products for scenario
- `filters` (Optional[Dict]): Additional WHERE clauses

**Returns**: `ProductRecordResult`
```python
class ProductRecordResult(BaseModel):
    found: bool
    count: int
    records: List[ProductRecord]

class ProductRecord(BaseModel):
    id: str
    name: Optional[str]
    description: Optional[str]
    price: Optional[float]
    sizes: List[str]
    colors: List[str]
    image_urls: List[str]
    created_at: str
    metadata: dict
```

**Implementation**:
```python
def get_product_record(product_id=None, scenario_id=None, filters=None):
    if product_id:
        query = f"SELECT * FROM products WHERE id = '{product_id}'"
    elif scenario_id:
        query = f"SELECT * FROM products WHERE metadata->>'scenario_id' = '{scenario_id}'"
    else:
        query = "SELECT * FROM products LIMIT 10"

    result = mcp__supabase__execute_sql(query)

    return ProductRecordResult(
        found=len(result) > 0,
        count=len(result),
        records=[ProductRecord(**r) for r in result]
    )
```

**Usage Example**:
```python
result = get_product_record(scenario_id="cataloging_with_image")
if result.found:
    record = result.records[0]
    print(f"Product: {record.name}, Price: {record.price}")
```

---

## Analysis Tools - Level 2

### `get_full_run_details`

**Purpose**: Fetch complete run details (expensive, use sparingly)

**Signature**:
```python
def get_full_run_details(run_id: str) -> FullRunDetails:
    """Fetch full run with inputs/outputs."""
```

**Parameters**:
- `run_id` (str, required): Run ID to fetch

**Returns**: `FullRunDetails`
```python
class FullRunDetails(BaseModel):
    run_id: str
    name: str
    run_type: str
    status: str
    duration: float
    cost: float
    inputs: dict
    outputs: dict
    error: Optional[dict]
    metadata: dict
    children: List[str]
    parent: Optional[str]
```

**Token Cost**: 5,000-10,000 tokens

**Usage Criteria**:
- Root cause unclear from Level 0-1
- Need exact prompt/response
- Investigating complex reasoning
- Context leakage suspected

---

### `trace_data_lineage`

**Purpose**: Trace where data came from through execution hierarchy

**Signature**:
```python
def trace_data_lineage(
    field: str,
    final_run_id: str
) -> DataLineage:
    """Trace field transformations."""
```

**Parameters**:
- `field` (str, required): Field name to trace (e.g., "price")
- `final_run_id` (str, required): Run where field appears

**Returns**: `DataLineage`
```python
class DataLineage(BaseModel):
    field: str
    transformations: List[Transformation]
    origin_run_id: str
    origin_run_name: str

class Transformation(BaseModel):
    run_id: str
    run_name: str
    input_value: Any
    output_value: Any
    transformation_type: str  # "coercion" | "extraction" | "passthrough"
```

**Usage Example**: See HIERARCHICAL_TRACE_ANALYSIS.md

---

## Improvement Tools

### `generate_prompt_improvement`

**Purpose**: Generate improved prompt using LLM

**Signature**:
```python
def generate_prompt_improvement(
    issue_description: str,
    current_prompt: str,
    trace_examples: List[str]
) -> PromptImprovement:
    """Generate improved prompt based on issue."""
```

**Parameters**:
- `issue_description` (str, required): Human-readable issue
- `current_prompt` (str, required): Full current prompt text
- `trace_examples` (List[str], required): Run IDs showing issue

**Returns**: `PromptImprovement`
```python
class PromptImprovement(BaseModel):
    proposed_prompt: str
    reasoning: str
    expected_impact: str
    diff: str
    confidence: float
    affected_scenarios: List[str]
```

**Implementation**:
```python
def generate_prompt_improvement(issue_description, current_prompt, trace_examples):
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4", temperature=0.3)

    # Fetch trace examples
    examples_text = "\n\n".join([
        f"Example {i+1}:\n{get_trace_example(run_id)}"
        for i, run_id in enumerate(trace_examples)
    ])

    prompt = f"""You are an expert prompt engineer. Analyze this issue and improve the prompt.

Issue: {issue_description}

Current Prompt:
{current_prompt}

Trace Examples Showing Issue:
{examples_text}

Generate an improved prompt that fixes this issue. Explain your reasoning and show a diff of changes.

Output JSON:
{{
  "proposed_prompt": "...",
  "reasoning": "...",
  "expected_impact": "...",
  "confidence": 0.0-1.0
}}
"""

    response = llm.invoke(prompt)
    result = json.loads(response.content)

    # Generate diff
    import difflib
    diff = "\n".join(difflib.unified_diff(
        current_prompt.splitlines(),
        result["proposed_prompt"].splitlines(),
        lineterm=""
    ))

    return PromptImprovement(
        proposed_prompt=result["proposed_prompt"],
        reasoning=result["reasoning"],
        expected_impact=result["expected_impact"],
        diff=diff,
        confidence=result["confidence"],
        affected_scenarios=[]  # TODO: Identify affected scenarios
    )
```

**Usage Example**:
```python
improvement = generate_prompt_improvement(
    issue_description="Specialist returns price as string",
    current_prompt=read_file("..."),
    trace_examples=["run_abc123"]
)

print(f"Confidence: {improvement.confidence}")
print(f"Reasoning: {improvement.reasoning}")
print(f"\nDiff:\n{improvement.diff}")
```

---

### `generate_code_fix`

**Purpose**: Generate code fix using LLM

**Signature**:
```python
def generate_code_fix(
    issue_description: str,
    file_path: str,
    error_context: str
) -> CodeFix:
    """Generate code fix for issue."""
```

**Parameters**:
- `issue_description` (str, required): Issue description
- `file_path` (str, required): File to fix
- `error_context` (str, required): Error message/trace

**Returns**: `CodeFix`
```python
class CodeFix(BaseModel):
    proposed_changes: str
    reasoning: str
    files_affected: List[str]
    risk_level: str
    confidence: float
    test_recommendations: List[str]
```

**Usage Example**:
```python
fix = generate_code_fix(
    issue_description="save_product doesn't extract image_urls",
    file_path="agents/src/.../cataloging_tools.py",
    error_context=failure_analysis.error_message
)

if fix.risk_level == "low" and fix.confidence > 0.8:
    print("Safe to apply")
```

---

### `apply_improvement`

**Purpose**: Apply improvement with backup

**Signature**:
```python
def apply_improvement(
    improvement_type: str,
    target_file: str,
    changes: str,
    backup: bool = True
) -> ApplyResult:
    """Apply improvement and create backup."""
```

**Parameters**:
- `improvement_type` (str, required): "prompt" | "code"
- `target_file` (str, required): File to modify
- `changes` (str, required): New content or diff
- `backup` (bool, default=True): Create backup?

**Returns**: `ApplyResult`
```python
class ApplyResult(BaseModel):
    success: bool
    backup_path: Optional[str]
    files_modified: List[str]
    error: Optional[str]
```

**Implementation**:
```python
def apply_improvement(improvement_type, target_file, changes, backup=True):
    from datetime import datetime

    # Create backup
    backup_path = None
    if backup:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{target_file}.backup.{timestamp}"
        shutil.copy(target_file, backup_path)

    try:
        # Apply changes using Edit tool
        with open(target_file, 'r') as f:
            current_content = f.read()

        with open(target_file, 'w') as f:
            f.write(changes)

        # Log to improvement history
        log_improvement(improvement_type, target_file, changes)

        return ApplyResult(
            success=True,
            backup_path=backup_path,
            files_modified=[target_file],
            error=None
        )
    except Exception as e:
        # Restore from backup
        if backup and backup_path:
            shutil.copy(backup_path, target_file)

        return ApplyResult(
            success=False,
            backup_path=backup_path,
            files_modified=[],
            error=str(e)
        )
```

**Usage Example**:
```python
result = apply_improvement(
    improvement_type="prompt",
    target_file="agents/src/.../cataloging_specialist.prompt",
    changes=improvement.proposed_prompt
)

if result.success:
    print(f"✅ Applied. Backup: {result.backup_path}")
```

---

### `compare_execution_metrics`

**Purpose**: Compare metrics before/after improvement

**Signature**:
```python
def compare_execution_metrics(
    baseline_result: ExecutionResult,
    new_result: ExecutionResult
) -> MetricsComparison:
    """Compare execution results."""
```

**Parameters**:
- `baseline_result` (ExecutionResult, required): Before improvement
- `new_result` (ExecutionResult, required): After improvement

**Returns**: `MetricsComparison`
```python
class MetricsComparison(BaseModel):
    improved: bool
    success_rate_delta: float
    latency_delta: float
    cost_delta: float
    quality_delta: Optional[float]
    recommendation: str  # "KEEP" | "REVERT" | "ITERATE"
```

**Implementation**:
```python
def compare_execution_metrics(baseline, new):
    success_delta = int(new.success) - int(baseline.success)
    latency_delta = new.duration - baseline.duration
    cost_delta = new.cost - baseline.cost

    # Decision logic
    if success_delta > 0:
        recommendation = "KEEP"  # Success improved
    elif success_delta == 0 and latency_delta < 0:
        recommendation = "KEEP"  # Latency improved
    elif success_delta < 0:
        recommendation = "REVERT"  # Success degraded
    else:
        recommendation = "ITERATE"  # No clear improvement

    return MetricsComparison(
        improved=(success_delta > 0 or latency_delta < -0.5),
        success_rate_delta=success_delta,
        latency_delta=latency_delta,
        cost_delta=cost_delta,
        quality_delta=None,
        recommendation=recommendation
    )
```

**Usage Example**:
```python
baseline = execute_scenario("test")
# Apply improvement
new = execute_scenario("test")

comparison = compare_execution_metrics(baseline, new)
print(f"Recommendation: {comparison.recommendation}")
```

---

## Helper Tools

### `load_scenario_list`

**Purpose**: Load scenarios matching pattern

**Signature**:
```python
def load_scenario_list(pattern: str) -> List[str]:
    """Get all scenarios matching pattern."""
```

**Parameters**:
- `pattern` (str, required): Glob pattern
  - Examples: "cataloging_*", "text_*", "*_with_image"

**Returns**: List[str] - Scenario IDs

**Implementation**:
```python
def load_scenario_list(pattern):
    from tests.cli.simulate import get_predefined_scenarios
    import fnmatch

    scenarios = get_predefined_scenarios()
    return [s for s in scenarios.keys() if fnmatch.fnmatch(s, pattern)]
```

**Usage Example**:
```python
scenarios = load_scenario_list("cataloging_*")
# ["cataloging_with_image", "cataloging_text_only", ...]
```

---

### `select_next_scenario`

**Purpose**: Select next scenario based on priority

**Signature**:
```python
def select_next_scenario(
    queue: List[str],
    history: Dict[str, Any],
    strategy: str = "failure_rate"
) -> str:
    """Select next scenario to test."""
```

**Parameters**:
- `queue` (List[str], required): Available scenarios
- `history` (Dict, required): Past execution history
- `strategy` (str, default="failure_rate"): Prioritization strategy
  - Options: "failure_rate" | "last_tested" | "impact" | "round_robin"

**Returns**: str - Next scenario ID

**Implementation**:
```python
def select_next_scenario(queue, history, strategy="failure_rate"):
    if strategy == "failure_rate":
        # Prioritize scenarios with highest failure rate
        return max(queue, key=lambda s: history.get(s, {}).get("failure_rate", 0))
    elif strategy == "last_tested":
        # Prioritize scenarios not tested recently
        return min(queue, key=lambda s: history.get(s, {}).get("last_tested", 0))
    elif strategy == "round_robin":
        return queue[0]
```

**Usage Example**:
```python
next_scenario = select_next_scenario(
    queue=["cataloging_with_image", "text_clear"],
    history=improvement_history,
    strategy="failure_rate"
)
```

---

## Supabase MCP Tools

All DB operations use Supabase MCP for security and type safety.

### `mcp__supabase__execute_sql`

**Purpose**: Execute SQL query via MCP

**Signature**: Provided by Supabase MCP

**Usage Example**:
```python
result = mcp__supabase__execute_sql(
    "SELECT * FROM products WHERE price > 50 LIMIT 10"
)
```

---

## Pydantic Models

All tool return types defined as Pydantic models for type safety:

```python
# See individual tool specifications above for complete models
```

---

## Error Handling

All tools follow consistent error handling:

```python
class ToolError(BaseModel):
    tool_name: str
    error_type: str
    error_message: str
    context: dict
    recoverable: bool
    suggested_action: str
```

Tools return errors in result objects, not raise exceptions.

---

## Usage Patterns

### Pattern 1: Hierarchical Analysis

```python
# Level 0
structure = get_trace_structure(trace_id)

if structure.failed_runs:
    # Level 1
    for run_id in structure.failed_runs:
        failure = analyze_failure_chain(run_id)

        if not failure.root_cause_hypothesis:
            # Level 2
            details = get_full_run_details(run_id)
```

### Pattern 2: Improvement Cycle

```python
# Identify issue
failure = analyze_failure_chain(run_id)

# Generate fix
improvement = generate_prompt_improvement(failure.issue, ...)

# Apply
result = apply_improvement("prompt", file, improvement.proposed_prompt)

# Validate
new_execution = execute_scenario(scenario_id)
comparison = compare_execution_metrics(baseline, new_execution)
```

---

**Last Updated**: 2025-01-16
**Next Review**: After Phase 1 implementation
