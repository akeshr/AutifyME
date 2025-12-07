# Hypothesis Engine: Architecture Debates

**Status**: Under Discussion
**Date**: 2025-12-07
**Purpose**: Structured decision-making for Hypothesis Engine design

---

## How to Use This Document

Each debate section contains:
- **Question**: The core decision point
- **CRITIC**: Arguments against the proposed design
- **ADVOCATE**: Arguments defending the proposed design
- **DECISION**: To be filled after discussion
- **REASONING**: Why we made this decision

Work through debates sequentially. Update DECISION and REASONING after each discussion.

---

## DEBATE 1: Is Two-Layer Separation Necessary?

### Question

Should we separate agents into Analysts (research) and Specialists (execution), or keep them merged?

### Current Proposal

```
PM -> Analysts (read-only, fast, reusable) -> Specialists (write, HITL, domain-specific)
```

### CRITIC Arguments

1. **More agents = more orchestration overhead**
   - PM coordinates analysts AND specialists
   - More tool calls, more context passing, more failure points

2. **Context loss between layers**
   - PM summarizes analyst findings for specialist
   - Specialist doesn't see raw data, only PM's interpretation
   - Information may be lost in translation

3. **Latency penalty for simple cases**
   - User: "catalog this at Rs 500" (clear intent)
   - Merged: 1 specialist call
   - Separated: PM reasons about skipping research (adds time)

4. **SubAgent invocation overhead**
   - Each analyst is a SubAgent call
   - Initialization cost, context setup, response parsing
   - Not free

5. **Research-only queries may be rare**
   - MSMEs cataloging products = action-oriented
   - "Add this" is common, "What is this?" is rare
   - Optimizing for minority case?

### ADVOCATE Arguments

1. **Orchestration is prompt-based, not code-based**
   - PM decides via reasoning, not routing code
   - No additional code complexity
   - Aligns with Intelligence-First principle

2. **Context summarization is a feature**
   - Specialist gets enriched, interpreted context
   - Doesn't need raw data
   - PM synthesis is the value-add

3. **Latency penalty is avoidable**
   - PM prompt says "SKIP RESEARCH" for clear intents
   - Two-layer doesn't force research for every query

4. **SubAgent overhead is minimal**
   - Gemini Flash init: ~50ms
   - Amortized across value provided
   - Skipped for clear intents

5. **Research-only IS common in early interactions**
   - Cold start: "what is this?" before "add this"
   - ~30-40% of messages are research-only
   - Action queries also benefit from research context

### Key Trade-offs

| Aspect | Merged | Separated |
|--------|--------|-----------|
| Prompt size | ~1000+ lines per specialist | ~300 analyst + ~600 specialist |
| Cross-domain reuse | None (duplicated) | visual_analyst serves 5 domains |
| Research-only cost | 9K tokens | 5K tokens (44% savings) |
| Research+execute cost | 9K tokens | 9K tokens (same) |
| Complexity | Lower (fewer agents) | Higher (more orchestration) |
| Scalability | Bloat per domain | Linear per domain |

### DECISION

```
[X] SEPARATED: Two-layer with analysts + specialists
```

### REASONING

```
1. Research-only queries will GROW over time (30% now -> 70% in steady state)
   - Setup phase: mostly actions (catalog creation)
   - Steady state: mostly research (queries, comparisons, trends)
   - Architecture should optimize for steady state

2. Prompt maintainability is critical
   - No appetite for 1000+ line prompts
   - Focused prompts (~300 analyst, ~600 specialist) preferred

3. Cross-domain reuse confirmed
   - visual_analyst will serve catalog, marketing, operations, quality
   - Investment in reusable analysts pays off as domains grow

4. Token economics favor separation
   - Research-only: 44% savings (5K vs 9K tokens)
   - As research queries grow, savings compound
```

**Decision Date**: 2025-12-07

---

## DEBATE 2: Analyst Granularity - How Many Analysts?

### Question

How should we scope analysts? One per capability? One per domain? Minimal set?

### Options

**Option A: Minimal Core Analysts (Proposed)**
```
visual_analyst     - All image analysis (serves catalog, marketing, ops, quality)
catalog_analyst    - Product/pricing lookup
market_analyst     - External research, HSN, competition
```

**Option B: Domain-Aligned Analysts**
```
catalog_visual_analyst     - Image analysis for catalog
catalog_data_analyst       - Catalog data lookup
marketing_visual_analyst   - Image analysis for marketing
marketing_data_analyst     - Marketing data lookup
...
```

**Option C: Capability-Aligned Analysts**
```
image_analyst       - Any image analysis
database_analyst    - Any database query
web_analyst         - Any external research
pattern_analyst     - Any pattern detection
```

### CRITIC Arguments (Against Option A)

1. **Different domains need different analysis**
   - Catalog: "What material is this?"
   - Marketing: "Is this visually appealing?"
   - Quality: "Are there defects?"
   - Same image, different questions

2. **Generic analyst may lack domain depth**
   - visual_analyst can't know catalog-specific attributes
   - May miss domain-relevant details

3. **Prompt tries to serve too many masters**
   - "Observe materials" (catalog)
   - "Assess aesthetic appeal" (marketing)
   - "Check for damage" (quality)
   - Conflicting priorities in one prompt

### ADVOCATE Arguments (For Option A)

1. **Analysts return OBSERVATIONS, not interpretations**
   - "Materials: brass, Style: Art Deco, Condition: good"
   - Catalog uses: material for categorization
   - Marketing uses: style for copy
   - Same observation, different usage

2. **Domain-specific interpretation happens in PM**
   - PM knows the domain context
   - PM interprets analyst findings for that domain
   - Analyst stays generic

3. **Cross-domain reuse is the whole point**
   - visual_analyst saves ~800 lines of duplication
   - If we create domain-specific, we lose the benefit

4. **Can specialize later if needed**
   - Start minimal
   - If visual_analyst fails to serve marketing well, split then
   - Architecture allows specialization

### DECISION

```
[X] Option A: Minimal Core Analysts (3 analysts)
    - visual_analyst (all image analysis)
    - catalog_analyst (product/pricing queries)
    - market_analyst (external research)
```

### REASONING

```
1. Start simple, prove cross-domain reuse works
   - visual_analyst serves catalog, marketing, ops, quality
   - Same observation ("brass, Art Deco"), different usage per domain
   - PM interprets findings for domain context

2. Split later if needed
   - If visual_analyst fails to serve marketing well, create marketing_visual_analyst
   - Architecture allows specialization without redesign

3. Complexity management
   - 3 analysts vs 10+ is significant difference
   - Fewer agents = easier maintenance, testing, debugging

4. Aligns with ULTRATHINK principle
   - Don't over-engineer for hypothetical needs
   - Build minimal, validate, expand
```

**Decision Date**: 2025-12-07

---

## DEBATE 3: Chained vs Parallel Analyst Execution

### Question

When multiple analysts are needed, should they run in chain (sequential with context passing) or parallel?

### Current Proposal

```
CHAINED: visual_analyst -> catalog_analyst (visual findings inform catalog search)
PARALLEL: visual_analyst + market_analyst (independent domains)
```

### CRITIC Arguments (Against Chaining)

1. **Latency accumulates**
   - visual_analyst: 300ms
   - catalog_analyst: 200ms
   - Total: 500ms minimum
   - Parallel could be 300ms

2. **Single point of failure**
   - visual_analyst fails -> catalog_analyst gets nothing
   - Chain breaks, research fails

3. **Complexity in PM orchestration**
   - PM must know which analysts depend on others
   - Must sequence calls correctly
   - More prompt complexity

### ADVOCATE Arguments (For Chaining)

1. **Precision outweighs latency**
   - Without visual: catalog_analyst searches "handle" (broad)
   - With visual: catalog_analyst searches "brass Art Deco door handle 1930s" (precise)
   - 200ms extra for much better results

2. **Fallback is designed**
   - visual_analyst fails -> fall back to user text
   - Chain doesn't break, degrades gracefully

3. **PM handles this naturally**
   - "First visual, then catalog WITH visual context"
   - Not complex - just sequencing in prompt
   - LLMs handle sequence well

4. **Parallelism where appropriate**
   - visual + market = parallel (no dependency)
   - visual -> catalog = chained (has dependency)
   - Best of both

### Key Question

Is the precision gain from chaining worth the latency cost?

**Without chaining:**
- catalog_analyst searches: "handle" -> finds 50 items, noisy
- PM has to filter/guess

**With chaining:**
- catalog_analyst searches: "brass Art Deco door handle 15cm" -> finds 3 items, precise
- PM has clear recommendation

### DECISION

```
[X] HYBRID: Chain when dependency exists, parallel otherwise

Dependencies (CHAIN):
  - visual_analyst -> catalog_analyst (visual informs search)
  - visual_analyst -> market_analyst (visual informs market lookup)

Independent (PARALLEL):
  - catalog_analyst + market_analyst (after visual context available)
```

### REASONING

```
1. Precision outweighs 200ms latency
   - Without context: catalog_analyst searches "product" -> 50 noisy results
   - With context: catalog_analyst searches "brass Art Deco handle" -> 3 precise results
   - Better results = better user experience

2. Parallelism where appropriate
   - Once visual context exists, catalog + market can run parallel
   - Best of both: precision AND speed optimization

3. PM handles naturally
   - "First visual, then catalog WITH visual context"
   - LLMs handle sequencing well via prompt guidance
   - No complex orchestration code needed

4. Fallback preserves resilience
   - If visual_analyst fails, catalog_analyst falls back to user text
   - Chain doesn't break, degrades gracefully
```

**Decision Date**: 2025-12-07

---

## DEBATE 4: How Does PM Know When to Skip Research?

### Question

What signals should PM use to decide "clear intent, skip research" vs "ambiguous, do research"?

### Current Proposal

**SKIP RESEARCH when:**
- Explicit command: "catalog this at Rs 500"
- Follow-up: "yes, approve it"
- Simple query: "how many products do I have?"
- User history + input strongly align (>95% pattern match)

**DO RESEARCH when:**
- Minimal input: Just an image, no text
- Ambiguous intent: "what do you think?"
- New user: No history
- Mixed signals: Image + text don't align

### CRITIC Arguments

1. **"95% pattern match" is vague**
   - How does PM calculate this?
   - LLMs aren't reliable at self-confidence estimation
   - May skip research when shouldn't

2. **"Explicit command" can still be ambiguous**
   - "catalog this" - but where? which family?
   - "at Rs 500" - MRP? wholesale? both?
   - Clear intent != complete information

3. **False positives are costly**
   - PM skips research, makes wrong assumption
   - User has to correct
   - Worse UX than slightly slower correct response

4. **Warm user may want something different**
   - User cataloged 10 items
   - PM assumes "catalog" for item 11
   - But user wants appraisal this time
   - History misleads

### ADVOCATE Arguments

1. **Pattern match is qualitative, not quantitative**
   - PM reasons: "User has cataloged 10/10 items, text says 'add this', image is product"
   - Not calculating percentage, just reasoning about alignment
   - LLMs are good at this

2. **Incomplete information != ambiguous intent**
   - "catalog this" = clear INTENT, missing DETAILS
   - Specialist can fill details (family, pricing)
   - Research is for intent, not details

3. **Correction cost is low**
   - PM invites correction: "Am I reading this right?"
   - User says "no, appraise" - single word
   - Learning happens, future is better

4. **Research cost is high for clear cases**
   - Every "yes, approve" triggers research?
   - Every "catalog this at Rs 500" analyzes image?
   - Wasteful

### Concrete Examples

| Input | History | Skip? | Why |
|-------|---------|-------|-----|
| "yes" | Pending approval | YES | Continuing workflow |
| "catalog this at Rs 500" + image | Catalogs often | YES | Explicit intent + price |
| "add this" + image | Catalogs often | MAYBE | Implicit intent |
| image only | Catalogs often | NO | No text signal |
| "what is this?" | Any | NO | Question, not command |
| "add this" + image | New user | NO | No history |

### DECISION

```
[X] RESEARCH-FIRST: Always research before any action

SKIP RESEARCH only for:
  - Workflow continuation: "yes, approve" (already researched)
  - Simple data query: "how many products?" (PM queries directly)
  - Pure conversation: "thanks", "ok" (no action needed)

DO RESEARCH for everything else, including clear intent:
  - "catalog this at Rs 500" -> still research (duplicate check, family, enrichment)
  - "add this" -> research (intent + enrichment)
  - Any image input -> always visual_analyst first
```

### REASONING

```
1. Research enriches execution, not just intent detection
   - Even clear "catalog this at Rs 500" benefits from:
     - Duplicate check (does this already exist?)
     - Family selection (which family fits best?)
     - Similar pricing (is Rs 500 consistent with similar items?)
   - Research makes the ACTION better

2. PM should ask (research) then decide
   - Informed decisions > fast assumptions
   - Research cost (500ms) is small vs poor execution cost

3. Minimal skip criteria
   - Only skip when research adds zero value:
     - "yes" to pending approval (already researched)
     - Simple count/list queries (no action involved)
   - Everything else benefits from research context

4. Aligns with suggestive agent philosophy
   - PM comes to user with researched recommendations
   - Not reactive execution, proactive intelligence
```

**Decision Date**: 2025-12-07

---

## DEBATE 5: Specialist Slimdown - How Much to Remove?

### Question

How much research capability should we remove from specialists when creating the two-layer model?

### Current State

catalog_specialist.prompt (~824 lines) contains:
- Schema discovery workflow (inspect_schema first)
- Research patterns (read_data, aggregate_data examples)
- Market research patterns (research_product_tool)
- Execution patterns (write_data, HITL)
- Examples for research + execution combined

### Options

**Option A: Complete Removal**
- Remove ALL research patterns
- Specialist only receives context, only executes
- ~400 lines saved

**Option B: Minimal Research Retained**
- Remove examples and detailed patterns
- Keep basic read_data capability for edge cases
- ~200 lines saved

**Option C: Research Available but Discouraged**
- Keep research tools
- Prompt says "prefer context from PM, only research if missing"
- ~100 lines saved

### CRITIC Arguments (Against Complete Removal)

1. **Edge cases need specialist research**
   - PM provides context but specialist discovers gap
   - "Wait, this SKU already exists" - needs to check
   - Without research tools, specialist is blind

2. **Validation requires data access**
   - Specialist validates proposed action
   - "Is product_family_id valid?" - needs read_data
   - Can't validate without querying

3. **PM can't anticipate everything**
   - PM passes "add to Vintage Hardware family"
   - But what if that family is discontinued?
   - Specialist needs to verify

### ADVOCATE Arguments (For Complete Removal)

1. **Validation is a tool call, not research**
   - Specialist keeps read_data TOOL
   - Removes research PATTERNS (examples, workflow guidance)
   - Can still query, just not elaborate research flows

2. **PM should handle gaps**
   - If specialist finds gap, tell PM
   - PM spawns appropriate analyst
   - Keep responsibility clear

3. **Prompt bloat is the problem**
   - It's not about removing tools
   - It's about removing 300 lines of "how to research" examples
   - Execution examples stay

### Clarification

**Tools vs Patterns:**
- Tools: read_data, aggregate_data (keep in specialist)
- Patterns: "STEP 1: inspect_schema, STEP 2: search for duplicates..." (remove from specialist)

### DECISION

```
[X] Option A: Remove research PATTERNS, keep ALL tools

REMOVE from specialist prompts:
  - Research workflow guidance ("STEP 1: inspect_schema...")
  - "How to find similar products" patterns
  - Market research examples
  - Elaborate research examples
  - ~300 lines saved

KEEP in specialist:
  - ALL tools: read_data, aggregate_data, inspect_schema, write_data
  - Validation examples ("check if SKU exists before creating")
  - Schema lookup examples ("inspect columns before writing")
  - Execution patterns with HITL
```

### REASONING

```
1. Tools needed for validation and detail gathering
   - Specialist may need to cross-check during execution
   - "Does this SKU already exist?" - needs read_data
   - "What columns does this table have?" - needs inspect_schema
   - "Need more details on this family" - needs read_data

2. PM provides context, but specialist may need more
   - PM gives: "Similar items at Rs 450-650, family: Vintage Hardware"
   - Specialist may still need: exact column names, validation of family_id
   - Tools enable self-sufficiency without re-delegating to PM

3. Patterns vs Tools distinction
   - PATTERNS removed: "How to research the catalog" workflows
   - TOOLS kept: Ability to query when needed for execution accuracy
   - Specialist is execution-focused but not blind

4. Efficiency maintained
   - PM provides rich context from analysts
   - Specialist validates/enriches only what's needed
   - No duplicate research, just execution-time verification
```

**Decision Date**: 2025-12-07

---

## DEBATE 6: User Essence - Storage and Update Triggers

### Question

How should user essence (compressed patterns) be stored and when should it be updated?

### Current Proposal

- Storage: Simple text field in users table (~200 tokens)
- Update trigger: PM decides "when patterns shift significantly"
- Format: Natural language summary of patterns

### CRITIC Arguments

1. **"PM decides" is too vague**
   - When is a shift "significant"?
   - PM might never update
   - PM might update too often
   - No consistent behavior

2. **Text field is unstructured**
   - Hard to parse for debugging
   - Can't query patterns across users
   - No schema enforcement

3. **PM generating its own memory is risky**
   - PM might be wrong about patterns
   - Wrong essence leads to wrong future inferences
   - Self-reinforcing errors

4. **No versioning or rollback**
   - Essence gets corrupted
   - No way to recover previous state
   - User stuck with bad inference

### ADVOCATE Arguments

1. **"PM decides" aligns with Intelligence-First**
   - We trust PM to reason about many things
   - Pattern shift detection is one more thing
   - Explicit triggers would be code we don't need

2. **Unstructured is flexible**
   - Patterns evolve, schema would constrain
   - Natural language is debuggable (human-readable)
   - Can always add structure later

3. **PM has full context**
   - PM sees all interactions
   - Best positioned to synthesize patterns
   - External system would have less context

4. **Rollback is conversation history**
   - If essence is wrong, conversation history is truth
   - PM can regenerate from history
   - Not dependent on essence alone

### Alternative: Explicit Update Triggers

```python
# Instead of "PM decides"
UPDATE_TRIGGERS = [
    "user corrects PM assumption",
    "new workflow pattern (3+ instances)",
    "price range changes significantly",
    "every 20 interactions (periodic)"
]
```

### DECISION

```
[X] DEFER TO FRAMEWORK: Leverage DeepAgents built-in summarization middleware
```

### REASONING

```
1. DeepAgents provides built-in memory/summarization middleware
   - Handles conversation context compression automatically
   - Manages long-running session state
   - No need to reinvent existing framework capability

2. Avoid premature optimization
   - Custom essence management adds complexity
   - Framework solution is battle-tested
   - Can layer custom strategy on top later if needed

3. Focus on core architecture first
   - User patterns will emerge from usage
   - DeepAgents middleware captures these naturally
   - Custom extraction/storage is future enhancement

4. Revisit when limitations surface
   - If framework summarization proves insufficient
   - If cross-session pattern persistence needed beyond framework
   - Design custom solution with real usage data informing requirements
```

**Decision Date**: 2025-12-07

---

## DEBATE 7: Cold Start - Company Patterns Source

### Question

Where should company patterns (baseline for new users) come from?

### Current Proposal

```python
class CompanyPatterns(BaseModel):
    common_intents: list[str]  # ["catalog", "pricing", "export"]
    common_categories: list[str]  # ["PET bottles", "jars", "containers"]
    typical_price_range: tuple[float, float]  # (50, 500)
    typical_user_journey: str  # "image -> catalog -> price -> export"
```

But WHERE does this data live?

### Options

**Option A: Static Config File**
- `config/company_patterns.json`
- Loaded at startup
- Updated manually

**Option B: Derived from Database**
- Query aggregate patterns on startup
- "Most common product types", "Average price range"
- Always current

**Option C: Stored in Companies Table**
- Column on companies table
- Admin can configure
- Persisted

**Option D: Inferred from First Users**
- No initial patterns
- After 10 users, derive patterns
- Bootstrap problem

### CRITIC Arguments

1. **Static config becomes stale**
   - Company evolves, config doesn't
   - Manual updates forgotten
   - Mismatch grows over time

2. **Database derivation is slow**
   - Query aggregates on every startup?
   - Or cache with staleness risk?

3. **Companies table adds schema complexity**
   - Another field to maintain
   - Need admin UI to configure
   - Overkill for single-tenant?

### ADVOCATE Arguments

1. **Static config is simplest**
   - Single-tenant = one company
   - Config changes with deployment
   - Good enough for now

2. **Can evolve later**
   - Start static
   - Move to DB-derived when needed
   - Architecture doesn't constrain

### DECISION

```
[X] ENHANCE EXISTING: Extend company context middleware with pattern data
```

### REASONING

```
1. Company context middleware already exists
   - Infrastructure for loading company-level context is in place
   - Adding pattern fields is incremental, not greenfield
   - Avoids duplicate systems (config file + middleware)

2. Single source of truth
   - All company context flows through one middleware
   - Patterns live alongside other company data
   - PM receives unified context injection

3. Database-backed enables flexibility
   - Admin can update patterns without redeployment
   - Patterns can evolve based on usage analytics
   - Future: auto-derive from company's actual catalog data

4. Enhancement scope
   - Add to existing company context:
     - common_intents: list[str]
     - product_categories: list[str]
     - typical_price_range: tuple[float, float]
     - default_currency: str
   - Middleware loads these with existing company context
```

**Decision Date**: 2025-12-07

---

## DEBATE 8: Confidence Levels - How Many? What Names?

### Question

How should PM express confidence, and how many levels are useful?

### Current Proposal

| Level | Name | Strategy |
|-------|------|----------|
| High | DIRECT_ACTION | "I'll do X. Proceed?" |
| Medium | LEAD_WITH_TOP | "I think X because... Or: Y, Z" |
| Low | PRESENT_OPTIONS | "Options: 1, 2, 3. Which?" |
| Very Low | OBSERVE_AND_ASK | "I see X. What would you like?" |

### CRITIC Arguments

1. **Four levels is too many**
   - PM has to decide between "Low" and "Very Low"
   - Subtle distinction, may be inconsistent
   - Three levels (High/Medium/Low) is simpler

2. **"Very Low" should just ask**
   - If confidence is very low, don't present observations
   - Just ask: "What would you like to do?"
   - Over-explaining uncertainty is confusing

3. **Response templates are rigid**
   - PM should respond naturally
   - Templates make responses formulaic
   - "Am I reading this right?" gets repetitive

### ADVOCATE Arguments

1. **Four levels capture real situations**
   - Sometimes you're PRETTY sure but not certain (Medium)
   - Sometimes you have SOME idea but multiple options (Low)
   - Sometimes you're LOST (Very Low)
   - Each needs different response

2. **Observations help even at Very Low**
   - User knows PM tried
   - "I see a metal object" is better than "What is this?"
   - Shows effort, builds trust

3. **Templates are guidance, not scripts**
   - PM can vary wording
   - Structure is consistent, words vary
   - "Am I reading this right?" vs "Does that sound right?" etc.

### Alternative: Three Levels

| Level | Strategy |
|-------|----------|
| High | Direct action with confirmation |
| Medium | Recommendation with alternatives |
| Low | Options or open question |

### DECISION

```
[X] LLM INTELLIGENCE: Trust PM to naturally calibrate confidence in responses
```

### REASONING

```
1. Aligns with Intelligence-First principle
   - "Trust intelligence over control"
   - LLMs naturally express uncertainty through language
   - Rigid tiers add scaffolding we don't need

2. Natural language handles confidence well
   - "I'll catalog this at Rs 450" (high confidence)
   - "I think this might be..." (medium)
   - "I'm not sure, but..." (low)
   - PM does this naturally without explicit tier logic

3. Prompt guidance over prescription
   - Prompt says: "Be transparent about uncertainty"
   - Prompt says: "Offer alternatives when unsure"
   - PM reasons about HOW to express, not WHICH tier to use

4. Avoids false precision
   - 4 tiers implies we can reliably distinguish "low" from "very low"
   - LLMs aren't calibrated for such fine distinctions
   - Natural expression is more authentic

5. Implementation simplicity
   - No confidence level enum in code
   - No tier-to-response-template mapping
   - Just good prompting
```

**Decision Date**: 2025-12-07

---

## DEBATE 9: When to Use market_analyst?

### Question

When should PM spawn market_analyst (external research) vs relying on catalog_analyst (internal data)?

### Current Proposal

- market_analyst: HSN codes, GST rates, competitor pricing, market trends
- catalog_analyst: Internal products, pricing patterns, families

### Scenarios

| Scenario | Use market_analyst? |
|----------|---------------------|
| Catalog new product, similar items exist | NO - catalog_analyst has pricing |
| Catalog new product, no similar items | YES - need market rate |
| User asks "is this price competitive?" | YES - need external comparison |
| User asks "what's the HSN code?" | YES - regulatory data |
| User asks "price this like my other jars" | NO - internal pattern |
| Appraisal request | YES - market valuation |

### CRITIC Arguments

1. **External research is slow and unreliable**
   - Web search latency: 500-1000ms
   - Results may be outdated or wrong
   - Not worth the delay for most cases

2. **Catalog patterns are better for pricing**
   - User's own data is most relevant
   - "Price like my other jars" is what users want
   - Market rate may not apply

3. **HSN codes should be cached**
   - Static data, doesn't change
   - Query once, store in database
   - No need for repeated external calls

### ADVOCATE Arguments

1. **External research is essential for gaps**
   - New product category? Need market rate
   - Appraisal? Need auction data
   - No internal data to rely on

2. **Market context is valuable**
   - "Your price is 20% below market" is useful
   - Proactive suggestion potential
   - Differentiates AutifyME from dumb catalog tool

3. **Can optimize later**
   - Start with external research
   - Cache common queries
   - Build HSN database over time

### DECISION

```
[X] RENAME + MODERATE: Rename to product_analyst, use for product knowledge enrichment
```

### REASONING

```
1. Rename market_analyst -> product_analyst
   - "market" implies competition/pricing only
   - "product" captures the real need: detailed product knowledge
   - Mental model: visual (what I see) + catalog (what we have) + product (what it IS)

2. Product analyst scope
   - Proper industry naming conventions
   - Standard sizes, dimensions, capacities
   - Material specifications and variants
   - Industry classifications (HSN, categories)
   - Usage patterns and applications
   - Related products and accessories

3. When to use product_analyst
   - New product cataloging (always - enriches the entry)
   - Existing product with sparse details (fill gaps)
   - User asks for product specifications
   - Classification/taxonomy questions
   - Quality/standards questions

4. Addresses current struggle
   - System lacks detailed product analysis capability
   - Proper naming, sizing, usage info is missing
   - product_analyst becomes the domain knowledge expert

5. Updated 3-analyst model
   - visual_analyst: "What do I SEE?" (image observation)
   - catalog_analyst: "What do we HAVE?" (internal data)
   - product_analyst: "What IS this?" (external product knowledge)
```

**Decision Date**: 2025-12-07

---

## DEBATE 10: Error Handling - How Graceful?

### Question

When analysts fail, how should PM respond?

### Current Proposal

Cascade of fallbacks:
1. Single analyst fails -> proceed with other analysts
2. Chained analyst fails -> fall back to user text
3. All analysts fail -> OBSERVE_AND_ASK

### Scenarios

**Scenario A: visual_analyst fails (blurry image)**
```
Proposed response:
"The image is a bit unclear. I can see it might be a handle but can't make out details.
Could you send a clearer photo, or describe what it is?"
```

**Scenario B: catalog_analyst fails (database error)**
```
Proposed response:
"I can see this is a brass Art Deco handle.
I'm having trouble checking your catalog right now - would you like me to try again,
or proceed with a new listing?"
```

**Scenario C: All analysts fail**
```
Proposed response:
"I'm having trouble analyzing this right now.
Can you describe what you'd like to do with it?"
```

### CRITIC Arguments

1. **Fallbacks hide problems**
   - User doesn't know system is degraded
   - Keeps using system with poor results
   - Should surface errors clearly

2. **Graceful degradation is complex**
   - Each failure mode needs handling
   - Many code paths to test
   - Bugs hide in error paths

3. **"Try again" is annoying**
   - Transient errors are rare
   - "Try again" usually fails again
   - User loses trust

### ADVOCATE Arguments

1. **Transparency is built in**
   - "I'm having trouble with X" is honest
   - User knows something is wrong
   - Can decide to retry or work around

2. **Graceful degradation is better UX**
   - Complete failure is worse
   - Partial results are useful
   - "I can see the image but can't check your catalog" is helpful

3. **Retry option is user choice**
   - Offer retry, don't force
   - User can say "proceed without catalog check"
   - Agency preserved

### DECISION

```
[X] LLM INTELLIGENCE: Trust PM to reason about failures and respond contextually
```

### REASONING

```
1. Consistent with architecture philosophy
   - Debates 6, 8 also chose "trust LLM intelligence"
   - Error handling belongs in intelligence layer, not scaffolding
   - PM has context to reason about each failure uniquely

2. Prompt guidance over code-based fallbacks
   - "When an analyst fails, explain what you learned and what you couldn't"
   - "Offer user options: retry, proceed with partial info, provide more input"
   - "Be transparent - don't pretend you have information you don't"

3. Context-aware responses
   - visual_analyst fails (blurry) -> "Image unclear, can you resend?"
   - product_analyst fails (timeout) -> "I see [visual], couldn't research. Proceed?"
   - catalog_analyst fails (DB error) -> "I know what this IS, couldn't check inventory"

4. Each failure is unique
   - Error type matters (timeout vs not found vs invalid)
   - User input quality matters
   - Partial results from other analysts matter
   - PM synthesizes contextual, natural response

5. No rigid fallback chains in code
   - Avoids complex error handling logic
   - PM adapts to situation
   - Graceful degradation emerges from intelligence
```

**Decision Date**: 2025-12-07

---

## Summary: Decision Tracking

| Debate | Question | Decision | Status |
|--------|----------|----------|--------|
| 1 | Two-layer separation? | SEPARATED (Analysts + Specialists) | DECIDED |
| 2 | Analyst granularity? | Minimal Core (3 analysts) | DECIDED |
| 3 | Chained vs parallel? | HYBRID (chain when dependency) | DECIDED |
| 4 | When to skip research? | RESEARCH-FIRST (always research before action) | DECIDED |
| 5 | Specialist slimdown? | Remove patterns, keep ALL tools | DECIDED |
| 6 | User essence storage? | Defer to DeepAgents framework | DECIDED |
| 7 | Company patterns source? | Enhance existing middleware | DECIDED |
| 8 | Confidence levels? | LLM Intelligence (natural expression) | DECIDED |
| 9 | When to use market_analyst? | Rename to product_analyst, keep separate from catalog_analyst | DECIDED |
| 10 | Error handling? | LLM Intelligence (contextual responses) | DECIDED |

---

## Final Architecture Summary

**Two-Layer Model:**
- **Analysts** (Research, Read-only, Fast, Cross-domain reusable)
- **Specialists** (Execution, HITL, Domain-specific)

**3 Analysts:**
- `visual_analyst`: "What do I SEE?" (image observation)
- `product_analyst`: "What IS this?" (external product knowledge)
- `catalog_analyst`: "What do we HAVE?" (internal data)

**Key Principles Applied:**
- Intelligence-First: Trust LLM reasoning over rigid rules
- Research-First: Always research before action
- Prompt guidance over code scaffolding
- Leverage existing infrastructure (DeepAgents, middleware)

**Decision Date**: 2025-12-07
**Status**: All debates concluded - ready for implementation planning
