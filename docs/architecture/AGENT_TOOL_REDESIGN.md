# Agent & Tool Redesign - Third Iteration

**Date:** 2025-12-11
**Status:** DIAGNOSTIC PHASE
**Goal:** Fix recurring PM/specialist/tool behavioral issues with first-principles design

---

## Executive Summary

**Problem:** Despite two prior redesign attempts, agents continue exhibiting problematic behaviors with tool usage and delegation. We're repeating mistakes.

**Approach:** Systematic diagnosis -> principles -> phased redesign with validation gates

**Success Criteria:**
- PM delegates correctly (right specialist, right context)
- Specialists use tools effectively (correct tool choice, complete inputs)
- Tools return actionable data (agents can proceed without confusion)
- No repeated anti-patterns from prior attempts

---

## PART I: DIAGNOSIS

### Current Architecture Snapshot

**PM (Project Manager):**
- Orchestrates 2-layer hierarchy: Analysts (research) + Specialists (execution)
- Has direct tools: inspect_schema, read_data, download_media, view_image
- Delegates to 5 sub-agents (3 analysts + 2 specialists)

**Analysts (Read-only research):**
- visual_analyst - image description
- product_analyst - market research
- catalog_analyst - catalog queries

**Specialists (Execution with HITL):**
- creative_specialist - image processing (Gemini 3 Pro)
- catalog_specialist - catalog CRUD

**Tools Inventory:**
1. **Platform Tools:** download_{platform}_media
2. **Research Tools:** research_product_tool, extract_web_content_tool
3. **Image Tools:** view_image, image_studio
4. **Data Engine:** inspect_schema, read_data, aggregate_data, write_data

### PM-Specific Architectural Issues

**FOUNDATIONAL: 6 PM Issues That Drive Lower-Layer Failures**

#### PM Issue #1: Role Ambiguity - Orchestrator vs Executor

**Problem:** PM's role oscillates between pure orchestrator and hands-on executor

**Evidence:**

| PM Behavior | Implication |
|-------------|-------------|
| Has tools (view_image, read_data, inspect_schema) | PM can execute work itself |
| Delegates to analysts for same capabilities | PM is pure orchestrator |
| Prompt: "Research and Propose - Never Ask Without Trying" | PM should do research itself |
| Prompt: "Delegate problems to team" | PM shouldn't do work, only orchestrate |

**Conflicting Signals:**

- PM has view_image BUT also delegates to visual_analyst
- PM has read_data BUT also delegates to catalog_analyst
- PM told to "research" BUT also has product_analyst for research

**Impact:** PM doesn't know when to execute vs delegate. Leads to:

- Inconsistent behavior (sometimes does itself, sometimes delegates)
- Wasted delegation (PM delegates what it could do itself)
- Wasted execution (PM does what should be delegated to specialists)

---

#### PM Issue #2: Tool Ownership Without Clear Purpose

**Problem:** PM has tools but no clear guidance on when to use them

**PM has these tools:**

| Tool | Why PM Has It? | When Should PM Use It? | Current Guidance |
|------|----------------|------------------------|------------------|
| view_image | ? | View before delegating? Or delegate viewing? | "Quick look at images" |
| read_data | ? | Quick lookups? Or always delegate? | "Simple lookups YOU need" |
| inspect_schema | ? | When PM needs clarity? Or delegate schema understanding? | "Quick schema reference when YOU need clarity" |
| download_media | Clear | PM always downloads first | "Download user attachments" |

**Questions Without Answers:**

- Why does PM have view_image if visual_analyst exists?
- Why does PM have read_data if catalog_analyst exists?
- When should PM use these vs delegate to analysts?

**Current Guidance is Vague:**

- "Quick look" - how quick? What counts as quick vs deep analysis?
- "Simple lookups YOU need" - what's simple? Who decides?
- "When YOU need clarity" - PM always needs clarity for routing

**Impact:** PM guesses at tool usage, leading to inconsistent delegation patterns

---

#### PM Issue #3: Context Enrichment Without Schema

**Problem:** PM told to "enrich context" but no definition of what that means

**Current Guidance:**

- "Delegate with enriched context from analysts"
- "Include: image path, relevant context from analysts, specific identifiers"

**Missing Specifications:**

| Scenario | What Context to Include? | Current Guidance |
|----------|-------------------------|------------------|
| User sends image + "catalog this" | Image description? Product count? Material? All? | "Relevant context" (vague) |
| User says "research product X" | Research results? Or just product name? | "Include from analysts" (vague) |
| User sends multiple images | Which images? Descriptions of each? | "Image path" (ambiguous) |
| Multi-step workflow | Context from step 1 to step 2? | None |

**Consequences:**

- PM improvises context inclusion
- Sometimes over-includes (waste tokens)
- Sometimes under-includes (specialist lacks info)
- No consistency across similar scenarios

**Impact:** Specialists receive unpredictable context quality

---

#### PM Issue #4: Delegation Logic Without Protocol

**Problem:** PM has no clear decision tree for delegation

**When should PM delegate to analyst vs specialist?**

Current prompt says:

- "Analysts (research, read-only)"
- "Specialists (execution, HITL required)"

**But this is ambiguous:**

| User Intent | Should PM... | Why Ambiguous? |
|-------------|--------------|----------------|
| "Check if product X exists" | Delegate to catalog_analyst? Or catalog_specialist? | Both can read_data. Analyst is "research" but this is a query. |
| "Describe this image" | Delegate to visual_analyst? Or creative_specialist? | Visual_analyst for description, creative for processing. But user just said "describe." |
| "Research product X" | Delegate to product_analyst? Or let catalog_specialist research itself? | Product_analyst is for research, but catalog_specialist has research tools. |
| "Add product X to catalog" | Research first (analyst) then create (specialist)? Or let specialist handle both? | Specialist has research tools - should it be self-sufficient? |

**No Protocol Exists For:**

- When to use analyst vs specialist for same capability
- When to chain analyst → specialist vs direct specialist delegation
- When PM should do itself vs delegate

**Impact:** PM makes inconsistent routing decisions

---

#### PM Issue #5: Multi-Step Orchestration Without Coordination

**Problem:** PM has no framework for coordinating multi-specialist workflows

**Current Guidance:**

- "Two-Layer Flow: Analysts gather → Specialists execute"
- "Typical flow: Visual context → Catalog check → Product research → Specialist execution"

**Missing:**

| Coordination Need | Current Guidance | Impact |
|-------------------|------------------|--------|
| Passing context between specialists | "Include relevant context" | PM must manually shuttle data, error-prone |
| Avoiding duplicate work | None | Multiple agents view/analyze same data |
| Shared state management | None | Each specialist starts fresh, no awareness of prior work |
| Workflow checkpointing | None | If specialist fails, unclear how to resume |
| Output aggregation | "Synthesize results" | No schema for combining multi-specialist outputs |

**Example Failure:**

```
User: "Create marketing images for product X"

PM needs to:
1. Get product details (catalog_analyst)
2. Generate images (creative_specialist)
3. Create asset records (catalog_specialist)

But PM has no protocol for:
- Passing product details from step 1 to step 2
- Ensuring creative knows what catalog needs
- Coordinating image specs between specialists
- Handling failure at step 2 (retry? abort?)
```

**Impact:** Multi-specialist workflows are fragile and inefficient

---

#### PM Issue #6: "Research and Propose" Without Bounds

**Problem:** PM told to research proactively but no limits or escalation

**Current Guidance:**

- "Research and Propose - Never Ask Without Trying"
- "When information is missing: USE your tools and team to fill gaps"

**Missing:**

| Scenario | Guidance Needed | Current State |
|----------|-----------------|---------------|
| Research returns no results | Try different query? Give up? How many attempts? | None |
| Multiple valid interpretations | Pick one? Ask user? Present all? | "Present options with reasoning" (vague) |
| Ambiguous user intent | Research all possibilities? Or ask immediately? | "Never ask without trying" (but trying what?) |
| Tool failures | Retry? Escalate? Continue without? | None |

**Failure Scenarios:**

- PM researches 10 times with similar queries (wasteful)
- PM gives up after 1 attempt (premature)
- PM presents 20 options (overwhelming user)
- PM proceeds with wrong assumption (damaging)

**Impact:** PM either wastes resources or fails prematurely

---

## Analyst Level (Layer 1): Research Layer Issues

**CRITICAL: 7 Analyst Issues Creating Inefficiency and Confusion**

#### Analyst Issue #1: Redundant Capabilities with Specialists

**Problem:** Analysts provide read-only research, but specialists have identical tools.

**Evidence:**

| Capability | Analysts Have | Specialists Have | Duplication |
|------------|--------------|------------------|-------------|
| Image viewing | visual_analyst: view_image | creative_specialist: view_image | FULL |
| Product research | product_analyst: research_product_tool | catalog_specialist: research_product_tool | FULL |
| Catalog queries | catalog_analyst: read_data, aggregate_data | catalog_specialist: read_data, aggregate_data | FULL |
| Schema discovery | catalog_analyst: inspect_schema | Both specialists: inspect_schema | FULL |

**Failure Scenarios:**

- PM delegates to visual_analyst for image description, then creative_specialist views image AGAIN
- PM delegates to product_analyst for research, then catalog_specialist researches AGAIN
- PM delegates to catalog_analyst for query, then catalog_specialist queries AGAIN for validation

**Core Question:** If specialists can do everything analysts can, why do analysts exist?

**Possible Answers:**
- A. Token efficiency - analysts are cheaper/faster than specialists
- B. Separation of concerns - research separate from execution
- C. Over-engineering - analysts are redundant, should be removed

**Current State:** No clear answer. Architecture doesn't commit to A, B, or C.

**Impact:** Duplicate work across layers, unclear value proposition for analyst layer

---

#### Analyst Issue #2: Passive Role Without Agency

**Problem:** Analysts defined as "read-only" but unclear what this means for decision-making.

**Evidence:**

visual_analyst prompt:
- "Report observations, not recommendations"
- "Don't suggest pricing or categorization"
- "Don't tell PM what to do next"

product_analyst prompt:
- "Come with recommendations, not questions"
- "Research and propose"
- "Be thorough - specialists depend on you"

catalog_analyst prompt:
- "Strategic advisor. Full analysis WITH recommendations"
- "Default to ANALYSIS when intent is ambiguous"

**Contradictions:**

| Analyst | Autonomy Level | Decision-Making | Recommendations |
|---------|----------------|-----------------|-----------------|
| visual_analyst | Passive observer | None allowed | Forbidden |
| product_analyst | Proactive advisor | Make recommendations | Required |
| catalog_analyst | Strategic partner | Full analysis | Required |

**Impact:** Inconsistent analyst behavior - visual is passive, product/catalog are proactive

---

#### Analyst Issue #3: Multimodal Duplication Without Coordination

**Problem:** All 3 analysts inject multimodal middleware, all can view_image, no coordination protocol.

**Evidence:**

- visual_analyst: MultimodalInjectionMiddleware + view_image tool
- product_analyst: MultimodalInjectionMiddleware + view_image tool
- catalog_analyst: MultimodalInjectionMiddleware + view_image tool
- creative_specialist: MultimodalInjectionMiddleware + view_image tool

**Failure Scenario:**

```
User sends image: "Catalog this product"

Possible flow:
1. PM downloads image (storage: inbox/...)
2. PM delegates to visual_analyst -> views image (TOKEN COST 1)
3. PM delegates to product_analyst -> views image (TOKEN COST 2)
4. PM delegates to catalog_specialist -> views image (TOKEN COST 3)
5. catalog_specialist delegates to PM for creative_specialist -> views image (TOKEN COST 4)

Same image viewed 4 times. No coordination protocol exists.
```

**Missing:**
- Protocol for "image already analyzed by X"
- Context flag: "visual_analysis_complete: true"
- Guidance: "If PM provides visual analysis, DON'T view again"

**Impact:** High token costs from multimodal duplication

---

#### Analyst Issue #4: Unbounded Research Without Escalation

**Problem:** Analysts told to research comprehensively but no iteration limits or failure thresholds.

**Evidence:**

product_analyst prompt:
- "Use research_product_tool extensively. 3-5 queries is normal for thorough research."
- "Research comprehensively so downstream specialists can execute perfectly."

**Missing:**

| Scenario | Guidance Needed | Current State |
|----------|-----------------|---------------|
| Research returns no results | Try different query? How many attempts? Escalate? | "Research comprehensively" (no bounds) |
| Low-confidence results | Keep researching? Report uncertainty? | None |
| Contradictory information | Cross-reference? Pick one? Report all? | None |
| API failures or rate limits | Retry? Give up? Escalate to PM? | None |

**Failure Scenarios:**
- product_analyst makes 10 research queries trying to find HSN code (wasteful)
- product_analyst gives up after 1 query that returns poor results (premature)
- product_analyst presents 20 conflicting sources (overwhelming)

**Impact:** Inefficient resource usage or incomplete research

---

#### Analyst Issue #5: Cross-Domain Claims Without Usage Evidence

**Problem:** All analysts claim "cross-domain reuse" but actual cross-domain usage unclear.

**Evidence:**

visual_analyst docstring:
```python
"""Cross-domain reuse:
- Catalog: Material identification, condition assessment
- Marketing: Visual quality, composition analysis
- Operations: Damage detection, quality control
- Quality: Defect identification, compliance checking
"""
```

**Questions:**
- Has visual_analyst actually been used for Operations damage detection?
- Has product_analyst been used for Procurement sourcing context?
- Are these hypothetical claims or validated use cases?

**Risk:** Over-engineering based on hypothetical future needs, not actual requirements.

**Impact:** Complexity justified by unvalidated cross-domain scenarios

---

#### Analyst Issue #6: Unclear Value vs Direct PM Tools

**Problem:** PM has same tools as analysts but unclear when to delegate vs execute itself.

**PM has:**
- view_image (overlaps visual_analyst)
- read_data (overlaps catalog_analyst)
- inspect_schema (overlaps catalog_analyst)

**Analysts have:**
- Same tools + domain expertise prompts

**Value Proposition Question:**
- Is analyst value in the prompt (domain expertise)?
- Is analyst value in separation of concerns (PM doesn't want to do research)?
- Is analyst value in token optimization (cheap analysts vs expensive PM)?

**Current State:** No clear answer. PM told "delegate problems to team" BUT also "research and propose - use your tools."

**Impact:** PM inconsistently uses own tools vs delegates to analysts

---

#### Analyst Issue #7: Output Format Inconsistency

**Problem:** Analysts return unstructured natural language, not Pydantic models.

**Evidence:**

All analyst prompts end with:
- visual_analyst: "Comprehensive observations covering everything you see. Your natural format..."
- product_analyst: "Comprehensive product intelligence tailored to the specific product..."
- catalog_analyst: "Comprehensive catalog intelligence..."

**No Pydantic Output Models Defined:**
- visual_analyst doesn't return `VisualAnalysisDraft`
- product_analyst doesn't return `ProductIntelligenceDraft`
- catalog_analyst doesn't return `CatalogAnalysisDraft`

**Impact:**
- PM must parse natural language analyst outputs
- Inconsistent output formats across analysts
- Can't programmatically access analyst findings (e.g., product_count, materials_list)
- Specialist receives unstructured context from PM

**Contrast with Specialists:**
Specialists use structured write_data with Pydantic models. Why don't analysts return structured data?

---

## Specialist Level (Layer 2): Execution Layer Issues

**CRITICAL: 8 Specialist Issues Creating Behavioral Confusion**

#### Specialist Issue #1: Autonomy Paradox

**Problem:** Specialists receive conflicting signals about self-sufficiency vs dependency on PM context.

**Evidence:**

catalog_specialist prompt says:
- "PM delegates to you for catalog operations WITH enriched context from analysts" (DEPENDENCY)
- BUT ALSO "Has research_product_tool for unknown products" (AUTONOMY)
- AND "Use read_data to check duplicates" (AUTONOMY)
- AND "If PM's context is incomplete: Use your tools to fill gaps" (AUTONOMY)

creative_specialist prompt says:
- "PM delegates image tasks with context and goals" (DEPENDENCY)
- BUT ALSO "You SEE images directly (multimodal)" (AUTONOMY)
- AND "Have image path? view_image IMMEDIATELY" (AUTONOMY)
- AND "You cannot reason about images you haven't seen" (AUTONOMY)

**Contradictory Guidance:**

| Situation | Specialist Behavior A (Dependency) | Specialist Behavior B (Autonomy) | Actual Behavior? |
|-----------|-----------------------------------|----------------------------------|------------------|
| PM gives product name only | Wait for PM to provide research | Use research_product_tool itself | AMBIGUOUS |
| PM gives image path only | Wait for PM to provide visual analysis | view_image itself | AMBIGUOUS |
| PM gives incomplete context | Report missing info to PM | Fill gaps with own tools | AMBIGUOUS |
| Schema unknown | Assume PM knows | inspect_schema itself | AMBIGUOUS |

**Impact:** Specialists exhibit unpredictable behavior - sometimes autonomous, sometimes passive

---

#### Specialist Issue #2: Research Tool Redundancy

**Problem:** catalog_specialist has research tools BUT product_analyst exists for research.

**Evidence:**

catalog_specialist tools:
- research_product_tool
- extract_web_content_tool

product_analyst tools:
- research_product_tool
- extract_web_content_tool

**Design Questions:**

| Question | Answer A | Answer B | Current State |
|----------|----------|----------|---------------|
| Why does catalog_specialist have research tools? | For self-sufficiency when PM forgets | Legacy from before product_analyst existed | NO ANSWER |
| When should catalog_specialist research? | Always - don't depend on analysts | Never - product_analyst handles research | NO ANSWER |
| What if both research the same product? | Waste but acceptable | Should be prevented | NO ANSWER |

**Failure Scenario:**
```
User: "Add coffee maker to catalog"

Flow 1 (analyst-first):
PM -> product_analyst (research) -> catalog_specialist (create)
Result: Product researched once

Flow 2 (specialist self-sufficient):
PM -> catalog_specialist (research + create)
Result: Product researched once (no analyst used)

Flow 3 (duplication):
PM -> product_analyst (research) -> catalog_specialist (re-researches because "fill gaps")
Result: Product researched TWICE
```

**Impact:** Duplicate research, inconsistent workflows

---

#### Specialist Issue #3: Schema Discovery Cognitive Load

**Problem:** Both specialists told to "explore schema" every time, adding unnecessary cognitive load.

**Evidence:**

catalog_specialist prompt:
- "inspect_schema - ESSENTIAL: Discover before you act"
- "The schema has 20+ tables... Use inspect_schema to discover"
- "Don't assume you know the schema. Explore it."

creative_specialist prompt:
- "inspect_schema / read_data: When PM provides product_id, query to find storage_url"

**Questions:**
- Should specialists inspect_schema EVERY task? (wasteful)
- Should specialists cache schema knowledge? (how?)
- Should PM provide schema context? (shifts burden)
- Should specialists assume schema knowledge from training? (breaks on schema changes)

**Failure Scenarios:**
- Specialist calls inspect_schema for every task (wasteful API calls)
- Specialist assumes schema, breaks when columns change (fragile)
- Specialist has 1000-token schema context in every prompt (token waste)

**Missing:** Strategy for schema knowledge management across specialist invocations

**Impact:** Either wasteful inspection or fragile assumptions

---

#### Specialist Issue #4: HITL Summary Ambiguity

**Problem:** Specialists told to write "plain language for business user" but no examples or schema.

**Evidence:**

catalog_specialist prompt:
- "hitl_summary goes to a BUSINESS USER, not a developer"
- "Example: 'Adding new textured jar: JAR-PET-500ML-HONEYCOMB at Rs 38 MRP. Approve?'"
- "NOT: 'Creating record in products table with product_type FINISHED_GOOD...'"

**Missing:**

| Scenario | Good HITL Summary | Bad HITL Summary | How Specialist Knows? |
|----------|-------------------|------------------|----------------------|
| Creating product family | ? | ? | No template |
| Updating pricing | ? | ? | No template |
| Creating BOM | ? | ? | No template |
| Deleting discontinued product | ? | ? | No template |

**Questions:**
- How much detail in HITL summary? (SKU + price is enough? Or full spec?)
- What if creating 5 products? (list all? Or summarize count?)
- What if complex multi-table operation? (explain FK relationships? Or hide complexity?)

**Impact:** Inconsistent HITL summaries, users don't understand what they're approving

---

#### Specialist Issue #5: Verification Without Iteration Bounds

**Problem:** creative_specialist told to "iterate until perfect" with no limits or escalation.

**Evidence:**

creative_specialist prompt:
- "VERIFY Before Delivery: view_image output, critique, SHIP IT or ITERATE"
- "Iteration is expected. First attempts rarely perfect."
- "When verification fails, iterate with specifics"

**Missing:**

| Scenario | Guidance Needed | Current State |
|----------|-----------------|---------------|
| Output fails verification | Max iterations? | "Iterate" (unbounded) |
| 3 iterations still not acceptable | Escalate to PM? Lower quality threshold? | None |
| Iteration not improving quality | Try different approach? Give up? | None |
| API rate limit during iteration | Wait? Use alternative? Escalate? | None |

**Failure Scenarios:**
- Specialist iterates 10 times, burning API credits (wasteful)
- Specialist gives up after 1 iteration (premature)
- Specialist lowers quality bar to avoid iteration (poor quality)
- Specialist iterates infinitely on impossible requirement (infinite loop)

**Impact:** Resource waste or premature failures

---

#### Specialist Issue #6: Context Handoff Schema Missing

**Problem:** "Enriched context from analysts" is undefined - no schema for what PM must include.

**Evidence:**

catalog_specialist expects:
- "PM delegates WITH enriched context from analysts"
- "Visual observations -> description, materials, colors, tags"
- "Market research -> hsn_code, positioning tier, target market"
- "Catalog analysis -> family_id, price points, variant structure"

**But:**
- No Pydantic model defining `EnrichedCatalogContext`
- No validation that PM included required fields
- No error handling if PM forgets critical context
- No examples of good vs incomplete context

**Failure Scenarios:**

| PM Context | Specialist Behavior | Impact |
|------------|-------------------|--------|
| Only image path | view_image itself (duplicates visual_analyst) | Token waste |
| Only product name | research_product_tool itself (duplicates product_analyst) | Token waste |
| Visual analysis but no HSN code | research HSN itself OR fail? | AMBIGUOUS |
| Visual + HSN but no family_id | query catalog OR ask PM? | AMBIGUOUS |

**Missing:**
- `CatalogSpecialistContext` Pydantic model
- `CreativeSpecialistContext` Pydantic model
- PM validation before delegation
- Specialist validation on receiving context

**Impact:** Specialists receive incomplete context, waste tools filling gaps PM should have provided

---

#### Specialist Issue #7: "Fill Every Field" Pressure Without Relevance Filter

**Problem:** catalog_specialist told to "fill every field" but some fields may not be relevant.

**Evidence:**

catalog_specialist prompt:
- "Fill Every Field: The schema has many fields. Analysts gave you rich context. USE IT ALL."
- "Empty fields are missed opportunities for searchability and catalog quality."
- "Explore the schema to see what fields are available - don't self-limit."

**Questions:**
- Should specialist fill optional fields even when data is uncertain? (quality vs completeness trade-off)
- Should specialist fill fields with defaults to avoid empty? (defaulting may be worse than null)
- Should specialist skip irrelevant fields? (how to determine relevance?)

**Example:**
Product: "Brass door handle"
Schema has field: `food_grade_certified` (boolean, optional)

Should specialist:
- A. Leave null (relevant only for food containers)
- B. Fill with `false` (technically accurate but misleading - implies we checked)
- C. Fill with `null` + note "N/A for hardware" (verbose)

**Missing:** Guidance on when to skip optional fields vs fill with nulls vs fill with defaults

**Impact:** Either over-filled irrelevant data or under-filled relevant data

---

#### Specialist Issue #8: Missing Escalation Protocol

**Problem:** No guidance on when specialists should escalate to PM vs keep trying themselves.

**Evidence:**

Both specialists have tools to be self-sufficient BUT also depend on PM for context.

**Escalation Scenarios (No Guidance):**

| Situation | Should Specialist... | Current Guidance |
|-----------|---------------------|------------------|
| Tool returns error | Retry? Try alternative? Escalate? | "Fill gaps with tools" (but what if tools fail?) |
| Incomplete context from PM | Fill gaps? Or ask PM? | "Use tools to fill gaps" BUT "PM delegates with context" |
| Validation fails (duplicate found) | Auto-update? Report to PM? Fail? | "Check duplicates" (but then what?) |
| Quality threshold not met after 3 iterations | Lower bar? Escalate? Give up? | "Iterate" (unbounded) |
| Conflicting requirements (user wants X, best practice is Y) | Follow user? Follow best practice? Ask? | None |

**Missing:**
- Escalation triggers ("after 3 failed attempts, escalate to PM")
- PM escalation API (how does specialist signal "need help"?)
- Error classification (retryable vs escalate-worthy vs fatal)

**Impact:** Specialists stuck in failure loops or prematurely give up

---

### Architectural Failure Modes (ULTRATHINK Analysis)

**CRITICAL: 10 Fundamental Issues Identified**

#### 1. Analyst/Specialist Boundary Confusion

**Problem:** 3-way capability overlap creates decision paralysis

**Evidence:**
- PM has: view_image, read_data, inspect_schema
- Analysts: visual_analyst (images), catalog_analyst (queries), product_analyst (research)
- Specialists: Both have same tools (view_image, read_data, research_product_tool)

**Failure Scenarios:**
- PM unclear whether to query itself vs delegate to catalog_analyst vs delegate to catalog_specialist
- catalog_analyst exists for queries BUT catalog_specialist has read_data tool
- product_analyst exists for research BUT catalog_specialist has research_product_tool
- visual_analyst describes images BUT creative_specialist can view_image itself

**Impact:** PM makes inconsistent delegation decisions, work duplicated across layers

---

#### 2. Tool Selection Ambiguity

**Problem:** Multiple tools solve same problem, no decision tree in descriptions

**Evidence:**

| Task | Tool Options | Confusion |
|------|--------------|-----------|
| Check if product exists | read_data with filter? aggregate_data count? inspect_schema first? | 3 valid approaches |
| Get product count | aggregate_data? read_data + count? | 2 valid approaches |
| Understand schema | inspect_schema always? Only when needed? Assume knowledge? | No guidance |
| View image | PM view_image? Delegate visual_analyst? Specialist view itself? | 3 layers can view |

**Failure Scenarios:**
- Specialist calls inspect_schema every time (wasteful) or never (breaks on schema changes)
- Specialist uses read_data when aggregate_data is more efficient
- Multiple agents view same image (token duplication)

**Impact:** Inefficient tool usage, wasted API calls, high token costs

---

#### 3. Context Handoff Vagueness

**Problem:** "Enriched context" undefined, no schema for PM → Specialist communication

**Current Guidance:**
- PM: "When delegating, include: image path, relevant context from analysts, specific identifiers"
- Catalog Specialist: "PM delegates WITH enriched context from analysts"
- Creative Specialist: "PM delegates with context and goals"

**Failure Scenarios:**

| PM Behavior | Specialist Expectation | Result |
|-------------|------------------------|--------|
| Delegates without visual analysis | Expects "enriched context" | Specialist must view_image itself (should PM have done this?) |
| Delegates with description but no research | Might need market data | Specialist has research tool - should it research itself? Or fail? |
| Forgets product count in multi-product image | Creative specialist extracts N products | Mismatch with user intent |
| Provides storage_path only | Should specialist view? Or trust PM? | If PM analyzed via visual_analyst, viewing again wastes tokens |

**Impact:** Specialists get incomplete context, duplicate work, or skip essential steps

---

#### 4. Multimodal Flow Chaos

**Problem:** Images viewed multiple times by different agents, no coordination protocol

**For "Catalog this product" + image, possible flows:**

```
Option A: PM-centric
PM downloads → PM view_image → PM delegates catalog_specialist with description

Option B: Analyst delegation
PM downloads → PM delegates visual_analyst → gets description → delegates catalog_specialist

Option C: Minimal PM
PM downloads → PM delegates catalog_specialist with storage_path → specialist views itself

Option D: Full pipeline
PM → visual_analyst → creative_specialist → catalog_specialist
```

**Failure:** No guidance on which flow for which scenario. Options A & B result in duplicate viewing if specialist also view_image.

**Specific Example:**
- visual_analyst returns description
- PM delegates to creative_specialist with description + storage_path
- creative_specialist prompt: "Have image path? view_image IMMEDIATELY"
- Creative views image already analyzed by visual_analyst
- Result: Duplicate token cost, redundant analysis

**Impact:** High token costs, wasted LLM calls, slow workflows

---

#### 5. Tool Description Inadequacy

**Problem:** Descriptions are feature lists, not decision guides. Missing WHEN/WHY/WHEN-NOT.

**Current view_image description:**
```
"View an image - returns actual image so LLM can SEE it.
USE WHEN: Need to see what's in image, verify outputs, compare images
NOTE: Use proactively when visual information helps"
```

**Missing:**
- WHEN NOT: If PM already provided visual analysis from visual_analyst
- COST: Viewing adds N tokens - consider if description sufficient
- COORDINATION: Check if image already analyzed upstream
- "Use proactively" conflicts with "PM delegates enriched context"

**Current research_product_tool description:**
```
"Research product using web search. Returns ProductResearchResult with confidence, sources..."
```

**Missing:**
- WHEN NOT: If product_analyst already researched (specialist has analyst output)
- THRESHOLD: What confidence score means "retry with better query" vs "accept"
- EMPTY RESULTS: Is it "product unknown" or "bad query"? How to decide?
- ALTERNATIVE: When to use vs delegating to PM to use product_analyst?

**Current read_data description:**
```
"Query any table with filtering"
```

**Missing:**
- EXAMPLES: What does "filtering" look like? Pydantic schema?
- EMPTY RESULTS: Is it "no data" or "wrong query"? How to recover?
- VS aggregate_data: When to use which?
- VALIDATION: "Use this to check duplicates before write_data"
- LIMITS: What if 1000 records returned? Should agent paginate?

**Impact:** Agents guess at tool selection, skip validation, waste resources

---

#### 6. Specialist Autonomy Confusion

**Problem:** Conflicting signals on when specialist should be self-sufficient vs escalate to PM

**Contradictory Guidance:**

Catalog Specialist:
- "PM delegates WITH enriched context from analysts" (dependency)
- "Has research_product_tool for unknown products" (autonomy)
- "Use read_data to check duplicates" (autonomy)
- "PM synthesizes findings and delegates" (dependency)

Creative Specialist:
- "PM delegates with context and goals" (dependency)
- "view_image IMMEDIATELY if you have path" (autonomy)
- "You cannot reason about images you haven't seen" (autonomy)

**Failure Scenarios:**

| Situation | Specialist Should... | But Prompt Says... | Actual Behavior? |
|-----------|---------------------|-------------------|------------------|
| PM gives product name, no details | Use research_product_tool? Or ask PM? | "PM gives enriched" AND "Has research tool" | Ambiguous |
| PM gives image path, no description | view_image itself? Or ask PM for analysis? | "PM gives context" AND "view if have path" | Ambiguous |
| Schema unknown | inspect_schema? Or assume PM knows? | "Explore schema" AND "PM provides context" | Ambiguous |
| Product not in catalog | Research online? Or tell PM "not found"? | "Fill gaps" AND "PM enriched" | Ambiguous |
| Duplicate found during write | Update existing? Report to PM? Fail? | "Check duplicates" but no guidance | Ambiguous |

**Impact:** Specialists inconsistently autonomous vs passive, unpredictable behavior

---

#### 7. Verification Without Bounds

**Problem:** "Verify and iterate" but no iteration limits or escalation protocol

**Catalog Specialist:**
- Guidance: "Understand Before Acting: inspect_schema, read_data to check duplicates, THEN write_data"
- Missing: What if duplicate found? Update? Report? Fail? How to decide?

**Creative Specialist:**
- Guidance: "VERIFY Before Delivery: view_image output, critique, SHIP IT or ITERATE"
- Missing: How many iterations? What if 3 attempts still not good enough? Report to PM or keep trying? Quality threshold?

**PM:**
- Guidance: "Research and Propose - Never Ask Without Trying"
- Missing: What if research returns nothing? How many attempts? When to ask user?

**Failure Scenarios:**
- Specialist iterates infinitely on image generation, burning API credits
- Specialist gives up after 1 attempt when 2 would have succeeded
- PM asks user immediately without trying research first
- PM researches 10 times with same query, wasting API calls

**Impact:** Resource waste (infinite loops) or premature failures (give up too early)

---

#### 8. Research Tool Redundancy

**Problem:** product_analyst exists AND catalog_specialist has research_product_tool - which to use when?

**Current Setup:**
- product_analyst: "Market intelligence and product knowledge. Delegate when: Unknown product needs research"
- catalog_specialist tools: research_product_tool, extract_web_content_tool

**Failure Scenarios:**

| User Intent | PM Routing | Actual Behavior | Inefficiency |
|-------------|------------|-----------------|--------------|
| "Research product X" | Delegates to product_analyst | Analyst uses research_product_tool | Correct |
| "Add product X to catalog" | Delegates to catalog_specialist | Specialist has research_product_tool - should it research? | Ambiguous |
| "Research and add X" | Delegates to product_analyst → then catalog_specialist | catalog_specialist might research AGAIN if product_analyst results insufficient | Duplicate research |

**Root Question:** Why does product_analyst exist if catalog_specialist can research itself?

**Options:**
A. Remove product_analyst - catalog_specialist handles own research
B. Remove research tools from catalog_specialist - always delegate to analyst
C. Keep both - define clear protocol (analyst for deep research, specialist for quick lookups)

**Impact:** Duplicate research, wasted API credits, inconsistent delegation

---

#### 9. Missing Validation Gates

**Problem:** Prompts suggest validation but no enforcement or clear failure modes

**Examples:**

Catalog Specialist says: "CRITICAL: Never create duplicates. Always verify before writing."

BUT:
- No enforcement if specialist skips read_data check
- No error handling if specialist tries to create duplicate
- No guidance on what to do if duplicate found (update? report? fail?)

Creative Specialist says: "VERIFY Before Delivery: view_image after image_studio"

BUT:
- No enforcement if specialist skips verification
- No guidance on what "acceptable quality" means
- No bounded iteration (could iterate forever)

**Failure Scenarios:**
- Specialist skips duplicate check → creates duplicate product → database error or data integrity issue
- Specialist skips output verification → delivers poor-quality image → user rejects → wasted processing
- Specialist doesn't validate schema before write → malformed data → write fails

**Impact:** Data integrity issues, poor quality outputs, wasted work

---

#### 10. Cross-Domain Workflow Coordination Gaps

**Problem:** Multi-specialist workflows have no coordination protocol

**Scenario A: "Create marketing images for product X"**

Ideal: catalog_analyst (get product) → creative_specialist (generate) → catalog_specialist (create asset records)

Failures:
- PM uses read_data itself instead of catalog_analyst (inconsistent)
- creative_specialist doesn't know product details (PM didn't pass context)
- creative_specialist creates images but catalog_specialist doesn't know they exist
- No coordination on how many images, what types, where stored

**Scenario B: "Research and add product X"**

Ideal: product_analyst (research) → catalog_specialist (create with research data)

OR: catalog_specialist (uses own research_product_tool)

Failures:
- PM unclear whether to delegate research or let specialist do it
- Duplicate research if PM delegates analyst AND specialist researches again
- catalog_specialist doesn't know product_analyst already researched (no shared state)

**Scenario C: Complex product onboarding**

Ideal: visual_analyst → product_analyst → catalog_analyst → creative_specialist → catalog_specialist

Failures:
- Each specialist views image independently (5x duplication)
- Context degradation across handoffs (catalog_specialist doesn't get visual_analyst insights)
- PM must manually shuttle data between specialists (error-prone)

**Impact:** Wasteful multi-step workflows, context loss, coordination burden on PM

---

### User-Reported Issues (TO BE ADDED)

**Please add specific behavioral issues you've observed:**

**Issue 1:**
- Behavior:
- Frequency:
- LangSmith trace:

**Issue 2:**
- Behavior:
- Frequency:
- LangSmith trace:

**Issue 3:**
- Behavior:
- Frequency:
- LangSmith trace:

---

### Anti-Patterns from Prior Attempts (TO BE FILLED)

**What mistakes did we make in iteration 1?**
- [USER INPUT]

**What mistakes did we make in iteration 2?**
- [USER INPUT]

**Why are we repeating these mistakes?**
- [USER INPUT]

---

## PART II: ROOT CAUSE ANALYSIS

### Hypothesis Validation: Mapping Failures to Root Causes

**All 6 original hypotheses are CONFIRMED. Here's the detailed mapping:**

---

#### H1: Description Overlap/Ambiguity ✓ CONFIRMED

**Maps to Failures:**
- #1: Analyst/Specialist Boundary Confusion (3-way capability overlap)
- #8: Research Tool Redundancy (product_analyst vs catalog_specialist research)
- #10: Cross-Domain Workflow Coordination Gaps (unclear who does what)

**Evidence:**
- PM has view_image, read_data, inspect_schema
- Analysts have: visual_analyst (images), catalog_analyst (queries), product_analyst (research)
- Specialists have: SAME tools (view_image, read_data, research_product_tool)
- Result: PM confused whether to do itself, delegate to analyst, or delegate to specialist

**Root Cause:** 3-way capability overlap with no clear protocol. Each layer can do same work, leading to:
- PM doing specialist work (inconsistent)
- Analysts duplicating specialist capabilities (wasteful)
- Specialists duplicating analyst work (inefficient)

---

#### H2: Tool Description Inadequacy ✓ CONFIRMED

**Maps to Failures:**
- #2: Tool Selection Ambiguity (multiple tools, no decision tree)
- #5: Tool Description Inadequacy (missing WHEN/WHY/WHEN-NOT)

**Evidence:**

| Current Description | Missing Critical Info |
|---------------------|----------------------|
| view_image: "View image, use proactively" | WHEN NOT (if PM already analyzed), COST awareness, coordination protocol |
| research_product_tool: "Research product" | Confidence thresholds, empty result handling, vs analyst alternative |
| read_data: "Query any table with filtering" | Examples, empty result recovery, vs aggregate_data, validation usage |
| inspect_schema: "Schema introspection" | When to call vs assume knowledge, caching guidance |

**Root Cause:** Tools are documented as feature lists, not decision guides. Agents must guess:
- Which tool for which scenario
- What to do with edge case results (empty, error, low-quality)
- When to use tool A vs tool B for same problem
- When NOT to use a tool

---

#### H3: Prompt Bloat/Confusion ✓ CONFIRMED

**Maps to Failures:**
- #6: Specialist Autonomy Confusion (conflicting signals)
- #7: Verification Without Bounds (vague iteration guidance)

**Evidence:**

Catalog Specialist contradictions:
- "PM delegates WITH enriched context from analysts" (dependency)
- BUT ALSO "Has research_product_tool for unknown products" (autonomy)
- AND "Use read_data to check duplicates" (autonomy)

Creative Specialist contradictions:
- "PM delegates with context and goals" (dependency)
- BUT ALSO "view_image IMMEDIATELY if you have path" (autonomy)
- AND "VERIFY Before Delivery: iterate until acceptable" (but no bounds)

**Root Cause:** Prompts contain conflicting principles:
- "Trust PM for context" vs "Fill gaps yourself"
- "Iterate until perfect" vs "Don't waste resources"
- "Be autonomous" vs "Wait for PM orchestration"

Agents receive mixed signals, behavior becomes unpredictable.

---

#### H4: Context Loss ✓ CONFIRMED

**Maps to Failures:**
- #3: Context Handoff Vagueness ("enriched context" undefined)
- #4: Multimodal Flow Chaos (images viewed multiple times)
- #10: Cross-Domain Workflow Coordination Gaps (no shared state)

**Evidence:**

PM → Specialist handoff has no schema:
- "Include: image path, relevant context from analysts, specific identifiers" (too vague)
- Catalog Specialist expects "enriched context from analysts" (but what exactly?)
- Creative Specialist expects "context and goals" (but what format?)

Result:
- PM forgets critical info (product count, user intent, constraints)
- Specialists don't know what prior agents discovered (duplicate work)
- Images viewed 3-5 times across PM/analysts/specialists (token waste)

**Root Cause:** No structured context schema. PM improvises handoffs, specialists receive incomplete data, agents can't coordinate.

---

#### H5: Wrong Granularity ✓ CONFIRMED

**Maps to Failures:**
- #1: Analyst/Specialist Boundary Confusion (analysts might be too granular)
- #8: Research Tool Redundancy (analyst exists AND specialist has tool)

**Evidence:**

**Current: 3 Analysts + 2 Specialists**
- visual_analyst: Describes images
- product_analyst: Market research
- catalog_analyst: Catalog queries

BUT:
- creative_specialist can view_image (duplicates visual_analyst)
- catalog_specialist has research_product_tool (duplicates product_analyst)
- catalog_specialist has read_data (duplicates catalog_analyst)

**Questions:**
1. Do we need analysts if specialists have same capabilities?
2. Are analysts the right granularity or should they be specialist tools?
3. Is 3-layer (PM → Analyst → Specialist) over-engineered for 2-domain system?

**Root Cause:** Unclear whether analysts are:
- A. Essential research layer (PM always delegates research to analysts)
- B. Redundant with specialist tools (remove analysts, specialists self-sufficient)
- C. Optimization for token efficiency (lightweight analysts vs heavy specialists)

Current design doesn't commit, creating ambiguity.

---

#### H6: Missing Validation Gates ✓ CONFIRMED

**Maps to Failures:**
- #7: Verification Without Bounds (no iteration limits)
- #9: Missing Validation Gates (no enforcement)

**Evidence:**

Prompts suggest validation but lack enforcement:

| Agent | Validation Guidance | Missing |
|-------|-------------------|---------|
| Catalog Specialist | "CRITICAL: Never create duplicates. Always verify before writing." | No enforcement if skipped, no guidance on duplicate found |
| Creative Specialist | "VERIFY Before Delivery: view_image output, critique, SHIP IT or ITERATE" | No iteration limit, no quality threshold, no escalation |
| PM | "Research and Propose - Never Ask Without Trying" | No attempt limit, no failure threshold |

**Failure Scenarios:**
- Specialist skips duplicate check → database error
- Specialist iterates infinitely → burns API credits
- PM gives up after 1 research attempt → premature failure
- PM researches 10 times with same query → wasted calls

**Root Cause:** Validation is suggested in prompts but not enforced. No:
- Bounded iteration (max attempts before escalation)
- Quality thresholds (what's "good enough")
- Failure protocols (what to do when validation fails)
- Escalation paths (when to involve PM or user)

---

### Confirmed Root Causes (Priority Order)

**After ULTRATHINK analysis, the 6 core issues are:**

1. **Description Overlap/Ambiguity** (H1) - 3-way capability overlap, no protocol
2. **Tool Description Inadequacy** (H2) - Missing WHEN/WHY/WHEN-NOT guidance
3. **Prompt Bloat/Confusion** (H3) - Conflicting autonomy vs dependency signals
4. **Context Loss** (H4) - No structured context schema for handoffs
5. **Wrong Granularity** (H5) - Analyst layer ambiguity (essential vs redundant?)
6. **Missing Validation Gates** (H6) - No bounded iteration or enforcement

**All 6 hypotheses validated. All 10 failure modes traced to these root causes.**

---

### Comprehensive Hypothesis Coverage Review

**VALIDATION: Do the 6 hypotheses comprehensively cover all identified issues?**

We identified **31 total issues** across the architecture:
- 6 PM-level issues
- 7 Analyst-level issues
- 8 Specialist-level issues
- 10 Architectural failure modes

**Mapping ALL 31 issues to the 6 hypotheses:**

#### H1: Description Overlap/Ambiguity - Covers 9 Issues

**PM Level:**
- PM Issue #1: Role Ambiguity (orchestrator vs executor) ✓
- PM Issue #2: Tool Ownership Without Clear Purpose ✓

**Analyst Level:**
- Analyst Issue #1: Redundant Capabilities with Specialists ✓
- Analyst Issue #6: Unclear Value vs Direct PM Tools ✓

**Specialist Level:**
- Specialist Issue #2: Research Tool Redundancy ✓

**Architectural Failure Modes:**
- Failure #1: Analyst/Specialist Boundary Confusion ✓
- Failure #2: Tool Selection Ambiguity ✓
- Failure #8: Research Tool Redundancy ✓
- Failure #10: Cross-Domain Workflow Coordination Gaps ✓

**Root:** 3-way capability overlap with no protocol for who does what when.

---

#### H2: Tool Description Inadequacy - Covers 4 Issues

**Architectural Failure Modes:**
- Failure #2: Tool Selection Ambiguity ✓
- Failure #5: Tool Description Inadequacy ✓

**Analyst Level:**
- Analyst Issue #4: Unbounded Research Without Escalation ✓

**Specialist Level:**
- Specialist Issue #3: Schema Discovery Cognitive Load ✓

**Root:** Tools documented as features, not decision guides. Missing WHEN/WHEN-NOT/COST/ALTERNATIVES.

---

#### H3: Prompt Bloat/Confusion - Covers 8 Issues

**PM Level:**
- PM Issue #1: Role Ambiguity ✓
- PM Issue #4: Delegation Logic Without Protocol ✓
- PM Issue #6: "Research and Propose" Without Bounds ✓

**Analyst Level:**
- Analyst Issue #2: Passive Role Without Agency ✓
- Analyst Issue #4: Unbounded Research Without Escalation ✓

**Specialist Level:**
- Specialist Issue #1: Autonomy Paradox ✓
- Specialist Issue #5: Verification Without Iteration Bounds ✓
- Specialist Issue #7: "Fill Every Field" Pressure Without Relevance Filter ✓

**Architectural Failure Modes:**
- Failure #6: Specialist Autonomy Confusion ✓
- Failure #7: Verification Without Bounds ✓

**Root:** Prompts contain conflicting principles creating unpredictable agent behavior.

---

#### H4: Context Loss - Covers 6 Issues

**PM Level:**
- PM Issue #3: Context Enrichment Without Schema ✓
- PM Issue #5: Multi-Step Orchestration Without Coordination ✓

**Analyst Level:**
- Analyst Issue #3: Multimodal Duplication Without Coordination ✓
- Analyst Issue #7: Output Format Inconsistency ✓

**Specialist Level:**
- Specialist Issue #6: Context Handoff Schema Missing ✓

**Architectural Failure Modes:**
- Failure #3: Context Handoff Vagueness ✓
- Failure #4: Multimodal Flow Chaos ✓
- Failure #10: Cross-Domain Workflow Coordination Gaps ✓

**Root:** No structured context schema, PM improvises handoffs, specialists receive incomplete data.

---

#### H5: Wrong Granularity - Covers 2 Issues

**Analyst Level:**
- Analyst Issue #1: Redundant Capabilities with Specialists ✓
- Analyst Issue #5: Cross-Domain Claims Without Usage Evidence ✓

**Architectural Failure Modes:**
- Failure #1: Analyst/Specialist Boundary Confusion ✓
- Failure #8: Research Tool Redundancy ✓

**Root:** Unclear whether analyst layer is essential, redundant, or optimization. Design doesn't commit.

---

#### H6: Missing Validation Gates - Covers 5 Issues

**PM Level:**
- PM Issue #6: "Research and Propose" Without Bounds ✓

**Analyst Level:**
- Analyst Issue #4: Unbounded Research Without Escalation ✓

**Specialist Level:**
- Specialist Issue #4: HITL Summary Ambiguity ✓
- Specialist Issue #5: Verification Without Iteration Bounds ✓
- Specialist Issue #8: Missing Escalation Protocol ✓

**Architectural Failure Modes:**
- Failure #7: Verification Without Bounds ✓
- Failure #9: Missing Validation Gates ✓

**Root:** Validation suggested but not enforced. No bounded iteration, quality thresholds, or escalation paths.

---

### Coverage Summary

**Total Issues Identified:** 31
- 6 PM issues
- 7 Analyst issues
- 8 Specialist issues
- 10 Architectural failure modes

**Total Issues Mapped to Hypotheses:** 31/31 ✓

**Coverage Matrix:**

| Hypothesis | Issues Covered | Percentage |
|------------|---------------|------------|
| H1: Description Overlap/Ambiguity | 9 | 29% |
| H2: Tool Description Inadequacy | 4 | 13% |
| H3: Prompt Bloat/Confusion | 8 | 26% |
| H4: Context Loss | 6 | 19% |
| H5: Wrong Granularity | 2 | 6% |
| H6: Missing Validation Gates | 5 | 16% |

**Multi-mapped Issues:** 3 issues map to multiple hypotheses (compound root causes)
- Tool Selection Ambiguity: H1 + H2
- Research Tool Redundancy: H1 + H5
- Cross-Domain Workflow Coordination: H1 + H4

**VALIDATION RESULT: ✓ COMPREHENSIVE**

The 6 hypotheses fully explain all 31 identified issues. No orphaned issues. Ready to proceed with systematic redesign addressing these root causes.

---

## PART III: ARCHITECTURAL VISION & DESIGN PRINCIPLES

### The Vision: Multi-Domain Autonomous Business Operating System

**AutifyME is not a cataloging system. It is a multi-domain autonomous business operating system.**

The system will span multiple operational domains:

- **Catalog Domain:** Product information management, inventory, pricing, manufacturing data
- **Creative Domain:** Image processing, visual asset generation, brand consistency
- **Operations Domain:** Quality control, damage detection, compliance checking, fulfillment workflows
- **Marketing Domain:** Campaign assets, product positioning, competitive analysis, content generation
- **Procurement Domain:** Supplier coordination, sourcing intelligence, cost analysis
- **Quality Domain:** Defect identification, standards compliance, testing protocols
- **Future Domains:** Customer service, analytics, forecasting, etc.

**Each domain has deep expertise. Each domain performs with utmost quality. Each domain explores possibilities autonomously.**

---

### PM Role: Strategic Orchestrator

The PM is NOT a simple router. The PM is an **intelligent multi-domain orchestrator** with strategic coordination capabilities.

**PM Responsibilities:**

1. **Analyze User Intent Across Domains**
   - Understand which domains are involved in fulfilling the request
   - Identify cross-domain dependencies and handoffs
   - Recognize complex multi-domain workflows vs single-domain tasks

2. **Coordinate Complex Multi-Domain Workflows**
   - Route tasks to appropriate domain experts with structured context
   - Manage multi-specialist coordination and data flow between domains
   - Synthesize outputs from multiple domain experts into coherent results
   - Handle workflow checkpointing and recovery for complex orchestrations

3. **Context Enrichment & Handoff Management**
   - Provide domain experts with structured, complete context
   - Shuttle necessary context between domain experts in multi-step flows
   - Maintain workflow state across domain boundaries
   - Prevent duplicate work through intelligent context passing

4. **Strategic Decision-Making**
   - Determine optimal workflow paths based on task requirements
   - Decide when to delegate vs when to use own tools for quick lookups
   - Recognize when to run domain experts sequentially vs in parallel
   - Escalate to user when ambiguity cannot be resolved autonomously

**PM is NOT:**

- A passive message router
- A domain expert itself (doesn't perform deep domain work)
- A micromanager (doesn't dictate how domain experts execute)
- Limited to single-domain orchestration

---

### Subagent Role: Explorative Domain Expert

Subagents are **NOT workflow executors following rigid recipes.** They are **autonomous domain masters** who explore possibilities, iterate for quality, and deliver portfolio-worthy outputs.

**Subagent Characteristics:**

1. **Deep Domain Mastery**
   - Each subagent owns a domain with full tool access for that domain
   - Thinks in domain-specific vocabulary and patterns (e.g., "SKU architecture" for catalog, "light and composition" for creative)
   - Applies world-class judgment within domain boundaries
   - Knows industry standards, best practices, and quality thresholds for their domain

2. **Explorative Problem-Solving** (Explore → Reason → Output)
   - **FIRST: Explore comprehensively** - inspect schema, query data, research context, view images, validate prerequisites across ALL relevant areas
   - **THEN: Reason deeply** - analyze findings, synthesize patterns, identify gaps, evaluate options, make informed decisions
   - **FINALLY: Output intelligently** - return findings shaped by exploration, not pre-defined templates
   - Uses full range of available tools autonomously to discover what's needed
   - Iterates on outputs until quality standards are met

3. **Quality-First Execution**
   - Every output is portfolio-worthy, immediately publishable
   - Self-verification before returning results (e.g., view_image after image_studio, read_data to check duplicates)
   - Bounded iteration with clear quality thresholds and escalation protocols
   - Fills every relevant field, uses all available context, maximizes catalog/asset quality

4. **Intelligent Communication**
   - Returns domain intelligence shaped by explorative discovery (not rigid schemas)
   - For larger outputs, uses filesystem tool (DeepAgents default capability) for persistence
   - Provides complete, actionable findings that PM can route to other domains
   - Flags gaps, uncertainties, and recommendations clearly
   - Escalates to PM when hitting domain boundaries or unresolvable blockers

**Subagents are NOT:**

- Passive executors waiting for PM to provide everything
- Limited to narrow, scripted workflows
- Siloed from other domains (they understand cross-domain context)
- Allowed to produce mediocre outputs ("good enough" is not acceptable)

---

### Critical Design Questions

**Before proceeding with systematic redesign, we must answer these 3 architectural questions:**

---

#### Q1: PM's Intelligence Level

**What level of intelligence should the PM operate at?**

##### Option A: Strategic Orchestrator (RECOMMENDED)

- PM analyzes user intent, identifies involved domains, coordinates multi-domain workflows
- PM makes routing decisions based on task complexity and domain requirements
- PM uses own tools strategically for quick validations/lookups that inform routing
- PM enriches context through analyst delegation or direct tool use (whichever is optimal)
- PM synthesizes multi-domain outputs into coherent user-facing results

##### Option B: Workflow Coordinator

- PM follows established workflow patterns (analyst → specialist pipelines)
- PM shuttles data between predefined workflow stages
- PM delegates based on task type classification
- Limited strategic decision-making (follows templates)

##### Option C: Minimal Router

- PM parses user request into domain + task
- PM delegates immediately to appropriate domain expert with minimal preprocessing
- Domain experts are fully self-sufficient (no analyst layer, no PM tools)
- PM just aggregates results

**DECISION: Option A - Strategic Orchestrator**

PM is an intelligent coordinator analyzing intent, making strategic routing decisions, enriching context optimally, and synthesizing multi-domain results.

---

#### Q2: Domain Expert Autonomy Boundaries

**How autonomous should domain experts be within their domain?**

##### Option A: Bounded Autonomy with Intelligent Escalation (RECOMMENDED)

- Domain experts autonomous for standard execution within domain boundaries
- Use full tool access to explore, validate, research, and iterate
- Escalate to PM when:
  - Hitting domain boundaries (need cross-domain coordination)
  - Multiple iterations don't meet quality threshold (need requirement clarification)
  - Ambiguous requirements require business judgment (user input needed)
  - Tool failures or missing prerequisites block progress
- Clear escalation triggers and protocols defined

##### Option B: Always Autonomous

- Domain experts never escalate, always make decisions themselves
- Fill gaps through research and best-guess inference
- Risk: wrong assumptions, no user input even when needed

##### Option C: Escalate Immediately

- Domain experts report back to PM for any missing context or decision point
- PM must provide complete specifications before domain expert acts
- Risk: chatty workflows, PM becomes bottleneck

**DECISION: Option A - Bounded Autonomy with Intelligent Escalation**

Domain experts are autonomous within domain boundaries, use full tool access for exploration/validation/iteration, and escalate intelligently when hitting domain limits, quality thresholds, or ambiguous requirements.

---

#### Q3: Multi-Domain Coordination Pattern

**How should PM coordinate workflows spanning multiple domains?**

##### Option A: Dynamic Coordination (RECOMMENDED)

- PM analyzes task requirements and determines optimal execution pattern
- Can run domains sequentially (when B depends on A's output)
- Can run domains in parallel (when independent)
- Can chain domains dynamically based on intermediate results
- PM maintains workflow state and manages handoffs

##### Option B: Parallel First

- PM always delegates to all relevant domains simultaneously
- Domains self-coordinate through shared context
- Risk: domains may duplicate work or conflict

##### Option C: Sequential Pipeline

- PM always runs domains in fixed order (analysts → specialists)
- Predictable but potentially inefficient for simple tasks

**DECISION: Option A - Dynamic Coordination**

PM analyzes task requirements and determines optimal execution pattern - sequential when dependencies exist, parallel when independent, dynamically chained based on intermediate results. PM maintains workflow state and manages handoffs.

---

### From First Principles

**P1: Intelligence-First Design**
- Trust LLM reasoning over rigid control
- Give agents problems + context, not steps
- Rich context enables autonomy

**P2: Clear Boundaries Through Purpose**
- Each agent/tool answers: "What problem do I solve?"
- Overlap is acceptable when domains naturally intersect
- Boundaries = domain coherence, not artificial separation

**P3: Descriptions Are Navigation**
- Descriptions help agents CHOOSE correctly
- Include: WHEN to use, WHEN NOT to use, what you get
- Signal overlap explicitly ("Also consider X if...")

**P4: Context Flow Is Explicit**
- What context does PM pass to specialists?
- What context do tools need to succeed?
- What context do tools return that agents can use?

**P5: Fail-Fast with Actionable Errors**
- Tools validate inputs and return structured errors
- Error messages guide agents to correct action
- Agents can recover without PM intervention

**P6: Verification Over Hope**
- Agents verify before acting (duplicates, schema, prerequisites)
- Specialists verify outputs (view_image after image_studio)
- Multi-step validation gates prevent cascading failures

### Specific Design Rules (TO BE REFINED)

**For Specialist Descriptions:**
- [ ] Start with domain ownership (catalog, creative, etc.)
- [ ] "DELEGATE WHEN:" with 3-5 concrete scenarios
- [ ] "DOES NOT:" to clarify boundaries
- [ ] "REQUIRES:" for prerequisites (HITL, context, etc.)

**For Tool Descriptions:**
- [ ] Start with purpose (one-line problem statement)
- [ ] "USE WHEN:" with specific triggers
- [ ] "DON'T USE WHEN:" to prevent misuse
- [ ] "RETURNS:" with what agents get and how to use it
- [ ] "NEEDS:" for required context/inputs

**For Agent Prompts:**
- [ ] Identity: domain expert voice (photographer, architect, analyst)
- [ ] Capabilities: tool inventory with when/why
- [ ] Principles: decision-making heuristics (2-4 rules)
- [ ] Examples: canonical scenarios showing reasoning process

---

## PART IV: SYSTEMATIC REDESIGN PLAN

### Phase 1: Stabilize Tool Descriptions (Week 1)

**Goal:** Every tool description enables correct selection

**Tasks:**
1. Audit all tools (platform, research, image, data engine)
2. Rewrite descriptions using template: PURPOSE / USE WHEN / DON'T USE / RETURNS / NEEDS
3. Add explicit boundaries between similar tools
4. Test with PM: can it distinguish tools from descriptions alone?

**Validation Gate:** PM in test scenario correctly selects tools 90%+ of time

### Phase 2: Clarify Specialist Boundaries (Week 1)

**Goal:** PM delegates to correct specialist with right context

**Tasks:**
1. Rewrite specialist descriptions (catalog_specialist, creative_specialist)
2. Add explicit handoff contract (what context PM must provide)
3. Surface specialist prompts to align with new descriptions
4. Document PM -> Specialist context flow

**Validation Gate:** PM delegates correctly in 10 test scenarios

### Phase 3: Refine Specialist Prompts (Week 2)

**Goal:** Specialists use tools effectively and verify outputs

**Tasks:**
1. Audit specialist prompts for bloat and confusion
2. Align capabilities section with actual tools
3. Add verification principles (check before write, verify after create)
4. Prune conflicting or redundant guidance

**Validation Gate:** Specialists complete tasks correctly in 10 test scenarios

### Phase 4: PM Prompt Refinement (Week 2)

**Goal:** PM orchestrates intelligently without overstepping

**Tasks:**
1. Clarify delegation triggers (analyst vs specialist)
2. Strengthen "Research and Propose" behavior
3. Add context enrichment guidance
4. Prune any PM tool usage conflicts

**Validation Gate:** PM end-to-end flow in 15 test scenarios

### Phase 5: Validation & Regression Testing (Week 3)

**Goal:** Confirm no regressions, document learnings

**Tasks:**
1. Run autonomous testing suite on redesigned system
2. Compare traces to prior iterations
3. Document what changed and why
4. Create "Redesign Retrospective" to prevent iteration 4

---

## PART V: EXECUTION LOG

### Changes Made

**[Date] - [Component] - [Change]**
- Description of change
- Rationale
- Validation result

---

## PART VI: RETROSPECTIVE (Post-Completion)

### What We Fixed

### What We Learned

### Prevention for Future Iterations

**Canonical patterns to always follow:**
**Red flags that indicate we're drifting:**

---

## APPENDIX: Templates

### Tool Description Template

```
[One-line purpose statement]

USE WHEN:
- Scenario 1
- Scenario 2
- Scenario 3

DON'T USE WHEN:
- Wrong scenario 1
- Wrong scenario 2
- Use [alternative_tool] instead if [condition]

RETURNS:
- What you get
- How to use it
- Example: [concrete example]

NEEDS:
- Required context/input 1
- Required context/input 2
```

### Specialist Description Template

```
[Specialist Name] - [Domain ownership statement]

DELEGATE WHEN:
- Task scenario 1
- Task scenario 2
- Task scenario 3

DOES NOT: [Clarify boundaries - what this specialist doesn't do]
REQUIRES: [Prerequisites - HITL, context, etc.]
```

### Agent Prompt Template

```
<identity>
You are a [domain expert archetype] who [expertise statement].
You think in [domain vocabulary and patterns].

PM delegates to you for [domain tasks] WITH [expected context].
You focus on [core responsibility].
</identity>

<capabilities>
**tool_name** - [Purpose]
[When to use, what it does, what you get]
</capabilities>

<principles>
## Principle 1: [Name]
[Decision-making heuristic - how to think about this domain]

## Principle 2: [Name]
[Guideline for effective execution]
</principles>

<example scenario="[Canonical task]">
<input>PM delegation with context</input>
<reasoning>How expert thinks through the problem</reasoning>
<actions>Tool calls with intent</actions>
<output>What specialist returns to PM</output>
</example>
```
