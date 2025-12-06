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

    DIRECT_ACTION = "direct"      # >85% - proceed with explanation
    LEAD_WITH_TOP = "lead"        # 60-85% - present top, mention alternatives
    PRESENT_OPTIONS = "options"   # 30-60% - show 2-3 options equally
    OBSERVE_AND_ASK = "observe"   # <30% - show observations, ask direction


def determine_response_strategy(hypotheses: list[IntentHypothesis]) -> ResponseStrategy:
    """Determine strategy based on confidence distribution."""

    if not hypotheses:
        return ResponseStrategy.OBSERVE_AND_ASK

    top = hypotheses[0]

    if top.confidence > 0.85:
        return ResponseStrategy.DIRECT_ACTION

    if top.confidence > 0.60:
        return ResponseStrategy.LEAD_WITH_TOP

    if top.confidence > 0.30:
        return ResponseStrategy.PRESENT_OPTIONS

    return ResponseStrategy.OBSERVE_AND_ASK
```

### Response Templates

**DIRECT_ACTION (>85% confidence)**
```
{observations}

{action_statement}

{details}

Shall I proceed?
```

**LEAD_WITH_TOP (60-85% confidence)**
```
{observations}

{primary_recommendation}

Or:
- {alternative_1}
- {alternative_2}

Which direction?
```

**PRESENT_OPTIONS (30-60% confidence)**
```
{observations}

I see a few directions:
1. {option_1}
2. {option_2}
3. {option_3}

Which would you like?
```

**OBSERVE_AND_ASK (<30% confidence)**
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

## Open Questions for Refinement

1. **Researcher granularity**: Should `visual_researcher` be separate from `creative_specialist` in research mode, or reuse same specialist with different prompt?

2. **Routing sophistication**: Is keyword matching sufficient, or do we need lightweight classifier?

3. **Confidence calibration**: How do we tune thresholds based on actual accuracy?

4. **Cross-domain queries**: What if user query spans multiple domains equally? (e.g., "Update product and post to social")

5. **Cold start**: First message from new user - how do we handle no history?

6. **Researcher tool access**: Should researchers have access to all read tools, or scoped to their domain only?

---

## Next Steps

1. Review and refine through Q&A session
2. Finalize researcher schemas
3. Design PM synthesis prompt
4. Implement Phase 1 researchers
5. Integration testing with real scenarios
