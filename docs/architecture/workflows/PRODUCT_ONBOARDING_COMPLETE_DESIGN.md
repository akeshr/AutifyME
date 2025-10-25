# Product Onboarding: Complete Design Specification

**Date:** 2025-10-24
**Status:** Final Design - Ready for Implementation
**Architecture:** Production-Grade, Enterprise-Quality
**Purpose:** Foundation for all product-related workflows

---

## Executive Summary

### **Vision**
Product onboarding transforms raw user input (text + images) into a complete, multi-channel ready product family in the database. This serves as the **universal product foundation** for all downstream workflows: marketing campaigns, e-commerce channels, CRM, billing, inventory management.

### **Design Principles**
1. **Domain-Specific Specialists** - Reusable across workflows, not workflow-specific
2. **Database-Aligned** - Each specialist maps to specific database tables
3. **Production-Grade** - Full error handling, resilience, observability from day one
4. **Multi-Channel Ready** - Supports Google Shopping, Amazon, own website, offline catalogs
5. **Strategic HITL** - 4 validation points at critical decision moments
6. **Cost Transparent** - Track and report generation costs at every step

### **System Scope**
- **Input:** User text + multiple images via WhatsApp
- **Processing:** 5 domain specialists + PM orchestrator
- **Output:** Complete product family with variants, market positioning, professional assets, SEO metadata
- **Database:** Atomic persistence across 9 tables with full audit trail
- **Timeline:** ~90 seconds processing (excluding HITL wait time)

---

## System Architecture Overview

### **High-Level Flow**

```
User Input (WhatsApp)
   ↓
PM (DeepAgent) - Context Loading
   ↓
Phase 1: Product Architecture Specialist
   ↓
HITL 1: Variant Structure Validation
   ↓
Phase 2 (Parallel): Taxonomy + Market Intelligence + Visual Assets
   ↓
HITL 2: Visual Assets Approval
   ↓
Phase 3: Content & SEO Specialist
   ↓
HITL 3: Content & SEO Review
   ↓
PM Synthesis: UnifiedProductFoundation
   ↓
HITL 4: Final Unified Approval
   ↓
Atomic Database Persistence (9 tables)
   ↓
Success Response
```

### **Component Architecture**

```
┌────────────────────────────────────────────────────────┐
│          PROJECT MANAGER (DeepAgent)                   │
│  • Context management (store)                          │
│  • Specialist orchestration                            │
│  • HITL coordination                                   │
│  • Synthesis & error recovery                          │
└────────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┬───────────────┬───────────────┐
        ▼               ▼               ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│Product       │ │Taxonomy      │ │Market        │ │Visual        │ │Content &     │
│Architecture  │ │Specialist    │ │Intelligence  │ │Assets        │ │SEO           │
│              │ │              │ │              │ │              │ │Specialist    │
│Domain:       │ │Domain:       │ │Domain:       │ │Domain:       │ │Domain:       │
│Product       │ │Multi-system  │ │Strategic     │ │Image/Video   │ │Written       │
│Structure     │ │Classification│ │Positioning   │ │Creation      │ │Content +     │
│              │ │              │ │              │ │              │ │Discoverability│
│              │ │              │ │              │ │              │ │              │
│DB Tables:    │ │DB Tables:    │ │DB Tables:    │ │DB Tables:    │ │DB Tables:    │
│• families    │ │• categories  │ │• industries  │ │• product_    │ │• marketing_  │
│• products    │ │• google_cat  │ │• family_     │ │  images      │ │  content     │
│• variant_axes│ │• tags        │ │  industries  │ │              │ │• SEO fields  │
│• variant_vals│ │              │ │• customer_   │ │              │ │• schema.org  │
│• prod_var_val│ │              │ │  segments    │ │              │ │              │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

---

## Domain Specialist Specifications

### **Specialist 1: Product Architecture Specialist**

**Domain:** Understanding and structuring physical product reality - specs, variants, SKU architecture

**Database Tables (Writes To):**
- `product_families` - parent product concept
- `products` - individual SKU records
- `variant_axes` - variant dimensions
- `variant_values` - specific values per axis
- `product_variant_values` - M:N junction

**Responsibilities:**
1. Product Specification Extraction (vision analysis, specs from images/text)
2. Variant Structure Design (detect dimensions, calculate combinations)
3. SKU Architecture (naming patterns, uniqueness)
4. Pricing Structure (base + adjustments + bulk tiers)
5. Completeness Validation (missing fields, confidence scoring)

**Tools (3):**
- `analyze_product_multimodal` - Vision API multimodal analysis
- `calculate_sku_combinations` - Variant math with compatibility rules
- `generate_sku_pattern` - SKU string generation

**Inline Logic:**
- Variant detection from user text
- Compatibility rules (28mm neck only with certain capacities)
- Industry-specific rules (pharma = amber bottles only)
- Pricing strategy per segment

**Reusable In:** Product Onboarding, Product Update, Competitive Analysis, Quality Control, Bulk Import

---

### **Specialist 2: Taxonomy Specialist**

**Domain:** Multi-system classification and categorization

**Database Tables (Writes To):**
- `categories` - internal hierarchical taxonomy
- `google_product_category` field in product_families
- `custom_attributes` JSONB
- Tags

**Responsibilities:**
1. Internal Category Mapping (hierarchical tree traversal)
2. Google Product Category (6000+ taxonomy search)
3. Amazon Category Mapping (if applicable)
4. Schema.org Type Selection
5. Attribute Standardization (capacity vs volume vs size)
6. Tag Strategy (food-grade, BPA-free, certifications)
7. Faceted Navigation Design (filterable attributes)

**Tools (3):**
- `map_to_internal_category` - Internal taxonomy matching
- `find_google_product_category` - Google taxonomy search
- `standardize_attributes` - Attribute normalization

**Inline Logic:**
- Tag generation (industry-specific, material-specific, compliance)
- Facet design (discrete vs range facets)
- Amazon category mapping logic

**Reusable In:** Product Onboarding, Product Update, Catalog Organization, Bulk Import, Google Shopping Export, Amazon Listing

---

### **Specialist 3: Market Intelligence Specialist**

**Domain:** Strategic market positioning and customer segment analysis

**Database Tables (Writes To):**
- `industries` (reads NAICS)
- `product_family_industries` - M:N mapping
- `customer_segments` - B2B/B2C/D2C profiles

**Responsibilities:**
1. Industry Identification (NAICS taxonomy matching)
2. Industry Use Case Mapping (juice bottles vs medicine bottles)
3. Customer Segment Analysis (B2B Enterprise, D2C Brands)
4. Value Proposition Mapping (per segment)
5. Pain Point Identification (per segment)
6. Messaging Strategy (tone, channels per segment)
7. Competitive Positioning

**Tools (3):**
- `find_relevant_industries` - NAICS matcher
- `analyze_customer_segments` - Segment fit analyzer
- `analyze_competitive_positioning` - Competitor mapper

**Inline Logic:**
- Use case generation (product + industry → specific uses)
- Value prop mapping (segment-aware benefits)
- Tone selection (professional for B2B, aspirational for D2C)
- Channel strategy (LinkedIn for B2B, Instagram for D2C)

**Reusable In:** Product Onboarding, Marketing Campaign, Company Strategy, Market Research, Sales Enablement, CRM Segmentation

---

### **Specialist 4: Visual Assets Specialist**

**Domain:** Image and video creation, enhancement, and management

**Database Tables (Writes To):**
- `product_images` with complete metadata

**Responsibilities:**
1. Image Quality Assessment (1-10 scoring)
2. Enhancement vs Regeneration Decision (quality threshold-based)
3. Image Enhancement (background removal, lighting improvement)
4. Professional Shot Generation (multi-angle, studio lighting)
5. Style Consistency (match existing catalog)
6. Channel-Appropriate Formatting (web, print, social)
7. Image Metadata Management (alt text, dimensions, generation metadata)
8. Primary Image Selection (hero shot)

**Tools (4):**
- `analyze_image_quality` - Vision-based quality scorer
- `enhance_image` - AI enhancement (Imagen 3)
- `generate_professional_shot` - AI generation (multi-angle)
- `format_for_channel` - Resize/crop for different channels

**Inline Logic:**
- Decision tree: 8-10 score = use as-is, 5-7 = enhance, 1-4 = regenerate
- Style consistency check (compare with existing catalog)
- Primary selection (prefer front view product shot)
- Cost tracking (enhancement ~$0.02, generation ~$0.03)

**Reusable In:** Product Onboarding, Marketing Campaign, Product Update, Catalog Refresh, Multi-Channel Export, Print Catalog

---

### **Specialist 5: Content & SEO Specialist**

**Domain:** Written content creation and search engine optimization

**Database Tables (Writes To):**
- `marketing_content` - descriptions, meta tags, schema.org
- SEO fields in `product_families` (url_slug)

**Responsibilities:**
1. Product Description Generation (brand voice, keyword-aware)
2. Feature Highlights (5-8 bullets)
3. Benefit Statements (feature → benefit transformation)
4. Keyword Research (competitive analysis)
5. SEO Metadata Generation (URL slug, meta title/description)
6. Schema.org Markup (Product, Offer, Brand, Organization)
7. Alt Text Enhancement (SEO keywords + descriptive)
8. Competitive SEO Analysis

**Tools (4):**
- `generate_product_content` - LLM content generation
- `research_keywords` - Competitive keyword analysis
- `generate_schema_markup` - JSON-LD builder
- `optimize_meta_tags` - CTR-focused meta optimization

**Inline Logic:**
- URL slug generation (lowercase, hyphens, unique)
- Keyword integration (natural, not stuffing)
- Brand voice application (from company intelligence)
- Tone selection (per target segment)

**Reusable In:** Product Onboarding, Marketing Campaign, Product Update, Website SEO Audit, Blog Content, E-commerce Listing

---

## PM Orchestration Design

### **PM Critical Responsibilities**

**1. Context Management**
- Load from DeepAgents store: CompanyProfile, CompanyIntelligence, ExistingCatalog, ConversationHistory
- Inject context into specialist delegations
- Maintain state across HITL interrupts

**2. Intelligent Orchestration**
- Phase 1 (Sequential): Product Architecture MUST run first
- Phase 2 (Parallel): Taxonomy + Market Intelligence + Visual Assets simultaneously
- Phase 3 (Sequential): Content & SEO needs Phase 2 outputs
- Skip specialists if not applicable
- Retry failed specialists

**3. HITL Coordination**
- Present 4 HITL approval points in user-friendly format
- Handle Approve, Edit, Reject, Clarification actions
- Determine which specialist to re-engage based on edit type
- Track approval state

**4. Synthesis & Conflict Resolution**
- Combine 5 specialist outputs into UnifiedProductFoundation
- Resolve conflicts (Taxonomy vs Market Intelligence mismatches)
- Fill gaps, validate completeness

**5. Multi-Turn Conversation**
- Detect missing information
- Ask clarifying questions
- Wait for user response
- Resume workflow from interrupted phase

**6. Error Recovery**
- Retry failed specialists with adjusted inputs
- Handle low confidence with user validation
- Vision API timeout → compress image and retry
- Database conflict → rollback and retry

**7. Cost Tracking**
- Track costs per specialist
- Sum total cost
- Present transparency at HITL 4

**8. Atomic Persistence**
- Call `save_product_family_atomic` tool
- Handle transaction success/failure
- Return all created IDs

---

## HITL Points Design

### **HITL 1: Variant Structure Validation**
**When:** After Product Architecture Specialist
**Why Critical:** Prevents wasted compute if structure is wrong
**User Reviews:**
- Product family concept
- Variant axes and values
- SKU combinations
- Pricing structure
- Missing specs

**Actions:** ✅ Approve  ✏️ Edit Structure  ❌ Reject

---

### **HITL 2: Visual Assets Approval**
**When:** After Visual Assets Specialist (Phase 2)
**Why Critical:** Quality control + cost management
**User Reviews:**
- Enhanced/generated images
- Quality assessment
- Primary image selection
- Generation cost

**Actions:** ✅ Approve  ✏️ Regenerate  ↩️ Use Original

---

### **HITL 3: Content & SEO Review**
**When:** After Content & SEO Specialist (Phase 3)
**Why Critical:** Brand voice + SEO quality
**User Reviews:**
- Product description
- Feature bullets, benefits
- Meta title/description
- URL slug
- Keywords

**Actions:** ✅ Approve  ✏️ Edit Copy  🔄 Regenerate

---

### **HITL 4: Final Unified Approval**
**When:** After PM Synthesis
**Why Critical:** Last validation before database commit
**User Reviews:**
- Complete product record
- All specialists' outputs combined
- Total generation cost
- Database impact preview

**Actions:** ✅ Save to Database  ✏️ Edit Any Section  ❌ Cancel

---

## Data Models

### **Core Models**

**ProductArchitectureDraft:**
- family: ProductFamily
- variant_axes: List[VariantAxis]
- variant_values: List[VariantValue]
- sku_combinations: List[SKUCombination]
- sku_codes: List[str]
- images_metadata: List[ImageMetadata]
- confidence_score: float
- missing_fields: List[str]

**TaxonomyMapping:**
- category_id, category_path
- google_product_category
- amazon_browse_node (optional)
- schema_product_type
- attributes: Dict
- tags: List[str]
- facets: List[Facet]

**MarketPositioning:**
- industries: List[IndustryMatch]
- segments: List[CustomerSegment]
- value_propositions: Dict[str, List[str]]
- pain_points: Dict[str, List[str]]
- messaging_tone, preferred_channels
- competitors, positioning_matrix

**VisualAssets:**
- images: List[ProcessedImage]
- primary_image_url, primary_image_id
- channel_formats: Dict
- matches_catalog_style: bool
- total_cost: Decimal
- cost_breakdown: Dict

**ContentPackage:**
- product_description, feature_bullets, benefit_statements
- url_slug, meta_title, meta_description
- og_title, og_description
- keywords (primary, secondary, long-tail)
- schema.org JSON-LD (Product, Offer, Brand, Organization)
- enhanced_alt_texts: Dict

**UnifiedProductFoundation:**
- architecture: ProductArchitectureDraft
- taxonomy: TaxonomyMapping
- market_positioning: MarketPositioning
- visual_assets: VisualAssets
- content_package: ContentPackage
- metadata: UnifiedMetadata

---

## Database Integration

### **Atomic Transaction (9 Tables)**

**Order of Operations:**
1. `product_families` - Insert parent
2. `variant_axes` - Insert dimensions (if variants exist)
3. `variant_values` - Insert specific values
4. `products` - Insert N SKUs
5. `product_variant_values` - Insert M:N junctions
6. `product_family_industries` - Insert industry mappings
7. `customer_segments` - Insert segment profiles
8. `product_images` - Insert with complete metadata
9. `marketing_content` - Insert descriptions, meta, schema.org

**Plus Automatic (via triggers):**
- `product_price_history` - Initial price record
- `product_inventory_history` - Initial inventory record
- `audit_log` - Change tracking entries

**Rollback Strategy:**
All operations in single transaction - any failure rolls back everything.

---

## Error Handling & Resilience

**Specialist Errors:**
- Low confidence → Ask user for missing info
- Tool failure → Retry with adjusted input (3 attempts)
- Vision API timeout → Compress image, retry

**Database Errors:**
- Duplicate SKU → Regenerate with suffix
- Duplicate URL slug → Append variant identifier
- Foreign key violation → Rollback, log, retry
- Transaction failure → Complete rollback, user notification

**User Actions:**
- HITL rejection → Cancel workflow
- HITL edit → Re-delegate to relevant specialist
- Multi-turn clarification → Resume from interrupted phase

---

## Multi-Turn Conversation

**Pattern:**
1. Specialist detects missing information
2. PM saves partial data to state
3. PM asks clarifying questions
4. PM marks conversation phase as "awaiting_clarification"
5. User responds (next message)
6. PM extracts new info, merges with partial data
7. PM continues workflow from saved phase

**State Preservation:**
- Thread-level state in DeepAgents
- Partial specialist outputs saved
- Current phase tracked
- User edits accumulated

---

## Cost Tracking

**Components:**
- Vision API: ~$0.01 per image
- Image Enhancement: ~$0.02 per image
- Image Generation: ~$0.03 per image
- LLM calls: tracked via LangSmith

**Transparency:**
- Cost accumulated per specialist
- Total shown at HITL 4
- Breakdown available (enhancement vs generation)

**Per Product Estimate:**
- Base (2 images, vision only): ~$0.02
- Standard (2 enhanced + 1 generated): ~$0.07
- Premium (3 generated angles): ~$0.11

---

## Reusability Matrix

| Specialist | Product Onboarding | Product Update | Marketing Campaign | Competitive Analysis | Bulk Import | SEO Audit |
|------------|-------------------|----------------|-------------------|---------------------|-------------|-----------|
| Product Architecture | ✓ | ✓ | - | ✓ | ✓ | - |
| Taxonomy | ✓ | ✓ | - | - | ✓ | ✓ |
| Market Intelligence | ✓ | ✓ | ✓ | ✓ | - | - |
| Visual Assets | ✓ | ✓ | ✓ | ✓ | - | - |
| Content & SEO | ✓ | ✓ | ✓ | - | ✓ | ✓ |

---

## Implementation Readiness Checklist

**Design Complete:**
- [x] 5 Specialists specified (domain, responsibilities, tools, reusability)
- [x] PM orchestration logic defined
- [x] 4 HITL points designed
- [x] Data models specified (Pydantic)
- [x] Database integration mapped (9 tables)
- [x] Error handling strategy defined
- [x] Multi-turn conversation pattern designed
- [x] Cost tracking approach defined

**Ready for Implementation:**
- [ ] Week 1: Database tools + Product Architecture Specialist
- [ ] Week 2: Parallel - 4 specialists (Taxonomy, Market Intel, Visual, Content/SEO)
- [ ] Week 3: PM orchestration + HITL workflows + WhatsApp integration
- [ ] Week 4: Production testing + deployment

---

**Last Updated:** 2025-10-24
**Next Document:** Implementation Plan (phased roadmap with dependencies)
