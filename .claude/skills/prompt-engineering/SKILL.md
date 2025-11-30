---
name: prompt-engineering
description: Design prompts for AutifyME agents using XML structure, right altitude, and canonical examples. Use when creating or refactoring PM/specialist prompts.
---

# Prompt Engineering Standards

## Guiding Principle

> "Find the smallest possible set of high-signal tokens that maximize the likelihood of your desired outcome."

Prompts define **what to think**, not **what code to write**.

---

## The Right Altitude

| Too Low | Right Altitude | Too High |
|---------|---------------|----------|
| Python code snippets | Decision principles + examples | "Handle media" |
| Step-by-step implementation | Reasoning framework | Generic platitudes |

**AutifyME 2-Level Architecture:**
- **PM:** High altitude (cross-domain orchestration)
- **Specialists:** Low-medium altitude (domain execution with tools)

---

## XML Structure Template

```xml
<background_information>
  ## Your Role
  [Who you are in the hierarchy]

  ## Company Context
  [How brand/audience context is available - middleware-injected]

  ## Your Position
  [Who delegates to you, who you delegate to]
</background_information>

<available_tools>
  ## Tools You Have
  - tool_name: Purpose and when to use
  - another_tool: Purpose and when to use

  ## Available Specialists (if PM)
  - specialist_name: What domain they handle
</available_tools>

<instructions>
  ## Core Responsibilities
  [What decisions you make, what outcomes you produce]

  ## Decision-Making Framework
  [How to think about different scenarios]

  ## Quality Standards
  [What "good" looks like]

  ## Escalation & Errors
  [When to ask for help, how to handle failures]
</instructions>

<examples>
  ## Example 1: [Scenario Name]
  <example>
    <user_input>[Realistic input]</user_input>
    <your_reasoning>[Thought process]</your_reasoning>
    <your_action>[Tools called, delegation]</your_action>
    <expected_output>[What you return]</expected_output>
  </example>
</examples>

<output_format>
  ## Expected Structure
  Return: [Pydantic model or structure]

  ## Validation
  Before returning, verify:
  - [ ] Checklist item 1
  - [ ] Checklist item 2
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

**Exceptions allowed:** Pydantic model names, tool names, example JSON shapes.

### Simple, Direct Language

- Active voice: "Analyze the request" not "The request should be analyzed"
- Imperative mood: "Delegate to specialists" not "You should delegate"
- One idea per sentence

---

## Examples Strategy

**2-4 canonical examples** showing diverse scenarios, not 20 edge cases.

```xml
<example scenario="New product with partial data">
  <user_input>
    "catalog: t-shirt, size M"
    [No price, no image]
  </user_input>

  <your_reasoning>
    - Intent: New cataloging request
    - Data: Category (t-shirt), size (M)
    - Missing: Price (critical), image (helpful)
    - Decision: Ask for price before proceeding
  </your_reasoning>

  <your_action>
    Respond: "I can catalog that t-shirt in size M. What's the price?"
  </your_action>
</example>
```

**Coverage for PM:** Single-domain, multi-domain, interrupted workflows, different modalities.

**Coverage for Specialists:** Simple workflow, complex workflow, missing data, ambiguous input.

---

## Anti-Patterns

### Workflow-Specific Instructions (PM)

**Bad:**
```
You handle product cataloging. When users send product images:
1. Download from WhatsApp
2. Analyze the image
3. Create product listing
```

**Good:**
```
You orchestrate all business workflows by delegating to domain specialists:
- Cataloging Specialist: Product catalog management
- Marketing Specialist: Campaigns and content
- Operations Specialist: Billing, shipping, inventory

For each request:
1. Classify domain and intent
2. Delegate to appropriate specialist with complete context
3. Handle any approval workflows
4. Synthesize and relay results
```

### Implementation Instructions

**Bad:**
```
Use the download_whatsapp_media() function. It takes a media_id parameter
and returns a local file path. Check if return value is None.
```

**Good:**
```xml
<available_tools>
  - download_whatsapp_media: Downloads media from WhatsApp using media ID.
    Use when user sends images/videos. Returns local file path.
</available_tools>

<instruction>
  Download media before delegating to specialists that need visual analysis.
</instruction>
```

---

## Validation Checklist

### Structure
- [ ] Uses XML tags for sections
- [ ] Has all sections (background, tools, instructions, examples, output)
- [ ] Clear visual hierarchy

### Content
- [ ] No Python/code snippets (except model names)
- [ ] No workflow-specific hardcoding
- [ ] Right altitude for hierarchy position
- [ ] Simple, direct language
- [ ] Minimal tokens (no redundancy)

### Examples
- [ ] 2-4 canonical examples
- [ ] Diverse scenarios covered
- [ ] Includes reasoning process
- [ ] Realistic inputs/outputs

### Technical
- [ ] References correct Pydantic models
- [ ] Tool names match implementations
- [ ] Context injection points noted

---

## Reference

Full standards: `docs/architecture/tech/PROMPT_ENGINEERING_STANDARDS.md`
