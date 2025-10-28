# Specialist Build-Up Integration Plan

**Date:** October 28, 2025
**Status:** 🚧 In Progress
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

## Phase 1: Perfect Minimal PM ⚠️ NEEDS REVISION (4-6 hours)

### Goal (ORIGINAL)
PM with ZERO specialists, perfected core orchestration logic.

**Original Result:** ✅ PASSED basic test (intent detection, honest communication)
**Trace:** https://smith.langchain.com/public/7f12717c-b16c-45af-b251-4cff09e5c6da/r/9159e0bf-e02d-44c9-8a8f-62a3cf052df4
**Commit:** a2010b5

### Why Revision Needed

**Problem Discovered:** Phase 1 PM was TOO MINIMAL
- ❌ No image analysis capability
- ❌ No domain knowledge
- ❌ No intelligent discussion
- ❌ Just says "specialists coming soon" (not useful)

**New Understanding:** PM should be INTELLIGENT from Phase 1
- ✅ Can analyze images
- ✅ Has domain knowledge
- ✅ Can discuss with user
- ✅ Understands intent deeply

### Revised Goal
PM with ZERO specialists BUT with intelligent capabilities:
- Intent understanding (deep, not just keyword matching)
- Image analysis (understand what user sent)
- Domain knowledge (B2B packaging, product concepts)
- Company context (Pavisha details)
- User discussion (ask clarifying questions)
- Strategic planning

**Status:** NEEDS REWORK based on new paradigm

### Task 1.1: Define Minimal PM Responsibilities
**Core Capabilities (No Specialists):**
- Intent detection (recognize: product onboarding, marketing campaign, operations, unknown)
- Media handling (download attachments from platform)
- Planning tools (write_todos for complex workflows)
- HITL persistence (save_product_family, save_campaign triggers)
- Error communication (clear messages to user)
- Specialist delegation framework (ready but empty)

**Does NOT:**
- Analyze products (will delegate to Product Architecture Specialist)
- Classify taxonomy (will delegate to Taxonomy Specialist)
- Generate content (will delegate to Content Specialist)
- Create campaigns (will delegate to Campaign Specialists)

### Task 1.2: Write Minimal PM Prompt
**Location:** `agents/src/autifyme_agents/prompts/project_manager_minimal.prompt`

**Structure:**
```xml
<background_information>
You are the Project Manager for {company_name}, the central orchestrator.

Current Capabilities: MINIMAL (no specialists yet)
- Intent detection
- Media download
- Planning with write_todos
- Error communication

Future: Specialists will be added incrementally for domain expertise.
</background_information>

<available_tools>
## Platform Tools
- download_{platform}_media: Download user attachments

## Planning Tools
- write_todos: Track multi-step workflows

## Persistence Tools (HITL-enabled - DO NOT USE YET)
- save_product_family: Persist products (requires specialist data)
- save_campaign: Persist campaigns (requires specialist data)
</available_tools>

<instructions>
## Your Current Role

With NO specialists available yet, you:
1. Detect user intent (product onboarding, marketing, operations, unknown)
2. Download media if user sends attachments
3. Respond: "I've detected a [INTENT] request. Specialists are being added incrementally. Currently, I cannot process this yet."

## Intent Detection

Classify requests into:
- **product_onboarding**: Catalog, add product, new SKU, onboard item
- **marketing_campaign**: Campaign, ads, content, promote, marketing
- **operations**: Inventory, orders, shipping, billing
- **unknown**: Cannot classify

## Media Handling

If user sends media (image/video/document):
- Call download_{platform}_media(media_id)
- Store file path
- Mention in response: "I've downloaded your [media_type]"

## Communication

Be honest about current limitations:
- "I understand you want to [INTENT]"
- "I've downloaded your attachments"
- "Specialists are being integrated - this capability will be available soon"
</instructions>

<examples>
## Example 1: Product Onboarding Request
<example>
<user_input>
Platform: WhatsApp
Text: "Catalog PET jar 500ml Rs 30"
Media: [image_id: abc123]
</user_input>

<your_reasoning>
- Intent: product_onboarding (keyword "catalog")
- Media: Yes, need to download
- Action: Download media, acknowledge request, explain limitation
</your_reasoning>

<your_action>
→ download_whatsapp_media(media_id="abc123")
← file_path: "C:\Temp\media_downloads\abc123.jpg"
</your_action>

<your_response>
"I've detected a product onboarding request and downloaded your image. Product Architecture Specialist is being integrated next - this workflow will be available soon."
</your_response>
</example>

## Example 2: Marketing Campaign Request
<example>
<user_input>
Platform: WhatsApp
Text: "Create summer campaign for bottles"
</user_input>

<your_reasoning>
- Intent: marketing_campaign (keyword "campaign")
- Media: No
- Action: Acknowledge, explain limitation
</your_reasoning>

<your_response>
"I understand you want to create a summer marketing campaign for bottles. Campaign specialists are being integrated - this capability will be available soon."
</your_response>
</example>
</examples>

<output_format>
Single message response:
- Acknowledge intent
- Mention media download if applicable
- Set expectation about current limitations
</output_format>
```

### Task 1.3: Implement Minimal PM
**File:** `agents/src/autifyme_agents/workflows/project_manager.py`

**Changes:**
```python
def create_project_manager(
    company_profile: CompanyProfile,
    *,
    model: BaseChatModel | None = None,
    checkpointer: Any,
    storage: StorageInterface,
    channel: MessagingChannel | None = None,
) -> Any:
    """
    Create Minimal Project Manager - core orchestration only.

    Current: 0 specialists (building up incrementally)

    Capabilities:
    - Intent detection
    - Media download
    - Planning (write_todos)
    - HITL framework (persistence tools available but not callable yet)
    """

    if checkpointer is None:
        raise ValueError("checkpointer is required")
    if storage is None:
        raise ValueError("storage is required")

    llm = _resolve_model(model)
    instructions = load_prompt("project_manager_minimal.prompt").format(
        company_name=company_profile.name,
        brand_voice=company_profile.brand_voice,
        target_audience=company_profile.target_audience,
    )
    store = get_store()

    # PM Tools - minimal set
    pm_tools: list[Any] = []

    if channel is not None:
        from autifyme_agents.tools.platform_tools import create_platform_media_tools
        pm_tools.extend(create_platform_media_tools(channel))

    # HITL persistence tools (available but PM won't call them yet)
    # Kept for framework testing
    pm_tools.append(create_save_product_family_tool(storage))
    pm_tools.append(create_save_campaign_tool(storage))

    # NO SPECIALISTS YET - will add incrementally
    subagents: list[Any] = []

    # HITL config (for future)
    interrupt_configs: dict[str, bool] = {
        "save_product_family": True,
        "save_campaign": True,
    }

    # Create minimal DeepAgent
    project_manager = create_deep_agent(
        tools=pm_tools,
        system_prompt=instructions,
        model=llm,
        subagents=subagents,  # EMPTY
        interrupt_on=interrupt_configs,
        checkpointer=checkpointer,
        store=store,
        use_longterm_memory=True,
        context_schema=CompanyContext,
    )

    initial_state = {
        "company_profile": company_profile.model_dump(),
        "status": "minimal",  # Track build-up state
        "integrated_specialists": [],  # Track which specialists are active
        "specialist_results": {},
    }

    return project_manager.with_config(
        {
            "metadata": {
                "version": "1.0.0-minimal",
            },
            "initial_state": initial_state,
        }
    )
```

### Task 1.4: Test Minimal PM
**Test Cases:**
1. **Intent Detection:** Send "catalog jar" → PM detects product_onboarding
2. **Media Download:** Send image → PM downloads and stores path
3. **Planning:** Send complex request → PM uses write_todos
4. **Honest Communication:** PM acknowledges limitation, doesn't hallucinate

**Validation:**
- PM loads without errors
- Intent detection works
- Media download succeeds
- No crashes, no hallucinations

**Command:**
```bash
uv run python tests/cli/test_specialist_isolated.py --mode=minimal_pm
```

---

## Phase 1 (REVISED): Build Intelligent PM Core 🚧 PLANNING (6-8 hours)

### Goal
PM with intelligent capabilities (ZERO specialists yet):
- Multimodal understanding (analyze images)
- Domain knowledge (B2B packaging, product concepts)
- Company context (Pavisha: B2B packaging manufacturer in India)
- Intelligent discussion (ask clarifying questions)
- Strategic planning (understand → discuss → plan → prepare for delegation)

### Revised Responsibilities

**PM Should Be Able To:**

1. **Understand User Intent (Deep, Not Surface):**
   - Analyze images to see what user sent
   - Understand product from visual + text cues
   - Recognize product patterns (jars, bottles, containers)
   - Classify domains (product onboarding, marketing, operations)

2. **Have Intelligent Discussions:**
   - Ask clarifying questions when info missing
   - Example: Image of jar → "I see a 500ml PET jar. What's the price? Do you have other sizes?"
   - Guide user to provide complete information
   - Don't blindly delegate with incomplete data

3. **Know Company Context:**
   - Pavisha = B2B packaging manufacturer (India)
   - Product types: PET bottles, HDPE containers, glass jars, closures
   - Target market: Food, beverage, pharma, personal care industries
   - Pricing context: Budget-friendly, bulk orders
   - Brand voice: Professional, helpful, technical expertise

4. **Have Domain Knowledge:**
   - B2B vs B2C differences (bulk vs retail)
   - Packaging domain knowledge (materials, capacities, grades)
   - Product structure concepts (families, variants, SKUs)
   - When to ask what questions

5. **Plan Strategically:**
   - Understand what data is needed for downstream specialists
   - Enrich data before delegation
   - Example: Instead of passing "catalog this" to specialist, pass:
     "Analyze PET jar family. B2B packaging. 3 capacities: 250ml, 500ml, 1L. Base price Rs 30. Company: Pavisha. Image shows transparent food-grade PET."

6. **Prepare for Future Specialists:**
   - Know what Product Architecture Specialist will need (structure, variants, SKUs)
   - Know what Taxonomy Specialist will need (category, industry, use cases)
   - But can't call them yet (Phase 1 = 0 specialists)
   - Can describe what WILL happen when specialists are added

### Revised Tasks

#### Task 1.1: Add Image Analysis to PM ⏳
- Add `image_analysis_tool` to PM tools
- Update PM prompt with image understanding guidance
- Test: Send image + vague text → PM analyzes and asks smart questions

#### Task 1.2: Add Domain Knowledge to PM ⏳
- Update PM prompt with packaging domain knowledge
- B2B vs B2C context
- Product structure concepts (families, variants)
- Common product types (jars, bottles, containers)

#### Task 1.3: Add Company Context to PM ⏳
- Update PM prompt with Pavisha details
- Company profile: B2B packaging manufacturer
- Product catalog: PET, HDPE, glass
- Target market: Food, beverage, pharma
- Brand voice: Professional, technical

#### Task 1.4: Add Discussion Capability ⏳
- Update PM prompt with clarifying question patterns
- Examples of smart questions to ask
- When to ask (missing data, ambiguous intent)
- How to guide user to complete information

#### Task 1.5: Test Intelligent PM ⏳
- Test scenario: Image + "catalog this" → PM analyzes, asks questions
- Test scenario: Vague request → PM guides user
- Test scenario: Complete request → PM understands, plans (but can't execute yet)
- Validate: PM is intelligent, not just routing

**Status:** NEEDS TO START based on new paradigm

---

## Phase 2: Add Product Architecture Specialist ⏸️ PAUSED (4-5 hours)

### Goal
First specialist integrated - enables deep product structure analysis.

**Status:** Paused pending Phase 1 revision

### Revised Understanding of Specialist Role

**OLD Understanding:**
- Specialist receives raw user message
- Specialist does ALL analysis (basic + deep)
- Specialist returns structured output

**NEW Understanding:**
- Specialist receives ENRICHED input from PM
- PM already understood basics (what product, basic structure)
- Specialist focuses on DEEP analysis:
  - Detailed variant axis identification
  - SKU pattern design (naming conventions, hierarchies)
  - Catalog search and matching (autonomous create vs update)
  - Complex structural decisions (variant vs attribute, consolidation)

**Example Input to Specialist (NEW):**
```
PM → Product Architecture Specialist:

"Analyze PET jar family for catalog onboarding.

Context:
- Company: Pavisha (B2B packaging manufacturer, India)
- Product: PET jars for food packaging
- Capacities: 250ml, 500ml, 1L (3 variants on size axis)
- Material: Food-grade transparent PET
- Base price: Rs 30 (for 500ml)
- Target market: Food & beverage industry (B2B bulk orders)
- Image analysis: Transparent cylindrical jar, wide mouth, screw-top compatible

My understanding:
- This is a product FAMILY (not standalone)
- Single variant axis: capacity (250ml, 500ml, 1L)
- Material is constant (PET), not a variant dimension
- B2B context: Bulk pricing, technical specifications matter

Your task:
- Design detailed variant structure
- Calculate SKU combinations
- Generate SKU naming pattern (consider B2B naming conventions)
- Search catalog for existing PET jar families (autonomous matching)
- Recommend: create new family OR add to existing OR ask user

Return ProductArchitectureDraft with your expert analysis."
```

**Compare to OLD Input:**
```
PM → Product Architecture Specialist:

"catalog this" + [image]
```

**NEW input is ENRICHED** → Specialist can focus on deep analysis, not basic understanding.

**Status:** Will resume after Phase 1 revised

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

**Last Updated:** January 28, 2025
**Author:** Claude (with user guidance)
**Status:** Awaiting user approval to proceed
