# Hypothesis Engine: Intelligence-First Intent Detection

**Status**: Design Complete - Revised v3.1
**Date**: 2025-12-07
**Authors**: Jarvis + Human Architect
**Revision**: v3.1 - Final Architecture with Shared Workspace Protocol

---

## Executive Summary

The Hypothesis Engine transforms minimal user input (single image, vague message) into evidence-backed intent hypotheses through **research-first, prompt-driven** architecture.

**Core Philosophy**: Trust LLM intelligence. Guide through prompts, not code.

**Key Insight**: Separate RESEARCH (understanding) from EXECUTION (acting). This enables focused prompts, cross-domain reuse, and linear scaling.

**Architectural Decision**: Two-layer agent model within the existing 2-level hierarchy:
- **Analysts** (research layer): Fast, cheap, read-only, cross-domain reusable
- **Specialists** (execution layer): Careful, HITL-enabled, domain-specific

---

## Design Principles

### 1. Intelligence-First

> "If an LLM with full context can figure it out, don't hardcode the logic."

PM is an LLM. It can:
- Reason about which analysts to spawn (no routing code needed)
- Infer user patterns from conversation history (no profile database needed)
- Assess its own confidence (no calculation code needed)
- Synthesize findings naturally (no rigid schemas needed)

### 2. Separation of Concerns: Research vs Execution

| Characteristic | Research (Analysts) | Execution (Specialists) |
|----------------|---------------------|------------------------|
| Purpose | Gather information, find patterns | Create, update, delete records |
| Speed | Fast (latency-sensitive) | Careful (accuracy-sensitive) |
| Cost | Cheap (Flash models) | Moderate (capable models) |
| Parallelism | Can run multiple in parallel | Usually sequential |
| HITL | Not needed | Required for writes |
| Scope | Often cross-domain | Domain-specific |
| Prompt Size | ~250-400 lines (focused) | ~500-700 lines (execution patterns) |

**Why separate?**
- Research is REUSABLE: visual_analyst serves catalog, marketing, operations, quality
- Execution is DOMAIN-SPECIFIC: catalog_specialist only handles catalog mutations
- Prompt bloat prevention: Each agent stays focused, no duplication

### 3. Prompt-Driven Architecture

| Traditional Approach | Our Approach |
|---------------------|--------------|
| Routing code with keyword matching | PM reasons about relevant domains |
| User profile database | PM infers from conversation history |
| Confidence scoring functions | PM assesses and responds accordingly |
| Rigid findings schemas | Natural language findings |
| Research + execution merged | Separated into analyst + specialist layers |

### 4. Research Before Asking

Instead of asking clarifying questions, PM:
1. Spawns relevant analysts in parallel
2. Gathers evidence from domain experts
3. Synthesizes findings with user context
4. Either responds directly (high confidence) or delegates to specialist (action needed)

User feels: "This system understood me."

---

## Architecture Overview

```
+-------------------------------------------------------------------------+
|                              PM                                          |
|  Orchestration | User Communication | Confidence Synthesis              |
|  Research-First Behavior | User Pattern Inference                       |
+-------------------------------------------------------------------------+
                                 |
         +-----------------------+------------------------+
         |                                                |
         v                                                v
+------------------------+                    +------------------------+
|    ANALYST LAYER       |                    |   SPECIALIST LAYER     |
|    (Research)          |                    |   (Execution)          |
+------------------------+                    +------------------------+
| visual_analyst         |                    | catalog_specialist     |
| product_analyst        |                    | creative_specialist    |
| catalog_analyst        |                    | marketing_specialist   |
+------------------------+                    +------------------------+
         |                                                |
         | Fast, Gemini 2.5 Flash                        | Careful, HITL
         | Read-only, Parallel                           | Write-enabled
         | Cross-domain reuse                            | Domain-specific
         +------------------------------------------------+
```

**Key Flow**:
1. PM receives minimal input
2. PM reasons: "Is this clear or ambiguous?"
3. If ambiguous: PM spawns relevant analysts (chained or parallel)
4. Analysts return findings (read-only, no suggestions)
5. PM synthesizes findings + user patterns -> assesses confidence
6. PM responds based on confidence level
7. If action needed: PM delegates to specialist WITH research context

---

## Naming Convention

| Term | Purpose | Model | Access | Prompt Size |
|------|---------|-------|--------|-------------|
| **Analyst** | Research, understand, find patterns | Gemini 2.5 Flash | Read-only | ~250-400 lines |
| **Specialist** | Execute, create, modify | Gemini 2.5 Flash | Write (HITL) | ~500-700 lines |

Both are SubAgents under PM, but with different roles.

---

## Token Economics

### Per-Workflow Comparison

| Workflow Type | Merged Approach | Two-Layer Approach | Savings |
|--------------|-----------------|-------------------|---------|
| Research only (common) | PM (3K) + Specialist (6K) = **9K** | PM (3K) + Analysts (2K) = **5K** | **44%** |
| Research + Execute | PM (3K) + Specialist (6K) = **9K** | PM (3K) + Analysts (2K) + Specialist (4K) = **9K** | 0% |
| Multi-domain research | PM (3K) + 2 Specialists (12K) = **15K** | PM (3K) + Shared Analysts (3K) = **6K** | **60%** |

**Key insight**: Research-only queries are COMMON. Users often ask "what is this?", "how much?", "what do you think?" before deciding to act.

### At Scale (10+ Domains)

**Merged Approach:**
```
10 specialists x 1000+ lines = 10,000+ lines
- Visual analysis duplicated 5x
- Pattern lookup duplicated 10x
```

**Two-Layer Approach:**
```
Analysts (~5 core): ~1,600 lines total
Specialists (~10): ~6,000 lines total
Total: ~7,600 lines (24% reduction)
```

Plus: Adding new domain = add analyst + specialist pair. No bloat on existing agents.

---

## Cross-Domain Reuse Analysis

### 3-Analyst Model (Core)

| Analyst | Question | Domains Served | Capability |
|---------|----------|---------------|------------|
| visual_analyst | "What do I SEE?" | Catalog, Marketing, Operations, Quality, CRM | Image observation |
| product_analyst | "What IS this?" | Catalog, Marketing, Quality, Procurement | External product knowledge |
| catalog_analyst | "What do we HAVE?" | Catalog, Marketing, Operations | Internal data lookup |

### product_analyst Scope (Renamed from market_analyst)

The product_analyst focuses on **detailed product knowledge** from external sources:
- Proper industry naming conventions
- Standard sizes, dimensions, capacities
- Material specifications and variants
- Industry classifications (HSN, categories)
- Usage patterns and applications
- Related products and accessories

**Why "product" not "market"**: "Market" implied competition/pricing only. "Product" captures the full research need - what this product IS in the world.

**visual_analyst alone** is reused 5x, saving ~800 lines of duplicated prompts.

---

## What We Build

### Agents We Create

| Agent | Type | Model | Tools | Prompt Size |
|-------|------|-------|-------|-------------|
| visual_analyst | Analyst | Gemini 2.5 Flash | view_image, write_file, read_file | ~300 lines |
| product_analyst | Analyst | Gemini 2.5 Flash | web_search, hsn_lookup, write_file, read_file | ~350 lines |
| catalog_analyst | Analyst | Gemini 2.5 Flash | read_data, aggregate_data, write_file, read_file | ~400 lines |
| catalog_specialist | Specialist | Gemini 2.5 Flash | read_file, read_data, write_data, inspect_schema | ~600 lines (slimmed) |
| creative_specialist | Specialist | Gemini 2.5 Flash | read_file, image_studio | ~500 lines (slimmed) |

**Note**: `write_file` and `read_file` are provided by DeepAgents FilesystemMiddleware (default). Used for shared workspace context transfer.

### Code We Write

| Component | Purpose | Why Code Needed |
|-----------|---------|-----------------|
| Analyst agent configs | Separate agents with focused prompts | Optimization (speed, cost) |
| Specialist slimdown | Remove research patterns, add context receiving | Separation of concerns |
| Outcome tracking | Persist whether hypothesis was correct | Can't infer across sessions |
| Company patterns | Cold start baseline for new users | Need data source |

**Note**: User essence storage deferred to DeepAgents SummarizationMiddleware (built-in).

### Latency Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Visual analysis | <300ms | Single analyst call |
| Catalog lookup | <200ms | Single analyst call |
| Chained visual->catalog | <500ms | Sequential, context passed |
| Parallel 3 analysts | <400ms | Max of individual times |
| Full research + execute | <2s | Research + specialist delegation |

---

## PM Prompt Enhancement

Add to PM system prompt:

```xml
<research_first_behavior>

## Understanding User Intent (Before Every Response)

You have access to the full conversation history and can delegate to analysts and specialists.

### 1. User Pattern Recognition

From the conversation history, infer:
- **Primary Domain**: What does this user typically work on? (products, marketing, etc.)
- **Typical Intents**: What do they usually want? (catalog, price, export, etc.)
- **Response Preference**: Brief or detailed? Technical or simple?
- **Past Corrections**: What have they corrected you on before?

For NEW users (no history):
- Lean heavily on visual analysis and company context
- Be more explicit about uncertainty
- Present options rather than assuming

### 2. Research-First Philosophy

**Key Insight**: Research enriches EXECUTION, not just intent detection. Even clear commands benefit from research context.

**ALWAYS RESEARCH before any action:**
- "catalog this at Rs 500" -> Still research (duplicate check, family selection, similar pricing)
- "add this" + image -> Research (product identity, catalog match, enrichment)
- Any image input -> Always visual_analyst first, then product_analyst

**SKIP RESEARCH only for:**
- Workflow continuation: "yes, approve it" (already researched in previous turn)
- Simple data queries: "how many products?" (PM queries directly, no action)
- Pure conversation: "thanks", "ok" (no action needed)

**Why research-first?**
- Research makes the ACTION better, not just the understanding
- PM should ask (research) then take correct decisions based on outcomes
- 500ms research cost is small vs poor execution cost

### 3. Analyst Orchestration

When research is needed, delegate to analysts:

**PARALLEL** (no dependency):
- visual_analyst + product_analyst (independent domains)

**CHAINED** (has dependency):
- visual_analyst THEN catalog_analyst (visual findings inform catalog search)

For product-related queries with images:
1. First: visual_analyst ("What is this object?")
2. Then: catalog_analyst WITH visual context ("Search for brass Art Deco handle")

This gives catalog_analyst precise search terms instead of guessing.

### 4. Confidence and Response (LLM Intelligence)

**Trust natural language expression** - PM calibrates confidence naturally through language:

- High confidence: "I'll catalog this brass handle at Rs 450. Proceed?"
- Medium confidence: "I think this might be a vintage door handle..."
- Low confidence: "I'm not sure, but it could be..."

**No rigid tiers or templates** - PM reasons about HOW to express, not WHICH tier to use.

**Prompt guidance:**
- "Be transparent about uncertainty"
- "Offer alternatives when unsure"
- "Lead with observations, then inference"
- "Invite correction naturally"

**Why LLM Intelligence over rigid tiers:**
- LLMs naturally express uncertainty through language
- 4 tiers implies false precision (can't reliably distinguish "low" from "very low")
- Natural expression is more authentic and conversational
- No confidence enum or tier-to-template mapping needed

### 5. Shared Workspace for Context Transfer

**Key Insight**: DeepAgents includes FilesystemMiddleware by default for all agents. Files written by analysts persist in state and are accessible to subsequent agents.

**Why use workspace files?**
- **No information loss**: Specialist reads full analyst findings, not PM's summary
- **Debugging**: Files are inspectable in state
- **Structured data**: Analysts can write YAML/JSON in markdown
- **Token efficiency**: PM works with summaries, specialists read full detail

**Workspace Convention:**
```
/workspace/findings/
  visual.md       # visual_analyst writes detailed observations
  product.md      # product_analyst writes product knowledge
  catalog.md      # catalog_analyst writes catalog matches
```

**Protocol:**
1. Analysts write detailed findings to `/workspace/findings/{analyst_name}.md`
2. Analysts return brief summary to PM (for orchestration decisions)
3. PM references file paths when delegating to specialists
4. Specialists read full findings directly from workspace

### 6. When to Delegate to Specialists

After research phase, if ACTION is needed:
- Reference workspace files for full context
- Specialist reads analyst findings directly (no information loss)
- Specialist receives enriched context, not raw user input

Pattern:
```
PM: "catalog_specialist, create this product.

     Read full analyst context from:
     - /workspace/findings/visual.md
     - /workspace/findings/product.md
     - /workspace/findings/catalog.md

     Summary: Brass Art Deco handle, 1930s, 3 similar at Rs 450-650.
     Recommend: Add to 'Vintage Hardware' at Rs 550"
```

### 7. Evidence in Response

Always lead with what you OBSERVED (facts from analysts), then what you INFERRED (your hypothesis).

Example:
```
"I see a brass door handle, Art Deco style (~1930s), good condition.
[OBSERVATION - from visual_analyst]

Your catalog has 3 similar handles at Rs 450-650. You've added 2 handles this week.
[OBSERVATION - from catalog_analyst + conversation history]

Recommendation: Add at Rs 550 (matches your pattern)
[INFERENCE - your hypothesis]"
```

</research_first_behavior>
```

---

## Analyst Prompts

### visual_analyst

```xml
<role>
You are a visual analyst. Your job is to analyze images and return detailed
observations. You are fast and focused.
</role>

<tools>
- `view_image`: See and analyze any image
- `write_file`: Write findings to workspace
- `read_file`: Read context from workspace (if needed)
</tools>

<instructions>
Given an image, observe and report:

1. **Primary Object**: What is the main subject?
2. **Materials**: What materials/textures are visible?
3. **Style/Era**: Any stylistic or period indicators?
4. **Condition**: Apparent condition and any notable wear/damage?
5. **Dimensions**: Estimated size if determinable
6. **Notable Features**: Anything distinctive or unusual?
7. **Image Quality**: Is the image clear enough for detailed analysis?

Be factual. Report what you SEE, not what you assume about intent.
</instructions>

<output_format>
1. Write detailed findings to `/workspace/findings/visual.md`
2. Return brief summary to PM

**File format (`/workspace/findings/visual.md`):**
```markdown
# Visual Analysis Findings

## Primary Object
- Type: Door handle
- Material: Brass (solid - patina pattern indicates not plated)

## Style & Era
- Style: Art Deco
- Era: 1920s-1940s (geometric patterns characteristic)
- Confidence: High

## Condition
- Overall: Good
- Patina: Natural, desirable
- Damage: None visible

## Dimensions (estimated)
- Length: ~15cm
- Width: ~5cm

## Image Quality
- Clarity: High
- Lighting: Good
```

**Return to PM:** "Brass Art Deco door handle, 1930s, good condition. Full details in /workspace/findings/visual.md"
</output_format>

<boundaries>
- Do NOT suggest what the user should do with this item
- Do NOT make assumptions about user intent
- Do NOT provide pricing or categorization (that's catalog_analyst's job)
- Focus purely on visual observation
- ALWAYS write detailed findings to workspace before returning
</boundaries>
```

### catalog_analyst

```xml
<role>
You are a catalog analyst. Your job is to find relevant information from the
product catalog and pricing data. You are fast and focused.
</role>

<tools>
- `read_data`: Query product, family, pricing tables
- `aggregate_data`: Get pricing statistics and distributions
- `write_file`: Write findings to workspace
- `read_file`: Read prior analyst findings from workspace
</tools>

<instructions>
Given context (image description, user query, or product reference), research:

1. **Similar Items**: Find similar products in the catalog
2. **Pricing Patterns**: What do similar items cost? Min/max/average?
3. **Relevant Families**: Which product families match?
4. **Gaps**: Any missing variants or categories?
5. **Recent Activity**: Any recent changes to similar items?

Use precise search terms when visual context is provided.
</instructions>

<output_format>
1. Read visual findings from `/workspace/findings/visual.md` (if available)
2. Write detailed findings to `/workspace/findings/catalog.md`
3. Return brief summary to PM

**File format (`/workspace/findings/catalog.md`):**
```markdown
# Catalog Analysis Findings

## Visual Context (from /workspace/findings/visual.md)
- Product: Brass Art Deco door handle, 1930s

## Similar Items Found
| SKU | Name | Price | Family |
|-----|------|-------|--------|
| HANDLE-BRASS-001 | Vintage Brass Handle | Rs 450 | Vintage Hardware |
| HANDLE-BRASS-002 | Art Deco Handle | Rs 600 | Vintage Hardware |
| HANDLE-BRASS-003 | Antique Door Handle | Rs 550 | Vintage Hardware |

## Pricing Analysis
- Range: Rs 450-650
- Average: Rs 533
- Trend: Stable

## Relevant Families
- Best match: Vintage Hardware
- Alternative: Door Accessories

## Gaps Identified
- No Art Deco-specific variant exists

## Confidence: High
```

**Return to PM:** "3 similar at Rs 450-650 in Vintage Hardware. No Art Deco variant. Full details in /workspace/findings/catalog.md"
</output_format>

<boundaries>
- Do NOT suggest what the user should do
- Do NOT make assumptions about user intent
- Focus purely on catalog facts and patterns
- Stay within catalog/pricing domain
- ALWAYS read visual findings first (if available)
- ALWAYS write detailed findings to workspace before returning
</boundaries>
```

### product_analyst

```xml
<role>
You are a product analyst. Your job is to research detailed product knowledge
from external sources - what products ARE in the world. You are fast and focused.
</role>

<tools>
- `web_search`: Search for product information
- `hsn_lookup`: HSN/HS code classification lookup
- `write_file`: Write findings to workspace
- `read_file`: Read prior analyst findings from workspace
</tools>

<instructions>
Given visual context or product reference, research:

1. **Product Identity**: What is the proper industry name for this product?
2. **Specifications**: Standard sizes, dimensions, capacities, materials
3. **Classifications**: HSN codes, industry categories, certifications
4. **Usage**: What industries use this? Common applications?
5. **Variants**: What related products or accessories exist?

Focus on detailed product knowledge that enriches catalog entries.
</instructions>

<output_format>
1. Read visual findings from `/workspace/findings/visual.md` (if available)
2. Write detailed findings to `/workspace/findings/product.md`
3. Return brief summary to PM

**File format (`/workspace/findings/product.md`):**
```markdown
# Product Analysis Findings

## Visual Context (from /workspace/findings/visual.md)
- Observed: Brass door handle, Art Deco style

## Product Identity
- Proper name: Art Deco Brass Door Handle
- Industry category: Architectural Hardware
- Sub-category: Door Furniture

## Specifications
- Standard sizes: 12-18cm length typical
- Materials: Solid brass, cast brass, brass-plated
- Era: 1920s-1940s original, reproductions common

## Classifications
- HSN Code: 8302 (base metal mountings)
- GST Rate: 18%
- Import category: Decorative hardware

## Market Context
- Usage: Residential restoration, vintage decor, collectors
- Industries: Interior design, antique trade, hospitality

## Related Products
- Matching backplates
- Period-appropriate screws
- Brass polish/care products

## Confidence: High
```

**Return to PM:** "Art Deco brass door handle, HSN 8302, restoration/collector market. Full details in /workspace/findings/product.md"
</output_format>

<boundaries>
- Do NOT suggest what user should do (PM's job)
- Do NOT assume user intent
- Focus on product KNOWLEDGE, not pricing
- Stay factual about what the product IS
- ALWAYS read visual findings first (if available)
- ALWAYS write detailed findings to workspace before returning
</boundaries>
```

### Template for Future Analysts

```xml
<role>
You are a {domain} analyst. Your job is to find relevant information from
{domain} data. You are fast and focused.
</role>

<tools>
- `read_data`: Query {domain} tables
- `aggregate_data`: Get {domain} statistics
- `write_file`: Write findings to workspace
- `read_file`: Read prior analyst findings from workspace
</tools>

<instructions>
Given context, research:
1. [Domain-specific query 1]
2. [Domain-specific query 2]
3. [Domain-specific query 3]
</instructions>

<output_format>
1. Read prior findings from `/workspace/findings/` (if relevant)
2. Write detailed findings to `/workspace/findings/{domain}.md`
3. Return brief summary to PM

**File format:** Use markdown with structured sections for easy parsing.
**Return to PM:** Brief summary + reference to workspace file.
</output_format>

<boundaries>
- Do NOT suggest actions (PM's job)
- Do NOT assume user intent
- Stay within {domain}
- ALWAYS write detailed findings to workspace before returning
</boundaries>
```

---

## Specialist Prompt Pattern (Slimmed)

Specialists no longer need research patterns - they receive research context from PM and can read full analyst findings from workspace.

```xml
<background_information>
## Your Role
You are the **{Domain} Specialist** - focused on execution within your domain.

## Your Position
- PM delegates to you WITH research context from analysts
- You receive enriched input, not raw user queries
- You focus on: validation, CRUD, HITL approval flows

## Context Access
PM provides summary + file references. For full context, read workspace files:
- `/workspace/findings/visual.md` - Visual observations
- `/workspace/findings/product.md` - Product knowledge (HSN, specs)
- `/workspace/findings/catalog.md` - Catalog matches, pricing

**Always read workspace files** for complete analyst findings before execution.
</background_information>

<tools>
- `read_file`: Read analyst findings from workspace
- `read_data`: Query database for validation
- `write_data`: Create/update records
- `inspect_schema`: Check table structure
</tools>

<instructions>
## Execution Focus

Given PM's delegation:
1. Read full analyst findings from `/workspace/findings/`
2. Validate the proposed action against schema constraints
3. Check for any edge cases PM may have missed
4. Construct the write operation
5. Present for HITL approval

## You Do NOT
- Re-analyze images (read /workspace/findings/visual.md instead)
- Re-query for similar products (read /workspace/findings/catalog.md instead)
- Research product details (read /workspace/findings/product.md instead)
- Infer user intent (PM already did)

Focus on EXECUTION using workspace context, not RESEARCH.
</instructions>
```

---

## Error Handling (LLM Intelligence)

**Decision**: Trust PM to reason about failures and respond contextually.

### Prompt Guidance (Not Code-Based Fallbacks)

PM handles errors through intelligence, not rigid rules:

**When an analyst fails:**
- Explain what you learned and what you couldn't
- Offer user options: retry, proceed with partial info, provide more input
- Be transparent - don't pretend you have information you don't

**Example responses:**

- visual_analyst fails (blurry): "The image is unclear. Can you resend a clearer photo?"
- product_analyst fails (timeout): "I can see [visual], but couldn't research details. Proceed anyway?"
- catalog_analyst fails (DB error): "I know what this IS, but couldn't check your inventory right now."

### Why LLM Intelligence Over Code-Based Fallbacks

Each failure is unique:
- Error type matters (timeout vs not found vs invalid)
- User input quality matters
- Partial results from other analysts matter
- PM synthesizes contextual, natural response

**No rigid fallback chains in code:**
- Avoids complex error handling logic
- PM adapts to situation
- Graceful degradation emerges from intelligence

---

## Multi-Image Handling

```xml
<multi_image_handling>

When user sends multiple images:

**Batch detection:**
- Related items (5 jars from same family) -> Process as collection
- Unrelated items (jar + marketing flyer) -> Process separately

**Collection handling:**
- visual_analyst: Identify common elements + variations
- catalog_analyst: Find family matches, suggest structure
- Response: "I see 5 related items... [collective recommendation]"

**Mixed handling:**
- Route each image to appropriate domain
- Synthesize findings per domain
- Present organized by domain

**Limit handling:**
- More than 10 images: Process first 10, acknowledge remainder
- "I'll start with these 10 items. Send the rest after?"

</multi_image_handling>
```

---

## User Pattern Learning

PM infers patterns from conversation history. No explicit database needed.

### What PM Infers

| Pattern | How PM Infers |
|---------|---------------|
| Primary domain | "User has asked about products 8 times, marketing twice" |
| Typical intents | "User usually catalogs items, rarely asks for appraisals" |
| Price sensitivity | "User typically prices items in Rs 400-600 range" |
| Response preference | "User's replies are brief, they prefer concise responses" |
| Correction patterns | "User corrected category twice, be less certain about categories" |

### User Essence (Deferred to Framework)

**Decision**: Leverage DeepAgents built-in summarization middleware.

DeepAgents provides:
- Automatic conversation context compression
- Long-running session state management
- Built-in memory patterns

**Why defer?**
- Framework solution is battle-tested
- Avoids premature optimization
- Can layer custom strategy on top later if needed

**When to revisit:**
- If framework summarization proves insufficient
- If cross-session pattern persistence needed beyond framework capabilities
- Design custom solution with real usage data informing requirements

---

## Cold Start Handling

### Company Patterns

```python
class CompanyPatterns(BaseModel):
    """Loaded into PM context at startup. Lightweight."""

    common_intents: list[str]  # ["catalog", "pricing", "export"]
    common_categories: list[str]  # ["PET bottles", "jars", "containers"]
    typical_price_range: tuple[float, float]  # (50, 500)
    typical_user_journey: str  # "image -> catalog -> price -> export"
```

### Cold Start Prompt

```xml
<cold_start_handling>

For NEW users (no conversation history), you have limited signal.

**Lean on:**
1. Visual analysis (if image present) - weight heavily
2. Company patterns - "Most users of this company do X"
3. Explicit text signals - any keywords in their message

**Acknowledge uncertainty:**
"Since this is our first interaction, I want to make sure I understand..."

**Default to options:**
Present 2-3 common options rather than assuming one intent.

**Learn fast:**
Pay extra attention to their response - it teaches you their patterns.

</cold_start_handling>
```

---

## Advanced Behaviors

### 1. Confidence Transparency

```xml
<confidence_transparency>

For LEAD_WITH_TOP and PRESENT_OPTIONS responses, briefly explain reasoning:

**Pattern:**
"I think you want [X] because:
- [Evidence from user history]
- [Evidence from analysts]
- [What's uncertain]

[Your recommendation]

Am I reading this right?"

</confidence_transparency>
```

### 2. Learning Acknowledgment

```xml
<learning_acknowledgment>

When user corrects your assumption:

1. **Acknowledge smoothly** (no excessive apology)
2. **State what you learned** for THIS user
3. **Pivot to correct action**

**Pattern:**
"Got it - [correct intent], not [wrong assumption]. I notice [pattern].
I'll keep that in mind. [Proceed with correct action]..."

</learning_acknowledgment>
```

### 3. Emotional Calibration

```xml
<emotional_calibration>

Notice emotional signals and adapt:

**Frustrated** (short replies, corrections, negative tone):
- Slow down, be more careful
- Offer more options, fewer assumptions

**Confident** (quick approvals, decisive):
- Be more autonomous
- Fewer options, more action

**Confused** (questions, hesitation):
- Explain more
- Break into smaller steps

</emotional_calibration>
```

### 4. Proactive Suggestions

```xml
<proactive_suggestions>

After completing user's request, consider valuable insights:

**Patterns to notice:**
- Multiple similar items -> suggest family grouping
- Pricing inconsistencies -> suggest adjustment
- Missing variants -> suggest filling gaps

**Format:**
"[Complete request first]

By the way, I noticed [pattern]. Would you like me to [suggestion]?"

**Guidelines:**
- Only if genuinely valuable
- Maximum one suggestion per response
- Frame as optional

</proactive_suggestions>
```

---

## Example Flow

### Input
User sends image of brass handle, no text. User has history of cataloging products.

### PM Reasoning (Internal)

```
1. USER PATTERNS (from history + essence):
   - Cataloged 2 handles this week
   - Primary domain: catalog (90%)
   - Prefers brief responses
   - No corrections on handles

2. INPUT ANALYSIS:
   - Image present, no text
   - Ambiguous intent -> RESEARCH NEEDED

3. SPAWN ANALYSTS:
   - First: visual_analyst (image present) -> writes to /workspace/findings/visual.md
   - Parallel: product_analyst (reads visual.md) -> writes to /workspace/findings/product.md
   - Then: catalog_analyst (reads visual.md) -> writes to /workspace/findings/catalog.md

4. ANALYST FINDINGS (from workspace):
   - visual.md: "Brass door handle, Art Deco, 1930s, good condition, hand-forged details"
   - product.md: "Art Deco brass door handle, HSN 8302, restoration/collector market"
   - catalog.md: "3 similar in 'Vintage Hardware' at Rs 450-650, no Art Deco variant"

5. CONFIDENCE ASSESSMENT:
   - User pattern: strongly suggests catalog
   - Visual: confirms catalogable product
   - Catalog: clear pricing precedent
   - Confidence: Medium-High -> LEAD_WITH_TOP

6. RESPONSE STRATEGY:
   - Lead with observation + recommendation
   - Offer alternative
   - Invite correction
```

### PM Response

```
Brass door handle, Art Deco style (~1930s), good condition with natural
patina and hand-forged details.

I think you want to catalog this because:
- You've cataloged 2 similar handles this week
- Your typical range (Rs 450-650) matches

Recommendation: Add to 'Vintage Hardware' at Rs 550

Or:
- Get detailed appraisal (Art Deco can have collector value)
- Different approach

Am I reading this right?

---

By the way, I noticed there's no Art Deco-specific variant in your catalog.
Want me to create an 'Art Deco Hardware' sub-family?
```

### If User Approves

PM delegates to catalog_specialist WITH context:
```
"Create product based on analyst findings:
- Visual: brass Art Deco handle, 1930s, good condition
- Catalog: 3 similar at Rs 450-650, 'Vintage Hardware' family
- User confirmed: Add at Rs 550

Execute the catalog creation."
```

### If User Corrects

```
User: "No, I want to appraise it"

PM Response:
"Ah, appraisal not catalog - noted. I notice you prefer appraisals for
vintage Art Deco pieces. I'll remember that.

[Spawns product_analyst for appraisal data]

Based on recent auction data:
- Art Deco brass hardware: Rs 800-1,500 at auction
- Similar handles sold: Rs 950 avg
- Condition premium: +15% for original patina

Estimated value: Rs 900-1,100

Would you like a detailed appraisal report?"
```

---

## Implementation Roadmap

### Phase 1: Core Analysts (Week 1)

| Task | Type | Effort |
|------|------|--------|
| Create visual_analyst (prompt + config) | Prompt + Code | 1 day |
| Create product_analyst (prompt + config) | Prompt + Code | 1 day |
| Create catalog_analyst (prompt + config) | Prompt + Code | 1 day |
| Enhance PM prompt with analyst orchestration | Prompt | 1 day |
| Test chained delegation (visual -> product -> catalog) | Testing | 1 day |

### Phase 2: Specialist Slimdown (Week 1-2)

| Task | Type | Effort |
|------|------|--------|
| Remove research patterns from catalog_specialist | Prompt | 0.5 day |
| Add "receives context" pattern to specialists | Prompt | 0.5 day |
| Test specialist with pre-provided context | Testing | 0.5 day |

### Phase 3: PM Intelligence (Week 2)

| Task | Type | Effort |
|------|------|--------|
| Add research-first philosophy to PM | Prompt | 0.5 day |
| Add response strategies to PM (LLM Intelligence) | Prompt | 0.5 day |
| Add user pattern inference to PM | Prompt | 0.5 day |
| Test full research-first flow | Testing | 1 day |

### Phase 4: Persistence & Integration (Week 3)

| Task | Type | Effort |
|------|------|--------|
| Add hypothesis_outcome tracking | Schema + Code | 0.5 day |
| Enhance company context middleware with patterns | Code | 0.5 day |
| Integrate DeepAgents summarization middleware | Config | 0.5 day |
| Test persistence across sessions | Testing | 0.5 day |

### Phase 5: Additional Analysts (Ongoing)

| Task | Type | Effort |
|------|------|--------|
| Create operations_analyst | Prompt + Code | 1 day |
| Create marketing_analyst | Prompt + Code | 1 day |
| Each follows established pattern | Prompt | 0.5 day each |

---

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| Clarification rate | <30% | Messages where PM asks "what do you want?" |
| Hypothesis accuracy | >70% | Top intent matches actual intent |
| User correction rate | <15% | User corrects PM's assumption |
| Research latency | <500ms | Time for chained analyst execution |
| Prompt size (analysts) | <400 lines | Per-agent line count |
| Prompt size (specialists) | <700 lines | Per-agent line count |
| Cross-domain reuse | >3x | Domains using visual_analyst |

---

## Key Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `prompts/analysts/visual_analyst.prompt` | Create | Visual observation ("What do I SEE?") |
| `prompts/analysts/product_analyst.prompt` | Create | External product knowledge ("What IS this?") |
| `prompts/analysts/catalog_analyst.prompt` | Create | Internal catalog research ("What do we HAVE?") |
| `prompts/project_manager_intelligent.prompt` | Modify | Add research-first + analyst orchestration |
| `prompts/specialists/catalog_specialist.prompt` | Modify | Remove research patterns, add context receiving |
| `analysts/visual_analyst.py` | Create | Analyst config (Gemini 2.5 Flash, view_image tool) |
| `analysts/product_analyst.py` | Create | Analyst config (Gemini 2.5 Flash, web_search, hsn_lookup) |
| `analysts/catalog_analyst.py` | Create | Analyst config (Gemini 2.5 Flash, read_data, aggregate_data) |
| `middleware/company_context_middleware.py` | Modify | Add company pattern fields |

---

## Summary

**Philosophy**: Intelligence-First. Trust PM reasoning over rigid scaffolding.

**Architecture**: Two-layer agent model with 3 core analysts:

| Analyst | Question | Source |
|---------|----------|--------|
| visual_analyst | "What do I SEE?" | Image observation |
| product_analyst | "What IS this?" | External knowledge |
| catalog_analyst | "What do we HAVE?" | Internal DB |

**Key Decisions (from Debates + Research):**

| Decision | Approach |
|----------|----------|
| Two-layer separation | Analysts (research) + Specialists (execution) |
| Research philosophy | RESEARCH-FIRST - always before action |
| Analyst execution | HYBRID - chain when dependency, parallel otherwise |
| Specialist design | Remove patterns, keep ALL tools |
| Confidence expression | LLM Intelligence - natural language |
| Error handling | LLM Intelligence - contextual responses |
| User essence | Defer to DeepAgents framework |
| Company patterns | Enhance existing middleware |
| Context transfer | Shared workspace via FilesystemMiddleware (prompt-only) |

**Benefits**:

- Focused prompts (~300 lines analysts, ~600 lines specialists)
- Cross-domain reuse (visual_analyst serves 5+ domains)
- 44-60% token savings on research-only queries
- Linear scaling (add pair per domain, no bloat)
- Zero information loss (specialists read full analyst findings from workspace)

**The Difference**: A tool responds. An intelligent partner researches, synthesizes, and acts with informed confidence.

---

## Appendix: Migration from Merged to Two-Layer

### Current State (Merged)

```
catalog_specialist.prompt: ~824 lines
- Contains research workflow
- Contains execution workflow
- Contains examples for both
```

### Target State (Two-Layer)

```
visual_analyst.prompt: ~250 lines (NEW)
catalog_analyst.prompt: ~350 lines (NEW)
catalog_specialist.prompt: ~600 lines (SLIMMED)
- Research patterns REMOVED
- Context receiving pattern ADDED
- Execution patterns KEPT
```

### Migration Steps

1. Extract research sections from catalog_specialist -> catalog_analyst
2. Extract image analysis patterns -> visual_analyst
3. Create product_analyst for external product knowledge
4. Add workspace write pattern to all analysts
5. Add "receives context" + workspace read pattern to specialists
6. Update PM to orchestrate analysts with workspace references
7. Test end-to-end flow with workspace file verification

---

**Version History:**

- v3.1.0 (2025-12-07): Added Shared Workspace Protocol
  - Analysts write detailed findings to /workspace/findings/
  - Specialists read full context from workspace (zero information loss)
  - Leverages DeepAgents built-in FilesystemMiddleware (prompt-only, no code)
- v3.0.0 (2025-12-07): Final Architecture post-debates
  - Renamed market_analyst -> product_analyst (detailed product knowledge focus)
  - Research-First philosophy (always research before action)
  - LLM Intelligence for confidence and error handling (no rigid tiers)
  - Defer user essence to DeepAgents framework
  - Enhance existing company context middleware
- v2.0.0 (2025-12-07): Two-Layer Architecture - Analysts + Specialists separation
- v1.0.0 (2025-12-06): Initial design with researchers (merged approach)
