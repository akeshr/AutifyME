---
name: prompt-engineering
description: Design world-class prompts using domain expert voice, professional vocabulary, and versatility through principles. Frame agents as top 0.01% practitioners, not AI assistants. (project) (project)
---

# Prompt Engineering Standards

## The Prime Directive

> **Make the LLM WANT to do what you need.**

Don't fight the model. Don't constrain it. Don't micromanage it.

Instead: Give it an identity worth inhabiting, expertise worth wielding, and standards worth upholding. A prompt that makes the LLM feel like a world-class expert will produce world-class work.

**The shift:** From "instructions for an AI" to "mindset for an expert."

### Ruthless Conciseness

> **Every token must earn its place.**

| Bloat | Earned |
|-------|--------|
| "Please remember to..." | (delete - LLMs don't forget) |
| "It's important that..." | (delete - everything is important) |
| 10 simple examples | 2-3 complex examples |
| Lists of don'ts | One "NEVER" for proven confusions |

**The test:** For every line, ask: "If I remove this, does behavior degrade?" If no, delete it.

### Senior Partner, Not Junior Assistant

> **Agents research, analyze, and recommend. They don't ask - they propose.**

| Junior Assistant | Senior Partner |
|------------------|----------------|
| "What price should I use?" | "Similar products are Rs 20-35. I recommend Rs 28. Options: 1) Rs 28, 2) Rs 32, 3) Specify" |
| Blocks on ambiguity | Resolves with analysis |
| Waits for instructions | Comes with recommendations |

**Non-negotiable:** An agent that asks "what do you want?" when it could research is failing.

---

## The Core Insight: Domain Expert Voice

**Don't write for "an AI assistant." Write for the world's best practitioner.**

| Generic AI | Domain Expert |
|------------|---------------|
| "You are an image editing assistant" | "You've shot for Apple, Dyson, Rolex" |
| "Adjust the lighting professionally" | "Key/fill ratio 3:1, rim light for separation" |
| "Check quality before returning" | "Portfolio Test: Would this make your portfolio?" |

### Five Elements of Domain Mastery

**1. Professional Credentials** - Real-world expertise framing
```
You've shot campaigns for luxury brands. Your work appears in Vogue and museum catalogs.
```

**2. Domain Vocabulary** - Actual language experts use
```
BAD: "Make the glass look realistic"
GOOD: "Glass: Internal caustics, edge refraction, transparency depth"
```

**3. Domain Doctrine** - Knowledge to reason FROM
```
MATERIAL TRUTH:
- Glass: Internal caustics, edge refraction, transparency depth
- Metal: Gradient reflections, micro-texture, controlled specularity
- Fabric: Weave texture, drape shadows, fiber detail
```

**4. Quality as Identity** - Excellence is WHO they are
```
BAD: "Verify output meets quality standards"
GOOD: "Every image must be immediately publishable. This is the final frame."
```

**5. Versatility Through Principles** - Enable infinite scenarios
```
BAD: "For hero shots, use white background"
GOOD: "Light reveals form and material truth. Background serves the story."
```

---

## The Right Altitude

| Too Low | Right | Too High |
|---------|-------|----------|
| Python code snippets | Decision principles + examples | "Handle media appropriately" |
| Step-by-step procedures | Reasoning frameworks | Generic platitudes |

### Agent Hierarchy

| Agent | Altitude | Focus |
|-------|----------|-------|
| PM (Orchestrator) | High | Routes to specialists, synthesizes results |
| Analysts | Medium-High | Research, workspace findings |
| Specialists | Medium | Domain execution, HITL operations |

**Orchestrators:** Minimal direct tools, rich subagent descriptions, reasoning framework
**Executors:** Deep domain expertise, tool mastery, workspace/HITL awareness

---

## Tool Mastery: The Warrior's Weapons

> **An agent is only as good as its knowledge of its tools.**

### Three Levels

| Level | Behavior |
|-------|----------|
| Novice | Calls tool when told |
| Competent | Correct parameters |
| **Master** | Strategic selection, chaining, error recovery |

**Goal:** Create Masters.

### Four Elements

**1. Purpose (WHY)**
```
Not: "Downloads media"
But: "Gets source material into workspace - first step before creative work"
```

**2. Exclusivity (WHEN only choice)**
```
"**This is the ONLY way to see images** - not ls, not cat, not filesystem"
```

**3. Strategic Context (WHERE in workflow)**
```
"Use AFTER download_media to diagnose"
"Use AFTER image_studio to verify"
```

**4. Chaining Patterns (HOW together)**
```
download_media -> view_image (diagnose) -> image_studio -> view_image (verify) -> write_data
```

### Verification Loop

Every action tool needs verification:
```
ACTION -> VERIFY -> (iterate if needed) -> PERSIST
```

---

## Protocol Design (Domain Reasoning Framework)

> **Protocols are dynamically-loaded domain expertise. Prompts are static identity.**

### Prompts vs Protocols: The Boundary

| Put in PROMPT | Put in PROTOCOL |
|---------------|-----------------|
| Agent identity ("You are...") | Domain-specific reasoning patterns |
| Core capabilities and tools | Tool mastery patterns for specific domain |
| Process framework (DIAGNOSE -> EXECUTE) | Decision flows (family_fit scoring) |
| Quality standards as identity | Anti-patterns for specific scenarios |
| 2-4 canonical examples | Domain vocabulary and tables |

**The key insight:** Prompts define WHO the agent is. Protocols define HOW to reason in specific domains.

### Protocol Types

| Type | Purpose | When Agent Loads |
|------|---------|------------------|
| `tool_mastery` | How to use tools correctly | Before data operations |
| `decision` | Structured reasoning patterns | Before making domain decisions |
| `exploration` | What to investigate | Before analysis tasks |
| `domain_orientation` | Business context, vocabulary | At start of domain work |
| `routing` | PM routing decisions | PM system prompt (static) |
| `orchestration` | Multi-domain coordination | PM system prompt (static) |

### Protocol Structure Template

```xml
<protocol name="protocol_name" type="decision|exploration|tool_mastery" domain="catalog|pm|shared">

## PURPOSE

One sentence: what decision/task this protocol guides.

---

## CORE PRINCIPLE

The fundamental insight that drives all patterns below.

---

## DECISION FLOW / ANALYSIS FOCUS / TOOL PATTERNS

[Type-specific content]

For decision protocols:
- Scoring criteria
- Decision tree
- Threshold definitions

For exploration protocols:
- Focus areas with tables
- Analysis template
- Output structure

For tool_mastery protocols:
- Correct patterns with examples
- Parameter guidance
- Chaining patterns

---

## ANTI-PATTERNS

### Wrong: [Description]

WRONG: [Bad pattern]
RIGHT: [Correct pattern]

---

## OUTPUT STRUCTURE (if applicable)

[JSON/markdown template for structured output]

</protocol>
```

### Protocol Design Principles

1. **Authoritative instruction** - Protocols are not suggestions, they're expert guidance
2. **Patterns over procedures** - Show reasoning patterns, not step-by-step recipes
3. **Anti-patterns are critical** - Show what NOT to do (from real failures)
4. **Tables for quick reference** - Decision matrices, scoring criteria, mappings
5. **Domain vocabulary** - Use actual terms experts use

### When to Create a New Protocol

| Signal | Action |
|--------|--------|
| Agent makes same mistake repeatedly | Create decision protocol with anti-pattern |
| Tool usage patterns are domain-specific | Create tool_mastery protocol |
| Analysis misses key focus areas | Create exploration protocol |
| Agent lacks domain vocabulary | Create business_context protocol |
| PM routes incorrectly | Update domain_awareness protocol |

### Protocol vs Prompt Decision Tree

```text
Need to add guidance?
        |
        v
Is it about WHO the agent is?
        |
    Yes -> Add to PROMPT (identity, capabilities, quality)
        |
    No  -> Is it domain-specific reasoning?
                |
            Yes -> Create/update PROTOCOL
                |
            No  -> Is it a proven confusion?
                        |
                    Yes -> Add "NEVER" to PROMPT
                        |
                    No  -> Probably don't need it
```

---

## Examples: The Teaching Mechanism

> **Complex examples teach simple scenarios. Simple examples do NOT teach complex.**

### Requirements for 2-4 Examples

- Force multi-step reasoning
- Include edge cases and ambiguity
- Show full cycle: **Analyze -> Research -> Decide -> Execute -> Review**
- Handle ambiguity with **suggestions**, not questions
- Show COMPLETE tool calls with ALL parameters

### Example Count as Design Signal

| Symptom | Diagnosis |
|---------|-----------|
| Need 6+ examples | Agent too broad - split by domain |
| Need A+B, A+C combinations | Domain coherence problem |
| Examples feel repetitive | Good sign - keep together |

### Quality Comparison

**WEAK:**
```xml
<example>
  <input>"Update X to Y"</input>
  <action>write_data(update)</action>
</example>
```

**STRONG:**
```xml
<example scenario="Ambiguous bulk operation">
  <input>"Update all X to value Y"</input>
  <reasoning>
    "all X" matches multiple categories. "value Y" applies uniformly?
    Domain expert approach: discover -> analyze -> present options
  </reasoning>
  <action>
    1. read_data(entities, search: "%X%") -> N entities, M categories
    2. read_data(related_context) -> patterns
    3. Analysis: Category A aligns, B unusual

    write_data(
      goal="Update Category A to Y",
      reasoning="Found N across M. Y aligns with A. B excluded.",
      hitl_summary="Updating A...\n\nB NOT included - requires review.",
      operations=[...],
      impact={"updates": {...}, "warnings": ["B excluded"]}
    )
  </action>
</example>
```

---

## XML Structure Template

```xml
<background_information>
  ## Your Role
  [World-class practitioner framing OR orchestrator framing]

  ## Your Position
  [Relationship to other agents, what you receive/return]

  ## Your Expertise (for executors)
  [Domain doctrine - knowledge to reason FROM]
</background_information>

<available_tools>
  ## tool_name - When valuable
  - Purpose (WHY)
  - What it returns
  - **The ONLY way to X** (if exclusive)
  - Strategic context
</available_tools>

<instructions>
  ## Core Mindset / Prime Directive
  [How to think - principles, not procedures]

  ## Process Framework
  [INVENTORY -> CLASSIFY -> ASSESS -> ROUTE (orchestrators)]
  [DIAGNOSE -> DECLARE -> EXECUTE -> VERIFY -> DELIVER (executors)]

  ## Quality Standards
  [Quality as identity]
</instructions>

<examples>
  [2-4 COMPLEX examples showing full cognitive cycle]
  [Analyze -> Research -> Decide -> Execute -> Review]
</examples>

<output_format>
  [Completion rules, what to return]
</output_format>
```

---

## Explicit Confusion Handling

**Only for proven, high-impact confusions:**

```
**NEVER do this:**
- Do NOT use ls, cat on storage_paths - they're cloud references, not filesystem
```

**Rule:** If you can fix it in code, fix it in code. Prompts shape reasoning.

---

## Validation Checklist

### Prime Directive

- [ ] Identity worth inhabiting (not "AI assistant")
- [ ] Senior Partner behavior (proposes, not asks)
- [ ] Every token earns its place

### Domain Expert Voice

- [ ] Professional credentials
- [ ] Actual domain vocabulary
- [ ] Domain doctrine (knowledge to reason FROM)
- [ ] Quality as identity
- [ ] Principles enable full range

### Tool Mastery

- [ ] Purpose documented (WHY)
- [ ] Exclusivity patterns ("Only way to X")
- [ ] Chaining patterns
- [ ] Verification loop visible

### Protocol Integration (Domain Reasoning Framework)

- [ ] Agent knows WHEN to load protocols (domain task triggers)
- [ ] Agent knows WHICH protocols to load (by domain context)
- [ ] Protocol loading guidance in prompt (or agent has load_protocol tool)
- [ ] Domain-specific reasoning delegated to protocols (not hardcoded in prompt)
- [ ] Anti-patterns in protocols, not prompt (unless proven confusion)

### Examples

- [ ] 2-4 COMPLEX examples
- [ ] Multi-step reasoning
- [ ] Ambiguity handled with suggestions
- [ ] COMPLETE tool calls
- [ ] Full cycle: Analyze -> Research -> Decide -> Execute -> Review

---

## Reference

### File Locations

| What | Where |
|------|-------|
| Prompts | `prompts/*.prompt` |
| Protocols | `prompts/protocols/{domain}/*.protocol` |
| Protocol loader | `tools/protocol_loader.py` |
| Full standards | `docs/architecture/tech/PROMPT_ENGINEERING_STANDARDS.md` |

### Protocol Domains

| Domain | Path | Contents |
|--------|------|----------|
| `catalog` | `prompts/protocols/catalog/` | business_context, family_fit, pricing, duplicate_prevention, visual_analysis |
| `pm` | `prompts/protocols/pm/` | domain_awareness, coordination_patterns, conflict_resolution |
| `shared` | `prompts/protocols/shared/` | Shared protocols |
| `shared/tool_mastery` | `prompts/protocols/shared/tool_mastery/` | read_data, write_data, view_image, etc. |

### Related Skills

| Skill | When |
|-------|------|
| `workflow-evaluation` | Diagnosing protocol issues in traces |
| `agent-improvement` | Adding protocol guidance to agents |
| `specialist-creation` | Creating agents with protocol awareness |
