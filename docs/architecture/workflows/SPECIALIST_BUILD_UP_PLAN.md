# Specialist Build-Up Integration Plan

**Created:** October 28, 2025
**Last Updated:** November 29, 2025
**Status:** Database Schema v2 Complete - Ready for Phase 3A (Minimal Catalog Specialist)
**Strategy:** Hybrid approach - minimal consolidation -> Image Studio -> full consolidation

---

## Executive Summary

**Goal:** Build autonomous product lifecycle management for Indian MSMEs.

**Architecture Evolution:**
```
Original: 7 narrow specialists (over-engineered)
    |
    v
Optimized: 2 domain specialists + shared tools (token-efficient)
```

**Why Domain-Driven Specialists (Not Workflow-Specific):**
- Add specialists when NEW DOMAINS emerge, not when new workflows appear
- Each specialist = domain expert with clear table ownership
- Currently 2 domains (Catalog, Operations) = 2 specialists
- Marketing domain will add 3rd specialist when needed
- Avoid over-engineering: don't pre-build specialists for future domains

**Token Economics Validates This Approach:**
- Fewer specialists = fewer PM orchestration handoffs
- 7 narrow specialists: ~24K tokens/workflow
- 2 domain specialists: ~13K tokens/workflow (45% savings)
- LLMs handle broader scope well; narrow specialists were over-engineered

**Token Analysis:**
```
7-Specialist Model:
- PM prompt: ~3K tokens
- Per specialist: ~2K tokens x 7 = 14K tokens
- PM orchestration overhead: ~1K per handoff x 6 = 6K tokens
- Total: ~24K tokens per workflow

2-Specialist Model:
- PM prompt: ~3K tokens
- Per specialist: ~4K tokens x 2 = 8K tokens (richer prompts)
- PM orchestration overhead: ~1K per handoff x 1 = 1K tokens
- Total: ~13K tokens per workflow

Savings: 45% token reduction
```

---

## Architectural Foundation (Completed)

### Intelligent PM Paradigm

**Key Insight:** Modern LLMs are highly capable - don't restrict them.

**Pattern Chosen:**
```
PM = "Intelligent Orchestrator"
- Analyzes images to understand context
- Has domain knowledge (B2B, packaging, products)
- Asks clarifying questions
- ENRICHES data before delegating to specialists

Specialists = "Deep Domain Experts"
- Receive enriched input from PM
- Focus on specialized analysis
- Return structured Pydantic outputs
```

**Why This Works:**
- PM understands intent from first message
- Specialists get rich context, not raw user input
- Better user experience (intelligent conversations)
- Faster workflows (PM makes smart decisions)

### Context Feeding Strategy (Option D: Hybrid)

**Decision:** Load lightweight base context at startup, query details on-demand.

**Implementation:**
- `PMBaseContext` loaded at PM construction
- Contains: `catalog_summary`, `taxonomy_tree`
- Refreshed periodically (catalog changes)
- PM uses `read_data` tool for detailed queries

**Benefits:**
- PM intelligent from message 1 (has base context)
- Scales (base = 1-2K tokens)
- Always fresh (details queried when needed)

---

## Current Architecture: Domain-Driven Specialists

**Principle:** One specialist per business domain. Add specialists as new domains emerge.

```
PM (Intelligent Orchestrator)
|
+-- Catalog Specialist (what we sell)
|   |-- products, product_families, product_uom_conversion  [CRUD]
|   |-- bom, bom_lines                                      [CRUD]
|   |-- price_lists, product_prices                         [CRUD]
|   |-- assets                                              [CRUD] (shared)
|   |-- product_assets, asset_composition_rules             [CRUD]
|   +-- uom                                                 [READ]
|
+-- Operations Specialist (how we get/store/ship)
|   |-- suppliers, supplier_products                        [CRUD]
|   |-- locations                                           [CRUD]
|   |-- batches, inventory, inventory_transactions          [CRUD]
|   |-- uom, uom_conversion                                 [CRUD]
|   +-- products                                            [READ]
|
+-- Marketing Specialist (future - how we promote)
    |-- campaigns, campaign_assets                          [CRUD]
    |-- social_posts, social_post_assets                    [CRUD]
    |-- marketing_templates                                 [CRUD]
    |-- assets                                              [CRUD] (shared)
    +-- products, product_assets                            [READ]
```

### Access Control Matrix

| Table | Catalog | Operations | Marketing (future) |
|-------|---------|------------|-------------------|
| products | CRUD | R | R |
| product_families | CRUD | - | - |
| product_uom_conversion | CRUD | - | - |
| bom, bom_lines | CRUD | - | - |
| price_lists, product_prices | CRUD | R | - |
| assets | CRUD | - | CRUD |
| product_assets | CRUD | - | R |
| asset_composition_rules | CRUD | - | R |
| suppliers, supplier_products | - | CRUD | - |
| locations | - | CRUD | - |
| batches, inventory | - | CRUD | - |
| inventory_transactions | - | CRUD | - |
| uom, uom_conversion | R | CRUD | - |

### What Happened to Original 7 Specialists

The original plan had 7 narrow specialists:
1. Product Architecture -> **Catalog Specialist**
2. Taxonomy -> **Catalog Specialist** (or PM tool)
3. Market Intelligence -> **Catalog Specialist** (or PM tool)
4. Visual Assets -> **Catalog Specialist + Image Studio tool**
5. Content SEO -> **Catalog Specialist** (or tool)
6. Marketing Content -> **Marketing Specialist** (future)
7. Creative Assets -> **Marketing Specialist + Image Studio tool**

**Why Consolidated:**
- Token overhead from PM orchestration (24K vs 13K per workflow)
- Most workflows spanned 2-3 specialists
- Didn't match human mental model
- Over-engineered for LLM capabilities

---

## Image Processing Strategy: Image Studio Tool

> **Detailed Design:** [IMAGE_STUDIO_TOOL.md](../tools/IMAGE_STUDIO_TOOL.md)

### Summary

**Decision:** Tool, not specialist. Image processing is a CAPABILITY, not a DOMAIN.

**Architecture:**
```
image_studio (pure processing) -> temp paths
    |
    v
Specialist self-reviews output (analyze job)
    |
    v
Specialist calls create_record (existing HITL)
    |
    v
User approves -> storage moves temp -> permanent
```

**Key Design Decisions:**

| Decision | Rationale |
|----------|-----------|
| Tool outputs to temp folder | No DB operations in tool - specialists use existing DB tools |
| Unified tool with job_type | One atomic tool: analyze, product_shot, lifestyle, composite, enhance |
| Specialist self-review | Validate quality before bothering user (max 2 iterations) |
| Reuse existing HITL | create_record already has HITL - add preview_image_path to payload |
| PM holds state for feedback | Specialists are stateless - PM provides context for regeneration |

**Job Types:**
- `analyze` - Extract visual attributes (colors, materials, style)
- `product_shot` - Clean catalog image (white bg, professional)
- `lifestyle` - AI-generated contextual scene with product
- `composite` - Layer-based composition (banners, social)
- `enhance` - Quality improvement (denoise, sharpen, upscale)

**Workflow Example:**
```
User sends product photo
    |
PM downloads -> /tmp/raw.jpg
    |
Specialist: image_studio(job_type="analyze") -> understand image
    |
Specialist: image_studio(job_type="product_shot") -> generate
    |
Specialist: image_studio(job_type="analyze") -> self-review output
    |
Specialist: create_record(table="assets", preview_image_path=...) -> HITL
    |
User approves -> asset persisted, linked to product
```

---

## Completed Phases Summary

| Phase | Name | Duration | Key Achievement |
|-------|------|----------|-----------------|
| 0 | Preparation | 2h | Identified integration issues, created plan |
| 1 | Intelligent PM Core | 15h | Base context loading, multimodal analysis, read_data tool |
| 2 | Product Architecture Specialist | 5h | First specialist integrated, CRUD operations |
| 2B | CRUD Enhancement | 8h | Schema-driven operations, OperationIntent pattern |
| 2C | Dynamic Schema CRUD | 11h | Table metadata, universal tool |
| 2D | Executable Schema | 8h | Business rules from metadata, 350 LOC removed |
| 2E | Transaction Support | 5h | Atomic operations with rollback |
| 2F | Access Control | 8h | Operation-scoped dynamic Pydantic schemas |
| 2G | Product Research | 8h | Web research tools (Tavily integration) |
| **2H** | **Database Schema v2** | **6h** | **18 tables, agent-critical metadata, v2.json** |
| **2I** | **Schema Tool Enhancement** | **4h** | **Constraints detail, valid_values, patterns** |

**Total Completed:** ~80 hours

### Database Schema v2 (COMPLETED)

**Status:** Migrations applied to Supabase, schema JSON updated

**Tables (18 across 7 domains):**

| Domain | Tables | Status |
|--------|--------|--------|
| Product (PIM) | products, product_families, product_uom_conversion | DONE |
| Manufacturing | bom, bom_lines | DONE |
| Pricing | price_lists, product_prices | DONE |
| Procurement | suppliers, supplier_products | DONE |
| Inventory | locations, batches, inventory, inventory_transactions | DONE |
| Assets (DAM) | assets, product_assets, asset_composition_rules | DONE |
| Master Data | uom, uom_conversion | DONE |

### Schema Enhancements (COMPLETED)

- [x] Agent-critical fields: valid_values, pattern, computed, element_type, jsonb_schema
- [x] TableSchema helper methods: get_enum_columns(), get_computed_columns(), get_pattern_columns()
- [x] inspect_schema tool: "constraints" detail type
- [x] v2.json with full enum values and business descriptions
- [x] Test coverage for all new functionality (444 tests passing)

---

## Current Integration Status

### PM Configuration
- **Model:** gemini-2.5-flash (temperature=0.5)
- **Tools:** platform_media, inspect_schema, image_analysis, read_data
- **Subagents:** product_architecture_specialist (to be consolidated into catalog_specialist)

### Tools Architecture

**Atomic, Powerful Tools:**
- `inspect_schema` - Schema introspection with constraints detail
- `read_data` - Query any table with filtering
- `create_record` - Validated inserts with business rules
- `update_record` - Validated updates with field-level permissions
- `delete_record` - Soft/hard delete with cascade handling
- `execute_transaction` - Atomic multi-operation commits

**Future Tools:**
- `image_studio` - AI-powered image processing
- `web_research` - Market intelligence gathering

---

## Upcoming Phases

### Execution Strategy: Hybrid Approach

**Rationale:** Balance architecture integrity with user value delivery.

The original Phase 3 (full consolidation) delays Image Studio by 8-10 hours. Analysis shows:
- Image Studio is a TOOL, not a specialist - works with any specialist
- BUT self-review pattern needs clear ownership for product imagery
- Minimal Catalog Specialist provides that ownership without full consolidation

**Execution Order:** 3A -> 5 -> 3B -> 4

| Phase | Hours | Cumulative | Deliverable |
|-------|-------|------------|-------------|
| 3A | 4-5h | 4-5h | Catalog Specialist (minimal) |
| 5 | 10-12h | 14-17h | Image Studio Tool |
| 3B | 4-5h | 18-22h | Full consolidation |
| 4 | 6-8h | 24-30h | Operations Specialist |

---

### Phase 3A: Minimal Catalog Specialist (4-5 hours)

**Goal:** Establish clear ownership for product imagery before Image Studio

**Why First:**
- Image Studio's self-review pattern requires ONE specialist to own product imagery
- 7 narrow specialists create ambiguous ownership (Visual Assets? Product Architecture?)
- Catalog Specialist provides clear boundary: "all product catalog operations"

**Tasks:**
1. [ ] Create Catalog Specialist prompt (products + assets + image responsibilities)
2. [ ] Configure table access control (products, product_families, assets, product_assets)
3. [ ] Wire into PM as primary product specialist (replace product_architecture_specialist)
4. [ ] Test basic product CRUD workflow
5. [ ] Document specialist-tool contract for Image Studio integration

**Scope Boundaries:**
- IN: Product CRUD, asset management, image processing ownership
- OUT: Full BOM/pricing integration, narrow specialist deprecation (deferred to 3B)

**Success Criteria:**
- Catalog Specialist can create products with associated assets
- Clear ownership for image_studio tool integration
- PM routes product image requests to Catalog Specialist

---

### Phase 5: Image Studio Tool (10-12 hours)

**Goal:** Implement unified image tool with self-review pattern

**Design Doc:** [IMAGE_STUDIO_TOOL.md](../tools/IMAGE_STUDIO_TOOL.md)

**Why After 3A:**
- Catalog Specialist owns product imagery (clear self-review ownership)
- Self-review pattern: Catalog Specialist calls image_studio twice (generate + analyze)
- Feedback iteration: PM routes user feedback to Catalog Specialist with context

**Tasks:**
1. [ ] Define Pydantic models for all job specs (ImageStudioInput, OutputSpec, etc.)
2. [ ] Implement job routing and validation
3. [ ] Merge existing image_analysis_tool into analyze job
4. [ ] Integrate background removal API (Remove.bg/Replicate)
5. [ ] Integrate enhancement APIs (Real-ESRGAN)
6. [ ] Implement lifestyle generation (Stability/SDXL)
7. [ ] Add temp file management with cleanup
8. [ ] Add preview generation for HITL
9. [ ] Update storage adapter for temp -> permanent move
10. [ ] Add review_context to HITL payload
11. [ ] Test self-review pattern with Catalog Specialist
12. [ ] Test feedback iteration flow

**User Value Delivered:**
- Phone photos -> professional catalog images
- Self-review ensures quality before user approval
- Feedback loop for adjustments ("make background cream")

---

### Phase 3B: Complete Consolidation (4-5 hours)

**Goal:** Finish specialist consolidation, realize full token savings

**Why After Image Studio:**
- Image Studio validates the consolidated architecture pattern
- Real usage data informs what to include vs. keep as tools
- Avoid over-engineering consolidation before validation

**Tasks:**
1. [ ] Expand Catalog Specialist prompt (add BOM, pricing, SEO capabilities)
2. [ ] Deprecate narrow specialists (Product Architecture, Visual Assets, Content SEO, etc.)
3. [ ] Update PM routing to use only Catalog Specialist for product domain
4. [ ] Migrate/archive narrow specialist tests
5. [ ] Verify 45% token reduction achieved
6. [ ] Update documentation

**Merged Capabilities (Full):**
- Product Architecture -> product definition, families, variants
- Visual Assets -> asset management (image processing via Image Studio tool)
- Content SEO -> product descriptions
- Pricing logic -> price lists, tiered pricing

**Success Criteria:**
- Single Catalog Specialist handles 80%+ of product workflows
- Token usage reduced ~45% compared to 7-specialist model
- All 444+ tests passing (with narrow specialist tests archived/migrated)

---

### Phase 4: Operations Specialist (6-8 hours)

**Goal:** Build Operations Specialist for supply chain

**Tasks:**
1. [ ] Create Operations Specialist prompt
2. [ ] Configure table access (suppliers, inventory, locations, batches)
3. [ ] Test supplier onboarding workflow
4. [ ] Test inventory operations (receive, transfer, adjust)

---

### Phase 6: Marketing Specialist (future)

**Goal:** Campaign and content creation

**Tables to add:**
- campaigns
- campaign_assets
- social_posts
- social_post_assets
- marketing_templates

**Capabilities:**
- Campaign planning
- Creative generation (uses Image Studio)
- Multi-platform adaptation
- Content scheduling

---

## Success Metrics

- [ ] Domain-driven specialists handle all product lifecycle operations
- [ ] Single specialist call for 80%+ of workflows (validates domain boundaries)
- [ ] Image Studio generates catalog-ready assets from phone photos
- [ ] Master assets reusable across catalog/marketing/website
- [ ] End-to-end workflow under 2 minutes
- [ ] All 444+ tests passing

---

**Version History:**
- v3.2.0 (2025-11-29): Hybrid execution strategy (3A -> 5 -> 3B -> 4), split Phase 3 into minimal (3A) and full consolidation (3B), prioritize Image Studio user value
- v3.1.0 (2025-11-29): Extracted Image Studio design to separate doc, added self-review pattern, stateless specialist considerations
- v3.0.0 (2025-11-29): Consolidated to 2-specialist model, added Image Studio design, marked Database Schema v2 complete
- v2.0.0 (2025-11-25): Streamlined doc - archived detailed phase notes (3943 -> 180 lines)
- v1.0.0 (2025-10-28): Initial plan
