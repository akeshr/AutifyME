# Domain Reasoning Framework

**Created:** December 15, 2025
**Consolidated:** December 17, 2025
**Status:** Phase 1 Ready
**Supersedes:** DOMAIN_REASONING_PROTOCOLS.md, DOMAIN_REASONING_IMPLEMENTATION_PLAN.md

---

## Vision: Autonomous Agentic Organization

AutifyME is an **autonomous agentic organization** - a system of intelligent agents that dynamically plan, adapt, and execute across business domains.

**The 2-Level Architecture:**

```
                         USER
                           |
                           v
+----------------------------------------------------------+
|              PROJECT MANAGER (Orchestrator)               |
|  - Understands all domains                                |
|  - Routes to specialists dynamically                      |
|  - Composes workflows on-the-fly                          |
+----------------------------------------------------------+
                           |
         +-----------------+-----------------+
         v                 v                 v
+----------------+ +----------------+ +----------------+
|   CATALOGING   | |   MARKETING    | |   OPERATIONS   |
|   Specialist   | |   Specialist   | |   Specialist   |
+----------------+ +----------------+ +----------------+
         |                 |                 |
         v                 v                 v
      [Tools]           [Tools]           [Tools]
```

**The Challenge:** LLMs are general-purpose. Each domain requires SPECIFIC expertise - your business rules, your data patterns, your decision criteria. Without domain grounding, agents apply generic knowledge and fail.

**The Solution:** Domain Reasoning Protocols - executable examples that encode domain expertise as step-by-step reasoning processes. Protocols bridge the gap between general intelligence and specific domain mastery.

**Why This Matters:**

| Without Protocols | With Protocols |
|-------------------|----------------|
| Agent uses generic retail knowledge | Agent queries YOUR catalog data |
| Family assignment by material | Family assignment by customer segment |
| Pricing from market assumptions | Pricing from YOUR established patterns |
| Inconsistent decisions | Repeatable, grounded reasoning |

---

## Table of Contents

1. [Core Mechanism](#1-core-mechanism)
2. [Architecture](#2-architecture)
3. [Generic Patterns](#3-generic-patterns)
4. [Domain Instantiation: Catalog](#4-domain-instantiation-catalog)
5. [Protocol Composition](#5-protocol-composition)
6. [Implementation](#6-implementation)
7. [Decision Log](#7-decision-log)
8. [Success Metrics](#8-success-metrics)
9. [Risk Register](#9-risk-register)

**Separate Documents:**
- [PM_INTELLIGENCE_ROADMAP.md](./PM_INTELLIGENCE_ROADMAP.md) - Future PM capabilities (aspirational)

---

## 1. Core Mechanism

### 1.1 The Protocol Solution

**Protocols are executable reasoning examples.** They show HOW to think through domain decisions, not just WHAT to conclude.

| Approach | What Agent Gets | Result |
|----------|-----------------|--------|
| Rules | Abstract principles | Applies inconsistently |
| Output Examples | Final answers | Copies format, hallucinates data |
| **Protocols** | Step-by-step process with tool calls | Executes each step, grounded in real data |

### 1.2 Tool Grounding: Why Protocols Work

```
Protocol Step: "QUERY customer_segments for this family"
                    |
                    v
            Agent calls read_data()
                    |
                    v
            Tool returns REAL records
                    |
                    v
            Agent reasons about ACTUAL data
```

**The agent can't fake query results.** When a protocol says "Execute read_data(...)", the tool returns actual database records. This grounds reasoning in reality.

### 1.3 The Grounding Boundary

| Step Type | Grounded? | Example |
|-----------|-----------|---------|
| QUERY | YES | read_data returns real records |
| AGGREGATE | YES | Statistics are factual |
| ANALYZE | NO | "This looks decorative" is inference |
| COMPARE | PARTIAL | Data grounded, interpretation not |

**Mitigation for ungrounded steps:** Structured criteria, comparison to grounded data, HITL checkpoint.

### 1.4 Protocol Applicability: All Agent Types

Protocols are NOT just for specialists. Every agent in the hierarchy needs domain grounding.

| Agent Level | Protocol Types | Purpose |
|-------------|----------------|---------|
| **PM** | Routing, Multi-domain | Route correctly, coordinate across domains |
| **Analysts** | Exploration, Orientation | Query comprehensively, discover patterns |
| **Specialists** | Decision, Domain-specific | Make grounded decisions using business rules |

**The distinction:**

| Aspect | Analyst | Specialist |
|--------|---------|------------|
| Function | Explore and suggest | Decide and commit |
| Output | Options, recommendations | Decisions, writes |
| Protocol usage | IMPLICIT (mental model) | EXPLICIT (documented execution) |
| HITL | Never (read-only) | On writes |

---

## 2. Architecture

### 2.1 Protocol Delivery

> STATUS: REPL VERIFIED

```
1. Agent calls load_protocol(["family_fit", "pricing"])
2. Tool returns protocol CONTENT
3. Middleware injects into system prompt
4. Agent sees protocol as INSTRUCTIONS
```

**Design Decisions:**

| Decision | Rationale |
|----------|-----------|
| Message-history based | ToolMessages persist; config doesn't |
| Agent autonomy | Agent matches situation to protocol index |
| Batch loading | Single call prevents parallel issues |
| Deduplication | Middleware injects each protocol once |

**Protocol Selection:**

| Aspect | Approach |
|--------|----------|
| Selection | Pure agent autonomy via protocol index |
| Observability | Trace evaluation via LangSmith |
| Enforcement | None - measure first, strengthen prompt if needed |

### 2.2 Protocol Loading Tool

```python
def create_load_protocol_tool(agent_type: str):
    """Factory for agent-specific load_protocol tool."""

    @tool
    def load_protocol(names: list[str]) -> str:
        """Load reasoning protocols for structured domain decisions."""
        results = []
        for name in names:
            content = _load_protocol_content(agent_type, name)
            results.append(f"## Protocol: {name}\n{content}")
        return "\n\n".join(results)

    return load_protocol
```

### 2.3 Protocol Injection Middleware

```python
class ProtocolInjectionMiddleware(AgentMiddleware):
    """Injects loaded protocols into system prompt."""

    def wrap_model_call(self, request, handler):
        # Scan ToolMessages for load_protocol results
        # Deduplicate by protocol name
        # Inject into system prompt via request.override()
        return handler(request)
```

### 2.4 Protocol Library Structure

```
protocols/
├── pm/                      # PM orchestration
├── catalog_specialist/      # Catalog domain (FIRST DOMAIN)
├── catalog_analyst/         # Catalog exploration
├── marketing_specialist/    # Marketing domain (FUTURE)
├── operations_specialist/   # Operations domain (FUTURE)
└── shared/                  # Cross-domain patterns
    ├── fit_assessment.protocol
    ├── value_discovery.protocol
    ├── duplicate_prevention.protocol
    └── tool_mastery/
```

**Resolution:** Agent-specific first, then shared.

### 2.5 Token Budget

| Scenario | Tokens |
|----------|--------|
| Base prompt | ~1,500 |
| Per protocol | ~400-600 |
| Simple task | ~1,500 (no protocols) |
| Complex task | ~2,500-3,000 (2-3 protocols) |

**Savings:** 55-70% vs static 5,000-8,000 token prompts.

---

## 3. Generic Patterns

Generic patterns are **domain-agnostic templates**. Each domain INSTANTIATES these with specific entities, relationships, and business rules.

### 3.1 Pattern Registry

| Pattern | Question It Answers | Domain Examples |
|---------|---------------------|-----------------|
| **Fit Assessment** | Does X belong with Y? | Family fit, Audience fit, Supplier fit |
| **Value Discovery** | What should X cost/value? | Pricing, Budgeting, Estimation |
| **New Entity** | Should we create new Y? | New family, New segment, New category |
| **Duplicate Prevention** | Does X already exist? | Product, Campaign, Order dedup |
| **Domain Orientation** | What's the current state? | Catalog landscape, Market overview |

### 3.2 Instantiation Process

```
GENERIC PATTERN (domain-agnostic)
         |
         v
+-------------------+
| Replace:          |
| [ENTITY] → family |
| [SUBJECT] → product |
| [VALUE] → price   |
| [CRITERIA] → customer_segment |
+-------------------+
         |
         v
+-------------------+
| Add Domain Context: |
| - Why This Matters |
| - How to Interpret |
| - Anti-patterns    |
+-------------------+
         |
         v
DOMAIN PROTOCOL (Catalog-specific)
```

### 3.3 Fit Assessment Pattern

```xml
<pattern name="Fit Assessment" type="generic">

## PURPOSE
Determine if [SUBJECT] belongs with [ENTITY].

## STEPS

### Step 1: IDENTIFY - Target [ENTITY]
Document: [ENTITY_ID], [ENTITY_NAME]

### Step 2: QUERY - Qualifying [CRITERIA]
Execute: read_data(table="[CRITERIA_TABLE]", filters={"[ENTITY_KEY]": [id]})
Why: [CRITERIA] is THE deciding factor for fit.

### Step 3: QUERY - [ENTITY] Examples
Execute: read_data(table="[SUBJECT_TABLE]", filters={"[ENTITY_KEY]": [id]}, limit=10)

### Step 4: ANALYZE - [SUBJECT] Attributes
Determine [SUBJECT] profile based on attributes.

### Step 5: COMPARE - [CRITERIA] vs Attributes
- MATCH: Criteria aligns
- PARTIAL: Some alignment
- MISMATCH: Does not align

### Step 6: CONCLUDE
- MATCH: [SUBJECT] FITS this [ENTITY]
- PARTIAL: Present options to user
- MISMATCH: Needs DIFFERENT [ENTITY]

</pattern>
```

### 3.4 Value Discovery Pattern

```xml
<pattern name="Value Discovery" type="generic">

## PURPOSE
Determine appropriate [VALUE] for [SUBJECT] based on patterns.

## STEPS

### Step 1: IDENTIFY - [SUBJECT] Category
Classify into tier based on attributes.

### Step 2: QUERY - Similar [SUBJECTS]
Execute: read_data(table="[SUBJECT_TABLE]", filters={"[CATEGORY]": "[tier]"}, limit=15)

### Step 3: AGGREGATE - [VALUE] Range
Execute: aggregate_data(aggregations={"min": "[VALUE]", "max": "[VALUE]", "avg": "[VALUE]"})

### Step 4: POSITION - Within Range
Based on specific attributes, position within discovered range.

### Step 5: CONCLUDE
Recommend [VALUE] WITHIN discovered range.
Flag if outside range.

</pattern>
```

### 3.5 Multi-Domain Application

| Domain | Fit Assessment | Value Discovery |
|--------|----------------|-----------------|
| **Catalog** | Product → Family fit | Product pricing |
| **Marketing** | Campaign → Audience fit | Campaign budgeting |
| **Operations** | Order → Process fit | Task estimation |
| **Procurement** | Supplier → Category fit | Cost estimation |

**Same patterns, different instantiation.** This enables rapid domain expansion.

---

## 4. Domain Instantiation: Catalog

Catalog is the **first domain** implemented. This section shows how generic patterns become domain-specific protocols.

### 4.1 Business Context

```xml
<business_context domain="catalog">

## Positioning Tiers
- UTILITY (Rs 0-50): Functional buyers, plain products
- DECORATIVE (Rs 50-150): Gift buyers, designed products
- PREMIUM (Rs 150+): Luxury seekers, artisan products

## Key Relationships
- product_families → customer_segments (WHO buys)
- products → product_families (WHERE it belongs)
- customer_segments DETERMINES family fit (not material, not price)

## Common Misconceptions
- NOT: Same material = same family
- ACTUALLY: Same customer journey = same family

</business_context>
```

### 4.2 Protocol Index

```xml
<protocol_index>
| Situation | Protocol |
|-----------|----------|
| Which family does product belong to? | family_fit |
| What should this product cost? | pricing |
| Does this product already exist? | duplicate_prevention |
| Understanding the catalog landscape | business_context |
| No existing family matches | new_entity |

For familiar tasks with clear paths, proceed without loading protocols.
</protocol_index>
```

### 4.3 Family Fit Protocol (Instantiated)

```xml
<protocol name="Family Fit" domain="catalog">

## PURPOSE
Determine if a product belongs in a candidate family.

## STEPS

### Step 1: IDENTIFY - Candidate Family
Document: family_id, family_name

### Step 2: QUERY - Customer Segment
Execute: read_data(table="customer_segments", filters={"family_id": [id]})
Why: customer_segments is THE deciding factor. NOT material. NOT price.

### Step 3: QUERY - Family's Current Products
Execute: read_data(table="products", filters={"family_id": [id]}, limit=10)

### Step 4: ANALYZE - Product's Target Customer
Based on visual style, materials, price point:
- Utility/everyday use?
- Decorative/display?
- Gifting?
- Premium/luxury?

### Step 5: COMPARE - Customer Match
- MATCH: Same customer type
- PARTIAL: Overlapping but distinct
- MISMATCH: Different customer type

### Step 6: CONCLUDE
- MATCH + Cohesive: FITS this family
- PARTIAL/Ambiguous: Present options to user
- MISMATCH: Needs DIFFERENT family

## VERIFICATION
- [ ] Step 2 query executed (not assumed)
- [ ] Conclusion references step results

## ANTI-PATTERNS
- Concluding based on material match alone
- Using general retail knowledge instead of queried data

</protocol>
```

### 4.4 Pricing Protocol (Instantiated)

```xml
<protocol name="Pricing" domain="catalog">

## PURPOSE
Determine appropriate price based on catalog patterns.

## STEPS

### Step 1: IDENTIFY - Product Positioning
Classify: UTILITY / DECORATIVE / PREMIUM

### Step 2: QUERY - Similar Products
Execute: read_data(table="products", filters={"positioning": "[tier]"}, limit=15)

### Step 3: AGGREGATE - Price Range
Execute: aggregate_data(aggregations={"min": "price", "max": "price", "avg": "price"})

### Step 4: POSITION - Within Range
- Lower: Basic, simple
- Middle: Standard for category
- Upper: Premium features

### Step 5: CONCLUDE
Recommend specific price WITHIN discovered range.

</protocol>
```

### 4.5 Execution Example

```
TASK: Determine family fit for printed floral PET jar

STEP 1: IDENTIFY
Candidate: "PET Kitchen Storage" (fam-001)

STEP 2: QUERY - Customer Segment
Result: "Households organizing kitchen pantry - utility-focused buyers"

STEP 3: QUERY - Family Products
Result: Plain containers, bulk storage. Price Rs 25-60.

STEP 4: ANALYZE
Product: Printed floral design, decorative finish
Target: Gift buyers, home decor enthusiasts

STEP 5: COMPARE
Family: Utility buyers | Product: Decorative buyers
Assessment: MISMATCH

STEP 6: CONCLUDE
MISMATCH → Needs DIFFERENT FAMILY
→ Search for decorative family or trigger New Entity protocol
```

---

## 5. Protocol Composition

### 5.1 Composition Patterns

| Pattern | When | Example |
|---------|------|---------|
| Sequential | Each depends on previous | Duplicate → Fit → Pricing |
| Conditional | Branch on conclusion | If MISMATCH: New Entity |
| Parallel | Independent checks | Duplicate ∥ Schema Validation |

### 5.2 Standard Compositions

| Task | Protocol Sequence |
|------|-------------------|
| New Product | Duplicate → Fit → (New Entity?) → Pricing → Write |
| Update Product | Read Current → Validate → Write |
| Family Assignment | Orientation → Fit → (New Entity?) |

### 5.3 Ambiguous Results

| Scenario | Action |
|----------|--------|
| Clear winner | Proceed with decision |
| Multiple valid options | Present options to user via HITL |
| No valid options | Trigger alternative protocol |

**Control mechanism:** HITL on writes catches all decisions. Agent expresses uncertainty in natural language, not percentages.

---

## 6. Implementation

### 6.1 Phase Overview

| Phase | Focus | Status |
|-------|-------|--------|
| **Phase 1** | Foundation (Catalog) | READY |
| **Phase 2** | Core Protocols | PENDING |
| **Phase 3** | Token Optimization | PENDING |
| **Phase 4** | Multi-Domain | FUTURE |

### 6.2 Phase 1: Foundation

- [ ] Protocol file structure
- [ ] `create_load_protocol_tool()`
- [ ] `ProtocolInjectionMiddleware`
- [ ] `business_context.protocol` for Catalog
- [ ] Specialist prompt with protocol index

### 6.3 Phase 2: Core Protocols

- [ ] `duplicate_prevention.protocol`
- [ ] `family_fit.protocol`
- [ ] `pricing.protocol`
- [ ] `new_entity.protocol`

### 6.4 Phase 3: Token Optimization

- [ ] Summary protocol versions
- [ ] `protocol_depth` parameter
- [ ] Token budget enforcement

### 6.5 Phase 4: Multi-Domain

- [ ] Validate generic patterns across domains
- [ ] Second domain protocols (when needed)
- [ ] Cross-domain coordination

---

## 7. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-12-16 | Unified Tool + Middleware | All agents use same pattern |
| 2025-12-16 | Message-history based | REPL verified: ToolMessages persist |
| 2025-12-16 | Agent-driven selection | Pure autonomy; protocol index guides |
| 2025-12-16 | Per-agent directories | Resolution: agent-specific first, then shared |
| 2025-12-17 | Consolidated documentation | 77% reduction (4748 → 1090 lines) |
| 2025-12-17 | Removed confidence framework | HITL is control mechanism |

---

## 8. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Family assignment accuracy | 90%+ | HITL approval rate |
| Pricing acceptance | 85%+ | HITL approval rate |
| Duplicate prevention | 99%+ | Zero duplicates |
| Token usage | ~3,000 | LangSmith traces |

**Verification:** Use `workflow-evaluation` skill for trace analysis and protocol testing.

---

## 9. Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Protocol attention dilution | High | Token budget, tiered depth |
| Visual analysis ungrounded | Medium | Structured criteria, HITL |
| Agent skips protocols | High | Trace monitoring, prompt strengthening |
| Cold start errors | High | Heavy confirmation, warnings |

---

## References

- [PM_INTELLIGENCE_ROADMAP.md](./PM_INTELLIGENCE_ROADMAP.md) - Future PM capabilities
- [DOMAIN_DESIGN_GUIDELINES.md](./DOMAIN_DESIGN_GUIDELINES.md) - Design principles
- [AGENTS_DESIGN.md](./AGENTS_DESIGN.md) - Agent hierarchy

---

## Archived

Superseded by this document:
- `DOMAIN_REASONING_PROTOCOLS.md`
- `DOMAIN_REASONING_IMPLEMENTATION_PLAN.md`

---

**Version:** 3.0 (Vision-Aligned)
**Updated:** December 17, 2025
