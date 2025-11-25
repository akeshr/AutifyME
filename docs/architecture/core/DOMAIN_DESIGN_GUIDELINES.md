# Domain Design Guidelines

**Version:** 1.0.0
**Created:** October 25, 2025
**Purpose:** Architectural standards for designing new AutifyME domains and workflows

---

## Core Architectural Principles

### 1. Single Generic PM Pattern

**Decision:** One main Project Manager orchestrates ALL workflows.

**Guidelines:**
- Main PM (`project_manager.py`) handles current and future workflows
- PM detects workflow intent from user input
- PM routes to appropriate specialists
- PM synthesizes results and persists data
- Each workflow adds specialists/tools to PM (no separate PM per workflow)

**Anti-Pattern:**
- ❌ Creating separate PMs for each workflow
- ❌ Workflow-specific orchestrators
- ❌ Hardcoding workflow logic in PM

**Implementation:**
```python
# Good: Generic PM with workflow detection
def create_project_manager(company_profile, checkpointer, storage, channel):
    # PM with all specialists (current workflows + future)
    subagents = [
        specialist_1,  # Workflow A
        specialist_2,  # Workflow B
        specialist_3,  # Shared across workflows
    ]
```

---

### 2. Domain-Specific Specialists (NOT Workflow-Specific)

**Decision:** Specialists are organized by domain expertise, reusable across workflows.

**Guidelines:**
- Design specialists around domain knowledge (not workflow steps)
- Each specialist masters ONE domain (single responsibility)
- Specialists should be composable across multiple workflows
- Validate reusability: "Which other workflows need this specialist?"

**Examples:**
- ✅ **Taxonomy Specialist** - Reusable for: product onboarding, catalog management, compliance
- ✅ **Market Intelligence Specialist** - Reusable for: product onboarding, pricing updates, competitive analysis
- ❌ **Product Onboarding Specialist** - Tied to single workflow, not reusable

**Design Test:**
- If specialist name includes workflow name → redesign
- If specialist can't be used in 3+ workflows → too narrow

**Implementation:**
```python
# Good: Domain specialist
def create_taxonomy_specialist(storage):
    """Multi-system classification specialist.

    Reusable for:
    - Product onboarding (current)
    - Catalog organization (future)
    - Compliance mapping (future)
    """

# Bad: Workflow specialist
def create_product_onboarding_step2_specialist():
    """Specific to product onboarding workflow only."""
```

---

### 3. HITL at PM Level ONLY

**Decision:** Human-in-the-loop interrupts configured at PM level, not specialist level.

**Guidelines:**
- `interrupt_on` configured for PM's persistence tools
- Specialists analyze and return data (NO persistence, NO HITL)
- PM synthesizes all specialist outputs
- PM presents unified data to user for approval
- PM persists atomically after approval

**Rationale:**
- Single approval point with full context
- User sees complete picture before persistence
- Specialists stay focused on analysis
- Clean separation of concerns

**Implementation:**
```python
# PM configuration
interrupt_configs = {
    "save_product_family": True,  # HITL here
}

project_manager = create_deep_agent(
    tools=pm_tools,  # Persistence tools with HITL
    subagents=subagents,  # Specialists with NO HITL
    interrupt_on=interrupt_configs,
)
```

**Anti-Pattern:**
```python
# ❌ HITL at specialist level
specialist = {
    "tools": [analysis_tool, save_tool],  # NO persistence in specialists
    "tool_configs": {"save_tool": {"interrupt": True}},  # NO HITL config
}
```

---

### 4. Specialist Output Pattern

**Decision:** Specialists return structured Pydantic models, not tool invocations.

**Guidelines:**
- Each specialist defines domain-specific output model
- Models use Pydantic for type safety
- Specialists analyze and structure data
- PM consumes specialist outputs and synthesizes
- NO persistence in specialist outputs

**Implementation:**
```python
# Specialist output model
class TaxonomyClassificationDraft(BaseModel):
    internal_category: CategoryMatch | None
    google_product_category: GoogleCategoryMatch
    industries: list[IndustryMatch]
    classification_confidence: float

# Specialist returns data
def create_taxonomy_specialist(storage):
    return {
        "name": "taxonomy_specialist",
        "description": "Classifies products into taxonomies",
        "tools": [find_categories_tool, classify_industries_tool],
        "system_prompt": prompt,
        # Returns TaxonomyClassificationDraft
    }
```

---

### 5. Orchestration Patterns

**Decision:** Use sequential for dependencies, parallel for independent tasks.

**Guidelines:**

**Sequential (Phase N must complete before Phase N+1):**
- Use when Phase N+1 depends on Phase N outputs
- Example: Product architecture BEFORE content generation (needs structure)

**Parallel (Phases can run simultaneously):**
- Use when phases are independent
- Example: Taxonomy + Market Intelligence + Visual Assets (no dependencies)
- Significant performance improvement

**PM Responsibility:**
- Detect dependencies between specialists
- Orchestrate sequential/parallel execution
- Wait for all parallel tasks before proceeding
- Synthesize all outputs into unified structure

**Implementation Pattern:**
```python
# Phase 1: Sequential (must complete first)
architecture_result = delegate_to(product_architecture_specialist)

# Phase 2: Parallel (independent)
taxonomy_result, market_result, visual_result = parallel_delegate([
    taxonomy_specialist,
    market_intelligence_specialist,
    visual_assets_specialist,
])

# Phase 3: Sequential (needs Phase 2 data)
content_result = delegate_to(content_seo_specialist,
                              inputs=Phase2_results)

# Synthesis: PM combines all
final_input = synthesize_all_results(...)
```

---

### 6. Tool Design Principles

**Decision:** Tools are focused, reusable infrastructure shared across specialists.

**Guidelines:**
- **Single Responsibility:** Each tool does ONE thing well
- **Reusable:** Design for use by multiple specialists
- **Factory Pattern:** Use factories for dependency injection
- **Storage Injection:** Tools receive storage adapter, not hardcoded
- **No HITL:** Tools perform operations, PM handles approval

**Tool Categories:**

**Analysis Tools:**
- Read-only operations
- Data extraction and processing
- No persistence side effects

**Persistence Tools:**
- Write operations to database
- Owned by PM only
- Trigger HITL interrupts

**Platform Tools:**
- External API integrations
- Media download, messaging, etc.
- Optional based on channel

**Implementation:**
```python
# Good: Factory with storage injection
def create_find_categories_tool(storage: StorageInterface):
    @tool
    def find_relevant_categories(product_name: str, description: str):
        """Search internal category hierarchy."""
        return storage.search_categories(product_name, description)
    return find_relevant_categories

# Good: Focused, reusable
@tool
def assess_image_quality(image_path: str) -> dict:
    """Assess single image quality for ecommerce."""
    # Resolution, aspect ratio, file size checks
    return quality_metrics

# Bad: Too broad, does everything
@tool
def process_product_complete(product_data: dict):
    """Analyzes, classifies, generates content, AND persists."""
    # ❌ Multiple responsibilities
```

---

### 7. Atomic Persistence Strategy

**Decision:** All persistence operations are atomic (all-or-nothing transactions).

**Guidelines:**
- Group related database operations into single transaction
- Rollback on ANY failure (no partial data)
- Return detailed result with all generated IDs
- Use retry logic for transient failures
- Centralized error classification

**Pattern:**
```python
async def save_domain_entity_atomic(storage, entity_input):
    """Atomically persist entity across N tables."""
    async with atomic_transaction(storage) as client:
        # Table 1: Parent entity
        parent_id = await client.insert("parent_table", parent_data)

        # Table 2-N: Related entities
        for related in entity_input.related_items:
            await client.insert("related_table", related_data)

        # Automatic triggers: audit_log, history tables

        # All succeed or all rollback

    return PersistenceResult(
        success=True,
        entity_id=parent_id,
        related_ids=[...],
    )
```

**Benefits:**
- Data integrity guaranteed
- No orphaned records
- Easy error recovery
- Clear success/failure states

---

### 8. Prompt Engineering Standards

**Decision:** Prompts are versioned artifacts with strict structure.

**Guidelines:**
- Store prompts in `agents/src/autifyme_agents/prompts/`
- Use `.prompt` extension (plain text templates)
- Load via `prompt_loader.py` (supports formatting)
- No Python code in prompts (logic stays in code)
- Use XML structure for complex prompts
- Right altitude: orchestrators get workflow view, specialists get domain focus

**Hierarchy-Specific Prompting:**

**PM Level (Orchestrator):**
- Workflow detection and routing
- Specialist delegation instructions
- Synthesis guidelines
- HITL presentation format
- High-level decision making

**Specialist Level (Domain Expert):**
- Domain-specific analysis instructions
- Tool usage guidelines
- Output structure requirements
- Quality standards
- NO workflow orchestration

**Structure:**
```
prompts/
├── project_manager.prompt          # Main PM (generic, all workflows)
├── basic_project_manager.prompt    # Legacy cataloging PM
└── specialists/
    ├── taxonomy_specialist.prompt
    ├── market_intelligence_specialist.prompt
    └── ...
```

**Template Format:**
```
# Specialist Name

You are the **Domain Expert** for {company_name}.

## Your Mission
[Clear, focused domain responsibility]

## Your Tools
[Tool descriptions]

## Output Format
[Pydantic model structure]

## Quality Standards
[Domain-specific quality criteria]
```

---

### 9. Model Configuration Strategy

**Decision:** Standardized models for optimal caching and cost efficiency.

**Guidelines:**

**Default Model:** `gpt-4.1-mini`
- Use for: All orchestration, analysis, generation (non-vision)
- Rationale: 75% prompt caching discount (best available)
- Temperature: 0.2 for orchestration, 0.7 for creative content

**Vision Model:** `gpt-5-mini`
- Use for: Image analysis ONLY
- Rationale: Superior vision capabilities
- Temperature: 0.0 for deterministic analysis

**Configuration:**
```python
# PM and specialists
model = "gpt-4.1-mini"
temperature = 0.2  # Orchestration/analysis

# Creative content generation
model = "gpt-4.1-mini"
temperature = 0.7  # More variety

# Image analysis
model = "gpt-5-mini"
temperature = 0.0  # Deterministic
```

**Cost Optimization:**
- System prompts (1024+ tokens) cached automatically
- 75% discount on cached tokens (gpt-4.1-mini)
- Subsequent workflow invocations: ~30% of initial cost
- High-volume operations: significant savings

---

### 10. Data Model Design

**Decision:** Type-safe Pydantic models for all data transfer.

**Guidelines:**

**Specialist Output Models:**
- One model per specialist (domain-specific)
- Suffix: `*Draft` (indicates pre-persistence)
- Include confidence scores
- Nested models for complex structures

**Persistence Input Models:**
- One model per workflow persistence operation
- Complete data package (all tables)
- Strict validation rules
- Clear field documentation

**Structure:**
```python
# Specialist output
class TaxonomyClassificationDraft(BaseModel):
    """Output from taxonomy specialist."""
    internal_category: CategoryMatch | None
    google_product_category: GoogleCategoryMatch
    industries: list[IndustryMatch]
    classification_confidence: float

# Persistence input
class ProductFamilyInput(BaseModel):
    """Complete product family for atomic persistence."""
    product_group_id: str
    name: str
    variant_axes: list[VariantAxisInput]
    products: list[ProductSKUInput]
    images: list[ProductImageInput]
    # ... all related entities
```

**Benefits:**
- Type safety at development time
- Runtime validation
- Clear contracts between components
- Self-documenting code

---

## Design Process Guidelines

### 1. Production-Grade from Day One

**Principle:** No MVP shortcuts, build enterprise-grade from start.

**Checklist:**
- ✅ Error handling and retry logic
- ✅ Atomic transactions
- ✅ Type-safe models
- ✅ Comprehensive prompts
- ✅ Observability (logging, tracing)
- ✅ Recovery mechanisms
- ✅ Verification at each step

**NOT:**
- ❌ "We'll add error handling later"
- ❌ "This is just MVP, we'll refactor"
- ❌ Partial implementations
- ❌ Skipping quality standards

---

### 2. Domain Research Before Design

**Process:**
1. **Enumerate all options** - Research thoroughly
2. **Analyze trade-offs** - Honest pros/cons for each
3. **Recommend best path** - Clear rationale
4. **Validate reusability** - "Which workflows need this?"

**Questions to Answer:**
- What domain expertise is needed?
- How does this compose with existing specialists?
- Which workflows will use this?
- What data needs to be persisted?
- What are the quality standards?
- Where are dependencies between components?

---

### 3. Clean Separation of Concerns

**Principle:** Clear boundaries between layers.

**Layers:**

**PM Layer (Orchestration):**
- Workflow detection
- Specialist delegation
- Result synthesis
- HITL presentation
- Atomic persistence

**Specialist Layer (Domain Analysis):**
- Domain-specific analysis
- Tool invocation
- Structured output
- NO persistence
- NO HITL

**Tool Layer (Infrastructure):**
- Focused operations
- Reusable utilities
- Storage abstraction
- NO business logic

**Persistence Layer (Data):**
- Atomic transactions
- Error classification
- Retry logic
- Audit trails

**Boundaries:**
- Specialists call tools (not directly to storage)
- PM calls specialists (not directly to tools)
- Tools use storage adapters (not direct DB)
- Persistence tools owned by PM only

---

### 4. Extensibility Built-In

**Principle:** Design for future workflows, not just current one.

**Guidelines:**
- Generic PM design (not workflow-specific)
- Domain specialists (reusable across workflows)
- Workflow detection in PM prompt
- Add specialists/tools as workflows grow
- Keep core pattern consistent

**Adding New Workflow:**
1. Identify domain specialists needed
2. Check existing specialists (reuse if possible)
3. Create new domain specialists if gaps exist
4. Create workflow-specific persistence tool
5. Update PM prompt with workflow detection
6. Add persistence tool to PM's toolkit
7. Configure HITL for new persistence tool

**Pattern Stays Same:**
- PM detects intent
- PM delegates to specialists
- PM synthesizes results
- PM presents for approval
- PM persists atomically

---

## Common Anti-Patterns to Avoid

### 1. Workflow-Specific Specialists
❌ **Bad:** Creating specialists tied to single workflow
✅ **Good:** Domain specialists reusable across workflows

### 2. HITL at Specialist Level
❌ **Bad:** Specialists with persistence tools and HITL
✅ **Good:** PM owns all persistence and HITL

### 3. Multiple PMs per Workflow
❌ **Bad:** Separate PM for each workflow
✅ **Good:** Single generic PM orchestrates all

### 4. Direct Tool-to-Database
❌ **Bad:** Tools accessing database directly
✅ **Good:** Tools use storage adapters

### 5. Partial Persistence
❌ **Bad:** Saving to some tables, failing on others
✅ **Good:** Atomic all-or-nothing transactions

### 6. Hardcoded Prompts
❌ **Bad:** Prompt text in Python code
✅ **Good:** Versioned .prompt files with loader

### 7. Mixed Responsibilities
❌ **Bad:** Single tool doing analysis + classification + persistence
✅ **Good:** Focused tools, each with single responsibility

### 8. MVP Mindset
❌ **Bad:** "We'll add quality later"
✅ **Good:** Production-grade from day one

---

## Validation Checklist

Before finalizing domain design, validate:

### Architecture
- [ ] Specialists are domain-specific (not workflow-specific)
- [ ] Each specialist reusable in 3+ workflows
- [ ] HITL configured at PM level only
- [ ] PM synthesizes all specialist outputs
- [ ] Persistence is atomic (all-or-nothing)

### Specialist Design
- [ ] Single domain responsibility
- [ ] Returns Pydantic model
- [ ] No persistence operations
- [ ] Tools are reusable infrastructure
- [ ] Prompt stored in .prompt file

### Orchestration
- [ ] Sequential phases have dependencies documented
- [ ] Parallel phases are truly independent
- [ ] PM waits for all parallel before proceeding
- [ ] Synthesis logic in PM, not specialists

### Data Models
- [ ] Pydantic models for all data transfer
- [ ] Specialist outputs suffixed with `Draft`
- [ ] Persistence input is complete package
- [ ] Type-safe throughout

### Quality
- [ ] Error handling with retry logic
- [ ] Comprehensive logging
- [ ] Audit trails automatic
- [ ] Recovery mechanisms in place
- [ ] Verification at each step

### Extensibility
- [ ] PM design is generic (not workflow-specific)
- [ ] Specialists composable across workflows
- [ ] Clear workflow detection strategy
- [ ] Easy to add new workflows

---

## Reference Implementation

**Product Onboarding Domain** serves as the canonical reference:

**File Locations:**
```
agents/src/autifyme_agents/
├── workflows/
│   ├── project_manager.py              # Generic PM (reference)
│   └── basic_project_manager.py        # Legacy (for comparison)
├── specialists/
│   ├── product_architecture_specialist.py
│   ├── taxonomy_specialist.py
│   ├── market_intelligence_specialist.py
│   ├── visual_assets_specialist.py
│   └── content_seo_specialist.py
├── tools/
│   ├── universal_crud_tool.py          # Schema-driven CRUD (all tables)
│   └── schema_tools.py                 # Schema query tools
└── prompts/
    ├── project_manager.prompt          # Generic PM prompt
    └── specialists/
        └── *.prompt                     # Specialist prompts
```

**Documentation:**
- `PRODUCT_ONBOARDING_BUILD_SUMMARY.md` - Architecture and components
- `PRODUCT_ONBOARDING_COMPLETE_DESIGN.md` - Detailed design
- `MODEL_CONFIGURATION.md` - Model strategy

---

## Key Takeaways

1. **Single Generic PM** - One orchestrator for all workflows
2. **Domain Specialists** - Reusable expertise, not workflow steps
3. **HITL at PM Level** - Single approval point with full context
4. **Atomic Persistence** - All-or-nothing data integrity
5. **Sequential + Parallel** - Orchestrate based on dependencies
6. **Type-Safe Models** - Pydantic throughout
7. **Production-Grade First** - No shortcuts, build right from start
8. **Extensible Design** - Easy to add workflows without refactoring

---

**Version History:**
- v1.0.0 (2025-10-24): Initial guidelines based on product onboarding design
