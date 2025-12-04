# Workflow Evaluation Framework

**Date**: 2025-12-04
**Status**: Design Complete
**Purpose**: World-class framework for intelligent agents to systematically evaluate and improve any agentic workflow

---

## Executive Summary

A first-principles framework that transforms LangSmith traces into structured evaluation contexts, enabling any intelligent agent to:

1. **Extract** a minimal execution tree from trace data
2. **Review** each node's inputs, outputs, reasoning, and decisions sequentially
3. **Evaluate** behavior across multiple dimensions with evidence
4. **Generate** specific, implementable improvements to prompts, tools, or architecture

**Core Insight**: The framework provides structure and data extraction; the evaluating agent provides intelligence and judgment. This separation enables any capable LLM to perform world-class workflow analysis.

---

## Part 1: First Principles

### The Fundamental Problem

Given a trace ID of an executed workflow, how do we enable an intelligent agent to:
1. Understand exactly what happened at each step
2. Assess the quality of each decision point
3. Identify root causes of suboptimal outcomes
4. Produce changes that measurably improve future executions

### Why This Is Hard

| Challenge | Implication |
|-----------|-------------|
| Traces are noisy | Must extract signal from verbose LangSmith data |
| Quality is contextual | Can't use fixed scoring - need judgment |
| Improvements span domains | Prompts, tools, architecture are different beasts |
| Token efficiency matters | Can't dump entire trace to evaluator |

### Design Philosophy

1. **Minimal Viable Context**: Extract only what's needed for evaluation at each stage
2. **Sequential Depth**: Start shallow, go deep only where problems exist
3. **Evidence-Grounded**: Every finding must cite specific trace evidence
4. **Implementation-Ready**: Improvements include exact changes, not vague suggestions

---

## Part 2: The Minimal Execution Tree

### What Is It?

A compact representation of workflow execution that captures:
- **Who** acted (agent name, type, hierarchy level)
- **What** they decided (key decisions, tool calls, outputs)
- **Why** they decided it (visible reasoning, context used)
- **How** it went (success/failure, latency, cost)

### Why "Minimal"?

Full LangSmith traces contain massive amounts of data - serialization details, internal LangChain metadata, streaming chunks, etc. An evaluator needs:
- The decision points (not the plumbing)
- The reasoning (not the token counts)
- The outcomes (not the timestamps)

### Minimal Execution Tree Schema

```
MinimalExecutionTree
|
+-- trace_id: str
+-- outcome: "success" | "failure" | "partial"
+-- total_cost: float
+-- total_latency_ms: int
|
+-- nodes: List[ExecutionNode]
    |
    +-- ExecutionNode
        |
        +-- id: str (run_id)
        +-- agent: str (meaningful name, not "ChatOpenAI")
        +-- type: "orchestrator" | "department" | "specialist" | "tool"
        +-- sequence: int (execution order)
        |
        +-- decision_summary: str (what this node decided)
        +-- reasoning_visible: bool (did it show its work?)
        +-- reasoning_snippet: str | None (key reasoning if visible)
        |
        +-- tool_calls: List[ToolCallSummary]
        |   +-- name: str
        |   +-- args_summary: str (human-readable summary)
        |   +-- result_summary: str
        |   +-- success: bool
        |
        +-- output_summary: str (key output, not full blob)
        +-- output_quality_signals: Dict[str, Any]
        |   +-- has_required_fields: bool
        |   +-- format_correct: bool
        |   +-- data_complete: bool
        |
        +-- context_received: str (summary of input context)
        +-- context_utilized: List[str] (which parts were used)
        +-- context_ignored: List[str] (which parts were NOT used)
        |
        +-- status: "success" | "error"
        +-- error_summary: str | None
        +-- latency_ms: int
        +-- cost: float
        |
        +-- children: List[ExecutionNode] (recursive)
```

### Extraction Process

```
LangSmith Trace
      |
      v
+------------------+
| 1. Fetch runs    |  list_runs(trace_id)
+------------------+
      |
      v
+------------------+
| 2. Filter noise  |  Remove internal LangChain nodes
+------------------+
      |
      v
+------------------+
| 3. Build tree    |  Parent-child from parent_run_id
+------------------+
      |
      v
+------------------+
| 4. Extract       |  Pull decision points, reasoning,
|    signals       |  tool calls, outputs into summaries
+------------------+
      |
      v
+------------------+
| 5. Annotate      |  Add quality signals and
|    quality       |  context utilization markers
+------------------+
      |
      v
MinimalExecutionTree
```

---

## Part 3: Sequential Node Review Protocol

### The Review Loop

For each node in execution order:

```
REVIEW NODE {agent} (sequence {n}/{total})
============================================

1. CONTEXT ASSESSMENT
   - What context did this node receive?
   - Was it sufficient for the task?
   - Was any context missing that should have been provided?

2. DECISION ANALYSIS
   - What decision(s) did this node make?
   - Was the reasoning visible and sound?
   - Given the context, was this the right decision?
   - What would an expert have decided differently?

3. TOOL USAGE ANALYSIS (if applicable)
   - Were the right tools selected?
   - Were arguments correct and complete?
   - Were results handled appropriately?

4. OUTPUT ASSESSMENT
   - Does output meet downstream requirements?
   - Is structure correct?
   - Is data complete and accurate?

5. ANOMALY DETECTION
   - Any unexpected behavior?
   - Any constraint violations?
   - Any efficiency concerns?

6. PRELIMINARY FINDINGS
   - [ ] No issues found
   - [ ] Minor issue: {description}
   - [ ] Major issue: {description}
   - [ ] Critical issue: {description}
```

### When to Go Deeper

The minimal tree provides summaries. Go to full detail (Level 1/2) when:

| Trigger | Action |
|---------|--------|
| Reasoning unclear | Fetch full messages with `get_run_messages()` |
| Tool failure | Fetch run details with `get_run_details()` |
| Output malformed | Fetch full outputs |
| Context mismatch | Fetch full inputs |

This lazy-loading approach keeps token usage efficient while enabling deep investigation.

---

## Part 4: Evaluation Dimensions

### Dimension 1: REASONING_CHAIN

**What we're evaluating**: Quality of the agent's thinking process.

**Key questions**:
- Did the agent show its reasoning (thinking, analysis, rationale)?
- Is the reasoning chain logically sound?
- Are conclusions supported by the reasoning?
- Are there logical gaps or jumps?

**Evidence markers**:
```
GOOD: "Let me analyze... First, I see X. This suggests Y because Z. Therefore, I will do W."
BAD:  "I'll do W." (no reasoning)
BAD:  "I see X, therefore W." (gap between X and W)
```

**Severity classification**:
- **Critical**: Reasoning contradicts evidence or violates constraints
- **Major**: Reasoning has gaps that led to wrong decision
- **Minor**: Reasoning could be clearer but decision was correct
- **OK**: Reasoning is clear and sound

---

### Dimension 2: DECISION_QUALITY

**What we're evaluating**: Correctness of choices made.

**Decision types by agent level**:
| Agent Type | Key Decisions |
|------------|---------------|
| Orchestrator | Which department/specialist to route to |
| Department | Which specialist to invoke, in what order |
| Specialist | How to approach task, which tools to use |
| Tool | (N/A - tools execute, don't decide) |

**Evaluation approach**:
1. Identify all decision points in the node
2. For each decision, assess:
   - What options were available?
   - What option was chosen?
   - Was this optimal given context?
   - What would have been better (if suboptimal)?

**Evidence markers**:
```
GOOD: Routed product image to ImageAnalysisSpecialist (correct for image task)
BAD:  Routed product image to TextExtractionSpecialist (wrong specialist)
```

---

### Dimension 3: TOOL_ORCHESTRATION

**What we're evaluating**: Selection and use of tools.

**Sub-dimensions**:

**3a. Tool Selection**
- Was the right tool chosen for the task?
- Were any necessary tools not called?
- Were any unnecessary tools called?

**3b. Argument Quality**
- Are all required arguments provided?
- Are argument values correct?
- Are argument formats correct?

**3c. Result Handling**
- Was the result correctly interpreted?
- Were errors handled appropriately?
- Was the result properly used in subsequent reasoning?

**Evidence markers**:
```
GOOD: Called analyze_image with valid URL, processed results correctly
BAD:  Called analyze_image without URL (missing required arg)
BAD:  Called extract_text for image analysis (wrong tool)
BAD:  Tool returned error, agent ignored and proceeded (poor error handling)
```

---

### Dimension 4: CONTEXT_ENGINEERING

**What we're evaluating**: How well context flows through the workflow.

**Sub-dimensions**:

**4a. Context Received**
- Did this node receive the context it needed?
- Was context format appropriate?
- Was there too much context (overload)?

**4b. Context Utilization**
- Which provided context was actually used?
- Was important context ignored?
- Was context correctly interpreted?

**4c. Context Propagation**
- Did this node pass appropriate context to children?
- Was context transformed correctly?
- Was any context lost in translation?

**Evidence markers**:
```
GOOD: Received image URL, used it in tool call, passed analysis to next specialist
BAD:  Received image URL but asked user to provide image (ignored context)
BAD:  Received 50KB context blob, only 2KB was relevant (overload)
```

---

### Dimension 5: OUTPUT_INTEGRITY

**What we're evaluating**: Quality and correctness of outputs.

**Sub-dimensions**:

**5a. Structural Correctness**
- Does output match expected schema?
- Are all required fields present?
- Are field types correct?

**5b. Data Quality**
- Is data complete?
- Is data accurate?
- Is data consistent?

**5c. Downstream Compatibility**
- Will this output work for the next node?
- Are there any format issues?
- Is the output actionable?

**Evidence markers**:
```
GOOD: Product extraction has all required fields, correct types, accurate data
BAD:  Missing "price" field (structural failure)
BAD:  Price extracted as "$25" string instead of 25.00 float (type mismatch)
BAD:  Product name doesn't match source image (accuracy failure)
```

---

### Dimension 6: CONSTRAINT_COMPLIANCE

**What we're evaluating**: Adherence to instructions and constraints.

**Constraint sources**:
- System prompt explicit instructions
- System prompt implicit expectations
- Tool schemas and requirements
- Business rules and policies

**Evaluation approach**:
1. Identify all constraints applicable to this node
2. Check each constraint against observed behavior
3. Flag any violations

**Evidence markers**:
```
GOOD: System prompt says "always include confidence score" - output includes confidence
BAD:  System prompt says "never make up data" - output contains hallucinated field
BAD:  System prompt says "respond in JSON" - output is plain text
```

---

## Part 5: Improvement Generation

### The Four Improvement Domains

Every issue maps to one of four improvement domains:

| Domain | What Changes | Example Fix |
|--------|--------------|-------------|
| **PROMPT** | System prompts, instructions | Add explicit field requirements |
| **TOOL** | Tool definitions, schemas | Clarify argument descriptions |
| **ARCHITECTURE** | Workflow structure, routing | Add intermediate specialist |
| **CONTEXT** | What context flows where | Include source URL in context |

### Improvement Specification Format

Each improvement must be fully specified:

```yaml
improvement:
  id: IMP-001
  domain: PROMPT | TOOL | ARCHITECTURE | CONTEXT
  priority: CRITICAL | HIGH | MEDIUM | LOW

  finding:
    dimension: REASONING_CHAIN | DECISION_QUALITY | etc.
    severity: critical | major | minor
    node: {agent_name}
    evidence: |
      Exact quote or reference from trace showing the issue

  root_cause:
    summary: Why this happened (one line)
    analysis: |
      Detailed analysis of root cause

  change:
    component: {file_path or component name}
    location: {specific section or line}

    current: |
      Exact current state (code, prompt text, etc.)

    proposed: |
      Exact proposed state (code, prompt text, etc.)

    diff_summary: What changes between current and proposed

  rationale: |
    Why this change fixes the root cause

  expected_impact:
    - What will improve
    - How to verify improvement

  implementation:
    effort: trivial | small | medium | large
    risk: low | medium | high
    dependencies: []
    steps:
      - Step 1
      - Step 2
```

### Improvement Prioritization Matrix

```
                    IMPACT
                Low    Medium    High
           +--------+--------+--------+
     Low   |   P4   |   P3   |   P2   |
  E        +--------+--------+--------+
  F  Med   |   P3   |   P2   |   P1   |
  F        +--------+--------+--------+
  O  High  |   P2   |   P1   |   P1   |
  R        +--------+--------+--------+
  T
```

- **P1**: Do immediately (high impact, any effort)
- **P2**: Do soon (medium+ impact, medium effort OR high effort + high impact)
- **P3**: Do when able (low-medium impact, low effort)
- **P4**: Consider (low impact, low effort)

---

## Part 6: Complete Evaluation Report Structure

```yaml
workflow_evaluation_report:
  metadata:
    trace_id: str
    trace_url: str
    evaluated_at: datetime
    evaluator: str (model/agent that did evaluation)
    evaluation_duration_ms: int

  execution_summary:
    outcome: success | failure | partial
    total_nodes: int
    total_llm_calls: int
    total_tool_calls: int
    total_cost: float
    total_latency_ms: int

  minimal_execution_tree:
    # Full tree structure as defined above

  node_evaluations:
    - node_id: str
      agent: str
      sequence: int

      dimensions:
        reasoning_chain:
          score: critical | major | minor | ok
          finding: str
          evidence: str

        decision_quality:
          score: critical | major | minor | ok
          finding: str
          evidence: str

        tool_orchestration:
          score: critical | major | minor | ok
          finding: str
          evidence: str

        context_engineering:
          score: critical | major | minor | ok
          finding: str
          evidence: str

        output_integrity:
          score: critical | major | minor | ok
          finding: str
          evidence: str

        constraint_compliance:
          score: critical | major | minor | ok
          finding: str
          evidence: str

      node_summary:
        overall: critical | major | minor | ok
        key_finding: str

  cross_cutting_analysis:
    context_flow:
      finding: str
      issues: []

    delegation_efficiency:
      finding: str
      unnecessary_hops: int
      missed_optimizations: []

    resource_utilization:
      finding: str
      cost_optimization_opportunities: []
      latency_optimization_opportunities: []

    end_to_end_quality:
      goal_achieved: bool
      quality_of_outcome: str

  root_cause_analysis:
    # Only if outcome != success
    primary_cause:
      node: str
      dimension: str
      explanation: str

    contributing_factors: []

  improvements:
    - # Full improvement specification as defined above

  executive_summary:
    outcome: str (1 line)
    key_findings: [] (3-5 bullets)
    top_improvements: [] (top 3 by priority)
    overall_assessment: str (2-3 sentences)
```

---

## Part 7: Implementation Architecture

### Component Overview

```
+------------------------------------------------------------------+
|                 WORKFLOW EVALUATION FRAMEWORK                     |
+------------------------------------------------------------------+
|                                                                   |
|  +-----------------------+     +---------------------------+      |
|  | Trace Extractor       |     | Evaluation Engine         |      |
|  |-----------------------|     |---------------------------|      |
|  | - fetch_trace()       |     | - evaluate_node()         |      |
|  | - build_minimal_tree()|---->| - assess_dimension()      |      |
|  | - extract_signals()   |     | - cross_cutting_analysis()|      |
|  +-----------------------+     +---------------------------+      |
|           |                              |                        |
|           v                              v                        |
|  +-----------------------+     +---------------------------+      |
|  | LangSmith Client      |     | Improvement Generator     |      |
|  | (existing)            |     |---------------------------|      |
|  |-----------------------|     | - identify_root_cause()   |      |
|  | - list_runs()         |     | - generate_improvement()  |      |
|  | - read_run()          |     | - prioritize()            |      |
|  +-----------------------+     +---------------------------+      |
|                                          |                        |
|                                          v                        |
|                                +---------------------------+      |
|                                | Report Generator          |      |
|                                |---------------------------|      |
|                                | - compile_report()        |      |
|                                | - format_output()         |      |
|                                +---------------------------+      |
|                                                                   |
+------------------------------------------------------------------+
```

### File Structure

```
tests/tools/
|-- trace_analysis.py       # Existing - trace fetching
|-- models.py               # Existing - base models
|
|-- evaluation/
    |-- __init__.py
    |-- extractor.py        # Minimal tree extraction
    |-- engine.py           # Evaluation logic
    |-- dimensions.py       # Dimension definitions
    |-- improvements.py     # Improvement generation
    |-- report.py           # Report compilation
    |-- models.py           # Evaluation-specific models
```

### Key Functions

```python
# extractor.py
def build_minimal_execution_tree(trace_id: str) -> MinimalExecutionTree:
    """Transform LangSmith trace into minimal evaluation tree."""

def extract_node_signals(run: Run) -> ExecutionNode:
    """Extract evaluation signals from a single run."""

# engine.py
def evaluate_trace(trace_id: str) -> EvaluationReport:
    """Full workflow evaluation - main entry point."""

def evaluate_node(node: ExecutionNode, context: EvaluationContext) -> NodeEvaluation:
    """Evaluate a single node across all dimensions."""

def assess_dimension(
    node: ExecutionNode,
    dimension: str,
    context: EvaluationContext
) -> DimensionAssessment:
    """Assess one dimension for one node."""

# improvements.py
def identify_improvements(
    evaluations: list[NodeEvaluation],
    cross_cutting: CrossCuttingAnalysis
) -> list[Improvement]:
    """Generate improvements from evaluation findings."""

def prioritize_improvements(improvements: list[Improvement]) -> list[Improvement]:
    """Sort improvements by priority."""
```

---

## Part 8: Usage Protocol for Evaluating Agents

### Step-by-Step Protocol

When an intelligent agent (Claude, GPT, etc.) wants to evaluate a workflow:

```markdown
## WORKFLOW EVALUATION PROTOCOL

### STEP 1: ACQUIRE TRACE
```python
tree = build_minimal_execution_tree(trace_id)
```

Print summary:
- Outcome: {tree.outcome}
- Nodes: {len(tree.nodes)}
- Cost: ${tree.total_cost}
- Latency: {tree.total_latency_ms}ms

### STEP 2: SEQUENTIAL NODE REVIEW

For each node in tree.nodes (sorted by sequence):

```
NODE {n}/{total}: {node.agent} ({node.type})
===========================================

CONTEXT ASSESSMENT:
- Received: {node.context_received}
- Utilized: {node.context_utilized}
- Ignored: {node.context_ignored}
- Assessment: [sufficient/insufficient/overloaded]

DECISION ANALYSIS:
- Decision: {node.decision_summary}
- Reasoning visible: {node.reasoning_visible}
- Reasoning: {node.reasoning_snippet}
- Assessment: [sound/flawed/missing]

TOOL USAGE (if applicable):
{for tool in node.tool_calls}
- {tool.name}({tool.args_summary}) -> {tool.result_summary}
- Assessment: [correct/incorrect args/wrong tool]

OUTPUT ASSESSMENT:
- Summary: {node.output_summary}
- Quality signals: {node.output_quality_signals}
- Assessment: [complete/incomplete/malformed]

DIMENSION SCORES:
- Reasoning: [critical/major/minor/ok]
- Decision: [critical/major/minor/ok]
- Tools: [critical/major/minor/ok]
- Context: [critical/major/minor/ok]
- Output: [critical/major/minor/ok]
- Compliance: [critical/major/minor/ok]

KEY FINDING: {one line summary}
```

### STEP 3: CROSS-CUTTING ANALYSIS

After all nodes reviewed:
- Context flow issues across nodes?
- Delegation efficiency (unnecessary hops)?
- Resource optimization opportunities?
- End-to-end outcome assessment

### STEP 4: ROOT CAUSE ANALYSIS (if failure)

Trace back from failure point:
1. Which node failed?
2. What dimension failed?
3. Why did that dimension fail?
4. What upstream factor caused it?

### STEP 5: GENERATE IMPROVEMENTS

For each major/critical finding:
1. Identify domain (prompt/tool/architecture/context)
2. Specify exact change needed
3. Provide current vs proposed
4. Explain rationale and expected impact

### STEP 6: COMPILE REPORT

Generate full evaluation report in standard format.
```

---

## Part 9: Quality Standards for Evaluations

### What Makes a Good Evaluation

| Criterion | Description |
|-----------|-------------|
| **Evidence-based** | Every finding cites specific trace data |
| **Dimensional** | Covers all 6 dimensions for each node |
| **Actionable** | Improvements are specific and implementable |
| **Prioritized** | Clear priority ordering of improvements |
| **Traceable** | Can follow logic from evidence to conclusion to fix |

### Anti-patterns to Avoid

| Anti-pattern | Problem | Better |
|--------------|---------|--------|
| Vague findings | "Reasoning was poor" | "Reasoning jumped from X to Z without explaining Y" |
| Opinion without evidence | "This decision was wrong" | "Decision was X, but given context Y, better would be Z" |
| Generic improvements | "Improve the prompt" | "Add explicit instruction to always include confidence score" |
| Missing root cause | "Output was wrong" | "Output wrong because context lost at step 3 when..." |

---

## Part 10: Integration Points

### With Autonomous Testing Framework

```python
# Execute scenario and immediately evaluate
result = execute_scenario(scenario)
evaluation = evaluate_trace(result.trace_id)

# Check for critical issues
critical_issues = [
    e for e in evaluation.node_evaluations
    if e.overall == "critical"
]

if critical_issues:
    # Auto-generate improvement PRs
    for improvement in evaluation.improvements:
        if improvement.priority == "CRITICAL":
            apply_improvement(improvement)
```

### With CI/CD Pipeline

```yaml
# In CI workflow
- name: Evaluate Recent Traces
  run: |
    python -m evaluation.cli evaluate-recent \
      --project autifyme-dev \
      --hours 24 \
      --output report.json

- name: Fail on Critical Issues
  run: |
    python -m evaluation.cli check-quality \
      --report report.json \
      --max-critical 0 \
      --max-major 5
```

### With LangSmith Datasets

```python
# Convert evaluated traces to dataset examples
for trace in evaluated_traces:
    if trace.outcome == "success" and trace.overall_quality == "ok":
        client.create_example(
            dataset_id=golden_dataset.id,
            inputs=trace.inputs,
            outputs=trace.outputs,
            metadata={"evaluation_score": trace.overall_score}
        )
```

---

## References

### LangSmith Documentation
- [Query Traces SDK](https://docs.langchain.com/langsmith/export-traces)
- [Run Data Format](https://docs.langchain.com/langsmith/run-data-format)
- [Evaluation Concepts](https://docs.langchain.com/langsmith/evaluation-concepts)
- [LangSmith Python Client](https://reference.langchain.com/python/langsmith/observability/sdk/client/)

### Internal Documentation
- [Autonomous Testing Framework](./AUTONOMOUS_TESTING_FRAMEWORK.md)
- [Hierarchical Trace Analysis](./HIERARCHICAL_TRACE_ANALYSIS.md)
- [Existing trace_analysis.py](../../../tests/tools/trace_analysis.py)

---

## Appendix: Example Evaluation

See separate document: `EVALUATION_EXAMPLE.md` (to be created with real trace evaluation)
