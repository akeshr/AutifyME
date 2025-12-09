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
- [ ] File/media paths: ___
- [ ] User message: ___
- [ ] Domain context: ___
- [ ] Previous findings: ___

What parent PASSED to tool:
- [ ] In args: ___
- [ ] In task description: ___
- [ ] Via shared files: ___

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

## Phase 1: Build Context

**First see the trace, then understand expected behavior.**

### 1.1 Build the Tree (Always First)

`show_tree("<trace_id>")` - Always start here.

The header immediately tells you:

- **USER/PM preview** - what this trace is about
- **Root trace** = PM (orchestrator)
- **Nested task** = Sub-agent (analyst or specialist)

### 1.2 Establish Expected Behavior (First Principles)

**Question:** "What SHOULD happen for this user input?"

**Sources (in order of authority):**

1. **User Intent** - What is the user actually trying to accomplish?
2. **Domain Knowledge** - What would an expert do in this situation?
3. **System Design** - What is this agent designed to do?

**Read the relevant files:**

- For PM: `prompts/project_manager_intelligent.prompt`
- For sub-agents: `prompts/<agent_name>.prompt`
- Tool definitions: `tools/<tool_name>.py`

**[CRITICAL] The prompt tells you what the system DOES - not what it SHOULD do.**

When comparing actual vs expected, the gap could be in ANY layer:

| If... | Then fix... |
|-------|-------------|
| Agent deviated from correct prompt | Agent reasoning or handoff |
| Agent followed prompt, outcome wrong | **Prompt itself** |
| Agent lacked tools to succeed | Tool availability/descriptions |
| Agent was wrong choice entirely | Architecture/routing |

### 1.3 Continue Building Context

1. `show_orchestrator_flow("<trace_id>")` - See decision sequence
2. `show_node(ids['<short_id>'])` - Drill into specific node
3. `show_handoff(parent_id, child_id)` - Check context passing before recursing

### 1.4 Thread Navigation (On-Demand)

During analysis, if you need adjacent traces:

- `prev_trace(trace_id)` - What happened before?
- `next_trace(trace_id)` - What happened after?

**When to check:**

- PM asked user for direction - check next trace for response
- Agent behavior seems correct - check if prior trace set wrong context
- User had to repeat themselves - compare consecutive traces

**Why on-demand:** Navigate based on what you discover, not upfront.

### Tree Output Format

```text
TRACE: <trace_id>
Status: success | Cost: $0.04 | Time: 45.2s | Tokens: 471,193
LLM calls: 12 | Tool calls: 8 | Total nodes: 150

USER: [Image] (no text)
PM: "I see four children's water bottles..."
================================================================================
[<full-uuid>] LangGraph (chain) | 45.2s
  +-- [<full-uuid>] ModelWithRetry (llm) | 14,076tok -> download_media *
  +-- [<full-uuid>] ModelWithRetry (llm) | 14,439tok -> task *
      +-- [<full-uuid>] task (tool) -> agent_a
          +-- [<full-uuid>] LangGraph (chain) | 4,924tok
      +-- [<full-uuid>] task (tool) -> agent_b
  ...

Legend: * = LLM | X = Error | -> = delegates/calls
```

Copy any UUID directly: `show_node("<full-uuid>")`

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
Read("prompts/<agent_name>.prompt")

# 2. Read tool definitions this agent can use
Read("tools/<tool_name>.py")

# 3. Read the agent implementation (for tool bindings, schema)
Read("workflows/<agent_name>.py")
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
run = client.read_run(id_map['<short_id>'])  # Use full UUID from map
# Parse run.outputs for the LLM's reasoning and decisions
```

**Reasoning Checklist**:

- [ ] LLM acknowledged input correctly?
- [ ] Reasoning chain is logical?
- [ ] No jumps or unfounded assumptions?
- [ ] If followed prompt but outcome wrong - is the prompt flawed?

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
CONTEXT HANDOFF: [Orchestrator] -> task([Child Agent])
======================================================

WHAT PARENT HAD:
- File path: <path from previous tool> [if applicable]
- User message: <original user input>
- Domain context: <company/user context>
- Prior results: <from earlier tool calls>

WHAT PARENT PASSED IN TASK ARGS:
- agent_type: <child_agent_name>
- description: "<task description>"
- file_path: ??? <-- CHECK THIS

WHAT CHILD RECEIVED:
- Did it get the file path? Y/N
- Did it get domain context? Y/N
- Did it get prior findings? Y/N

WHAT CHILD OUTPUT:
- Result/error message from the child
- Reveals consequence of broken handoff immediately

HANDOFF QUALITY: [OK / PARTIAL / BROKEN]
ISSUE: [None / Describe what was lost]
```

### Common Handoff Issues

| Issue | Symptom | Where to Look |
|-------|---------|---------------|
| File path not passed | Child can't access file | Task args in parent output |
| Domain context lost | Generic responses | Task description or shared state |
| Prior findings not shared | Redundant work | Shared workspace compliance |
| Wrong file path format | File not found | Path in task description |

---

## Phase 4: Diagnosis (AFTER Full Analysis)

### Only Now Consider Metrics

After completing node-by-node analysis, you may examine:
- Token usage patterns
- Cost distribution
- Latency bottlenecks

But diagnosis should be based on **behavioral issues found during analysis**, not metrics.

### Issue Classification (Multi-Layer)

**[CRITICAL] Don't assume the prompt is correct. Consider ALL layers:**

| Issue Type | Possible Root Causes (check all) |
|------------|----------------------------------|
| Wrong routing | Prompt routing rules, tool descriptions, agent capabilities |
| Missing tool call | Prompt instructions, tool availability, tool descriptions |
| Wrong tool args | Prompt examples, schema definition, handoff quality |
| Context loss | Handoff description, shared state design, parent reasoning |
| Wrong outcome | **Prompt logic itself**, tool behavior, architecture |
| Hallucination | Prompt grounding, context insufficiency, tool limitations |

**Diagnosis questions:**

1. What did the USER want? (ground truth)
2. What would an EXPERT do? (ideal behavior)
3. What did the SYSTEM do? (actual behavior)
4. WHERE is the gap? (could be any layer)

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

### Issue Pattern Reference

Use these patterns when diagnosing and describing issues:

| Pattern | Detection | Typical Root Cause |
|---------|-----------|-------------------|
| PREMATURE_TERMINATION | Orchestrator responded with research tools unused | Prompt ambiguity about "sufficient" research |
| WRONG_ROUTING | Task sent to wrong sub-agent | Tool descriptions unclear |
| CONTEXT_LOSS | Child missing info parent had | Handoff description incomplete |
| FORMAT_TEMPLATE_TRAP | Agent followed format literally without reasoning | Example showed format, not thinking process |
| HIGH_TOKENS | >50k tokens in single call | Unbounded context or loop |
| TOOL_LOOP | Same tool called 3+ times | Missing termination condition |

**Orchestrator-Specific Patterns:**

| Pattern | What Happened | Look For |
|---------|---------------|----------|
| PREMATURE_TERMINATION | PM responded before exhausting research | Research tools available but not called |
| WRONG_ROUTING | PM delegated to wrong specialist | Task description vs specialist capabilities |
| MISSING_DELEGATION | PM did work specialist should do | PM prompt routing rules |
| OVER_DELEGATION | Specialist called for PM-level task | Task complexity vs specialist scope |

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
- Child output: ___
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
6. **DO NOT assume prompt is correct** - Gap could be in any layer

---

## The Mindset

1. **Execution flow first** - Top to bottom, depth-first
2. **User intent is truth** - Prompt tells you what system does, not what it should do
3. **Handoffs are fragile** - Always verify context passing
4. **Metrics are symptoms** - Behavioral analysis reveals causes
5. **Template prevents drift** - Fill it completely before moving on
6. **Verify always** - Never assume fix worked

---

## Helper Functions Reference

All helpers in `tests/tools/evaluation/helpers.py`:

```python
from tests.tools.evaluation.helpers import (
    # Thread Navigation (on-demand)
    prev_trace,            # Get previous trace in session
    next_trace,            # Get next trace in session

    # Core Analysis (Phases 1-4)
    show_tree,             # Phase 1: Build tree, get ID lookup
    show_orchestrator_flow, # Phase 1: Orchestrator decisions chronologically
    show_node,             # Phase 2: Full INPUT/REASONING/OUTPUT for one node
    show_handoff,          # Phase 3: Context handoff analysis
    show_llm_calls,        # Summary of all LLM calls

    # Supplementary: Issue Detection
    detect_issues,         # Auto-detect errors, high tokens, loops, missing context
    scan_all_handoffs,     # List all task delegations with context markers

    # Utilities
    compare_traces,        # Before/after comparison (Phase 6)
    list_recent,           # Recent traces
    list_failures,         # Failed traces
)
```

### Thread Navigation Functions

| Function | Purpose | Returns |
|----------|---------|---------|
| `prev_trace(trace_id)` | Get previous trace in same session | `str` (trace ID) or `None` |
| `next_trace(trace_id)` | Get next trace in same session | `str` (trace ID) or `None` |

**Usage:** Navigate on-demand when analysis reveals you need context from adjacent traces.

### Core Analysis Functions

| Function | Purpose | Returns |
|----------|---------|---------|
| `show_tree(trace_id)` | Hierarchical tree with tokens, decisions | `dict[short_id, full_uuid]` |
| `show_orchestrator_flow(trace_id)` | Orchestrator decisions in order with tool calls | `list[dict]` |
| `show_node(run_id)` | Full analysis template for one node (no truncation on `description`) | `dict` with parsed data |
| `show_handoff(parent_id, child_id)` | Context handoff: HAD -> PASSED -> RECEIVED -> **OUTPUT** | `dict` with issues |
| `show_llm_calls(trace_id)` | All LLM calls summary | `None` (prints) |
| `compare_traces(id1, id2)` | Before/after metrics | `None` (prints) |

### Supplementary: Automated Issue Detection

Use these **after** systematic analysis to cross-check findings, or to quickly scan for obvious problems:

| Function | Purpose | Returns |
|----------|---------|---------|
| `detect_issues(trace_id)` | Auto-detect: ERROR, HIGH_TOKENS (>50k), TOOL_LOOP (3+ calls), MISSING_CONTEXT | `list[dict]` with severity |
| `scan_all_handoffs(trace_id)` | List all task delegations showing `[OK]`/`[X]` status and `[+file]` marker | `list[dict]` of issues only |

**`scan_all_handoffs` output**:
- `[OK] agent_name` - Delegation looks healthy
- `[OK] agent_name [+file]` - File path was passed in description
- `[X] agent_name` - Child asked for missing context (HIGH severity)

**Note**: `show_handoff` is optimized for orchestrator -> task delegations. For agent LLM -> tool handoffs, "WHAT PARENT PASSED" may be empty but "WHAT CHILD RECEIVED" will show correct data.

### Typical Workflow

```python
# 1. Build tree, get ID lookup
ids = show_tree("<trace_id>")

# 2. See orchestrator's decisions
show_orchestrator_flow("<trace_id>")

# 3. Analyze first orchestrator LLM call
show_node(ids['<short_id>'])

# 4. Before recursing into task, check handoff
show_handoff(ids['<parent_id>'], ids['<child_id>'])

# 5. Then analyze child node
show_node(ids['<child_id>'])

# 6. (Optional) Cross-check with automated detection
detect_issues("<trace_id>")       # Verify no issues missed
scan_all_handoffs("<trace_id>")   # Overview of all delegations
```

---

## Quick Reference: File Locations

| What | Where |
|------|-------|
| Orchestrator prompt | `prompts/<orchestrator>.prompt` |
| Agent prompts | `prompts/<agents>/*.prompt` |
| Tool definitions | `tools/*.py` |
| Agent implementations | `workflows/*.py`, `agents/*.py` |
| Shared state/workspace | Application-specific |
| **Evaluation helpers** | `tests/tools/evaluation/helpers.py` |

---

## Related Skills

| Skill | When |
|-------|------|
| `prompt-engineering` | Before editing any prompt |
| `tool-development` | Fixing tool definitions |
| `specialist-creation` | Adding new agents |
| `autonomous-testing` | Verifying fixes |
