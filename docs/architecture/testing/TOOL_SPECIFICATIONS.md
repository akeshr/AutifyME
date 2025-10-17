# Testing Tool Specifications

**Status**: Design Complete | **Date**: 2025-10-17
**Purpose**: Complete API reference for autonomous testing framework tools

---

## Overview

This document provides detailed specifications for the 5 essential testing tools that enable Claude to observe workflow executions and trace data.

**Core Principle**: These tools provide **information only**. Claude uses existing tools (Edit, Write, Read, MCP) for analysis and fixes.

---

## Tool 1: execute_scenario

Executes a test scenario via simulate.py and returns execution outcome.

### Function Signature

```python
def execute_scenario(
    scenario_id: str,
    hitl_mode: str = "auto_approve",
    media_path: Optional[str] = None
) -> ExecutionResult:
    """Execute test scenario programmatically.

    Args:
        scenario_id: Scenario name or custom prompt text
        hitl_mode: HITL behavior - "auto_approve" | "auto_reject" | "auto_edit" | "manual"
        media_path: Optional path to media file for multimodal testing

    Returns:
        ExecutionResult with success status, trace info, metrics
    """
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `scenario_id` | str | Yes | Scenario identifier or custom prompt |
| `hitl_mode` | str | No | HITL behavior (default: "auto_approve") |
| `media_path` | str | No | Path to image/video file |

### Return Type: ExecutionResult

```python
class ExecutionResult(BaseModel):
    """Result of scenario execution."""

    success: bool
    """Whether scenario completed successfully."""

    thread_id: str
    """LangGraph thread ID (format: console:test_abc123)."""

    trace_url: str
    """LangSmith trace URL for viewing in browser."""

    trace_id: str
    """LangSmith trace ID for API queries."""

    products_created: int
    """Number of products created in database."""

    execution_time_seconds: float
    """Total execution time."""

    errors: List[str]
    """List of error messages if failed."""
```

### Usage Example

```python
# Basic scenario test
result = execute_scenario("cataloging_with_image", "auto_approve")

if not result.success:
    print(f"Scenario failed: {result.errors}")
    # Analyze trace
    trace = get_trace_overview(result.trace_id)

# Multimodal test with image
result = execute_scenario(
    scenario_id="cataloging_with_image",
    hitl_mode="auto_approve",
    media_path="tests/fixtures/images/sneakers.jpg"
)

# Custom prompt test
result = execute_scenario(
    scenario_id="Catalog these blue jeans for $49",
    hitl_mode="auto_approve"
)
```

### Implementation Notes

- Wraps simulate.py functionality
- Sets up ConsoleChannel with specified HITL mode
- Creates WorkflowRunner with checkpointer
- Captures trace_id from LangSmith context
- Returns structured execution summary

---

## Tool 2: get_trace_overview

Fetches hierarchical structure of entire trace with metadata only (no inputs/outputs).

**This is Level 0 analysis** - always start here to identify which runs failed.

### Function Signature

```python
def get_trace_overview(trace_id: str) -> TraceOverview:
    """Get lightweight trace structure - metadata only.

    Fetches hierarchical run tree with status, timing, costs but excludes
    inputs/outputs to minimize token usage. Use this first to identify
    failures before drilling down with get_run_details().

    Args:
        trace_id: LangSmith trace ID from ExecutionResult

    Returns:
        TraceOverview with run hierarchy and metadata
    """
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `trace_id` | str | Yes | LangSmith trace ID |

### Return Type: TraceOverview

```python
class TraceOverview(BaseModel):
    """Hierarchical overview of trace execution."""

    trace_id: str
    """LangSmith trace ID."""

    total_runs: int
    """Total number of runs in trace."""

    total_cost: float
    """Total cost in dollars."""

    total_latency_ms: int
    """Total execution time in milliseconds."""

    run_tree: List[RunNode]
    """Hierarchical tree of all runs."""

class RunNode(BaseModel):
    """Single run node in trace hierarchy."""

    run_id: str
    """Unique run ID for drilling down."""

    name: str
    """Run name: 'PM' | 'CatalogingDept' | 'ImageAnalysisSpecialist' | 'save_product'."""

    run_type: str
    """Run type: 'chain' | 'llm' | 'tool'."""

    status: str
    """Status: 'success' | 'error'."""

    start_time: datetime
    """When run started."""

    end_time: datetime
    """When run ended."""

    duration_ms: int
    """Duration in milliseconds."""

    error: Optional[str]
    """High-level error message if failed (not full traceback)."""

    children: List[RunNode]
    """Child runs (recursive tree structure)."""
```

### Usage Example

```python
# Get trace overview first
overview = get_trace_overview(trace_id)

print(f"Total runs: {overview.total_runs}")
print(f"Total cost: ${overview.total_cost:.3f}")

# Visualize hierarchy
def print_tree(node, indent=0):
    status_icon = "✅" if node.status == "success" else "❌"
    print(f"{'  ' * indent}{status_icon} {node.name} ({node.duration_ms}ms)")
    if node.error:
        print(f"{'  ' * indent}   Error: {node.error}")
    for child in node.children:
        print_tree(child, indent + 1)

for root in overview.run_tree:
    print_tree(root)

# Identify failures
def find_failed_runs(node, failed=[]):
    if node.status == "error":
        failed.append(node.run_id)
    for child in node.children:
        find_failed_runs(child, failed)
    return failed

failed_run_ids = find_failed_runs(overview.run_tree[0])

# Now drill into specific failures
for run_id in failed_run_ids:
    details = get_run_details(run_id)
    print(f"Failed run {details.name}: {details.error}")
```

### Token Cost

**~500 tokens** (vs 50K+ for full trace dump)

### Implementation Notes

- Uses LangSmith API: `client.list_runs(trace_id=trace_id)`
- Fetches metadata only: `select=["id", "name", "run_type", "status", "start_time", "end_time", "error", "parent_run_id"]`
- Excludes inputs/outputs fields (these are expensive)
- Builds recursive tree from parent_run_id relationships
- Returns structured hierarchy for visualization

---

## Tool 3: get_run_details

Fetches specific run's inputs, outputs, and error details.

**This is Level 1 analysis** - use after identifying failures in Level 0.

### Function Signature

```python
def get_run_details(run_id: str) -> RunDetails:
    """Get detailed information for specific run.

    Fetches inputs, outputs, and error details for a single run.
    Use this after get_trace_overview() identifies a failure to
    investigate the specific problem.

    Args:
        run_id: Run ID from TraceOverview

    Returns:
        RunDetails with inputs, outputs, error
    """
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `run_id` | str | Yes | Run ID from TraceOverview |

### Return Type: RunDetails

```python
class RunDetails(BaseModel):
    """Detailed information for a specific run."""

    run_id: str
    """Run ID."""

    name: str
    """Run name."""

    run_type: str
    """Run type: 'chain' | 'll m' | 'tool'."""

    inputs: Dict[str, Any]
    """Full inputs (prompts, tool arguments, etc)."""

    outputs: Optional[Dict[str, Any]]
    """Full outputs if successful (structured output, tool results)."""

    error: Optional[str]
    """Full error message and traceback if failed."""

    metadata: RunMetadata
    """Additional metadata."""

class RunMetadata(BaseModel):
    """Metadata for a run."""

    model: str
    """Model used (e.g., 'gpt-4')."""

    total_tokens: int
    """Token usage."""

    latency_ms: int
    """Latency in milliseconds."""

    parent_run_id: Optional[str]
    """Parent run ID for context."""
```

### Usage Example

```python
# After identifying failure in Level 0
overview = get_trace_overview(trace_id)
failed_runs = [node.run_id for node in overview.run_tree if node.status == "error"]

# Get details for each failure
for run_id in failed_runs:
    details = get_run_details(run_id)

    print(f"Failed Run: {details.name}")
    print(f"Error: {details.error}")
    print(f"Inputs: {details.inputs}")

    # Analyze based on run type
    if details.run_type == "tool":
        # Tool failure - check tool inputs
        print(f"Tool was called with: {details.inputs}")

    elif details.run_type == "llm":
        # LLM failure - check prompt and response
        prompt = details.inputs.get("messages", [])
        print(f"Prompt: {prompt}")

        if details.outputs:
            print(f"Output: {details.outputs}")

    # Check if parent context needed
    if details.metadata.parent_run_id:
        parent = get_run_details(details.metadata.parent_run_id)
        print(f"Parent run: {parent.name}")
```

### Token Cost

**~1,500 tokens per run** (includes inputs/outputs)

### Implementation Notes

- Uses LangSmith API: `client.read_run(run_id)`
- Fetches full run with inputs/outputs
- Returns structured data for analysis
- Use sparingly - only for identified failures

---

## Tool 4: get_run_messages

Fetches full conversation messages for a run (expensive, rare use).

**This is Level 2 analysis** - only use when Level 1 doesn't explain the issue.

### Function Signature

```python
def get_run_messages(run_id: str) -> RunMessages:
    """Get full conversation messages for a run.

    Fetches complete message history for an LLM run. This is expensive
    in tokens and should only be used when get_run_details() doesn't
    provide enough information to understand the failure.

    Args:
        run_id: Run ID from TraceOverview (typically LLM run)

    Returns:
        RunMessages with full conversation history
    """
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `run_id` | str | Yes | Run ID (should be LLM run type) |

### Return Type: RunMessages

```python
class RunMessages(BaseModel):
    """Full conversation messages for a run."""

    run_id: str
    """Run ID."""

    messages: List[Message]
    """All messages in conversation."""

class Message(BaseModel):
    """Single message in conversation."""

    role: str
    """Message role: 'system' | 'user' | 'assistant'."""

    content: str
    """Message content (text, JSON, etc)."""

    tool_calls: Optional[List[ToolCall]]
    """Tool calls made by assistant."""

    tool_results: Optional[List[ToolResult]]
    """Tool results returned."""

class ToolCall(BaseModel):
    """Tool call made by assistant."""

    name: str
    """Tool name."""

    arguments: Dict[str, Any]
    """Tool arguments."""

class ToolResult(BaseModel):
    """Tool execution result."""

    name: str
    """Tool name."""

    result: Any
    """Tool return value."""
```

### Usage Example

```python
# Only use after Level 1 analysis doesn't explain issue
details = get_run_details(specialist_run_id)

# If error unclear, fetch full messages
if "unclear reasoning" or "need to see full context":
    messages = get_run_messages(specialist_run_id)

    print("Full Conversation:")
    for msg in messages.messages:
        print(f"[{msg.role}]: {msg.content[:200]}...")

        if msg.tool_calls:
            for call in msg.tool_calls:
                print(f"  Tool Call: {call.name}({call.arguments})")

        if msg.tool_results:
            for result in msg.tool_results:
                print(f"  Tool Result: {result.name} = {result.result}")
```

### Token Cost

**~5,000+ tokens** (varies with conversation length)

### Usage Criteria

Only use when:
- Root cause unclear from Level 0 + Level 1
- Need to see exact prompt/response
- Debugging complex multi-step reasoning
- Investigating context leakage

### Implementation Notes

- Uses LangSmith API: `client.read_run(run_id)`
- Extracts full message array from inputs/outputs
- Expensive - use rarely
- Most issues can be diagnosed with Level 0 + Level 1

---

## Tool 5: list_recent_tests

Lists recent test executions for progress tracking.

### Function Signature

```python
def list_recent_tests(limit: int = 10) -> TestHistory:
    """List recent test executions.

    Returns history of recent test executions with outcomes.
    Useful for tracking progress across iterations and comparing
    metrics before/after improvements.

    Args:
        limit: Maximum number of tests to return (default: 10)

    Returns:
        TestHistory with list of recent executions
    """
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | No | Max tests to return (default: 10) |

### Return Type: TestHistory

```python
class TestHistory(BaseModel):
    """History of test executions."""

    tests: List[TestExecution]
    """List of test executions, newest first."""

class TestExecution(BaseModel):
    """Single test execution record."""

    timestamp: datetime
    """When test was executed."""

    scenario_id: str
    """Scenario identifier."""

    thread_id: str
    """LangGraph thread ID."""

    trace_url: str
    """LangSmith trace URL."""

    success: bool
    """Whether test passed."""

    products_created: int
    """Products created in database."""

    execution_time_seconds: float
    """Execution time."""

    errors_summary: str
    """Brief error summary if failed."""
```

### Usage Example

```python
# View recent test results
history = list_recent_tests(limit=20)

print(f"Recent Tests ({len(history.tests)}):")
for test in history.tests:
    status = "✅" if test.success else "❌"
    print(f"{status} {test.scenario_id} - {test.timestamp} ({test.execution_time_seconds:.1f}s)")
    if not test.success:
        print(f"   Error: {test.errors_summary}")

# Compare before/after improvement
history = list_recent_tests(limit=10)
scenario = "cataloging_with_image"

scenario_tests = [t for t in history.tests if t.scenario_id == scenario]
recent = scenario_tests[0]
baseline = scenario_tests[-1]

print(f"Improvement for {scenario}:")
print(f"  Before: {'✅' if baseline.success else '❌'} ({baseline.execution_time_seconds:.1f}s)")
print(f"  After:  {'✅' if recent.success else '❌'} ({recent.execution_time_seconds:.1f}s)")

# Track success rate over time
success_rate = sum(1 for t in history.tests if t.success) / len(history.tests)
print(f"Overall success rate: {success_rate * 100:.1f}%")
```

### Implementation Notes

- Stores test history in local SQLite DB or JSON file
- Captures key metrics from ExecutionResult
- Sorted by timestamp (newest first)
- Used for improvement validation and progress tracking

---

## Implementation Guidance

### Phase 1 (Week 1)

Implement these 5 tools in order:

1. `execute_scenario()` - Core execution capability
2. `get_trace_overview()` - Level 0 analysis
3. `get_run_details()` - Level 1 analysis
4. `list_recent_tests()` - History tracking
5. Test manually with Claude on 5-10 scenarios

### File Structure

```
tests/tools/
  ├── execution.py          # execute_scenario
  ├── trace_analysis.py     # get_trace_overview, get_run_details, get_run_messages
  ├── test_history.py       # list_recent_tests
  └── models.py             # Pydantic models
```

### Dependencies

```python
# LangSmith client
from langsmith import Client

# Supabase MCP (already available)
# No additional dependencies needed

# Existing simulate.py infrastructure
from tests.cli.simulate import ConsoleChannel, WorkflowRunner
```

### Testing Strategy

Manual testing with Claude:
1. Execute 5 scenarios with `execute_scenario()`
2. Analyze failures with `get_trace_overview()` + `get_run_details()`
3. Validate token costs (Level 0: ~500, Level 1: ~1,500)
4. Test improvement cycle end-to-end
5. Verify history tracking with `list_recent_tests()`

---

## Token Budget Summary

| Tool | Token Cost | Frequency |
|------|------------|-----------|
| `execute_scenario()` | Minimal | Every test |
| `get_trace_overview()` | ~500 | Every test (Level 0) |
| `get_run_details()` | ~1,500 | Per failure (Level 1) |
| `get_run_messages()` | ~5,000+ | Rare (Level 2) |
| `list_recent_tests()` | Minimal | As needed |

**Target**: < 3K tokens per scenario analysis (90% cases stay at Level 0 + Level 1)

**Savings**: 25x vs naive full dump approach (50K → 2K tokens)

---

## Related Documentation

- `AUTONOMOUS_TESTING_FRAMEWORK.md` - Complete framework overview
- `HIERARCHICAL_TRACE_ANALYSIS.md` - Token optimization strategy
- `QUICK_REFERENCE.md` - Cheat sheet for common workflows
