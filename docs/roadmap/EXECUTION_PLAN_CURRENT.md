# Current Execution Plan - Product Onboarding System

**Date:** 2025-10-23
**Status:** 🚀 ACTIVE EXECUTION
**Current Phase:** Week 1 - Product Intelligence Specialist
**Prerequisites:** ✅ Database schema implemented, ✅ PAVISHA data populated, ✅ Market research complete

---

## Executive Summary

**Objective:** Build production-ready product onboarding system for PAVISHA PET INDUSTRIES to catalog 200+ SKUs across 7 product families with complete marketing intelligence.

**Approach:** Systematic implementation following 10-day development plan with ultrathink analysis and REPL verification at every step.

**Success Criteria:**
- ✅ Database normalized schema implemented (DONE)
- ✅ Company and market intelligence populated (DONE)
- 🔄 Pydantic models aligned with new schema (IN PROGRESS)
- ⏳ Product intelligence specialist operational
- ⏳ Variant generation tools functional
- ⏳ Marketing content generation ready
- ⏳ End-to-end workflow tested with real PAVISHA products

---

## Current Status (2025-10-23)

### ✅ Completed (Phase 0: Foundation)
1. **Database Schema** - All 14 tables created via Supabase migrations
   - Categories (8 records: 2 root + 6 subcategories)
   - Product Families (7 records: Bottles, Fridge Bottles, Kids Bottles, Jars, Cans, Preforms, Lids)
   - Variant Axes (24 axes across 7 families)
   - Variant Values (102 values total)
   - Sample Products (13 SKUs with variant linkages)

2. **Company Data** - PAVISHA profile complete
   - Company profile with certifications (IS:12252, FSSAI, BPA-free)
   - Company intelligence with market positioning
   - Competitor analysis (Milton, Cello, Tupperware, Bikaner Polymers)
   - Pricing strategy (wholesale B2B focus, ₹3-68 range)

3. **Market Research** - Comprehensive analysis
   - India PET market: $1.31B (2025), 1.9% CAGR
   - Competitive landscape documented
   - Pricing benchmarks established
   - Target segments defined (B2B 70%, B2C 30%)

4. **Documentation**
   - ✅ DATABASE_SCHEMA_DESIGN.md (marked IMPLEMENTED)
   - ✅ PAVISHA_PRODUCT_CATALOG.md (7 product families)
   - ✅ PAVISHA_MARKET_ANALYSIS.md (competitor intel)
   - ✅ PRODUCT_ONBOARDING_DEVELOPMENT_PLAN.md (10-day roadmap)

### 🔄 In Progress (Week 1, Day 1)
- **Task:** Update Pydantic models to match new schema
- **File:** `agents/src/autifyme_agents/schemas/models.py`
- **Status:** Models need alignment with ProductFamily/VariantAxis/VariantValue structure

### ⏳ Next Up (Week 1, Days 2-7)
- Product Intelligence Specialist implementation
- Database persistence tools
- Variant generation logic
- Testing with PAVISHA products

---

## Week 1 Detailed Execution Plan

### Day 1: Update Pydantic Models (TODAY)
**Estimated:** 4 hours | **Actual:** TBD

**Objective:** Align data models with normalized database schema

**Tasks:**
1. **REPL Verification** - Test Pydantic v2 features
   ```python
   uv run python -c "from pydantic import BaseModel, Field; print(BaseModel.__version__)"
   ```

2. **Create New Models** in `schemas/models.py`:
   - `ProductFamily` - Parent product concept
   - `VariantAxis` - Dimension of variation (capacity, color, etc.)
   - `VariantValue` - Specific value for an axis
   - `ProductVariant` - Individual SKU (rename from `Product`)
   - `CustomerSegment` - B2B/B2C/D2C targeting
   - `ProductFamilyIndustry` - Industry targeting junction

3. **Update Existing Models**:
   - Keep `Product` for backward compatibility, add deprecation notice
   - Update `CompanyProfile` to match current schema
   - Keep `CatalogingResult` (department output)

4. **Validation**:
   - Verify Pydantic v2 compatibility
   - Test model serialization/deserialization
   - Run mypy type checking

**Success Criteria:**
- ✅ All new models created with proper field types
- ✅ Pydantic v2 ConfigDict used (not Config class)
- ✅ Field descriptions for LLM guidance
- ✅ Type hints accurate (UUID | None, not Optional[UUID])
- ✅ No mypy errors

**Files Modified:**
- `agents/src/autifyme_agents/schemas/models.py`

---

### Day 2: Build Product Intelligence Specialist (4 hours)
**Objective:** Extract comprehensive product data from images/text

**Tasks:**
1. **REPL Verification** - Test LangChain v1 structured output
   ```python
   uv run python -c "from langchain_core.output_parsers import PydanticOutputParser; ..."
   ```

2. **Create Specialist**:
   - File: `agents/src/autifyme_agents/specialists/product_intelligence_specialist.py`
   - Use `with_structured_output(ProductFamily)` for extraction
   - Multimodal: Accept both text descriptions AND images
   - Extract: name, description, material, base_price, category, custom_attributes

3. **Prompt Engineering** (per PROMPT_ENGINEERING_STANDARDS.md):
   - No Python code in prompts
   - XML structure for clarity
   - Canonical examples for PET packaging
   - Right altitude: Specialist-level detail

4. **Testing**:
   - Test with PAVISHA bottle image
   - Test with text description
   - Verify structured output matches schema

**Success Criteria:**
- ✅ Specialist extracts ProductFamily data accurately
- ✅ Handles both image and text inputs
- ✅ Structured output validated against Pydantic model
- ✅ No hallucinations in certifications/specifications

**Files Created:**
- `agents/src/autifyme_agents/specialists/product_intelligence_specialist.py`
- `agents/src/autifyme_agents/prompts/product_intelligence_prompt.py`

---

### Day 3: Database Persistence Tools (4 hours)
**Objective:** Tools for saving ProductFamily and variants to Supabase

**Tasks:**
1. **REPL Verification** - Test Supabase client operations
   ```python
   uv run python -c "from supabase import create_client; ..."
   ```

2. **Create Tools**:
   - `save_product_family(family: ProductFamily) -> UUID`
   - `save_variant_axis(axis: VariantAxis, family_id: UUID) -> UUID`
   - `save_variant_value(value: VariantValue, axis_id: UUID) -> UUID`
   - `link_product_to_variants(product_id: UUID, variant_value_ids: list[UUID])`

3. **Error Handling**:
   - Use ToolException for failures
   - Handle unique constraint violations (duplicate SKUs)
   - Validate foreign key references

4. **Testing**:
   - Test creating product family for "500ml PET Bottle"
   - Test variant axis creation (capacity, neck_finish, color)
   - Test variant value creation
   - Verify database state with Supabase MCP

**Success Criteria:**
- ✅ Tools save data correctly to Supabase
- ✅ Proper error handling with ToolException
- ✅ Foreign key relationships maintained
- ✅ Tool descriptions clear for LLM usage

**Files Created:**
- `agents/src/autifyme_agents/tools/product_family_tools.py`

---

### Day 4: Variant Generation Logic (6 hours)
**Objective:** Generate product SKUs from variant combinations

**Tasks:**
1. **REPL Verification** - Test itertools.product for Cartesian product
   ```python
   uv run python -c "import itertools; list(itertools.product([1,2], ['a','b']))"
   ```

2. **Create Tool**:
   - `generate_product_variants(family_id: UUID, generate_all: bool = True)`
   - Fetch variant axes and values for family
   - Generate Cartesian product of all values
   - Create SKUs: `{sku_prefix}-{value1_code}-{value2_code}-...`
   - Insert products with junction table links

3. **SKU Naming Strategy**:
   - Follow pattern: `PAV-BTL-500ML-28PCO-CLR`
   - Use variant_value.sku_code for construction
   - Ensure uniqueness (database constraint)

4. **Pricing Logic**:
   - Start with family.base_price
   - Apply variant_value.price_adjustment
   - Calculate final price per product

5. **Testing**:
   - Generate variants for "PET Bottles" family
   - Verify: 8 capacities × 3 neck finishes × 4 colors = 96 SKUs
   - Check SKU format correctness
   - Validate pricing calculations

**Success Criteria:**
- ✅ Cartesian product generation works correctly
- ✅ SKU naming follows standard pattern
- ✅ Price adjustments applied properly
- ✅ All products linked to correct variant values
- ✅ Database constraints respected (unique SKUs)

**Files Created:**
- `agents/src/autifyme_agents/tools/variant_generation_tools.py`

---

### Day 5: Integration Testing (4 hours)
**Objective:** End-to-end test with real PAVISHA product

**Tasks:**
1. **Test Scenario**: Catalog "500ml PET Bottle - Clear - 28mm PCO"
   - Input: Product image + text description
   - Expected: ProductFamily created, 3 variant axes, 96 SKUs generated

2. **Test Workflow**:
   a. Product Intelligence Specialist extracts data
   b. Save ProductFamily to database
   c. Create variant axes (capacity, neck_finish, color)
   d. Create variant values for each axis
   e. Generate all product variants
   f. Verify database state

3. **Validation**:
   - Check product_families table
   - Check variant_axes table
   - Check variant_values table
   - Check products table
   - Check product_variant_values junction table

4. **Error Testing**:
   - Test duplicate SKU handling
   - Test invalid foreign keys
   - Test malformed input data

**Success Criteria:**
- ✅ Full workflow completes without errors
- ✅ All 96 SKUs generated correctly
- ✅ Database relationships intact
- ✅ Error cases handled gracefully
- ✅ LangSmith traces show correct flow

**Files Modified:**
- `tests/integration/test_product_onboarding.py` (create)

---

### Days 6-7: Marketing Content Generation (8 hours)
**Objective:** Generate platform-specific content for products

**Tasks:**
1. **Create Specialist**:
   - File: `specialists/marketing_content_specialist.py`
   - Input: ProductFamily + CustomerSegment + Industry
   - Output: Platform-specific content (Instagram, LinkedIn, Facebook)

2. **Content Types**:
   - Instagram: Visual post with hashtags (B2C focus)
   - LinkedIn: Technical specs and B2B benefits
   - Facebook: Community engagement, applications
   - Website: SEO-optimized product descriptions

3. **Personalization**:
   - Use customer_segment.tone
   - Highlight relevant pain_points
   - Include industry-specific use cases

4. **Testing**:
   - Generate content for "PET Fridge Bottles" (B2C segment)
   - Generate content for "PET Preforms" (B2B segment)
   - Verify tone appropriateness
   - Check platform constraints (char limits, hashtag count)

**Success Criteria:**
- ✅ Content generated for all platforms
- ✅ Tone matches customer segment
- ✅ Platform constraints respected
- ✅ Industry use cases included
- ✅ No generic marketing fluff

**Files Created:**
- `agents/src/autifyme_agents/specialists/marketing_content_specialist.py`
- `agents/src/autifyme_agents/prompts/marketing_content_prompt.py`
- `agents/src/autifyme_agents/tools/marketing_content_tools.py`

---

## Week 2 Preview

### Phase 2: Department Integration (Days 8-10)
- Update Cataloging Department to use new specialists
- Integrate variant generation into workflow
- Add marketing content generation step
- End-to-end testing with HITL approval
- Production deployment

---

## Ultrathink Principles Applied

### 1. Deep Research Before Implementation
- ✅ Exhaustively researched market (6 web searches, competitor analysis)
- ✅ Verified pricing with real market data (Milton, Bikaner benchmarks)
- ✅ Documented all permutations (7 families × 3-4 axes × 3-5 values = 200+ SKUs)
- 🔄 Will verify LangChain v1 APIs with REPL before using

### 2. REPL Verification Mandatory
- **Before each implementation day:** Verify library capabilities
- **Test cases:** Pydantic v2 features, LangChain structured output, Supabase operations
- **Document findings:** Capture API signatures, gotchas, version-specific behavior

### 3. Architectural Integrity
- ✅ Maintained hexagonal architecture (tools at edges, core logic clean)
- ✅ Type safety with Pydantic models
- ✅ Separation of concerns (specialist → tools → storage)
- 🔄 Will follow PROMPT_ENGINEERING_STANDARDS.md strictly

### 4. Challenge and Iterate
- ✅ User corrected missing product lines (fridge bottles, kids bottles) - fixed immediately
- ✅ Pricing challenged - researched market and adjusted
- 🔄 Will validate each implementation with user before proceeding

### 5. Production-Grade from Start
- ✅ Error handling: ToolException pattern
- ✅ Observability: LangSmith tracing enabled
- ✅ Recovery: Database migrations for schema changes
- ✅ Verification: Test each component before integration

---

## Risk Mitigation

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| LangChain v1 alpha API changes | HIGH | HIGH | REPL verify before each use, pin versions, test frequently |
| Pydantic v2 breaking changes | MEDIUM | MEDIUM | Use ConfigDict, avoid deprecated patterns, test serialization |
| Supabase MCP instability | LOW | HIGH | Fallback to direct supabase-py client, error handling |
| Variant explosion (1000+ SKUs) | MEDIUM | MEDIUM | Batch inserts, progress tracking, pagination |

### Process Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Scope creep | MEDIUM | MEDIUM | Strict adherence to 10-day plan, defer non-essentials |
| Integration complexity | HIGH | MEDIUM | Test each component in isolation first |
| Data quality issues | MEDIUM | HIGH | HITL approval workflow, validation at every step |

---

## Success Metrics

### Week 1 Goals
- [ ] All 7 Pydantic models created and validated
- [ ] Product Intelligence Specialist extracts data accurately (>90% accuracy)
- [ ] Database tools save without errors
- [ ] Variant generation creates correct SKU count
- [ ] End-to-end test passes with real PAVISHA product

### Week 2 Goals (Preview)
- [ ] Cataloging Department uses new specialists
- [ ] HITL workflow approves ProductFamily before variant generation
- [ ] Marketing content generated for all platforms
- [ ] 10+ products onboarded successfully
- [ ] Production deployment ready

---

## Next Actions (Immediate)

### 🎯 TODAY: Day 1 - Update Pydantic Models

**Step 1: REPL Verification (15 min)**
```bash
# Verify Pydantic v2
uv run python -c "from pydantic import BaseModel, Field, ConfigDict; print('Pydantic OK')"

# Test UUID handling
uv run python -c "from uuid import UUID; from pydantic import BaseModel; class T(BaseModel): id: UUID | None = None; print(T(id='invalid'))"

# Test Decimal handling
uv run python -c "from decimal import Decimal; from pydantic import BaseModel; class T(BaseModel): price: Decimal; print(T(price='12.50'))"
```

**Step 2: Read Existing Code (15 min)**
- Read `agents/src/autifyme_agents/schemas/models.py` completely
- Understand current Product model usage
- Check if Product is imported anywhere else

**Step 3: Create New Models (2 hours)**
- Implement ProductFamily model
- Implement VariantAxis model
- Implement VariantValue model
- Implement ProductVariant model (new, not replacing Product yet)
- Implement CustomerSegment model
- Implement ProductFamilyIndustry model

**Step 4: Validation (30 min)**
- Run mypy: `uv run mypy agents/src/autifyme_agents/schemas/models.py`
- Test model instantiation with sample data
- Verify serialization: `model.model_dump()`, `model.model_dump_json()`

**Step 5: Documentation (30 min)**
- Add docstrings to all models
- Document field purposes
- Add examples in docstrings

---

## Documentation Consolidation Decision

### Keep (Essential)
1. ✅ **EXECUTION_PLAN_CURRENT.md** (this file) - Active execution guide
2. ✅ **PRODUCT_ONBOARDING_DEVELOPMENT_PLAN.md** - Detailed 10-day plan
3. ✅ **PAVISHA_PRODUCT_CATALOG.md** - Product reference data
4. ✅ **PAVISHA_MARKET_ANALYSIS.md** - Market intelligence
5. ✅ **IMPLEMENTATION_ROADMAP.md** - Will update with current status
6. ✅ **PRODUCT_SCALING_ROADMAP.md** - Future phases (bulk, multi-platform)

### Archive (Future reference)
- None at this time - all docs serve active purposes

### Update Required
- **IMPLEMENTATION_ROADMAP.md** - Mark foundation items complete, add new roadmap items

---

**Status:** Ready to begin Day 1 execution
**Next:** REPL verification of Pydantic v2 features
