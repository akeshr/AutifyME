# Domain Reasoning Framework

**Created:** December 15, 2025
**Consolidated:** December 17, 2025
**Status:** Phase 1 Ready
**Supersedes:** DOMAIN_REASONING_PROTOCOLS.md, DOMAIN_REASONING_IMPLEMENTATION_PLAN.md

---

## Executive Summary

LLMs are general-purpose. Our domains require specific behavior. Fine-tuning is not an option.

**Problem:** Output examples get COPIED, not understood. Rules get applied blindly.

**Solution:** Domain-Specific Reasoning Protocols - examples that encode the REASONING PROCESS, not just the output. Agents must EXECUTE the steps, not copy the answer.

**Core Mechanism:** Protocols force TOOL CALLS that ground reasoning in real data. Agents can't fake query results.

**Delivery:** `load_protocol` tool + `ProtocolInjectionMiddleware` injects protocols into system prompt on demand.

---

## Table of Contents

1. [Why Protocols Work](#1-why-protocols-work)
2. [Architecture](#2-architecture)
3. [Catalog Domain](#3-catalog-domain)
4. [Generic Patterns](#4-generic-patterns)
5. [Protocol Composition](#5-protocol-composition)
6. [Implementation](#6-implementation)
7. [Decision Log](#7-decision-log)
8. [Success Metrics](#8-success-metrics)
9. [Risk Register](#9-risk-register)

**Separate Documents:**
- [PM_INTELLIGENCE_ROADMAP.md](./PM_INTELLIGENCE_ROADMAP.md) - Future PM capabilities (aspirational)

---

## 1. Why Protocols Work

### 1.1 The Fundamental Gap

| What LLM Has | What Domain Needs |
|--------------|-------------------|
| General intelligence | Specific expertise |
| Broad knowledge | YOUR business rules |
| Pattern matching | Grounded reasoning |

### 1.2 Why Common Solutions Fail

| Approach | Limitation |
|----------|------------|
| **Output Examples** | Agent copies OUTPUT format, not REASONING |
| **Rules** | Abstract - agent doesn't know when/how to apply |
| **RAG** | Agent doesn't know what questions to ask |
| **More context** | Passive - doesn't guide reasoning |

### 1.3 The Protocol Solution

**Protocols are executable reasoning examples.** They show HOW to think, not just WHAT to conclude.

| Type | What It Shows | How Agent Uses It |
|------|---------------|-------------------|
| Rule | Abstract principle | Applies inconsistently |
| Output Example | Final result | Copies format |
| **Protocol** | Step-by-step process | EXECUTES each step |

### 1.4 Tool Grounding: The Core Mechanism

```
Without protocols:
Agent sees example --> Copies output --> Hallucinates data

With protocols:
Agent sees steps --> Executes read_data() --> Gets REAL data --> Reasons about ACTUAL results
```

**The agent can't fake query results.** When Step 2 says "EXECUTE read_data(...)", the tool returns actual database records.

### 1.5 The Grounding Boundary

Tool grounding prevents DATA hallucination, not INTERPRETATION errors.

| Step Type | Grounded? | Example |
|-----------|-----------|---------|
| QUERY | YES | read_data returns real records |
| AGGREGATE | YES | Statistics are factual |
| ANALYZE | NO | "This looks decorative" is inference |
| COMPARE | PARTIAL | Data side grounded, interpretation not |

**Visual analysis remains ungrounded.** Protocols structure the reasoning, but agents must apply genuine judgment on visual inference. Mitigation: structured criteria, comparison to grounded data, HITL checkpoint.

### 1.6 Protocol Applicability: ALL Agents

**Critical:** Protocols are NOT just for specialists. Every agent type needs domain grounding.

| Agent Level | Protocol Types | Why |
|-------------|----------------|-----|
| **PM** | Routing, Intelligence | Must understand domains to route correctly |
| **Analysts** | Exploration, Orientation, Tool Mastery | Must query comprehensively, discover patterns |
| **Specialists** | Decision, Domain-Specific, Tool Mastery | Must make grounded decisions using business rules |
| **Any SubAgent** | Tool Mastery | Must use tools efficiently |

**Protocol coverage by agent:**

| Protocol Category | PM | Analysts | Specialists |
|-------------------|:--:|:--------:|:-----------:|
| Tool Mastery | Y | Y | Y |
| Domain Orientation | Y | Y | Y |
| Business Context | Y | Y | Y |
| Routing/Intelligence | Y | - | - |
| Exploration Patterns | - | Y | - |
| Decision Protocols | - | - | Y |

### 1.7 Analyst vs Specialist Distinction

The line is about **ACCOUNTABILITY**, not capability.

| Aspect | Analyst | Specialist |
|--------|---------|------------|
| Primary function | Explore and suggest | Decide and commit |
| Output type | Findings, options, recommendations | Decisions, actions, writes |
| Accountability | "Here's what I found" | "This is the answer" |
| HITL trigger | Never (read-only) | On writes and uncertain decisions |
| Protocol usage | **IMPLICIT** (mental model) | **EXPLICIT** (documented execution) |

**Example:**

```
Analyst exploring family fit:
  "Product could fit in:
   - Decorative Ceramics (material match)
   - Kitchen Display (use case match)
   - Gift Items (customer match)
   Recommend evaluating each."

Specialist deciding family fit:
  [Executes full Fit Assessment Protocol]
  "Family: Decorative Ceramics
   Evidence: Customer segment query shows gift/decor buyers
   DECISION: Assign to Decorative Ceramics"
```

**Analysts use protocols IMPLICITLY** (guides what to explore).
**Specialists use protocols EXPLICITLY** (documented step execution).

---

## 2. Architecture

### 2.1 Protocol Delivery Mechanism

> STATUS: REPL VERIFIED

```
1. Agent calls load_protocol(["family_fit", "pricing"])
2. Tool returns protocol CONTENT (identified by tool name)
3. Middleware's wrap_model_call scans ToolMessages where msg.name == 'load_protocol'
4. Middleware deduplicates by protocol name, injects into system prompt
5. Agent sees protocol as INSTRUCTIONS (semantically correct placement)
```

**Key Design Decisions:**

| Decision | Rationale |
|----------|-----------|
| Message-history based | Config doesn't persist across tool calls; ToolMessages do |
| Tool name identification | `msg.name == 'load_protocol'` - no marker parsing |
| Batch loading | Single tool call for multiple protocols prevents parallel issues |
| Deduplication | Middleware tracks seen names, injects each once |
| Agent autonomy | Agent decides what to load based on protocol index |

**Protocol Selection Approach:**

| Aspect | Approach |
|--------|----------|
| Selection | Pure agent autonomy - agent matches situation to protocol index |
| Observability | Trace evaluation - `load_protocol` calls visible in LangSmith |
| Enforcement | None - measure first, strengthen prompt if agents skip |

Why not PM-specified protocols? Reduces autonomy, adds Task Specification complexity. Protocol index IS the domain grounding for selection. Trust agent to match, verify via traces.

### 2.2 Protocol Loading Tool

```python
# agents/src/autifyme_agents/tools/protocol_tools.py

from functools import lru_cache
from pathlib import Path
from langchain_core.tools import tool

PROTOCOL_BASE_PATH = Path(__file__).parent.parent / "prompts" / "protocols"


@lru_cache(maxsize=64)
def _load_protocol_content(agent_type: str, name: str) -> str:
    """Load protocol with resolution: agent-specific first, then shared."""
    agent_path = PROTOCOL_BASE_PATH / agent_type / f"{name}.protocol"
    if agent_path.exists():
        return agent_path.read_text(encoding="utf-8")

    shared_path = PROTOCOL_BASE_PATH / "shared" / f"{name}.protocol"
    if shared_path.exists():
        return shared_path.read_text(encoding="utf-8")

    raise FileNotFoundError(f"Protocol '{name}' not found for {agent_type}")


def create_load_protocol_tool(agent_type: str):
    """Factory for agent-specific load_protocol tool."""

    @tool
    def load_protocol(names: list[str]) -> str:
        """Load reasoning protocols for structured domain decisions.

        Load all needed protocols in ONE call to avoid parallel execution issues.

        Args:
            names: Protocol names (e.g., ['family_fit', 'pricing'])
        """
        results, errors = [], []

        for name in names:
            try:
                content = _load_protocol_content(agent_type, name)
                results.append(f"## Protocol: {name}\n{content}")
            except FileNotFoundError as e:
                errors.append(f"Error: {e}")

        output = "\n\n".join(results)
        if errors:
            output += "\n\n" + "\n".join(errors)
        return output if output else "\n".join(errors)

    return load_protocol
```

### 2.3 Protocol Injection Middleware

```python
# agents/src/autifyme_agents/middleware/protocol_injection.py

from typing import Callable
from deepagents.graph import AgentMiddleware
from langchain_core.messages import SystemMessage, ToolMessage


class ProtocolInjectionMiddleware(AgentMiddleware):
    """Injects loaded protocols into system prompt before LLM call."""

    def wrap_model_call(
        self,
        request,
        handler: Callable,
    ):
        """Scan for load_protocol results, deduplicate, inject."""
        seen_protocols: dict[str, str] = {}

        for msg in request.state.get("messages", []):
            if not isinstance(msg, ToolMessage):
                continue
            if msg.name != "load_protocol":
                continue
            if str(msg.content).startswith("Error:"):
                continue

            content = str(msg.content)
            for section in content.split("## Protocol: ")[1:]:
                lines = section.split("\n", 1)
                name = lines[0].strip()
                body = lines[1] if len(lines) > 1 else ""
                if name not in seen_protocols:
                    seen_protocols[name] = f"## Protocol: {name}\n{body}"

        if seen_protocols:
            protocol_section = (
                "<active_protocols>\n"
                + "\n\n".join(seen_protocols.values())
                + "\n</active_protocols>"
            )
            new_prompt = (request.system_prompt or "") + "\n\n" + protocol_section
            request = request.override(system_message=SystemMessage(content=new_prompt))

        return handler(request)
```

### 2.4 Protocol Lifecycle

Protocol lifecycle is bounded by message history scope. No explicit management needed.

| Scope | Behavior |
|-------|----------|
| SubAgents | Fresh messages per invocation = automatic isolation |
| PM | New conversation = fresh messages = clean start |
| Same conversation | ToolMessages persist, protocols remain active |

### 2.5 Protocol Library Structure

```
agents/src/autifyme_agents/prompts/protocols/
├── pm/                              # PM orchestration protocols
│   └── (future: routing, multi-domain)
├── catalog_specialist/              # Catalog domain decisions
│   ├── business_context.protocol
│   ├── family_fit.protocol
│   ├── pricing.protocol
│   ├── duplicate_prevention.protocol
│   └── new_entity.protocol
├── catalog_analyst/                 # Catalog exploration (implicit use)
│   ├── catalog_exploration.protocol
│   └── family_analysis.protocol
└── shared/                          # Cross-agent protocols
    ├── fit_assessment.protocol      # Generic pattern
    ├── value_discovery.protocol     # Generic pattern
    └── tool_mastery/
        ├── read_data.protocol
        └── aggregate_data.protocol
```

**Resolution order:** Agent-specific (`protocols/{agent_type}/`) first, then shared (`protocols/shared/`).

### 2.6 Token Budget

| Component | Tokens | Notes |
|-----------|--------|-------|
| Base specialist prompt | ~1,500 | Identity + tools + protocol index |
| Per protocol loaded | ~400-600 | On demand |
| Simple task | ~1,500 | No protocols needed |
| Complex task | ~2,500-3,000 | 2-3 protocols |

**Comparison:** Old static prompts: 5,000-8,000 tokens always. New approach: 55-70% savings on typical tasks.

---

## 3. Catalog Domain

### 3.1 Business Context

```xml
<business_context domain="catalog">

## Positioning Tiers

### UTILITY (Budget: Rs 0-50)
- Customer: Price-conscious, functional buyers
- Products: Plain, bulk, everyday use
- Signal: "Affordable, practical"

### DECORATIVE (Mid: Rs 50-150)
- Customer: Gift buyers, aesthetics-conscious
- Products: Designed, gift-worthy, display items
- Signal: "Worth presenting, thoughtful"

### PREMIUM (Rs 150+)
- Customer: Luxury seekers, statement makers
- Products: Artisan, unique, high-quality
- Signal: "Special, exclusive"

## Key Relationships

- product_families --> customer_segments (who buys from this family)
- products --> product_families (which family product belongs to)
- customer_segments DETERMINES family fit (not material, not price)

## Common Misconceptions

- NOT: Same material = same family
- ACTUALLY: Same customer journey = same family
- NOT: Price determines positioning
- ACTUALLY: Positioning determines price range

</business_context>
```

### 3.2 Protocol Index (Specialist Prompt Section)

```xml
<protocol_index>
When you need structured guidance, use load_protocol:

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

### 3.3 Family Fit Protocol (Reference)

> Actual content in: `protocols/catalog_specialist/family_fit.protocol`

```xml
<protocol name="Family Fit" domain="catalog" type="decision">

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
Compare Step 2 (family's customer) with Step 4 (product's customer):
- MATCH: Same customer type (90%+)
- PARTIAL: Overlapping (60-89%)
- MISMATCH: Different type (<60%)

### Step 6: COMPARE - Product Cohesion
Would customer browsing the family naturally consider this product?

### Step 7: CONCLUDE
- MATCH + Cohesive: FITS this family
- MATCH + Not Cohesive: FITS, consider sub-family
- PARTIAL/Ambiguous: Present options to user
- MISMATCH: Needs DIFFERENT family

## VERIFICATION
- [ ] Step 2 query executed (not assumed)
- [ ] Step 3 query executed
- [ ] Conclusion references step results

## ANTI-PATTERNS
- Concluding based on material match alone
- Skipping customer segment query
- Using general retail knowledge instead of queried data

</protocol>
```

### 3.4 Pricing Protocol (Reference)

> Actual content in: `protocols/catalog_specialist/pricing.protocol`

```xml
<protocol name="Pricing" domain="catalog" type="decision">

## PURPOSE
Determine appropriate price based on catalog patterns.

## STEPS

### Step 1: IDENTIFY - Product Positioning
Classify: UTILITY / DECORATIVE / PREMIUM (see business_context)

### Step 2: QUERY - Similar Products
Execute: read_data(table="products", filters={"positioning": "[tier]"}, limit=15)

Why: Similar products reveal YOUR established patterns, not market assumptions.

### Step 3: AGGREGATE - Price Range
Execute: aggregate_data(table="products", filters={"positioning": "[tier]"},
         aggregations={"min": "price", "max": "price", "avg": "price", "count": "id"})

### Step 4: POSITION - Within Range
- Lower: Basic, simple, functional
- Middle: Standard for category
- Upper: Premium features, higher quality

### Step 5: CONCLUDE
- Recommend specific price WITHIN discovered range
- If outside range warranted, FLAG for review

## VERIFICATION
- [ ] Step 2 query executed
- [ ] Step 3 aggregate executed
- [ ] Recommendation within range

</protocol>
```

### 3.5 Protocol Execution Example

```
TASK: Determine family fit for printed floral PET jar

STEP 1: IDENTIFY
Candidate: "PET Kitchen Storage" (fam-001)
Source: Analyst suggestion based on material match

STEP 2: QUERY - Customer Segment
Executed: read_data(table="customer_segments", filters={"family_id": "fam-001"})
Result: "Households organizing kitchen pantry - utility-focused buyers"

STEP 3: QUERY - Family Products
Executed: read_data(table="products", filters={"family_id": "fam-001"}, limit=10)
Result: Plain containers, bulk storage, organizers. Price Rs 25-60.

STEP 4: ANALYZE - Product's Customer
Product: Printed floral design, decorative finish, gift packaging
Target: Gift buyers, home decor enthusiasts (NOT pantry organizers)

STEP 5: COMPARE - Customer Match
Family: Utility buyers | Product: Decorative buyers
Assessment: MISMATCH - different customer intent

STEP 6: COMPARE - Cohesion
Family: Plain, functional | Product: Decorative, designed
Assessment: Would NOT be browsed together

STEP 7: CONCLUDE
MISMATCH + Not Cohesive = Needs DIFFERENT FAMILY
--> Trigger: Search for decorative family or New Entity protocol
```

---

## 4. Generic Patterns

Generic patterns are domain-agnostic templates. Domain protocols INSTANTIATE these with specific entities.

### 4.1 Pattern Registry

| Pattern | Purpose | Instantiation |
|---------|---------|---------------|
| Fit Assessment | Does X belong with Y? | Family Fit, Audience Fit |
| Value Discovery | What should X cost/value? | Pricing, Budget Discovery |
| New Entity | Should we create new Y? | New Family, New Segment |
| Duplicate Prevention | Does X already exist? | Product duplicate check |
| Domain Orientation | Current state of domain? | Catalog landscape |

### 4.2 Instantiation Process

```
GENERIC PATTERN
      |
      v
+------------------+
| Replace          |
| - [ENTITY]       | --> family, audience, supplier
| - [SUBJECT]      | --> product, campaign, order
| - [VALUE]        | --> price, budget, cost
| - [CRITERIA]     | --> customer_segment, audience_profile
+------------------+
      |
      v
+------------------+
| Add Domain       |
| - Why This Matters (business significance)
| - How to Interpret (domain guidance)
| - Anti-patterns (domain-specific)
+------------------+
      |
      v
DOMAIN PROTOCOL
```

### 4.3 Fit Assessment Pattern (Abstract)

```xml
<pattern name="Fit Assessment" type="generic">

### Step 1: IDENTIFY - Target [ENTITY]
Document: [ENTITY_ID], [ENTITY_NAME]

### Step 2: QUERY - Qualifying [CRITERIA]
Execute: read_data(table="[CRITERIA_TABLE]", filters={"[ENTITY_KEY]": [id]})

Why: [CRITERIA] is THE deciding factor for fit.

### Step 3: QUERY - [ENTITY] Examples (Optional)
Execute: read_data(table="[SUBJECT_TABLE]", filters={"[ENTITY_KEY]": [id]}, limit=10)

### Step 4: ANALYZE - [SUBJECT] Attributes
Determine [SUBJECT] profile based on attributes.

### Step 5: COMPARE - [CRITERIA] vs Attributes
- MATCH: Criteria aligns
- MISMATCH: Criteria does not align
- PARTIAL: Some alignment, some gaps

### Step 6: CONCLUDE
- MATCH: [SUBJECT] FITS this [ENTITY]
- MISMATCH: [SUBJECT] needs DIFFERENT [ENTITY]
- PARTIAL: Consider alternatives

</pattern>
```

### 4.4 Value Discovery Pattern (Abstract)

```xml
<pattern name="Value Discovery" type="generic">

### Step 1: IDENTIFY - [SUBJECT] Category
Classify into tier: [TIER_1] / [TIER_2] / [TIER_3]

### Step 2: QUERY - Similar [SUBJECTS]
Execute: read_data(table="[SUBJECT_TABLE]", filters={"[CATEGORY]": "[tier]"}, limit=15)

### Step 3: AGGREGATE - [VALUE] Range
Execute: aggregate_data(table="[SUBJECT_TABLE]", filters={"[CATEGORY]": "[tier]"},
         aggregations={"min": "[VALUE]", "max": "[VALUE]", "avg": "[VALUE]"})

### Step 4: POSITION - Within Range
- Lower end: [WHEN_LOWER]
- Middle: [WHEN_MIDDLE]
- Upper end: [WHEN_UPPER]

### Step 5: CONCLUDE
Recommend [VALUE] WITHIN discovered range.
Flag if outside range.

</pattern>
```

---

## 5. Protocol Composition

Tasks rarely need a single protocol. This section defines chaining rules.

### 5.1 Composition Patterns

| Pattern | When | Example |
|---------|------|---------|
| Sequential | Each depends on previous | Duplicate --> Fit --> Pricing |
| Conditional | Branch on conclusion | If MISMATCH: New Entity |
| Parallel | Independent checks | Duplicate ∥ Schema Validation |

### 5.2 Standard Compositions

| Task | Protocol Sequence |
|------|-------------------|
| New Product | Duplicate --> Fit --> (New Entity?) --> Pricing --> Write |
| Update Product | Read Current --> Validate --> Write |
| Family Assignment | Orientation --> Fit --> (New Entity?) |
| Price Recommendation | Orientation --> Value Discovery |

### 5.3 Ambiguous Results

When protocol yields no clear answer (e.g., multiple families seem valid):

| Scenario | Action |
|----------|--------|
| Clear winner | Proceed with decision |
| Multiple valid options | Present options to user via HITL |
| No valid options | Trigger alternative protocol (e.g., New Entity) |

**Control mechanism:** HITL on writes catches all decisions. Agent expresses uncertainty in natural language, not percentages.

---

## 6. Implementation

### 6.1 Phase Overview

| Phase | Focus | Duration | Status |
|-------|-------|----------|--------|
| **Phase 1** | Foundation | 1 week | READY |
| **Phase 2** | Core Protocols | 1 week | PENDING |
| **Phase 3** | Token Optimization | 3-4 days | PENDING |
| **Phase 4** | Multi-Domain | 2 weeks | FUTURE |

### 6.2 Phase 1: Foundation

**Deliverables:**
- [ ] Protocol file structure created
- [ ] `create_load_protocol_tool()` in `tools/protocol_tools.py`
- [ ] `ProtocolInjectionMiddleware` in `middleware/protocol_injection.py`
- [ ] `business_context.protocol` for Catalog
- [ ] Specialist prompt updated with protocol index
- [ ] Integration test: load --> inject --> verify in system prompt

### 6.3 Phase 2: Core Protocols

**Deliverables:**
- [ ] `duplicate_prevention.protocol`
- [ ] `family_fit.protocol`
- [ ] `pricing.protocol`
- [ ] `new_entity.protocol`
- [ ] Integration test: full protocol chain execution

### 6.4 Phase 3: Token Optimization

**Deliverables:**
- [ ] Summary versions of protocols (~150-200 tokens)
- [ ] `protocol_depth` parameter (full/summary)
- [ ] Token budget enforcement middleware
- [ ] Metrics: token usage before/after

### 6.5 Phase 4: Multi-Domain

**Deliverables:**
- [ ] Generic patterns validated across domains
- [ ] Second domain protocols (when needed)
- [ ] Cross-domain coordination (when needed)

---

## 7. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-12-16 | Unified Tool + Middleware | All agents use same pattern; semantically correct |
| 2025-12-16 | Message-history based | REPL verified: config doesn't persist; ToolMessages do |
| 2025-12-16 | Tool name identification | `msg.name == 'load_protocol'` - no marker parsing |
| 2025-12-16 | Batch loading (list input) | Prevents parallel tool call race conditions |
| 2025-12-16 | Middleware deduplication | Prevents duplicate injection |
| 2025-12-16 | No unload_protocol tool | Natural scope boundaries; adds complexity with no benefit |
| 2025-12-16 | Agent-driven selection | Agent autonomy preserved; PM provides defaults |
| 2025-12-16 | Per-agent protocol directories | Resolution: agent-specific first, then shared |
| 2025-12-17 | Consolidated documentation | Merged framework + implementation; eliminated redundancy |
| 2025-12-17 | Removed confidence framework | HITL on writes is control mechanism; agent expresses uncertainty naturally |

---

## 8. Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Family assignment accuracy | TBD | 90%+ | HITL approval rate |
| Pricing acceptance | TBD | 85%+ | HITL approval rate |
| Duplicate prevention | TBD | 99%+ | Zero duplicates created |
| Token usage per call | ~8,000 | ~3,000 | LangSmith traces |
| Protocol step completion | TBD | 100% | Trace analysis |

---

## 9. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Protocol size causes attention dilution | Medium | High | Token budget, tiered depth |
| Visual analysis remains ungrounded | High | Medium | Structured criteria, HITL |
| Cold start bootstrap errors | Medium | High | Heavy confirmation, warnings |
| Protocol coverage gaps | Medium | Medium | Fallback guidance, gap tracking |
| Agent skips protocol steps | Medium | High | Verification sections, trace monitoring |

---

## References

- [PM_INTELLIGENCE_ROADMAP.md](./PM_INTELLIGENCE_ROADMAP.md) - Future PM capabilities
- [DOMAIN_DESIGN_GUIDELINES.md](./DOMAIN_DESIGN_GUIDELINES.md) - General design principles
- [PROMPT_ENGINEERING_STANDARDS.md](../tech/PROMPT_ENGINEERING_STANDARDS.md) - Prompt design
- [UV_REPL_BEST_PRACTICES.md](../tech/UV_REPL_BEST_PRACTICES.md) - API verification

---

## Archived Documents

The following documents are superseded by this consolidated framework:
- `DOMAIN_REASONING_PROTOCOLS.md` (archived)
- `DOMAIN_REASONING_IMPLEMENTATION_PLAN.md` (archived)

---

**Document Version:** 2.0 (Consolidated)
**Last Updated:** December 17, 2025
