# Hypothesis Engine: Intelligence-First Intent Detection

**Status**: Design Complete - Revised v3.0
**Date**: 2025-12-07
**Authors**: Jarvis + Human Architect
**Revision**: v3.0 - Final Architecture (Post-Debates)

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
         | Fast, Gemini Flash                            | Careful, HITL
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
| **Analyst** | Research, understand, find patterns | Gemini Flash | Read-only | ~250-400 lines |
| **Specialist** | Execute, create, modify | Gemini Flash/Pro | Write (HITL) | ~500-700 lines |

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
| visual_analyst | Analyst | Gemini Flash 2.0 | view_image | ~250 lines |
| product_analyst | Analyst | Gemini Flash 2.0 | web_search, hsn_lookup | ~300 lines |
| catalog_analyst | Analyst | Gemini Flash 2.0 | read_data, aggregate_data | ~350 lines |
| catalog_specialist | Specialist | Gemini Flash 2.0 | write_data, create_record | ~600 lines (slimmed) |
| creative_specialist | Specialist | Gemini Flash 2.0 | image_studio | ~500 lines (slimmed) |

### Code We Write

| Component | Purpose | Why Code Needed |
|-----------|---------|-----------------|
| Analyst agent configs | Separate agents with focused prompts | Optimization (speed, cost) |
| Specialist slimdown | Remove research patterns, add context receiving | Separation of concerns |
| Outcome tracking | Persist whether hypothesis was correct | Can't infer across sessions |
| Company patterns | Cold start baseline for new users | Need data source |
| User essence storage | Persist compressed user patterns | Context window limits |

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

### 6. When to Delegate to Specialists

After research phase, if ACTION is needed:
- Pass analyst findings as context to specialist
- Specialist focuses on execution, not research
- Specialist receives enriched context, not raw user input

Pattern:
```
PM: "catalog_specialist, create this product based on analyst findings:
     - Visual: brass Art Deco handle, 1930s, good condition
     - Catalog: 3 similar at Rs 450-650, no Art Deco variant exists
     - User history: catalogs products, typical range Rs 400-700

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
Return findings in natural language:

"Primary object: Door handle
Materials: Brass, possibly solid (not plated based on patina pattern)
Style/Era: Art Deco, likely 1920s-1940s based on geometric patterns
Condition: Good - natural patina present, no damage visible
Dimensions: Approximately 15cm length based on proportions
Notable features: Hand-forged details on backplate
Image quality: High - good lighting, sharp focus

Confidence: High - clear image with distinctive style markers"
</output_format>

<boundaries>
- Do NOT suggest what the user should do with this item
- Do NOT make assumptions about user intent
- Do NOT provide pricing or categorization (that's catalog_analyst's job)
- Focus purely on visual observation
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
Return findings in natural language:

"Similar items found: 3 brass handles in 'Vintage Hardware' family
- HANDLE-BRASS-001: Vintage Brass Handle, Rs 450
- HANDLE-BRASS-002: Art Deco Handle, Rs 600
- HANDLE-BRASS-003: Antique Door Handle, Rs 550

Pricing patterns: Range Rs 450-650, average Rs 533, trend stable

Relevant families: 'Vintage Hardware' (best match), 'Door Accessories' (broader)

Gaps identified: No Art Deco-specific variant exists in catalog

Confidence: High - good data coverage for this category"
</output_format>

<boundaries>
- Do NOT suggest what the user should do
- Do NOT make assumptions about user intent
- Focus purely on catalog facts and patterns
- Stay within catalog/pricing domain
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
Return findings in natural language:

"Product identity: Wide Mouth Glass Mason Jar
Standard sizes: 250ml, 500ml, 1L (most common)
Materials: Borosilicate glass (premium), soda-lime glass (standard)

Classifications:
- HSN Code: 7010 (glass containers)
- Category: Food storage containers
- GST Rate: 18%

Usage: Food preservation, canning, craft storage, DIY projects
Common in: Food industry, home goods, craft supplies

Related products: Metal lids, plastic pour caps, labels, jar openers

Confidence: High - well-documented product category"
</output_format>

<boundaries>
- Do NOT suggest what user should do (PM's job)
- Do NOT assume user intent
- Focus on product KNOWLEDGE, not pricing
- Stay factual about what the product IS
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
</tools>

<instructions>
Given context, research:
1. [Domain-specific query 1]
2. [Domain-specific query 2]
3. [Domain-specific query 3]
</instructions>

<output_format>
Return findings in natural language with confidence assessment.
</output_format>

<boundaries>
- Do NOT suggest actions (PM's job)
- Do NOT assume user intent
- Stay within {domain}
</boundaries>
```

---

## Specialist Prompt Pattern (Slimmed)

Specialists no longer need research patterns - they receive research context from PM.

```xml
<background_information>
## Your Role
You are the **{Domain} Specialist** - focused on execution within your domain.

## Your Position
- PM delegates to you WITH research context from analysts
- You receive enriched input, not raw user queries
- You focus on: validation, CRUD, HITL approval flows

## Context You Receive
PM provides analyst findings as context:
- Visual analysis (what the item is)
- Catalog research (similar items, pricing patterns)
- Market research (external rates, HSN codes)
- User patterns (history, preferences)

You don't need to re-research - focus on execution.
</background_information>

<instructions>
## Execution Focus

Given PM's research context + intent:
1. Validate the proposed action against schema constraints
2. Check for any edge cases PM may have missed
3. Construct the write operation
4. Present for HITL approval

## You Do NOT
- Re-analyze images (visual_analyst already did)
- Re-query for similar products (catalog_analyst already did)
- Research product details (product_analyst already did)
- Infer user intent (PM already did)

Focus on EXECUTION, not RESEARCH.
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

3. SPAWN ANALYSTS (CHAINED):
   - First: visual_analyst (image present)
   - Then: catalog_analyst WITH visual context

4. VISUAL FINDINGS:
   "Brass door handle, Art Deco, 1930s, good condition, hand-forged details"

5. CATALOG FINDINGS (with visual context):
   "3 similar in 'Vintage Hardware' at Rs 450-650, no Art Deco variant"

6. CONFIDENCE ASSESSMENT:
   - User pattern: strongly suggests catalog
   - Visual: confirms catalogable product
   - Catalog: clear pricing precedent
   - Confidence: Medium-High -> LEAD_WITH_TOP

7. RESPONSE STRATEGY:
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
| `analysts/visual_analyst.py` | Create | Analyst config (Gemini Flash, view_image tool) |
| `analysts/product_analyst.py` | Create | Analyst config (Gemini Flash, web_search, hsn_lookup) |
| `analysts/catalog_analyst.py` | Create | Analyst config (Gemini Flash, read_data, aggregate_data) |
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

**Key Decisions (from Debates):**

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

**Benefits**:

- Focused prompts (~300 lines analysts, ~600 lines specialists)
- Cross-domain reuse (visual_analyst serves 5+ domains)
- 44-60% token savings on research-only queries
- Linear scaling (add pair per domain, no bloat)

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
3. Add "receives context" pattern to catalog_specialist
4. Update PM to orchestrate analysts
5. Test end-to-end flow

---

**Version History:**

- v3.0.0 (2025-12-07): Final Architecture post-debates
  - Renamed market_analyst -> product_analyst (detailed product knowledge focus)
  - Research-First philosophy (always research before action)
  - LLM Intelligence for confidence and error handling (no rigid tiers)
  - Defer user essence to DeepAgents framework
  - Enhance existing company context middleware
- v2.0.0 (2025-12-07): Two-Layer Architecture - Analysts + Specialists separation
- v1.0.0 (2025-12-06): Initial design with researchers (merged approach)
