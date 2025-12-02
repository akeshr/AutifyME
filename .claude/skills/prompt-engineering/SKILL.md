---
name: prompt-engineering
description: Design prompts for AutifyME agents using XML structure, right altitude, and canonical examples. Use when creating or refactoring PM/specialist prompts. (project)
---

# Prompt Engineering Standards

## Guiding Principles

> "Find the smallest possible set of high-signal tokens that maximize the likelihood of your desired outcome."

**Trust LLM Intelligence:** Modern LLMs have massive context windows, strong reasoning, and autonomous problem-solving. Give them problems + rich context, not step-by-step recipes. Don't handhold - if an LLM with full context can figure it out, don't hardcode the logic.

**Prompts define what to think, not what code to write.**

---

## [CRITICAL] Examples Strategy

### Complex Examples Over Simple

**Complex examples teach simple scenarios. Simple examples do NOT teach complex scenarios.**

An agent learning from a complex example (multi-table operation, edge cases, ambiguous input, research phase) can easily handle simple cases. But an agent learning only from simple examples will FAIL when encountering complexity.

### What Makes a Good Example

**2-4 complex canonical examples** that:
- Force multi-step reasoning and OOTB thinking
- Include edge cases and ambiguity
- Show the full cognitive cycle: **Analyze -> Research -> Decide -> Execute -> Review**
- Demonstrate handling ambiguity with **suggestions and options**, not questions
- Show complete tool calls with ALL parameters (especially HITL fields)

### Bad vs Good Examples

**BAD (too simple, doesn't teach reasoning):**
```xml
<example scenario="Price update">
  <user_input>"Update JAR-PET-500ML to Rs 35"</user_input>
  <your_action>write_data(update price)</your_action>
</example>
```

**GOOD (forces holistic thinking, shows complete execution):**
```xml
<example scenario="Ambiguous bulk pricing request">
  <user_input>"Update jar prices to Rs 35"</user_input>
  <your_reasoning>
    Ambiguous: "jar" matches multiple families (PET Jars, Glass Jars)
    "prices" plural - all products? MRP only? All price lists?

    Domain expert approach:
    1) Discover all jar products and current pricing
    2) Analyze if Rs 35 makes sense for each
    3) Present options with recommendation (don't just ask)
  </your_reasoning>
  <your_action>
    1. read_data(products, search: "%jar%") -> 8 products across 2 families
    2. read_data(product_prices, relations: [products, price_lists]) -> MRP + Wholesale
    3. read_data(product_families, filter: name contains "jar") -> PET Jars, Glass Jars

    Analysis: PET Jars avg Rs 28 (Rs 35 = +25%), Glass Jars avg Rs 45 (Rs 35 = -22%)

    write_data(
      goal="Update PET Jar prices to Rs 35 (MRP)",
      reasoning="User said 'jar prices Rs 35'. Found 8 jars across 2 families. Rs 35 aligns with PET Jars (+25% increase, reasonable). Glass Jars at Rs 35 would be -22% decrease (unusual). Recommending PET Jars only.",
      hitl_summary="Updating PET Jar prices to Rs 35 (MRP tier).\n\n5 products affected:\n- JAR-PET-250ML: Rs 22 -> Rs 35\n- JAR-PET-500ML: Rs 28 -> Rs 35\n- JAR-PET-1L: Rs 32 -> Rs 35\n...\n\nNote: Glass Jars (3 products) NOT included - Rs 35 would be unusual decrease from current Rs 40-55.\n\nReply *approve* to proceed or *reject* to cancel.",
      operations=[...],
      impact={"updates": {"product_prices": 5}, "warnings": ["Glass Jars excluded - price decrease unusual"]}
    )
  </your_action>
</example>
```

### Coverage Requirements

**PM Examples Must Show:**
- Multi-specialist orchestration with complete handoffs
- Incomplete requests handled with **suggestions** (not just questions)
- Error recovery and alternative paths
- Complex multi-step workflows with all context passed

**Specialist Examples Must Show:**
- Deep research phase (5+ queries across multiple related tables)
- Ambiguity resolution using domain expertise
- Complete tool calls with ALL parameters (goal, reasoning, hitl_summary, asset_uploads, operations, impact)
- Self-review and quality verification before returning

---

## Agent Behavior Standards

### Suggestive, Not Passive

Agents are proactive partners. When requests are incomplete or ambiguous:
- **Come with options and recommendations** - don't just ask questions
- **Surface what's missing** with proposed solutions
- **Use domain expertise** to fill gaps intelligently

**BAD:** "What price should I use?"
**GOOD:** "Similar products are Rs 20-35. Based on [analysis], I recommend Rs 28. Options: 1) Rs 28 (recommended), 2) Specify your price, 3) Research market rates"

### Holistic Analysis

Before acting, build a complete mental model:
- What exists in this domain? What patterns are established?
- How does this request fit with existing data?
- What are the implications and edge cases?

### Deep Research

Thorough investigation beats shallow validation:
- Search with multiple term variations
- Query related tables to understand context
- Look at existing patterns before proposing changes
- 5+ queries is normal for complex operations

### Self-Review Before Delivery

Review outputs before returning:
- Does this meet quality standards?
- Are all required fields populated?
- Would I approve this if I were the user?

---

## The Right Altitude

| Too Low | Right Altitude | Too High |
|---------|---------------|----------|
| Python code snippets | Decision principles + examples | "Handle media" |
| Step-by-step implementation | Reasoning framework | Generic platitudes |
| Hardcoded rules | Trust intelligence with context | Vague instructions |

**AutifyME 2-Level Architecture:**
- **PM:** High altitude (cross-domain orchestration, delegate with context)
- **Specialists:** Low-medium altitude (domain execution, deep research, complete tool calls)

---

## XML Structure Template

```xml
<background_information>
  ## Your Role
  [Who you are in the hierarchy]

  ## Your Position
  [Who delegates to you, what domains you own]

  ## Your Expertise
  [What makes you a domain expert, not a data entry clerk]
</background_information>

<available_tools>
  ## Tool Name - When valuable
  - What it does
  - When to use it
  - What it returns
</available_tools>

<instructions>
  ## Core Mindset
  [How to think - domain expert, not passive executor]

  ## Decision Framework
  [How to analyze, research, decide]

  ## Quality Standards
  [What "good" looks like]
</instructions>

<examples>
  [2-4 COMPLEX examples showing full cognitive cycle]
</examples>

<output_format>
  ## Return Structure
  [What to return in different scenarios]

  ## Before Returning
  [Self-review checklist]
</output_format>
```

---

## Core Rules

### No Code in Prompts

**Instead of:**
```python
if state.get("pending_interrupts"):
    intent = "resume_workflow"
```

**Write:**
```xml
<instruction>
Check if workflow is interrupted (pending approvals exist):
- If yes: Intent is resume_workflow
- If no: Classify based on message content
</instruction>
```

**Exceptions:** Pydantic model names, tool names, example JSON shapes in examples.

### No Hardcoded Rules or Anti-Patterns Lists

Trust intelligence. Instead of listing 10 things NOT to do, show 2-4 complex examples of what TO do. The LLM will generalize.

### Simple, Direct Language

- Active voice: "Analyze the request" not "The request should be analyzed"
- Imperative mood: "Delegate to specialists" not "You should delegate"
- One idea per sentence

---

## Anti-Patterns to Avoid

### Workflow-Specific Instructions

**Bad:**
```
When users send product images:
1. Download from WhatsApp
2. Call creative specialist
3. Then call catalog specialist
```

**Good:**
```
Delegate to domain specialists with complete context.
They handle research, validation, and execution in their domain.
```
Then show a complex example demonstrating the flow.

### Simple Examples That Don't Teach

**Bad:** Single-step examples, happy-path only, no ambiguity handling

**Good:** Multi-step examples with research phases, ambiguity resolved through analysis not questions, complete tool calls

### Lists of Anti-Patterns

**Bad:**
```
NEVER do X
NEVER do Y
NEVER do Z
```

**Good:** Show positive examples of correct behavior. LLMs generalize from good examples.

---

## Validation Checklist

### Structure
- [ ] Uses XML tags for sections
- [ ] Has all sections (background, tools, instructions, examples, output)
- [ ] Clear visual hierarchy

### Content
- [ ] No Python/code snippets (except in examples)
- [ ] No workflow-specific hardcoding
- [ ] No lists of anti-patterns - use positive examples
- [ ] Right altitude for hierarchy position
- [ ] Trust intelligence - minimal prescriptive rules

### Examples (CRITICAL)
- [ ] 2-4 COMPLEX examples (not simple)
- [ ] Examples force multi-step reasoning
- [ ] Examples show ambiguity handled with suggestions
- [ ] Examples show deep research (5+ queries)
- [ ] Examples show COMPLETE tool calls (all parameters)
- [ ] Examples include edge cases and OOTB thinking
- [ ] Each example shows: Analyze -> Research -> Decide -> Execute -> Review

### Agent Behavior
- [ ] Suggestive behavior emphasized
- [ ] Holistic analysis encouraged
- [ ] Deep research expected
- [ ] Self-review before delivery

---

## Reference

Full standards: `docs/architecture/tech/PROMPT_ENGINEERING_STANDARDS.md`
