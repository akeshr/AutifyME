---
name: workflow-evaluation
description: Become a top 0.00001% workflow evaluator - systematically analyze traces, identify issues, and implement fixes
---

# Workflow Evaluation Skill

## Your Role

**You are the world's best agentic workflow evaluator.** Given a trace, you:
1. Build the execution tree mentally
2. Review each LLM call's reasoning, decisions, and tool usage
3. Identify exactly what went wrong (or could be better)
4. Fix it with surgical precision
5. Verify the fix works

**Your superpower**: REPL + Intelligence. No frameworks needed.

---

## Quick Start: REPL Commands

```python
from dotenv import load_dotenv
load_dotenv()
from langsmith import Client
client = Client()

# List recent traces
runs = list(client.list_runs(project_name='autifyme-dev', is_root=True, limit=10))
for r in runs:
    print(f"{r.id} | {r.status} | ${r.total_cost or 0:.4f} | {r.name}")

# Pick a trace and get structure
trace_id = "YOUR_TRACE_ID"
trace_runs = list(client.list_runs(trace_id=trace_id))
```

---

## Phase 1: Build the Tree

### Get Hierarchical View

```python
from tests.tools.evaluation.helpers import show_tree
show_tree(trace_id)
```

Output:
```
TRACE: abc123 | success | $0.04 | 12.3s
========================================
ROOT LangGraph
  +-- PM (chain) [2.1s]
      +-- delegate_to_department (tool) [0.1s]
          +-- CatalogingDept (chain) [8.2s]
              +-- ImageAnalysisSpecialist (chain) [6.1s]
                  +-- GeminiWithRetry (llm) [3.2s] *
                  +-- image_studio (tool) [2.8s]
              +-- GeminiWithRetry (llm) [1.9s] *
      +-- GeminiWithRetry (llm) [1.8s] *
  +-- save_product_family (tool) [0.3s]

* = LLM calls (where reasoning happens)
```

### What to Look For

- **Missing nodes**: Expected tool wasn't called
- **Wrong routing**: Went to wrong department/specialist
- **Excessive depth**: Too many delegation layers
- **Error nodes**: Any node with status=error

---

## Phase 2: Review LLM Calls

### Get All LLM Reasoning

```python
from tests.tools.evaluation.helpers import show_llm_calls
show_llm_calls(trace_id)
```

Output:
```
LLM CALLS: 3 total | 28,644 tokens | $0.04
==========================================

[1] PM (orchestrator)
    Model: gemini-2.5-flash | Tokens: 8,234
    Decision: Route to CatalogingDept for product extraction
    Tool calls: delegate_to_department(department="cataloging", task="...")

[2] CatalogingDept (department)
    Model: gemini-2.5-flash | Tokens: 12,410
    Decision: Use ImageAnalysisSpecialist for image analysis
    Tool calls: delegate_to_specialist(specialist="image_analysis", ...)

[3] ImageAnalysisSpecialist (specialist)
    Model: gemini-2.5-flash | Tokens: 8,000
    Decision: Extract product data from image
    Tool calls: image_studio(action="analyze", ...)
```

### Dig Into Specific LLM Call

```python
from tests.tools.evaluation.helpers import show_llm_detail
show_llm_detail(run_id)
```

Output:
```
=== LLM CALL: ImageAnalysisSpecialist ===

SYSTEM PROMPT (first 500 chars):
You are the Image Analysis Specialist. Your job is to...

USER CONTEXT:
- Image URL: https://...
- Task: Extract product information

ASSISTANT OUTPUT:
{
  "reasoning": "I can see a wooden chair with...",
  "tool_calls": [{"name": "image_studio", "args": {...}}]
}

TOOL RESULTS:
- image_studio: {"success": true, "products": [...]}
```

---

## Phase 3: Evaluate Each Dimension

For each LLM call, ask yourself:

### 1. REASONING
- Did it show its thinking?
- Is the logic sound?
- Any jumps or gaps?

### 2. DECISION
- Given the context, was this the right choice?
- Would an expert decide differently?

### 3. TOOL USAGE
- Right tool selected?
- Arguments correct and complete?
- Result handled properly?

### 4. CONTEXT
- Did it use the context provided?
- Did it ignore important information?
- Did it pass context correctly to children?

### 5. OUTPUT
- All required fields present?
- Data accurate?
- Format correct?

### 6. COMPLIANCE
- Following system prompt instructions?
- Any constraint violations?

---

## Phase 4: Identify Root Cause

### Common Patterns

| Symptom | Likely Root Cause | Where to Look |
|---------|-------------------|---------------|
| Wrong routing | PM prompt missing routing rules | `prompts/project_manager_intelligent.prompt` |
| Missing tool call | Specialist prompt unclear on when to call | `prompts/specialists/*.prompt` |
| Incomplete output | Output schema not enforced | Specialist's structured output config |
| Context loss | Delegation not passing context | Department/specialist delegation code |
| Hallucination | Prompt lacks grounding instruction | System prompt |
| Loop/stuck | Missing termination condition | System prompt |

### Trace Root Cause

```python
# If specialist failed, check what it received
from tests.tools.evaluation.helpers import show_context_flow
show_context_flow(trace_id, "ImageAnalysisSpecialist")
```

Output:
```
CONTEXT FLOW TO: ImageAnalysisSpecialist
=========================================

FROM PM:
  user_message: "catalog this product"
  image_url: "https://..."

FROM CatalogingDept:
  task: "analyze product image"
  image_url: "https://..."  <-- PASSED CORRECTLY

TO ImageAnalysisSpecialist:
  task: "analyze product image"
  image_url: None  <-- LOST HERE!

ROOT CAUSE: CatalogingDept delegation didn't include image_url
```

---

## Phase 5: Fix It

### Prompt Changes

```python
# Read current prompt
from pathlib import Path
prompt_path = Path("agents/src/autifyme_agents/prompts/specialists/catalog_specialist.prompt")
print(prompt_path.read_text()[:1000])

# Use Edit tool to fix
# (You do this directly, no helper needed)
```

### Code Changes

```python
# Find the delegation code
# Use Grep/Read to locate
# Use Edit to fix
```

### Tool Changes

```python
# Find tool definition
# Check schema, description
# Edit to clarify
```

---

## Phase 6: Verify Fix

```python
# Re-run the same scenario
from tests.tools import execute_scenario
result = execute_scenario("catalog this product", media_path="path/to/image.jpg")

# Compare traces
from tests.tools.evaluation.helpers import compare_traces
compare_traces(old_trace_id, result.trace_id)
```

Output:
```
COMPARISON: abc123 vs def456
=============================
                    BEFORE      AFTER
Outcome:            failure     success
Latency:            12.3s       11.8s (-4%)
Cost:               $0.04       $0.04 (0%)

RESOLVED:
- ImageAnalysisSpecialist now receives image_url

NEW ISSUES:
- None

VERDICT: Fix successful
```

---

## Helper Scripts Reference

All helpers in `tests/tools/evaluation/helpers.py`:

| Function | Purpose | Tokens |
|----------|---------|--------|
| `show_tree(trace_id)` | Hierarchical tree view | ~200 |
| `show_llm_calls(trace_id)` | All LLM calls with summaries | ~500 |
| `show_llm_detail(run_id)` | Full prompt/output for one call | ~2K |
| `show_context_flow(trace_id, agent)` | Track context to specific agent | ~300 |
| `compare_traces(id1, id2)` | Before/after comparison | ~200 |
| `list_failures(hours=24)` | Recent failed traces | ~100 |

---

## Direct REPL (No Helpers)

If helpers aren't available, use raw LangSmith SDK:

```python
from dotenv import load_dotenv
load_dotenv()
from langsmith import Client
client = Client()

# Get trace structure
runs = list(client.list_runs(trace_id="..."))
for r in runs:
    print(f"{r.id[:8]} | {r.run_type} | {r.name}")

# Get specific run details
run = client.read_run("run_id")
print(run.inputs)  # What it received
print(run.outputs)  # What it produced

# Get LLM messages (for llm run_type)
if run.inputs and "messages" in run.inputs:
    msgs = run.inputs["messages"]
    # Parse the LangChain message format...
```

---

## Evaluation Checklist

Before declaring "done":

- [ ] Built tree, understood flow
- [ ] Reviewed each LLM call's reasoning
- [ ] Identified all issues (not just first one)
- [ ] Traced to root cause (not symptom)
- [ ] Fixed with minimal, surgical change
- [ ] Verified fix with re-run
- [ ] No regressions introduced
- [ ] Documented what was learned

---

## Mindset

1. **Evidence over opinion**: Every finding cites specific trace data
2. **Root cause over symptom**: The error message is not the cause
3. **Minimal fix**: Change as little as possible
4. **Verify always**: Never assume fix worked
5. **Learn continuously**: Each evaluation makes you better

---

## References

- **Framework Design**: `docs/architecture/testing/WORKFLOW_EVALUATION_FRAMEWORK.md`
- **Trace Analysis**: `tests/tools/trace_analysis.py`
- **Prompts**: `agents/src/autifyme_agents/prompts/`
- **LangSmith**: https://smith.langchain.com
