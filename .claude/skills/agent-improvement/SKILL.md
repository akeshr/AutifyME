---
name: agent-improvement
description: Diagnose and fix underperforming agents using systematic analysis. Bridges the general-purpose LLM gap with canonical examples and domain grounding. (project) (project)
---

# Agent Improvement Skill

## The Core Insight

**LLMs are general-purpose. Your agents need domain-specific grounding.**

| LLMs Know | LLMs DON'T Know |
|-----------|-----------------|
| General reasoning, patterns | Your tool APIs and quirks |
| How to call functions | What "good output" looks like |
| Common data structures | Your business rules and schema semantics |

**Examples bridge this gap** - but they must be canonical (2-4 complex), not exhaustive.

---

## Diagnostic Table

**Before adding examples, diagnose the actual problem.**

| Symptom | Root Cause | Fix |
|---------|------------|-----|
| Agent doesn't know what to do | Unclear role/goal | Sharpen identity section |
| Agent picks wrong tool | Tool descriptions unclear | Better tool docstrings |
| Agent uses tool wrong | No usage patterns | Add tool mastery section |
| Agent misses edge cases | Missing domain rules | Add domain doctrine |
| Agent output format wrong | No format reference | Add 1-2 output examples |
| Agent reasons poorly | Too many responsibilities | Split by domain coherence |
| Need 6+ examples | Wrong agent boundaries | Decompose agent |

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
   [ ] Decision patterns shown
   [ ] Output format exemplified

5. WORKFLOW: Does agent know WHERE it fits?
   [ ] Relationship to other agents
   [ ] What it receives / returns

6. PROTOCOLS (Domain Reasoning Framework):
   [ ] Agent has load_protocol tool
   [ ] Agent knows WHEN to load protocols (task triggers)
   [ ] Agent knows WHICH protocols to load (by domain)
   [ ] Prompt guides protocol loading early in execution
   [ ] Domain context flows from PM delegations
```

---

## Fix Routing

| Gap Found | Fix | Invoke Skill |
|-----------|-----|--------------|
| Identity unclear | Sharpen role section | `prompt-engineering` |
| Tool usage wrong | Improve docstrings or add mastery section | `tool-development` or `prompt-engineering` |
| Domain rules missing | Add domain doctrine | `prompt-engineering` |
| Judgment unclear | Add 2-3 canonical examples | `prompt-engineering` |
| Agent scope wrong | Decompose by domain | `specialist-creation` |

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
| Add examples for every edge case | O(2^n) explosion | Add domain doctrine |
| Skip diagnosis, jump to examples | Treating symptoms | Gap Analysis first |
| Add 10 simple examples | Don't teach reasoning | 2-3 complex canonical |
| Copy examples from other agents | Different domains | Design for THIS agent |

---

## Quick Decision Tree

```text
Agent underperforming?
         |
    Gap Analysis
         |
    +----+----+----+----+----+
    |    |    |    |    |    |
  ID   Tool  Domain Judgment Workflow Protocol
  gap? gap?  gap?   gap?     gap?     gap?
    |    |    |      |        |        |
    v    v    v      v        v        v
  prompt- tool- prompt- prompt- specialist- See Protocol
  engineering development engineering engineering creation  Process above
```

### Protocol Reference

For protocol types, structure templates, and design guidance: invoke `prompt-engineering` skill.
For expected protocols by agent and verification: see `workflow-evaluation` skill.

---

## Related Skills

| Skill | When |
|-------|------|
| `workflow-evaluation` | Deep trace analysis before diagnosis |
| `prompt-engineering` | Fixing prompts and creating protocols |
| `specialist-creation` | Decomposing agents by domain |
