---
name: workflow-evaluation
description: Become a top 0.00001% workflow evaluator - systematically analyze traces, identify issues, and implement fixes (project)
---

# Workflow Evaluation Skill

## Your Role

**You are the world's best agentic workflow debugger.** You follow execution flow with surgical precision:

1. Start at the root node
2. For each LLM call: INPUT (from codebase) -> REASONING (from trace) -> OUTPUT (from trace)
3. **BEFORE recursing**: Verify context handoff quality
4. When output is a tool call, recursively analyze that tool's execution
5. Diagnose root cause (AFTER full trace analysis), implement fix, verify

**Your discipline**: Follow the execution flow. Never jump to symptoms. Never skip nodes.

---

## [CRITICAL] Anti-Drift Rules

These rules prevent common evaluation mistakes:

### Rule 1: NO Token/Cost Analysis Until Phase 4

Token counts and costs are SYMPTOMS, not causes. You may note them in the tree for reference, but:
- **DO NOT** investigate high token usage until you've completed node-by-node analysis
- **DO NOT** let token numbers guide your investigation order
- **DO** follow execution order (chronological/depth-first)

### Rule 2: Full UUIDs, Not Truncated

When building the tree:
- Display short IDs for readability: `[bf173a71]`
- But ALWAYS have full UUID accessible for API calls
- Tree helper should return: `{short_id: full_uuid}` mapping

### Rule 3: Context Handoff Checkpoint (MANDATORY)

**BEFORE recursing into any tool call**, you MUST complete the Context Handoff Checklist:

```
CONTEXT HANDOFF: [parent] -> [tool_name] -> [child]
----------------------------------------------------
What parent HAD available:
- [ ] Image path: ___
- [ ] User message: ___
- [ ] Company context: ___
- [ ] Previous findings: ___

What parent PASSED to tool:
- [ ] In args: ___
- [ ] In task description: ___
- [ ] Via workspace files: ___

What child RECEIVED:
- [ ] Matches what was passed? Y/N
- [ ] Missing anything critical? Y/N

HANDOFF QUALITY: [OK / PARTIAL / BROKEN]
```

**Only after completing this checklist, recurse into the child node.**

### Rule 4: Complete Analysis Before Moving On

For each node, you MUST fill out the analysis template BEFORE moving to the next node:

```
NODE: [id] [name]
================
INPUT (from codebase):
- Prompt file: ___ (key rules: ___)
- Tools available: ___
- Context received: ___

REASONING (from trace):
- LLM's decision: ___
- Logic sound? Y/N - Why: ___

OUTPUT (from trace):
- Action taken: ___
- Args passed: ___

ISSUES FOUND: [ ] None / [ ] List: ___

NEXT: [ ] Recurse to ___ / [ ] Return to parent / [ ] Done
```

---

## Phase 1: Build the Execution Tree

### Using Helper Functions

```python
from tests.tools.evaluation.helpers import show_tree, show_node, show_handoff, show_pm_flow

# Step 1: Get tree structure with full UUID lookup
ids = show_tree("3c3cfa58-8eb9-4f0e-a381-584ec5859d12")

# Step 2: See PM's decision flow
show_pm_flow("3c3cfa58-8eb9-4f0e-a381-584ec5859d12")

# Step 3: Analyze specific node (use FULL UUID from ids dict)
show_node(ids['44427c51'])

# Step 4: Check handoff before recursing
show_handoff(ids['e5c016a5'], ids['e0bdc7ae'])
```

### Tree Output Format

Tree shows **FULL UUIDs** for direct copy-paste into `show_node()` and `show_handoff()`:

```
TRACE: 3c3cfa58-8eb9-4f0e-a381-584ec5859d12
Status: success | Cost: $0.04 | Time: 45.2s | Tokens: 471,193
LLM calls: 12 | Tool calls: 8 | Total nodes: 150
================================================================================
[3c3cfa58-8eb9-4f0e-a381-584ec5859d12] LangGraph (chain) | 45.2s
  +-- [44427c51-9d91-4927-9911-d2b3c31301b5] GeminiWithRetry (llm) | 14,076tok -> download *
  +-- [e5c016a5-f179-42ca-b73b-571fe706b1d1] GeminiWithRetry (llm) | 14,439tok -> task *
      +-- [e0bdc7ae-xxxx-xxxx-xxxx-xxxxxxxxxxxx] task (tool) -> visual_analyst
          +-- [c3b8232c-xxxx-xxxx-xxxx-xxxxxxxxxxxx] LangGraph (chain) | 4,924tok
      +-- [8fb88c64-xxxx-xxxx-xxxx-xxxxxxxxxxxx] task (tool) -> product_analyst
  ...

Legend: * = LLM | X = Error | -> = delegates/calls
```

Copy any UUID directly: `show_node("44427c51-9d91-4927-9911-d2b3c31301b5")`

---

## Phase 2: Systematic Node Analysis

### The Three-Layer Analysis (PER NODE)

```
+------------------+     +------------------+     +------------------+
|   1. INPUT       | --> |   2. REASONING   | --> |   3. OUTPUT      |
|   (from CODE)    |     |   (from TRACE)   |     |   (from TRACE)   |
+------------------+     +------------------+     +------------------+
| - System prompt  |     | - What did LLM   |     | - Tool call?     |
| - Tools + desc   |     |   think/decide?  |     |   -> HANDOFF     |
| - User context   |     | - Is logic sound?|     |      CHECK then  |
| - Schema         |     | - Any gaps?      |     |      RECURSE     |
+------------------+     +------------------+     +------------------+
```

### Step 2.1: Reconstruct INPUT from Codebase

**DO NOT rely solely on trace for input.** Read the source files:

```python
# 1. Read the agent's prompt file
Read("agents/src/autifyme_agents/prompts/project_manager_intelligent.prompt")

# 2. Read tool definitions this agent can use
Read("agents/src/autifyme_agents/tools/task_tool.py")

# 3. Read the agent implementation (for tool bindings, schema)
Read("agents/src/autifyme_agents/workflows/project_manager.py")
```

**Input Checklist**:

| Component | Source | Status |
|-----------|--------|--------|
| System prompt | `prompts/*.prompt` | [ ] Read |
| Tool definitions | `tools/*.py` | [ ] Read |
| Output schema | Agent implementation | [ ] Read |
| User context | Trace inputs | [ ] Checked |

### Step 2.2: Analyze REASONING from Trace

Get what the LLM actually thought:

```python
run = client.read_run(id_map['bf173a71'])  # Use full UUID from map
# Parse run.outputs for the LLM's reasoning and decisions
```

**Reasoning Checklist**:
- [ ] LLM acknowledged input correctly?
- [ ] Reasoning chain is logical?
- [ ] No jumps or unfounded assumptions?
- [ ] Followed prompt instructions?

### Step 2.3: Analyze OUTPUT from Trace

**If OUTPUT is a TOOL CALL:**

1. **STOP** - Do not immediately recurse
2. **Complete Context Handoff Checklist** (see Rule 3)
3. **Only then** recurse into child node

**If OUTPUT is a FINAL ANSWER:**
- Validate correctness against expected outcome

---

## Phase 3: Context Handoff Analysis

### [CRITICAL] Before Every Recursion

When parent calls a tool/task, verify the handoff:

```
CONTEXT HANDOFF: PM -> task(visual_analyst)
============================================

WHAT PM HAD:
- Image path: inbox/whatsapp_.../image.jpg [from download tool]
- User message: [Media attachment: 1812452379380528]
- Company context: Pavisha, Professional brand voice
- Conversation history: 2 cancelled downloads, 1 successful

WHAT PM PASSED IN TASK ARGS:
- subagent_type: visual_analyst
- description: "Analyze the image to identify materials..."
- image_path: ??? <-- CHECK THIS

WHAT VISUAL_ANALYST RECEIVED:
- Did it get the image path? Y/N
- Did it get company context? Y/N
- Did it get any prior findings? N/A (first analyst)

HANDOFF QUALITY: [OK / PARTIAL / BROKEN]
ISSUE: [None / Describe what was lost]
```

### Common Handoff Issues

| Issue | Symptom | Where to Look |
|-------|---------|---------------|
| Image path not passed | Child can't see image | Task args in parent output |
| Company context lost | Generic responses | Task description or workspace |
| Prior findings not shared | Redundant work | Workspace protocol compliance |
| Wrong workspace path | File not found | Path in task description |

---

## Phase 4: Diagnosis (AFTER Full Analysis)

### Only Now Consider Metrics

After completing node-by-node analysis, you may examine:
- Token usage patterns
- Cost distribution
- Latency bottlenecks

But diagnosis should be based on **behavioral issues found during analysis**, not metrics.

### Issue Classification

| Issue Type | Root Cause Location |
|------------|---------------------|
| Wrong routing | PM prompt routing rules |
| Missing tool call | Specialist prompt OR tool description |
| Wrong tool args | Prompt examples OR schema definition |
| Context loss | **Handoff point** - task args or workspace |
| Incomplete output | Output schema OR prompt instructions |
| Hallucination | Prompt lacks grounding instructions |

### Root Cause Template

```
ISSUE: [What went wrong]
NODE: [Where it happened]
TRACE BACK:
1. OUTPUT showed: ___
2. REASONING was: ___
3. INPUT analysis reveals: ___

ROOT CAUSE: [One sentence - the actual source of the problem]
FIX LOCATION: [File:line]
```

---

## Phase 5: Implement Fix

### [CRITICAL] For Prompt Changes

```
skill: prompt-engineering
```

**Always invoke `prompt-engineering` skill before editing any prompt file.**

### Fix Template

```markdown
## Fix for: [Issue description]

**Root Cause**: [One sentence]
**Location**: [File path:line numbers]

**Change**:
- Before: [What it said]
- After: [What it should say]

**Rationale**: [Why this fixes the root cause]
```

---

## Phase 6: Verify Fix

```python
# Re-run scenario
from tests.tools import execute_scenario
result = execute_scenario("original user message", media_path="...")

# Compare
compare_traces(old_trace_id, result.trace_id)
```

**Verification Checklist**:
- [ ] Issue no longer reproduces
- [ ] Same scenario produces correct output
- [ ] No new issues introduced
- [ ] No regressions in other scenarios

---

## Complete Evaluation Template

**Use this template for every evaluation. Fill ALL sections.**

```markdown
# Trace Evaluation: [full_trace_id]

## Overview
- **Status**: [success/failure]
- **User Input**: [what user sent]
- **Expected Outcome**: [what should happen]
- **Actual Outcome**: [what happened]

## Execution Tree
[Paste tree with full UUIDs in lookup]

## Node-by-Node Analysis

### Node 1: [name] [full_uuid]

**INPUT** (from codebase):
- Prompt: [file] - Key rules: ___
- Tools: [list]
- Context received: ___

**REASONING** (from trace):
- Decision: ___
- Logic: [sound/flawed] - ___

**OUTPUT** (from trace):
- Action: ___
- Args: ___

**CONTEXT HANDOFF** (if tool call):
- Parent had: ___
- Parent passed: ___
- Child received: ___
- Handoff quality: [OK/PARTIAL/BROKEN]

**Issues**: [None / List]

### Node 2: [name] [full_uuid]
[Repeat structure]

## Diagnosis Summary

| Issue | Node | Root Cause | Fix Location |
|-------|------|------------|--------------|
| | | | |

## Fixes Applied
[Details per fix]

## Verification
- [ ] Re-ran scenario
- [ ] Issue resolved
- [ ] No regressions
```

---

## Anti-Patterns (DO NOT)

1. **DO NOT jump to token analysis first** - Follow execution flow, metrics come last
2. **DO NOT skip the handoff checklist** - Context loss is a common root cause
3. **DO NOT use truncated IDs for API calls** - Keep full UUID mapping
4. **DO NOT move to next node without completing template** - Prevents drift
5. **DO NOT fix symptoms** - Trace to root cause first
6. **DO NOT assume agent behavior** - Read the prompt file

---

## The Mindset

1. **Execution flow first** - Top to bottom, depth-first
2. **Code is truth** - Prompts define expected behavior
3. **Handoffs are fragile** - Always verify context passing
4. **Metrics are symptoms** - Behavioral analysis reveals causes
5. **Template prevents drift** - Fill it completely before moving on
6. **Verify always** - Never assume fix worked

---

## Helper Functions Reference

All helpers in `tests/tools/evaluation/helpers.py`:

```python
from tests.tools.evaluation.helpers import (
    show_tree,      # Phase 1: Build tree, get ID lookup
    show_pm_flow,   # Phase 1: PM decisions chronologically
    show_node,      # Phase 2: Full INPUT/REASONING/OUTPUT for one node
    show_handoff,   # Phase 3: Context handoff analysis
    show_llm_calls, # Summary of all LLM calls
    compare_traces, # Before/after comparison
    list_recent,    # Recent traces
    list_failures,  # Failed traces
)
```

| Function | Purpose | Returns |
|----------|---------|---------|
| `show_tree(trace_id)` | Hierarchical tree with tokens, decisions | `dict[short_id, full_uuid]` |
| `show_pm_flow(trace_id)` | PM decisions in order with tool calls | `list[dict]` |
| `show_node(run_id)` | Full analysis template for one node | `dict` with parsed data |
| `show_handoff(parent_id, child_id)` | Context handoff verification | `dict` with issues |
| `show_llm_calls(trace_id)` | All LLM calls summary | `None` (prints) |
| `compare_traces(id1, id2)` | Before/after metrics | `None` (prints) |

### Typical Workflow

```python
# 1. Build tree, get ID lookup
ids = show_tree("trace_id")

# 2. See PM's orchestration decisions
show_pm_flow("trace_id")

# 3. Analyze first PM LLM call
show_node(ids['44427c51'])

# 4. Before recursing into task, check handoff
show_handoff(ids['44427c51'], ids['e0bdc7ae'])

# 5. Then analyze child node
show_node(ids['e0bdc7ae'])
```

---

## Quick Reference: File Locations

| What | Where |
|------|-------|
| PM prompt | `prompts/project_manager_intelligent.prompt` |
| Specialist prompts | `prompts/specialists/*.prompt` |
| Tool definitions | `tools/*.py` |
| Agent implementations | `workflows/*.py`, `specialists/*.py` |
| Workspace protocol | `/workspace/findings/` |
| **Evaluation helpers** | `tests/tools/evaluation/helpers.py` |

---

## Related Skills

| Skill | When |
|-------|------|
| `prompt-engineering` | Before editing any prompt |
| `tool-development` | Fixing tool definitions |
| `specialist-creation` | Adding new specialists |
| `autonomous-testing` | Verifying fixes |
