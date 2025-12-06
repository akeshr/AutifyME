# Hypothesis Engine: Intent Detection from Minimal Input

**Status**: Design Proposal
**Date**: 2025-12-06
**Author**: Jarvis + Human Architect

---

## Executive Summary

The Hypothesis Engine is a pre-reasoning layer that transforms minimal user input (single image, vague message) into ranked intent hypotheses with confidence scores. Instead of asking clarifying questions, the system demonstrates intelligence by:

1. **Observing** - Extracting rich features from limited input
2. **Inferring** - Generating plausible intent hypotheses
3. **Researching** - Gathering context to rank hypotheses
4. **Suggesting** - Presenting options that show understanding

**Core Philosophy**: Intelligence is demonstrated through inference, not interrogation.

---

## Problem Statement

### Current Limitation

```
User: [sends single product image]
Current PM: "What would you like to do with this image?"
```

The system has information (image features, user history, business context) but doesn't use it proactively.

### Desired Behavior

```
User: [sends single product image]
Hypothesis Engine: Extracts features, generates hypotheses, researches context
PM Response: "I see a vintage brass door handle, Art Deco style, ~1930s.

Based on your recent activity (3 antique hardware listings this week):
1. **Catalog for sale** - Similar handles in your catalog: Rs 450-650 range
2. **Get appraisal** - I can pull auction records for valuation
3. **Add to existing family** - Matches your 'Vintage Hardware' collection

Which direction?"
```

---

## Architecture Overview

```
                    +-------------------+
                    |   User Input      |
                    | (image/text/both) |
                    +--------+----------+
                             |
                             v
+----------------+   +-------+--------+   +------------------+
| Feature        |   | Hypothesis     |   | Context          |
| Extractor      |-->| Generator      |<--| Aggregator       |
| (Multi-Modal)  |   | (LLM-based)    |   | (User + Business)|
+----------------+   +-------+--------+   +------------------+
                             |
                             v
                    +--------+----------+
                    | Hypothesis        |
                    | Ranker            |
                    | (Evidence-based)  |
                    +--------+----------+
                             |
                             v
                    +--------+----------+
                    | Response          |
                    | Formatter         |
                    | (Confidence-aware)|
                    +--------+----------+
                             |
                             v
                    +--------+----------+
                    |   PM Orchestrator |
                    | (Enriched Input)  |
                    +-------------------+
```

---

## Component Design

### 1. Feature Extractor (Multi-Modal)

Extracts structured signals from raw input in parallel.

#### Visual Feature Extraction

```python
class VisualFeatures(BaseModel):
    """Structured features extracted from image."""

    # Object Detection
    primary_object: str  # "brass door handle"
    secondary_objects: list[str]  # ["mounting plate", "screws"]
    object_count: int  # 1

    # Material Analysis
    materials: list[str]  # ["brass", "metal"]
    material_confidence: float  # 0.85

    # Style/Era Detection
    style_period: str | None  # "Art Deco"
    estimated_era: str | None  # "1920s-1940s"
    style_confidence: float  # 0.7

    # Condition Assessment
    condition: str  # "good", "fair", "excellent"
    condition_notes: list[str]  # ["patina present", "minor wear"]

    # Technical Details
    estimated_dimensions: str | None  # "~15cm length"
    color_palette: list[str]  # ["gold", "brown", "oxidized"]

    # Visual Quality
    image_quality: str  # "high", "medium", "low"
    lighting_quality: str  # "good", "poor"
    background_type: str  # "plain", "contextual", "cluttered"
```

#### Text Feature Extraction

```python
class TextFeatures(BaseModel):
    """Structured features extracted from text."""

    # Intent Signals
    action_verbs: list[str]  # ["catalog", "add", "price"]
    question_type: str | None  # "how_much", "what_is", "can_you"
    urgency_level: str  # "normal", "urgent", "casual"

    # Entity Extraction
    mentioned_prices: list[str]  # ["Rs 450"]
    mentioned_quantities: list[int]  # [5]
    mentioned_products: list[str]  # ["door handle"]
    mentioned_categories: list[str]  # ["hardware"]

    # Sentiment/Tone
    sentiment: str  # "neutral", "positive", "frustrated"
    formality: str  # "casual", "formal"

    # Completeness
    has_explicit_intent: bool  # False for "help with this"
    missing_info: list[str]  # ["price", "quantity", "category"]
```

#### Implementation Strategy

**Option A: Dedicated Vision Model (Fast, Limited)**
- Use lightweight vision model (e.g., CLIP, ViT) for object/material detection
- Pros: Fast (<100ms), consistent
- Cons: Limited to trained categories

**Option B: LLM Vision (Flexible, Slower)**
- Use multi-modal LLM (GPT-4V, Gemini) with structured output
- Pros: Flexible, understands context
- Cons: Slower (~500ms), more expensive

**Recommendation: Hybrid Approach**
- Fast classifier for common categories (product types, materials)
- LLM fallback for unusual/complex images
- Parallel execution - use whichever returns first with confidence > threshold

```python
async def extract_visual_features(image: bytes) -> VisualFeatures:
    """Extract visual features using hybrid approach."""

    # Launch both in parallel
    classifier_task = asyncio.create_task(fast_classifier(image))
    llm_task = asyncio.create_task(llm_vision_analysis(image))

    # Use fast classifier if confident
    classifier_result = await classifier_task
    if classifier_result.confidence > 0.8:
        llm_task.cancel()
        return classifier_result

    # Fall back to LLM for complex cases
    return await llm_task
```

---

### 2. Context Aggregator

Gathers all available context to inform hypothesis generation.

#### Context Sources

```python
class AggregatedContext(BaseModel):
    """All available context for hypothesis generation."""

    # Business Context (from PMBaseContext)
    company_profile: CompanyProfile
    catalog_summary: CatalogSummary
    taxonomy_tree: TaxonomyTree

    # User Context (NEW - needs implementation)
    user_profile: UserProfile | None
    recent_interactions: list[InteractionSummary]
    user_patterns: UserPatterns | None

    # Conversation Context
    conversation_history: list[MessageSummary]
    pending_workflows: list[str]

    # Temporal Context
    time_of_day: str  # "morning", "afternoon", "evening"
    day_of_week: str
    is_business_hours: bool

    # Platform Context
    platform: str  # "whatsapp"
    message_type: str  # "text", "image", "voice"
```

#### User Profile & Patterns (New Schema)

```python
class UserProfile(BaseModel):
    """User-specific context learned over time."""

    user_id: str
    first_interaction: datetime
    total_interactions: int

    # Preferences (learned)
    preferred_response_style: str  # "detailed", "brief"
    preferred_categories: list[str]  # ["hardware", "furniture"]
    typical_price_range: tuple[float, float] | None

    # Behavioral Patterns
    typical_request_types: list[str]  # ["catalog", "pricing"]
    avg_images_per_session: float
    approval_rate: float  # How often they approve vs reject

    # Communication Style
    uses_voice_notes: bool
    typical_message_length: str  # "brief", "detailed"
    language_preference: str  # "en", "hi", "mixed"


class UserPatterns(BaseModel):
    """Patterns detected from user history."""

    # Recent Activity
    recent_categories: list[str]  # Last 7 days
    recent_actions: list[str]  # ["cataloged", "priced", "exported"]

    # Sequence Patterns
    common_workflows: list[str]  # ["image -> catalog -> price"]
    time_between_actions: float  # avg minutes

    # Interaction Patterns
    correction_rate: float  # How often they correct system
    common_corrections: list[str]  # ["wrong category", "wrong price"]
```

#### Context Loading Strategy

```python
async def aggregate_context(
    user_id: str,
    thread_id: str,
    company_id: str,
) -> AggregatedContext:
    """Load all context in parallel."""

    # Parallel loading - all independent
    business_ctx, user_ctx, conv_ctx = await asyncio.gather(
        load_business_context(company_id),  # ~50ms (cached)
        load_user_context(user_id),          # ~100ms (DB query)
        load_conversation_context(thread_id), # ~50ms (checkpointer)
    )

    return AggregatedContext(
        **business_ctx,
        **user_ctx,
        **conv_ctx,
        time_of_day=get_time_of_day(),
        platform="whatsapp",
    )
```

---

### 3. Hypothesis Generator

Generates ranked intent hypotheses from features + context.

#### Hypothesis Schema

```python
class IntentHypothesis(BaseModel):
    """Single intent hypothesis with evidence."""

    # Core
    intent_type: str  # "catalog_product", "get_appraisal", "ask_question"
    intent_description: str  # Human-readable description

    # Confidence
    confidence: float  # 0.0 to 1.0
    confidence_reasoning: str  # Why this confidence level

    # Evidence
    supporting_evidence: list[str]  # ["user cataloged 3 similar items this week"]
    contradicting_evidence: list[str]  # ["no price mentioned"]

    # Action
    suggested_specialist: str | None  # "catalog_specialist"
    suggested_action: str  # "Extract and catalog with pricing research"

    # Follow-up (if needed)
    clarification_needed: list[str]  # ["price", "quantity"]
    clarification_priority: str  # "optional", "recommended", "required"


class HypothesisSet(BaseModel):
    """Ranked set of hypotheses."""

    hypotheses: list[IntentHypothesis]  # Sorted by confidence

    # Meta
    total_confidence: float  # Sum of all confidences (should be ~1.0)
    dominant_hypothesis: bool  # True if top hypothesis >> others
    ambiguity_level: str  # "low", "medium", "high"

    # Observations (what system noticed)
    key_observations: list[str]  # ["vintage brass handle", "Art Deco style"]

    # Generation metadata
    features_used: list[str]  # ["visual", "text", "user_history"]
    generation_time_ms: int
```

#### Generation Strategy

**Approach: LLM with Structured Output**

The hypothesis generation is fundamentally a reasoning task - perfect for LLM.

```python
HYPOTHESIS_GENERATION_PROMPT = """
You are an intent detection specialist. Given minimal user input, generate
ranked hypotheses about what the user likely wants.

## Input Features
{features}

## Available Context
{context}

## Your Task
1. Analyze all available signals (visual, text, history, business)
2. Generate 3-5 plausible intent hypotheses
3. Rank by confidence based on evidence
4. For each hypothesis, explain supporting/contradicting evidence
5. Suggest what specialist/action would handle each intent

## Confidence Calibration Guidelines
- 85%+: Strong evidence from multiple sources (history + explicit signals)
- 60-85%: Good evidence from one source (clear visual OR explicit text)
- 30-60%: Reasonable inference with limited evidence
- <30%: Speculation - should ask before proceeding

## Output Format
Return structured HypothesisSet following the schema.
"""

async def generate_hypotheses(
    features: CombinedFeatures,
    context: AggregatedContext,
) -> HypothesisSet:
    """Generate intent hypotheses using LLM reasoning."""

    llm = get_hypothesis_llm()  # Fast model (Gemini Flash, GPT-4o-mini)

    response = await llm.with_structured_output(HypothesisSet).ainvoke(
        HYPOTHESIS_GENERATION_PROMPT.format(
            features=features.model_dump_json(),
            context=context.model_dump_json(),
        )
    )

    return response
```

#### Hypothesis Templates (Domain-Specific)

Pre-defined hypothesis templates for common AutifyME intents:

```python
INTENT_TEMPLATES = {
    "catalog_product": {
        "triggers": ["image with product", "text mentions 'add'/'catalog'"],
        "specialist": "catalog_specialist",
        "typical_workflow": "extract -> catalog -> price",
    },
    "get_pricing": {
        "triggers": ["mentions price/cost/rate", "existing product reference"],
        "specialist": "catalog_specialist",
        "typical_workflow": "lookup -> compare -> suggest",
    },
    "image_editing": {
        "triggers": ["mentions edit/enhance/background", "image quality issues"],
        "specialist": "creative_specialist",
        "typical_workflow": "analyze -> enhance -> preview",
    },
    "bulk_operation": {
        "triggers": ["mentions 'all'/'bulk'/'batch'", "multiple items visible"],
        "specialist": "catalog_specialist",
        "typical_workflow": "scope -> preview -> execute",
    },
    "information_query": {
        "triggers": ["question words", "no actionable intent"],
        "specialist": None,  # PM handles directly
        "typical_workflow": "lookup -> respond",
    },
    "appraisal": {
        "triggers": ["vintage/antique items", "value/worth mentions"],
        "specialist": "catalog_specialist",
        "typical_workflow": "research -> compare -> estimate",
    },
}
```

---

### 4. Hypothesis Ranker

Refines confidence scores using evidence and business rules.

#### Ranking Factors

```python
class RankingFactors(BaseModel):
    """Factors that influence hypothesis ranking."""

    # Evidence Strength
    visual_evidence_score: float  # How clearly image supports this intent
    text_evidence_score: float  # How clearly text supports this intent
    history_evidence_score: float  # How consistent with user patterns

    # Business Alignment
    business_relevance: float  # How relevant to company's catalog
    specialist_availability: float  # Is required specialist available

    # Practical Factors
    action_complexity: float  # Simpler actions rank higher when uncertain
    clarification_cost: float  # How disruptive would asking be

    # Learned Adjustments (Phase 2)
    historical_accuracy: float  # How accurate this intent type has been
    user_preference_alignment: float  # Does user typically want this


def rank_hypotheses(
    hypotheses: list[IntentHypothesis],
    factors: RankingFactors,
) -> list[IntentHypothesis]:
    """Re-rank hypotheses using evidence and business factors."""

    for h in hypotheses:
        # Compute composite score
        h.confidence = compute_composite_score(h, factors)

    # Sort by confidence descending
    return sorted(hypotheses, key=lambda h: h.confidence, reverse=True)
```

#### Confidence Calibration Rules

```python
CONFIDENCE_RULES = {
    # Boost conditions
    "user_did_this_recently": +0.15,  # User cataloged similar item this week
    "explicit_action_word": +0.20,    # User said "catalog", "add", "price"
    "matches_company_catalog": +0.10, # Product type exists in catalog
    "high_image_quality": +0.05,      # Clear, well-lit image

    # Penalty conditions
    "contradicts_recent_action": -0.15,  # User just did opposite
    "unusual_for_user": -0.10,           # User never does this
    "missing_critical_info": -0.20,      # Can't proceed without asking
    "ambiguous_image": -0.10,            # Multiple interpretations possible
}
```

---

### 5. Response Formatter

Transforms hypotheses into user-facing response with appropriate confidence handling.

#### Response Strategies by Confidence

```python
class ResponseStrategy(Enum):
    """How to respond based on confidence distribution."""

    DIRECT_ACTION = "direct"      # >85% confidence - proceed with explanation
    LEAD_WITH_TOP = "lead"        # 60-85% - present top option, mention alternatives
    PRESENT_OPTIONS = "options"   # 30-60% - equal presentation of top 2-3
    OBSERVE_AND_ASK = "observe"   # <30% - show observations, ask for direction


def determine_strategy(hypotheses: HypothesisSet) -> ResponseStrategy:
    """Determine response strategy based on confidence distribution."""

    top = hypotheses.hypotheses[0]

    if top.confidence > 0.85:
        return ResponseStrategy.DIRECT_ACTION

    if top.confidence > 0.60:
        # Check if there's a clear winner
        if len(hypotheses.hypotheses) > 1:
            gap = top.confidence - hypotheses.hypotheses[1].confidence
            if gap > 0.25:
                return ResponseStrategy.LEAD_WITH_TOP
        return ResponseStrategy.LEAD_WITH_TOP

    if top.confidence > 0.30:
        return ResponseStrategy.PRESENT_OPTIONS

    return ResponseStrategy.OBSERVE_AND_ASK
```

#### Response Templates

```python
RESPONSE_TEMPLATES = {
    ResponseStrategy.DIRECT_ACTION: """
{observations}

{action_statement}

{details}

{confirmation_prompt}
""",

    ResponseStrategy.LEAD_WITH_TOP: """
{observations}

{primary_suggestion}

Alternatively:
{alternatives}

{selection_prompt}
""",

    ResponseStrategy.PRESENT_OPTIONS: """
{observations}

I see a few directions here:
{numbered_options}

{selection_prompt}
""",

    ResponseStrategy.OBSERVE_AND_ASK: """
{observations}

What would you like to do with this?
""",
}
```

#### Example Formatted Responses

**DIRECT_ACTION (>85% confidence)**
```
I see a brass door handle, Art Deco style (~1930s), good condition with natural patina.

Adding to your 'Vintage Hardware' family at Rs 550 (matches your similar handles).

SKU: HANDLE-BRASS-DECO-001
Category: Hardware > Door Hardware > Handles
Price: Rs 550 (based on your catalog average)

Shall I proceed?
```

**LEAD_WITH_TOP (60-85% confidence)**
```
I see a brass door handle, Art Deco style (~1930s), good condition.

Based on your recent listings, I'm guessing you want to catalog this.
- Suggested family: 'Vintage Hardware'
- Suggested price: Rs 500-600 (based on similar items)

Alternatively:
- Get appraisal (I can pull auction records)
- Just analyze (detailed condition report)

Which direction?
```

**PRESENT_OPTIONS (30-60% confidence)**
```
I see a brass door handle, Art Deco style (~1930s).

I see a few directions here:
1. **Catalog for sale** - Add to your hardware collection
2. **Get appraisal** - Research market value
3. **Image enhancement** - Improve photo for listing

Which would you like?
```

**OBSERVE_AND_ASK (<30% confidence)**
```
Interesting piece - brass hardware, appears vintage, Art Deco styling.

What would you like to do with this?
```

---

### 6. Integration with PM

The Hypothesis Engine sits **before** PM, enriching the input.

#### Updated Message Flow

```
User Message
    |
    v
[Hypothesis Engine]
    |-- Feature Extraction (parallel)
    |-- Context Aggregation (parallel)
    |-- Hypothesis Generation
    |-- Response Strategy Selection
    |
    v
[Enriched Input to PM]
    |-- Original message
    |-- HypothesisSet
    |-- ResponseStrategy
    |-- Key observations
    |
    v
[PM Orchestrator]
    |-- Uses hypotheses to inform routing
    |-- Uses observations in response
    |-- Uses strategy to format output
```

#### PM Prompt Enhancement

Add to PM prompt:

```xml
<hypothesis_context>

## Pre-Analyzed Input

The Hypothesis Engine has analyzed this message:

### Key Observations
{observations}

### Intent Hypotheses (ranked by confidence)
{hypotheses_formatted}

### Recommended Response Strategy
{strategy}: {strategy_explanation}

## Using This Context

1. **Observations**: Include these in your response - they show you understood
2. **Top Hypothesis**: If confidence >60%, proceed in that direction
3. **Strategy**: Follow the recommended presentation style
4. **Don't Re-Ask**: The hypothesis engine already considered whether to ask

</hypothesis_context>
```

#### Schema Updates

```python
class EnrichedMessage(BaseModel):
    """Message enriched with hypothesis analysis."""

    # Original
    raw_text: str | None
    media_id: str | None
    sender_id: str

    # Hypothesis Engine Output
    hypotheses: HypothesisSet
    response_strategy: ResponseStrategy
    key_observations: list[str]
    extracted_features: CombinedFeatures

    # Confidence Summary
    top_intent: str
    top_confidence: float
    needs_clarification: bool
    suggested_clarifications: list[str]
```

---

## User Context & Learning

### User Profile Storage

New database table for user context:

```sql
CREATE TABLE user_profiles (
    user_id TEXT PRIMARY KEY,
    company_id UUID NOT NULL REFERENCES companies(id),

    -- Interaction Stats
    first_interaction TIMESTAMPTZ NOT NULL,
    last_interaction TIMESTAMPTZ NOT NULL,
    total_interactions INTEGER DEFAULT 0,

    -- Learned Preferences (JSONB for flexibility)
    preferences JSONB DEFAULT '{}',
    -- {
    --   "response_style": "brief",
    --   "typical_categories": ["hardware", "furniture"],
    --   "price_range": [100, 1000],
    --   "language": "en"
    -- }

    -- Behavioral Patterns (JSONB)
    patterns JSONB DEFAULT '{}',
    -- {
    --   "common_intents": ["catalog", "pricing"],
    --   "approval_rate": 0.85,
    --   "correction_rate": 0.12,
    --   "common_corrections": ["wrong category"]
    -- }

    -- Recent Activity Cache (updated on each interaction)
    recent_activity JSONB DEFAULT '[]',
    -- [
    --   {"action": "cataloged", "category": "hardware", "timestamp": "..."},
    --   {"action": "priced", "sku": "HANDLE-001", "timestamp": "..."}
    -- ]

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast lookup
CREATE INDEX idx_user_profiles_company ON user_profiles(company_id);
```

### Learning Loop

```python
async def update_user_profile(
    user_id: str,
    interaction: InteractionOutcome,
) -> None:
    """Update user profile based on interaction outcome."""

    profile = await load_user_profile(user_id)

    # Update stats
    profile.total_interactions += 1
    profile.last_interaction = datetime.now()

    # Update patterns based on outcome
    if interaction.hypothesis_was_correct:
        # Reinforce pattern
        profile.patterns["common_intents"].append(interaction.intent)
    else:
        # Record correction
        profile.patterns["corrections"].append({
            "predicted": interaction.predicted_intent,
            "actual": interaction.actual_intent,
            "timestamp": datetime.now(),
        })

    # Update recent activity (keep last 20)
    profile.recent_activity.insert(0, {
        "action": interaction.action_taken,
        "category": interaction.category,
        "timestamp": datetime.now(),
    })
    profile.recent_activity = profile.recent_activity[:20]

    await save_user_profile(profile)
```

---

## Performance Considerations

### Latency Budget

| Component | Target | Parallel? |
|-----------|--------|-----------|
| Feature Extraction | 200ms | Yes (visual + text) |
| Context Loading | 100ms | Yes (all sources) |
| Hypothesis Generation | 300ms | No (depends on features) |
| Ranking | 50ms | No (lightweight) |
| **Total** | **<500ms** | |

### Optimization Strategies

1. **Aggressive Caching**
   - User profiles: Cache for 5 minutes
   - Company context: Cache for 15 minutes
   - Feature extraction models: Keep warm

2. **Parallel Execution**
   - Feature extraction runs parallel with context loading
   - Cancel slower path if faster path returns confident result

3. **Early Exit**
   - If text has explicit intent ("catalog this"), skip deep visual analysis
   - If high-confidence hypothesis found, skip lower-priority checks

4. **Lightweight First**
   - Fast classifier before LLM vision
   - Template matching before generative hypothesis

---

## Phase 1 Implementation Plan

### Scope

1. **Feature Extraction** - Visual + Text (LLM-based, optimize later)
2. **Context Aggregation** - Business context only (user profiles Phase 2)
3. **Hypothesis Generation** - LLM with structured output
4. **Response Formatting** - Confidence-based templates
5. **PM Integration** - Enriched message schema

### Out of Scope (Phase 2)

- User profile learning
- Fast classifier for common categories
- Historical accuracy tracking
- Adaptive confidence calibration

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| User clarification rate | <30% | % of messages requiring follow-up questions |
| Hypothesis accuracy (top-1) | >70% | % where top hypothesis = actual intent |
| Latency | <500ms | P95 processing time |
| User satisfaction | Qualitative | "System understood me" feedback |

---

## Open Questions

1. **Cold Start**: How intelligent can we be on first interaction with new user?
   - Proposal: Lean heavily on business context + visual features

2. **Confidence Threshold Tuning**: What's the right threshold for each strategy?
   - Proposal: Start conservative (higher thresholds), tune based on correction rates

3. **Multi-Intent Messages**: What if user wants multiple things?
   - Proposal: Generate hypotheses for each detected intent, present sequentially

4. **Voice Notes**: How do we handle audio input?
   - Proposal: Transcribe first, then treat as text (Phase 2: tone analysis)

5. **Recovery from Wrong Hypothesis**: How graceful is the correction flow?
   - Proposal: Design specific recovery patterns that don't feel like failure

---

## Appendix: Example Scenarios

### Scenario 1: Single Image, No Text

**Input**: [Image of ornate wooden chair]

**Feature Extraction**:
```json
{
  "visual": {
    "primary_object": "wooden chair",
    "materials": ["wood", "possibly mahogany"],
    "style_period": "Victorian",
    "estimated_era": "1870-1900",
    "condition": "good",
    "condition_notes": ["some wear on armrests", "original upholstery faded"]
  },
  "text": null
}
```

**Context**:
```json
{
  "user_recent_activity": ["cataloged antique table", "priced Victorian lamp"],
  "company_catalog": ["Antique Furniture", "Vintage Decor"],
  "user_patterns": {"common_intents": ["catalog", "appraisal"]}
}
```

**Generated Hypotheses**:
```json
[
  {
    "intent_type": "catalog_product",
    "confidence": 0.75,
    "supporting_evidence": ["user cataloged antique table recently", "matches company catalog"],
    "suggested_action": "Catalog Victorian chair with pricing research"
  },
  {
    "intent_type": "get_appraisal",
    "confidence": 0.55,
    "supporting_evidence": ["Victorian piece may have significant value", "user did appraisal before"],
    "suggested_action": "Research auction records for valuation"
  }
]
```

**Response Strategy**: LEAD_WITH_TOP (top confidence 0.75)

**Output**:
```
I see a Victorian-era wooden chair, possibly mahogany, good condition
with original upholstery showing age-appropriate wear.

Based on your recent antique listings, I'm guessing you want to catalog this.
- Suggested family: 'Antique Furniture'
- Estimated value: Rs 8,000-12,000 (based on similar Victorian pieces)

Alternatively:
- Get detailed appraisal (auction records, maker identification)
- Just analyze (condition report, era verification)

Which direction?
```

### Scenario 2: Vague Text, No Image

**Input**: "help me with the prices"

**Feature Extraction**:
```json
{
  "visual": null,
  "text": {
    "action_verbs": ["help"],
    "mentioned_products": [],
    "has_explicit_intent": false,
    "missing_info": ["which products", "what kind of help"]
  }
}
```

**Context**:
```json
{
  "user_recent_activity": ["cataloged 5 jars yesterday", "asked about bulk pricing last week"],
  "pending_workflows": [],
  "conversation_history": ["last discussed: jar pricing update"]
}
```

**Generated Hypotheses**:
```json
[
  {
    "intent_type": "bulk_pricing_update",
    "confidence": 0.65,
    "supporting_evidence": ["discussed jar pricing recently", "plural 'prices' suggests multiple"],
    "suggested_action": "Review and update pricing for recent jar products"
  },
  {
    "intent_type": "pricing_query",
    "confidence": 0.45,
    "supporting_evidence": ["help could mean information need"],
    "suggested_action": "Show current pricing structure"
  }
]
```

**Response Strategy**: LEAD_WITH_TOP

**Output**:
```
I recall we discussed jar pricing recently, and you cataloged 5 jars yesterday.

Are you looking to:
1. **Update prices** for those jars (I can analyze and suggest adjustments)
2. **View current pricing** across your catalog
3. **Something else** with prices

Which one?
```

---

## Next Steps

1. Review design with human architect
2. Finalize Phase 1 scope
3. Create implementation tasks
4. Build feature extraction first (unblocks everything else)
5. Iterate on prompt engineering for hypothesis generation
