---
name: trace-scoring
description: Score PM workflow traces against expected behavior. Returns structured evaluations with scores for protocol loading, tool usage, delegation, and synthesis quality.
---

# Trace Scoring Skill

## Your Role

**You are a workflow scoring judge.** Your ONLY job is to:
1. Understand what SHOULD happen (read prompts/protocols)
2. See what ACTUALLY happened (fetch trace data)
3. Score each criterion objectively
4. Return structured scores with reasoning

**You do NOT fix issues.** You only score and explain gaps.

---

## Before Scoring ANY Trace

### Step 1: Load Expected Behavior (Once Per Session)

Read these files to understand what PM should do:

```python
# PM's core instructions
Read("agents/src/autifyme_agents/prompts/project_manager.prompt")

# Key PM protocols
Read("agents/src/autifyme_agents/prompts/protocols/pm/discovery_mindset.protocol")
Read("agents/src/autifyme_agents/prompts/protocols/pm/synthesis.protocol")
Read("agents/src/autifyme_agents/prompts/protocols/pm/execution_flows.protocol")
```

**After reading, you know:**
- What PM is instructed to do
- What protocols PM should load
- What delegation patterns are expected
- What synthesis behavior is correct

---

## Scoring Process

### Step 2: Analyze User Input

From the trace, determine:

| Question | How to Check |
|----------|--------------|
| What did user ask? | First message in trace inputs |
| Was there an image? | Check for `[media_id:` or image paths |
| Is this a query or action? | Query = "what/show/list", Action = "add/create/catalog" |

### Step 3: Determine Expected Behavior

Based on input type:

| Input Type | Expected PM Behavior |
|------------|---------------------|
| **Image + Action** | Protocol first → visual_analyst (Wave 1) → other analysts (Wave 2) → Approval gate with open question |
| **Image + Query** | Protocol first → visual_analyst → Direct answer |
| **Text + Action** | Protocol first → catalog_analyst → Approval gate |
| **Text + Query** | Protocol first → catalog_analyst → Direct answer |

### Step 4: Fetch Actual Behavior

```python
from tests.tools import (
    get_protocol_loads,
    get_delegation_graph,
    get_tool_call_sequence,
    get_agent_final_message,
)

trace_id = "<the trace id>"

protocols = get_protocol_loads(trace_id)
graph = get_delegation_graph(trace_id)
seq = get_tool_call_sequence(trace_id)
final_msg = get_agent_final_message(trace_id, "PM")
```

### Step 5: Score Each Criterion

---

## Scoring Criteria

### 1. Protocol Loading (0-1)

| Check | Score |
|-------|-------|
| PM loaded protocol as FIRST action | +0.5 |
| PM loaded correct protocol (discovery_mindset for analysis) | +0.3 |
| All subagents loaded their protocols first | +0.2 |

**Data to check:**
```python
protocols.pm_first_action_was_protocol  # True/False
protocols.pm_protocol                    # "discovery_mindset"
protocols.agent_protocols                # {"PM": "...", "visual_analyst": "..."}
```

---

### 2. Tool Usage (0-1)

| Check | Score |
|-------|-------|
| Used critical tools (load_protocol, task) | +0.4 |
| No tool errors | +0.3 |
| No redundant consecutive tool calls | +0.2 |
| First tool was load_protocol | +0.1 |

**Data to check:**
```python
seq.total_tool_calls                     # Count
seq.first_tool_call.tool_name            # Should be "load_protocol"
[tc for tc in seq.tool_calls if tc.status == "error"]  # Errors
```

---

### 3. Delegation (0-1)

| Check | Score Impact |
|-------|--------------|
| Delegated to appropriate agents for input type | +0.4 |
| Correct wave structure (visual first if image) | +0.3 |
| Context passed to each delegation | +0.2 |
| Correct order (analysts before specialists) | +0.1 |

**Data to check:**
```python
graph.agents_involved                    # ["visual_analyst", "catalog_analyst"]
graph.waves                              # {1: ["visual_analyst"], 2: ["catalog_analyst"]}
graph.delegation_order                   # Order of delegations
[d.context_passed for d in graph.delegations]  # Context in each
```

**Expected agents by input:**

| Input | Expected Agents |
|-------|-----------------|
| Image present | visual_analyst (Wave 1), then others |
| No image, catalog task | catalog_analyst |
| Market research needed | product_analyst |
| Execution phase | creative_specialist, catalog_specialist |

---

### 4. Synthesis Quality (0-1)

| Check | Score |
|-------|-------|
| Final message has substance (>50 chars) | +0.2 |
| Asks open-ended question (not numbered options) | +0.3 |
| Mentions product/context details | +0.2 |
| Has structure (paragraphs, headers) | +0.1 |
| Asks for user direction | +0.2 |

**Data to check:**
```python
final_msg.message                        # The actual message
final_msg.has_open_question              # True/False
final_msg.has_numbered_options           # True/False (anti-pattern!)
```

**Anti-patterns (reduce score):**
- Numbered options like "1. Create 2. Skip 3. Edit" → -0.3
- No question at all → -0.2
- Message too short (<50 chars) → -0.2

---

## Output Format

**Always return this exact structure:**

```json
{
  "trace_id": "<trace_id>",
  "input_analysis": {
    "user_message": "<first 100 chars>",
    "has_image": true,
    "input_type": "image_action",
    "expected_behavior": "Protocol -> visual_analyst -> analysts -> approval gate"
  },
  "scores": {
    "protocol_loading": {
      "score": 0.8,
      "max": 1.0,
      "details": {
        "pm_first_action_protocol": true,
        "correct_protocol": true,
        "all_agents_compliant": false
      },
      "reason": "PM loaded discovery_mindset first. catalog_analyst did not load protocol first."
    },
    "tool_usage": {
      "score": 0.9,
      "max": 1.0,
      "details": {
        "critical_tools_used": ["load_protocol", "task", "view_image"],
        "error_count": 0,
        "redundant_calls": 0
      },
      "reason": "All critical tools used, no errors."
    },
    "delegation": {
      "score": 0.7,
      "max": 1.0,
      "details": {
        "agents_involved": ["visual_analyst", "catalog_analyst"],
        "wave_structure": {"1": ["visual_analyst"], "2": ["catalog_analyst"]},
        "context_passed": true
      },
      "reason": "Correct agents but product_analyst was expected for market research."
    },
    "synthesis": {
      "score": 0.5,
      "max": 1.0,
      "details": {
        "has_substance": true,
        "has_open_question": false,
        "has_numbered_options": true,
        "asks_direction": true
      },
      "reason": "Used numbered options instead of open-ended question - violates synthesis protocol."
    }
  },
  "overall_score": 0.725,
  "critical_issues": [
    "Synthesis uses numbered options (anti-pattern)",
    "catalog_analyst did not load protocol first"
  ],
  "summary": "PM followed correct delegation pattern but synthesis quality needs improvement. The numbered options pattern violates the open-ended question requirement in synthesis protocol."
}
```

---

## Quick Reference: What Good Looks Like

### Perfect Protocol Loading (1.0)
```
PM: load_protocol (discovery_mindset) ← FIRST action
visual_analyst: load_protocol (visual_analysis) ← FIRST action
catalog_analyst: load_protocol (business_context) ← FIRST action
```

### Perfect Delegation for Image+Action (1.0)
```
Wave 1: visual_analyst (image must be analyzed first)
Wave 2: catalog_analyst + product_analyst (can run parallel)
Wave 3: [execution phase if approved]
```

### Perfect Synthesis (1.0)
```
"Based on my analysis, this appears to be a set of stackable storage jars
in the 'Kitchen Storage' family. The visual analysis identified 3 variants
with floral patterns.

What would you like me to do with these products?"
                     ↑ Open-ended question, no numbered options
```

### Bad Synthesis (0.3)
```
"I found some jars. What would you like to do?
1. Create products
2. Skip
3. Edit details"
  ↑ Numbered options = anti-pattern
```

---

## Recording Results

After scoring, record to LangSmith:

```python
from tests.tools import record_evaluation, EvaluationResult, EvaluationCriterion
from datetime import datetime

result = EvaluationResult(
    scenario_id=scenario_id,
    trace_id=trace_id,
    thread_id=thread_id,
    status="PASS" if overall_score >= 0.7 else "FAIL",
    overall_score=overall_score,
    criteria_results=[
        EvaluationCriterion(criterion="protocol_loading", passed=score>=0.7, score=score, reasoning="..."),
        # ... other criteria
    ],
    passed_criteria=count_passed,
    failed_criteria=count_failed,
    evaluated_at=datetime.now()
)

record_evaluation(trace_id, scenario_id, result)
```

---

## Checklist Before Returning Scores

- [ ] Read PM prompt and key protocols (if not already in session)
- [ ] Analyzed user input type (image? query? action?)
- [ ] Determined expected behavior for this input type
- [ ] Fetched all trace data (protocols, delegations, tools, final message)
- [ ] Scored all 4 criteria with specific reasons
- [ ] Identified critical issues
- [ ] Returned structured JSON output

---

## Related Skills

| Skill | When to Use |
|-------|-------------|
| `workflow-evaluation` | Deep investigation and fixing (AFTER scoring identifies issues) |
| `agent-improvement` | Fixing identified issues |
| `prompt-engineering` | Updating prompts based on findings |
