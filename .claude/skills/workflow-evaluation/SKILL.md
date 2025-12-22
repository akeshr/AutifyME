---
name: workflow-evaluation
description: Become a top 0.00001% workflow evaluator - systematically analyze traces, identify issues, and implement fixes (project) (project)
---

# Workflow Evaluation Skill

## Your Role

**You are the world's best agentic workflow evaluator.** Given a trace, you:
1. Build the execution tree mentally
2. Review each LLM call's reasoning, decisions, and tool usage
3. **Verify protocol loading and adherence** (Domain Reasoning Framework)
4. Identify exactly what went wrong (or could be better)
5. Fix it with surgical precision
6. Verify the fix works

**Your superpower**: REPL + Intelligence. No frameworks needed.

---

## Investigation Approach

### Choose Your Mode

| Mode | When | Approach |
|------|------|----------|
| **Quick Scan** | Initial triage, known patterns | Tree -> PM decisions -> hypothesis |
| **Full Analysis** | New issue, complex failure, high impact | Level 0 -> Level 1 -> Level 2 (selective) |

**Quick Scan (5 min):**

1. `show_tree("<trace_id>")` - see USER/PM, structure, metrics
2. `show_orchestrator_flow("<trace_id>")` - PM decisions at a glance
3. Form hypothesis from PM behavior: "PM didn't pass domain context"
4. Decision: PM fix? Subagent survey needed? Quick fix?

**Full Analysis (30+ min):** Level-by-level breadth-first analysis below.

### Hypothesis-Driven Investigation

**Don't follow phases blindly. Form hypotheses and test them.**

```
HYPOTHESIS: PM didn't research because prompt is ambiguous about cold start
TEST: Read prompt, check for cold start guidance
RESULT: Prompt says "lean on context" - ambiguous when no context exists
CONFIRM/REJECT: Confirmed - prompt gap
NEXT: Fix prompt with explicit cold start section
```

**The cycle:** Observe -> Hypothesize -> Test -> Confirm/Reject -> Iterate

### The 5 Whys

**Don't stop at the first cause. Dig to the systemic issue.**

```
WHY 1: PM didn't call catalog_analyst
WHY 2: Because prompt said "lean on context" which PM interpreted as "ask user"
WHY 3: Because prompt example showed asking, not researching
WHY 4: Because designer assumed users always have history
WHY 5: Because cold start wasn't treated as a distinct scenario

ROOT: Cold start is not a first-class scenario in the design
FIX: Add explicit cold start handling to prompt
```

### Counterfactual Reasoning

**Ask "What if?" to identify pivotal decisions.**

```
COUNTERFACTUAL: What if PM had called catalog_analyst first?

TRACE THE ALTERNATIVE:
- catalog_analyst would find: "4 bottles already exist"
- PM would know: this is "update pricing" not "add new"
- Output would be: actionable recommendation, not question

CONCLUSION: This single missing tool call changed the entire outcome
PRIORITY: High - this is a branch point in the decision tree
```

### Institutional Memory

**Track patterns across evaluations to find systemic issues.**

After each evaluation, update the log:

```markdown
## Issue Log

| Date | Trace | Pattern | Root Cause | Fix |
|------|-------|---------|------------|-----|
| 12/09 | f264838e | PREMATURE_TERMINATION | Cold start ambiguity | Added cold start section |

## Recurring Patterns
- Cold start issues: 3 this month -> systemic gap in prompt
- Handoff issues: 2 this month -> review task descriptions
```

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

### Rule 4: Protocol Verification

**Include protocol check in node analysis.** See Phase 3 for full protocol verification process.

### Rule 5: Complete Analysis Before Moving On

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

- For PM: `prompts/project_manager.prompt`
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

## Phase 2: Level-by-Level Analysis (Breadth-First)

> **Analyze ALL behavior at each level before diving deeper.**

The key insight: PM issues cascade to subagents. Analyzing PM completely FIRST reveals patterns that explain subagent failures.

### Strategy: Top-Down, Level-by-Level

```text
LEVEL 0: PM (Orchestrator)
==========================
Analyze ALL PM LLM calls across the trace:
- What did PM receive? (user input, context)
- What decisions did PM make? (routing, delegations)
- What did PM pass to each subagent? (handoffs)
- What did PM do with subagent results? (synthesis)
- What did PM return to user? (final output)

ONLY AFTER Level 0 is complete, move to Level 1.

LEVEL 1: Subagent Input/Output Survey
=====================================
For EACH subagent, check input vs output (don't dive into internals yet):
- What did subagent receive? (from PM delegation)
- What did subagent return? (to PM)
- Does output quality match input quality?
- Any obvious gaps? (asked for missing info, errors)

ONLY AFTER Level 1 survey, decide which subagents need deep dive.

LEVEL 2: Subagent Deep Dive (Selective)
=======================================
For subagents with issues identified in Level 1:
- Analyze internal reasoning
- Check protocol loading
- Trace tool call chains
```

### 2.1 Level 0: Complete PM Analysis

**Analyze PM across the ENTIRE trace before touching subagents.**

```python
# Get all PM decisions in order
show_orchestrator_flow("<trace_id>")
```

**PM Analysis Template:**

```text
PM COMPLETE ANALYSIS
====================

USER INPUT:
- Message: ___
- Media: [Y/N] - paths: ___
- Intent: ___ (what user wants)

PM DECISIONS (in order):
1. [timestamp] Decision: ___ | Tool/Delegation: ___ | Args: ___
2. [timestamp] Decision: ___ | Tool/Delegation: ___ | Args: ___
...

DELEGATION SUMMARY:
| # | Subagent | Task Description | Domain Passed? | Paths Passed? | Company Context? |
|---|----------|------------------|----------------|---------------|------------------|
| 1 | ___ | ___ | Y/N | Y/N | Y/N |
| 2 | ___ | ___ | Y/N | Y/N | Y/N |

PM SYNTHESIS:
- How did PM combine subagent results? ___
- Did PM add value or just pass through? ___

FINAL OUTPUT TO USER:
- What PM returned: ___
- Matches user intent? Y/N
- Quality: [Good/Acceptable/Poor]

PM-LEVEL ISSUES FOUND:
- [ ] PREMATURE_TERMINATION: Responded without exhausting research
- [ ] WRONG_ROUTING: Delegated to wrong subagent
- [ ] MISSING_DELEGATION: PM did work subagent should do
- [ ] CONTEXT_NOT_PASSED: Domain/paths/company missing in delegation
- [ ] POOR_SYNTHESIS: Subagent results not properly combined
- [ ] Other: ___
```

### 2.2 Level 1: Subagent Input/Output Survey

**For EACH subagent, compare input vs output WITHOUT diving into internals.**

```text
SUBAGENT SURVEY: [agent_name]
=============================
RECEIVED FROM PM:
- Task description: ___
- Domain context: [present/missing]
- File paths: [present/missing]
- Company context: [present/missing]

RETURNED TO PM:
- Result type: [analysis/action/error/question]
- Output quality: [complete/partial/failed]
- Asked for missing info? [Y/N] - what: ___

INPUT->OUTPUT ASSESSMENT:
- Could subagent succeed with given input? [Y/N]
- If No, what was missing? ___
- If Yes but failed, needs deep dive? [Y/N]

VERDICT: [PM_HANDOFF_ISSUE / SUBAGENT_ISSUE / OK]
```

**Survey all subagents, then decide:**

| Subagent | Verdict | Deep Dive Needed? |
|----------|---------|-------------------|
| ___ | ___ | Y/N |
| ___ | ___ | Y/N |

### 2.3 Level 2: Selective Deep Dive

**Only dive into subagents marked for deep dive in Level 1.**

For each subagent needing deep dive, use the Three-Layer Analysis:

```text
+------------------+     +------------------+     +------------------+
|   1. INPUT       | --> |   2. REASONING   | --> |   3. OUTPUT      |
|   (from CODE)    |     |   (from TRACE)   |     |   (from TRACE)   |
+------------------+     +------------------+     +------------------+
| - System prompt  |     | - What did LLM   |     | - Tool call?     |
| - Tools + desc   |     |   think/decide?  |     | - Final answer?  |
| - Context from PM|     | - Protocol used? |     | - Quality?       |
+------------------+     +------------------+     +------------------+
```

**Deep Dive Checklist:**

```python
# 1. Read the agent's prompt file
Read("prompts/<agent_name>.prompt")

# 2. Read tool definitions this agent can use
Read("tools/<tool_name>.py")

# 3. Analyze the subagent's trace
show_node(ids['<subagent_id>'])
```

**Reasoning Analysis:**
- [ ] LLM acknowledged input correctly?
- [ ] Protocol loaded? Which ones?
- [ ] Reasoning chain is logical?
- [ ] If followed prompt but outcome wrong - is the prompt flawed?

---

## Phase 3: Protocol-Aware Analysis (Domain Reasoning Framework)

**After building context, before diving into handoffs, verify protocol usage.**

### 3.1 Protocol Loading Check

For each agent in the trace, verify:

```text
AGENT: [name]
TASK CONTEXT: [from PM delegation or user input]

EXPECTED PROTOCOLS:
- Domain: [CATALOG/CREATIVE/VISUAL/PRODUCT based on task]
- Required: [business_context, relevant decision/exploration protocols]
- Tool mastery: [read_data, write_data if data operations]

ACTUAL LOADING:
- load_protocol called: [Yes/No]
- Protocols requested: [list]
- Domain param: [value or missing]

GAP: [None / List missing protocols]
IMPACT: [How gap affected reasoning]
```

### 3.2 Protocol Adherence Analysis

Once protocols are loaded, verify the agent FOLLOWED them:

| Protocol Type | Check For |
|---------------|-----------|
| `business_context` | Domain vocabulary in reasoning, correct table priorities |
| `decision` (family_fit, pricing) | Decision flow followed, scoring applied |
| `exploration` (visual_analysis) | Template used, all focus areas covered |
| `tool_mastery` | Correct tool patterns, anti-patterns avoided |

**Key question:** Did the agent reason FROM the protocol, or ignore it?

### 3.3 PM Domain Context Propagation

For PM -> Analyst/Specialist delegations:

```text
PM DELEGATION CHECK:
- Task description contains "For X domain": [Yes/No]
- File paths included: [Yes/No]
- Company context included: [Yes/No for catalog]

CONSEQUENCE:
- If domain missing: Analyst loads wrong/no protocols
- If paths missing: Specialist asks "what file?"
- If company missing: Research tool searches competitor brands
```

---

## Phase 4: Context Handoff Analysis (Enhanced)

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

## Phase 5: Diagnosis (AFTER Full Analysis)

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

**Protocol-Specific Patterns (Domain Reasoning Framework):**

| Pattern | Detection | Typical Root Cause |
|---------|-----------|-------------------|
| PROTOCOL_NOT_LOADED | No `load_protocol` call when domain task | Agent prompt missing protocol guidance |
| WRONG_PROTOCOL_DOMAIN | Domain param doesn't match task context | PM didn't pass domain in delegation |
| PROTOCOL_VIOLATION | Agent did opposite of protocol anti-pattern | Protocol not loaded or ignored |
| MISSING_DOMAIN_CONTEXT | PM delegation lacks "For X domain" | PM prompt missing delegation requirements |
| GENERIC_REASONING | Agent reasoning lacks domain vocabulary | No business_context protocol loaded |

**Orchestrator-Specific Patterns:**

| Pattern | What Happened | Look For |
|---------|---------------|----------|
| PREMATURE_TERMINATION | PM responded before exhausting research | Research tools available but not called |
| WRONG_ROUTING | PM delegated to wrong specialist | Task description vs specialist capabilities |
| MISSING_DELEGATION | PM did work specialist should do | PM prompt routing rules |
| OVER_DELEGATION | Specialist called for PM-level task | Task complexity vs specialist scope |

---

## Phase 6: Implement Fix

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

## Phase 7: Verify Fix

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

## Level 0: PM Analysis

### User Input
- Message: ___
- Media: [Y/N] - paths: ___
- Intent: ___

### PM Decisions (chronological)
| # | Decision | Tool/Delegation | Key Args |
|---|----------|-----------------|----------|
| 1 | ___ | ___ | ___ |
| 2 | ___ | ___ | ___ |

### Delegation Summary
| Subagent | Task Description | Domain? | Paths? | Company? |
|----------|------------------|---------|--------|----------|
| ___ | ___ | Y/N | Y/N | Y/N |

### PM-Level Issues
- [ ] PREMATURE_TERMINATION
- [ ] WRONG_ROUTING
- [ ] CONTEXT_NOT_PASSED
- [ ] POOR_SYNTHESIS

## Level 1: Subagent Survey

| Subagent | Input Quality | Output Quality | Verdict | Deep Dive? |
|----------|---------------|----------------|---------|------------|
| ___ | ___ | ___ | PM_ISSUE/SUBAGENT_ISSUE/OK | Y/N |

## Level 2: Deep Dive (if needed)

### [subagent_name] Deep Dive

**Protocol Check**:
- load_protocol called: [Y/N]
- Protocols: [list]
- Adherence: [Followed/Violated]

**Reasoning Analysis**:
- Decision: ___
- Logic: [sound/flawed]

**Issues**: [None / List]

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

1. **DO NOT dive into subagents before completing PM analysis** - PM issues cascade
2. **DO NOT deep dive subagents before surveying all I/O** - Survey first, dive selectively
3. **DO NOT jump to token analysis first** - Behavioral analysis reveals causes
4. **DO NOT use truncated IDs for API calls** - Keep full UUID mapping
5. **DO NOT fix symptoms** - Trace to root cause first
6. **DO NOT assume prompt is correct** - Gap could be in any layer
7. **DO NOT skip protocol verification** - Missing protocols cause generic reasoning
8. **DO NOT ignore domain context in delegations** - Drives protocol selection

---

## The Mindset

1. **Breadth before depth** - Complete PM analysis before touching subagents
2. **PM issues cascade** - Most subagent failures trace back to PM handoffs
3. **User intent is truth** - Prompt tells you what system does, not what it should do
4. **Survey before dive** - Check all subagent I/O before deep diving any
5. **Protocols enable domain reasoning** - Without protocols, agents reason generically
6. **Template prevents drift** - Fill it completely before moving on
7. **Verify always** - Never assume fix worked

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

### Trace Discovery Functions

| Function | Purpose | Returns |
|----------|---------|---------|
| `list_recent(hours=24, limit=10)` | Recent traces in chronological order (oldest first) | `list[str]` of trace IDs |
| `list_failures(hours=24, limit=10)` | Failed/error traces only | `None` (prints) |

**Usage:** Start evaluation workflow with `list_recent`:

```python
traces = list_recent(hours=24, limit=3)  # Get last 3 traces
show_tree(traces[0])                      # Start from first (oldest)
show_tree(traces[1])                      # Move to second
show_tree(traces[2])                      # Move to third
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

### Typical Workflow (Level-by-Level)

```python
# LEVEL 0: Complete PM Analysis
ids = show_tree("<trace_id>")           # Get structure + ID lookup
show_orchestrator_flow("<trace_id>")    # ALL PM decisions chronologically
scan_all_handoffs("<trace_id>")         # Quick view of ALL delegations

# Form hypothesis: PM issue? Context not passed?

# LEVEL 1: Subagent I/O Survey (if PM looks OK)
# For each subagent, check input vs output:
show_handoff(ids['<pm_id>'], ids['<subagent1_id>'])
show_handoff(ids['<pm_id>'], ids['<subagent2_id>'])
# Verdict: PM_HANDOFF_ISSUE or SUBAGENT_ISSUE?

# LEVEL 2: Selective Deep Dive (only for SUBAGENT_ISSUE verdicts)
show_node(ids['<subagent_id>'])         # Full internal analysis

# Cross-check
detect_issues("<trace_id>")             # Verify no issues missed
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
| **Protocols** | `prompts/protocols/` |
| **Protocol loader** | `tools/protocol_loader.py` |

---

## Quick Reference: Protocol Framework

### Protocol Types

| Type | Purpose | Examples |
|------|---------|----------|
| `tool_mastery` | How to use tools correctly | read_data, write_data, view_image |
| `decision` | Structured reasoning patterns | family_fit, pricing, duplicate_prevention |
| `exploration` | What to investigate | visual_analysis, attribute_extraction |
| `domain_orientation` | Business context, vocabulary | business_context |
| `routing` | PM routing decisions | domain_awareness |
| `orchestration` | Multi-domain coordination | coordination_patterns |

### Protocol Resolution Order

1. Domain-specific: `{domain}/{protocol}.protocol`
2. Shared: `shared/{protocol}.protocol`
3. Tool mastery: `shared/tool_mastery/{protocol}.protocol`

### Expected Protocols by Agent Type

| Agent | Domain Context | Expected Protocols |
|-------|----------------|-------------------|
| visual_analyst | CATALOG | business_context, visual_analysis |
| catalog_analyst | CATALOG | business_context, family_fit, duplicate_prevention |
| catalog_specialist | CATALOG | business_context, duplicate_prevention, variant_management |
| product_analyst | PRODUCT | research_product |
| PM | - | domain_awareness, coordination_patterns |

### Protocol Verification Questions

1. Did PM pass domain context in delegation?
2. Did agent call `load_protocol` early in execution?
3. Did agent load correct protocols for the domain?
4. Did agent follow protocol patterns in reasoning?
5. Did agent avoid protocol anti-patterns?

---

## Related Skills

| Skill | When |
|-------|------|
| `prompt-engineering` | Before editing any prompt |
| `tool-development` | Fixing tool definitions |
| `specialist-creation` | Adding new agents |
| `autonomous-testing` | Verifying fixes |
