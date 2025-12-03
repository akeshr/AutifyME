---
name: prompt-engineering
description: Design world-class prompts using domain expert voice, professional vocabulary, and versatility through principles. Frame agents as top 0.01% practitioners, not AI assistants. (project)
---

# Prompt Engineering Standards

## Guiding Principles

> "Find the smallest possible set of high-signal tokens that maximize the likelihood of your desired outcome."

**Trust LLM Intelligence:** Modern LLMs have massive context windows, strong reasoning, and autonomous problem-solving. Give them problems + rich context, not step-by-step recipes. Don't handhold - if an LLM with full context can figure it out, don't hardcode the logic.

**Prompts define what to think, not what code to write.**

---

## [CRITICAL] Domain Expert Voice

### World-Class Practitioner Framing

**Don't write prompts for "an AI assistant." Write prompts for a world-class domain expert.**

The agent should think, speak, and reason like a top 0.01% practitioner in their domain. This means:

1. **Professional credentials** - "You've shot for Apple, Dyson, Rolex" not "You are an image editing assistant"
2. **Domain vocabulary** - Use the actual language experts use, not generic AI terms
3. **Mental models** - Teach how experts think, not what steps to follow

### Domain Vocabulary Over Generic Terms

**Photography Example:**
- BAD: "Adjust the lighting to look professional"
- GOOD: "Key/fill ratio 3:1 for dimension, rim light for separation, specular highlights controlled not blown"

**Catalog Example:**
- BAD: "Organize products properly"
- GOOD: "Family-variant hierarchy with inheritance, price list tiers, cross-reference validation"

### Material/Domain Doctrine

For specialists that work with specific domains, encode deep domain knowledge:

**Photography Materials Doctrine:**
```
- Glass: Internal caustics, edge refraction, transparency depth - never flat
- Metal: Gradient reflections, micro-texture, controlled specularity
- Fabric: Weave texture, drape shadows, fiber detail at edges
- Ceramic: Subtle surface texture, weight impression, matte-to-satin range
```

**Catalog Domain Doctrine:**
```
- Products exist in families with variant axes (size, color, material)
- Price lists have tiers (MRP, wholesale, distributor) with relationships
- SKUs follow patterns that encode product attributes
```

This doctrine becomes the agent's expertise - they reason FROM it, not just follow rules.

### Quality Standard as Identity

Don't make quality a checklist. Make it identity:

- BAD: "Check that the image meets quality standards before returning"
- GOOD: "Portfolio Test: Would this image make your portfolio? If not, iterate."

The agent should be embarrassed to return subpar work, not just checking boxes.

### Versatility Through Principles

**Teach principles that enable the full range of the domain, not specific use cases.**

- BAD: "For hero shots, use white background with soft lighting"
- GOOD: "Light reveals form and material truth. Background serves the story. Execute the creative direction."

The first teaches one scenario. The second enables infinite scenarios.

### Explicit Confusion Point Handling

When there's a common confusion (e.g., cloud storage vs filesystem), address it explicitly:

```xml
**NEVER do this:**
- Do NOT use ls, cat, or filesystem commands on storage_paths
- storage_path like `inbox/thread_id/photo.jpg` is a cloud reference, not `/inbox/...` on disk
```

This is the ONE exception to "no anti-pattern lists" - when there's a specific, common confusion that causes real failures.

---

## [CRITICAL] Tool Prompts vs Agent Prompts

### Two Fundamentally Different Prompt Types

**Agent Prompts** (e.g., `creative_specialist.prompt`):
- Define identity, expertise, reasoning patterns
- Guide tool selection and usage
- Shape how the agent thinks about problems
- Live in `prompts/specialists/` or `prompts/pm/`

**Tool Prompts** (e.g., `TOOL_SYSTEM_PROMPT` in tool.py):
- Instruct the underlying model executing the tool (e.g., Gemini for image generation)
- Interpret and execute instructions received from the agent
- Provide domain mastery for faithful execution
- Live inside tool implementations

### The "Execute the Brief" Pattern for Tool Prompts

**Tool prompts should honor instructions, not impose preferences.**

The agent decides WHAT to do. The tool executes HOW to do it expertly.

**BAD (tool imposing defaults):**
```
Always use white background for product shots.
Apply studio lighting with soft shadows.
```

**GOOD (tool honoring the brief):**
```
EXECUTE THE CREATIVE DIRECTION - The instruction is your brief. Honor it precisely.

Light reveals form and material truth. Background serves the story.
Your job: interpret the instruction with professional expertise, not override it.
```

### Tool Prompt Domain Mastery

Tool prompts need DEEP domain knowledge to interpret instructions correctly:

```
MATERIAL TRUTH:
- Glass: Internal caustics, edge refraction, transparency depth
- Metal: Gradient reflections, micro-texture, controlled specularity
- Fabric: Weave texture, drape shadows, fiber detail

This knowledge lets you interpret "make it look premium" correctly for each material.
```

### Tool Prompt Quality Standard

End every tool prompt with an uncompromising quality bar:

```
OUTPUT: Every image must be immediately publishable.
No "almost there." This is the final frame.
```

---

## [CRITICAL] Prompt Debugging Methodology

### When Agent Behavior is Wrong

Follow this diagnostic flow:

```
1. OBSERVE: What exactly is the agent doing wrong?
   - Using wrong tool? (ls instead of view_image)
   - Wrong parameter format? (leading slashes)
   - Missing required step? (no research phase)
   - Wrong reasoning? (treating cloud as filesystem)

2. DIAGNOSE: What's missing or wrong in the prompt?
   - Mental model mismatch? (cloud vs filesystem confusion)
   - Missing explicit guidance? (only way to do X)
   - Altitude wrong? (too prescriptive or too vague)
   - Missing domain doctrine? (doesn't know material behavior)
   - Examples too simple? (didn't show the pattern)

3. FIX: Add minimal, targeted guidance
   - For mental model issues: Add explicit "NEVER do this" section
   - For missing patterns: Add to tool description or examples
   - For wrong reasoning: Add domain doctrine
   - For altitude issues: Adjust to principles vs steps

4. VERIFY: Test the specific scenario again
```

### Common Prompt Bugs and Fixes

| Symptom | Root Cause | Fix |
|---------|------------|-----|
| Agent uses wrong tool | Unclear tool purpose | Clarify "This is the ONLY way to X" |
| Agent adds path artifacts | Mental model mismatch | Add explicit format guidance + code normalization |
| Agent asks instead of suggests | Missing suggestive behavior | Show examples with recommendations |
| Agent skips research | Examples too simple | Add complex examples with 5+ queries |
| Tool ignores instruction | Tool prompt too prescriptive | Add "execute the brief" pattern |
| Tool uses wrong defaults | Tool prompt has hardcoded preferences | Remove defaults, add "honor the instruction" |

### LLM Artifact Handling

LLMs generate artifacts that need handling at TWO layers:

**Code Layer (normalization):**
```python
def normalize_storage_path(path: str) -> str:
    """LLMs sometimes add leading slashes."""
    return path.lstrip("/\\")
```

**Prompt Layer (clarification):**
```xml
storage_path format: `inbox/thread_id/photo.jpg` (no leading slash)
```

Both layers working together = robust system.

---

## [CRITICAL] Execution Patterns

### Parallel vs Sequential Tool Calls

Explicitly guide when to parallelize:

**Parallel (independent operations):**
```
When you need multiple pieces of information that don't depend on each other,
call tools in parallel for efficiency:
- view_image(source1) AND view_image(source2) - parallel
- read_data(products) AND read_data(price_lists) - parallel
```

**Sequential (dependent operations):**
```
When outputs feed inputs, execute sequentially:
- read_data(products) THEN write_data(using product IDs)
- image_studio(edit) THEN view_image(verify result)
```

### Context Flow Between Layers

```
PM -> Specialist:
- Full user request + relevant history
- Any media references (storage_paths)
- Constraints or preferences

Specialist -> Tool:
- Clear instruction (the "brief")
- Required parameters
- Expected outcome

Tool -> Specialist:
- Results with storage_paths
- Metadata for verification
- Any warnings or limitations
```

### The "Only Way" Pattern

When there's ONE correct way to do something, make it explicit:

**BAD (implies alternatives exist):**
```
You can use view_image to see images.
```

**GOOD (closes off wrong paths):**
```
**This is the ONLY way to see images** - not ls, not cat, not filesystem commands.
Use view_image(storage_path) to fetch from cloud and see the actual image.
```

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

### Domain Expert Voice (CRITICAL)

- [ ] Agent framed as world-class practitioner, not "AI assistant"
- [ ] Uses actual domain vocabulary (not generic AI terms)
- [ ] Has domain doctrine (deep knowledge the agent reasons FROM)
- [ ] Quality standard is identity ("Portfolio Test"), not checklist
- [ ] Principles enable full range (versatile), not specific use cases
- [ ] Common confusion points addressed explicitly with "NEVER do this"

### Content

- [ ] No Python/code snippets (except in examples)
- [ ] No workflow-specific hardcoding
- [ ] No lists of anti-patterns - use positive examples (except confusion points)
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

### Tool Prompts (if applicable)

- [ ] "Execute the brief" pattern (honor instructions, don't impose)
- [ ] Deep domain mastery for interpretation
- [ ] Uncompromising quality bar at the end
- [ ] No hardcoded defaults that override instructions

### Execution Patterns

- [ ] Parallel vs sequential guidance included
- [ ] "Only way" pattern for exclusive methods
- [ ] Context flow between layers documented

---

## Reference

Full standards: `docs/architecture/tech/PROMPT_ENGINEERING_STANDARDS.md`
