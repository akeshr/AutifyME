# Hypothesis Engine: Intelligence-First Intent Detection

**Status**: Design Complete
**Date**: 2025-12-06
**Authors**: Jarvis + Human Architect

---

## Executive Summary

The Hypothesis Engine transforms minimal user input (single image, vague message) into evidence-backed intent hypotheses through **research-first, prompt-driven** architecture.

**Core Philosophy**: Trust LLM intelligence. Guide through prompts, not code.

**Key Insight**: PM already has everything it needs - conversation history, tool access, reasoning capability. We don't need routing code, user profile databases, or confidence calculations. We need good prompts.

---

## Design Principles

### 1. Intelligence-First

> "If an LLM with full context can figure it out, don't hardcode the logic."

PM is an LLM. It can:
- Reason about which researchers to spawn (no routing code needed)
- Infer user patterns from conversation history (no profile database needed)
- Assess its own confidence (no calculation code needed)
- Synthesize findings naturally (no rigid schemas needed)

### 2. Prompt-Driven Architecture

| Traditional Approach | Our Approach |
|---------------------|--------------|
| Routing code with keyword matching | PM reasons about relevant domains |
| User profile database | PM infers from conversation history |
| Confidence scoring functions | PM assesses and responds accordingly |
| Rigid findings schemas | Natural language findings |
| Cross-domain protocol code | PM synthesizes all findings |

### 3. Research Before Asking

Instead of asking clarifying questions, PM:
1. Spawns relevant researchers in parallel
2. Gathers evidence from domain experts
3. Synthesizes findings with user context
4. Presents evidence-backed options

User feels: "This system understood me."

---

## Architecture Overview

```
User: [minimal input]
         |
         v
+--------+--------+
|       PM        |  <-- Full context: conversation history, company, tools
+--------+--------+
         |
   PM REASONS (via prompt guidance):
   - "What patterns do I see in this user's history?"
   - "Which domain researchers would help here?"
   - "How confident am I about their intent?"
         |
   PM DELEGATES (existing SubAgent capability):
   - visual_researcher
   - catalog_researcher
   - [others as PM decides]
         |
         v (PARALLEL)
+--------+---------+
| Researcher       |
| Findings         |
| (Natural Language)|
+--------+---------+
         |
   PM SYNTHESIZES (via prompt guidance):
   - Combine findings + user patterns
   - Assess confidence level
   - Apply response strategy
         |
         v
+--------+---------+
| Evidence-Backed  |
| Response         |
+------------------+
```

---

## What We Build

### Code We Write

| Component | Purpose | Why Code Needed |
|-----------|---------|-----------------|
| Researcher specialists | Separate agents with focused prompts, fast models | Optimization (speed, cost) |
| Outcome tracking | Persist hypothesis accuracy for calibration | Can't infer from context |
| Company patterns | Cold start baseline for new users | Need data source |

### Prompts We Write

| Prompt | Purpose |
|--------|---------|
| PM enhancement | Guide research-first behavior, user pattern inference, confidence assessment |
| visual_researcher | Focused image analysis |
| catalog_researcher | Focused catalog/pricing lookup |
| [domain]_researcher | One per domain as we scale |

---

## PM Prompt Enhancement

Add to PM system prompt:

```xml
<research_first_behavior>

## Understanding User Intent (Before Every Response)

You have access to the full conversation history. Before responding to any message,
reason through the following:

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

### 2. Research Before Responding

When input is minimal or ambiguous, spawn domain researchers to gather evidence:

- **Always** spawn `visual_researcher` if image is present
- Spawn `catalog_researcher` if likely product-related
- Spawn `marketing_researcher` if likely campaign-related
- Spawn other domain researchers based on your judgment

Delegate to researchers in PARALLEL - they return findings, you synthesize.

### 3. Confidence Assessment

After gathering evidence, honestly assess your confidence:

- **High (>90%)**: Strong evidence from multiple sources, clear user pattern match
- **Medium-High (70-90%)**: Good evidence, likely correct but alternatives exist
- **Medium (40-70%)**: Some evidence, multiple plausible interpretations
- **Low (<40%)**: Limited evidence, mostly speculation

### 4. Response Strategy (Based on Confidence)

**High Confidence (>90%)** - DIRECT_ACTION:
```
[Observations from research]

[Action you're taking with clear reasoning]

[Details: price, category, etc.]

Shall I proceed?
```

**Medium-High (70-90%)** - LEAD_WITH_TOP:
```
[Observations from research]

[Primary recommendation with reasoning]

Or:
- [Alternative 1]
- [Alternative 2]

Which direction?
```

**Medium (40-70%)** - PRESENT_OPTIONS:
```
[Observations from research]

I see a few directions:
1. [Option 1 with brief context]
2. [Option 2 with brief context]
3. [Option 3 with brief context]

Which would you like?
```

**Low (<40%)** - OBSERVE_AND_ASK:
```
[Observations - what you noticed]

What would you like to do with this?
```

### 5. Evidence in Response

Always lead with what you OBSERVED (facts from research), then what you INFERRED (your hypothesis). This lets users correct inference without feeling you're blind.

Example:
```
"I see a brass door handle, Art Deco style (~1930s), good condition.
[OBSERVATION - from visual_researcher]

Your catalog has 3 similar handles at Rs 450-650. You've added 2 handles this week.
[OBSERVATION - from catalog_researcher + conversation history]

Recommendation: Add at Rs 550 (matches your pattern)
[INFERENCE - your hypothesis]
"
```

</research_first_behavior>
```

---

## Researcher Prompts

### visual_researcher

```xml
<role>
You are a visual analysis specialist. Your job is to analyze images and return
detailed observations. You are fast and focused.
</role>

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
Return your findings in natural language. Example:

"Primary object: Door handle
Materials: Brass, possibly solid (not plated based on patina pattern)
Style/Era: Art Deco, likely 1920s-1940s based on geometric patterns
Condition: Good - natural patina present, no damage visible, original finish intact
Dimensions: Approximately 15cm length based on proportions
Notable features: Hand-forged details on backplate, original screws present
Image quality: High - good lighting, sharp focus

Confidence: High (85%) - clear image with distinctive style markers"
</output_format>

<boundaries>
- Do NOT suggest what the user should do with this item
- Do NOT make assumptions about user intent
- Do NOT provide pricing or categorization (that's catalog_researcher's job)
- Focus purely on visual observation
</boundaries>
```

### catalog_researcher

```xml
<role>
You are a catalog research specialist. Your job is to find relevant information
from the product catalog and pricing data. You are fast and focused.
</role>

<instructions>
Given context (image description, user query, or product reference), research:

1. **Similar Items**: Find similar products in the catalog
2. **Pricing Patterns**: What do similar items cost? Min/max/average?
3. **Relevant Families**: Which product families match?
4. **Gaps**: Any missing variants or categories?
5. **Recent Activity**: Any recent changes to similar items?

Use your tools:
- `read_data`: Query product, family, pricing tables
- `aggregate_data`: Get pricing statistics
</instructions>

<output_format>
Return your findings in natural language. Example:

"Similar items found: 3 brass handles in 'Vintage Hardware' family
- HANDLE-BRASS-001: Vintage Brass Handle, Rs 450
- HANDLE-BRASS-002: Art Deco Handle, Rs 600
- HANDLE-BRASS-003: Antique Door Handle, Rs 550

Pricing patterns: Range Rs 450-650, average Rs 533, trend stable

Relevant families: 'Vintage Hardware' (best match), 'Door Accessories' (broader)

Gaps identified: No Art Deco-specific variant exists in catalog

Confidence: High (90%) - good data coverage for this category"
</output_format>

<boundaries>
- Do NOT suggest what the user should do
- Do NOT make assumptions about user intent
- Focus purely on catalog facts and patterns
- Stay within catalog/pricing domain (don't query marketing, finance, etc.)
</boundaries>
```

### Template for Future Researchers

```xml
<role>
You are a {domain} research specialist. Your job is to find relevant information
from {domain} data. You are fast and focused.
</role>

<instructions>
Given context, research:
1. [Domain-specific query 1]
2. [Domain-specific query 2]
3. [Domain-specific query 3]

Use your tools:
- `read_data`: Query {domain} tables
- `aggregate_data`: Get {domain} statistics
</instructions>

<output_format>
Return findings in natural language with confidence assessment.
</output_format>

<boundaries>
- Do NOT suggest actions (PM's job)
- Do NOT assume user intent
- Stay within {domain} (don't query other domains)
</boundaries>
```

---

## User Pattern Learning (No Database)

PM infers user patterns from conversation history. No explicit storage needed.

### What PM Infers

| Pattern | How PM Infers |
|---------|---------------|
| Primary domain | "User has asked about products 8 times, marketing twice" |
| Typical intents | "User usually catalogs items, rarely asks for appraisals" |
| Price sensitivity | "User typically prices items in Rs 400-600 range" |
| Response preference | "User's replies are brief, they prefer concise responses" |
| Correction patterns | "User corrected category twice, I should be less certain about categories" |

### Prompt Guidance for Inference

```xml
<user_pattern_inference>

The conversation history IS the user profile. From it, notice:

- **Frequency patterns**: What does this user ask about most?
- **Language patterns**: How do they phrase requests? Brief or detailed?
- **Correction patterns**: What have they corrected? (signals where to be less confident)
- **Workflow patterns**: What sequences do they follow? (image -> catalog -> price?)
- **Preference patterns**: Do they prefer options or recommendations?

Use these patterns to:
- Adjust which researchers you spawn
- Calibrate your confidence levels
- Match their response style

Example reasoning:
"Looking at history: User has sent 5 product images this week, all cataloged.
They corrected my category suggestion once. They reply with single words ('yes', 'ok').
Inference: High likelihood of catalog intent, be careful with categories, keep response brief."

</user_pattern_inference>
```

---

## Cold Start Handling (Minimal Code)

For truly new users, PM uses company patterns as baseline.

### Company Patterns (Loaded into Context)

```python
class CompanyPatterns(BaseModel):
    """Loaded into PM context at startup. Lightweight."""

    common_intents: list[str]  # ["catalog", "pricing", "export"]
    common_categories: list[str]  # ["PET bottles", "jars", "containers"]
    typical_price_range: tuple[float, float]  # (50, 500)
    typical_user_journey: str  # "image -> catalog -> price -> export"
```

### PM Prompt for Cold Start

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

## Outcome Tracking (Minimal Code Needed)

We need to track outcomes to calibrate confidence over time. This requires code.

### What We Track

```python
class HypothesisOutcome(BaseModel):
    """Extend workflow_outcomes with hypothesis tracking."""

    # Link to workflow
    tracking_id: str
    thread_id: str

    # What PM predicted
    predicted_intent: str
    predicted_confidence: float  # PM's stated confidence
    response_strategy: str  # "direct_action", "lead_with_top", etc.

    # What actually happened
    actual_intent: str  # Inferred from user's selection/correction
    was_correct: bool
    user_corrected: bool

    # For calibration
    timestamp: datetime
```

### How We Use It

1. **Track**: After each interaction, record prediction vs. outcome
2. **Analyze**: Periodically analyze accuracy by confidence band
3. **Adjust**: Update PM prompt with calibration guidance

```xml
<calibration_feedback>

Based on historical accuracy:
- When you say "90% confident", you're actually right 85% of the time
- When you say "70% confident", you're actually right 68% of the time

Adjust accordingly:
- Be slightly more conservative with high confidence claims
- Your medium confidence is well-calibrated

</calibration_feedback>
```

---

## Response Strategy Reference

### Confidence Thresholds (Prompt Guidance)

| Confidence | Strategy | When to Use |
|------------|----------|-------------|
| >90% | DIRECT_ACTION | Multiple evidence sources align, clear user pattern |
| 70-90% | LEAD_WITH_TOP | Good evidence, but alternatives plausible |
| 40-70% | PRESENT_OPTIONS | Mixed signals, multiple valid interpretations |
| <40% | OBSERVE_AND_ASK | Limited evidence, high uncertainty |

### Response Patterns

**DIRECT_ACTION (>90%)**
```
[Observations]
[Action statement]
[Details]
Shall I proceed?
```

**LEAD_WITH_TOP (70-90%)**
```
[Observations]
[Primary recommendation]

Or:
- [Alternative 1]
- [Alternative 2]

Which direction?
```

**PRESENT_OPTIONS (40-70%)**
```
[Observations]

I see a few directions:
1. [Option 1]
2. [Option 2]
3. [Option 3]

Which would you like?
```

**OBSERVE_AND_ASK (<40%)**
```
[Observations]

What would you like to do with this?
```

---

## Example Flow

### Input
User sends image of brass handle, no text. User has history of cataloging products.

### PM Reasoning (Internal)

```
1. USER PATTERNS (from history):
   - Cataloged 2 handles this week
   - Primary domain: catalog
   - Prefers brief responses
   - No corrections on handle categorization

2. RESEARCHERS TO SPAWN:
   - visual_researcher (image present)
   - catalog_researcher (likely product-related based on pattern)

3. [Spawns researchers in parallel]

4. FINDINGS RECEIVED:
   - Visual: "Brass door handle, Art Deco, 1930s, good condition"
   - Catalog: "3 similar at Rs 450-650 in 'Vintage Hardware'"

5. CONFIDENCE ASSESSMENT:
   - User pattern strongly suggests catalog intent
   - Visual confirms it's a product
   - Catalog shows clear pricing precedent
   - Confidence: ~85% (LEAD_WITH_TOP)

6. RESPONSE:
```

### PM Response

```
Brass door handle, Art Deco style (~1930s), good condition with natural patina.

Your catalog has 3 similar handles in 'Vintage Hardware' at Rs 450-650.
You've added 2 handles this week.

Recommendation: Add at Rs 550 (matches your pattern)

Or:
- Get detailed appraisal
- Different approach

Which direction?
```

---

## Implementation Roadmap

### Phase 1: Core (Week 1)

| Task | Type | Effort |
|------|------|--------|
| Enhance PM prompt with research-first behavior | Prompt | 1 day |
| Create visual_researcher specialist | Prompt + Config | 1 day |
| Create catalog_researcher specialist | Prompt + Config | 1 day |
| Test parallel delegation | Testing | 1 day |
| Refine based on testing | Iteration | 1 day |

### Phase 2: Tracking (Week 2)

| Task | Type | Effort |
|------|------|--------|
| Add HypothesisOutcome to workflow_outcomes | Schema | 0.5 day |
| Track predictions in runner | Code | 0.5 day |
| Infer actual intent from user response | Code | 1 day |
| Build basic accuracy report | Code | 1 day |
| Add company patterns loading | Code | 1 day |

### Phase 3: Calibration (Week 3+)

| Task | Type | Effort |
|------|------|--------|
| Analyze accuracy by confidence band | Analysis | 0.5 day |
| Update PM prompt with calibration feedback | Prompt | 0.5 day |
| Iterate based on real usage | Ongoing | - |

### Phase 4: Domain Expansion (Ongoing)

- Add researcher per new domain (prompt only)
- Update PM prompt with new domain awareness
- No code changes needed for expansion

---

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| Clarification rate | <30% | Messages where PM asks "what do you want?" |
| Hypothesis accuracy | >70% | Top intent matches actual intent |
| User correction rate | <15% | User corrects PM's assumption |
| Research latency | <500ms | Time for parallel researcher execution |
| Cold start recovery | <5 msgs | Messages until accuracy matches warm users |

---

## What We Removed (vs. Previous Design)

| Removed | Why |
|---------|-----|
| Routing code (keyword matching) | PM reasons about relevance |
| User profile database | PM infers from conversation history |
| Confidence calculation code | PM assesses naturally |
| Rigid findings schemas | Natural language findings |
| Scoped tool factory | Prompt researchers to stay focused |
| Cross-domain protocol code | PM synthesizes all findings |
| Complex implementation roadmap | Mostly prompts now |

---

## Key Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `prompts/project_manager_intelligent.prompt` | Modify | Add research-first behavior section |
| `prompts/researchers/visual_researcher.prompt` | Create | Visual analysis specialist |
| `prompts/researchers/catalog_researcher.prompt` | Create | Catalog research specialist |
| `specialists/visual_researcher.py` | Create | Minimal config (model, tools) |
| `specialists/catalog_researcher.py` | Create | Minimal config (model, tools) |
| `schemas/hypothesis_outcome.py` | Create | Outcome tracking schema |
| `workflows/outcome_tracker.py` | Modify | Add hypothesis tracking |

---

## Summary

**Philosophy**: Trust PM intelligence. Guide through prompts, not code.

**Architecture**: PM reasons about user patterns, spawns researchers, synthesizes findings, responds with calibrated confidence.

**Implementation**: Mostly prompts. Minimal code for outcome tracking and researcher configs.

**Scaling**: Add researchers via prompts. No code changes per domain.

This is how I work. Now PM works the same way.
