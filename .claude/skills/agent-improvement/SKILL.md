---
name: agent-improvement
description: Diagnose and fix underperforming agents using systematic analysis. Protocol-based decomposition, doctrine over examples, cognitive load management. (project) (project) (project)
---

# Agent Improvement Skill

## Quick Reference (Start Here)

**When to use this skill:**
- Agent behavior is inconsistent ("dream vs nightmare")
- Agent needs many examples to work
- Agent "forgets" rules sometimes
- Adding new capability requires touching everything

**Key decisions:**

| If You See | Do This |
|------------|---------|
| Prompt > 500 lines | Protocol-based decomposition |
| Tool prompt > 100 lines | Move doctrine to protocols |
| 6+ examples needed | Replace with doctrine |
| Multiple mental models | One protocol per model |
| Inconsistent behavior | Check cognitive load first |

**The fix pattern:**
```
Bloated Agent (1000+ lines) -> Lean Agent (~200 lines) + Domain Protocols (~300 lines each)
```

---

## The Core Insight

**LLMs are general-purpose. Your agents need domain-specific grounding.**

| LLMs Know | LLMs DON'T Know |
|-----------|-----------------|
| General reasoning, patterns | Your tool APIs and quirks |
| How to call functions | What "good output" looks like |
| Common data structures | Your business rules and schema semantics |

**Doctrine bridges this gap better than examples.** LLMs copy examples literally. Give them mental models to reason FROM instead.

---

## Doctrine Over Examples (Critical Principle)

**The Problem:** LLMs copy-paste examples rather than reasoning from them.

| Approach | LLM Behavior | Result |
|----------|--------------|--------|
| Examples | Copy structure literally | Rigid, breaks on novel cases |
| Doctrine | Reason from principles | Flexible, generalizes |

**Doctrine = Mental models + Decision frameworks + Quality reasoning**

```xml
<!-- BAD: Example to copy -->
<example>
When you see a glass jar, use lighting="backlight" and material="glass"
</example>

<!-- GOOD: Doctrine to reason FROM -->
<doctrine>
## Material Reasoning
Each material has physics. Honor it.

Glass: Invisible without light. Reveal depth through backlight and edge refraction.
Metal: Reflects everything. Control with large soft sources.

Don't memorize treatments. Ask: "What does light DO to this material?"
</doctrine>
```

**When to use examples (sparingly):**
- Output FORMAT demonstration (1-2 max)
- Tool SYNTAX demonstration (in tool_mastery protocols)
- Complex multi-step WORKFLOW illustration

**When to use doctrine:**
- Decision making (how to think about choices)
- Quality reasoning (what "good" looks like and why)
- Domain expertise (how an expert approaches problems)

---

## Diagnostic Table

**Before adding examples, diagnose the actual problem.**

| Symptom | Root Cause | Fix |
|---------|------------|-----|
| Agent doesn't know what to do | Unclear role/goal | Sharpen identity section |
| Agent picks wrong tool | Tool descriptions unclear | Better tool docstrings |
| Agent uses tool wrong | No usage patterns | Add tool mastery protocol |
| Agent misses edge cases | Missing domain rules | Add domain doctrine |
| Agent output format wrong | No format reference | Add 1-2 output examples |
| Agent reasons poorly | Too many responsibilities | Protocol-based decomposition |
| Need 6+ examples | Wrong agent boundaries | Protocol-based decomposition |
| **Inconsistent behavior** | **Cognitive overload (prompt bloat)** | **Lean prompt + protocols** |
| **"Dream vs nightmare"** | **Multiple mental models competing** | **One protocol per task type** |

### Cognitive Load Analysis (New)

**Prompt bloat causes inconsistent behavior.** Agent "sometimes remembers" rules because too much is in context.

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| Specialist prompt | < 300 lines | 300-500 lines | > 500 lines |
| Tool system prompt | < 50 lines | 50-100 lines | > 100 lines |
| Total guidance (prompt + protocols) | < 600 lines | 600-1000 lines | > 1000 lines per task |

**Diagnosis:**
```bash
# Check prompt sizes
wc -l prompts/specialists/*.prompt
wc -l prompts/protocols/**/*.protocol

# If specialist prompt > 500 lines -> DECOMPOSE via protocols
# If tool prompt > 100 lines -> Move domain doctrine to protocols
```

**Protocol-Related Issues (Domain Reasoning Framework):**

| Symptom | Root Cause | Fix |
|---------|------------|-----|
| Agent reasoning is generic | No protocols loaded | Add protocol loading guidance |
| Agent ignores domain patterns | Wrong protocols loaded | Fix domain context in delegation |
| Agent violates anti-patterns | Protocol not followed | Strengthen protocol adherence in prompt |
| Agent doesn't know tables/schema | Missing business_context | Load business_context protocol |
| Agent uses tool incorrectly for domain | Missing tool_mastery | Load domain-specific tool_mastery |

---

## Gap Analysis Checklist

```text
AGENT: [name]
=============

1. IDENTITY: Does agent know WHO it is?
   [ ] Role clearly defined (not "AI assistant")
   [ ] Domain expertise framed
   [ ] Quality standards as identity

2. TOOLS: Does agent know HOW to use tools?
   [ ] Tool purposes clear (WHY)
   [ ] Chaining patterns documented
   [ ] Exclusivity patterns ("ONLY way to X")

3. DOMAIN: Does agent know domain rules?
   [ ] Domain vocabulary present
   [ ] Business rules explicit
   [ ] Schema semantics explained

4. JUDGMENT: Does agent know what "good" looks like?
   [ ] Quality criteria defined
   [ ] Decision patterns shown (doctrine, not examples)
   [ ] Output format exemplified (1-2 examples max)

5. WORKFLOW: Does agent know WHERE it fits?
   [ ] Relationship to other agents
   [ ] What it receives / returns

6. PROTOCOLS (Domain Reasoning Framework):
   [ ] Agent has load_protocol tool
   [ ] Agent knows WHEN to load protocols (task triggers)
   [ ] Agent knows WHICH protocols to load (by domain)
   [ ] Prompt guides protocol loading early in execution
   [ ] Domain context flows from PM delegations

7. COGNITIVE LOAD (Critical for inconsistency):
   [ ] Specialist prompt < 300 lines
   [ ] Tool system prompt < 100 lines
   [ ] Total per task < 600 lines
   [ ] Only ONE mental model active per task type
   [ ] Doctrine-based, not example-heavy
```

---

## Fix Routing

| Gap Found | Fix | Invoke Skill |
|-----------|-----|--------------|
| Identity unclear | Sharpen role section | `prompt-engineering` |
| Tool usage wrong | Improve docstrings or add mastery section | `tool-development` or `prompt-engineering` |
| Domain rules missing | Add domain doctrine | `prompt-engineering` |
| Judgment unclear | Add 2-3 canonical examples | `prompt-engineering` |
| Agent scope wrong | Protocol-based decomposition | See below |
| Cognitive overload | Lean prompt + protocols | See below |

---

## Protocol-Based Decomposition (Preferred Over Agent Splitting)

**When agent handles multiple mental models, DON'T split into multiple agents. Use protocols.**

### Why Protocols > Multiple Agents

| Multiple Agents | Protocol-Based |
|-----------------|----------------|
| N agents to maintain | 1 lean agent + N protocols |
| PM routes to right agent | PM provides domain context, agent loads protocol |
| Duplicate tool configurations | Shared tool configuration |
| Agent proliferation | Protocol library |

### Architecture Pattern

```
BEFORE (bloated agent):
+---------------------------------------+
|     Specialist (1000+ lines)          |
|  [Domain A + Domain B + Domain C      |
|   ALL mental models in context]       |
+---------------------------------------+
         | cognitive overload
         v
    Inconsistent behavior

AFTER (lean agent + focused protocols):
+---------------------------------------+
|   Specialist (~200 lines)             |
|   [Identity + Operating Mode + Tools] |
+---------------------------------------+
         | load_protocol based on PM's domain
         v
+------------+ +------------+ +------------+
| domain_a   | | domain_b   | | domain_c   |
| .protocol  | | .protocol  | | .protocol  |
| (~300 ln)  | | (~300 ln)  | | (~300 ln)  |
+------------+ +------------+ +------------+
         | ONE focused mental model per task
         v
    Consistent behavior
```

### Implementation Steps

1. **Identify mental models** - What distinct ways of thinking does agent need?
2. **Create domain protocols** - One protocol per mental model with doctrine
3. **Lean the specialist prompt** - Keep only: identity, operating mode, tools, protocol loading
4. **Add protocol loading guidance** - Batched loading, triggers, conditional protocols
5. **Move domain expertise to protocols** - Tool prompts become execution-focused

### Lean Specialist Template (~200 lines)

```xml
<identity>
WHO you are (role, expertise, quality bar)
</identity>

<operating_mode>
HOW you work (stages, gates, critique)
</operating_mode>

<protocol_loading>
WHAT protocols to load WHEN (batched, by domain, conditional)
</protocol_loading>

<tools>
Tool purposes and critical sequences
</tools>

<output_format>
What to report to PM
</output_format>
```

### Domain Protocol Template (~300 lines)

```xml
<protocol name="domain_x" type="domain" domain="category">

## PURPOSE
What this protocol teaches (HOW TO THINK, not steps)

## MENTAL MODEL
How an expert thinks about this domain

## DOMAIN DOCTRINE
Principles to reason FROM (not examples to copy)
- Decision frameworks
- Quality reasoning
- Anti-patterns

## TOOL APPLICATION (This Domain)
Which specs/tools matter for THIS domain
Which don't apply

## SELF-CRITIQUE
Questions to ask before shipping

</protocol>
```

### Comprehensive Protocol Loading

Specialist prompt should guide loading ALL needed protocols:

```
BATCH 1: ALWAYS (on task start)
  input_validation, resource_efficiency

BATCH 2: DOMAIN (from PM context)
  domain_x.protocol (domain='category')

BATCH 3: TOOL MASTERY
  tool_a, tool_b (for tools you'll use)

BATCH 4: CONDITIONAL
  multi_item -> when trigger X
  write_data, inspect_schema -> when creating records
  domain_support -> when workflow needs it
  hitl -> on HITL feedback
```

**Protocol-Related Fixes:**

| Gap Found | Fix | Location |
|-----------|-----|----------|
| No protocol loading | Add load_protocol to agent tools | Agent implementation |
| Wrong protocols loaded | Fix PM delegation domain context | PM prompt |
| Protocol not followed | Add protocol adherence guidance to prompt | Agent prompt |
| Missing domain patterns | Create new protocol | `prompts/protocols/{domain}/` |
| Tool_mastery gap | Create/update tool_mastery protocol | `prompts/protocols/shared/tool_mastery/` |

---

## Process

```text
1. DIAGNOSE: Run Gap Analysis checklist (including Protocol section)
2. FIX: Route to appropriate skill (see tables above)
3. VERIFY: Re-run scenario, compare traces
```

For deep trace analysis, use `workflow-evaluation` skill first.

### Protocol-Specific Process

```text
1. CHECK TRACE: Did agent call load_protocol?
   |
   +-- No -> Add protocol loading to agent prompt/tools
   |
   +-- Yes -> Did agent load CORRECT protocols?
              |
              +-- No -> Fix PM delegation domain context
              |
              +-- Yes -> Did agent FOLLOW protocol patterns?
                         |
                         +-- No -> Strengthen adherence guidance in prompt
                         |
                         +-- Yes -> Protocol is working, issue is elsewhere
```

---

## Anti-Patterns

| Don't | Why | Instead |
|-------|-----|---------|
| Add examples for every edge case | O(2^n) explosion, LLMs copy literally | Add domain doctrine |
| Skip diagnosis, jump to examples | Treating symptoms | Gap Analysis first |
| Add 10 simple examples | Don't teach reasoning | Doctrine + 1-2 format examples |
| Copy examples from other agents | Different domains | Design for THIS agent |
| Hardcode domain doctrine in tool prompts | Can't version, duplicates protocols | Move to protocols, tool = execution only |
| Load ALL protocols for every task | Cognitive overload | Load domain-specific per task |
| Put multiple mental models in one prompt | Inconsistent behavior | One protocol per mental model |
| Make prompt "comprehensive" (1000+ lines) | Agent "forgets" rules | Lean prompt + focused protocols |

---

## Quick Decision Tree

```text
Agent underperforming?
         |
    Gap Analysis + Cognitive Load Check
         |
    +----+----+----+----+----+----+
    |    |    |    |    |    |    |
  ID   Tool  Domain Judgment Workflow Protocol Cognitive
  gap? gap?  gap?   gap?     gap?     gap?    overload?
    |    |    |      |        |        |         |
    v    v    v      v        v        v         v
  prompt- tool- prompt- prompt- specialist- See     Protocol-based
  engineering dev  engineering engineering creation Protocol decomposition
                                            Process
```

### Protocol Reference

For protocol types, structure templates, and design guidance: invoke `prompt-engineering` skill.
For expected protocols by agent and verification: see `workflow-evaluation` skill.

---

## Complete Refactoring Process (Cognitive Overload Fix)

When agent has prompt bloat / inconsistent behavior, follow this process:

### Phase 1: Analyze

```text
1. MEASURE cognitive load
   wc -l prompts/specialists/X.prompt  # > 500 lines? BLOATED
   grep -n "SYSTEM_PROMPT" tools/X/tool.py  # > 100 lines? MOVE TO PROTOCOLS

2. IDENTIFY mental models
   Ask: "What distinct ways of thinking does this agent need?"

   Mental model test questions:
   - Does task A require different reasoning than task B?
   - Would examples for A+B create combinatorial explosion?
   - Would a human expert specialize in one or all?

   List them: [model_a, model_b, model_c]

3. COUNT guidance sources
   - Prompt + protocols + tool prompts = total lines
   - If > 1000 lines hitting context per task -> DECOMPOSE

4. CHECK example count
   - More than 4-5 examples? -> Doctrine is missing, examples compensating
   - Examples for every edge case? -> Need domain doctrine instead
```

### Phase 2: Design

```text
1. DEFINE lean specialist structure (~200 lines)
   - Identity (WHO)
   - Operating mode (HOW)
   - Protocol loading guidance (WHAT/WHEN)
   - Tools (critical sequences)
   - Output format

2. DEFINE domain protocols (one per mental model)
   - Mental model section
   - Domain doctrine (reasoning principles)
   - Tool application for THIS domain
   - Anti-patterns
   - Self-critique questions

3. DEFINE protocol loading batches
   - ALWAYS: cross-cutting protocols
   - DOMAIN: from PM context
   - TOOL_MASTERY: for tools used
   - CONDITIONAL: triggered by task characteristics
```

### Phase 3: Implement

```text
1. ARCHIVE old files
   mv specialist.prompt specialist.prompt.legacy
   mv old.protocol old.protocol.legacy

2. CREATE domain protocols FIRST
   - One per mental model identified
   - ~300 lines each, doctrine-focused
   - Test protocol resolution

3. CREATE lean specialist prompt
   - ~200 lines
   - Reference protocols, don't duplicate
   - Comprehensive protocol loading guidance

4. REFACTOR tool prompts
   - Keep technical execution rules
   - Move domain expertise to protocols
   - Add references to domain protocols

5. VERIFY protocol resolution
   uv run python -c "
   from autifyme_agents.tools.protocol_loader import _resolve_protocol_path
   # Test each protocol resolves correctly
   for name, domain in [('protocol_name', 'domain'), ...]:
       path = _resolve_protocol_path(name, domain)
       print(f'{name}: {\"OK\" if path else \"MISSING\"}')"
```

### Phase 4: Verify

```text
1. LINE COUNT CHECK
   - Specialist: < 300 lines
   - Each protocol: < 400 lines
   - Tool prompt: < 100 lines

2. PROTOCOL RESOLUTION
   - All protocols resolve correctly
   - Domain parameter works

3. TRACE REVIEW (workflow-evaluation skill)
   - Agent loads correct protocols
   - Agent follows protocol doctrine
   - Behavior is consistent
```

### Real Example: creative_specialist Refactoring

```
BEFORE:
- creative_specialist.prompt: 1052 lines
- TOOL_SYSTEM_PROMPT: 140 lines
- product_photography.protocol: 529 lines
- social_media.protocol: 492 lines
- Total per task: 2000+ lines

AFTER:
- creative_specialist.prompt: 237 lines
- TOOL_SYSTEM_PROMPT: 35 lines
- catalog_visual.protocol: 296 lines (doctrine)
- lifestyle_visual.protocol: 333 lines (doctrine)
- social_content.protocol: 319 lines (doctrine)
- Total per task: ~570 lines (one domain protocol loaded)

RESULT:
- 77% reduction in specialist prompt
- 75% reduction in tool prompt
- Consistent behavior (one mental model per task)
- Doctrine-based reasoning (not example copying)
```

---

## Related Skills

| Skill | When |
|-------|------|
| `workflow-evaluation` | Deep trace analysis before diagnosis |
| `prompt-engineering` | Fixing prompts and creating protocols |
| `specialist-creation` | Creating new specialists (use protocol-based approach) |
