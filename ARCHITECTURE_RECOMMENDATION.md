# Architecture Recommendation: Based on PM Vision

**Date:** October 29, 2025
**Context:** Post-Phase 2C review, before Phase 3
**Based on:** SPECIALIST_BUILD_UP_PLAN.md + CLAUDE.md design philosophy

---

## PM VISION SUMMARY (From Specialist Doc)

### Core Paradigm: **Intelligent PM, Not Dumb Orchestrator**

**PM Role:**
- ✅ Analyzes images to understand what user sent
- ✅ Has domain knowledge (B2B vs B2C, packaging, products)
- ✅ Knows company context (brand, capabilities, catalog)
- ✅ Asks clarifying questions (intelligent discussion)
- ✅ Plans strategically based on understanding
- ✅ **ENRICHES data before delegating to specialists**

**Specialist Role:**
- ✅ Receive ENRICHED, well-understood input from PM
- ✅ Focus on **SPECIALIZED analysis** (not basic understanding)
- ✅ Return expert analysis to PM

**Key Quote from Vision:**
> "Modern LLMs Are Capable - Don't Restrict Them"
> "If an LLM with full context can figure it out, don't hardcode the logic"

**Workflow:**
```
PM understands → discusses → enriches → delegates
NOT just: routes → delegates
```

---

## DESIGN PRINCIPLES EXTRACTED

From CLAUDE.md and Specialist Doc:

### 1. Intelligence-First Design
> "Trust intelligence over control. Give agents problems + rich context, not step-by-step recipes"
> "Don't restrict LLMs - they have 200K+ context, strong reasoning, multimodal capabilities"

### 2. Context Enables Autonomy
> "Rich, well-structured context beats rigid orchestration"
> "PM enriches data, specialists receive RICH input for DEEP analysis"

### 3. Minimal Scaffolding
> "Avoid over-engineering; let agents reason about goals and adapt dynamically"
> "If an LLM with full context can figure it out, don't hardcode the logic"

### 4. Domain-Centric Specialists
> "Build reusable domain specialists, not workflow-specific agents"
> "Specialists are DEEP domain experts, not basic understanding processors"

---

## BLOAT CLEANUP: ALIGNED WITH VISION

### ✅ REMOVE: `get_product_schema` from PM

**Vision Check:**
- PM is intelligent orchestrator, not technical analyst
- PM enriches business context (product type, target market, pricing)
- PM doesn't need table schemas - that's specialist's technical domain
- Specialist queries schema for deep analysis

**Action:** REMOVE (bloat confirmed)

---

### ✅ DEFER: `save_campaign` from PM

**Vision Check:**
- PM has persistence tools (HITL pattern correct)
- But no campaign specialists exist yet
- Adding tools before specialists violates "incremental build-up"

**Action:** DEFER until campaign specialists built

---

### ✅ FIX: Base Context Formatting

**Current:**
```python
# Formatted as text in prompt
catalog_summary_text = f"""
**Your Catalog Summary (Loaded at Startup):**
- Total Product Families: {base_context.catalog_summary.total_families}
...
"""

# Also in state as structured data
initial_state = {
    "base_context": base_context.model_dump(),  # Duplicate
}
```

**Vision Check:**
- Context feeding strategy: Base context at startup (correct)
- But duplication = bloat
- LLM can read from state directly

**Action:** Keep structured data in state only, remove text formatting

---

### ✅ REMOVE: Unused status tracking

**Current:**
```python
"status": "product_architecture_and_taxonomy_integrated"  # Implementation detail
```

**Vision Check:**
- PM doesn't use this status
- Leaks implementation details
- Not part of PM's operational model

**Action:** REMOVE unused fields

---

## TAXONOMY DECISION: MERGE INTO PRODUCT ARCHITECTURE

### Analysis Against Vision

**Question:** Should taxonomy be separate specialist or merged?

**Vision Framework:**

1. **"Don't restrict LLMs"**
   - Product Architecture Specialist already has FULL product context
   - Material, use cases, target industries, applications
   - LLM with this context CAN classify intelligently

2. **"Specialists receive ENRICHED input for SPECIALIZED analysis"**
   - Is taxonomy a SPECIALIZED domain requiring deep expertise?
   - NO - it's database lookups (categories, NAICS codes) + mapping
   - YES - product structure is SPECIALIZED (schema-driven, variant math, SKU patterns)

3. **"Rich context beats rigid orchestration"**
   - Separate specialist = PM must coordinate two specialists
   - Merged = specialist has COMPLETE context for better classification

4. **"Schema-driven architecture"**
   - We just built universal CRUD with OperationIntent
   - Classification = more operations in execution plan
   - NOT a separate concern, just additional tables

### The Case for MERGING

**Product Architecture Specialist already:**
- Analyzes product deeply (material, use cases, target markets)
- Understands B2B vs B2C
- Knows target industries from enriched PM input
- Has schema-driven OperationIntent (can add ANY table operations)
- Returns complete execution plan

**Adding classification means:**
- Add 3 tools to specialist:
  - `find_google_product_category` (rule-based mapping)
  - `find_relevant_categories` (DB lookup)
  - `classify_into_industries` (NAICS matching)

- OperationIntent includes classification operations:
```python
operations = [
    # Product structure
    Operation(op_type="insert", table="product_families", ...),
    Operation(op_type="insert", table="variant_axes", ...),
    Operation(op_type="insert", table="products", ...),
    # Classification (NEW)
    Operation(op_type="insert", table="product_family_categories", ...),
    Operation(op_type="insert", table="product_family_industries", ...),
]
```

**Benefits:**
1. ✅ **Intelligence-first:** Specialist has full context for smarter classification
2. ✅ **Simpler PM:** One delegation call, not two
3. ✅ **Single HITL:** User approves complete product setup (structure + classification)
4. ✅ **Schema-driven:** Fits the architecture we just built
5. ✅ **Better classification:** Specialist knows materials, applications, use cases deeply

**Trade-offs:**
- ⚠️ Specialist prompt gets larger (but we can manage it)
- ⚠️ Can't run classification in parallel (but classification is fast - just DB lookups)

---

## RECOMMENDATION: ULTRATHINK APPROACH

### Phase 3 Revised: Enhance Product Architecture Specialist

**Instead of:** Adding separate Taxonomy Specialist

**Do:** Add classification capabilities to Product Architecture Specialist

### Implementation:

**1. Add Classification Tools to Specialist:**
```python
def create_product_architecture_specialist(storage):
    tools = [
        # Existing
        get_product_schema,
        get_table_schema,
        list_available_tables,
        search_product_families,
        image_analysis_tool,
        # ADD: Classification
        find_google_product_category,
        find_relevant_categories,
        classify_into_industries,
    ]
```

**2. Update Specialist Prompt:**
- Add classification responsibilities
- Add examples of OperationIntent with classification operations
- Keep prompt focused (remove Phase 3 separate specialist bloat)

**3. OperationIntent includes classification:**
- Specialist generates operations for all tables
- PM presents complete product setup
- Single HITL approval

**4. PM stays simple:**
- No orchestration complexity
- Delegates once → gets complete setup
- Presents to user → executes

---

## COMPARISON

### Option A: Separate Taxonomy Specialist (Original Plan)

**Workflow:**
```
PM enriches
  ↓
PM delegates to Product Architecture (structure)
  ↓
PM delegates to Taxonomy (classification)  ← Parallel or sequential?
  ↓
PM coordinates results
  ↓
PM presents to user (2 separate outputs?)
  ↓
User approves
  ↓
PM executes (2 separate tools?)
```

**Complexity:** Medium-High
**Alignment with vision:** Partial (over-orchestration)

---

### Option B: Merged Classification (Recommended)

**Workflow:**
```
PM enriches
  ↓
PM delegates to Product Architecture (structure + classification)
  ↓
Specialist analyzes with FULL context
  ↓
Returns complete OperationIntent (structure + classification)
  ↓
PM presents to user (single unified output)
  ↓
User approves
  ↓
PM executes (single universal tool)
```

**Complexity:** Low
**Alignment with vision:** FULL ✅

---

## FINAL RECOMMENDATION

### Execute This Plan:

**Phase 1: Cleanup (30 minutes)**
1. Remove `get_product_schema` from PM
2. Remove `save_campaign` from PM (defer)
3. Remove base context text formatting
4. Remove unused status fields
5. Update PM prompt (remove outdated limitations)

**Phase 2: Enhance Product Architecture Specialist (2-3 hours)**
1. Add 3 classification tools to specialist
2. Update specialist prompt with classification guidance
3. Add examples showing OperationIntent with classification operations
4. Test: specialist returns structure + classification in single OperationIntent

**Phase 3: Skip Separate Taxonomy Specialist**
- Don't add taxonomy_specialist to PM
- Mark Phase 3 as "merged into Phase 2"
- Update specialist doc

**Phase 4: Future Specialists**
- Phase 4: Market Intelligence (pricing, segmentation)
- Phase 5: Content Generation (marketing copy)
- Phase 6: Image Processing (quality, dimensions)

---

## QUESTIONS FOR USER

Before executing:

1. **Agree with merging taxonomy into Product Architecture Specialist?**
   - Aligns with "intelligence-first" and "don't restrict LLMs"
   - Simpler orchestration
   - Better classification with full context

2. **Execute cleanup + merge plan above?**

3. **Any concerns about specialist prompt size?**
   - Will grow from 913 lines → ~1100 lines
   - But still manageable, focused on single domain (product setup)

**Ready to execute if you approve.**

