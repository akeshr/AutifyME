# Domain Reasoning Framework

**Created:** December 15, 2025
**Rewritten:** December 17, 2025 (ULTRATHINK revision)
**Status:** Phase 1 Ready
**Grounded In:** [ARCHITECTURAL_VISION.md](../ARCHITECTURAL_VISION.md), [AGENTS_DESIGN.md](./AGENTS_DESIGN.md), [AUTONOMY_PROBLEMS.md](../AUTONOMY_PROBLEMS.md)

---

## 1. Vision Context

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

---

## 2. The Domain Model

### 2.1 What IS a Domain?

A domain is a coherent area of business expertise with:
- **Vocabulary:** Specific terms and mental models
- **Business Rules:** Decision criteria and constraints
- **Data Entities:** Tables, relationships, patterns
- **Quality Standards:** Verification and acceptance criteria

### 2.2 Domain Structure

Each domain contains:

```
DOMAIN (e.g., Catalog)
|
+---> Protocols
|     +---> Business Context (domain orientation)
|     +---> Decision Protocols (family_fit, pricing)
|     +---> Exploration Protocols (what to investigate)
|     +---> Tool Mastery (how to use tools in this domain)
|
+---> Analysts (read-only exploration, cheap models)
|     +---> Domain-specific (catalog_analyst)
|     +---> Cross-domain (visual_analyst, product_analyst)
|
+---> Specialists (execution with HITL, expensive models)
|     +---> catalog_specialist
|
+---> Domain-Specific Tools (if any)
      +---> (future: save_product_family, etc.)
```

### 2.3 Domain Ownership Matrix

| Decision Type | Owning Domain | Cross-Domain Input |
|---------------|---------------|-------------------|
| Product family assignment | Catalog | Visual analysis |
| Product pricing | Catalog | Market research |
| Image generation | Creative | Product context from Catalog |
| Campaign asset creation | Marketing | Product context from Catalog |
| Quality assessment | Quality | Visual analysis |
| Supplier evaluation | Procurement | Product specs from Catalog |

### 2.4 Domain Boundary Scenarios

Understanding how tasks map to domains:

**Scenario 1: Single-Domain Task**
```
User: "Add this product to catalog"

Analysis:
- Domain: Catalog (clear ownership)
- Agents: visual_analyst -> catalog_analyst -> catalog_specialist
- Cross-domain input: None needed
- Result: Single domain handles entirely
```

**Scenario 2: Multi-Domain Task**
```
User: "Create marketing images for product X"

Analysis:
- Domains: Catalog + Creative (+ Catalog again)
- Flow:
  1. Catalog: Get product details (product_id, attributes)
  2. Creative: Generate images (needs product context)
  3. Catalog: Link assets to product (needs asset_ids)
- Dependencies: Sequential (each step needs prior output)
- PM Role: Coordinate handoffs, pass context between domains
```

**Scenario 3: Cross-Domain Decision**
```
User: "Is this product quality good enough to catalog?"

Analysis:
- Primary: Quality domain (assessment)
- Secondary: Catalog domain (final decision)
- Flow:
  1. Quality: Assess defects, compliance, standards
  2. Catalog: Use quality assessment to decide cataloging
- Decision owner: Catalog (Quality provides input)
```

**Scenario 4: Ambiguous Domain**
```
User: "Generate product description"

Analysis:
- Could be: Catalog (product data) OR Marketing (positioning)
- Resolution: PM analyzes INTENT
  - If for catalog listing -> Catalog domain
  - If for campaign -> Marketing domain
- PM asks if ambiguous, doesn't guess
```

---

## 3. Agents Within Domains

### 3.1 Analyst vs Specialist

| Aspect | Analyst | Specialist |
|--------|---------|------------|
| **Purpose** | Gather, explore, understand | Decide, execute, create |
| **Tools** | Read-only (read_data, view_image, aggregate_data) | Read + Write (write_data, image_studio) |
| **Output** | Information for PM/Specialist | Persistent changes, artifacts |
| **HITL** | No (read-only = no risk) | Yes (writes = needs approval) |
| **Model** | Cheap (Gemini Flash ~$0.01/1K) | Expensive (Claude/GPT-4) |
| **Protocols** | Exploration protocols | Decision protocols |

### 3.2 Why Analysts Exist

| Without Analysts | With Analysts |
|------------------|---------------|
| Specialist does all exploration + decision | Analyst explores cheap, Specialist decides |
| Every image view costs $0.05+ (Claude) | Image view costs ~$0.01 (Gemini Flash) |
| Specialist context bloated with exploration | Specialist gets condensed findings |

**Key Insight:** Analysts exist for **token efficiency** and **separation of concerns**.

### 3.3 Domain Agent Registry

| Domain | Domain-Specific Analysts | Domain-Specific Specialists |
|--------|--------------------------|----------------------------|
| **Catalog** | catalog_analyst | catalog_specialist |
| **Creative** | (uses visual_analyst) | creative_specialist |
| **Operations** | operations_analyst (FUTURE) | operations_specialist (FUTURE) |
| **Marketing** | marketing_analyst (FUTURE) | marketing_specialist (FUTURE) |
| **Quality** | quality_analyst (FUTURE) | quality_specialist (FUTURE) |
| **Procurement** | procurement_analyst (FUTURE) | procurement_specialist (FUTURE) |

---

## 4. Cross-Domain Agents

### 4.1 What Makes an Agent Cross-Domain?

Cross-domain agents provide **capabilities** that serve multiple domains, not domain-specific decisions.

| Agent | Serves Domains | Capability |
|-------|----------------|------------|
| **visual_analyst** | Catalog, Creative, Marketing, Quality, Operations | Visual analysis |
| **product_analyst** | Catalog, Marketing, Procurement | Product research |

### 4.2 The Context Problem

Same agent, different domain context, different focus:

| Domain | visual_analyst Focus | Key Questions |
|--------|---------------------|---------------|
| **Catalog** | Product attributes | Materials? Style? Target customer? |
| **Creative** | Visual quality | Composition? Lighting? Brand fit? |
| **Marketing** | Appeal and positioning | Eye-catching? Message clarity? |
| **Quality** | Defects and issues | Damage? Flaws? Standards met? |
| **Operations** | Condition assessment | Shipping damage? Compliance? |

#### visual_analyst Output: Generic vs Domain-Specific

**WITHOUT Domain Context (Generic - Not Useful):**
```
PM: "Analyze this product image"

visual_analyst output:
"I see a blue cylindrical jar with floral pattern printed on it.
The jar appears to be made of plastic (PET material).
It has a screw-top lid in matching blue color.
Approximate size: 500ml capacity.
The surface has a glossy finish with pink and white flower designs."
```
*Problem: Generic description. Doesn't answer domain-specific questions.*

**WITH Catalog Domain Context:**
```
PM: "Analyze this product image for CATALOG domain"

visual_analyst output:
"MATERIALS: PET plastic, printed surface
STYLE: Decorative (floral print, not plain)
TARGET CUSTOMER: Gift buyers / Home decor enthusiasts
  - Reasoning: Decorative floral pattern elevates beyond utility
  - NOT utility buyers (too ornate for everyday kitchen use)
POSITIONING TIER: DECORATIVE (Rs 50-150 range)
CATALOG NOTES:
  - Should NOT go in 'Plain PET Storage' family (different customer)
  - Look for 'Decorative Kitchen' or 'Gift Storage' families
  - Print quality suggests mid-range pricing within tier"
```
*Result: Directly feeds family_fit protocol. Answers the right questions.*

**WITH Quality Domain Context:**
```
PM: "Analyze this product image for QUALITY domain"

visual_analyst output:
"DEFECTS: None visible
PRINT QUALITY:
  - Alignment: Centered, no skew
  - Color consistency: Even, no fading
  - Registration: Clean edges, no bleeding
SURFACE FINISH:
  - Glossy coating: Uniform, no bubbles or scratches
  - No visible dust particles under coating
LID SEAL: Appears intact, threads visible and clean
COMPLIANCE NOTES:
  - Food-grade marking not visible in image (check physical)
  - No visible BPA-free certification mark
ASSESSMENT: PASS for visual quality check"
```
*Result: Quality-specific assessment. Completely different focus.*

### 4.3 How Cross-Domain Agents Know Context

**Mechanism:** Cross-domain agents load **domain-specific protocols** based on context from PM.

```
PM delegates: "Analyze this product image for CATALOG domain"
       |
       v
visual_analyst loads: catalog/visual_analysis.protocol
       |
       v
Protocol tells agent: Focus on materials, style, target customer
       |
       v
Output: Catalog-relevant visual analysis
```

### 4.4 Cross-Domain Protocol Structure

```
protocols/
+-- catalog/
|   +-- visual_analysis.protocol    # What visual_analyst looks for in Catalog
|   +-- product_research.protocol   # What product_analyst focuses on for Catalog
|
+-- quality/
|   +-- visual_analysis.protocol    # What visual_analyst looks for in Quality
|
+-- marketing/
|   +-- visual_analysis.protocol    # What visual_analyst looks for in Marketing
|
+-- shared/
    +-- visual_analysis_base.protocol  # Common visual analysis patterns
    +-- product_research_base.protocol # Common research patterns
```

---

## 5. Tools and Tool Mastery

### 5.1 Tool Categories

| Category | Tools | Scope |
|----------|-------|-------|
| **Data Engine** | inspect_schema, read_data, write_data, aggregate_data | Cross-domain |
| **Vision** | view_image | Cross-domain |
| **Research** | research_product_tool, extract_web_content | Cross-domain |
| **Platform** | download_media | Cross-domain |
| **Creative** | image_studio | Creative domain |

### 5.2 The Tool Mastery Problem

Same tool, different domain, different usage pattern:

| Domain | read_data Usage | WHY |
|--------|-----------------|-----|
| **Catalog** | `read_data(table="customer_segments", filters={"family_id": X})` | Customer segment is THE deciding factor |
| **Marketing** | `read_data(table="audience_segments", filters={"campaign_id": X})` | Audience fit determines success |
| **Procurement** | `read_data(table="supplier_categories", filters={"supplier_id": X})` | Category alignment determines fit |

### 5.3 Tool Mastery Protocol

```xml
<tool_mastery domain="catalog" tool="read_data">

## KEY TABLES FOR CATALOG DECISIONS
| Decision | Primary Table | Key Filter | Why |
|----------|---------------|------------|-----|
| Family fit | customer_segments | family_id | Customer segment is THE deciding factor |
| Pricing | products | family_id + positioning_tier | Price must fit family range |
| Duplicates | products | name ILIKE, material, volume | Multiple attributes for matching |

## COMMON PATTERNS

### Pattern: Family Fit Query
Execute: read_data(table="customer_segments", filters={"family_id": [id]})
Returns: WHO buys from this family
Use for: Matching product's target customer to family's customer

### Pattern: Price Range Query
Execute: read_data(table="products", filters={"family_id": [id]}, columns=["mrp", "cost_price"])
Returns: Price range for similar products
Use for: Positioning new product within established range

## ANTI-PATTERNS
- Querying by material alone (material != family fit)
- Skipping customer_segments for family decisions
- Using LIMIT 1 when you need range/distribution

</tool_mastery>
```

### 5.4 Which Tools Need Mastery Protocols?

| Tool | Needs Mastery? | Why |
|------|----------------|-----|
| **read_data** | YES | Domain-specific query patterns |
| **aggregate_data** | YES | Domain-specific aggregations |
| **write_data** | YES | Domain-specific validation before write |
| **view_image** | YES | Domain-specific visual analysis focus |
| **research_product_tool** | YES | Domain-specific research focus |
| **inspect_schema** | YES | Domain-specific table priorities and relationship interpretation |
| **download_media** | NO | Generic download; same usage everywhere |
| **extract_web_content** | YES | Domain-specific extraction focus |
| **image_studio** | NO | Domain-specific tool; handled within Creative domain protocols |

---

## 6. Protocol Architecture

### 6.1 Protocol Types

| Type | Purpose | Used By | Example |
|------|---------|---------|---------|
| **Business Context** | Domain orientation, vocabulary, relationships | All domain agents | catalog/business_context |
| **Decision Protocol** | Structured reasoning for specific decisions | Specialists | family_fit, pricing |
| **Exploration Protocol** | What to investigate, what questions to ask | Analysts | catalog_exploration |
| **Tool Mastery** | How to use tools in domain context | All agents | read_data patterns |

### 6.2 Complete Protocol Structure

```
protocols/
+-- catalog/                          # CATALOG DOMAIN
|   +-- business_context.protocol     # Domain orientation
|   +-- family_fit.protocol           # Decision: Product -> Family
|   +-- pricing.protocol              # Decision: Price determination
|   +-- duplicate_prevention.protocol # Decision: Check existing
|   +-- new_family.protocol           # Decision: Create new family
|   +-- visual_analysis.protocol      # For visual_analyst in Catalog context
|   +-- product_research.protocol     # For product_analyst in Catalog context
|   +-- tool_mastery.protocol         # How to use tools in Catalog
|
+-- creative/                         # CREATIVE DOMAIN (FUTURE - Phase 3)
|   +-- business_context.protocol
|   +-- visual_analysis.protocol      # For visual_analyst in Creative context
|   +-- style_consistency.protocol
|   +-- asset_quality.protocol
|
+-- marketing/                        # MARKETING DOMAIN (FUTURE - Phase 3)
|   +-- business_context.protocol
|   +-- visual_analysis.protocol
|   +-- audience_fit.protocol
|
+-- quality/                          # QUALITY DOMAIN (FUTURE - Phase 3)
|   +-- business_context.protocol
|   +-- visual_analysis.protocol      # For visual_analyst in Quality context
|   +-- defect_assessment.protocol
|   +-- compliance_check.protocol
|
+-- operations/                       # OPERATIONS DOMAIN (FUTURE - Phase 3)
|   +-- business_context.protocol
|   +-- visual_analysis.protocol      # For visual_analyst in Operations context
|   +-- condition_assessment.protocol
|
+-- procurement/                      # PROCUREMENT DOMAIN (FUTURE - Phase 3)
|   +-- business_context.protocol
|   +-- product_research.protocol     # For product_analyst in Procurement context
|   +-- supplier_evaluation.protocol
|
+-- shared/                           # CROSS-DOMAIN
    +-- patterns/
    |   +-- fit_assessment.protocol   # Generic: Does X belong with Y?
    |   +-- value_discovery.protocol  # Generic: What should X cost?
    |   +-- new_entity.protocol       # Generic: Should we create Y?
    |   +-- duplicate_prevention.protocol
    |
    +-- tool_mastery/
        +-- data_engine_base.protocol # Common read_data/write_data patterns
        +-- visual_analysis_base.protocol
        +-- research_base.protocol
```

### 6.3 Protocol Loading

```
1. Agent receives task from PM with domain context
2. Agent assesses: "What protocols do I need?"
3. Agent calls load_protocol(["family_fit", "tool_mastery"])
4. Middleware loads: catalog/family_fit.protocol, catalog/tool_mastery.protocol
5. Agent executes with domain-grounded reasoning
```

**Resolution Order:**
1. Domain-specific first: `catalog/family_fit.protocol`
2. Shared fallback: `shared/patterns/fit_assessment.protocol`

---

## 7. PM Role with Protocols

### 7.1 What PM Needs (NOT Full Protocols)

PM uses **lightweight coordination** rather than domain decision protocols.

| PM Need | Type | Purpose |
|---------|------|---------|
| **Domain Awareness** | Knowledge | Know which domains own which decisions |
| **Context Schema** | Template | What to pass to each domain |
| **Coordination Patterns** | Patterns | Multi-domain workflow orchestration |
| **Escalation Protocol** | Reference | Use Section 8 framework + escalate to user when ambiguous |

### 7.2 Domain Awareness

```xml
<domain_awareness>
| Domain | Owns | Does NOT Own |
|--------|------|--------------|
| Catalog | Product data, families, pricing | Image generation, marketing content |
| Creative | Image processing, visual assets | Product data, pricing |
| Operations | Fulfillment workflows, condition assessment | Product creation, pricing |
| Marketing | Campaigns, positioning | Product data, image processing |
| Quality | Defect assessment, standards compliance | Product creation, marketing |
| Procurement | Supplier evaluation, sourcing | Product creation, quality assessment |
</domain_awareness>
```

### 7.3 Context Schema Per Domain

```xml
<context_schema domain="catalog">
## REQUIRED
- image_path (if visual product)
- user_intent (what they want to accomplish)

## OPTIONAL (if available from analysts)
- visual_analysis_summary
- product_research_summary
- existing_catalog_matches

## FORMAT
Pass as structured context, not instructions.
Let specialist decide HOW to accomplish the goal.
</context_schema>
```

### 7.4 Multi-Domain Coordination Patterns

```xml
<coordination_pattern name="product_with_marketing_assets">
## SCENARIO
User wants product cataloged with marketing images

## FLOW
1. Catalog domain: Create/find product (returns product_id)
2. Creative domain: Generate assets (needs product_id, product_context)
3. Catalog domain: Link assets to product (needs asset_ids)

## DEPENDENCIES
- Step 2 REQUIRES output from Step 1
- Step 3 REQUIRES output from Step 2
- Run sequentially, not parallel
</coordination_pattern>
```

### 7.5 Design Decision: Why PM Uses Coordination, Not Decision Protocols

**The Question:** Does PM need full protocols like specialists?

**Option A: PM Has Full Routing Protocols**
```
PM loads: routing_protocol.protocol
Protocol says: "For cataloging tasks, delegate to catalog_analyst then catalog_specialist"
```
- Pro: Consistent routing
- Con: Becomes RIGID WORKFLOW TEMPLATES (we killed this in AUTONOMY_PROBLEMS)
- Con: PM stops reasoning, just follows recipe
- **REJECTED**

**Option B: PM Has No Protocols At All**
```
PM receives task -> Reasons from scratch -> Delegates
```
- Pro: Maximum flexibility
- Con: PM doesn't understand domain boundaries
- Con: May route incorrectly (original problem!)
- **REJECTED**

**Option C: PM Has Lightweight Coordination (SELECTED)**
```
PM has:
- Domain Awareness (knowledge of what each domain owns)
- Context Schemas (what to pass to each domain)
- Coordination Patterns (how to orchestrate multi-domain)
- Escalation Protocol (edge case handling)

PM does NOT have:
- Routing protocols (uses reasoning)
- Domain decision protocols (delegates to specialists)
```
- Pro: PM understands boundaries without rigid templates
- Pro: Maintains dynamic reasoning (AUTONOMY_PROBLEMS fix preserved)
- Pro: Specialists own domain decisions
- **SELECTED**

**Key Insight:** PM's job is COORDINATION, not DOMAIN DECISIONS. PM needs to know domain boundaries to route correctly, but shouldn't make domain-specific decisions itself.

### 7.6 PM Does NOT Have

- Routing protocols (uses dynamic reasoning)
- Domain decision protocols (that's for specialists)
- Fixed workflow templates (killed in AUTONOMY_PROBLEMS)

**Future PM Intelligence:** Reference resolution, intent inference, user state tracking, correction flow. See [PM_INTELLIGENCE_ROADMAP.md](./PM_INTELLIGENCE_ROADMAP.md).

---

## 8. Escalation Framework

### 8.1 Escalation Triggers

| Scenario | Trigger | Escalate To | Action |
|----------|---------|-------------|--------|
| **PARTIAL result** | Protocol completes but ambiguous | HITL | Present options to user |
| **Missing data** | Required query returns empty | Cold Start | Use fallback then HITL |
| **Tool failure** | API error, timeout | Retry then PM | Retry 3x with backoff |
| **Quality not met** | N iterations without success | PM + HITL | Flag for human review |
| **Cross-domain conflict** | Domain A says X, Domain B says Y | PM | Use Conflict Resolution Protocol |
| **Compound failure** | Multiple failure conditions | Highest handler | HITL > PM > Retry priority |

### 8.2 Iteration Bounds

| Protocol Type | Max Iterations | After Max |
|---------------|----------------|-----------|
| Family fit search | 3 families | Trigger new_family |
| Pricing discovery | 2 tier searches | Flag for manual pricing |
| Duplicate check | 1 (deterministic) | Proceed or merge |
| Image generation | 3 iterations | Escalate to user |
| Research queries | 5 queries | Report best findings |

### 8.3 Escalation Flow

```
PROTOCOL EXECUTION
       |
       v
   +--------+
   | RESULT |
   +--------+
       |
  +----+----+----+----+
  |    |    |    |    |
MATCH PARTIAL EMPTY ERROR
  |    |    |    |
  v    v    v    v
DONE  HITL COLD  RETRY(3)
           START    |
             |      v
             v   ESCALATE
           HITL   TO PM
```

### 8.4 Conflict Resolution Protocol

When domains produce conflicting recommendations, PM resolves using this protocol:

```xml
<conflict_resolution>

## DETECTION
- Two or more domains return contradictory recommendations
- Example: Marketing says "price at Rs 50 for positioning" vs Catalog says "family pricing demands Rs 100"

## RESOLUTION STEPS

### Step 1: IDENTIFY Conflict Type
| Type | Example | Resolution Owner |
|------|---------|------------------|
| Data conflict | Different facts from different sources | Query authoritative source |
| Priority conflict | Both valid, different business priorities | Domain ownership matrix |
| Interpretation conflict | Same data, different conclusions | Owning domain decides |

### Step 2: APPLY Domain Ownership
- Check Domain Ownership Matrix (Section 2.3)
- Owning domain's recommendation takes precedence
- Non-owning domain's input becomes "consideration" not "decision"

### Step 3: SYNTHESIZE for User
If ownership unclear OR stakes high:
- Present both perspectives via HITL
- Include: Domain A recommendation + reasoning, Domain B recommendation + reasoning
- Let user decide

## CRITICAL RULES
- NEVER silently pick one domain over another
- ALWAYS document which domain "won" and why
- High-stakes conflicts (pricing, family creation) ALWAYS go to HITL

</conflict_resolution>
```

### 8.5 Compound Failure Handling

When multiple failure conditions occur simultaneously:

```xml
<compound_failure_handling>

## PRIORITY ORDER (Highest to Lowest)
1. HITL - Any condition requiring human judgment
2. PM Escalation - Cross-domain or architectural decisions
3. Cold Start - Missing foundational data
4. Retry - Transient failures

## RESOLUTION
- Identify ALL active failure conditions
- Escalate to HIGHEST priority handler
- Handler addresses all conditions, not just its primary concern
- Example: Tool failure + Cold start = Cold start handler (includes retry logic)

## NEVER
- Handle failures independently (creates inconsistent state)
- Retry if HITL condition also present (human judgment first)

</compound_failure_handling>
```

---

## 9. Cold Start Handling

### 9.1 Cold Start Scenarios

| Scenario | Example | Detection |
|----------|---------|-----------|
| **First product** | Empty catalog | products count = 0 |
| **No matching family** | Product doesn't fit | family search returns no MATCH |
| **No pricing data** | First in tier | price range query empty |
| **New category** | Novel product type | no similar products found |

### 9.2 Cold Start Protocol

```xml
<cold_start_handling>

## DETECTION
- Query returns empty
- No similar entities found
- First-of-kind indicator

## RESPONSE STEPS
1. Acknowledge cold start situation in reasoning
2. Broaden search criteria (adjacent categories, similar attributes)
3. Fall back to external data (market research, industry standards)
4. Present findings WITH uncertainty flags
5. ALWAYS escalate to HITL for cold start decisions

## CRITICAL
- NEVER auto-approve cold start decisions
- NEVER use defaults without flagging uncertainty
- ALWAYS flag first-of-kind for human review

</cold_start_handling>
```

### 9.3 Bootstrap Phase

The Bootstrap Phase defines when a domain transitions from LEARNING mode to AUTONOMOUS mode.

```xml
<bootstrap_phase>

## DEFINITION
Bootstrap Phase = Period when domain lacks sufficient data for autonomous decisions.
During bootstrap, ALL decisions require HITL approval to establish foundational patterns.

## BOOTSTRAP THRESHOLDS (Per Domain)

| Domain | Bootstrap Ends When | Rationale |
|--------|---------------------|-----------|
| **Catalog** | 3+ product families with 5+ products each | Enough pattern diversity |
| **Creative** | 10+ approved image generations | Style preferences established |
| **Marketing** | 5+ approved campaigns | Positioning patterns learned |
| **Quality** | 20+ quality assessments reviewed | Standards calibrated |
| **Procurement** | 5+ supplier evaluations | Evaluation criteria validated |

## BOOTSTRAP MODE BEHAVIOR

### During Bootstrap (LEARNING)
- ALL domain decisions require HITL approval
- System explicitly flags: "Bootstrap mode: Building foundational patterns"
- Each approval trains the system on user preferences
- No autonomous execution, even for "obvious" decisions

### After Bootstrap (AUTONOMOUS)
- Standard escalation rules apply (Section 8)
- HITL only for ambiguous/high-stakes decisions
- Cold start protocol only for genuinely new categories
- System operates with learned patterns

## BOOTSTRAP TRACKING
- Track per-domain: decisions_made, decisions_approved, approval_rate
- Transition requires: threshold met AND approval_rate > 80%
- If approval_rate < 80% at threshold, extend bootstrap by 50%

## CRITICAL
- Bootstrap thresholds are MINIMUMS, not guarantees
- User can extend bootstrap manually ("stay in learning mode")
- New business = ALL domains in bootstrap simultaneously
- Bootstrap reset if business rules change significantly

</bootstrap_phase>
```

---

## 10. Tool Grounding: Why Protocols Work

### 10.1 The Core Mechanism

Protocols work because they force **TOOL CALLS** that ground reasoning in real data.

```
Without protocols:
Agent sees example --> Copies output --> Hallucinates plausible data

With protocols:
Agent sees steps --> Executes read_data() --> Gets REAL data --> Reasons about ACTUAL results
```

**The agent can't fake query results.** When Step 2 says "Execute read_data(...)", the tool returns actual database records.

### 10.2 The Grounding Boundary

| Step Type | Grounded? | Example |
|-----------|-----------|---------|
| QUERY | YES | read_data returns real records |
| AGGREGATE | YES | Statistics are factual |
| ANALYZE | NO | "This looks decorative" is inference |
| COMPARE | PARTIAL | Data grounded, interpretation not |

### 10.3 Mitigation for Ungrounded Steps

- **Structured criteria** - Define what "decorative" means
- **Comparison to grounded data** - Compare inference to queried facts
- **HITL checkpoint** - Visual-heavy decisions get human review

---

## 11. Catalog Domain: Complete Protocol Set

### 11.1 Business Context Protocol

```xml
<business_context domain="catalog">

## POSITIONING TIERS
| Tier | Price Range | Target Customer | Product Style |
|------|-------------|-----------------|---------------|
| UTILITY | Rs 0-50 | Functional buyers | Plain, everyday use |
| DECORATIVE | Rs 50-150 | Gift buyers | Designed, display-worthy |
| PREMIUM | Rs 150+ | Luxury seekers | Artisan, exclusive |

## KEY RELATIONSHIPS
- product_families -> customer_segments (WHO buys)
- products -> product_families (WHERE it belongs)
- customer_segments DETERMINES family fit (not material, not price)

## COMMON MISCONCEPTIONS
| Wrong | Right |
|-------|-------|
| Same material = same family | Same customer journey = same family |
| Price determines tier | Tier determines price RANGE |
| Visual similarity = family match | Customer segment = family match |

## BUSINESS RULES
1. Customer Segment is PRIMARY - Family assignment is about WHO BUYS
2. Price Follows Positioning - Don't set price first, find family first
3. Explore Before Concluding - Always query, never assume

</business_context>
```

### 11.2 Family Fit Protocol

```xml
<protocol name="Family Fit" domain="catalog" type="decision">

## PURPOSE
Ground the decision: Does this product belong in this family?

## PREREQUISITE
Visual analysis must be complete (Step 4 depends on visual analysis findings).
If visual analysis not available, delegate to visual_analyst first.

## EXPLORATION STEPS

### Step 1: IDENTIFY - Candidate Family
Document: family_id, family_name
Source: User input, search result, or PM context

### Step 2: QUERY - Customer Segment
Execute: read_data(table="customer_segments", filters={"family_id": [id]})
Why: customer_segments is THE deciding factor. NOT material. NOT price.

### Step 3: QUERY - Family's Current Products
Execute: read_data(table="products", filters={"family_id": [id]}, limit=10)
Why: See what products already belong - establishes the pattern.

### Step 4: ANALYZE - Product's Target Customer
Based on visual analysis + product attributes:
- Utility/everyday use? -> UTILITY customer
- Decorative/display? -> DECORATIVE customer
- Gift-worthy? -> GIFT customer
- Premium/luxury? -> PREMIUM customer

### Step 5: COMPARE - Customer Match
| Result | Condition | Next Action |
|--------|-----------|-------------|
| MATCH | Product customer = Family customer | Proceed to OUTPUT |
| PARTIAL | Overlapping but distinct | HITL with options |
| MISMATCH | Different customer type | Search other families |

### Step 6: CONCLUDE
- MATCH: Product FITS this family -> Proceed with assignment
- PARTIAL: Present options via HITL -> User decides
- MISMATCH: Needs DIFFERENT family -> Search or new_family protocol

## VERIFICATION
- [ ] Step 2 query executed (not assumed)
- [ ] Customer segment explicitly identified
- [ ] Conclusion references step results

## ANTI-PATTERNS
- Concluding based on material match alone
- Skipping customer segment query
- Using general retail knowledge instead of queried data

## ITERATION BOUNDS
- Max 3 candidate families before triggering new_family
- If PARTIAL on all 3, present all options via HITL

</protocol>
```

### 11.3 Pricing Protocol

```xml
<protocol name="Pricing" domain="catalog" type="decision">

## PURPOSE
Ground the decision: What should this product cost?

## PREREQUISITE
Family assignment must be complete (pricing follows family)

## EXPLORATION STEPS

### Step 1: IDENTIFY - Product Tier
From family assignment:
- Family's customer segment -> Tier
- UTILITY/DECORATIVE/PREMIUM

### Step 2: QUERY - Family Price Range
Execute: read_data(table="products", filters={"family_id": [id]}, columns=["mrp", "cost_price"])

### Step 3: AGGREGATE - Price Statistics
Execute: aggregate_data(table="products", filters={"family_id": [id]}, aggregations={"min": "mrp", "max": "mrp", "avg": "mrp"})

### Step 4: POSITION - Within Range
Based on product attributes within the family:
- More features/quality -> Higher in range
- Basic variant -> Lower in range
- Unique attributes -> Justify premium

### Step 5: CONCLUDE
| Scenario | Action |
|----------|--------|
| Price within family range | Proceed |
| Price above family max | Flag for review - might need different family |
| Price below family min | Flag for review - might be loss leader |
| Cold start (no family data) | Use tier defaults + market research |

## TIER DEFAULTS (Cold Start Only)
| Tier | Default Range | Use When |
|------|---------------|----------|
| UTILITY | Rs 25-50 | No family price data |
| DECORATIVE | Rs 75-125 | No family price data |
| PREMIUM | Rs 175-250 | No family price data |

</protocol>
```

### 11.4 Duplicate Prevention Protocol

```xml
<protocol name="Duplicate Prevention" domain="catalog" type="decision">

## PURPOSE
Ground the decision: Does this product already exist?

## WHEN TO USE
BEFORE any product creation. Non-negotiable.

## EXPLORATION STEPS

### Step 1: QUERY - Exact Name Match
Execute: read_data(table="products", filters={"name": {"ilike": "%[product_name]%"}})

### Step 2: QUERY - Attribute Match
Execute: read_data(table="products", filters={
  "material": [material],
  "volume_ml": [volume],
  "product_type": [type]
})

### Step 3: ANALYZE - Results
| Result | Condition | Action |
|--------|-----------|--------|
| Exact match | Same name, same attributes | DO NOT CREATE - return existing |
| Near match | Similar but different variant | Confirm with user via HITL |
| No match | Nothing similar found | Proceed with creation |

## CRITICAL
- Run BEFORE write_data, not after
- Err on side of caution - flag near matches
- Include existing product_id in HITL if near match

</protocol>
```

### 11.5 New Family Protocol

```xml
<protocol name="New Family" domain="catalog" type="decision">

## PURPOSE
Ground the decision: Should we create a new product family?

## TRIGGER
- family_fit protocol returned MISMATCH on 3+ candidates
- User explicitly requests new family
- Product represents genuinely new category

## EXPLORATION STEPS

### Step 1: VERIFY - No Existing Fit
Confirm: family_fit attempted on at least 3 candidates
Document: Why each was MISMATCH

### Step 2: IDENTIFY - New Family Attributes
Define:
- Customer segment (WHO will buy)
- Positioning tier (UTILITY/DECORATIVE/PREMIUM)
- Distinguishing characteristics

### Step 3: QUERY - Similar Families
Execute: read_data(table="product_families", filters={"positioning_tier": [tier]})
Ensure: Not duplicating existing family concept

### Step 4: PROPOSE - New Family Definition
Structure:
- family_name: Descriptive, follows naming convention
- customer_segment: Clear target customer
- positioning_tier: Based on customer segment
- description: What products belong here

## HITL REQUIRED
New family creation ALWAYS requires HITL approval.
Present: Proposed family + reasoning + what products would fit

</protocol>
```

### 11.6 Catalog Visual Analysis Protocol

```xml
<protocol name="Visual Analysis" domain="catalog" type="exploration">

## PURPOSE
Guide visual_analyst when analyzing images FOR CATALOG DOMAIN.

## FOCUS AREAS (Catalog-Specific)
| Area | Questions | Why It Matters |
|------|-----------|----------------|
| **Materials** | Plastic/glass/metal/wood/ceramic? | Affects family grouping |
| **Style** | Plain/printed/textured/artisan? | Indicates target customer |
| **Target Customer** | Utility buyer? Gift buyer? Luxury seeker? | Determines family fit |
| **Positioning** | Everyday? Decorative? Premium? | Maps to tier |
| **Quality Indicators** | Finish quality? Design sophistication? | Supports pricing |

## OUTPUT STRUCTURE
```
MATERIALS: [identified materials]
STYLE: [plain/printed/textured/artisan]
TARGET CUSTOMER: [utility/gift/luxury] - [reasoning]
POSITIONING TIER: [UTILITY/DECORATIVE/PREMIUM]
CATALOG NOTES: [anything relevant to family fit or pricing]
```

## NOT IN SCOPE (For Catalog Context)
- Defect detection (that's Quality domain)
- Marketing appeal (that's Marketing domain)
- Shipping condition (that's Operations domain)

</protocol>
```

### 11.7 Catalog Tool Mastery Protocol

```xml
<tool_mastery domain="catalog">

## read_data PATTERNS

### Family Fit Query
```
read_data(table="customer_segments", filters={"family_id": [id]})
```
Returns: Customer segment for the family
Use: Determining if product matches family's customer

### Price Range Query
```
read_data(table="products", filters={"family_id": [id]}, columns=["mrp", "cost_price", "name"])
```
Returns: Products in family with prices
Use: Establishing price range for new product

### Duplicate Check Query
```
read_data(table="products", filters={"name": {"ilike": "%term%"}})
```
Returns: Products with similar names
Use: Preventing duplicate creation

## aggregate_data PATTERNS

### Price Statistics
```
aggregate_data(table="products", filters={"family_id": [id]}, aggregations={"min": "mrp", "max": "mrp", "avg": "mrp"})
```
Returns: Price min/max/avg for family
Use: Positioning new product in price range

### Product Count
```
aggregate_data(table="products", filters={"family_id": [id]}, aggregations={"count": "id"})
```
Returns: Number of products in family
Use: Understanding family size

## inspect_schema PATTERNS

### Schema Discovery for Catalog
```
inspect_schema(table="customer_segments")
```
Priority tables: customer_segments, product_families, products
Key relationships: customer_segments.family_id -> product_families.id

### When to Use
- Cold start: Unknown table structure
- New feature: Verify column exists before query
- Debugging: Query returning unexpected results

## COMMON MISTAKES
| Mistake | Why Wrong | Correct Approach |
|---------|-----------|------------------|
| Query by material for family fit | Material != family | Query customer_segments |
| Skip duplicate check | Creates data quality issues | ALWAYS check before create |
| Use LIMIT 1 for price range | Misses distribution | Query multiple, then aggregate |
| Assume schema | Schema may have changed | inspect_schema when uncertain |

</tool_mastery>
```

---

## 12. Implementation

### 12.1 Implementation Approach

**[CRITICAL] FRESH BUILD - NOT PATCHWORK**

Phase 1 is a complete rebuild from first principles, not patches on existing agents:

| Component | Approach |
|-----------|----------|
| **PM** | Rebuild with domain awareness, coordination patterns, conflict resolution |
| **Analysts** | Build fresh with protocol-driven exploration |
| **Specialists** | Rebuild with protocol-driven decisions |
| **Protocols** | New structure from scratch |
| **Middleware** | New ProtocolInjectionMiddleware |

**Rationale:** Existing agents were built before the Domain Reasoning Framework. Patchwork creates architectural debt. Clean slate ensures framework principles are foundational, not bolted-on.

**Existing code:** Reference for patterns learned, but implementation is unconstrained by it.

### 12.2 Phase Overview

| Phase | Focus | Status |
|-------|-------|--------|
| **Phase 1** | Foundation + Catalog (PM, Analysts, Specialist, Protocols) | READY |
| **Phase 2** | Cross-Domain Protocols | PENDING |
| **Phase 3** | Additional Domains | FUTURE |

### 12.3 Phase 1: Foundation + Catalog (Fresh Build)

**Build Order:** PM -> Analysts -> Specialist -> Protocols -> Middleware

#### Stage 1: PM (Domain-Aware Orchestrator)
- [ ] PM prompt with domain awareness
- [ ] Domain ownership knowledge
- [ ] Coordination patterns (single-domain, multi-domain)
- [ ] Conflict resolution protocol integration
- [ ] Bootstrap phase awareness

#### Stage 2: Analysts (Protocol-Driven Exploration)
- [ ] visual_analyst - cross-domain visual analysis
- [ ] catalog_analyst - catalog-specific exploration
- [ ] Protocol loading mechanism for domain context

#### Stage 3: Catalog Specialist (Protocol-Driven Decisions)
- [ ] catalog_specialist with protocol integration
- [ ] HITL checkpoints for decisions
- [ ] Bootstrap mode behavior

#### Stage 4: Protocol Infrastructure
- [ ] Protocol file structure (`protocols/catalog/`, `protocols/shared/`)
- [ ] `create_load_protocol_tool()` factory
- [ ] `ProtocolInjectionMiddleware`
- [ ] Catalog protocols:
  - [ ] business_context.protocol
  - [ ] family_fit.protocol
  - [ ] pricing.protocol
  - [ ] duplicate_prevention.protocol
  - [ ] new_family.protocol
  - [ ] visual_analysis.protocol
  - [ ] tool_mastery.protocol

#### Stage 5: Validation
- [ ] Before/after trace comparison
- [ ] Bootstrap phase verification
- [ ] Conflict resolution testing

### 12.4 Phase 2: Cross-Domain

- [ ] Visual analysis protocols for other domains (Quality, Marketing)
- [ ] Product research protocols for other domains (Marketing, Procurement)
- [ ] Shared pattern protocols (fit_assessment, value_discovery)
- [ ] Tool mastery base protocols

---

## 13. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-12-16 | Unified Tool + Middleware | All agents use same pattern |
| 2025-12-16 | Agent-driven selection | Pure autonomy; agents decide when to load |
| 2025-12-17 | Protocols organized by domain | Domains contain analysts + specialists |
| 2025-12-17 | Cross-domain agents load domain-specific protocols | Same agent, different context |
| 2025-12-17 | Tool mastery protocols | Same tool, different domain usage |
| 2025-12-17 | PM uses coordination patterns, not decision protocols | PM coordinates, doesn't decide domain matters |
| 2025-12-17 | Explicit iteration bounds | Prevent infinite loops |
| 2025-12-17 | Cold start always escalates to HITL | First-of-kind needs human judgment |
| 2025-12-17 | Conflict Resolution Protocol added | Multi-domain conflicts need explicit resolution mechanism |
| 2025-12-17 | Bootstrap Phase defined | Explicit transition from LEARNING to AUTONOMOUS mode |
| 2025-12-17 | Compound Failure Handling added | Multiple failures escalate to highest priority handler |
| 2025-12-17 | Fresh build approach | Rebuild from scratch, not patchwork on existing agents |

---

## 14. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Family assignment accuracy | 90%+ | HITL approval rate |
| Pricing acceptance | 85%+ | HITL approval rate |
| Duplicate prevention | 99%+ | Zero duplicates created |
| Token efficiency | Analysts < Specialists | Cost per task type |
| Protocol adherence | 100% | Trace analysis |

**Verification:** Use `workflow-evaluation` skill for trace analysis.

---

## 15. Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Protocol attention dilution | High | Token budget, load only when needed |
| Cross-domain context confusion | High | Explicit domain context in delegation |
| Agent skips protocols | High | Trace monitoring, prompt strengthening |
| Cold start mishandling | High | Always HITL, never auto-approve |
| Tool mastery drift | Medium | Regular protocol review |
| Escalation loops | Medium | Clear escalation bounds |

---

## References

- [ARCHITECTURAL_VISION.md](../ARCHITECTURAL_VISION.md) - North star vision
- [AGENTS_DESIGN.md](./AGENTS_DESIGN.md) - 2-Level architecture
- [AUTONOMY_PROBLEMS.md](../AUTONOMY_PROBLEMS.md) - Autonomy fixes
- [DOMAIN_DESIGN_GUIDELINES.md](./DOMAIN_DESIGN_GUIDELINES.md) - Domain design
- [PM_INTELLIGENCE_ROADMAP.md](./PM_INTELLIGENCE_ROADMAP.md) - Future PM capabilities

---

**Version:** 6.0 (ULTRATHINK - Fresh Build Ready)
**Updated:** December 17, 2025
