# Context Sufficiency Gate: Design Specification

**Date:** 2025-12-08
**Status:** Design Draft - Pending Review
**Replaces:** Research-First Philosophy (rigid mandate)
**Purpose:** Intelligent context assessment before action routing

---

## Executive Summary

### Problem Statement

Current PM architecture mandates "ALWAYS RESEARCH before any action" (line 112, PM prompt). This is **architecturally rigid** and violates the Intelligence-First principle:

| Scenario | Current Behavior | Optimal Behavior |
|----------|------------------|------------------|
| "Yes, approve it" | Skip research (hardcoded exception) | Skip (context sufficient) |
| "Catalog this at Rs 500" [image] | **Full research** (despite clear intent) | Targeted research (validate only) |
| User provides all details explicitly | **Full research** (redundant) | Skip or minimal validation |
| "Change price to Rs 60" (mid-conversation) | **Full research** (wasteful) | Direct action (context known) |
| New user, vague request, no image | Full research | Full research (correct) |

**Core Issue:** Binary decision (research vs don't) based on **input type**, not **context sufficiency**.

### Proposed Solution

**Context Sufficiency Gate** - PM explicitly reasons about:

1. What context do I HAVE? (inventory)
2. What context do I NEED for this intent? (requirements)
3. What's the GAP? (assessment)
4. Route based on gap size (decision)

This preserves Intelligence-First (PM reasons, not follows recipe) while making decisions explicit and traceable.

---

## Architectural Design

### Current vs Proposed Flow

**CURRENT (Rigid):**

```text
User Input
    |
[Is this continuation/query/chat?]
    |
  YES --> Skip Research --> Action
    |
   NO --> FULL Research --> Synthesis --> Action
```

**PROPOSED (Intelligent):**

```text
User Input
    |
[Context Inventory] - What do I know?
    |
[Intent Classification] - What are they trying to do?
    |
[Sufficiency Assessment] - Do I have what I need?
    |
    +-- SUFFICIENT ------> Direct Action
    |
    +-- PARTIAL ---------> Targeted Research --> Action
    |
    +-- INSUFFICIENT ----> Full Research --> Synthesis --> Action
```

---

## Context Sufficiency Framework

### Phase 0: Context Inventory

PM explicitly catalogs available context:

| Context Source | Contents | Availability |
|----------------|----------|--------------|
| **Conversation History** | Past interactions, user preferences, corrections, established patterns | Always (from checkpoint) |
| **Company Context** | Brand voice, catalog summary, taxonomy, patterns | Always (middleware injection) |
| **Current Message** | Text, images, explicit parameters (prices, quantities) | Current turn |
| **Workspace** | Analyst findings from current workflow | If research already done this workflow |
| **Pending State** | HITL interrupts, approval context | If resuming workflow |

**Inventory Output (PM internal reasoning):**

```text
CONTEXT INVENTORY:
- Session: User has cataloged 5 products today, prefers brief responses
- Company: 234 SKUs, primary workflow=catalog, price range Rs 20-500
- Message: Image of bottle + "add this at Rs 45"
- Workspace: Empty (new workflow)
- Pending: None
```

### Phase 1: Intent Classification

PM classifies user intent with confidence:

| Intent Category | Examples | Typical Context Needs |
|-----------------|----------|----------------------|
| **New Product** | "add this", "catalog this" + image | Visual + Product + Catalog |
| **Modification** | "change price", "update description" | Product identity only |
| **Query** | "how many jars?", "show me X" | None (PM queries directly) |
| **Continuation** | "yes", "approve", "option 2" | None (context in pending state) |
| **Feedback** | "no, the blue one", "make it cheaper" | Correction context only |
| **Conversation** | "thanks", "ok", "hello" | None |
| **Complex/Ambiguous** | Vague request, multiple intents | Full research |

**Classification Output:**

```text
INTENT: New Product Catalog (85% confidence)
SIGNALS: Image present + "add" keyword + price specified
```

### Phase 2: Sufficiency Assessment

PM compares HAVE vs NEED:

```text
SUFFICIENCY ASSESSMENT:

NEED for "New Product Catalog":
  [ ] Visual identification (material, size, features)
  [ ] Product intelligence (naming, HSN, compliance)
  [ ] Catalog context (similar items, pricing patterns, family fit)

HAVE:
  [x] Price: Rs 45 (user specified)
  [ ] Visual: Not analyzed yet
  [ ] Product: Unknown
  [ ] Catalog: Unknown

GAP: Visual + Product + Catalog context missing
VERDICT: INSUFFICIENT - Full research needed
```

**Another Example (Partial):**

```text
SUFFICIENCY ASSESSMENT:

INTENT: Modify existing product price

NEED:
  [x] Product identity (which product)
  [x] New price (what to change to)
  [ ] Validation (does this disrupt pricing tiers?)

HAVE:
  [x] Product: "Premium Glass Jar 500ml" (from conversation)
  [x] New price: Rs 60 (user specified)
  [ ] Pricing tier impact: Unknown

GAP: Only pricing validation needed
VERDICT: PARTIAL - Targeted catalog_analyst query
```

**Continuation Example (Sufficient):**

```text
SUFFICIENCY ASSESSMENT:

INTENT: Approve pending operation

NEED:
  [x] What operation is pending
  [x] User decision (approve/reject/modify)

HAVE:
  [x] Pending: Create Premium Glass Jars family (from interrupt)
  [x] Decision: "yes, approve it"

GAP: None
VERDICT: SUFFICIENT - Proceed to execution
```

### Phase 3: Decision Routing

Based on sufficiency verdict:

| Verdict | Action | Latency Impact |
|---------|--------|----------------|
| **SUFFICIENT** | Skip research, proceed to specialist delegation | Fastest |
| **PARTIAL** | Targeted analyst call (only missing piece) | Medium |
| **INSUFFICIENT** | Full research flow (current behavior) | Slowest |

---

## Sufficiency Decision Matrix

### By Intent + Context Combination

| Intent | Has Visual | Has Product | Has Catalog | Has User Details | Verdict |
|--------|------------|-------------|-------------|------------------|---------|
| New Product + Image | No | No | No | Partial | INSUFFICIENT |
| New Product + Image | No | No | No | Full (price, name) | PARTIAL (visual only) |
| New Product + Image | Yes (workspace) | Yes | No | - | PARTIAL (catalog only) |
| New Product + Image | Yes | Yes | Yes | - | SUFFICIENT |
| Modify Existing | - | Known | No | Full | PARTIAL (validate pricing) |
| Modify Existing | - | Known | - | Full | SUFFICIENT |
| Query | - | - | - | - | SUFFICIENT (PM direct) |
| Continuation | - | - | - | - | SUFFICIENT (use pending) |
| Feedback | - | - | - | - | SUFFICIENT (apply correction) |

### Skip Research Conditions (Expanded)

**Current prompt (line 117-120):**

- Workflow continuation
- Simple data queries
- Pure conversation

**Proposed expansion:**

1. **Workflow continuation** - "yes", "approve", "option 2" (pending state has context)
2. **Simple data queries** - "how many X?", "show me Y" (PM queries directly)
3. **Pure conversation** - "thanks", "ok", greetings (no action needed)
4. **Explicit user context** - User provides all needed details (validate only)
5. **Feedback/correction** - User corrects previous output (apply delta)
6. **Modification with identity** - "change X to Y" where X is known from conversation
7. **Workspace populated** - Research already done this workflow (reuse findings)

---

## Implementation: PM Prompt Changes

### Replace Section: Research-First Philosophy

**Current (lines 108-126):**

```text
### 2. Research-First Philosophy

**Key Insight**: Research enriches EXECUTION, not just intent detection...
**ALWAYS RESEARCH before any action:**
...
**SKIP RESEARCH only for:**
- Workflow continuation
- Simple data queries
- Pure conversation
```

**Proposed Replacement:**

```xml
### 2. Context-First Decision Framework

**Key Insight**: Research fills GAPS, not checkboxes. The goal is confident action, not maximum research.

**Before every action, assess context sufficiency:**

1. INVENTORY what you know:
   - Session context (conversation history, user patterns)
   - Company context (catalog summary, taxonomy, patterns)
   - Message context (what user just provided - text, images, explicit params)
   - Workspace context (analyst findings from this workflow)
   - Pending context (HITL state if resuming)

2. CLASSIFY intent with confidence:
   - What is the user trying to do?
   - What context would I need to do it confidently?

3. ASSESS sufficiency:
   - What do I HAVE vs what do I NEED?
   - Is the gap worth research latency?

4. ROUTE based on verdict:
   - SUFFICIENT: Proceed directly to action
   - PARTIAL: Targeted research (only the gap)
   - INSUFFICIENT: Full research flow

**SUFFICIENT (skip research):**
- Continuation: "yes", "approve", "option 2" (pending state has context)
- Queries: "how many?", "show me" (PM queries directly)
- Conversation: "thanks", "ok", greetings
- Explicit context: User provided all details needed
- Corrections: "no, the blue one" (apply delta to known context)
- Modifications: "change X to Y" where X is established
- Workspace populated: Research already done this workflow

**PARTIAL (targeted research):**
- Image present but catalog context missing -> catalog_analyst only
- Product known but pricing validation needed -> catalog_analyst only
- User provided details but visual confirmation needed -> visual_analyst only

**INSUFFICIENT (full research):**
- New product with image, no conversation history
- Ambiguous request, multiple interpretations
- Complex multi-product scenario
- Cold-start user with vague input

**Why context-first?**
- 500ms research cost is justified ONLY when there's a real gap
- Redundant research wastes latency and adds no value
- Intelligence-first: You reason about sufficiency, not follow rigid rules
- User experience: Fast responses when context permits
```

---

## Examples: Context Sufficiency in Action

### Example 1: SUFFICIENT - Direct Action

**Input:** User in active workflow says "yes, approve it"

```text
CONTEXT INVENTORY:
- Session: Creating Premium Glass Jars family (from 2 turns ago)
- Pending: HITL interrupt with 3 variants at Rs 60/80/100
- Message: "yes, approve it"

INTENT: Approve pending operation (100% confidence)

SUFFICIENCY:
- NEED: What's pending + user decision
- HAVE: Both from pending state + message
- GAP: None

VERDICT: SUFFICIENT
ACTION: Resume workflow with approval, skip all research
```

### Example 2: PARTIAL - Targeted Research

**Input:** "catalog this at Rs 500" + image (user has 50+ products cataloged)

```text
CONTEXT INVENTORY:
- Session: User catalogs daily, prefers quick flow, last 5 products were jars
- Company: Catalog has 234 SKUs, jar families well-established
- Message: Image + explicit price Rs 500
- Workspace: Empty (new workflow)

INTENT: New Product Catalog (95% confidence)

SUFFICIENCY:
- NEED: Visual ID, product intelligence, catalog context, price
- HAVE: Price (Rs 500), strong user patterns, company context
- GAP: Visual identification (what IS this product?)

VERDICT: PARTIAL
ACTION: visual_analyst only -> Then assess if catalog_analyst needed
        (User pattern suggests they know their products - trust the price)
```

### Example 3: INSUFFICIENT - Full Research

**Input:** New user sends image with "help me with this"

```text
CONTEXT INVENTORY:
- Session: Empty (new user)
- Company: Primary workflow = catalog
- Message: Image + vague text
- Workspace: Empty

INTENT: Ambiguous (40% catalog, 30% question, 30% other)

SUFFICIENCY:
- NEED: Visual ID, product intelligence, catalog context, user intent
- HAVE: Image only
- GAP: Everything

VERDICT: INSUFFICIENT
ACTION: Full research flow
        visual_analyst -> product_analyst -> catalog_analyst
        Then present options (don't assume intent)
```

### Example 4: SUFFICIENT - Modification

**Input:** "change the price to Rs 60" (mid-conversation about specific product)

```text
CONTEXT INVENTORY:
- Session: Discussing "Premium Glass Jar 500ml" for last 3 turns
- Message: "change the price to Rs 60"

INTENT: Modify existing product price (100% confidence)

SUFFICIENCY:
- NEED: Product identity, new price
- HAVE: Both (from conversation + message)
- GAP: None (price validation is optional enhancement, not blocker)

VERDICT: SUFFICIENT
ACTION: Direct delegation to catalog_specialist with modification
```

---

## Architectural Benefits

| Aspect | Current (Research-First) | Proposed (Context-First) |
|--------|--------------------------|--------------------------|
| **Latency** | Fixed overhead for most requests | Adaptive - fast when possible |
| **Intelligence** | Rule-following | True reasoning |
| **User Experience** | Consistent but slow | Responsive and contextual |
| **Cost** | Higher (redundant API calls) | Lower (targeted research) |
| **Traceability** | Implicit decisions | Explicit reasoning visible |
| **Flexibility** | Rigid exceptions list | Dynamic assessment |

---

## Migration Path

### Phase 1: Prompt Update (Non-Breaking)

1. Replace "Research-First Philosophy" section with "Context-First Decision Framework"
2. Add sufficiency assessment to PM reasoning examples
3. Update skip conditions list
4. No code changes required

### Phase 2: Observability (Optional)

1. Add `sufficiency_verdict` to PM output schema
2. Log inventory/assessment for debugging
3. Track research skip rate vs outcome quality

### Phase 3: Refinement (Based on Data)

1. Tune sufficiency thresholds based on production data
2. Identify patterns where PARTIAL should become SUFFICIENT
3. Optimize targeted research combinations

---

## Validation Criteria

### Success Metrics

- **Research Skip Rate:** % of requests where research is skipped (target: 30-40%)
- **False Skip Rate:** Skipped research that should have happened (target: <5%)
- **Latency Improvement:** Average response time reduction (target: 20-30%)
- **Quality Parity:** Output quality same or better than current

### Test Scenarios

1. Continuation flows should always skip research
2. Explicit user context should skip or partial research
3. Cold-start/ambiguous should always full research
4. Mid-conversation modifications should skip research
5. New products with images should research (but targeted when possible)

---

## Comprehensive Input Scenario Matrix

### Input Components

| Component | Variants |
|-----------|----------|
| **Text** | None / Vague / Specific / Command |
| **Image** | None / Single / Multiple / Mixed (products + non-products) |
| **Session Context** | Cold (new user) / Warm (some history) / Hot (active workflow) |
| **Pending State** | None / HITL awaiting / Feedback loop |

---

### Master Verdict Matrix

```text
                    COLD START          WARM SESSION         HOT (ACTIVE FLOW)
                    ----------          ------------         -----------------
IMAGE ONLY          INSUFFICIENT        PARTIAL/INSUFF*      PARTIAL
                    (no signal)         (depends on pattern) (continuation)

TEXT ONLY
  - Vague           INSUFFICIENT        PARTIAL              PARTIAL
  - Specific        INSUFFICIENT**      SUFFICIENT           SUFFICIENT
  - Command         INSUFFICIENT**      SUFFICIENT           SUFFICIENT
  - Query           SUFFICIENT          SUFFICIENT           SUFFICIENT
  - Conversation    SUFFICIENT          SUFFICIENT           SUFFICIENT

TEXT + IMAGE
  - Vague           INSUFFICIENT        PARTIAL              PARTIAL
  - Specific        PARTIAL             PARTIAL              SUFFICIENT***
  - Full specs      PARTIAL (validate)  PARTIAL (validate)   SUFFICIENT

CONTINUATION        N/A                 SUFFICIENT           SUFFICIENT
CORRECTION          N/A                 SUFFICIENT           SUFFICIENT

* Depends on whether user pattern is strong (90%+ single domain)
** "change price to Rs 60" with no context = INSUFFICIENT (which product?)
*** If text + image align with active workflow context
```

---

### Image-Only Scenarios (Deep Dive)

| Scenario | Session | Pending | Verdict | Rationale |
|----------|---------|---------|---------|-----------|
| Image only + Cold start | New user | None | **INSUFFICIENT** | No patterns, no intent signal, must research + present options |
| Image only + Warm (catalog user) | Has history | None | **PARTIAL** | User pattern = catalog (90%), visual_analyst -> then assess |
| Image only + Warm (mixed user) | Has history | None | **INSUFFICIENT** | Can't infer intent from pattern, full research + options |
| Image only + Hot (mid-catalog flow) | Active | None | **PARTIAL** | Continuation implied, visual_analyst -> use established context |
| Image only + HITL pending | Any | Awaiting | **AMBIGUOUS** | Could be related or new - see decision tree below |
| Multiple images only + Any | Any | Any | **INSUFFICIENT** | Complex, need visual to understand grouping |

#### Image-Only Decision Tree

```text
USER SENDS: [Image only, no text]

DECISION TREE:

1. Is there HITL pending?
   YES -> Is this image related to pending operation?
          - Can't know without asking or visual analysis
          -> PARTIAL: visual_analyst to identify
          -> Then ask: "Is this related to [pending item] or a new product?"
   NO  -> Continue to step 2

2. What's the session context?
   COLD (new user):
          -> INSUFFICIENT: Full research + present options
             Response: "I see [description]. Would you like me to:
              1. Add this to your catalog
              2. Tell you more about it
              3. Something else?"

   WARM (has history):
          -> Check user pattern strength
             - 90%+ catalog intent -> PARTIAL (visual -> assume catalog)
             - Mixed patterns -> INSUFFICIENT (research + options)

   HOT (active workflow):
          -> Is this continuation of current flow?
             - Same product type -> PARTIAL (visual, use existing context)
             - Different type -> INSUFFICIENT (new workflow)

3. Image complexity?
   SINGLE clear product:
          -> Use verdict from above

   MULTIPLE items:
          -> INSUFFICIENT (need visual to understand grouping)

   MIXED (product + non-product):
          -> INSUFFICIENT (need visual to separate)

   AMBIGUOUS (can't tell what it is):
          -> INSUFFICIENT (visual + ask user)
```

---

### Text-Only Scenarios

| Scenario | Text Type | Session | Pending | Verdict | Action |
|----------|-----------|---------|---------|---------|--------|
| "yes" / "approve" / "ok" | Command | Any | HITL | **SUFFICIENT** | Resume workflow |
| "yes" / "approve" | Command | Any | None | **INSUFFICIENT** | Ask: "Approve what?" |
| "how many jars?" | Query | Any | Any | **SUFFICIENT** | PM queries directly |
| "add water bottle" | Vague command | Cold | None | **INSUFFICIENT** | Ask for image/details |
| "add water bottle" | Vague command | Warm | None | **PARTIAL** | Check existing families |
| "change price to Rs 60" | Specific command | Hot | None | **SUFFICIENT** | Product known from context |
| "change price to Rs 60" | Specific command | Cold | None | **INSUFFICIENT** | Which product? |
| "thanks" / "hello" | Conversation | Any | Any | **SUFFICIENT** | Respond, no action |
| "no, the blue one" | Correction | Hot | Any | **SUFFICIENT** | Apply delta |
| "make it cheaper" | Vague feedback | Hot | HITL | **PARTIAL** | Interpret "cheaper" |

---

### Text + Image Scenarios

| Scenario | Text | Image | Session | Verdict | Action |
|----------|------|-------|---------|---------|--------|
| "add this" + image | Vague | Single | Cold | **INSUFFICIENT** | Full research + options |
| "add this" + image | Vague | Single | Warm (catalog) | **PARTIAL** | Visual only, trust pattern |
| "catalog at Rs 500" + image | Specific | Single | Any | **PARTIAL** | Visual to confirm |
| "500ml PET bottle at Rs 500" + image | Full specs | Single | Any | **PARTIAL** | Visual to validate claims |
| "what is this?" + image | Question | Single | Any | **PARTIAL** | Visual + product, no catalog |
| "help me" + image | Vague | Single | Cold | **INSUFFICIENT** | Full research + options |
| "these are my new jars" + images | Vague | Multiple | Any | **INSUFFICIENT** | Complex grouping |
| "catalog these at Rs 45 each" + images | Specific | Multiple | Warm | **PARTIAL** | Visual to identify |

---

## Edge Cases and Special Handling

### Identified Edge Cases

| Edge Case | Description | Handling |
|-----------|-------------|----------|
| **Image during HITL** | User sends image while approval pending | Ask if related or new product |
| **Contradictory text+image** | "This glass jar" but image shows plastic | Visual validates, flag mismatch |
| **Multi-intent message** | "add this and update my jar prices" | Split intents, handle sequentially |
| **Reference to past** | "like the last one I added" | Resolve reference from history |
| **Negation** | "don't add yet, just tell me about it" | Detect intent override |
| **Partial approval** | "approve 2 and 3, change 1" | Parse partial + modification |
| **Voice note** | Audio instead of text | Transcribe -> treat as text |
| **Document/PDF** | Non-product media | Route to appropriate handler |

### Image During HITL State

**Problem:** User sends image while HITL approval is pending. Ambiguous:

- Additional angle of pending product?
- Replacement image for pending?
- Completely new product?

**Solution:**

```text
1. visual_analyst: Identify what's in the new image
2. Compare to pending context:
   - Similar product type? -> Likely related
   - Different product type? -> Likely new
3. If ambiguous, ask explicitly:
   "I see [description]. Is this:
    1. Another view of [pending item]
    2. A replacement image
    3. A new product to add separately"
```

### Multi-Intent Messages

**Problem:** "add this bottle and also update all my jar prices by 10%"

**Solution:**

```text
1. Detect multiple intents:
   - Intent A: New product catalog (image)
   - Intent B: Bulk price update (text command)

2. Assess each independently:
   - Intent A: PARTIAL (visual needed)
   - Intent B: PARTIAL (need jar count + validation)

3. Handle sequentially:
   - "I'll help with both. Let me start with the bottle..."
   - Complete A -> then handle B
```

### Reference Resolution

**Problem:** "price it like the last one I added"

**Solution:**

```text
1. Search conversation history for recent product additions
2. Extract pricing pattern from referenced product
3. Apply to current context

CONTEXT INVENTORY update:
- Reference: "last one I added" -> Premium Glass Jar at Rs 85
- Apply: Use Rs 85 as baseline for current product
```

### Contradictory Input

**Problem:** User says "glass jar" but image shows plastic container

**Solution:**

```text
1. visual_analyst identifies: Plastic container (high confidence)
2. Compare to user text: "glass jar"
3. Flag mismatch in response:
   "I see a plastic container in the image, but you mentioned 'glass jar'.
    Which is correct?
    1. It's actually plastic (use visual)
    2. It's glass (trust your description)"
```

---

## Gap Analysis Summary

| Gap | Severity | Status | Resolution |
|-----|----------|--------|------------|
| Image during HITL state | High | **RESOLVED** | Ask if related or new |
| Multi-intent messages | Medium | **RESOLVED** | Split and handle sequentially |
| Reference to past items | Medium | **RESOLVED** | History search + resolution |
| Contradictory text+image | Medium | **RESOLVED** | Visual validates, ask on mismatch |
| Image complexity detection | Medium | **RESOLVED** | Visual analyst for grouping |
| Negation detection | Low | **RESOLVED** | Intent override parsing |
| Voice note handling | Low | **NOTED** | Transcribe first |
| Document/PDF handling | Low | **NOTED** | Route to appropriate handler |

---

## Conclusion

**Context Sufficiency Gate** transforms PM from a rigid "always research" mandate to intelligent context-aware routing. This aligns with:

- **Intelligence-First:** PM reasons about needs, not follows recipes
- **ULTRATHINK:** Optimal architecture from first principles
- **User Experience:** Fast when possible, thorough when necessary

The comprehensive scenario matrix ensures all input permutations are covered, with explicit handling for edge cases like image-only inputs, HITL state conflicts, and multi-intent messages.

The change is primarily prompt-level, requiring no code modifications, making it low-risk and easily reversible.
