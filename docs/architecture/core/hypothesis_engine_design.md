# Hypothesis Engine: Research-First Intent Detection

**Status**: Design Proposal (Refinement Phase)
**Date**: 2025-12-06
**Authors**: Jarvis + Human Architect

---

## Executive Summary

The Hypothesis Engine transforms minimal user input (single image, vague message) into evidence-backed intent hypotheses. Unlike inference-only approaches, this architecture performs **actual research** before presenting options.

**Core Philosophy**: Intelligence demonstrated through research, not interrogation.

**Key Architectural Decision**: PM handles user context (has conversation history), domain researchers handle domain-specific knowledge, PM synthesizes both into hypotheses.

---

## Problem Statement

### Current Limitation

```
User: [sends single product image]
PM: "What would you like to do with this image?"
```

PM has access to rich context but doesn't leverage it proactively.

### Desired Behavior

```
User: [sends single product image]

[Research Phase - parallel, ~300ms]:
- visual_researcher: "Brass door handle, Art Deco, 1930s, good condition"
- catalog_researcher: "3 similar in 'Vintage Hardware' at Rs 450-650"
- PM (user context): "User cataloged 2 handles this week"

[Synthesis Phase]:
PM combines findings into evidence-backed hypotheses

[Response]:
"Brass door handle, Art Deco style (~1930s), good condition with natural patina.

Your catalog has 3 similar handles at Rs 450-650. You've added 2 handles this week.

Recommendation: Add at Rs 550 (matches your pattern)

Or:
- Get detailed appraisal
- Different approach

Which direction?"
```

---

## Architecture Overview

```
User: [minimal input]
         |
         v
+--------+--------+
|       PM        |  <-- Has full conversation history
+--------+--------+
         |
   [1] PM analyzes user context (no delegation needed)
         |
   [2] PM determines relevant domains (lightweight routing)
         |
         +---> visual_researcher (if image present)
         |           |
         +---> catalog_researcher (if product-related)
         |           |
         +---> marketing_researcher (if campaign-related)
         |           |
         +---> [other domain researchers as relevant]
         |
         v (PARALLEL - DeepAgents supports this)
+--------+---------+
| Domain Findings  |
| (Structured)     |
+--------+---------+
         |
   [3] PM synthesizes: User Context + Domain Findings --> Hypotheses
         |
         v
+--------+---------+
| Evidence-Backed  |
| Options          |
+------------------+
         |
         v
   User selects option
         |
         v
   [4] PM delegates to EXECUTION specialist
         |
         +---> creative_specialist (image work)
         +---> catalog_specialist (product work)
         +---> [other execution specialists]
```

---

## Core Design Principles

### 1. PM Handles User Context

PM has what no specialist has:
- **Full conversation history** across sessions
- **Cross-domain visibility** of all specialists
- **Orchestration intelligence** for routing

**Therefore**: PM analyzes user context directly. No delegation needed for user research.

### 2. Domain Research Delegated to Specialists

Domain-specific knowledge requires domain expertise:
- Catalog pricing patterns need catalog knowledge
- Marketing campaign context needs marketing knowledge
- Visual analysis needs creative expertise

**Therefore**: Domain researchers handle domain-specific research in parallel.

### 3. Not All Domains Every Time

With 10-15 domains at scale, querying all researchers for every message is wasteful.

**Therefore**: PM uses lightweight routing to determine relevant domains.

### 4. Research vs. Execution Separation

| Type | Purpose | Speed | Mutations |
|------|---------|-------|-----------|
| **Researchers** | Gather evidence, return findings | Fast (<300ms) | None (read-only) |
| **Executors** | Perform actions, create/update | Careful | Yes (with HITL) |

---

## Specialist Design

### Research Specialists (NEW)

Lightweight, fast, read-only. Return structured findings, not hypotheses.

| Researcher | Domain | Read Access | Purpose |
|------------|--------|-------------|---------|
| `visual_researcher` | Images | view_image | Object, material, style, condition analysis |
| `catalog_researcher` | Products | products, families, pricing, assets | Similar items, pricing patterns |
| `marketing_researcher` | Campaigns | campaigns, posts, templates | Active campaigns, brand alignment |
| `finance_researcher` | Billing | invoices, expenses | Outstanding items, patterns |
| `hr_researcher` | People | employees, contracts | Team context, availability |
| `inventory_researcher` | Stock | inventory, batches, suppliers | Stock levels, reorder needs |
| `customer_researcher` | CRM | customers, leads, tickets | Customer context, history |

### Execution Specialists (EXISTING + FUTURE)

Domain experts that create, update, mutate. Slower, more careful, HITL-gated.

| Executor | Domain | Write Access | Purpose |
|----------|--------|--------------|---------|
| `creative_specialist` | Assets | assets, image_studio | Create/edit images |
| `catalog_specialist` | Products | products, families, pricing | Manage catalog |
| `marketing_specialist` | Campaigns | campaigns, posts | Run campaigns |
| `finance_specialist` | Billing | invoices, expenses | Handle finances |
| `hr_specialist` | People | employees, contracts | Manage HR |
| `inventory_specialist` | Stock | inventory, batches | Manage stock |

### Researcher Prompt Pattern

```xml
<role>
You are a {domain} research specialist. Your ONLY job is to gather relevant information.
</role>

<responsibilities>
## You Do
- Query relevant tables for the given context
- Identify patterns and anomalies in the data
- Return factual observations with confidence scores

## You Do NOT
- Make decisions or recommendations
- Generate hypotheses about user intent
- Suggest actions to take
- Mutate any data (read-only access)
</responsibilities>

<output>
Return {Domain}Findings schema with:
- relevant_items: What you found
- patterns: Notable patterns observed
- anomalies: Anything unusual
- confidence: How complete/reliable is this picture (0.0-1.0)
</output>
```

---

## Findings Schemas

### Visual Findings

```python
class VisualFindings(BaseModel):
    """Structured output from visual_researcher."""

    # Object identification
    primary_object: str  # "door handle"
    secondary_objects: list[str]  # ["mounting plate", "screws"]
    object_count: int

    # Material analysis
    materials: list[str]  # ["brass", "metal"]
    material_confidence: float

    # Style/Era detection
    style_period: str | None  # "Art Deco"
    estimated_era: str | None  # "1920s-1940s"

    # Condition assessment
    condition: str  # "good", "fair", "excellent"
    condition_notes: list[str]  # ["patina present", "minor wear"]

    # Technical details
    estimated_dimensions: str | None  # "~15cm length"
    color_palette: list[str]  # ["gold", "brown"]

    # Notable features
    notable_features: list[str]  # ["hand-forged", "original finish"]

    # Confidence
    confidence: float  # Overall confidence in analysis
```

### Catalog Findings

```python
class SimilarItem(BaseModel):
    """Similar item found in catalog."""
    sku: str
    name: str
    family: str
    price: float
    similarity_score: float


class PricingPattern(BaseModel):
    """Pricing patterns observed."""
    min_price: float
    max_price: float
    avg_price: float
    price_trend: str  # "stable", "increasing", "decreasing"


class CatalogFindings(BaseModel):
    """Structured output from catalog_researcher."""

    # Similar items
    similar_items: list[SimilarItem]

    # Pricing analysis
    pricing_patterns: PricingPattern

    # Categorization
    relevant_families: list[str]
    suggested_category: str | None

    # Gaps/opportunities
    gaps_identified: list[str]  # "No blue variant exists"

    # Confidence
    confidence: float
```

### Marketing Findings

```python
class CampaignSummary(BaseModel):
    """Active campaign summary."""
    id: str
    name: str
    status: str
    channels: list[str]
    relevance_score: float


class MarketingFindings(BaseModel):
    """Structured output from marketing_researcher."""

    # Active campaigns
    active_campaigns: list[CampaignSummary]

    # Templates
    relevant_templates: list[str]

    # Brand context
    brand_alignment_notes: list[str]

    # Channel recommendations
    suggested_channels: list[str]

    # Confidence
    confidence: float
```

### Generic Pattern for Other Domains

```python
class DomainFindings(BaseModel):
    """Generic findings pattern for any domain."""

    # What was found
    relevant_items: list[dict]

    # Patterns observed
    patterns: list[str]

    # Anomalies/concerns
    anomalies: list[str]

    # Domain-specific context
    context_notes: list[str]

    # Confidence
    confidence: float
```

---

## PM Routing Logic

PM determines which researchers to spawn based on input signals and user context.

### Routing Heuristics

```python
def determine_relevant_researchers(
    input: UserInput,
    user_context: UserContext,
) -> list[str]:
    """PM determines which domain researchers are relevant."""

    researchers = []

    # Visual input --> always need visual research
    if input.has_image:
        researchers.append("visual_researcher")

    # Product signals
    if any([
        input.mentions_terms(["catalog", "product", "SKU", "price", "add"]),
        input.has_image,  # Images often product-related
        user_context.recent_domain == "catalog",
    ]):
        researchers.append("catalog_researcher")

    # Marketing signals
    if any([
        input.mentions_terms(["campaign", "post", "social", "marketing"]),
        user_context.recent_domain == "marketing",
    ]):
        researchers.append("marketing_researcher")

    # Finance signals
    if any([
        input.mentions_terms(["invoice", "payment", "bill", "expense"]),
        input.has_invoice_image,
    ]):
        researchers.append("finance_researcher")

    # HR signals
    if any([
        input.mentions_terms(["employee", "hire", "payroll", "leave"]),
    ]):
        researchers.append("hr_researcher")

    # Inventory signals
    if any([
        input.mentions_terms(["stock", "inventory", "reorder", "warehouse"]),
    ]):
        researchers.append("inventory_researcher")

    # Customer/CRM signals
    if any([
        input.mentions_terms(["customer", "lead", "ticket", "support"]),
    ]):
        researchers.append("customer_researcher")

    # Fallback: If truly ambiguous, use user's most common domain
    if not researchers:
        primary = user_context.primary_domain
        if primary:
            researchers.append(f"{primary}_researcher")

    return researchers
```

### Routing Decision Matrix

| Input Signal | Researchers Spawned |
|--------------|---------------------|
| Product image | visual, catalog |
| Product image + price mention | visual, catalog |
| "Help with prices" | catalog (+ finance if billing context) |
| Invoice image | visual, finance |
| "Update campaign" | marketing |
| "Stock running low" | inventory, procurement |
| "New employee" | hr |
| Vague "help me" | Based on user's primary domain |

**Key**: This routing is LIGHTWEIGHT - keyword matching + user context. Not a full LLM call.

---

## PM Synthesis: Findings to Hypotheses

### Hypothesis Schema

```python
class IntentHypothesis(BaseModel):
    """Single intent hypothesis with evidence."""

    # Core
    intent_type: str  # "catalog_product", "get_appraisal"
    intent_description: str  # Human-readable description

    # Confidence
    confidence: float  # 0.0 to 1.0
    confidence_reasoning: str

    # Evidence
    supporting_evidence: list[str]
    contradicting_evidence: list[str]

    # Action
    suggested_specialist: str | None  # "catalog_specialist"
    suggested_action: str

    # Clarification (if needed)
    clarification_needed: list[str]
    clarification_priority: str  # "optional", "recommended", "required"


class HypothesisSet(BaseModel):
    """Ranked set of hypotheses from PM synthesis."""

    hypotheses: list[IntentHypothesis]  # Sorted by confidence

    # Key observations (what system noticed)
    key_observations: list[str]

    # Ambiguity assessment
    ambiguity_level: str  # "low", "medium", "high"
    dominant_hypothesis: bool  # True if top >> others

    # Response strategy
    response_strategy: ResponseStrategy
```

### Synthesis Process

```python
async def synthesize_hypotheses(
    user_input: UserInput,
    user_context: UserContext,  # PM's own analysis from history
    domain_findings: dict[str, Findings],  # From researchers
) -> HypothesisSet:
    """PM synthesizes all evidence into ranked hypotheses."""

    # Build unified evidence picture
    evidence = UnifiedEvidence(
        user_signals=user_context.extract_signals(),
        conversation_context=user_context.recent_topics,
        visual=domain_findings.get("visual"),
        catalog=domain_findings.get("catalog"),
        marketing=domain_findings.get("marketing"),
        finance=domain_findings.get("finance"),
        # ... other domains
    )

    # Generate hypotheses (PM reasoning with evidence)
    hypotheses = await pm_generate_hypotheses(evidence)

    # Rank by evidence strength
    ranked = rank_by_evidence(hypotheses)

    # Determine response strategy
    strategy = determine_response_strategy(ranked)

    return HypothesisSet(
        hypotheses=ranked,
        key_observations=extract_observations(evidence),
        ambiguity_level=assess_ambiguity(ranked),
        dominant_hypothesis=ranked[0].confidence > 0.7,
        response_strategy=strategy,
    )
```

---

## Response Strategy

### Confidence-Based Strategies

```python
class ResponseStrategy(Enum):
    """How to respond based on confidence distribution."""

    DIRECT_ACTION = "direct"      # >90% - proceed with explanation
    LEAD_WITH_TOP = "lead"        # 70-90% - present top, mention alternatives
    PRESENT_OPTIONS = "options"   # 40-70% - show 2-3 options equally
    OBSERVE_AND_ASK = "observe"   # <40% - show observations, ask direction


def determine_response_strategy(hypotheses: list[IntentHypothesis]) -> ResponseStrategy:
    """Determine strategy based on confidence distribution."""

    if not hypotheses:
        return ResponseStrategy.OBSERVE_AND_ASK

    top = hypotheses[0]

    # Conservative thresholds - avoid trust damage from wrong assumptions
    if top.confidence > 0.90:
        return ResponseStrategy.DIRECT_ACTION

    if top.confidence > 0.70:
        return ResponseStrategy.LEAD_WITH_TOP

    if top.confidence > 0.40:
        return ResponseStrategy.PRESENT_OPTIONS

    return ResponseStrategy.OBSERVE_AND_ASK
```

### Response Templates

**DIRECT_ACTION (>90% confidence)**
```
{observations}

{action_statement}

{details}

Shall I proceed?
```

**LEAD_WITH_TOP (70-90% confidence)**
```
{observations}

{primary_recommendation}

Or:
- {alternative_1}
- {alternative_2}

Which direction?
```

**PRESENT_OPTIONS (40-70% confidence)**
```
{observations}

I see a few directions:
1. {option_1}
2. {option_2}
3. {option_3}

Which would you like?
```

**OBSERVE_AND_ASK (<40% confidence)**
```
{observations}

What would you like to do with this?
```

---

## Example Flow: Complete Walkthrough

### Input
User sends image of brass handle, no text.

### Step 1: PM Analyzes User Context
```
PM (from conversation history):
- User cataloged 2 handles this week
- User's primary domain: catalog
- User's typical intent: catalog at competitive prices
- User prefers brief responses
- Last discussed: vintage hardware pricing
```

### Step 2: PM Routes to Researchers
```
PM routing decision:
- Has image --> visual_researcher
- Likely product (image + user's domain) --> catalog_researcher
- No marketing signals --> skip marketing_researcher
- No finance signals --> skip finance_researcher

Spawning: [visual_researcher, catalog_researcher] in parallel
```

### Step 3: Researchers Execute (Parallel, ~300ms)
```
visual_researcher returns VisualFindings:
{
  "primary_object": "door handle",
  "materials": ["brass"],
  "style_period": "Art Deco",
  "estimated_era": "1920s-1940s",
  "condition": "good",
  "condition_notes": ["natural patina", "original finish"],
  "notable_features": ["hand-forged details"],
  "confidence": 0.85
}

catalog_researcher returns CatalogFindings:
{
  "similar_items": [
    {"sku": "HANDLE-BRASS-001", "name": "Vintage Brass Handle", "price": 450, "family": "Vintage Hardware"},
    {"sku": "HANDLE-BRASS-002", "name": "Art Deco Handle", "price": 600, "family": "Vintage Hardware"},
    {"sku": "HANDLE-BRASS-003", "name": "Antique Door Handle", "price": 550, "family": "Vintage Hardware"}
  ],
  "pricing_patterns": {"min": 450, "max": 650, "avg": 533, "trend": "stable"},
  "relevant_families": ["Vintage Hardware"],
  "gaps_identified": ["No Art Deco specific variant"],
  "confidence": 0.90
}
```

### Step 4: PM Synthesizes Hypotheses
```
Evidence combined:
- User: Cataloged 2 handles this week, prefers competitive pricing
- Visual: Brass Art Deco handle, 1930s, good condition
- Catalog: 3 similar at Rs 450-650, avg Rs 533, "Vintage Hardware" family

Generated hypotheses:
1. catalog_product (confidence: 0.82)
   - Supporting: User pattern (2 handles this week), similar items exist, price range clear
   - Contradicting: None significant
   - Suggested action: Add to "Vintage Hardware" at Rs 550

2. get_appraisal (confidence: 0.45)
   - Supporting: Art Deco pieces can have collector value
   - Contradicting: User typically catalogs, doesn't appraise

3. image_enhancement (confidence: 0.25)
   - Supporting: Could improve photo for listing
   - Contradicting: Image quality seems adequate

Response strategy: LEAD_WITH_TOP (0.82 confidence)
```

### Step 5: PM Presents Response
```
"Brass door handle, Art Deco style (~1930s), good condition with natural patina.

Your catalog has 3 similar handles in 'Vintage Hardware' at Rs 450-650.
You've added 2 handles this week.

Recommendation: Add at Rs 550 (matches your pricing pattern)

Or:
- Get detailed appraisal (Art Deco pieces can have collector value)
- Different approach

Which direction?"
```

### Step 6: User Selects, PM Delegates to Executor
```
User: "Yes, add it"

PM delegates to catalog_specialist:
"Create product in 'Vintage Hardware' family:
- Type: Door handle
- Material: Brass
- Style: Art Deco (~1930s)
- Condition: Good, natural patina
- Price: Rs 550
- Image: [attached]"
```

---

## Scaling: 10-15 Domains

### Domain Growth Plan

| Phase | Domains | Researchers | Executors |
|-------|---------|-------------|-----------|
| Current | Products, Assets | 2 | 2 |
| Phase 2 | + Marketing, Website | 4 | 4 |
| Phase 3 | + Finance, CRM | 6 | 6 |
| Phase 4 | + HR, Inventory, Procurement | 9 | 9 |
| Phase 5 | + Production, QC, Forecasting | 12 | 12 |

### Why This Scales

1. **PM routing limits researchers per message** - Only 2-3 researchers run, not all 12
2. **Parallel execution** - Researchers run simultaneously via DeepAgents
3. **Lightweight researchers** - Read-only, fast, focused
4. **Domain coherence** - Each researcher is expert in one domain
5. **Structured outputs** - Consistent schemas enable reliable synthesis

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Research latency | <300ms | Parallel researcher execution |
| Synthesis latency | <200ms | PM reasoning with structured evidence |
| Total latency | <500ms | Before user sees response |
| Hypothesis accuracy (top-1) | >70% | Correct intent in top hypothesis |
| Clarification rate | <30% | Messages needing follow-up questions |

---

## Implementation Priority

### Phase 1 (Immediate)
1. `visual_researcher` - Image analysis specialist
2. `catalog_researcher` - Product/pricing lookup specialist
3. PM routing logic - Keyword + context based
4. PM synthesis prompt - Evidence to hypotheses
5. Response formatting - Confidence-based templates

### Phase 2 (With Marketing Domain)
6. `marketing_researcher`
7. `marketing_specialist` (executor)

### Phase 3+ (As Domains Added)
- Add researcher + executor pair for each new domain
- Extend PM routing heuristics
- Update synthesis prompt with new evidence types

---

## Design Decisions (Finalized)

### Decision 1: Researcher Granularity

**Question**: Should `visual_researcher` be separate from `creative_specialist` in research mode, or reuse same specialist with different prompt?

**Decision**: **Separate Specialists**

**Rationale**:
- **Different optimization targets**: Research optimizes for speed (small, fast model), execution optimizes for quality (larger model)
- **Cleaner tool scoping**: Researchers get read-only tools only, no mutation risk
- **Smaller prompts**: Each specialist focused, not overloaded with dual responsibilities
- **Domain knowledge sync**: Extract shared domain knowledge to common reference doc

**Implementation**:
```
visual_researcher
  - Model: Fast (Gemini Flash, GPT-4o-mini)
  - Tools: view_image (read-only)
  - Prompt: ~200 lines (analysis focused)

creative_specialist
  - Model: Quality (Gemini Pro, GPT-4)
  - Tools: view_image, image_studio, write_data
  - Prompt: ~800 lines (execution focused)

Shared: domain_knowledge/visual_analysis.md (both prompts reference)
```

---

### Decision 2: Routing Sophistication

**Question**: Is keyword matching sufficient, or do we need lightweight classifier?

**Decision**: **Hybrid - Keywords + User Context + LLM Fallback**

**Rationale**:
- Keywords handle ~80% of cases instantly (<10ms)
- User context (primary domain) handles ambiguous cases
- LLM fallback only for truly unclear cases (<5%)
- No training data overhead of classifier

**Implementation**:
```python
def route_to_researchers(input: UserInput, user_context: UserContext) -> list[str]:
    researchers = []

    # Rule 1: Explicit signals (keywords) - fast path
    if input.has_image:
        researchers.append("visual_researcher")

    keyword_matches = match_domain_keywords(input.text)
    researchers.extend(keyword_matches)

    # Rule 2: If keywords found, use them
    if researchers:
        return deduplicate(researchers)

    # Rule 3: User context fallback
    if user_context.primary_domain:
        return [f"{user_context.primary_domain}_researcher"]

    # Rule 4: LLM fallback (rare, <5% of cases)
    return await llm_determine_domains(input)
```

**Keyword Matching Limitations** (handled by fallback):
- Synonyms: "Stock running low" vs "We're out of inventory"
- Implicit intent: "The blue ones" (context-dependent)
- Negation: "Don't update the campaign"

---

### Decision 3: Confidence Calibration

**Question**: How do we tune thresholds based on actual accuracy?

**Decision**: **Conservative Start + Outcome Tracking + Periodic Calibration**

**Phase 1 - Launch (Conservative)**:
```python
CONFIDENCE_THRESHOLDS = {
    "direct_action": 0.90,    # Was 0.85 - more conservative
    "lead_with_top": 0.70,    # Was 0.60 - more conservative
    "present_options": 0.40,  # Was 0.30 - more conservative
}
```

**Phase 2 - Measure Accuracy**:

Track in `workflow_outcomes` table:
```python
class HypothesisOutcome(BaseModel):
    """Track hypothesis accuracy for calibration."""

    tracking_id: str
    top_hypothesis_intent: str
    top_hypothesis_confidence: float
    actual_intent: str  # What user actually wanted
    was_correct: bool
    user_corrected: bool
    correction_friction: str  # "smooth", "frustrating"
```

**Phase 3 - Build Calibration Curve** (after 500+ interactions):
```
Confidence Band | Predicted | Actual | Action
90-100%         | 95%       | 88%    | Lower threshold or improve model
80-90%          | 85%       | 82%    | Well calibrated
70-80%          | 75%       | 71%    | Well calibrated
60-70%          | 65%       | 58%    | Slightly overconfident
```

**Phase 4 - Dynamic Adjustment**:
```python
def get_strategy_thresholds() -> dict:
    calibration = load_calibration_metrics()

    if calibration.sample_size < 500:
        return CONSERVATIVE_DEFAULTS

    return {
        "direct_action": calibration.threshold_for_accuracy(0.85),
        "lead_with_top": calibration.threshold_for_accuracy(0.70),
        "present_options": calibration.threshold_for_accuracy(0.50),
    }
```

---

### Decision 4: Cross-Domain Queries

**Question**: What if user query spans multiple domains equally? (e.g., "Update product and post to social")

**Decision**: **Parallel Research, Sequential Execution**

**Rationale**:
- Research is read-only, no dependency issues - parallelize
- Execution has dependencies - PM orchestrates order
- User sees holistic response, not fragmented tasks

**Implementation**:
```python
async def handle_multi_domain(
    input: UserInput,
    domains: list[str],  # ["catalog", "marketing"]
) -> HypothesisSet:

    # Research in parallel (no dependencies)
    findings = await asyncio.gather(*[
        get_researcher(domain).research(input)
        for domain in domains
    ])

    # Synthesize with dependency awareness
    hypotheses = await pm_synthesize(
        input=input,
        findings=findings,
        detect_dependencies=True,
    )

    return hypotheses
```

**Response Pattern for Multi-Domain**:
```
"I see you want to update the product AND post to social.

Here's what I found:
- Product: 'Blue Widget' - current price Rs 450
- Marketing: No active campaigns for this product

Plan:
1. First: Update product details (what changes?)
2. Then: Create social post with updated info

What would you like to change in the product?"
```

**Dependency Detection**:
- Marketing needs product data - catalog first
- Invoice needs customer - CRM first
- Campaign needs assets - creative first

---

### Decision 5: Cold Start Handling

**Question**: First message from new user - how do we handle no history?

**Decision**: **Company Patterns + Visual Heavy + Explicit Uncertainty**

**Strategy Layers**:

**Layer 1 - Lean on Visual + Company Context**:
```python
if user_context.is_new_user:
    # Weight visual findings heavily
    visual_weight = 0.5  # (normally 0.3)

    # Use company's common patterns
    company_patterns = load_company_patterns(company_id)

    # Lower confidence (acknowledge uncertainty)
    confidence_penalty = 0.15
```

**Layer 2 - Company-Level Patterns**:
```python
class CompanyPatterns(BaseModel):
    """What do users of THIS company typically want?"""

    common_intents: list[str]  # ["catalog", "pricing"]
    common_categories: list[str]  # ["PET bottles", "jars"]
    typical_price_range: tuple[float, float]
    common_workflows: list[str]
```

**Layer 3 - Explicit Uncertainty in Response**:
```
"I see a brass door handle, Art Deco style (~1930s).

Since this is our first interaction, I'm not sure what you'd like to do.
Common options:
1. Catalog for sale
2. Get appraisal
3. Something else

What would you like?"
```

**Layer 4 - Fast Learning**:
```python
async def update_user_profile(user_id: str, outcome: Outcome):
    profile = await load_or_create_profile(user_id)

    # New users: weight recent interactions heavily
    if profile.interaction_count < 10:
        recency_weight = 0.8  # Recent interactions dominate
    else:
        recency_weight = 0.3  # Blend with history

    profile.update_patterns(outcome, recency_weight)
```

**Cold Start Confidence Formula**:
```
confidence =
    (visual_confidence * 0.5) +
    (company_pattern_match * 0.3) +
    (domain_keyword_match * 0.2) -
    (new_user_penalty: 0.15)
```

**Default Strategy**: `PRESENT_OPTIONS` for first 3-5 interactions until patterns emerge.

---

### Decision 6: Researcher Tool Access

**Question**: Should researchers have access to all read tools, or scoped to their domain only?

**Decision**: **Domain-Scoped Primary + Explicit Cross-Domain Protocol**

**Rationale**:
- Researchers should be domain experts, not generalists
- Cross-domain insights are PM's job (sees all findings)
- Scoped tools = faster, cheaper, less confusion
- Prevents scope creep and token waste

**Implementation - Scoped Tools**:
```python
# catalog_researcher tools (scoped)
catalog_researcher_tools = [
    create_scoped_read_data(["products", "product_families", "pricing", "assets"]),
    create_scoped_aggregate_data(["products", "product_families", "pricing"]),
    create_scoped_inspect_schema(["products", "product_families", "pricing", "assets"]),
]

# marketing_researcher tools (scoped)
marketing_researcher_tools = [
    create_scoped_read_data(["campaigns", "posts", "templates"]),
    create_scoped_aggregate_data(["campaigns", "posts"]),
    create_scoped_inspect_schema(["campaigns", "posts", "templates"]),
]
```

**Tool Scoping Implementation**:
```python
def create_scoped_read_data(allowed_tables: list[str]) -> StructuredTool:
    """Create read_data tool scoped to specific tables."""

    async def scoped_read(query: str, table: str) -> dict:
        if table not in allowed_tables:
            return {
                "success": False,
                "error": f"Table '{table}' outside scope. Allowed: {allowed_tables}"
            }
        return await read_data(query, table)

    return StructuredTool.from_function(scoped_read, ...)
```

**Cross-Domain Protocol** (rare cases):

If researcher needs cross-domain data, return a request (not fetch directly):
```python
class CatalogFindings(BaseModel):
    # ... normal findings ...

    cross_domain_requests: list[CrossDomainRequest] = []
    # e.g., [{"domain": "marketing", "query": "active promotions for SKU-123"}]
```

PM evaluates cross-domain requests and spawns additional researchers if warranted.

---

## Decision Summary

| Question | Decision | Key Rationale |
|----------|----------|---------------|
| Researcher granularity | Separate specialists | Different optimization targets, cleaner scoping |
| Routing sophistication | Hybrid (keywords + context + LLM fallback) | 95%+ coverage, no training overhead |
| Confidence calibration | Conservative start + outcome tracking | Avoid trust damage, data-driven tuning |
| Cross-domain queries | Parallel research, sequential execution | Fast research, correct dependencies |
| Cold start | Company patterns + visual heavy + explicit uncertainty | Graceful degradation, fast learning |
| Tool access | Domain-scoped with cross-domain protocol | Focused, fast, prevents scope creep |

---

## Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1-2)
1. Create `visual_researcher` specialist (separate from creative_specialist)
2. Create `catalog_researcher` specialist
3. Implement PM routing logic (keyword + context + fallback)
4. Implement PM synthesis prompt
5. Add confidence-based response formatting
6. Create scoped tool factory

### Phase 2: Calibration & Learning (Week 3-4)
7. Add `HypothesisOutcome` tracking to workflow_outcomes
8. Implement user profile creation/update
9. Add company patterns schema and loading
10. Implement cold start handling

### Phase 3: Testing & Tuning (Week 5-6)
11. Integration testing with real scenarios
12. Calibration curve analysis (if enough data)
13. Threshold tuning based on accuracy
14. Cross-domain scenario testing

### Phase 4: Domain Expansion (Ongoing)
- Add researcher + executor pair for each new domain
- Extend PM routing heuristics
- Update synthesis prompt with new evidence types
- Maintain domain knowledge docs

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Research latency | <300ms | P95 parallel researcher execution |
| Total latency | <500ms | P95 before user sees response |
| Hypothesis accuracy (top-1) | >70% | Correct intent in top hypothesis |
| Clarification rate | <30% | Messages needing follow-up questions |
| User correction rate | <15% | Users correcting system's assumption |
| Cold start recovery | <5 interactions | Interactions until accuracy matches warm users |
