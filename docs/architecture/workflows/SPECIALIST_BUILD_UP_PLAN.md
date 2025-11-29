# Specialist Build-Up Integration Plan

**Created:** October 28, 2025
**Last Updated:** November 29, 2025
**Status:** Phase 2G Complete - Ready for Phase 3 (Taxonomy Specialist Integration)
**Strategy:** Incremental build-up - add specialists one by one, test each before adding next

---

## Executive Summary

**Goal:** Integrate all domain specialists into the Intelligent PM, enabling full product onboarding workflow.

**Approach:**
1. Perfect minimal PM core (done)
2. Add specialists ONE BY ONE in dependency order
3. Test end-to-end after each integration
4. PM synthesizes all specialist outputs before HITL approval

**Current State:** 1 of 7 production specialists integrated (Product Architecture)

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

## Pending: Database Infrastructure

### Product Data Model v2 (PENDING IMPLEMENTATION)

**Status:** Design Complete - Ready for Implementation
**Document:** `docs/architecture/database/PRODUCT_DATA_MODEL_V2.md`
**Estimated Effort:** 15-20 hours

**Overview:**
Universal product data model for Indian MSMEs supporting all business types (manufacturers, assemblers, traders) and all sales channels (B2B, D2C, online, offline).

**Schema Summary (22 Tables across 9 Domains):**

| Domain | Tables | Purpose |
|--------|--------|---------|
| Product Master | products, product_families, product_categories | Core product data |
| Variants | variant_axes, variant_values, product_variant_values | Product variations |
| UoM | uom, uom_conversion, product_uom_conversion | Unit handling |
| BOM | bom, bom_lines | Manufacturing recipes |
| Packaging | packaging_configs | Logistics packaging |
| Pricing | price_lists, product_prices, customer_prices | Multi-currency pricing |
| Inventory | locations, batches, inventory, inventory_transactions | Stock management |
| Suppliers | suppliers, supplier_products | Procurement |
| Digital Assets | assets, product_assets, asset_composition_rules | AI image composition |

**Key Design Decisions:**
- SKU-level BOM for variant flexibility
- Hybrid BOM: fixed + configurable products
- Multi-currency pricing with tax-inclusive/exclusive flag
- AI image composition via `composition_asset_id` on variant_values
- HSN code + GST rate for Indian tax compliance
- Inventory planning (reorder_point, safety_stock)

**Implementation Tasks:**
- [ ] Create Supabase migrations for all 22 tables
- [ ] Seed UoM and category reference data
- [ ] Update Pydantic models in `schemas/`
- [ ] Integrate with existing specialists (Product Architecture, Taxonomy)
- [ ] Update `read_data` tool for new schema

**Dependencies:**
- Blocks: Full product onboarding workflow
- Affects: All product-related specialists

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

**Total Completed:** ~70 hours

---

## Current Integration Status

### PM Configuration
- **Model:** gemini-2.5-flash (temperature=0.5)
- **Tools:** platform_media, inspect_schema, image_analysis, read_data
- **Subagents:** product_architecture_specialist only

### Specialists Available (Code Complete)

| Specialist | Code | PM Integration | Status |
|------------|------|----------------|--------|
| Product Architecture | Ready | **Integrated** | Active |
| Taxonomy | Ready | Pending | Phase 3 |
| Market Intelligence | Ready | Pending | Phase 4 |
| Visual Assets | Ready | Pending | Phase 5 |
| Content SEO | Ready | Pending | Phase 6 |
| Marketing Content | Ready | Pending | Phase 7+ |
| Cataloging (Legacy) | Ready | Deprecated | Archived |

---

## Upcoming Phases

### Phase 3: Taxonomy Specialist (3-4 hours)

**Goal:** Multi-system classification (internal + Google + NAICS)

**Tasks:**
1. Verify tool integration (classify_into_industries, find_relevant_categories)
2. Test in isolation (B2B packaging, B2C products, multi-industry)
3. Add to PM subagents list
4. Update PM prompt with taxonomy delegation
5. Test parallel execution with Product Architecture

**Success Criteria:**
- PM delegates to both specialists
- Returns TaxonomyClassificationDraft
- Google Product Category mapped

---

### Phase 4: Market Intelligence Specialist (3-4 hours)

**Goal:** Price positioning and customer segmentation

**Tasks:**
1. Verify tools (analyze_price_positioning, identify_customer_segments)
2. Test with/without price input
3. Add to PM (no storage dependency)
4. Enable 3-specialist parallel execution

---

### Phase 5: Visual Assets Specialist (3-4 hours)

**Goal:** Image organization and quality assessment

**Tasks:**
1. Verify tools (assess_quality, organize_images)
2. Test with various image sets
3. Add to PM

---

### Phase 6: Content SEO Specialist (4-5 hours)

**Goal:** Product descriptions and SEO optimization

**Tasks:**
1. Verify tools (generate_descriptions, optimize_seo)
2. Test with Product Architecture + Market Intelligence input
3. Add to PM (sequential after other specialists)

---

### Phase 7-11: Marketing Campaign Specialists (15-20 hours)

**Goal:** Full marketing workflow capability

**Specialists:**
- Ad Copy Specialist (Phase 7)
- Audience Intelligence Specialist (Phase 8)
- Campaign Strategy Specialist (Phase 9)
- Platform Adaptation Specialist (Phase 10)
- Creative Assets Specialist (Phase 11)

---

### Phase 12: Final Integration (4-6 hours)

**Goal:** Full product onboarding workflow

**Tasks:**
1. PM synthesizes ALL specialist outputs
2. Single HITL approval point
3. Atomic persistence of complete ProductFamilyInput
4. End-to-end testing with real products

---

## Success Metrics

- [ ] All 7 production specialists integrated
- [ ] PM orchestrates parallel/sequential execution correctly
- [ ] Single HITL approval for complete product family
- [ ] End-to-end workflow under 2 minutes
- [ ] Test coverage for all specialist combinations

---

**Version History:**
- v2.0.0 (2025-11-25): Streamlined doc - archived detailed phase notes (3943 -> 180 lines)
- v1.0.0 (2025-10-28): Initial plan
