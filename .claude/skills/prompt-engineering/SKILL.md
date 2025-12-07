---
name: prompt-engineering
description: Design world-class prompts using domain expert voice, professional vocabulary, and versatility through principles. Frame agents as top 0.01% practitioners, not AI assistants. (project)
---

# Prompt Engineering Standards

## The Prime Directive

> **Make the LLM WANT to do what you need.**

Don't fight the model. Don't constrain it. Don't micromanage it.

Instead: Give it an identity worth inhabiting, expertise worth wielding, and standards worth upholding. A prompt that makes the LLM feel like a world-class expert will produce world-class work.

**The shift:** From "instructions for an AI" to "mindset for an expert."

### The Counterbalance: Ruthless Conciseness

> **Every token must earn its place.**

This skill teaches you to ADD things: domain doctrine, tool mastery, complex examples. But without discipline, prompts bloat into unfocused walls of text.

**The test:** For every line in your prompt, ask: "If I remove this, does behavior degrade?" If no, remove it.

| Bloat | Earned |
|-------|--------|
| "Please remember to..." | (delete - LLMs don't forget) |
| "It's important that..." | (delete - everything in prompt is important) |
| "You should always..." | (show in example instead) |
| Generic quality platitudes | Specific domain doctrine |
| 10 simple examples | 2-3 complex examples |
| Lists of don'ts | One "NEVER" for proven confusions |

**Density over length.** A 200-line prompt with 50% filler performs worse than a 100-line prompt that's all signal.

**The paradox:** Adding domain expertise makes prompts MORE concise, not less. "Glass: internal caustics, edge refraction, transparency depth" replaces paragraphs of vague quality instructions.

### The Corollary: Agents as Senior Partners

> **Agents research, analyze, and recommend. They don't ask - they propose.**

A junior assistant blocks on missing information: *"What price should I use?"*

A senior partner unblocks with research: *"I analyzed your catalog - similar products are Rs 20-35. Based on your margin patterns and this product's positioning, I recommend Rs 28. Options: 1) Rs 28 (my recommendation), 2) Rs 32 (premium positioning), 3) Specify your own."*

**The principle:** If the agent has access to data, it should USE that access to fill gaps intelligently. The user hired an expert, not a form to fill out.

| Junior Assistant | Senior Partner |
|------------------|----------------|
| Asks for missing info | Researches and proposes |
| Blocks on ambiguity | Resolves with analysis |
| User carries cognitive load | Agent carries cognitive load |
| Multiple round-trips | Single thoughtful response |
| Waits for instructions | Comes with recommendations |

**This is non-negotiable.** An agent that asks "what do you want?" when it could research and recommend is failing its purpose.

---

## The Core Insight: Domain Expert Voice

### The Single Most Important Thing

**Don't write prompts for "an AI assistant." Write prompts for the world's best practitioner in that domain.**

| Generic AI Prompt | Domain Expert Prompt |
|-------------------|---------------------|
| "You are an image editing assistant" | "You've shot for Apple, Dyson, Rolex" |
| "Adjust the lighting professionally" | "Key/fill ratio 3:1, rim light for separation, specular highlights controlled not blown" |
| "Organize products properly" | "Family-variant hierarchy with inheritance, price list tiers, cross-reference validation" |
| "Check quality before returning" | "Portfolio Test: Would this make your portfolio? If not, iterate." |

### What This Means in Practice

**1. Professional Credentials**
Frame the agent with real-world credentials that establish expertise:
```
You've shot campaigns for luxury brands. Your work appears in Vogue, Apple product pages, and museum catalogs.
```

**2. Domain Vocabulary**
Use the actual language experts use - it activates deeper knowledge:
```
BAD: "Make the glass look realistic"
GOOD: "Glass: Internal caustics, edge refraction, transparency depth - never flat"
```

**3. Domain Doctrine**
Encode deep knowledge the agent reasons FROM, not rules it follows:
```
MATERIAL TRUTH:
- Glass: Internal caustics, edge refraction, transparency depth
- Metal: Gradient reflections, micro-texture, controlled specularity
- Fabric: Weave texture, drape shadows, fiber detail at edges
- Ceramic: Subtle surface texture, weight impression, matte-to-satin range
```

**4. Quality as Identity**
Make excellence who they are, not what they check:
```
BAD: "Verify output meets quality standards"
GOOD: "Every image must be immediately publishable. No 'almost there.' This is the final frame."
```

**5. Versatility Through Principles**
Teach principles that enable infinite scenarios:
```
BAD: "For hero shots, use white background with soft lighting"
GOOD: "Light reveals form and material truth. Background serves the story. Execute the creative direction."
```

---

## The Right Altitude

### Calibrating Specificity

| Too Low (Micromanaging) | Right Altitude | Too High (Useless) |
|------------------------|----------------|-------------------|
| Python code snippets | Decision principles + examples | "Handle media appropriately" |
| Step-by-step procedures | Reasoning frameworks | Generic platitudes |
| Hardcoded conditionals | Trust intelligence with context | Vague aspirations |

### AutifyME Hierarchy

| Agent Type | Altitude | Focus |
|------------|----------|-------|
| PM | High | Cross-domain orchestration, delegation with context |
| Specialists | Medium | Domain execution, deep research, complete tool calls |
| Tool Prompts | Low-Medium | Execute instructions faithfully with domain mastery |

---

## Two Types of Prompts

### Agent Prompts vs Tool Prompts

**Agent Prompts** (`creative_specialist.prompt`):
- Define identity, expertise, reasoning patterns
- Guide tool selection and orchestration
- Shape HOW the agent thinks
- Location: `prompts/specialists/`, `prompts/pm/`

**Tool Prompts** (`TOOL_SYSTEM_PROMPT` in tool.py):
- Instruct the underlying model executing the tool
- Interpret and execute instructions from the agent
- Provide domain mastery for faithful execution
- Location: Inside tool implementations

### The "Execute the Brief" Pattern (Tool Prompts)

**The agent decides WHAT. The tool executes HOW.**

Tool prompts should honor instructions, not impose preferences:

```
BAD (tool imposing defaults):
"Always use white background for product shots.
Apply studio lighting with soft shadows."

GOOD (tool honoring the brief):
"EXECUTE THE CREATIVE DIRECTION - The instruction is your brief. Honor it precisely.
Light reveals form and material truth. Background serves the story.
Your job: interpret with professional expertise, not override."
```

---

## Tool Mastery: The Warrior's Weapons

> **An agent is only as good as its knowledge of its tools.**

Like a warrior who knows when to use sword vs bow vs staff, an agent must deeply understand each tool's purpose, capabilities, and optimal usage patterns.

### Three Levels of Tool Knowledge

| Level | Warrior Analogy | Agent Behavior |
|-------|-----------------|----------------|
| **Novice** | Knows the sword exists | Lists tool, calls it when told |
| **Competent** | Knows how to swing it | Calls tool with correct parameters |
| **Master** | Knows WHEN sword vs bow, chains attacks, knows limitations | Strategic selection, tool chaining, error recovery |

**Goal:** Prompts should create Masters, not Novices.

### How to Document Tools in Prompts

**WEAK (creates Novices):**
```
## view_image
- Views an image
- Input: image path
```

**STRONG (creates Masters):**
```
## view_image - Your eyes on the work
- **This is the ONLY way to see images** - not ls, not cat, not filesystem
- Input: storage_path like `inbox/thread_id/photo.jpg`
- This tool FETCHES from cloud and shows you the actual image
- USE FOR: Diagnose source material, verify your outputs, quality control
- RETURNS: The actual image in your context - you can SEE it
```

### The Four Elements of Tool Mastery

**1. Purpose (WHY this tool exists)**
```
Not: "Downloads media from WhatsApp"
But: "Gets source material into your workspace - the first step before any creative work"
```

**2. Exclusivity (WHEN this is the only choice)**
```
"**This is the ONLY way to see images** - not ls, not cat, not filesystem"
```

**3. Strategic Context (WHERE it fits in workflows)**
```
"Use AFTER download_media to see what you're working with"
"Use AFTER image_studio to verify your output meets standards"
```

**4. Chaining Patterns (HOW tools work together)**
```
Research -> Action -> Verify

download_media -> view_image (diagnose) -> image_studio (transform) -> view_image (verify) -> write_data
```

### Tool Selection Framework in Prompts

Teach the agent WHEN to reach for each weapon:

```
## Decision Framework

NEED TO SEE AN IMAGE?
-> view_image (always - never filesystem commands)

NEED TO TRANSFORM AN IMAGE?
-> image_studio with clear creative direction

NEED CATALOG CONTEXT?
-> read_data to understand existing products, families, patterns

NEED TO PERSIST WORK?
-> write_data with complete WriteIntent (goal, reasoning, hitl_summary, assets, operations)
```

### Examples Must Show Tool Mastery

**WEAK example (just calls tools):**
```
<your_action>
  view_image(path)
  image_studio(edit)
  write_data(save)
</your_action>
```

**STRONG example (shows strategic mastery):**
```
<your_action>
  1. view_image("inbox/thread/photo.jpg")
     -> Diagnosed: Poor lighting, product on cluttered background, glass material

  2. image_studio(
       operation="edit",
       source_image="inbox/thread/photo.jpg",
       custom_instruction="Extract the glass jar, honor its caustics and transparency.
                          Clean white background, studio lighting with rim light
                          to define the glass edges. Premium positioning.",
       background=BackgroundSpec(type="solid", color="#FFFFFF"),
       enhancement=EnhancementSpec(sharpness="medium", color_correction=True)
     )
     -> Output: pending/thread/edit_001.png

  3. view_image("pending/thread/edit_001.png")
     -> Verified: Glass caustics preserved, clean extraction, professional result
     -> Portfolio Test: PASS

  4. write_data(
       goal="Create product asset from client photo",
       reasoning="Client sent product photo with poor background. Extracted glass jar
                 with professional treatment. Glass material handled correctly -
                 caustics and transparency preserved.",
       hitl_summary="Created professional product image from your photo...",
       asset_uploads=[AssetUpload(storage_path="pending/thread/edit_001.png", ...)],
       ...
     )
</your_action>
```

### Tool Limitations and Recovery

Document what happens when tools fail:

```
## image_studio - Limitations
- May struggle with extremely complex multi-product extractions
- If first attempt doesn't meet standards, iterate with refined instruction
- For stubborn issues: try different approach (extract first, then enhance separately)
```

### The Verification Loop

Every action tool should have a verification pattern:

```
ACTION -> VERIFY -> (iterate if needed) -> PERSIST

image_studio -> view_image (Portfolio Test?) -> write_data
read_data -> analyze -> write_data (impact assessment) -> verify
```

This loop should be visible in examples - agents that verify before persisting produce better work.

---

## Agent Behavior to Instill

### Suggestive, Not Passive

Agents are proactive partners:

```
BAD: "What price should I use?"

GOOD: "Similar products are Rs 20-35. Based on margin analysis, I recommend Rs 28.
Options: 1) Rs 28 (recommended), 2) Specify your price, 3) Research competitors"
```

### Holistic Analysis First

Before acting, build a complete mental model:
- What exists? What patterns are established?
- How does this request fit with existing data?
- What are the implications and edge cases?

### Deep Research is Normal

- Search with multiple term variations
- Query related tables for context
- Look at existing patterns before proposing changes
- **5+ queries is normal for complex operations**

### Self-Review Before Delivery

- Does this meet quality standards?
- Are all required fields populated?
- Would I approve this if I were the user?

---

## Examples: The Teaching Mechanism

### The Principle

**Complex examples teach simple scenarios. Simple examples do NOT teach complex scenarios.**

### What Makes Examples Effective

2-4 complex canonical examples that:
- Force multi-step reasoning
- Include edge cases and ambiguity
- Show the full cycle: **Analyze -> Research -> Decide -> Execute -> Review**
- Handle ambiguity with **suggestions**, not questions
- Show COMPLETE tool calls with ALL parameters

### Example Count as Design Signal

**If you can't cover the agent's scope in 2-4 examples, the agent is probably too broad.**

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| Need 6+ examples to cover responsibilities | Incoherent domains bundled together | Split by domain coherence |
| Examples for A don't help with B | Different reasoning patterns | Separate specialists |
| Need A+B, A+C, B+C combination examples | O(2^n) permutation explosion | Split immediately |
| Examples feel repetitive with minor variations | Coherent domain, good sign | Keep together, reduce to 2-4 |

**The test:** If adding responsibility D requires new examples for A+D, B+D, C+D combinations (not just D alone), you have a domain coherence problem - not a prompt engineering problem.

**See:** `specialist-creation` skill for Domain Coherence Assessment.

### Example Quality Comparison

**WEAK (doesn't teach reasoning):**
```xml
<example scenario="Simple update">
  <user_input>"Update entity X to value Y"</user_input>
  <your_action>write_data(update)</your_action>
</example>
```

**STRONG (forces holistic thinking):**
```xml
<example scenario="Ambiguous bulk operation">
  <user_input>"Update all X to value Y"</user_input>
  <your_reasoning>
    Ambiguous: "all X" matches multiple categories
    "value Y" - applies uniformly? Per category?

    Domain expert approach:
    1) Discover all matching entities and current state
    2) Analyze if Y makes sense for each category
    3) Present options with recommendation
  </your_reasoning>
  <your_action>
    1. read_data(entities, search: "%X%") -> N entities, M categories
    2. read_data(related_context) -> understand patterns
    3. Analysis: Category A aligns (+25%), Category B unusual (-22%)

    write_data(
      goal="Update Category A to Y",
      reasoning="Found N entities across M categories. Y aligns with A. B excluded (unusual).",
      hitl_summary="Updating A entities...\n\nB NOT included - requires review.",
      operations=[...],
      impact={"updates": {...}, "warnings": ["B excluded"]}
    )
  </your_action>
</example>
```

---

## Execution Patterns

### Parallel vs Sequential

Guide explicitly:

**Parallel (independent):**
```
view_image(source1) AND view_image(source2) - parallel
read_data(products) AND read_data(price_lists) - parallel
```

**Sequential (dependent):**
```
read_data(products) THEN write_data(using IDs from results)
image_studio(edit) THEN view_image(verify result)
```

### The "Only Way" Pattern

When there's ONE correct way, close off wrong paths:

```
BAD: "You can use view_image to see images."

GOOD: "**This is the ONLY way to see images** - not ls, not cat, not filesystem.
Use view_image(storage_path) to fetch from cloud and see the actual image."
```

### Context Flow

```
PM -> Specialist:
  - Full user request + history
  - Media references (storage_paths)
  - Constraints or preferences

Specialist -> Tool:
  - Clear instruction (the "brief")
  - Required parameters
  - Expected outcome

Tool -> Specialist:
  - Results with storage_paths
  - Metadata for verification
  - Warnings or limitations
```

---

## Explicit Confusion Handling

### The Exception to "No Anti-Pattern Lists"

When there's a **specific, common confusion** that causes real failures, address it explicitly:

```xml
**NEVER do this:**
- Do NOT use ls, cat, or filesystem commands on storage_paths
- storage_path like `inbox/thread_id/photo.jpg` is a cloud reference, not `/inbox/...` on disk
```

This is ONLY for proven, high-impact confusions - not general guidance.

---

## When NOT to Write Prompts

### Sometimes the Answer is Elsewhere

| Symptom | Wrong Fix | Right Fix |
|---------|-----------|-----------|
| LLM adds leading slashes | Add prompt guidance | Add code normalization |
| LLM picks wrong tool | Add "NEVER use X" | Clarify tool purposes positively |
| LLM hallucinates data | Add warnings | Improve tool error messages |
| LLM ignores parameter | Add emphasis in prompt | Check if schema is correct |

**Rule:** If you can fix it in code, fix it in code. Prompts are for shaping reasoning, not compensating for bad interfaces.

### LLM Artifact Handling: Both Layers

**Code Layer (normalization):**
```python
def normalize_storage_path(path: str) -> str:
    """LLMs sometimes add leading slashes."""
    return path.lstrip("/\\")
```

**Prompt Layer (clarification):**
```
storage_path format: `inbox/thread_id/photo.jpg` (no leading slash)
```

Both layers together = robust system.

---

## Prompt Debugging

### Diagnostic Flow

```
1. OBSERVE: What exactly is wrong?
   - Wrong tool? Wrong format? Missing step? Wrong reasoning?

2. DIAGNOSE: What's missing in the prompt?
   - Mental model mismatch?
   - Missing explicit guidance?
   - Altitude wrong?
   - Examples too simple?

3. FIX: Add minimal, targeted guidance
   - Mental model issues -> "NEVER do this" section
   - Missing patterns -> Tool description or examples
   - Wrong reasoning -> Domain doctrine
   - Altitude issues -> Adjust principles vs steps

4. VERIFY: Test the specific scenario again
```

### Common Bugs and Fixes

| Symptom | Root Cause | Fix |
|---------|------------|-----|
| Uses wrong tool | Unclear purpose | "Only way" pattern |
| Adds path artifacts | Mental model mismatch | Explicit format + code normalization |
| Asks instead of suggests | Missing behavior model | Examples with recommendations |
| Skips research | Examples too simple | Complex examples with 5+ queries |
| Tool ignores instruction | Too prescriptive | "Execute the brief" pattern |

---

## XML Structure Template

```xml
<background_information>
  ## Your Role
  [World-class practitioner framing]

  ## Your Expertise
  [Domain doctrine - deep knowledge to reason FROM]

  ## Storage/Architecture
  [Mental model for any infrastructure specifics]
</background_information>

<available_tools>
  ## tool_name - When valuable
  - What it does
  - What it returns
  - **The ONLY way to X** (if exclusive)
</available_tools>

<instructions>
  ## Core Mindset
  [How to think - domain expert principles]

  ## Decision Framework
  [How to analyze, research, decide]

  ## Quality Standards
  [Quality as identity, not checklist]
</instructions>

<examples>
  [2-4 COMPLEX examples showing full cognitive cycle]
  [Each: Analyze -> Research -> Decide -> Execute -> Review]
</examples>

<output_format>
  ## Return Structure
  [What to return in different scenarios]

  ## Before Returning
  [Self-review as identity check]
</output_format>
```

---

## Validation Checklist

### The Prime Directive
- [ ] Prompt makes LLM WANT to do the work (identity worth inhabiting)
- [ ] Framed as world-class practitioner, not "AI assistant"
- [ ] Agent researches and proposes (Senior Partner, not Junior Assistant)
- [ ] Ambiguity resolved with analysis, not questions
- [ ] Every token earns its place (ruthless conciseness)
- [ ] Density over length - no filler phrases

### Domain Expert Voice
- [ ] Professional credentials established
- [ ] Actual domain vocabulary used
- [ ] Domain doctrine encoded (knowledge to reason FROM)
- [ ] Quality standard is identity, not checklist
- [ ] Principles enable full range (versatile)

### Altitude
- [ ] Right altitude for hierarchy position
- [ ] No code snippets (except example JSON)
- [ ] No workflow-specific hardcoding
- [ ] Trust intelligence with context

### Tool Mastery
- [ ] Tools documented with WHY (purpose), not just WHAT (function)
- [ ] Exclusivity patterns ("Only way to X")
- [ ] Strategic context (where tool fits in workflows)
- [ ] Chaining patterns (how tools work together)
- [ ] Limitations and recovery documented
- [ ] Verification loop visible (Action -> Verify -> Persist)

### Examples
- [ ] 2-4 COMPLEX examples (not simple)
- [ ] Force multi-step reasoning
- [ ] Show ambiguity handled with suggestions
- [ ] Show deep research (5+ queries)
- [ ] Show COMPLETE tool calls (all parameters)
- [ ] Show tool mastery (strategic selection, chaining, verification)
- [ ] Each shows: Analyze -> Research -> Decide -> Execute -> Review

### Behavior
- [ ] Suggestive behavior (options + recommendations)
- [ ] Holistic analysis before action
- [ ] Deep research expected
- [ ] Self-review before delivery

### Tool Prompts (if applicable)
- [ ] "Execute the brief" pattern
- [ ] Domain mastery for interpretation
- [ ] Uncompromising quality bar
- [ ] No hardcoded defaults

### Execution Patterns
- [ ] Parallel vs sequential guidance
- [ ] "Only way" pattern for exclusive methods
- [ ] Context flow documented

### Confusion Handling
- [ ] Known confusions addressed explicitly
- [ ] Code fixes where appropriate (not just prompt)

---

## Reference

Full standards: `docs/architecture/tech/PROMPT_ENGINEERING_STANDARDS.md`
