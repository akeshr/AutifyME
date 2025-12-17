# Domain Reasoning Framework

**Created:** December 15, 2025
**Rewritten:** December 17, 2025
**Status:** Phase 1 Ready
**Grounded In:** [ARCHITECTURAL_VISION.md](../ARCHITECTURAL_VISION.md), [AGENTS_DESIGN.md](./AGENTS_DESIGN.md), [AUTONOMY_PROBLEMS.md](../AUTONOMY_PROBLEMS.md)

---

## 1. Context: The AutifyME Vision

> "AutifyME is not a cataloging system. It is a **multi-domain autonomous business operating system**."
> -- ARCHITECTURAL_VISION.md

**The Domains:**
- **Catalog:** Product information, inventory, pricing, manufacturing data
- **Creative:** Image processing, visual assets, brand consistency
- **Operations:** Quality control, compliance, fulfillment workflows
- **Marketing:** Campaign assets, positioning, competitive analysis
- **Procurement:** Supplier coordination, sourcing, cost analysis
- **Quality:** Defect identification, standards compliance
- **Future:** Customer service, analytics, forecasting

**Each domain has deep expertise. Each domain performs with utmost quality. Each domain explores possibilities autonomously.**

---

## 2. The Architecture

From [AGENTS_DESIGN.md](./AGENTS_DESIGN.md) - the 2-Level Model:

```
[User Request]
      |
      v
+---------------------------+
| PROJECT MANAGER           |
| - Analyzes INTENT         |
| - Routes dynamically      |
| - Delegates with CONTEXT  |
| - Synthesizes results     |
+---------------------------+
      |
      +---> [Analysts]      (Read-only exploration, cheap models)
      |     - visual_analyst
      |     - product_analyst
      |     - catalog_analyst
      |
      +---> [Specialists]   (Domain experts, Explore->Reason->Output)
            - catalog_specialist
            - creative_specialist
            - (future domains)
                  |
                  v
               [Tools]
```

### PM Role (from ARCHITECTURAL_VISION.md)

**PM Does:**
- Analyze user INTENT (not content)
- Identify which domains are involved
- Delegate to analysts for content analysis
- Use analyst summaries to decide next steps dynamically
- Synthesize multi-domain outputs into coherent narrative

**PM Does NOT:**
- Analyze image content, research products, or query catalog
- Follow fixed workflow templates
- Tell subagents what to do (passes context, not instructions)

### Analyst Role (from ARCHITECTURAL_VISION.md)

Analysts are **PM's intelligence layer** for detailed content analysis:
- **Read-only:** view_image, read_data, research_product_tool, aggregate_data
- **No execution:** Never write_data, never persistence
- **Cheap models:** Gemini 2.5 Flash (~$0.01/1K tokens)
- **Output:** Write to workspace/thread_123/*.md, return summary + path to PM

### Specialist Role (from ARCHITECTURAL_VISION.md)

Specialists are **autonomous domain masters**:

> "Explorative Problem-Solving (Explore -> Reason -> Output) **ALWAYS**"

1. **EXPLORE** - Query data, inspect schema, view images, validate prerequisites
2. **REASON** - Synthesize findings, apply domain expertise, evaluate options
3. **OUTPUT** - Execute with validated information, verify outputs

**Critical:** Analyst context is SUPPLEMENTARY. Specialists ALWAYS explore.

---

## 3. The Problem Protocols Solve

From [AUTONOMY_PROBLEMS.md](../AUTONOMY_PROBLEMS.md):

> "LLMs are general-purpose - they DON'T know your tools, business rules, or domain expectations."

**The Gap:**

| What LLM Has | What Domain Needs |
|--------------|-------------------|
| Generic retail knowledge | YOUR catalog patterns |
| Material-based reasoning | Customer-segment reasoning |
| Market assumptions | YOUR pricing data |
| Inconsistent heuristics | Repeatable domain logic |

**The Solution:** Domain Reasoning Protocols - executable examples that ground the EXPLORE step in Explore->Reason->Output.

---

## 4. How Protocols Enable Autonomy

Protocols **support** the Explore->Reason->Output pattern. They don't replace it.

```
SPECIALIST RECEIVES TASK
         |
         v
+-------------------+
| EXPLORE (Step 1)  |  <-- Protocols provide STRUCTURE here
| - Load protocol   |
| - Execute queries |
| - Gather data     |
+-------------------+
         |
         v
+-------------------+
| REASON (Step 2)   |  <-- Agent applies domain expertise
| - Analyze results |
| - Apply criteria  |
| - Form conclusion |
+-------------------+
         |
         v
+-------------------+
| OUTPUT (Step 3)   |  <-- Agent acts on reasoning
| - Write decision  |
| - HITL approval   |
| - Verify output   |
+-------------------+
```

### Core Principle Alignment

From ARCHITECTURAL_VISION.md Core Design Principles:

| Principle | How Protocols Align |
|-----------|---------------------|
| **P1: Intelligence-First** | Protocols give context, not step-by-step recipes |
| **P3: Explorative Over Prescriptive** | Protocols structure exploration, not dictate conclusions |
| **P5: Verification Over Hope** | Protocols force tool calls that return real data |

### Tool Grounding: Why Protocols Work

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

**The agent can't fake query results.** When a protocol says "Execute read_data(...)", the tool returns actual database records. This grounds exploration in reality.

### The Grounding Boundary

| Step Type | Grounded? | Example |
|-----------|-----------|---------|
| QUERY | YES | read_data returns real records |
| AGGREGATE | YES | Statistics are factual |
| ANALYZE | NO | "This looks decorative" is inference |
| COMPARE | PARTIAL | Data grounded, interpretation not |

**Mitigation for ungrounded steps:** Structured criteria, comparison to grounded data, HITL checkpoint.

---

## 5. Protocol Architecture

### 5.1 Who Uses Protocols

| Agent | Protocol Usage | Purpose |
|-------|----------------|---------|
| **PM** | Rarely | PM delegates content analysis, doesn't do it |
| **Analysts** | Implicitly | Mental model for comprehensive exploration |
| **Specialists** | Explicitly | Structured exploration before decisions |

**Key insight:** PM passes CONTEXT to specialists, not protocols. Specialists decide which protocols to load based on their domain expertise.

### 5.2 Protocol Delivery

```
1. Specialist receives task from PM (context, not instructions)
2. Specialist assesses: "What exploration do I need?"
3. Specialist calls load_protocol(["family_fit", "pricing"])
4. Middleware injects protocol content into system prompt
5. Specialist executes exploration steps
6. Specialist reasons and outputs decision
```

### 5.3 Protocol Library Structure

```
protocols/
├── catalog_specialist/      # Catalog domain
│   ├── business_context.protocol
│   ├── family_fit.protocol
│   ├── pricing.protocol
│   └── duplicate_prevention.protocol
├── creative_specialist/     # Creative domain (FUTURE)
├── marketing_specialist/    # Marketing domain (FUTURE)
└── shared/                  # Cross-domain patterns
    ├── fit_assessment.protocol
    ├── value_discovery.protocol
    └── new_entity.protocol
```

**Resolution:** Agent-specific first, then shared.

### 5.4 Protocol Loading Tool

```python
def create_load_protocol_tool(agent_type: str):
    """Factory for agent-specific load_protocol tool."""

    @tool
    def load_protocol(names: list[str]) -> str:
        """Load reasoning protocols for structured domain decisions.

        USE WHEN: You need structured exploration for domain decisions.
        DON'T USE: For familiar tasks with clear paths.
        """
        results = []
        for name in names:
            content = _load_protocol_content(agent_type, name)
            results.append(f"## Protocol: {name}\n{content}")
        return "\n\n".join(results)

    return load_protocol
```

### 5.5 Integration with Autonomy Pattern

From AUTONOMY_PROBLEMS.md, specialists now have:

```xml
**Your Autonomy:**
- You EXPLORE first, regardless of what context PM provides
- Analyst findings are SUPPLEMENTARY - validate through your own exploration
- You decide HOW to accomplish the goal PM delegates
- You are a domain MASTER, not a passive executor
```

Protocols serve this autonomy by providing structured exploration patterns when the specialist determines they're needed.

---

## 6. Generic Patterns

Generic patterns are **domain-agnostic templates**. Each domain instantiates with specific entities and business rules.

### 6.1 Pattern Registry

| Pattern | Question | Examples |
|---------|----------|----------|
| **Fit Assessment** | Does X belong with Y? | Family fit, Audience fit, Supplier fit |
| **Value Discovery** | What should X cost? | Pricing, Budgeting, Estimation |
| **New Entity** | Should we create Y? | New family, New segment |
| **Duplicate Prevention** | Does X exist? | Product, Campaign dedup |

### 6.2 Fit Assessment Pattern

```xml
<pattern name="Fit Assessment" type="generic">

## PURPOSE
Ground the decision: Does [SUBJECT] belong with [ENTITY]?

## EXPLORATION STEPS

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
- PARTIAL: Present options to user via HITL
- MISMATCH: Needs DIFFERENT [ENTITY]

</pattern>
```

### 6.3 Value Discovery Pattern

```xml
<pattern name="Value Discovery" type="generic">

## PURPOSE
Ground the decision: What should [SUBJECT] cost/value?

## EXPLORATION STEPS

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

### 6.4 Multi-Domain Application

| Domain | Fit Assessment | Value Discovery |
|--------|----------------|-----------------|
| **Catalog** | Product -> Family fit | Product pricing |
| **Marketing** | Campaign -> Audience fit | Campaign budgeting |
| **Operations** | Order -> Process fit | Task estimation |
| **Procurement** | Supplier -> Category fit | Cost estimation |

---

## 7. Domain Instantiation: Catalog

Catalog is the **first domain**. This shows how generic patterns become domain-specific protocols.

### 7.1 Business Context

```xml
<business_context domain="catalog">

## Positioning Tiers
- UTILITY (Rs 0-50): Functional buyers, plain products
- DECORATIVE (Rs 50-150): Gift buyers, designed products
- PREMIUM (Rs 150+): Luxury seekers, artisan products

## Key Relationships
- product_families -> customer_segments (WHO buys)
- products -> product_families (WHERE it belongs)
- customer_segments DETERMINES family fit (not material, not price)

## Common Misconceptions
- NOT: Same material = same family
- ACTUALLY: Same customer journey = same family

</business_context>
```

### 7.2 Protocol Index (In Specialist Prompt)

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

### 7.3 Family Fit Protocol (Instantiated)

```xml
<protocol name="Family Fit" domain="catalog">

## PURPOSE
Ground the decision: Does this product belong in this family?

## EXPLORATION STEPS

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
- MATCH: Product FITS this family
- PARTIAL: Present options to user via HITL
- MISMATCH: Needs DIFFERENT family -> Search or New Entity

## VERIFICATION
- [ ] Step 2 query executed (not assumed)
- [ ] Conclusion references step results

## ANTI-PATTERNS
- Concluding based on material match alone
- Using general retail knowledge instead of queried data

</protocol>
```

### 7.4 Execution Example

```
TASK: Determine family fit for printed floral PET jar

EXPLORE (Protocol-guided):
  Step 1: Candidate "PET Kitchen Storage" (fam-001)
  Step 2: read_data(customer_segments) -> "Utility-focused buyers"
  Step 3: read_data(products) -> Plain containers, Rs 25-60

REASON (Agent expertise):
  Product has: Printed floral design, decorative finish
  Target customer: Gift buyers, home decor enthusiasts
  Family customer: Utility buyers
  Assessment: MISMATCH

OUTPUT (Decision):
  MISMATCH -> Needs DIFFERENT FAMILY
  -> Search for decorative family or trigger New Entity protocol
```

---

## 8. Communication Protocol

From ARCHITECTURAL_VISION.md - filesystem-based coordination:

```
workspace/thread_123/
├── visual_analysis.md      # visual_analyst output
├── catalog_analysis.md     # catalog_analyst output
├── product_research.md     # product_analyst output
└── catalog_results.md      # catalog_specialist output (includes protocol execution)
```

**Flow:**
1. PM delegates with context (1-2 liner)
2. Analyst/Specialist explores (using protocols when needed)
3. Agent writes detailed findings to filesystem
4. Agent returns summary + file path to PM
5. PM reasons about next step from summary

---

## 9. Implementation

### 9.1 Phase Overview

| Phase | Focus | Status |
|-------|-------|--------|
| **Phase 1** | Foundation | READY |
| **Phase 2** | Core Protocols | PENDING |
| **Phase 3** | Multi-Domain | FUTURE |

### 9.2 Phase 1: Foundation

- [ ] Protocol file structure
- [ ] `create_load_protocol_tool()`
- [ ] `ProtocolInjectionMiddleware`
- [ ] `business_context.protocol` for Catalog
- [ ] Add protocol index to catalog_specialist prompt

### 9.3 Phase 2: Core Protocols

- [ ] `family_fit.protocol`
- [ ] `pricing.protocol`
- [ ] `duplicate_prevention.protocol`
- [ ] `new_entity.protocol`

---

## 10. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-12-16 | Unified Tool + Middleware | All agents use same pattern |
| 2025-12-16 | Message-history based | REPL verified: ToolMessages persist |
| 2025-12-16 | Agent-driven selection | Pure autonomy; specialists decide when to load |
| 2025-12-17 | Protocols enable autonomy | Serve Explore->Reason->Output, don't replace it |
| 2025-12-17 | HITL is control mechanism | No confidence scores; HITL catches decisions |

---

## 11. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Family assignment accuracy | 90%+ | HITL approval rate |
| Pricing acceptance | 85%+ | HITL approval rate |
| Duplicate prevention | 99%+ | Zero duplicates |
| Token usage | ~3,000 | LangSmith traces |

**Verification:** Use `workflow-evaluation` skill for trace analysis.

---

## 12. Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Protocol attention dilution | High | Token budget, load only when needed |
| Visual analysis ungrounded | Medium | Structured criteria, HITL |
| Agent skips protocols | High | Trace monitoring, prompt strengthening |
| Protocols become prescriptive | High | Design review against P3 (Explorative Over Prescriptive) |

---

## References

- [ARCHITECTURAL_VISION.md](../ARCHITECTURAL_VISION.md) - North star vision
- [AGENTS_DESIGN.md](./AGENTS_DESIGN.md) - 2-Level architecture
- [AUTONOMY_PROBLEMS.md](../AUTONOMY_PROBLEMS.md) - Autonomy fixes
- [DOMAIN_DESIGN_GUIDELINES.md](./DOMAIN_DESIGN_GUIDELINES.md) - Domain design
- [PM_INTELLIGENCE_ROADMAP.md](./PM_INTELLIGENCE_ROADMAP.md) - Future PM capabilities

---

**Version:** 4.0 (Properly Grounded)
**Updated:** December 17, 2025
