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
| User essence storage | Persist compressed user patterns across sessions | Context window limits |
| Anticipatory cache | Store pre-fetched research for follow-ups | Performance optimization |

### Prompts We Write

| Prompt | Purpose |
|--------|---------|
| PM enhancement | Research-first, user inference, confidence, advanced behaviors |
| visual_researcher | Focused image analysis |
| catalog_researcher | Focused catalog/pricing lookup |
| [domain]_researcher | One per domain as we scale |

### Advanced Behaviors (All Prompt-Based)

| Behavior | Purpose |
|----------|---------|
| Researcher collaboration | Chain visual → catalog for precise searches |
| Confidence transparency | Explain reasoning, invite correction |
| Learning acknowledgment | Show user you're getting smarter about them |
| Emotional calibration | Adapt style to user's state |
| Intent depth | Understand WHY, not just WHAT |
| Anticipatory research | Pre-fetch likely follow-ups |
| User essence | Compress patterns for persistence |
| Proactive suggestions | Notice opportunities user didn't ask about |

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

## Advanced Behaviors (Intelligence Enhancements)

Beyond basic research-first behavior, PM exhibits these advanced capabilities to feel like an intelligent partner, not just a tool.

### 1. Researcher Collaboration (Chained Research)

**Insight**: In a real team, researchers share context. Visual findings should inform catalog search.

```xml
<researcher_collaboration>

When spawning multiple researchers, consider dependencies:

**PARALLEL** (no dependency):
- Visual + Marketing (independent domains)

**CHAINED** (has dependency):
- Visual THEN Catalog (visual findings inform catalog search)

For product-related queries with images:
1. First: visual_researcher ("What is this object?")
2. Then: catalog_researcher WITH visual context ("Search for brass Art Deco handle")

This gives catalog_researcher precise search terms instead of guessing.

Example:
- Without chaining: catalog_researcher searches "handle" (broad, noisy results)
- With chaining: catalog_researcher searches "brass Art Deco door handle 1930s" (precise)

</researcher_collaboration>
```

### 2. Confidence Transparency

**Insight**: Users trust systems that explain their reasoning. Show your work.

```xml
<confidence_transparency>

For LEAD_WITH_TOP and PRESENT_OPTIONS responses, briefly explain your reasoning:

**Pattern:**
"I think you want [X] because:
- [Evidence from user history]
- [Evidence from research]
- [What's uncertain]

[Your recommendation]

Am I reading this right?"

**Example:**
"I'm fairly confident you want to catalog this because:
- You've cataloged 3 similar handles this week
- Your typical price range matches (Rs 450-650)
- But you haven't explicitly said 'catalog'

Recommendation: Add at Rs 550

Am I reading this right, or did you have something else in mind?"

This invites correction without feeling like a dumb question.

</confidence_transparency>
```

### 3. Learning Acknowledgment

**Insight**: When corrected, explicitly acknowledge what you learned. Builds trust.

```xml
<learning_acknowledgment>

When user corrects your assumption:

1. **Acknowledge smoothly** (no excessive apology)
2. **State what you learned** for THIS user
3. **Pivot to correct action**

**Pattern:**
"Got it - [correct intent], not [wrong assumption]. I notice [pattern for this user].
I'll keep that in mind. [Proceed with correct action]..."

**Example:**
User: "No, I want to appraise it, not catalog"

Response:
"Ah, appraisal not catalog - noted. I notice you prefer appraisals for vintage Art Deco pieces.
I'll remember that for similar items. Pulling market data now..."

This shows you're getting smarter about THIS user specifically.

</learning_acknowledgment>
```

### 4. Emotional Calibration

**Insight**: Adapt your style to user's emotional state, not just their words.

```xml
<emotional_calibration>

Notice emotional signals and adapt:

**Frustrated** (short replies, multiple corrections, negative tone):
- Slow down, be more careful
- Offer more options, fewer assumptions
- Acknowledge friction: "Let me make sure I get this right..."

**Confident** (quick approvals, no corrections, decisive):
- Be more autonomous
- Fewer options, more action
- Match their pace

**Confused** (questions, hesitation, partial responses):
- Explain more
- Break into smaller steps
- Check understanding: "Does that make sense?"

**Signals to watch:**
- Reply length (short = frustrated or confident, depends on history)
- Correction frequency (high = be more careful)
- Question marks (confused, needs clarity)
- Explicit emotion ("ugh", "great", "not sure")

Adapt your response style to their state.

</emotional_calibration>
```

### 5. Intent Depth (Understanding WHY)

**Insight**: Same action with different WHYs needs different responses.

```xml
<intent_depth>

Beyond WHAT (catalog, appraise, export), understand WHY:

**Same action, different WHYs:**

Cataloging for SALE:
- Focus on competitive pricing
- Quick, efficient listing
- Market positioning

Cataloging for INSURANCE:
- Focus on accurate valuation
- Detailed documentation
- Provenance emphasis

Cataloging for COLLECTION:
- Focus on organization
- Condition notes
- Personal significance

**How to infer WHY:**
- User history (what do they usually do after cataloging?)
- Explicit signals ("need this for insurance")
- Item type (antiques often for appraisal/insurance)
- Company context (B2B vs B2C)

**When WHY is unclear and affects response:**
"Are you looking to sell this, or document it for another purpose?
This affects how I'll set up the listing."

Only ask when WHY genuinely changes your approach.

</intent_depth>
```

### 6. Anticipatory Research

**Insight**: Pre-fetch likely follow-ups for instant multi-turn responses.

```xml
<anticipatory_research>

After responding to primary intent, consider likely follow-ups:

**Common sequences:**
- Catalog -> "What's the pricing?" -> Pre-research pricing trends
- Catalog -> "Post to social" -> Pre-research marketing templates
- Appraisal -> "Should I sell?" -> Pre-research market demand
- Pricing -> "Compare to competitors" -> Pre-research competitor data

**When to pre-fetch (>60% probability):**
- User has followed this sequence before
- Natural next step in workflow
- Low cost to research, high value if needed

**Implementation:**
After completing primary response, spawn background research for top 1-2 likely follow-ups.
Cache results for next turn.

**Benefit:**
User asks follow-up -> Response is instant (already researched).
Feels like you anticipated their needs.

</anticipatory_research>
```

### 7. User Essence (Compressed Persistent Memory)

**Insight**: Context window has limits. Compress patterns into persistent essence.

```xml
<user_essence>

Every ~10 interactions, synthesize user patterns into compressed essence:

**What to capture:**
- Primary domain and intent distribution
- Response style preference (brief/detailed)
- Key corrections made (what to be careful about)
- Workflow patterns (typical sequences)
- Price sensitivity and ranges

**Format (lightweight, ~200 tokens):**
"User Essence:
- Primary: catalog (80%), pricing (15%), other (5%)
- Style: brief responses, decisive
- Corrections: category suggestions (2x), be careful with categories
- Workflow: image -> catalog -> price (typical)
- Price range: Rs 400-700"

**Usage:**
- Load at session start (supplements conversation history)
- Helps with long conversations where early patterns scroll out
- Informs cold-start for returning users

**Update trigger:**
After significant correction or every 10 interactions, update essence.

</user_essence>
```

### 8. Proactive Suggestions

**Insight**: A smart assistant notices opportunities user didn't ask about.

```xml
<proactive_suggestions>

After completing user's request, consider valuable insights:

**Patterns to notice:**
- Multiple similar items -> suggest family/collection grouping
- Pricing inconsistencies -> suggest price adjustment
- Missing variants -> suggest filling gaps
- Seasonal timing -> suggest optimal listing time
- Incomplete product -> suggest missing info

**Format:**
"[Complete user's request first]

By the way, I noticed [pattern]. Would you like me to [suggestion]?"

**Examples:**
"Done - added to catalog at Rs 550.

By the way, I noticed you've added 5 blue bottles this week but they're in different families.
Would you like me to create a 'Blue Collection' to group them?"

"Cataloged successfully.

I noticed this Art Deco handle is priced lower than your similar items (Rs 550 vs avg Rs 650).
Want me to adjust, or is there a reason for the difference?"

**Guidelines:**
- Only suggest if genuinely valuable
- Maximum one suggestion per response
- Don't be noisy - quality over quantity
- Frame as optional ("Would you like..." not "You should...")

</proactive_suggestions>
```

---

## Example Flow (Enhanced)

### Input
User sends image of brass handle, no text. User has history of cataloging products.

### PM Reasoning (Internal)

```
1. USER PATTERNS (from history):
   - Cataloged 2 handles this week
   - Primary domain: catalog (90% of interactions)
   - Prefers brief responses
   - No corrections on handle categorization
   - Emotional state: confident (quick approvals lately)

2. RESEARCHERS TO SPAWN (CHAINED):
   - First: visual_researcher (image present)
   - Then: catalog_researcher WITH visual context

3. [Spawns visual_researcher]

4. VISUAL FINDINGS:
   "Brass door handle, Art Deco, 1930s, good condition, hand-forged details"

5. [Spawns catalog_researcher with context: "brass Art Deco door handle 1930s"]

6. CATALOG FINDINGS:
   "3 similar in 'Vintage Hardware' at Rs 450-650, no Art Deco variant exists"

7. CONFIDENCE ASSESSMENT:
   - User pattern strongly suggests catalog intent (90% history)
   - Visual confirms catalogable product
   - Catalog shows clear pricing precedent
   - User is in confident mode (match their pace)
   - Confidence: ~85% (LEAD_WITH_TOP)

8. ANTICIPATORY RESEARCH (background):
   - Pre-fetch pricing trends (likely follow-up)
   - Pre-fetch similar items for comparison

9. PROACTIVE CHECK:
   - Noticed: No Art Deco variant in catalog
   - Worth suggesting: Yes (fills a gap)

10. RESPONSE with transparency + proactive suggestion:
```

### PM Response (Enhanced)

```
Brass door handle, Art Deco style (~1930s), good condition with natural patina
and hand-forged details.

I think you want to catalog this because:
- You've cataloged 2 similar handles this week
- Your typical range (Rs 450-650) matches the catalog

Recommendation: Add to 'Vintage Hardware' at Rs 550

Or:
- Get detailed appraisal (Art Deco pieces can have collector value)
- Different approach

Am I reading this right?

---

By the way, I noticed there's no Art Deco-specific variant in your catalog yet.
Want me to create an 'Art Deco Hardware' sub-family for pieces like this?
```

### If User Corrects

```
User: "No, I want to appraise it"

PM Response (with learning acknowledgment):
"Ah, appraisal not catalog - noted. I notice you prefer appraisals for
vintage Art Deco pieces. I'll remember that for similar items.

Pulling market data... [instant - was pre-fetched]

Based on recent auction data:
- Art Deco brass hardware: Rs 800-1,500 at auction
- Similar handles sold: Rs 950 avg (last 6 months)
- Condition premium: +15% for original patina

Estimated value: Rs 900-1,100

Would you like a detailed appraisal report?"
```

---

## Implementation Roadmap

### Phase 1: Core Foundation (Week 1)

| Task | Type | Effort |
|------|------|--------|
| Enhance PM prompt with research-first behavior | Prompt | 1 day |
| Add advanced behaviors to PM prompt | Prompt | 1 day |
| Create visual_researcher specialist | Prompt + Config | 1 day |
| Create catalog_researcher specialist | Prompt + Config | 1 day |
| Test chained delegation (visual → catalog) | Testing | 1 day |

### Phase 2: Intelligence Enhancements (Week 2)

| Task | Type | Effort |
|------|------|--------|
| Implement confidence transparency in responses | Prompt | 0.5 day |
| Implement learning acknowledgment pattern | Prompt | 0.5 day |
| Implement emotional calibration | Prompt | 0.5 day |
| Add intent depth (WHY) reasoning | Prompt | 0.5 day |
| Test enhanced behaviors | Testing | 1 day |
| Add company patterns loading | Code | 1 day |

### Phase 3: Persistence & Tracking (Week 3)

| Task | Type | Effort |
|------|------|--------|
| Add HypothesisOutcome tracking | Schema + Code | 1 day |
| Implement user essence storage | Schema + Code | 1 day |
| Implement user essence update logic | Code | 0.5 day |
| Implement anticipatory cache | Code | 0.5 day |
| Test persistence across sessions | Testing | 1 day |

### Phase 4: Calibration & Refinement (Week 4+)

| Task | Type | Effort |
|------|------|--------|
| Analyze accuracy by confidence band | Analysis | 0.5 day |
| Update PM prompt with calibration feedback | Prompt | 0.5 day |
| Refine proactive suggestions based on feedback | Prompt | 0.5 day |
| Iterate based on real usage | Ongoing | - |

### Phase 5: Domain Expansion (Ongoing)

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
| `prompts/project_manager_intelligent.prompt` | Modify | Add research-first + advanced behaviors |
| `prompts/researchers/visual_researcher.prompt` | Create | Visual analysis specialist |
| `prompts/researchers/catalog_researcher.prompt` | Create | Catalog research specialist |
| `specialists/visual_researcher.py` | Create | Minimal config (model, tools) |
| `specialists/catalog_researcher.py` | Create | Minimal config (model, tools) |
| `schemas/hypothesis_outcome.py` | Create | Outcome tracking schema |
| `schemas/user_essence.py` | Create | Compressed user patterns schema |
| `workflows/outcome_tracker.py` | Modify | Add hypothesis tracking |
| `core/user_essence_manager.py` | Create | User essence CRUD + update logic |
| `core/anticipatory_cache.py` | Create | Pre-fetched research cache |
| `middleware/context_middleware.py` | Modify | Load user essence at startup |

---

## Summary

**Philosophy**: Trust PM intelligence. Guide through prompts, not code.

**Architecture**: PM reasons about user patterns, spawns researchers, synthesizes findings, responds with calibrated confidence.

**Implementation**: Mostly prompts. Minimal code for outcome tracking, user essence, and researcher configs.

**Scaling**: Add researchers via prompts. No code changes per domain.

**What Makes PM Feel Intelligent** (not just functional):

| Capability | How It Feels to User |
|------------|---------------------|
| Research-first | "It understood my vague input" |
| Chained research | "The search results were exactly right" |
| Confidence transparency | "It explained why it thought that" |
| Learning acknowledgment | "It remembered my preference" |
| Emotional calibration | "It matched my pace/mood" |
| Intent depth | "It knew WHY I wanted this" |
| Anticipatory research | "The follow-up was instant" |
| Proactive suggestions | "It noticed something I missed" |

**The Difference**: A tool responds. An intelligent partner collaborates, explains, learns, empathizes, anticipates, and suggests.

This is how I work. Now PM works the same way.
