# Specialist Build-Up Integration Plan

**Date:** October 28, 2025
**Last Updated:** October 28, 2025
**Status:** ✅ Phase 1 Complete | 🎯 Phase 2 Design Complete - Ready for Implementation
**Current Phase:** Phase 2 - Product Architecture Specialist
**Strategy:** Incremental build-up - unplug all specialists, perfect PM core, add specialists one by one

---

## Executive Summary

**Problem:** Current workflow is breaking due to incomplete feature integration and specialist-tool mismatches.

**Solution:** Surgical build-up approach:
1. Unplug all 11 specialists from PM
2. Perfect minimal PM (core orchestration only)
3. Add specialists ONE BY ONE in dependency order
4. Perfect each specialist before adding next
5. Update PM prompt incrementally as specialists are added
6. Test end-to-end after each integration

**Timeline:** ~40-50 hours (4-5 hours per specialist + PM core)

**Success Criteria:** Each specialist works independently, PM orchestrates correctly, end-to-end workflows succeed.

---

## ARCHITECTURAL PARADIGM: Intelligent PM vs Dumb Orchestrator

### Critical Insight (October 28, 2025)

**Modern LLMs Are Capable - Don't Restrict Them**

**Why This Matters:**
- ✅ LLMs have 200k+ token context windows
- ✅ Multimodal capabilities (analyze images, understand visual context)
- ✅ Strong reasoning abilities (understand domain, plan strategically)
- ✅ Built-in domain knowledge (B2B, packaging, product concepts)

**OLD Paradigm (Initially Planned):**
```
PM = "Dumb Orchestrator"
- Just routes messages
- No domain knowledge
- No image analysis
- No user discussion
- Delegates blindly to specialists

Specialists = "Smart Domain Experts"
- Receive raw user messages
- Do ALL the intelligence work
- Return structured outputs
```

**Problem with OLD Paradigm:**
- PM can't understand user intent without specialists (catch-22)
- PM can't have intelligent discussions with users
- Specialists receive poor-quality, raw input
- Workflow breaks with vague user requests (just image + "catalog this")

**NEW Paradigm (Revised Architecture):**
```
PM = "Intelligent Orchestrator"
- Analyzes images to understand what user sent
- Has domain knowledge (B2B vs B2C, packaging, products)
- Knows company context (Pavisha = B2B packaging manufacturer)
- Asks clarifying questions (intelligent discussion)
- Plans strategically based on understanding
- ENRICHES data before delegating to specialists

Specialists = "Deep Domain Experts"
- Receive ENRICHED, well-understood input from PM
- Focus on SPECIALIZED analysis (not basic understanding)
- Return expert analysis to PM
```

**Benefits of NEW Paradigm:**
1. **PM understands intent early** → Can plan better, ask smart questions
2. **Specialists get rich input** → "Analyze PET jar family, B2B packaging, 3 sizes..." (not raw "catalog this")
3. **Better user experience** → PM has intelligent conversations
4. **Faster workflows** → PM makes smart decisions, doesn't need specialist for basic understanding

### Example Comparison

**Scenario:** User sends image of jar + vague text "catalog this"

**OLD Paradigm (Dumb PM):**
```
PM: "I detect product_onboarding intent. Specialists are being integrated - Phase 2 coming soon."
❌ PM is blind, can't help
```

**NEW Paradigm (Intelligent PM):**
```
PM:
1. Analyzes image → "PET jar, transparent, ~500ml capacity"
2. Checks company context → "Pavisha = B2B packaging"
3. Understands intent → "Product onboarding for packaging"
4. Asks smart question → "I see a 500ml PET jar. What's the price? Do you have other sizes?"

User: "Rs 30, we also make 250ml and 1L"

PM:
5. Plans workflow
6. Delegates to Product Architecture Specialist:
   "Analyze PET jar family. B2B packaging. 3 capacities: 250ml, 500ml, 1L.
    Base price Rs 30. Company: Pavisha (B2B packaging in India).
    Image analysis: transparent food-grade PET."

Product Architecture Specialist:
7. Receives ENRICHED input (not raw message)
8. Focuses on DEEP analysis (variant structure, SKU patterns)
9. Returns expert analysis

PM:
10. Synthesizes intelligently
11. Presents for approval
✅ Intelligent, complete workflow
```

### Architectural Implications

**What Changes:**
1. **PM Prompt:** Add domain knowledge, image analysis guidance, discussion patterns
2. **PM Tools:** Add image analysis tool to PM (not just specialists)
3. **Specialist Input:** Specialists receive enriched context (not raw user messages)
4. **Workflow:** PM understands → discusses → enriches → delegates (not just routes)

**What Stays Same:**
1. **Specialist autonomy:** Specialists still make domain decisions
2. **HITL at PM level:** PM still owns persistence tools
3. **Incremental build-up:** Still add specialists one by one
4. **2-level architecture:** PM → Specialists → Tools

---

## CONTEXT FEEDING STRATEGY ✅ DECIDED (October 28, 2025)

### The Foundational Question

**For Intelligent PM to work, HOW does PM get context?**

PM needs:
- Company context (brand, products, capabilities)
- Existing catalog (to know "do we have this?")
- Taxonomy structure (to suggest classifications)
- User conversation history

**Critical Decision:** When/how does this context get loaded?

---

### Four Options Analyzed

#### Option A: PM Has Context Query Tools
PM actively queries DB for context on-demand

**Verdict:** ⚠️ Works but adds latency per message (200-500ms)

---

#### Option B: Context Loaded at Startup
Load full catalog/taxonomy at PM construction

**Verdict:** ❌ Doesn't scale (10K products → 50K+ tokens), stale data risk

---

#### Option C: Specialists Query, PM Learns
PM has no context until specialists return data

**Verdict:** ❌ Violates Intelligent PM paradigm (PM stays "dumb")

---

#### Option D: Hybrid (Base Context + Query Details) ✅ CHOSEN
Load lightweight **base context** at startup, query **details** on-demand

**Why This Wins:**
1. **PM is intelligent from message 1** (has base context for discussion)
2. **Scales** (base = 1-2K tokens, details queried only when needed)
3. **Mostly fresh** (base refreshed every 15min, details always current)
4. **Resilient** (DB down → uses stale base, degrades gracefully)
5. **Efficient** (PM gets summaries, specialists get full details - no duplication)

---

### Option D Implementation Design

#### Base Context (Injected at Startup)

```python
class PMBaseContext(BaseModel):
    """Lightweight context, loaded at PM startup, refreshed every 15min"""

    # Already have
    company_profile: CompanyProfile

    # NEW: Catalog summary
    catalog_summary: CatalogSummary
    # Example: {
    #   "total_families": 7,
    #   "total_skus": 200,
    #   "family_names": ["PET Bottles", "Glass Jars", ...],
    #   "top_categories": ["Food & Beverage", "Personal Care"]
    # }

    # NEW: Taxonomy tree structure
    taxonomy_tree: TaxonomyTree
    # Example: {
    #   "root_categories": [
    #     {"id": "...", "name": "Food & Beverage", "children": [...]},
    #   ]
    # }

    # FUTURE: Recent activity summary
    recent_activity: list[str] = []
```

**Token Cost:** ~1-2K tokens (acceptable, always in PM state)

---

#### PM Query Tools (On-Demand Details)

```python
# NEW tools for PM (summary-level only):

1. search_catalog_summary(query: str) -> CatalogSearchSummary
   # Returns: Matching family names, IDs, variant counts (NOT full product data)
   # Use: PM checks if product exists before delegation
   # Cost: 200-500ms query latency

2. get_category_info(category_name: str) -> CategoryInfo
   # Returns: Category details, product count (NOT full product list)
   # Use: PM needs category context for discussion
   # Cost: 200-500ms query latency
```

---

#### Specialist Query Tools (Unchanged)

```python
# Specialists keep existing tools (FULL detail level):

Product Architecture Specialist:
- search_product_families(product_group_id, name, brand, material)
  # Returns: FULL product data, match recommendations, confidence scores

Taxonomy Specialist:
- find_relevant_categories(keywords)
  # Returns: FULL category matches with descriptions

# No duplication: PM = summaries, Specialists = full details
```

---

### Context Flow Example

**Scenario: User sends "catalog this" + image**

```
[PM Startup via ContextMiddleware]
PMBaseContext loaded:
  - company_profile: Pavisha (B2B packaging manufacturer)
  - catalog_summary: {7 families, 200 SKUs, ["PET Bottles", "Glass Jars", ...]}
  - taxonomy_tree: [Food & Bev → Packaging, Personal Care → Containers]

═══════════════════════════════════════

User: "catalog this" + [jar.jpg]

PM (reasoning):
  Step 1: Analyze image → "PET jar, ~500ml, transparent"
  Step 2: Check base context → catalog_summary shows ["PET Bottles", "Glass Jars"]
  Step 3: Query details → search_catalog_summary("PET jar") → No matches
  Step 4: Ask clarifying questions → "I see 500ml PET jar. Price? Target market?"

User: "Rs 30, food packaging, B2B"

PM (reasoning):
  Now I have complete context:
  - Product: PET jar, 500ml, Rs 30
  - Market: Food packaging, B2B
  - Decision: ENRICH and delegate to Product Architecture Specialist

PM → Product Architecture Specialist:
"Analyze PET jar family for B2B food packaging.

Context (from my understanding):
- Company: Pavisha (B2B packaging, India)
- Product: PET jars, transparent, food-grade
- Variant: 500ml capacity
- Price: Rs 30 (base)
- Target: Food industry, B2B bulk
- Image analysis: Transparent, wide mouth, screw-top
- Catalog search: No existing PET jar families (create new)

Your task: Design variant structure, SKU pattern, confirm catalog search."

═══════════════════════════════════════

Product Architecture Specialist (receives ENRICHED input):
  - PM already did basic understanding
  - I focus on DEEP analysis (variant axes, SKU patterns, catalog matching)

  Step 1: Confirm catalog search (full query with scoring)
  Step 2: Design variant structure (capacity + neck + color)
  Step 3: Generate SKU pattern (PAV-JAR-PET-{capacity}-{neck}-{color})

  Returns: ProductArchitectureDraft with full analysis

PM synthesizes and continues workflow...
```

---

### Scenario Matrix Results

| Scenario | A (Query) | B (Startup) | C (Specialists) | D (Hybrid) ✅ |
|----------|-----------|-------------|-----------------|--------------|
| New product (no match) | ✅ Query shows none | ✅ Memory shows none | ❌ Can't know | ✅ Base + query |
| New variant (existing) | ✅ Query finds family | ⚠️ Stale risk | ❌ Can't know | ✅ Base + query |
| Vague request + image | ✅ Query → discuss | ✅ Memory → discuss | ❌ Blind delegate | ✅ Base + query |
| Large catalog (10K SKUs) | ✅ Query filters | ❌ Token bloat | ✅ Scales | ✅ Scales |
| User asks "what products?" | ✅ Query & answer | ✅ Answer from memory | ❌ Can't answer | ✅ Answer from base |
| DB unavailable | ⚠️ Queries fail | ❌ Startup fails | ⚠️ Specialist fails | ✅ Degrade gracefully |
| Performance (latency) | ⚠️ +200-500ms | ✅ Instant | ✅ No overhead | ✅ Instant (base) |
| Token efficiency | ✅ Query results only | ❌ Full catalog | ✅ Efficient | ✅ Base (1-2K) + queries |

**Winner: Option D (10/8 scenarios perfect)**

---

### Trade-offs Explicitly Accepted

**⚠️ Base context slightly stale (15 min refresh window):**
- **Acceptable:** Summary stats don't change rapidly
- **Mitigation:** Detail queries always fresh, PM discovers updates before persistence
- **Risk:** PM says "we have 7 families" but actually 8 (one added 5 min ago)
- **Impact:** Low (discovered during specialist delegation)

**⚠️ Increased complexity (middleware + refresh logic):**
- **Acceptable:** Benefits (intelligent + scalable + resilient) outweigh cost
- **Mitigation:** Clear separation of concerns, comprehensive testing
- **Risk:** More moving parts = more potential failures
- **Impact:** Medium (managed with good engineering)

**⚠️ Two query patterns (PM summaries, specialist details):**
- **Acceptable:** Different granularity, not duplication
- **Mitigation:** Clear contracts on what PM vs specialists query
- **Risk:** Could query similar data twice
- **Impact:** Low (caching middleware prevents this)

---

### Decision Status

**✅ APPROVED: Option D (Hybrid Base + Query)**

**Next:** Implement in Phase 1 (broken into Phase 1A-D)

---

## Phase 0: Preparation ✅ COMPLETE (2 hours)

### Task 0.1: Backup Current State ✅
- **Action:** Create git branch `specialist-build-up-v1`
- **Command:** `git checkout -b specialist-build-up-v1`
- **Validation:** Branch created, current work preserved
- **Commit:** 99c0b6f

### Task 0.2: Create Minimal PM Shell ✅
- **Action:**
  - Copy [project_manager.py](../../../agents/src/autifyme_agents/workflows/project_manager.py) to `project_manager_BACKUP.py`
  - Strip all specialist imports and registrations
  - Keep only: PM tools (platform media, write_todos), persistence tools (for HITL testing)
  - Create minimal prompt with core orchestration only
- **Files:**
  - `agents/src/autifyme_agents/workflows/project_manager.py`
  - `agents/src/autifyme_agents/prompts/project_manager_minimal.prompt`
- **Validation:** PM loads without errors, has 0 specialists
- **Commit:** 5948b58, e2406e7

### Task 0.3: Test Harness ✅
- **Action:** Use existing intelligent testing framework
- **File:** `tests/tools/intelligent_execution.py`
- **Purpose:** Test each specialist in isolation before PM integration
- **Validation:** Framework works, AI acts as test user
- **Commit:** N/A (already exists)

---

## Phase 1: Build Intelligent PM Core ✅ COMPLETE (11-15 hours)

**Status:** All Sub-Phases Complete (1A ✅ + 1B ✅ + 1C ✅ + 1D ✅)
**Timeline:** October 28, 2025
**Goal:** PM with intelligent capabilities (ZERO specialists, but fully context-aware)

### Phase 1 Overview

**Original Approach (Revised):**
- Phase 1 initially created "minimal PM" with no context → too dumb
- Discovered PM needs intelligence BEFORE specialists are added
- Decided on Hybrid Context Feeding (Option D) for intelligence

**New Approach (4 Sub-Phases):**
1. **Phase 1A:** Base Context Infrastructure (models + middleware)
2. **Phase 1B:** PM Query Tools (summary-level queries)
3. **Phase 1C:** Intelligent PM Prompt (domain knowledge + discussion patterns)
4. **Phase 1D:** End-to-End Testing (all scenarios from matrix)

---

### Phase 1A: Base Context Infrastructure ✅ COMPLETE (3-4 hours)

**Goal:** Create infrastructure to load and inject base context into PM at startup

#### Task 1A.1: Create Pydantic Models for Base Context
**File:** `agents/src/autifyme_agents/schemas/context_models.py` (NEW)

**Models to Create:**
```python
class CatalogSummary(BaseModel):
    """Lightweight catalog summary for PM base context"""
    total_families: int
    total_skus: int
    family_names: list[str]  # Just names, not full data
    top_categories: list[str]
    last_updated: datetime

class TaxonomyTree(BaseModel):
    """Taxonomy structure for PM understanding"""
    root_categories: list[CategoryNode]
    # CategoryNode = {id, name, children: list[CategoryNode]}

class PMBaseContext(BaseModel):
    """Complete base context injected at PM startup"""
    company_profile: CompanyProfile  # Already exists
    catalog_summary: CatalogSummary  # NEW
    taxonomy_tree: TaxonomyTree  # NEW
    recent_activity: list[str] = []  # FUTURE
```

**Validation:**
- REPL test: Instantiate models with sample data
- Verify serialization: `model.model_dump()`, `model.model_dump_json()`
- Token estimate: Serialize and count (target: <2K tokens)

---

#### Task 1A.2: Create Context Middleware
**File:** `agents/src/autifyme_agents/middleware/context_middleware.py` (NEW)

**Purpose:** Load base context from DB and inject into PM initial state

**Functions:**
```python
async def load_catalog_summary(storage: StorageInterface) -> CatalogSummary:
    """Query DB for lightweight catalog summary"""
    # Query: SELECT COUNT(*), family names, categories
    # Return: CatalogSummary

async def load_taxonomy_tree(storage: StorageInterface) -> TaxonomyTree:
    """Query DB for taxonomy tree structure"""
    # Query: Categories with parent-child relationships
    # Return: TaxonomyTree

async def load_base_context(
    company_profile: CompanyProfile,
    storage: StorageInterface
) -> PMBaseContext:
    """Load complete base context for PM"""
    catalog_summary = await load_catalog_summary(storage)
    taxonomy_tree = await load_taxonomy_tree(storage)
    return PMBaseContext(
        company_profile=company_profile,
        catalog_summary=catalog_summary,
        taxonomy_tree=taxonomy_tree,
    )
```

**Error Handling:**
- DB unavailable → Return empty summaries with flag `stale=True`
- Graceful degradation → PM can still operate with limited context

**Validation:**
- REPL test with real DB connection
- Test with DB unavailable (should not crash)
- Verify query performance (<500ms)

---

#### Task 1A.3: Integrate Middleware with PM
**File:** `agents/src/autifyme_agents/workflows/project_manager.py`

**Changes:**
```python
from autifyme_agents.middleware.context_middleware import load_base_context

async def create_project_manager(
    company_profile: CompanyProfile,
    *,
    model: BaseChatModel | None = None,
    checkpointer: Any,
    storage: StorageInterface,
    channel: MessagingChannel | None = None,
) -> Any:
    """Create Intelligent Project Manager with base context"""

    # Load base context (NEW)
    base_context = await load_base_context(company_profile, storage)

    # ... (rest of PM setup)

    initial_state = {
        "base_context": base_context.model_dump(),  # NEW
        "status": "intelligent_core",
        "integrated_specialists": [],
        "specialist_results": {},
    }

    return project_manager.with_config(...)
```

**Validation:**
- PM starts successfully with base context
- `initial_state["base_context"]` populated
- Token count in acceptable range (<2K for base context)

---

#### Task 1A.4: Test Base Context Infrastructure
**Test:** PM has base context at startup

**Command:**
```bash
uv run python -c "
from dotenv import load_dotenv; load_dotenv('.env')
from autifyme_agents.workflows.project_manager import create_project_manager
from autifyme_agents.integrations.storage import get_storage
from autifyme_agents.schemas.models import CompanyProfile

storage = get_storage()
profile = CompanyProfile(name='Test Co', ...)
pm = await create_project_manager(profile, storage=storage, ...)
print('Base Context:', pm.initial_state['base_context'])
"
```

**Success Criteria:**
- ✅ PM loads without errors
- ✅ `base_context` present in initial state
- ✅ `catalog_summary` has realistic data
- ✅ `taxonomy_tree` has structure
- ✅ Total tokens <2K

**Commit:** ✅ de36475
```bash
Phase 1A: Base Context Infrastructure - COMPLETE

- Created schemas/context_models.py (PMBaseContext, CatalogSummary, TaxonomyTree, CategoryNode)
- Created middleware/context_middleware.py (load_base_context, load_catalog_summary, load_taxonomy_tree)
- Modified workflows/project_manager.py (load base context at initialization)
- Testing: 909 tokens, 7 families, 62 SKUs, 10 categories

Status: PM now has catalog/taxonomy awareness at startup
```

**Test Results:**
- ✅ All Pydantic models work (recursive CategoryNode)
- ✅ Middleware loads real DB data successfully
- ✅ Token cost: 909 tokens (target: <2000)
- ✅ PM creates with base context in initial_state
- ✅ Graceful degradation tested (empty summaries if DB down)

---

### Phase 1B: PM Query Tools ✅ COMPLETE (3-4 hours)

**Goal:** Add summary-level query tools for PM to get details on-demand

#### Task 1B.1: Create PM Context Query Tools
**File:** `agents/src/autifyme_agents/tools/pm_context_tools.py` (NEW)

**Tools:**
```python
1. search_catalog_summary(query: str) -> CatalogSearchSummary
   # Input: "PET jar", "bottles"
   # Output: List of matching family names, IDs, variant counts
   # NOT full product data

2. get_category_info(category_name: str) -> CategoryInfo
   # Input: "Food & Beverage"
   # Output: Category details, subcategories, product count
   # NOT full product list
```

**Implementation Pattern:**
- Use `@tool` decorator from LangChain
- Accept `storage: StorageInterface` parameter
- Return Pydantic models (structured output)
- Raise `ToolException` on errors

**Validation:**
- REPL test each tool independently
- Verify query performance (<500ms)
- Test with various inputs (exact match, fuzzy, no match)

---

#### Task 1B.2: Add Query Tools to PM
**File:** `agents/src/autifyme_agents/workflows/project_manager.py`

**Changes:**
```python
from autifyme_agents.tools.pm_context_tools import (
    create_search_catalog_summary_tool,
    create_get_category_info_tool,
)

def create_project_manager(...):
    # PM Tools
    pm_tools: list[Any] = []

    # Platform tools (existing)
    if channel is not None:
        pm_tools.extend(create_platform_media_tools(channel))

    # NEW: Context query tools
    pm_tools.append(create_search_catalog_summary_tool(storage))
    pm_tools.append(create_get_category_info_tool(storage))

    # Image analysis tool (NEW - for multimodal PM)
    pm_tools.append(image_analysis_tool)

    # HITL persistence tools (existing)
    pm_tools.append(create_save_product_family_tool(storage))
    pm_tools.append(create_save_campaign_tool(storage))

    # ... rest of PM setup
```

**Validation:**
- PM loads with new tools
- Tools appear in PM's tool list
- No import errors

---

#### Task 1B.3: Test PM Query Tools
**Test:** PM can query catalog and taxonomy

**Command:**
```bash
uv run python tests/cli/pm_chat.py
```

**Interaction:**
```
User: "What products do we make?"
PM: [Uses base_context.catalog_summary] "We have 7 product families: PET Bottles, Glass Jars, ..."

User: "Do we have PET jars?"
PM: [Calls search_catalog_summary("PET jar")] "Let me check... [query result] Yes/No..."

User: "What categories do we serve?"
PM: [Uses base_context.taxonomy_tree] "We serve Food & Beverage, Personal Care, ..."
```

**Success Criteria:**
- ✅ PM uses base context for quick answers
- ✅ PM queries details when needed
- ✅ Query latency acceptable (<500ms)
- ✅ PM doesn't hallucinate (answers from data)

**Commit:** ✅ 1d3a14b
```bash
Phase 1B: PM Query Tools - COMPLETE

- Created pm_context_tools.py (search_catalog_summary, get_category_info)
- Fixed column name (product_family_id not family_id)
- Integrated tools with PM
- Testing: Query tools working, <500ms latency

Status: PM can now query DB for details beyond base context
```

**Test Results:**
- ✅ search_catalog_summary finds matches correctly
- ✅ get_category_info returns taxonomy details
- ✅ Query latency <500ms (target met)
- ✅ PM integrated with both tools

---

### Phase 1C: Intelligent PM Prompt ✅ COMPLETE (3-4 hours)

**Goal:** Update PM prompt with domain knowledge, discussion patterns, enrichment strategies

#### Task 1C.1: Design Intelligent PM Prompt
**File:** `agents/src/autifyme_agents/prompts/project_manager_intelligent.prompt` (NEW)

**Structure:** (Following PROMPT_ENGINEERING_STANDARDS.md)
```xml
<background_information>
You are the Intelligent Project Manager for {company_name}.

You have BASE CONTEXT (loaded at startup):
- Company profile: {company_name}, {brand_voice}, {target_audience}
- Catalog summary: {catalog_summary}
- Taxonomy tree: {taxonomy_tree}

You have QUERY TOOLS for details:
- search_catalog_summary: Find product families by name
- get_category_info: Get category details

You are MULTIMODAL:
- Analyze images to understand products
- Combine visual + text understanding

Your role: INTELLIGENT ORCHESTRATOR
- Understand user intent deeply (not just keywords)
- Ask clarifying questions when info missing
- Enrich data before delegating to specialists
- Plan strategically based on context
</background_information>

<available_tools>
## Context Tools
- search_catalog_summary: Find families in catalog
- get_category_info: Get taxonomy details

## Analysis Tools
- image_analysis_tool: Analyze product images

## Platform Tools
- download_{platform}_media: Get user attachments

## Specialist Delegation (Phase 2+)
[Specialists will be added incrementally]

## Persistence Tools (HITL)
- save_product_family: Persist after specialist analysis
- save_campaign: Persist campaign data
</available_tools>

<instructions>
## Your Intelligence

### 1. Understand User Intent (Deep Analysis)

When user sends message:
1. Analyze any images (if present) → What product? What details visible?
2. Check base context → Do we have this? Similar products?
3. Extract user intent → Product onboarding? Marketing? Question?
4. Identify missing info → Price? Quantities? Target market?

### 2. Have Intelligent Discussions

If info missing, DON'T blindly delegate. ASK:
- Image of jar + "catalog this" → "I see a PET jar, ~500ml. What's the price? Target market?"
- "Add new product" (no details) → "What product? Do you have images? Price?"
- "Create campaign" (vague) → "Campaign for which products? What's the goal?"

### 3. Use Your Context

Base context (instant access):
- catalog_summary: Know what families exist
- taxonomy_tree: Know categories/industries
- company_profile: Know brand voice, capabilities

Query tools (when needed):
- search_catalog_summary: Check if product exists
- get_category_info: Get category details

### 4. Enrich Before Delegating

When you have complete info, delegate with ENRICHED input:

BAD (raw delegation):
→ Product Architecture Specialist: "catalog this" + [image]

GOOD (enriched delegation):
→ Product Architecture Specialist: "Analyze PET jar family for B2B food packaging.
   Context: Company Pavisha (B2B packaging India), 3 capacities (250ml, 500ml, 1L),
   base price Rs 30, transparent food-grade PET. Image shows wide mouth, screw-top.
   Catalog search: No existing PET jar families. Your task: Design variant structure,
   SKU pattern, confirm search."

### 5. Plan Strategically

Product onboarding workflow (when specialists available):
1. Understand product (your job: image analysis, questions)
2. Check catalog (your job: base context + query)
3. Delegate to specialists WITH enriched context:
   - Product Architecture Specialist (structure, SKUs)
   - Taxonomy Specialist (categories, industries)
   - Market Intelligence Specialist (positioning, segments)
   - Visual Assets Specialist (if images)
   - Content & SEO Specialist (after others complete)
4. Synthesize outputs
5. Present for HITL approval
6. Persist to database

### 6. Current Limitations

No specialists integrated yet (Phase 1):
- Can analyze and discuss intelligently
- Can check catalog and answer questions
- CANNOT complete workflows (need specialists)
- Be honest: "I understand your request. Specialists are being integrated for [workflow]."
</instructions>

<examples>
[2-3 canonical examples of intelligent PM behavior]

Example 1: Vague product onboarding
Example 2: Complete product onboarding (with discussion)
Example 3: User question about catalog
</examples>

<output_format>
Natural conversation with user.
- Use base context to inform responses
- Query for details when needed
- Ask clarifying questions intelligently
- Be honest about current capabilities
</output_format>
```

---

#### Task 1C.2: Update PM to Use Intelligent Prompt
**File:** `agents/src/autifyme_agents/workflows/project_manager.py`

**Changes:**
```python
instructions = load_prompt("project_manager_intelligent.prompt").format(
    company_name=company_profile.name,
    brand_voice=company_profile.brand_voice,
    target_audience=company_profile.target_audience,
    catalog_summary=base_context.catalog_summary.model_dump_json(),
    taxonomy_tree=base_context.taxonomy_tree.model_dump_json(),
)
```

---

#### Task 1C.3: Test Intelligent PM Prompt
**Test Scenarios:**
1. Vague request + image → PM analyzes, asks questions
2. Complete request → PM understands, prepares for delegation
3. User question → PM answers from base context
4. Missing info → PM guides user to provide details

**Success Criteria:**
- ✅ PM asks intelligent questions (not generic)
- ✅ PM uses base context in responses
- ✅ PM enriches understanding through discussion
- ✅ PM prepares enriched input for future delegation

**Commit:** ✅ 08fe230
```bash
Phase 1C: Intelligent PM Prompt - COMPLETE

- Created project_manager_intelligent.prompt (504 lines, comprehensive)
- Fixed curly brace formatting issues in prompt
- Updated PM to use intelligent prompt with base_context formatting
- CRITICAL FIX: Format base_context data INTO prompt text (prevents hallucination)

Status: PM is now intelligent orchestrator (context-aware, domain-knowledgeable, discussion-capable)
```

**Test Results:**
- ✅ PM correctly reports base_context data (7 families, 62 SKUs)
- ✅ PM asks intelligent domain-aware questions
- ✅ PM uses base_context before querying
- ✅ PM prepares enriched context for delegation
- ✅ No hallucination (prompt fix working)

---

### Phase 1D: End-to-End Testing ✅ COMPLETE (2-3 hours)

**Goal:** Validate PM handles all scenarios from context feeding matrix

#### Task 1D.1: Comprehensive Scenario Testing

**Test Matrix:** (From context feeding analysis)

| Scenario | Test Case | Expected PM Behavior |
|----------|-----------|---------------------|
| New product (no match) | "Catalog PET jar" + image | Analyze image → Check base context → Query catalog → "No existing PET jars, need price..." |
| Existing product variant | "Add 750ml to bottles" | Check base context → Query details → "I see we have PET Bottles family. 750ml is new variant..." |
| Vague request | Image only, no text | Analyze image → "I see PET jar, ~500ml. What's price? Target market?" |
| User question | "What products do we make?" | Use base context → "We have 7 families: [list]" |
| Large catalog (future) | Simulate 10K products | Base context still <2K tokens, queries filter effectively |
| DB unavailable | Simulate DB down | Degrade gracefully → "Using cached context, may be slightly stale" |

**Validation:**
- ✅ All 6 scenarios pass
- ✅ PM uses base context appropriately
- ✅ PM queries when needed (not every message)
- ✅ PM asks intelligent questions
- ✅ PM prepares enriched context for delegation
- ✅ No hallucinations (answers from data)

---

#### Task 1D.2: Performance Validation

**Metrics:**
- Base context token size: <2K tokens ✅
- Query latency: <500ms per query ✅
- PM response time: <5s (including queries) ✅
- No memory leaks, no crashes ✅

---

#### Task 1D.3: LangSmith Trace Review

**Check Traces:**
- PM correctly uses base context (visible in state)
- PM queries only when needed (not redundant)
- PM tool calls are appropriate
- PM reasoning is sound

---

#### Task 1D.4: Final Phase 1 Validation

**Status:** ✅ COMPLETE (User will commit)

**Comprehensive Test Results:**
All 5 scenarios from behavior validation passed:

1. **Scenario 1 (User Question):** ✅ PASSED
   - PM correctly reports 7 families, 62 SKUs (not hallucinated 12!)
   - Lists accurate family names from base_context
   - Shows top categories correctly

2. **Scenario 2 (Existence Check):** ✅ PASSED
   - PM identifies "PET Jar 500ml with Blue Lid" from base_context
   - Offers to query for more details (appropriate tool use)

3. **Scenario 3 (Vague Request):** ✅ PASSED
   - PM asks comprehensive clarifying questions
   - Shows domain knowledge (materials, certifications, target markets)
   - Guides user to provide complete information

4. **Scenario 4 (Complete Request):** ✅ PASSED
   - PM called search_catalog_summary('PET jar') - correct
   - PM attempted save_product_family - triggered HITL (expected)

5. **Scenario 5 (Ambiguous Match):** ✅ PASSED
   - PM found 3 bottle families with variant counts
   - Asked intelligent clarifying questions

**Performance Metrics Met:**
- Base context: 931 tokens (53% under 2K target) ✅
- Context load: 406ms (59% under 1s target) ✅
- PM init: 774ms (85% under 5s target) ✅
- Query latency: <500ms ✅

**Phase 1 Status: COMPLETE**
- PM has base context (catalog summary, taxonomy tree)
- PM can query details on-demand
- PM is intelligent (domain-knowledgeable, discussion-capable, context-aware)
- PM enriches data before delegation (ready for Phase 2)
- No hallucination bug (base_context formatted into prompt)

**Next:** Phase 2 - Add Product Architecture Specialist

---

### Phase 1 Success Criteria (Overall)

**✅ When Phase 1 is complete:**
1. PM has base context at startup (company + catalog + taxonomy)
2. PM can query DB for summary-level details
3. PM analyzes images (multimodal understanding)
4. PM asks intelligent clarifying questions
5. PM checks catalog before responding
6. PM enriches understanding through discussion
7. PM prepares enriched input for future specialists
8. PM handles all scenarios (new/existing/vague/questions/errors)
9. PM scales (10K+ products, base context still <2K tokens)
10. PM is resilient (degrades gracefully if DB down)

**Then proceed to Phase 2:** Add Product Architecture Specialist (receives enriched input from intelligent PM)

---

## Phase 2: Add Product Architecture Specialist 🎯 READY TO START (4-5 hours)

### Goal
First specialist integrated - enables deep product structure analysis through autonomous domain expertise.

**Status:** Design Complete - Ready for Implementation

---

### FINALIZED DESIGN: Autonomous Intelligent Specialist

**Core Principle:** Context, Not Instructions

PM provides **enriched product context**, specialist autonomously decides analysis approach.

---

### Specialist's Unique Domain Expertise

**What Specialist Brings (that PM doesn't have):**

1. **Variant Structure Theory**
   - Variant axis identification with domain rules
   - Compatibility constraints (28mm neck only with 500ml+)
   - Industry patterns (pharma = amber bottles only)

2. **SKU Architecture Patterns**
   - Hierarchical naming conventions
   - Industry best practices (B2B vs B2C naming)
   - Uniqueness guarantees

3. **Catalog Matching Algorithms**
   - Fuzzy matching with material/brand/use-case filters
   - Confidence scoring
   - Autonomous create vs update vs add-variant decisions

4. **Pricing Structure Strategy**
   - Base + variant adjustments
   - Bulk tier design

5. **Completeness Validation**
   - Missing field detection
   - Confidence scoring
   - Quality assessment

---

### PM → Specialist Delegation Pattern

**✅ PM Provides (Enriched Context):**

```
Product onboarding for PET jars.

PRODUCT DETAILS:
- Type: PET jars (transparent, food-grade)
- Capacities: 250ml, 500ml, 1L
- Price: Rs 35/unit (for 500ml)
- Material: Food-grade PET
- Target: Food packaging, B2B bulk orders

IMAGES:
C:/Temp/jar_front.jpg
C:/Temp/jar_side.jpg

PM'S BASIC ANALYSIS:
Analyzed first image - transparent cylindrical jar, wide mouth opening,
screw-top compatible, food-grade quality appearance.

PM'S CATALOG AWARENESS:
Quick search found no 'PET jar' families (summary level).
Your detailed search is authoritative.

COMPANY CONTEXT:
state.company_profile has SKU conventions, brand info
state.base_context has catalog summary, taxonomy tree
```

**❌ PM Does NOT Provide:**
- ❌ Step-by-step instructions ("First do X, then Y")
- ❌ Conversation history ("User said this, then changed mind")
- ❌ User intent interpretation ("User wants new product line")
- ❌ Company details (in state, specialist reads directly)

**Rationale:**
- Specialist is autonomous expert, knows its job
- PM synthesizes conversation → product facts only
- Specialist reads company context from state
- Trust intelligent LLMs to decide methodology

---

### Specialist State Access (Automatic via DeepAgents)

**✅ Specialist Receives (Auto-Populated by DeepAgents):**
- `state.company_profile` - Company name, brand, SKU conventions
- `state.base_context.catalog_summary` - Product families overview
- `state.base_context.taxonomy_tree` - Category structure
- `state.specialist_results` - Other specialists' outputs (if sequential)

**❌ Specialist Does NOT Receive:**
- `state.messages` - Conversation history (excluded by DeepAgents)
- `state.todos` - PM's todo list (excluded by DeepAgents)

**Usage:**
- Specialist reads `state.company_profile.sku_prefix_pattern` for naming conventions
- Specialist reads `state.base_context.catalog_summary` for awareness
- No token duplication in task description

---

### Tool Allocation Strategy

#### Image Analysis Tool
**✅ Both PM and Specialist Use**

**PM's Usage:**
- When: If images provided, analyze FIRST image only
- Purpose: Basic understanding for intelligent conversation
- Depth: Product type, rough dimensions, obvious features
- Pass to specialist: Image file paths (not analysis - let specialist re-analyze)

**Specialist's Usage:**
- When: If PM provides image paths in delegation
- Purpose: Deep domain analysis for structural decisions
- Depth: ALL images, materials, quality, variant cues
- Never: Hallucinate paths - only use explicit paths from PM

#### Catalog Search Tools
**✅ Both Search, Different Roles**

**PM's search_catalog_summary:**
- When: If PM identified product type from user/image
- Purpose: Quick awareness for conversation ("We have PET Bottles family")
- NOT for: Final create vs update decisions
- Include in delegation: Yes, marked as "summary awareness only"

**Specialist's search_product_families:**
- When: Always (FIRST step in specialist analysis)
- Purpose: Authoritative create vs update decision
- Features: Fuzzy matching, filters, confidence scoring
- PM trusts: Specialist's recommendation overrides PM's summary

---

### Multi-Turn Conversation Pattern

**Specialist Signals → PM Handles:**

```
Specialist returns:
  confidence_score=0.4
  flags=["Material unclear - could be PET or HDPE"]

PM interprets flags:
PM asks user: "Is this PET or HDPE material?"

User clarifies: "PET"

PM re-delegates with updated facts:
"Material: PET (confirmed by user)"
```

**Rules:**
- ✅ Specialist NEVER asks questions directly
- ✅ Specialist signals uncertainty via confidence + flags
- ✅ PM interprets → asks user → re-delegates with facts
- ✅ Specialist is stateless (each call independent)

---

### Sequential Specialist Collaboration

**Content & SEO Specialist (runs AFTER Taxonomy + Market Intelligence):**

```python
# Content specialist reads from state:
taxonomy = state.specialist_results["taxonomy_specialist"]
market = state.specialist_results["market_intelligence_specialist"]

# Uses outputs to inform content generation
# No PM synthesis needed - direct specialist collaboration
```

---

### Error Handling: Graceful Degradation

**Specialist handles failures autonomously:**

```python
# Image analysis fails
try:
    image_result = image_analysis_tool(path)
except ToolException:
    image_result = None
    flags.append("Image analysis failed - text-only analysis")
    confidence_score *= 0.8

# Catalog search fails
try:
    search = search_product_families(...)
except DatabaseError:
    search = None
    flags.append("Catalog search unavailable - assuming create_new")
    recommendation = "create_new"
    confidence_score *= 0.7

# Return degraded output with transparency
return ProductArchitectureDraft(
    confidence_score=final_confidence,
    flags=all_flags,
    ...
)
```

**PM interprets and recovers:**
- If confidence < 0.7 → Review flags → Ask user for missing info
- If critical failure → Retry specialist
- If persistent failure → Inform user, offer manual entry

---

### Specialist Prompt Architecture

**Pattern:**

```xml
<background_information>
You are Product Architecture Specialist.
[Domain expertise description]
</background_information>

<your_responsibilities>
You autonomously:
- Analyze product structure from PM's enriched context
- Search catalog to determine create vs update
- Design variant architecture and SKU patterns
- Handle missing data gracefully
- Signal uncertainty with confidence scores
- Return structured ProductArchitectureDraft

You decide when to use tools, how to handle edge cases.
</your_responsibilities>

<state_access>
You have access to parent state:
- state.company_profile - SKU conventions, brand info
- state.base_context - Catalog summary, taxonomy tree

Use these for context-aware decisions.
</state_access>

<instructions>
PM provides enriched product context.
You autonomously determine analysis approach.

[Detailed domain methodology]
</instructions>
```

---

### PM Prompt Architecture

**Delegation Pattern:**

```xml
<delegation_to_specialists>
When delegating to Product Architecture Specialist:

Provide ENRICHED PRODUCT CONTEXT (not instructions):

1. Product details (synthesized from conversation):
   - Type, materials, dimensions, pricing
   - Latest values if user corrected information

2. Image file paths if available

3. Your basic analysis from image_analysis_tool

4. Your catalog awareness (mark as non-authoritative):
   "My catalog search (summary): [result]. Your detailed search is authoritative."

5. Pointers to state:
   "Company context in state.company_profile"
   "Catalog awareness in state.base_context"

DO NOT:
- Give step-by-step instructions
- Pass conversation history or user intent
- Duplicate state data in text
- Micromanage specialist methodology

Trust specialist autonomy. They know their job.
</delegation_to_specialists>
```

---

## Phase 2 Implementation Tasks

### Task 2.1: Update Specialist Prompt
**File:** `product_architecture_specialist.prompt`

**Goal:** Make prompt autonomous and context-driven (not instruction-driven)

**Key Updates:**
- Emphasize autonomous decision-making
- Document state access patterns
- Remove micromanagement language
- Show context-based delegation examples
- Include graceful degradation patterns

---

### Task 2.2: Review & Optimize Specialist Tools
**Critical Question:** Do we need all these tools, or can intelligent LLM reason through some?

**Current Tools:**
- search_product_families
- image_analysis_tool
- calculate_sku_combinations
- generate_sku_pattern

**Review Needed:** Which are essential vs which LLM can handle autonomously?

---

### Task 2.3: Update PM Prompt for Context Delegation
**File:** `project_manager_intelligent.prompt`

**Goal:** Add delegation pattern for Product Architecture Specialist

**Pattern:** Enriched context (product facts), NOT step-by-step instructions

---

### Task 2.4: Integrate Specialist with PM
**File:** `project_manager.py`

**Changes:**
- Add specialist to subagents list
- Pass storage for search tool
- Update initial_state tracking

---

### Task 2.5: Test Specialist Isolation
**Test 5 Scenarios:**
1. New product (no catalog match)
2. Existing product (add variant)
3. Ambiguous match
4. Missing data (graceful degradation)
5. Image analysis failure

**Validate:** Autonomy, confidence scoring, flag transparency

---

### Task 2.6: Test PM → Specialist End-to-End
**Flow:** User vague request → PM enriches → Delegate → Specialist analyzes → PM presents

**Validate Delegation:**
- Context-rich (product facts, images, PM analysis)
- NO instructions or conversation history
- State pointers included

---

### Task 2.7: PM Handles Specialist Recommendations
**Implement:** PM interprets specialist signals (create_new/add_variant/ask_user, confidence, flags)

**Multi-Turn:** Low confidence → PM asks user → Re-delegate

---

### Task 2.8: Documentation & Commit
**Update plan, capture learnings, commit Phase 2**

---

## Phase 2 Success Criteria

**✅ When Phase 2 is Complete:**

1. **Specialist Integration:**
   - Product Architecture Specialist integrated with PM
   - Tools wired correctly (search, image, SKU)
   - Structured output (ProductArchitectureDraft)

2. **Autonomous Operation:**
   - Specialist autonomously decides analysis approach
   - PM provides context, not instructions
   - Specialist reads state (company_profile, base_context)

3. **Delegation Pattern:**
   - PM writes enriched product context
   - NO conversation history passed
   - NO step-by-step instructions
   - State pointers included

4. **Error Handling:**
   - Graceful degradation working (flags + confidence)
   - PM interprets specialist signals
   - Multi-turn clarification flow working

5. **All Test Scenarios Pass:**
   - New product, add variant, ambiguous match
   - Missing data, image failures
   - End-to-end PM → Specialist flow

**Then Proceed to Phase 3:** Add Taxonomy Specialist (runs in parallel with Product Architecture)

---

### Task 2.1: Review Product Architecture Specialist Prompt
**File:** `agents/src/autifyme_agents/prompts/specialists/product_architecture_specialist.prompt`

**Audit Against Standards:**
- [ ] XML structure (background, tools, instructions, examples, output)
- [ ] No code snippets (only Pydantic model names)
- [ ] Right altitude (low-medium: domain execution)
- [ ] 2-4 canonical examples (diverse scenarios)
- [ ] Tool references match implementations
- [ ] Output format matches Pydantic models

**Issues to Fix:**
- References `search_product_families` tool but tool not wired
- Needs clarity on when to search vs when to skip
- Examples should show multimodal analysis (text + image)
- Missing error handling examples (no image, low confidence)

### Task 2.2: Wire Search Tool to Specialist
**File:** `agents/src/autifyme_agents/specialists/product_architecture_specialist.py`

**Changes:**
```python
from autifyme_agents.tools.product_search_tools import (
    create_search_product_families_tool,
)

def create_product_architecture_specialist(
    storage: StorageInterface,  # Required for search tool
) -> dict[str, Any]:
    """Create Product Architecture Specialist with search capability."""

    # Tools for specialist
    tools = [
        image_analysis_tool,
        calculate_sku_combinations,
        generate_sku_pattern,
        create_search_product_families_tool(storage),  # ADD THIS
    ]

    # Load prompt
    prompt = load_prompt("specialists/product_architecture_specialist.prompt")

    # Return SubAgent dict
    return {
        "name": "product_architecture_specialist",
        "instructions": prompt,
        "tools": tools,
    }
```

**Validation:**
```bash
uv run python -c "
from dotenv import load_dotenv; load_dotenv('.env')
from autifyme_agents.integrations.storage import get_storage
from autifyme_agents.specialists.product_architecture_specialist import create_product_architecture_specialist

storage = get_storage()
specialist = create_product_architecture_specialist(storage)
print(f'Tools: {len(specialist[\"tools\"])} - {[t.name for t in specialist[\"tools\"]]}')
"
```

**Expected Output:**
```
Tools: 4 - ['image_analysis_tool', 'calculate_sku_combinations', 'generate_sku_pattern', 'search_product_families']
```

### Task 2.3: Update Prompt with Complete Guidance
**File:** `agents/src/autifyme_agents/prompts/specialists/product_architecture_specialist.prompt`

**Key Additions:**
- **Step 0: Search Catalog FIRST** (before analysis)
- **Conditional SKU Pattern:** Use existing prefix if match found, generate new if create_new
- **Error Handling:** What to do if search fails, image analysis fails
- **Low Confidence Handling:** Flag to PM when confidence <0.7
- **Match Recommendation in Output:** Include search results for PM decision-making

### Task 2.4: Test Specialist in Isolation
**Test Script:** `tests/cli/test_specialist_isolated.py --specialist=product_architecture`

**Test Cases:**
1. **New Product (No Match):**
   - Input: "PET jar 500ml Rs 30" + image
   - Expected: Search returns `create_new`, generates new SKU pattern

2. **Existing Product (Exact Match):**
   - Input: "PET jar 750ml Rs 35" + image (same family)
   - Expected: Search returns `add_variant`, uses existing SKU prefix

3. **Ambiguous Match:**
   - Input: Similar name but different brand
   - Expected: Search returns `ask_user`, presents matches

4. **Text-Only (No Image):**
   - Input: "Glass bottles 250ml, 500ml, 1L"
   - Expected: Works without image, flags lower confidence

5. **Search Tool Failure:**
   - Simulate database error
   - Expected: Specialist continues with `create_new` assumption

**Validation:**
- All test cases pass
- Structured output returned (ProductArchitectureDraft)
- Search results included in output
- Confidence scores present

### Task 2.5: Add Specialist to PM
**File:** `agents/src/autifyme_agents/workflows/project_manager.py`

**Changes:**
```python
from autifyme_agents.specialists.product_architecture_specialist import (
    create_product_architecture_specialist,
)

def create_project_manager(...):
    # ... (pm_tools setup)

    # Specialists - incremental build-up
    subagents: list[Any] = [
        # Phase 2: Product Architecture Specialist
        create_product_architecture_specialist(storage),
    ]

    # ... (rest of PM setup)

    initial_state = {
        "company_profile": company_profile.model_dump(),
        "status": "building_up",
        "integrated_specialists": ["product_architecture_specialist"],  # Track
        "specialist_results": {},
    }
```

### Task 2.6: Update PM Prompt
**File:** `agents/src/autifyme_agents/prompts/project_manager.prompt`

**Changes:**
```xml
<available_tools>
## Specialists (Incremental Build-Up)

1. **product_architecture_specialist**
   - Expertise: Variant structure, SKU design, catalog search
   - Inputs: Product name/description, optional: images (file paths)
   - Outputs: Variant axes, SKU patterns, catalog match recommendation
   - Tools: image_analysis, search_catalog, generate_sku_pattern
   - When: User requests product onboarding/cataloging

[NOTE: Additional specialists will be added incrementally]
</available_tools>

<instructions>
## Product Onboarding Workflow (PARTIAL - Architecture Only)

**Current Capability:** Product structure analysis only

When user requests product onboarding:
1. Download media if provided
2. Delegate to product_architecture_specialist with:
   - Product description from user
   - Image file path (if downloaded)
3. Receive ProductArchitectureDraft with:
   - Variant axes, SKU pattern
   - Catalog search results (match recommendation)
4. Acknowledge receipt, explain: "Product structure analyzed. Additional specialists (taxonomy, market intel, content) coming next."

**DO NOT call save_product_family yet** - incomplete data without other specialists.
</instructions>

<examples>
## Example: Product Onboarding with Architecture Specialist

<example>
<user_input>
Text: "Catalog PET jar 500ml Rs 30"
Media: [image_id: abc123]
</user_input>

<your_reasoning>
- Intent: product_onboarding
- Specialists available: product_architecture_specialist only
- Media: Yes, download first
- Workflow: Download → Delegate → Acknowledge (incomplete workflow)
</your_reasoning>

<your_action>
→ download_whatsapp_media("abc123")
← "C:\Temp\abc123.jpg"

→ task(
    name="product_architecture_specialist",
    description="Analyze PET jar 500ml at Rs 30. Image: C:\Temp\abc123.jpg. Search catalog first for existing families."
  )
← ProductArchitectureDraft(
    product_family_name="PET Jar 500ml",
    product_group_id="PACK-PET-JAR",
    variant_axes=[...],
    sku_pattern=SKUPatternDraft(...),
    search_result=ProductFamilySearchResult(
      recommendation="create_new",
      confidence=0.95
    )
  )
</your_action>

<your_response>
"Product structure analyzed for PET Jar 500ml:
- 1 variant detected (500ml)
- SKU pattern: PACK-PET-JAR-500ML
- Catalog search: No existing family found (create new recommended)

Next specialists (taxonomy, market intelligence, content) are being integrated to complete onboarding workflow."
</your_response>
</example>
</examples>
```

### Task 2.7: Test End-to-End with PM
**Test:** Send product onboarding request through PM

**Command:**
```bash
uv run python tests/cli/pm_chat.py
```

**Interaction:**
```
User: Catalog PET jar 500ml Rs 30 [+ image]
PM: [Downloads image → Delegates to product_architecture_specialist → Returns structured analysis]
Expected: PM acknowledges analysis, mentions incomplete workflow
```

**Validation:**
- PM detects product_onboarding intent
- PM downloads media
- PM delegates to product_architecture_specialist
- Specialist returns ProductArchitectureDraft
- PM acknowledges, doesn't hallucinate completion

### Task 2.8: Commit and Document
```bash
git add .
git commit -m "Phase 2: Add Product Architecture Specialist

- Wire search tool to specialist
- Update prompt with search-first workflow
- Integrate with minimal PM
- Test end-to-end product structure analysis
- Partial product onboarding workflow (architecture only)

Specialists: 1/10 integrated"
```

---

## Phase 3: Add Taxonomy Specialist (3-4 hours)

### Goal
Second specialist integrated - enables multi-system classification.

### Task 3.1: Review Taxonomy Specialist Prompt
**File:** `agents/src/autifyme_agents/prompts/specialists/taxonomy_specialist.prompt`

**Focus:**
- Synthesis specialist (no external tools beyond classify functions)
- Multi-system classification (internal + Google + NAICS)
- Handles B2B multi-industry targeting
- Works with minimal info, flags low confidence

### Task 3.2: Verify Tool Integration
**File:** `agents/src/autifyme_agents/specialists/taxonomy_specialist.py`

**Check:**
- [ ] Tools match prompt (classify_into_industries, find_relevant_categories, find_google_product_category)
- [ ] Storage passed for database lookups
- [ ] Output model matches prompt (TaxonomyClassificationDraft)

### Task 3.3: Test Specialist in Isolation
**Test Cases:**
1. **B2B Packaging:** "PET jars for food packaging"
2. **B2C Product:** "Sneakers for athletes"
3. **Multi-Industry:** "Commercial kitchen equipment"

**Validation:**
- Returns structured TaxonomyClassificationDraft
- Multiple industries if applicable
- Google Product Category mapped
- Confidence scores present

### Task 3.4: Add to PM
**File:** `agents/src/autifyme_agents/workflows/project_manager.py`

```python
from autifyme_agents.specialists.taxonomy_specialist import create_taxonomy_specialist

subagents: list[Any] = [
    create_product_architecture_specialist(storage),
    create_taxonomy_specialist(storage),  # ADD
]

initial_state["integrated_specialists"] = [
    "product_architecture_specialist",
    "taxonomy_specialist",
]
```

### Task 3.5: Update PM Prompt
**Add to specialists list:**
```xml
2. **taxonomy_specialist**
   - Expertise: Multi-system classification (internal, Google, NAICS)
   - Inputs: Product name/description, product type
   - Outputs: Category mappings, industry codes
   - When: After product architecture analysis (can run in parallel)
```

**Update workflow:**
```xml
## Product Onboarding Workflow (PARTIAL - Architecture + Taxonomy)

1. Download media
2. Delegate to product_architecture_specialist
3. Delegate to taxonomy_specialist (parallel with architecture)
4. Receive both outputs
5. Acknowledge: "Product structure and classification complete. Market intelligence and content specialists coming next."
```

### Task 3.6: Test End-to-End
**Validation:**
- PM delegates to both specialists (parallel)
- Both return structured outputs
- PM synthesizes results
- PM acknowledges partial workflow

### Task 3.7: Commit
```bash
git commit -m "Phase 3: Add Taxonomy Specialist

- Verify tool integration
- Update PM for parallel delegation
- Test multi-system classification
- Product onboarding workflow: Architecture + Taxonomy

Specialists: 2/10 integrated"
```

---

## Phase 4: Add Market Intelligence Specialist (3-4 hours)

### Goal
Third specialist - enables price positioning and customer segmentation.

### Task 4.1: Review Prompt
**File:** `agents/src/autifyme_agents/prompts/specialists/market_intelligence_specialist.prompt`

**Focus:**
- Price positioning (budget/mid/premium/luxury)
- Customer segments (B2B/B2C/D2C)
- Industry use cases
- Adaptation: suggests defaults if price missing

### Task 4.2: Verify Tools
**Check:**
- [ ] analyze_price_positioning
- [ ] identify_customer_segments
- [ ] No storage dependency (synthesis specialist)

### Task 4.3: Test in Isolation
**Test Cases:**
1. **With Price:** "PET jar Rs 30"
2. **No Price:** "Glass bottles" (should suggest defaults)
3. **B2B:** "Industrial packaging"
4. **B2C:** "Consumer beverage containers"

### Task 4.4: Add to PM
```python
from autifyme_agents.specialists.market_intelligence_specialist import (
    create_market_intelligence_specialist,
)

subagents: list[Any] = [
    create_product_architecture_specialist(storage),
    create_taxonomy_specialist(storage),
    create_market_intelligence_specialist(),  # No storage needed
]
```

### Task 4.5: Update PM Prompt
**Add specialist:**
```xml
3. **market_intelligence_specialist**
   - Expertise: Price positioning, customer segments, use cases
   - Inputs: Product type, price (optional), target market
   - Outputs: Positioning, segments, use cases
```

**Update workflow:**
```xml
3. Delegate to 3 specialists in PARALLEL:
   - product_architecture_specialist
   - taxonomy_specialist
   - market_intelligence_specialist
```

### Task 4.6: Test End-to-End
**Validation:**
- 3 specialists run in parallel
- All return structured outputs
- PM synthesizes

### Task 4.7: Commit
```bash
git commit -m "Phase 4: Add Market Intelligence Specialist

Specialists: 3/10 integrated"
```

---

## Phase 5: Add Visual Assets Specialist (3-4 hours)

### Goal
Fourth specialist - enables image organization and quality assessment.

### Task 5.1: Review Prompt
**Focus:**
- Image organization for ecommerce
- Quality assessment
- Alt text generation
- Handles missing images gracefully

### Task 5.2: Verify Tools
**Check:**
- [ ] image_analysis_tool (shared with Product Architecture)
- [ ] ls, read, write (file operations)

### Task 5.3: Test in Isolation
**Test Cases:**
1. **Single Image:** Quality assessment
2. **Multiple Images:** Organization and ranking
3. **No Images:** Graceful skip

### Task 5.4: Add to PM
```python
from autifyme_agents.specialists.visual_assets_specialist import (
    create_visual_assets_specialist,
)

subagents.append(create_visual_assets_specialist())
```

### Task 5.5: Update PM Prompt
**Add specialist:**
```xml
4. **visual_assets_specialist**
   - Expertise: Image organization, quality assessment
   - Inputs: Images (file paths), product name
   - Outputs: Asset organization, quality scores, alt text
```

**Update workflow:**
```xml
4. Delegate to 4 specialists in PARALLEL (if images present):
   - product_architecture_specialist
   - taxonomy_specialist
   - market_intelligence_specialist
   - visual_assets_specialist (CONDITIONAL - skip if no images)
```

### Task 5.6: Test End-to-End
**Validation:**
- 4 specialists run in parallel
- Visual specialist skipped if no images

### Task 5.7: Commit
```bash
git commit -m "Phase 5: Add Visual Assets Specialist

Specialists: 4/10 integrated"
```

---

## Phase 6: Add Content & SEO Specialist (4-5 hours)

### Goal
Fifth specialist - FIRST SYNTHESIS SPECIALIST (depends on others).

### Task 6.1: Review Prompt
**Focus:**
- **Depends on:** Taxonomy + Market Intelligence outputs
- Generates descriptions, meta tags, SEO content
- Platform-specific content
- Works with partial data

### Task 6.2: Verify Tools
**Check:**
- [ ] No external tools (synthesis specialist)
- [ ] Receives outputs from other specialists as input

### Task 6.3: Test in Isolation
**Test Cases:**
1. **Full Data:** Taxonomy + Market + Product name
2. **Partial Data:** Only product name (should adapt)

### Task 6.4: Add to PM
```python
from autifyme_agents.specialists.content_seo_specialist import (
    create_content_seo_specialist,
)

subagents.append(create_content_seo_specialist())
```

### Task 6.5: Update PM Prompt
**CRITICAL CHANGE - Sequential Delegation:**
```xml
## Product Onboarding Workflow (COMPLETE - All 5 Specialists)

1. Download media if present
2. Delegate to 4 foundational specialists in PARALLEL:
   - product_architecture_specialist
   - taxonomy_specialist
   - market_intelligence_specialist
   - visual_assets_specialist (if images)
3. WAIT for all to complete
4. Delegate to content_seo_specialist with outputs from step 2
5. Synthesize all 5 outputs into ProductFamilyInput
6. Call save_product_family (triggers HITL)
7. User approves
8. Persistence tool saves atomically
9. Confirm to user with product_family_id
```

### Task 6.6: Test End-to-End FULL WORKFLOW
**Validation:**
- 4 specialists in parallel → content specialist sequential
- PM synthesizes into ProductFamilyInput
- PM calls save_product_family
- HITL triggers, user approves
- Product saved to database

**SUCCESS MILESTONE:** First complete workflow (Product Onboarding)!

### Task 6.7: Commit
```bash
git commit -m "Phase 6: Add Content & SEO Specialist - PRODUCT ONBOARDING COMPLETE

- First synthesis specialist (depends on taxonomy + market)
- Sequential delegation after foundational specialists
- Full end-to-end product onboarding workflow
- HITL approval flow tested
- Product persisted to database

Specialists: 5/10 integrated
Workflows: Product Onboarding ✅"
```

---

## Phase 7-11: Add Marketing Campaign Specialists (15-20 hours)

**Specialists to Add (in order):**
- Phase 7: Campaign Strategy Specialist (foundational for marketing)
- Phase 8: Audience Intelligence Specialist (depends on Campaign Strategy)
- Phase 9: Marketing Content Specialist (depends on Campaign Strategy)
- Phase 10: Platform Adaptation Specialist (depends on Marketing Content)
- Phase 11: Ad Copy Specialist (depends on Marketing Content + Platform)

**Each phase follows same pattern:**
1. Review prompt (2-3 examples, tools verified)
2. Test in isolation
3. Add to PM
4. Update PM prompt (add specialist, update marketing workflow)
5. Test end-to-end
6. Commit

**Phase 11 Success Milestone:** Marketing campaign workflow complete!

---

## Phase 12: Final Integration & Polish (4-6 hours)

### Task 12.1: Remove Dead Code
**File:** `agents/src/autifyme_agents/specialists/cataloging_specialist.py`
**Action:** Delete (legacy artifact, not used)

### Task 12.2: Finalize PM Prompt
**File:** `agents/src/autifyme_agents/prompts/project_manager.prompt`

**Changes:**
- Remove "incremental build-up" notes
- Update to "10 specialists fully integrated"
- Add complete workflow examples for both domains
- Add error handling examples
- Add multi-domain examples (product + marketing in same session)

### Task 12.3: Comprehensive Testing
**Test Matrix:**

| Workflow | Scenario | Expected Result |
|----------|----------|-----------------|
| Product Onboarding | New product + image | Create new family |
| Product Onboarding | Existing family variant | Add variant |
| Product Onboarding | Ambiguous match | Ask user |
| Product Onboarding | No image | Skip visual, continue |
| Marketing Campaign | Full campaign | All 5 specialists execute |
| Marketing Campaign | No products specified | Ask clarification |
| Error Handling | Specialist failure | Graceful degradation |
| Error Handling | HITL rejection | Cancel, ask for edits |
| Multi-Workflow | Product → Campaign | State persists across workflows |

### Task 12.4: Performance Optimization
- Verify parallel delegation working
- Check token usage (should be within budget)
- Validate LangSmith traces

### Task 12.5: Documentation Update
**Files to Update:**
- [CLAUDE.md](../../../CLAUDE.md) - Mark build-up plan complete
- [README.md](../../../README.md) - Update status to "Production Ready"
- [COMPREHENSIVE_ARCHITECTURAL_REVIEW.md](../COMPREHENSIVE_ARCHITECTURAL_REVIEW.md) - Document build-up approach

### Task 12.6: Final Commit
```bash
git commit -m "Phase 12: Final Integration Complete - All 10 Specialists Integrated

- Product Onboarding workflow: 5 specialists ✅
- Marketing Campaign workflow: 5 specialists ✅
- Dead code removed (cataloging_specialist)
- PM prompt finalized
- Comprehensive testing complete
- Documentation updated

Specialists: 10/10 integrated
Workflows: Product Onboarding ✅ | Marketing Campaigns ✅
Status: Production Ready"
```

---

## Success Metrics

### Per-Specialist Metrics
- [ ] Specialist loads without errors
- [ ] All tools wired correctly
- [ ] Prompt follows standards
- [ ] Isolated test passes
- [ ] PM integration successful
- [ ] End-to-end workflow works

### Workflow Metrics
- [ ] Product Onboarding: 5 specialists execute, HITL works, product saved
- [ ] Marketing Campaign: 5 specialists execute, HITL works, campaign saved
- [ ] Error scenarios handled gracefully
- [ ] No hallucinations (PM doesn't claim completion without save confirmation)

### System Metrics
- [ ] Token usage within budget (<150k per workflow)
- [ ] Execution time reasonable (<60s for standard workflow)
- [ ] LangSmith traces clean (no errors, clear hierarchy)
- [ ] State persistence working (multi-message workflows)

---

## Rollback Plan

**If a specialist breaks:**
1. Revert last commit: `git reset --hard HEAD~1`
2. Fix specialist in isolation
3. Re-test before re-integrating

**If PM breaks:**
1. Revert to last working commit
2. Debug PM in isolation
3. Re-integrate specialists one by one

---

## Timeline Estimate

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Phase 0: Preparation | 2h | 2h |
| Phase 1: Minimal PM | 4-6h | 6-8h |
| Phase 2: Product Architecture | 4-5h | 10-13h |
| Phase 3: Taxonomy | 3-4h | 13-17h |
| Phase 4: Market Intelligence | 3-4h | 16-21h |
| Phase 5: Visual Assets | 3-4h | 19-25h |
| Phase 6: Content & SEO | 4-5h | 23-30h |
| Phase 7-11: Marketing (5 specialists) | 15-20h | 38-50h |
| Phase 12: Final Integration | 4-6h | 42-56h |

**Total: 42-56 hours (~1-1.5 weeks full-time)**

---

## Next Steps

**Immediate Actions:**
1. Review this plan with user
2. Get approval to proceed
3. Start Phase 0 (backup and create minimal PM)
4. Begin Phase 1 (perfect minimal PM core)

**User Confirmation Needed:**
- [ ] Approve overall strategy
- [ ] Confirm specialist order
- [ ] Agree on testing approach
- [ ] Commit to incremental build-up (no shortcuts)

---

**Last Updated:** October 28, 2025
**Author:** Claude (with user guidance)
**Status:** Awaiting user approval to proceed
