# AutifyME Enterprise Database Schema Design

**Version:** 3.1.0
**Created:** October 23, 2025
**Status:** 🔄 Implementation Roadmap - Marketing Tables Pending
**Purpose:** Comprehensive enterprise-grade database architecture for all AutifyME workflows

---

## Executive Summary

This document defines the **complete enterprise database architecture** for AutifyME across all workflows and domains. The schema supports:

- ✅ **Product Onboarding - FULLY IMPLEMENTED** - Variant families, SKU architecture, multi-system taxonomy (14 tables, 64 products, 7 families)
- ❌ **Marketing Campaigns - DESIGN COMPLETE, NOT IMPLEMENTED** - Multi-platform orchestration, creative management, performance tracking (4 new tables + 2 table extensions needed)
- 🚀 **Platform Integration (Phase 3)** - 8 advertising platforms prioritized: Meta, Google Ads, Amazon, YouTube (Phase 1) → X, LinkedIn, TikTok (Phase 2+). Includes credentials, rate limiting, metrics, webhooks (7 new + 4 extended)
- ✅ **Infrastructure - PARTIALLY IMPLEMENTED** - Operational foundation, media management, thread tracking (20 tables implemented, recommendations need review)
- 🔮 **Future Workflows (Phase 4+)** - Inventory, CRM, Analytics (extensible foundation, requirements documented below)

**Design Principles:**
- **LangSmith-First Architecture** - LangSmith is source of truth for workflow tracing, learning, and observability
- **Normalized to 3NF** - No redundancy, referential integrity via foreign keys
- **Single-Tenant** - One company per database (simplified architecture)
- **Reusable Components** - Shared entities across workflows (customer_segments, industries, marketing_content)
- **Atomic Transactions** - All-or-nothing operations guarantee data integrity
- **Temporal Tracking** - Automatic history tables for price, inventory, audit changes
- **Extensible** - New workflows add tables without breaking existing schema
- **Hybrid Abstraction** - Generic models + JSONB extensions for platform-specific features

**Total Schema:**
- **34 Tables Currently Implemented** (20 infrastructure/framework, 14 product domain)
- **4 Marketing Tables Ready for Migration** (campaigns, campaign_products, campaign_assets, campaign_channels)
- **2 Table Extensions Needed** (customer_segments, marketing_content)
- **7 Platform Integration Tables (Phase 3)** - Future implementation
- **9 Automatic Triggers** for history and audit trails
- **LangSmith Integration** for workflow tracing and learning

**Implementation Priority:**
1. **Phase 1 (COMPLETE):** Product Onboarding - 14 tables, 5 specialists, atomic persistence ✅
2. **Phase 2 (NEXT):** Marketing Campaigns - 4 new tables + 2 extensions, 5 specialists, persistence tool
3. **Phase 3 (FUTURE):** Platform Integration - 7 tables for API credentials, rate limits, metrics
4. **Phase 4+ (FUTURE):** CRM, Inventory, Analytics - Requirements documented below

---

## Table Categories Overview

### Category 1: Infrastructure & System Tables (11 Tables)

Core platform functionality for operational requirements, framework support, and system operations.

**Architecture Note:** LangSmith is the source of truth for workflow tracing, learning, and observability. Infrastructure tables focus on operational needs that LangSmith cannot serve (real-time deduplication, HITL state, media lifecycle, thread metadata).

| Table | Purpose | Type |
|-------|---------|------|
| `companies` | Single-tenant company profile & system settings | Operational Config |
| `processed_messages` | Webhook deduplication (24h TTL) | Real-Time Dedup |
| `media_files` | Media lifecycle, cleanup, entity correlation | Media Management |
| `conversation_threads` | Thread metadata, archival, context summary | Thread Management |
| `checkpoints` | LangGraph workflow state snapshots | Framework (LangGraph) |
| `checkpoint_blobs` | LangGraph binary state objects | Framework (LangGraph) |
| `checkpoint_writes` | LangGraph incremental state writes | Framework (LangGraph) |
| `checkpoint_migrations` | LangGraph schema versioning | Framework (LangGraph) |
| `store` | DeepAgents long-term memory (company context) | Framework (DeepAgents) |
| `store_migrations` | DeepAgents schema versioning | Framework (DeepAgents) |
| `audit_log` | Automatic audit trail (database triggers) | Compliance |

**⚠️ Architecture Decision Needed - Potential Table Consolidation:**

**Current Implementation:** 34 tables including some that may overlap with LangSmith capabilities.

**Tables Under Review:**
- `workflow_outcomes` - 1,111 rows currently tracking execution metadata
- `company_intelligence` - Designed for auto-discovered brand metadata
- `routing_history` - Designed for routing decision tracking
- `pending_approvals` - Designed for HITL state (may be redundant with LangGraph checkpoints)

**LangSmith-First Architecture Consideration:**
LangSmith provides workflow tracing, learning, and observability. However, we need to validate:
1. **workflow_outcomes** - May be useful as local cache for fast queries (LangSmith requires API calls)
2. **company_intelligence** - May be needed for frequently-accessed company context
3. **routing_history** - Likely redundant (LangSmith traces contain routing decisions)
4. **pending_approvals** - Likely redundant (LangGraph checkpoints handle HITL)

**Recommendation:** Review actual usage in codebase before deletion. If unused, remove in Phase 2 cleanup.

**Note:** Current design already uses LangSmith for tracing and LangGraph checkpoints for HITL. These tables may be from earlier architecture iterations.

---

### Category 2: Product Domain Tables (14 Tables) ✅ FULLY IMPLEMENTED

Product catalog, variant management, and e-commerce operations.

**Implementation Status:** All 14 tables implemented and populated with production data.

| Table | Purpose | Current Rows | Status |
|-------|---------|--------------|--------|
| `categories` | Hierarchical product taxonomy | 10 | ✅ Implemented |
| `industries` | NAICS 2022 industry classification | 74 | ✅ Implemented |
| `product_families` | Parent products with variants | 7 | ✅ Implemented |
| `variant_axes` | Variant dimensions (size, color, etc.) | 24 | ✅ Implemented |
| `variant_values` | Specific variant values | 102 | ✅ Implemented |
| `products` | Individual SKUs/variants | 64 | ✅ Implemented |
| `product_variant_values` | M:N product-to-variant junctions | 45 | ✅ Implemented |
| `product_images` | Product visual assets | 0 | ✅ Implemented (empty) |
| `product_family_industries` | Multi-industry targeting | 0 | ✅ Implemented (empty) |
| `customer_segments` | Audience messaging strategies | 0 | ✅ Implemented (needs extension) |
| `marketing_content` | Platform-specific content | 0 | ✅ Implemented (needs extension) |
| `product_price_history` | Temporal price tracking | 52 | ✅ Implemented |
| `product_inventory_history` | Temporal stock tracking | 35 | ✅ Implemented |
| `audit_log` | Universal change audit trail | 82 | ✅ Implemented |

---

### Category 3: Marketing Domain Tables (4 New + 2 Extensions) ❌ NOT IMPLEMENTED - PHASE 2

Campaign management, creative assets, and multi-platform orchestration.

**Implementation Status:** Schema designed but tables NOT YET CREATED. Ready for migration implementation.

**Prerequisites:**
- customer_segments table needs campaign_id column addition
- marketing_content table needs campaign_id and campaign_asset_id columns addition

| Table | Purpose | Status | Migration Priority |
|-------|---------|--------|---------------------|
| `campaigns` | Campaign metadata, budget, timeline | ❌ **NOT IMPLEMENTED** | Priority 1 (Core) |
| `campaign_products` | M:N campaign-to-product links | ❌ **NOT IMPLEMENTED** | Priority 2 (Junction) |
| `campaign_assets` | Creative asset library | ❌ **NOT IMPLEMENTED** | Priority 3 (Assets) |
| `campaign_channels` | Platform-specific configurations | ❌ **NOT IMPLEMENTED** | Priority 4 (Platform) |
| `customer_segments` | Add campaign_id FK (nullable) | ⚠️ **NEEDS EXTENSION** | Priority 5 (Extension) |
| `marketing_content` | Add campaign_id, campaign_asset_id FKs | ⚠️ **NEEDS EXTENSION** | Priority 6 (Extension) |

---

### Category 4: Platform Integration Tables (Phase 3 - 7 New + 4 Extended) 🚀 FUTURE

External advertising platform integrations (Meta, Google Ads, Amazon, YouTube, X, LinkedIn, TikTok).

**Implementation Status:** Future phase after Marketing Campaign domain is complete.

**Dependency:** Requires Marketing Campaign tables (Phase 2) to be implemented first.

| Table | Purpose | Status | Phase |
|-------|---------|--------|-------|
| `platform_credentials` | Encrypted OAuth tokens and API keys | 🚀 **PHASE 3** | After Marketing |
| `platform_rate_limits` | Per-platform quota tracking | 🚀 **PHASE 3** | After Marketing |
| `platform_api_errors` | Error logging and retry tracking | 🚀 **PHASE 3** | After Marketing |
| `platform_webhook_events` | Real-time webhook event queue | 🚀 **PHASE 3** | After Marketing |
| `campaign_performance` | Normalized cross-platform metrics | 🚀 **PHASE 3** | After Marketing |
| `campaign_performance_raw` | Platform-specific metrics (JSONB) | 🚀 **PHASE 3** | After Marketing |
| `platform_campaign_mapping` | AutifyME ↔ Platform ID mapping | 🚀 **PHASE 3** | After Marketing |
| `campaigns` | Added platform_config (JSONB) | ⏳ **EXTENSION** | With Platform Integration |
| `campaign_channels` | Added sync tracking columns | ⏳ **EXTENSION** | With Platform Integration |
| `campaign_assets` | Added platform upload tracking | ⏳ **EXTENSION** | With Platform Integration |
| `marketing_content` | No changes (already ready) | ✅ **READY** | No changes needed |

---

### Category 5: Shared/Reusable Tables (7 Tables)

Cross-workflow entities reused across multiple domains.

| Table | Used By | Purpose |
|-------|---------|---------|
| `customer_segments` | Product Onboarding, Marketing | B2B/B2C/D2C messaging strategies |
| `industries` | Product Onboarding, Marketing | NAICS industry classification |
| `marketing_content` | Product Onboarding, Marketing | Platform-specific content (product + campaign) |
| `product_images` | Product Onboarding, Marketing | Product visuals (reused in campaigns) |
| `categories` | Product Onboarding, Future | Internal taxonomy |
| `company_intelligence` | All Workflows | Auto-discovered brand metadata |
| `companies` | All Workflows | Company profile (single-tenant) |

---

## Entity Relationship Model

### High-Level Architecture

**Infrastructure Layer:**
- Companies (single tenant) - all workflows implicitly belong to THE company
- Workflow outcomes - execution tracking
- Processed messages - webhook deduplication
- Pending approvals - HITL state persistence

**Product Layer:**
- Categories (tree structure) → Product Families
- Product Families → Variant Axes → Variant Values
- Product Families → Products (individual SKUs)
- Products ↔ Variant Values (M:N via product_variant_values)
- Products → Price History (temporal)
- Products → Inventory History (temporal)
- Product Families → Industries (M:N multi-targeting)
- Product Families → Customer Segments
- Product Families/Products → Marketing Content
- Product Families/Products → Product Images

**Marketing Layer:**
- Campaigns → Campaign Products (M:N to products/families)
- Campaigns → Campaign Assets (creative library)
- Campaigns → Campaign Channels (platform configurations)
- Campaigns → Marketing Content (via campaign_id FK)

**Shared Entities:**
- Industries - referenced by product_family_industries, marketing_content
- Customer Segments - referenced by marketing_content
- Product Images - reused across product + marketing workflows
- Marketing Content - multi-purpose: product content + campaign content

---

### Key Relationships

**Product Variant Architecture:**
- Product Families (1) → (N) Variant Axes (dimensions like size, color)
- Variant Axes (1) → (N) Variant Values (specific values like "Red", "Large")
- Products (M) ↔ (N) Variant Values via product_variant_values junction

**Multi-Level Targeting:**
- Product family can target multiple industries via product_family_industries
- Product family can have multiple customer segments via customer_segments
- Each segment + industry can have specific marketing_content

**Campaign Architecture:**
- Campaigns (1) → (N) Campaign Products (which products promoted)
- Campaigns (1) → (N) Campaign Assets (creative library)
- Campaigns (1) → (N) Campaign Channels (platform configurations)
- Campaigns (1) → (N) Marketing Content (via campaign_id foreign key)

**Multi-Purpose Content:**
- marketing_content serves BOTH product onboarding and marketing campaigns
- campaign_id IS NULL → Product onboarding content (organic)
- campaign_id IS NOT NULL → Campaign content (paid/promoted)

---

## Infrastructure & System Tables

---

### 1. Companies (Single-Tenant Configuration)

**Purpose:** Single-tenant company profile with operational system settings - exactly ONE row in production.

**Key Attributes:**
- **Identity:** id (UUID), name, legal_name, domain
- **Branding:** brand_voice, brand_attributes (JSONB - certifications, competitive advantages, social handles), target_markets (array)
- **Contact:** website, email, phone, full address fields (address_line1, address_line2, city, state, postal_code, country)
- **Defaults:** default_currency (INR), default_timezone (Asia/Kolkata), default_language (en)
- **System Settings:** system_settings (JSONB - HITL timeouts, archival policies, media limits)
- **Timestamps:** created_at, updated_at

**Schema:**
```sql
CREATE TABLE companies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  legal_name TEXT,
  domain TEXT,
  brand_voice TEXT,
  brand_attributes JSONB DEFAULT '{}'::jsonb,
  target_markets TEXT[],
  website TEXT,
  email TEXT,
  phone TEXT,
  address_line1 TEXT,
  address_line2 TEXT,
  city TEXT,
  state TEXT,
  postal_code TEXT,
  country TEXT DEFAULT 'India',
  default_currency TEXT DEFAULT 'INR',
  default_timezone TEXT DEFAULT 'Asia/Kolkata',
  default_language TEXT DEFAULT 'en',
  system_settings JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_companies_single_tenant ON companies ((true));
```

**Usage:**
- Loaded once at PM startup, injected into all specialists via middleware
- All workflows implicitly belong to this single company
- system_settings controls operational behavior (HITL timeouts, cleanup policies)

**Single-Tenant Enforcement:** Unique index on `(true)` ensures exactly one row.

---

### 2. Processed Messages (Webhook Deduplication)

**Purpose:** Prevent duplicate processing on webhook retry.

**Key Attributes:**
- **Identity:** message_id (TEXT, PRIMARY KEY - platform message ID like WhatsApp wamid)
- **Context:** sender_id, thread_id
- **Tracking:** received_at, processed_at
- **Lifecycle:** expires_at (24-hour TTL), created_at

**Schema:**
```sql
CREATE TABLE processed_messages (
  message_id TEXT PRIMARY KEY,
  sender_id TEXT NOT NULL,
  thread_id TEXT NOT NULL,
  received_at TIMESTAMPTZ NOT NULL,
  processed_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '24 hours'),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_processed_messages_expires ON processed_messages(expires_at);
```

**Usage:**
- Webhook handler checks message_id before processing
- Atomic check-and-insert prevents race conditions
- Automatic cleanup after 24 hours via scheduled job

**Stored Procedure:** check_and_mark_processed() - Atomic check + insert in single DB call.

---

### 3. Media Files (User-Uploaded Media Lifecycle)

**Purpose:** Track user-uploaded media (WhatsApp images) with lifecycle management and cleanup.

**Key Attributes:**
- **Identity:** id (UUID), platform (whatsapp/instagram/direct_upload), platform_media_id
- **File Metadata:** file_path (local storage), file_type (image/video/audio/document), mime_type, file_size_bytes
- **Deduplication:** content_hash (SHA256 for duplicate detection)
- **Lifecycle:** downloaded_at, last_accessed_at, expires_at (30-day TTL)
- **Entity Correlation:** used_by_entities (JSONB array - which products/campaigns use this)
- **Cleanup:** archived (boolean), archived_at

**Schema:**
```sql
CREATE TABLE media_files (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  platform TEXT NOT NULL CHECK (platform IN ('whatsapp', 'instagram', 'direct_upload')),
  platform_media_id TEXT NOT NULL,
  file_path TEXT NOT NULL,
  file_type TEXT NOT NULL CHECK (file_type IN ('image', 'video', 'audio', 'document')),
  mime_type TEXT NOT NULL,
  file_size_bytes BIGINT NOT NULL,
  content_hash TEXT,
  downloaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '30 days'),
  used_by_entities JSONB DEFAULT '[]'::jsonb,
  archived BOOLEAN DEFAULT FALSE,
  archived_at TIMESTAMPTZ,
  CONSTRAINT unique_platform_media UNIQUE (platform, platform_media_id)
);

CREATE INDEX idx_media_files_expires ON media_files(expires_at) WHERE NOT archived;
CREATE INDEX idx_media_files_hash ON media_files(content_hash);
CREATE INDEX idx_media_files_entities ON media_files USING GIN (used_by_entities);
```

**Usage:**
- User uploads image via WhatsApp → stored here with 30-day expiry
- content_hash prevents duplicate downloads of same image
- used_by_entities tracks which products/campaigns referenced this file
- Daily cleanup job archives expired media
- **Important:** User-uploaded media only; specialist-generated content goes to product_images

---

### 4. Conversation Threads (Thread Metadata & Archival)

**Purpose:** Track conversation threads with activity metadata and archival policies.

**Key Attributes:**
- **Identity:** id (TEXT, thread_id from platform)
- **Participant:** sender_id, platform (whatsapp/instagram/web)
- **Activity Tracking:** first_message_at, last_message_at, message_count
- **Context Summary:** recent_topics (array), active_workflows (JSONB)
- **Lifecycle:** is_active (boolean), archived_at, auto_archive_at (30-day default)
- **Traceability:** trace_ids (array of workflow trace IDs)
- **Timestamps:** created_at, updated_at

**Schema:**
```sql
CREATE TABLE conversation_threads (
  id TEXT PRIMARY KEY,
  sender_id TEXT NOT NULL,
  platform TEXT NOT NULL CHECK (platform IN ('whatsapp', 'instagram', 'web')),
  first_message_at TIMESTAMPTZ NOT NULL,
  last_message_at TIMESTAMPTZ NOT NULL,
  message_count INT DEFAULT 0,
  recent_topics TEXT[],
  active_workflows JSONB DEFAULT '[]'::jsonb,
  is_active BOOLEAN DEFAULT TRUE,
  archived_at TIMESTAMPTZ,
  auto_archive_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '30 days'),
  trace_ids TEXT[],
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_threads_sender ON conversation_threads(sender_id);
CREATE INDEX idx_threads_active ON conversation_threads(is_active, last_message_at DESC);
CREATE INDEX idx_threads_archive ON conversation_threads(auto_archive_at) WHERE is_active;
```

**Usage:**
- Updated on each message (last_message_at, message_count)
- recent_topics and active_workflows provide PM context for multi-turn conversations
- User dashboard queries active threads per sender
- Automatic archival after 30 days of inactivity
- trace_ids enable cross-conversation workflow traceability

---

### 5-8. LangGraph Tables (Framework-Managed)

**Purpose:** LangGraph state persistence, HITL resumption, time-travel debugging.

**Tables:**
- `checkpoints` - Workflow state snapshots (thread_id, checkpoint_id, checkpoint JSONB)
- `checkpoint_blobs` - Binary large objects (bytea)
- `checkpoint_writes` - Incremental state writes (performance optimization)
- `checkpoint_migrations` - Schema versioning

**Usage:**
- Framework-owned, managed by LangGraph
- Enables HITL (interrupt/resume via checkpoints)
- Provides time-travel debugging
- Never modify schema (breaks LangGraph compatibility)

**HITL Flow:**
```python
# PM tool triggers interrupt (interrupt_on=True in DeepAgents config)
pm.stream(...)
→ LangGraph creates checkpoint with __interrupt__ state
→ Runner detects interrupt, sends approval request to user
→ User approves/edits/rejects
→ Runner creates Command with interrupt_id
→ LangGraph resumes from checkpoint
```

**Monitoring:**
```sql
-- Check checkpoint growth
SELECT
  COUNT(*) as total_checkpoints,
  COUNT(DISTINCT thread_id) as unique_threads,
  pg_size_pretty(pg_total_relation_size('checkpoints')) as table_size
FROM checkpoints;
```

---

### 9-10. DeepAgents Store Tables (Framework-Managed)

**Purpose:** DeepAgents long-term memory across conversations.

**Tables:**
- `store` - Key-value store (prefix, key, value JSONB, TTL)
- `store_migrations` - Schema versioning

**Usage:**
- Company profile loaded once, stored with key `company:{company_id}`
- Injected into PM via DeepAgents middleware
- Cross-conversation memory (user preferences, learned patterns from LangSmith)
- TTL-based cleanup for temporary context

**Example:**
```python
# Load company context once
company_profile = storage.get_company_profile()
store.put(
    ("company", company_profile.id),
    company_profile.model_dump()
)

# DeepAgents middleware auto-injects into PM context
pm = create_deep_agent(..., store=store)
```

---

### 11. Audit Log (Compliance Trail)

**Purpose:** Automatic audit trail for all database changes (compliance requirement).

**Schema:**
```sql
CREATE TABLE audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  table_name TEXT NOT NULL,
  record_id UUID NOT NULL,
  operation TEXT NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
  old_values JSONB,
  new_values JSONB,
  changed_fields TEXT[] DEFAULT ARRAY[]::TEXT[],
  changed_by TEXT,  -- User/system identifier
  changed_at TIMESTAMPTZ DEFAULT NOW(),
  change_reason TEXT,
  session_id TEXT,
  ip_address INET,
  user_agent TEXT
);

CREATE INDEX idx_audit_log_table_record ON audit_log(table_name, record_id);
CREATE INDEX idx_audit_log_changed_at ON audit_log(changed_at DESC);
```

**Usage:**
- Automatic triggers on all business tables (products, campaigns, etc.)
- Captures old_values vs new_values
- Tracks changed_fields array for efficient queries
- Compliance audits: "Who changed product price on date X?"

**Why Not LangSmith:**
- Needs to track ALL database changes, not just agent operations
- Includes manual database updates, scripts, migrations
- Compliance requirement (immutable audit trail)

---

## Product Domain Tables

### 1. Categories (Hierarchical Taxonomy)

**Purpose:** Hierarchical internal product taxonomy.

**Key Attributes:**
- Identity: id (UUID), parent_id (self-referencing for tree)
- Naming: name, slug (unique, URL-friendly), description
- External: google_product_category (Google Shopping mapping)
- Display: sort_order, is_active

**Usage:** Product classification (Taxonomy Specialist), navigation, filtering.

**Relationships:** Tree structure via parent_id. Referenced by product_families.

---

### 2. Industries (NAICS 2022 Classification)

**Purpose:** NAICS 2022 industry classification - 6-level hierarchy.

**Key Attributes:**
- Identity: naics_code (PRIMARY KEY, 2-6 digits), parent_code (FK)
- Naming: label, description
- Hierarchy: level (1-6), naics_year (2022)
- Status: is_active

**Usage:** Multi-industry B2B targeting. Taxonomy Specialist classifies products into industries. Marketing campaigns target specific industries.

**Relationships:**
- Tree structure via parent_code
- Referenced by product_family_industries, marketing_content

**Current Data:** 74 industries loaded (20 sectors + 54 subcategories).

---

### 3. Product Families (Parent Concepts)

**Purpose:** Parent product concepts that have variants (e.g., "Nike Air Max Sneaker").

**Key Attributes:**
- Identity: id (UUID), product_group_id (business ID), sku_prefix (unique)
- Naming: name, description, brand
- Classification: category_id (FK), google_product_category, tags (array)
- Pricing: base_price, price_currency
- Attributes: material, condition (new/refurbished/used), custom_attributes (JSONB)
- Lifecycle: lifecycle_stage (new_arrival/regular/clearance/discontinued), is_active
- Audit: created_at, updated_at, created_by, updated_by

**Usage:** Product Architecture Specialist defines family structure. All variants inherit from family.

**Relationships:**
- (1) → (N) products (individual SKUs)
- (1) → (N) variant_axes (dimensions)
- (1) → (N) product_family_industries (B2B targeting)
- (1) → (N) customer_segments (messaging)
- (1) → (N) product_images (family-level images)
- (1) → (N) marketing_content (family-level content)

**Current Data:** 7 product families.

---

### 4. Variant Axes (Variant Dimensions)

**Purpose:** Dimensions along which a product family varies (e.g., size, color, material).

**Key Attributes:**
- Identity: id (UUID), product_family_id (FK)
- Naming: name (snake_case, e.g., "size"), display_label (e.g., "Size")
- Schema: schema_property (Schema.org mapping for SEO)
- Display: sort_order

**Usage:** Product Architecture Specialist defines variant structure. UI renders variant selectors based on axes.

**Relationships:**
- (N) ← (1) product_families
- (1) → (N) variant_values

**Current Data:** 24 variant axes across 7 families.

---

### 5. Variant Values (Specific Values)

**Purpose:** Specific values for each variant axis (e.g., "Red", "Large", "Cotton").

**Key Attributes:**
- Identity: id (UUID), variant_axis_id (FK)
- Naming: value, display_label, sku_code (SKU component, e.g., "M", "RED")
- Visual: color_hex (if color axis), image_url (swatch image)
- Pricing: price_adjustment (delta from base price)
- Display: sort_order, is_active

**Usage:** Product Architecture Specialist defines all possible values. Products reference values to define specific combinations.

**Relationships:**
- (N) ← (1) variant_axes
- (M) ↔ (N) products via product_variant_values

**Current Data:** 102 variant values (sizes, colors, materials, etc.).

---

### 6. Products (Individual SKUs)

**Purpose:** Individual SKUs - specific variant combinations (e.g., "Nike Air Max - Size M - Color Red").

**Key Attributes:**
- Identity: id (UUID), product_family_id (FK), sku (unique)
- Naming: name, description
- Pricing: price, sale_price, sale_price_start, sale_price_end
- Inventory: stock_quantity, availability (in_stock/out_of_stock/preorder/backorder/discontinued)
- Display: is_primary_variant (hero variant), link (product page URL)
- Legacy: sizes, colors, image_urls (arrays, for simple cataloging)
- Audit: created_at

**Usage:** Product Architecture Specialist generates all SKU combinations. Cataloging Specialist creates standalone products.

**Relationships:**
- (N) ← (1) product_families
- (M) ↔ (N) variant_values via product_variant_values
- (1) → (N) product_images (variant-specific)
- (1) → (N) marketing_content (variant-specific)
- (1) → (N) product_price_history (temporal)
- (1) → (N) product_inventory_history (temporal)

**Current Data:** 64 products (standalone + family variants).

**Constraint:** Exactly ONE is_primary_variant=true per family.

---

### 7. Product Variant Values (M:N Junction)

**Purpose:** M:N junction linking products to their variant dimension values.

**Key Attributes:**
- Identity: id (UUID), product_id (FK), variant_value_id (FK)

**Usage:** Defines which variant values (e.g., "Red", "Large") apply to each product.

**Example:** Product "SHOE-M-RED" has junctions to:
- variant_value "M" (size axis)
- variant_value "RED" (color axis)

**Constraint:** Family consistency enforced - product must belong to same family as variant value's axis.

**Current Data:** 45 junctions.

---

### 8. Product Images (Multi-Level Storage)

**Purpose:** Multi-level image storage - family-level (shared) or variant-specific.

**Key Attributes:**
- Identity: id (UUID)
- Links: product_family_id (FK, nullable), product_id (FK, nullable)
- Image: url, alt_text, image_type (primary/gallery/thumbnail/lifestyle/closeup/video_thumbnail)
- Technical: width, height, file_size_bytes
- Platform: whatsapp_media_id
- Display: is_primary (hero image), display_order
- Audit: created_at, updated_at

**Usage:** Visual Assets Specialist organizes images. Marketing campaigns reuse product images.

**Relationships:**
- (N) ← (1) product_families (CASCADE)
- (N) ← (1) products (CASCADE)

**Constraint:** At least ONE of product_family_id OR product_id must be set.

**Recommendation - Add Missing Constraint:**
```sql
ALTER TABLE product_images
ADD CONSTRAINT chk_product_images_link CHECK (
  product_family_id IS NOT NULL OR product_id IS NOT NULL
);
```

**Current Data:** 0 images (ready for population).

---

### 9. Product Family Industries (Multi-Industry Targeting)

**Purpose:** M:N junction for multi-industry B2B targeting.

**Key Attributes:**
- Identity: id (UUID), product_family_id (FK), industry_naics_code (FK)
- Targeting: industry_use_case, industry_benefits (array), compliance_notes
- Priority: is_primary_industry (default messaging focus)

**Usage:** Market Intelligence Specialist identifies target industries. Marketing campaigns create industry-specific content.

**Example:** Water bottle targets:
- Healthcare (NAICS 621) - "Hydration tracking for patient wellness"
- Sports (NAICS 713) - "Durable for athletes"
- Corporate (NAICS 551) - "Branded corporate gifts"

**Current Data:** 0 (ready for population).

---

### 10. Customer Segments (Audience Strategies)

**Purpose:** Messaging strategies for products AND campaigns - supports product-specific, campaign-specific, and global company segments.

**Key Attributes:**
- Identity: id (UUID)
- Ownership: product_family_id (FK, nullable), campaign_id (FK, nullable)
- Segment: segment_type (b2b/b2c/d2c/wholesale/enterprise/retail), segment_label
- Messaging: tone (professional/casual/technical/emotional/educational/aspirational)
- Strategy: key_benefits (array), pain_points (array)
- Channels: primary_channels (array: linkedin, instagram, email), content_formats (array: carousel, video)
- Pricing: pricing_notes
- Audit: created_at, updated_at

**Usage:**
- **Product Onboarding:** Market Intelligence Specialist defines product-specific segments
- **Marketing Campaigns:** Audience Intelligence Specialist defines campaign-specific segments (holiday shoppers, retargeting audiences)
- **Company-Wide:** Global segments (eco-conscious buyers, price-sensitive customers)

**Relationships:**
- (N) ← (1) product_families (CASCADE, optional)
- (N) ← (1) campaigns (CASCADE, optional)
- (1) → (N) marketing_content (segment-specific content)

**Recommendation - Add Campaign Support:**
```sql
ALTER TABLE customer_segments
ALTER COLUMN product_family_id DROP NOT NULL,
ADD COLUMN campaign_id UUID,
ADD CONSTRAINT fk_customer_segments_campaign
  FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
ADD CONSTRAINT chk_segment_ownership CHECK (
  (product_family_id IS NOT NULL) OR
  (campaign_id IS NOT NULL) OR
  (product_family_id IS NULL AND campaign_id IS NULL)  -- Global segments
);
```

**Rationale:**
- Product segments: product_family_id set, campaign_id NULL
- Campaign segments: campaign_id set, product_family_id NULL
- Global segments: both NULL (reusable across products and campaigns)

**Current Data:** 0 (ready for population).

---

### 11. Marketing Content (Platform-Specific Content)

**Purpose:** Platform-specific marketing content with versioning and performance tracking.

**Multi-Workflow Design:** Serves BOTH product onboarding and marketing campaigns.

**Key Attributes:**
- Identity: id (UUID)
- Links: product_family_id (FK, nullable), product_id (FK, nullable), customer_segment_id (FK, nullable), industry_naics_code (FK, nullable), campaign_id (FK, nullable), campaign_asset_id (FK, nullable)
- Platform: platform (instagram/facebook/twitter/linkedin/youtube/tiktok/website/email/catalog)
- Type: content_type (post/story/reel/video/carousel/ad/description/title/caption/subject_line/catalog_description)
- Content: content_text, content_metadata (JSONB platform-specific)
- SEO: hashtags (array), keywords (array), meta_title, meta_description
- Versioning: version (auto-incremented), is_active (only one active per combo)
- Performance: impressions, clicks, conversions
- Generation: generated_by, generation_prompt_version
- Audit: created_at, updated_at, published_at

**Usage:**
- **Product Onboarding:** Content & SEO Specialist generates platform content (campaign_id = NULL)
- **Marketing Campaigns:** Platform Adaptation + Ad Copy Specialists generate campaign content (campaign_id IS NOT NULL)

**Relationships:**
- (N) ← (1) product_families (CASCADE)
- (N) ← (1) products (CASCADE)
- (N) ← (1) customer_segments (SET NULL)
- (N) ← (1) industries (SET NULL)
- (N) ← (1) campaigns (CASCADE)
- (N) ← (1) campaign_assets (SET NULL)

**Recommendation - Add Campaign Foreign Keys:**
```sql
ALTER TABLE marketing_content
ADD COLUMN campaign_id UUID,
ADD COLUMN campaign_asset_id UUID,
ADD CONSTRAINT fk_marketing_content_campaign
  FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
ADD CONSTRAINT fk_marketing_content_campaign_asset
  FOREIGN KEY (campaign_asset_id) REFERENCES campaign_assets(id) ON DELETE SET NULL;
```

**Recommendation - Add Targeting Constraint:**
```sql
ALTER TABLE marketing_content
ADD CONSTRAINT chk_marketing_content_target CHECK (
  product_family_id IS NOT NULL OR
  product_id IS NOT NULL OR
  customer_segment_id IS NOT NULL OR
  industry_naics_code IS NOT NULL OR
  campaign_id IS NOT NULL
);
```

**Rationale:**
- campaign_id CASCADE: Campaign deletion cascades to all campaign content
- campaign_asset_id SET NULL: Content survives asset deletion (just loses asset reference)
- Constraint ensures content is targeted (prevents orphaned content with no association)

**Current Data:** 0 (ready for population).

---

### 12. Product Price History (Temporal Tracking)

**Purpose:** Temporal table tracking all price changes.

**Key Attributes:**
- Identity: id (UUID), product_id (FK)
- Pricing: price, sale_price, sale_price_start, sale_price_end
- Temporal: valid_from, valid_to (NULL = current active price)
- Audit: changed_by, change_reason, created_at

**Usage:** Database trigger auto-populates on products INSERT/UPDATE. Enables price trend analysis, rollback, compliance.

**Trigger:** update_product_price_history() fires AFTER INSERT/UPDATE on products.

**Current Data:** 52 price history records.

---

### 13. Product Inventory History (Temporal Tracking)

**Purpose:** Temporal table tracking all inventory changes.

**Key Attributes:**
- Identity: id (UUID), product_id (FK)
- Inventory: stock_quantity, availability
- Temporal: valid_from, valid_to (NULL = current active inventory)
- Audit: changed_by, change_reason, created_at

**Usage:** Database trigger auto-populates on products INSERT/UPDATE. Enables demand forecasting, shrinkage detection, compliance.

**Trigger:** update_product_inventory_history() fires AFTER INSERT/UPDATE on products.

**Current Data:** 35 inventory history records.

---

### 14. Audit Log (Universal Audit Trail)

**Purpose:** Universal audit trail for ALL table changes with JSONB snapshots.

**Key Attributes:**
- Identity: id (UUID), table_name, record_id (UUID of changed record)
- Operation: operation (INSERT/UPDATE/DELETE)
- Snapshots: old_values (JSONB before), new_values (JSONB after), changed_fields (array)
- Context: changed_by, change_reason, session_id, ip_address, user_agent
- Timing: changed_at

**Usage:** Database triggers auto-populate on ALL domain tables. Complete change history for compliance, debugging, rollback.

**Trigger:** audit_trigger() fires AFTER INSERT/UPDATE/DELETE on monitored tables.

**Current Data:** 82 audit records.

---

## Marketing Domain Tables

❌ **IMPLEMENTATION STATUS: NOT IMPLEMENTED - PHASE 2 PRIORITY**

All marketing tables below are designed but NOT YET CREATED in database. Implementation planned for Phase 2 after schema approval.

---

## Phase 2 Migration Plan - Marketing Campaign Tables

**Implementation Approach:** 6 sequential migrations to be created via Supabase MCP.

**Migration Sequence:**

1. **Migration: `campaigns`** (Priority 1)
   - Core campaign entity (no dependencies)
   - Columns: metadata, budget, timeline, lifecycle, performance aggregates
   - Indexes: status+date, type, date range
   - Constraints: date validation, enum checks

2. **Migration: `campaign_products`** (Priority 2)
   - M:N junction for campaign → products/families
   - Columns: promotion details, pricing, performance per product
   - Indexes: campaign, product_family, product, primary product uniqueness
   - Constraints: requires either product_family_id OR product_id

3. **Migration: `campaign_assets`** (Priority 3)
   - Creative asset library per campaign
   - Columns: asset metadata, approval status, versioning, usage tracking
   - Indexes: campaign, asset_type, active assets
   - Constraints: asset_type enumeration

4. **Migration: `campaign_channels`** (Priority 4)
   - Platform-specific configurations
   - Columns: platform IDs, budget allocation, config JSONB, performance
   - Indexes: campaign, platform, status
   - Constraints: unique (campaign, platform), platform enumeration

5. **Migration: Extend `customer_segments`** (Priority 5)
   - Add: `campaign_id` column (UUID, FK to campaigns, nullable)
   - Modify: `product_family_id` to nullable
   - Add: Check constraint for segment ownership (product OR campaign OR global)
   - Purpose: Support campaign-specific, product-specific, and global segments

6. **Migration: Extend `marketing_content`** (Priority 6)
   - Add: `campaign_id` column (UUID, FK to campaigns, nullable, CASCADE delete)
   - Add: `campaign_asset_id` column (UUID, FK to campaign_assets, nullable, SET NULL)
   - Add: Check constraint ensuring content is targeted
   - Indexes: campaign, campaign+platform, asset
   - Purpose: Separate product content (campaign_id NULL) from campaign content (campaign_id NOT NULL)

**Migration Verification:**
- Verify 4 new tables created
- Verify 2 existing tables extended with nullable FKs
- Verify all foreign keys and indexes created
- Verify check constraints enforced

**Rollback Strategy:** Reverse order (6 → 1), drop extensions first, then tables.

---

### 1. Campaigns (Campaign Orchestration) ❌ NOT IMPLEMENTED

**Purpose:** Top-level campaign metadata, budget, timeline, and lifecycle management.

**Implementation Status:** Schema designed, migration SQL ready, NOT YET CREATED.

**Key Attributes:**
- Identity: id (UUID), campaign_id (business ID, unique), name, description
- Classification: campaign_type (product_launch/seasonal/promotional/awareness/retention/acquisition), campaign_category
- Strategy: primary_objective (sales/awareness/engagement/traffic/leads/retention), secondary_objectives (array), target_audience_description
- Budget: total_budget, budget_currency, budget_allocation (JSONB per-channel breakdown)
- Timeline: planned_start_date, planned_end_date, actual_start_date, actual_end_date
- Status: status (draft/approved/scheduled/active/paused/completed/cancelled)
- Approval: approval_status (pending/approved/rejected/revision_requested), approved_by, approved_at
- KPIs: target_metrics (JSONB: impressions target, conversion target, etc.)
- Performance: total_impressions, total_clicks, total_conversions, total_spend (aggregated from channels)
- Generation: generated_by, generation_prompt_version, specialist_versions (JSONB tracking)
- Audit: created_at, updated_at, created_by, updated_by

**Usage:** Campaign Strategy Specialist defines campaign. PM presents for HITL approval. Runner tracks lifecycle.

**Relationships:**
- (1) → (N) campaign_products (promoted products)
- (1) → (N) campaign_assets (creative library)
- (1) → (N) campaign_channels (platform configs)
- (1) → (N) marketing_content (via campaign_id)

**Status:** ❌ NOT IMPLEMENTED - NEW table for marketing domain (Phase 2).

**Constraint:** planned_end_date >= planned_start_date.

---

### 2. Campaign Products (Promoted Products Junction) ❌ NOT IMPLEMENTED

**Purpose:** M:N junction linking campaigns to products they promote.

**Implementation Status:** Schema designed, migration SQL ready, NOT YET CREATED.

**Key Attributes:**
- Identity: id (UUID), campaign_id (FK)
- Links: product_family_id (FK, nullable), product_id (FK, nullable)
- Display: is_primary_product (hero product), featured_order
- Promotion: promotion_type (discount/bundle/bogo/new_arrival/clearance/featured)
- Pricing: discount_percentage, special_price, special_price_start, special_price_end
- Performance: impressions, clicks, conversions (product-specific within campaign)
- Audit: created_at

**Usage:** Campaign Strategy Specialist selects promoted products. Platform Adaptation Specialist generates product-specific campaign content.

**Relationships:**
- (N) ← (1) campaigns
- (N) → (1) product_families OR products (exactly one)

**Status:** ❌ NOT IMPLEMENTED - NEW table for marketing domain (Phase 2).

**Constraint:** Exactly ONE of product_family_id OR product_id must be set.

---

### 3. Campaign Assets (Creative Library) ❌ NOT IMPLEMENTED

**Purpose:** Campaign-specific creative asset library (images, videos, graphics).

**Implementation Status:** Schema designed, migration SQL ready, NOT YET CREATED.

**Key Attributes:**
- Identity: id (UUID), campaign_id (FK)
- Asset: asset_type (image/video/graphic/logo/banner), url, alt_text, title
- Technical: width, height, duration_seconds (video), file_size_bytes, mime_type
- Classification: usage_context (array: hero_banner, social_post, email_header), platform_optimized_for (array)
- Approval: is_approved, approved_by, approved_at
- Versioning: version, is_active
- Reuse: times_used (tracking)
- Audit: created_at, updated_at, uploaded_by

**Usage:** Visual Assets Specialist populates creative library. Platform Adaptation Specialist references assets when generating content.

**Relationships:**
- (N) ← (1) campaigns
- Referenced by marketing_content via campaign_asset_id

**Status:** ❌ NOT IMPLEMENTED - NEW table for marketing domain (Phase 2).

**Note:** Separate from product_images (product photography vs campaign creative).

---

### 4. Campaign Channels (Platform Configurations) ❌ NOT IMPLEMENTED

**Purpose:** Platform-specific campaign configurations and tracking IDs.

**Implementation Status:** Schema designed, migration SQL ready, NOT YET CREATED.

**Key Attributes:**
- Identity: id (UUID), campaign_id (FK)
- Platform: platform (facebook/instagram/youtube/twitter/linkedin/google_ads/amazon/whatsapp/email/website)
- External IDs: platform_campaign_id (Facebook Campaign ID, Google Ads ID), platform_account_id
- Budget: allocated_budget, actual_spend
- Config: channel_config (JSONB platform-specific settings: bidding, targeting)
- Status: status (draft/scheduled/active/paused/completed)
- Performance: total_impressions, total_clicks, total_conversions (aggregated from marketing_content)
- Timeline: started_at, ended_at
- Audit: created_at, updated_at

**Usage:** Campaign Strategy Specialist defines channel mix and budgets. Runner integrates with platform APIs using external IDs.

**Relationships:**
- (N) ← (1) campaigns
- Implicitly links to marketing_content via (campaign_id + platform) match

**Status:** ❌ NOT IMPLEMENTED - NEW table for marketing domain (Phase 2).

**Constraint:** UNIQUE (campaign_id, platform) - one config per campaign per platform.

---

## Platform Integration Tables (Phase 3) 🚀 FUTURE

**Implementation Status:** Future implementation after Marketing Campaign domain (Phase 2) is complete.

### 1. Platform Credentials (Encrypted Token Storage) 🚀 PHASE 3

**Purpose:** Encrypted storage for OAuth tokens, API keys, and platform credentials with auto-refresh capability.

**Implementation Status:** Future phase, requires Marketing Campaign tables first.

**Key Attributes:**
- Identity: id (UUID), company_id (FK)
- Platform: platform (meta/google_ads/tiktok/linkedin/twitter/amazon/youtube), credential_type (oauth_token/api_key/developer_token/system_user)
- Encrypted: access_token_encrypted (TEXT), refresh_token_encrypted (TEXT, nullable)
- Lifecycle: token_expires_at, scopes (array), is_active, last_refreshed_at
- External IDs: account_id (platform account ID), business_id (Meta Business Manager, Google Manager Account)
- Audit: created_at, updated_at

**Usage:** Platform adapters retrieve credentials before API calls. Middleware auto-refreshes expiring tokens. Application-level encryption (AES-256-GCM, key in environment variable).

**Relationships:**
- (N) ← (1) companies (single-tenant)
- Implicitly referenced by platform_api_errors, platform_rate_limits

**Status:** 🚀 PHASE 3 (platform integration implementation, after Marketing domain)

**Security:**
- Encryption key NEVER stored in database
- Refresh tokens NEVER exposed to agents or prompts
- Service account pattern for Meta (system users with permanent tokens)

**Constraint:** UNIQUE (company_id, platform, account_id)

---

### 2. Platform Rate Limits (Quota Tracking) 🚀 PHASE 3

**Purpose:** Per-platform quota tracking with adaptive throttling to prevent rate limit violations.

**Implementation Status:** Future phase, requires Marketing Campaign tables first.

**Key Attributes:**
- Identity: id (UUID), company_id (FK), platform (TEXT)
- Tracking: limit_type (cpu_time/daily_quota/requests_per_hour/operation_based), current_usage (BIGINT), limit_threshold (BIGINT), reset_at (TIMESTAMPTZ)
- Throttling: throttle_enabled (BOOLEAN), throttle_factor (DECIMAL 0.0-1.0, 1.0=normal, 0.5=half speed)
- Audit: last_updated_at

**Usage:** Platform adapters update usage after each API call. Request queue checks limits before dispatching. Adaptive throttling activates when usage > 75%.

**Platform-Specific Examples:**
- Meta: limit_type='cpu_time', limit_threshold=100 (CPU time per hour)
- YouTube: limit_type='daily_quota', limit_threshold=10000 (units per day)
- Google Ads: limit_type='operation_based' (varies by operation)

**Relationships:**
- (N) ← (1) companies (single-tenant)

**Status:** 🚀 PHASE 3 (platform integration implementation, after Marketing domain)

**Constraint:** UNIQUE (company_id, platform, limit_type)

---

### 3. Platform API Errors (Error Logging & Retry) 🚀 PHASE 3

**Purpose:** Centralized error logging with intelligent retry tracking for platform API failures.

**Implementation Status:** Future phase, requires Marketing Campaign tables first.

**Key Attributes:**
- Identity: id (UUID), company_id (FK), platform (TEXT)
- Classification: error_type (rate_limit/authentication/authorization/validation/platform_error/network/timeout), is_retryable (BOOLEAN)
- Details: endpoint (TEXT), http_status_code (INT), error_message (TEXT), error_code (TEXT platform-specific), request_payload (JSONB)
- Retry: retry_count (INT), next_retry_at (TIMESTAMPTZ), resolved_at (TIMESTAMPTZ, nullable)
- Audit: created_at

**Usage:** Platform adapters log all errors. Retry middleware checks is_retryable flag and retry_count. Circuit breaker monitors error rate to pause platform operations.

**Error Classification:**
- **Retryable:** Rate limiting (429), timeouts (504), network errors, temporary platform issues (500, 503)
- **Non-Retryable:** Authentication failures (401), authorization errors (403), validation errors (400), resource not found (404)

**Relationships:**
- (N) ← (1) companies (single-tenant)

**Status:** 🚀 PHASE 3 (platform integration implementation, after Marketing domain)

**Index:** idx_platform_api_errors_unresolved ON (company_id, platform, created_at DESC) WHERE resolved_at IS NULL

---

### 4. Platform Webhook Events (Real-Time Event Queue) 🚀 PHASE 3

**Purpose:** Real-time webhook event queue for platforms that support webhooks (Meta, TikTok).

**Implementation Status:** Future phase, requires Marketing Campaign tables first.

**Key Attributes:**
- Identity: id (UUID), company_id (FK), platform (meta/tiktok)
- Event: event_type (campaign_status_change/lead_created/conversion/ad_review_status), event_id (TEXT platform ID)
- Payload: payload (JSONB raw event data)
- Processing: processed (BOOLEAN), processed_at (TIMESTAMPTZ), processing_error (TEXT)
- Audit: received_at (TIMESTAMPTZ default now())

**Usage:** Webhook receiver endpoint ingests events. Background worker processes queue, updates campaign_channels.sync_status, triggers notifications.

**Auto-Cleanup:** Delete processed events older than 7 days (index: idx_webhook_events_cleanup ON processed_at WHERE processed = true)

**Deduplication:** UNIQUE (platform, event_id) prevents duplicate event processing.

**Relationships:**
- (N) ← (1) companies (single-tenant)

**Status:** 🚀 PHASE 3 (platform integration implementation, after Marketing domain)

**Index:** idx_webhook_events_unprocessed ON (company_id, platform, received_at) WHERE processed = false

---

### 5. Campaign Performance (Normalized Metrics) 🚀 PHASE 3

**Purpose:** Normalized cross-platform metrics for fast queries, aggregation, and comparison.

**Implementation Status:** Future phase, requires Marketing Campaign tables first.

**Key Attributes:**
- Identity: id (UUID), campaign_id (FK), channel_id (FK nullable)
- Time: date (DATE), hour (INT nullable, 0-23 for hourly, NULL for daily)
- Universal Metrics: impressions (BIGINT), clicks (BIGINT), conversions (INT), spend (DECIMAL), revenue (DECIMAL)
- Calculated: ctr (DECIMAL click-through rate), cpc (DECIMAL cost per click), cpa (DECIMAL cost per acquisition), roas (DECIMAL return on ad spend)
- Engagement: likes (INT), shares (INT), comments (INT)
- Audit: created_at, updated_at

**Usage:** Metrics collection jobs populate daily/hourly. Analytics queries aggregate across platforms. Campaign performance dashboards visualize trends.

**Normalization Rules:**
- impressions: Direct mapping (all platforms)
- clicks: Direct mapping (all platforms)
- conversions: Meta "purchases", Google "conversions", Amazon "attributed_units_ordered_14d"
- spend: Meta "spend", Google "cost_micros"/1M, Amazon "cost"
- revenue: Meta "purchase_value", Google "conversions_value", Amazon "attributedSales14d"

**Relationships:**
- (N) ← (1) campaigns
- (N) ← (1) campaign_channels (nullable for campaign-wide aggregates)
- (1) → (N) campaign_performance_raw (platform-specific details)

**Status:** 🚀 PHASE 3 (platform integration implementation, after Marketing domain)

**Constraint:** UNIQUE (campaign_id, channel_id, date, hour)

**Indexes:**
- idx_campaign_performance_date ON (campaign_id, date DESC)
- idx_campaign_performance_channel_date ON (channel_id, date DESC)

---

### 6. Campaign Performance Raw (Platform-Specific Metrics) 🚀 PHASE 3

**Purpose:** Platform-specific metrics in JSONB for detailed analysis and platform-unique data.

**Implementation Status:** Future phase, requires Marketing Campaign tables first.

**Key Attributes:**
- Identity: id (UUID), performance_id (FK to campaign_performance)
- Platform: platform (TEXT)
- Metrics: raw_metrics (JSONB platform-specific names and values)
- Audit: fetched_at (TIMESTAMPTZ default now())

**Usage:** Metrics collection jobs store full platform response. Analytics queries access platform-specific metrics not in normalized schema.

**Platform-Specific Examples:**
```
Meta: {
  "reach": 50000,
  "frequency": 2.3,
  "video_play_actions": 1200,
  "video_avg_time_watched": 8.5,
  "cost_per_thruplay": 0.15
}

Google Ads: {
  "quality_score": 8,
  "search_impression_share": 0.65,
  "average_position": 2.1
}

Amazon: {
  "attributedSales14d": 5000.00,
  "acos": 0.20,
  "attributed_units_ordered_14d": 150
}

TikTok: {
  "video_views": 25000,
  "video_watched_6s": 18000,
  "engaged_view": 12000
}
```

**Relationships:**
- (N) ← (1) campaign_performance (one raw per normalized)

**Status:** 🚀 PHASE 3 (platform integration implementation, after Marketing domain)

**Constraint:** UNIQUE (performance_id, platform)

---

### 7. Platform Campaign Mapping (External ID Tracking) 🚀 PHASE 3

**Purpose:** Bi-directional mapping between AutifyME campaigns and platform campaign IDs across hierarchies.

**Implementation Status:** Future phase, requires Marketing Campaign tables first.

**Key Attributes:**
- Identity: id (UUID), campaign_id (FK to campaigns), channel_id (FK to campaign_channels), platform (TEXT)
- Platform Hierarchy: platform_campaign_id (TEXT external campaign ID), platform_adset_id (TEXT nullable), platform_ad_ids (TEXT[] array)
- Sync: created_on_platform_at (TIMESTAMPTZ), last_synced_at (TIMESTAMPTZ), sync_version (INT incremented on update)
- Metadata: platform_metadata (JSONB platform-specific settings and status)
- Audit: created_at

**Usage:** Platform Sync Specialist stores external IDs after campaign creation. Runner uses IDs for status polling, metric fetching, campaign updates.

**Platform Hierarchy Examples:**
```
Meta (3-level):
- platform_campaign_id: Campaign ID
- platform_adset_id: Ad Set ID
- platform_ad_ids: [Ad ID 1, Ad ID 2]

Google Ads (3-level):
- platform_campaign_id: Campaign ID
- platform_adset_id: Ad Group ID
- platform_ad_ids: [Ad ID 1, Ad ID 2]

LinkedIn (4-level via metadata):
- platform_campaign_id: Campaign ID
- platform_adset_id: (not used, stored in metadata)
- platform_metadata: {"campaign_group_id": "12345"}
```

**Relationships:**
- (N) ← (1) campaigns
- (N) ← (1) campaign_channels
- Implicitly referenced by campaign_performance, platform_api_errors

**Status:** 🚀 PHASE 3 (platform integration implementation, after Marketing domain)

**Constraint:** UNIQUE (channel_id, platform)

---

### Extended Tables (Phase 2 Modifications)

**1. campaigns.platform_config (JSONB)**

**Purpose:** Store platform-specific advanced features without schema changes.

**Examples:**
```
Meta Advantage+ Campaign:
{
  "advantage_shopping_campaign": true,
  "catalog_id": "12345",
  "optimization_goal": "PURCHASE",
  "pixel_id": "98765"
}

Google Performance Max:
{
  "asset_group_type": "PERFORMANCE_MAX",
  "conversion_goals": ["PURCHASE", "ADD_TO_CART"],
  "budget_type": "DAILY",
  "bidding_strategy": "MAXIMIZE_CONVERSION_VALUE"
}

TikTok Smart Creative:
{
  "smart_creative_enabled": true,
  "dynamic_formats": ["video", "image"],
  "auto_optimize": true
}
```

**Benefits:** Supports 10% advanced use cases without breaking generic 90% model. Flexible extensibility as platforms evolve.

---

**2. campaign_channels Extensions (Sync Tracking)**

**New Columns:**
- `sync_status` TEXT CHECK IN (pending, syncing, live, paused, rejected, error) DEFAULT 'pending'
- `sync_error_message` TEXT (nullable)
- `last_synced_at` TIMESTAMPTZ (nullable)
- `platform_campaign_id` TEXT (nullable, quick reference to platform_campaign_mapping)

**Usage:** Platform Sync Specialist updates sync_status during campaign creation. Runner monitors status for completion. User sees sync progress in real-time.

**Status Flow:** pending → syncing → live (success) OR error/rejected (failure)

---

**3. campaign_assets Extensions (Platform Upload Tracking)**

**New Columns:**
- `platform_asset_id` JSONB ({"meta": "123456", "google_ads": "789012", "tiktok": "345678"})
- `platform_upload_status` JSONB ({"meta": "live", "google_ads": "pending", "tiktok": "rejected"})
- `compliance_check_results` JSONB ({"meta": {"compliant": false, "reason": "Text overlay > 20%"}})

**Usage:** Background worker pre-uploads assets to platforms before campaign creation. Records platform asset IDs for campaign creation reference. Validates compliance early to prevent campaign rejection.

**Benefits:**
- Decouples asset upload from campaign creation (faster specialist execution)
- Enables asset reuse across campaigns (upload once, reference many times)
- Validates compliance BEFORE HITL approval (no surprises after user approval)

---

**4. marketing_content (Ready for Phase 2)**

**No Changes:** Existing campaign_id and campaign_asset_id foreign keys already support Phase 2 platform integration.

**Usage:** Platform-specific content linked to campaigns via campaign_id. Creative assets linked via campaign_asset_id. Performance metrics (impressions, clicks, conversions) track content effectiveness per platform.

---

## Data Flow Patterns

### Product Onboarding Workflow

**Specialist Outputs → PM Synthesis → Atomic Persistence:**

1. **Product Architecture Specialist** → ProductArchitectureDraft (variant structure)
2. **Taxonomy Specialist** (parallel) → TaxonomyClassificationDraft (categories, Google, NAICS)
3. **Market Intelligence Specialist** (parallel) → MarketIntelligenceDraft (segments, positioning)
4. **Visual Assets Specialist** (parallel) → VisualAssetsDraft (image organization)
5. **Content & SEO Specialist** (sequential after 2-4) → ContentSEODraft (descriptions, SEO)
6. **PM Synthesizes** ALL Drafts → ProductFamilyInput (complete package)
7. **HITL Approval** → User approves/edits/rejects
8. **Atomic Persistence** (9 tables in transaction):
   - product_families (parent)
   - variant_axes (dimensions)
   - variant_values (options)
   - products (N SKUs)
   - product_variant_values (M:N junctions)
   - product_family_industries (B2B targeting)
   - customer_segments (messaging)
   - product_images (visuals)
   - marketing_content (platform variants)
9. **Automatic Triggers:**
   - product_price_history (on insert/update)
   - product_inventory_history (on insert/update)
   - audit_log (all changes)

---

### Marketing Campaign Workflow

**Specialist Outputs → PM Synthesis → Atomic Persistence:**

1. **Campaign Strategy Specialist** → CampaignStrategyDraft (objectives, budget, timeline)
2. **Audience Intelligence Specialist** (parallel) → AudienceTargetingDraft (segments, targeting)
3. **Marketing Content Specialist** (parallel) → MarketingContentDraft (narrative, headlines)
4. **Visual Assets Specialist** (parallel) → VisualAssetsDraft (creative selection)
5. **Platform Adaptation Specialist** (sequential after 2-4) → PlatformContentVariantsDraft (Facebook, Instagram, YouTube, etc.)
6. **Ad Copy Specialist** (sequential after 2-4) → AdCopyDraft (ad headlines, descriptions, A/B variants)
7. **PM Synthesizes** ALL Drafts → MarketingCampaignInput (complete campaign package)
8. **HITL Approval** → User approves/edits/rejects campaign plan
9. **Atomic Persistence** (5 tables in transaction):
   - campaigns (campaign metadata)
   - campaign_products (M:N product links)
   - campaign_assets (creative library)
   - campaign_channels (platform configs)
   - marketing_content (N platform content variants with campaign_id)
10. **Automatic Triggers:**
    - audit_log (all changes)

---

## Extensibility Strategy

### Adding New Workflows

**Pattern:** Extend schema incrementally without breaking existing workflows.

**Example: Inventory Management Workflow (Future)**

**New Tables Needed:**
1. inventory_locations - Warehouse/store locations
2. inventory_movements - Stock transfers, adjustments
3. inventory_counts - Physical count records
4. inventory_forecasts - Demand predictions

**Reused Tables:**
- products - Existing SKUs
- product_inventory_history - Already tracks stock changes
- audit_log - Automatic audit trail

**No Breaking Changes:**
- Product onboarding continues to use products.stock_quantity
- Inventory workflow EXTENDS with location tracking
- Existing foreign keys remain valid

---

### Multi-Workflow Table Reuse

**Design Principle:** Maximize reuse, minimize duplication.

**Examples:**

**customer_segments Table:**
- **Product Onboarding:** Defines messaging per segment (B2B vs B2C tone)
- **Marketing Campaigns:** Selects target segments for campaigns
- **Future CRM:** Links customers to segments for personalization
- **Single Source of Truth:** One segment definition, multiple uses

**industries Table:**
- **Product Onboarding:** Multi-industry targeting (water bottle → healthcare, sports, corporate)
- **Marketing Campaigns:** Industry-specific ad copy and messaging
- **Future Analytics:** Industry-level performance tracking
- **Reference Data:** NAICS 2022 hierarchy (74 industries currently)

**marketing_content Table:**
- **Product Onboarding:** Platform-specific product descriptions (Instagram, LinkedIn, Google Shopping)
- **Marketing Campaigns:** Campaign creative content linked via campaign_id
- **Future A/B Testing:** Version tracking already built-in (version, is_active)
- **Performance Tracking:** Impressions, clicks, conversions tracked per content piece

---

### Temporal Tracking Pattern

**Automatic History Tables:**

**Design:** Database triggers maintain complete change history without application logic.

**1. Price History:**
- product_price_history tracks every price change
- valid_from / valid_to intervals (temporal queries)
- Changed by user, change reason captured
- Enables: price trend analysis, rollback, compliance

**2. Inventory History:**
- product_inventory_history tracks every stock change
- Temporal intervals for point-in-time queries
- Supports: demand forecasting, shrinkage detection, compliance

**3. Universal Audit Log:**
- audit_log captures ALL table changes (INSERT/UPDATE/DELETE)
- JSONB snapshots of before/after values
- Changed fields array for efficient queries
- Supports: compliance, debugging, rollback, analytics

**Future Extensions:**
- campaign_performance_snapshots - Hourly/daily campaign metrics
- customer_interaction_history - Customer journey tracking
- content_version_history - A/B test variant evolution

---

## Schema Extensions for Marketing

### Marketing Content Table Extensions

**Two new columns added:**

**1. campaign_id (UUID, FK to campaigns, nullable)**
- NULL → Product onboarding content (organic)
- NOT NULL → Campaign content (paid/promoted)
- Enables clean separation while reusing performance tracking infrastructure

**2. campaign_asset_id (UUID, FK to campaign_assets, nullable)**
- Links content to specific creative asset from campaign library
- Tracks which asset used in which content piece

**New Indexes:**
- idx_marketing_content_campaign on campaign_id
- idx_marketing_content_campaign_platform on (campaign_id, platform)

**No Breaking Changes:** Existing product onboarding workflow unaffected (campaign_id = NULL).

---

## Performance & Optimization

### Indexes Strategy

**High-Volume Query Patterns:**

**Product Lookup:**
- products.sku (UNIQUE) - SKU search
- products.product_family_id - Family variants query
- products.availability - Stock filtering

**Campaign Performance:**
- campaigns.status, planned_start_date - Active campaign queries
- marketing_content.campaign_id, platform - Campaign content lookup
- campaign_channels.campaign_id - Channel configuration retrieval

**Temporal Queries:**
- product_price_history.valid_from, valid_to - Point-in-time pricing
- product_inventory_history.valid_from, valid_to - Historical stock levels
- workflow_outcomes.created_at DESC - Recent workflow analysis

**Analytics:**
- workflow_outcomes.intent, department - Routing success rates
- marketing_content.platform, is_active - Active content by platform
- audit_log.table_name, changed_at DESC - Recent changes audit

---

### Caching Strategy

**Application-Level Caching:**

**Static Reference Data (Cache Indefinitely):**
- companies (single row, loaded once)
- industries (74 rows, rarely changes)
- categories (10 rows, updated infrequently)

**Semi-Static Data (Cache with TTL):**
- company_intelligence (TTL: 1 hour, updated by specialists)
- product_families (TTL: 5 minutes, catalog updates)
- variant_axes, variant_values (TTL: 5 minutes)

**Dynamic Data (No Caching or Short TTL):**
- products.stock_quantity, availability (TTL: 30 seconds, real-time inventory)
- campaigns.status (TTL: 1 minute, lifecycle changes)
- marketing_content performance metrics (TTL: 5 minutes)

---

## Data Integrity & Constraints

### Foreign Key Cascade Rules

**DELETE CASCADE (Child Deleted When Parent Deleted):**
- campaigns deleted → cascade to campaign_products, campaign_assets, campaign_channels
- product_families deleted → cascade to products, variant_axes, product_images, etc.
- workflow_outcomes deleted → cascade to routing_history

**SET NULL (Child Reference Cleared):**
- campaigns deleted → marketing_content.campaign_id set NULL (preserve historical content)
- category deleted → product_families.category_id set NULL (preserve products)

**RESTRICT (Prevent Parent Deletion If Children Exist):**
- variant_axes cannot be deleted if variant_values exist
- variant_values cannot be deleted if product_variant_values exist

---

### Check Constraints

**Enumeration Validation:**
- campaigns.status IN (draft, approved, scheduled, active, paused, completed, cancelled)
- products.availability IN (in_stock, out_of_stock, preorder, backorder, discontinued)
- marketing_content.platform IN (instagram, facebook, twitter, linkedin, youtube, tiktok, website, email, catalog)

**Numeric Constraints:**
- campaigns.total_budget >= 0
- products.price >= 0
- company_intelligence.confidence_score BETWEEN 0 AND 1

**Date Constraints:**
- campaigns.planned_end_date >= planned_start_date
- product_price_history.valid_to >= valid_from

**String Format Constraints:**
- companies.default_currency matches '^[A-Z]{3}$' (3-letter ISO)
- variant_values.sku_code matches '^[A-Z0-9-]+$' (uppercase alphanumeric)
- variant_values.color_hex matches '^#[0-9A-Fa-f]{6}$' (hex color)

---

## Future-Proofing

### Planned Extensions (Phase 2-3)

**Analytics & Attribution:**
- campaign_performance_snapshots - Hourly/daily metrics snapshots
- customer_interactions - Customer journey tracking
- attribution_events - Multi-touch attribution modeling
- content_ab_tests - A/B test experiment tracking

**Inventory & Fulfillment:**
- inventory_locations - Warehouse/store locations
- inventory_movements - Stock transfers, adjustments
- inventory_counts - Physical count records
- inventory_forecasts - Demand predictions

**Customer Relationship Management:**
- customers - Customer profiles
- customer_orders - Order history
- customer_interactions - Support, chat, email history
- customer_preferences - Personalization data

**Advanced Marketing:**
- lookalike_audiences - AI-generated audience expansion
- campaign_experiments - Multi-variate testing
- influencer_collaborations - Influencer partnership tracking
- ugc_content - User-generated content library

**All Extensions Follow Same Patterns:**
- Normalized to 3NF
- Foreign keys to existing tables where applicable
- Temporal tracking where needed (valid_from/valid_to)
- Automatic audit_log triggers
- Performance indexes on common queries

---

## Future Domain Requirements (Phase 4+)

### CRM Domain (Customer Relationship Management)

**Strategic Priority:** Phase 4 - Customer engagement and retention workflows

**Core Entities:**
1. **customers** - Customer profiles (B2B companies or D2C individuals)
   - Identity: id, customer_type (b2b_company/d2c_individual), company_name, contact_name
   - Contact: email, phone, address, social profiles
   - Classification: customer_segment_id (FK), industry_naics_code (FK)
   - Lifecycle: lifecycle_stage (lead/prospect/customer/churned), acquisition_source, ltv (lifetime value)

2. **customer_interactions** - All touchpoints (chat, email, calls, meetings)
   - Interaction metadata, sentiment analysis, action items
   - Links to conversation_threads for WhatsApp continuity

3. **customer_orders** - Purchase history
   - Links to products, order_items, fulfillment status
   - Enables retention workflows, upsell recommendations

4. **customer_preferences** - Personalization data
   - Communication preferences, product preferences
   - Privacy consent tracking (GDPR compliance)

**Reused Tables:**
- customer_segments (already supports global segments)
- industries (B2B customer classification)
- products (order line items)
- marketing_content (personalized messaging)

**Workflow Examples:**
- Lead nurturing campaigns based on engagement
- Churn prediction and retention offers
- Upsell recommendations based on purchase history
- Personalized content delivery

---

### Inventory Management Domain

**Strategic Priority:** Phase 4 - Multi-location stock tracking and fulfillment

**Core Entities:**
1. **inventory_locations** - Warehouses, stores, fulfillment centers
   - Location metadata, capacity, operational hours

2. **inventory_movements** - Stock transfers, adjustments, receipts
   - Movement type (transfer/adjustment/receipt/return/sale)
   - Source/destination locations
   - Audit trail for shrinkage detection

3. **inventory_counts** - Physical count reconciliation
   - Scheduled counts, cycle counts, variance tracking

4. **inventory_forecasts** - Demand predictions
   - ML-based forecasting, seasonal patterns
   - Reorder point recommendations

**Reused Tables:**
- products (SKU inventory)
- product_inventory_history (already tracks changes)
- audit_log (automatic audit trail)

**Workflow Examples:**
- Automated reorder point alerts
- Multi-location inventory allocation
- Demand forecasting for seasonal products
- Shrinkage and variance reporting

---

### Analytics Domain

**Strategic Priority:** Phase 5 - Data-driven insights and optimization

**Core Entities:**
1. **attribution_events** - Multi-touch attribution
   - Customer journey touchpoints
   - Attribution models (first-touch, last-touch, linear, time-decay)
   - Revenue attribution across campaigns

2. **content_ab_tests** - Experimentation framework
   - A/B test definitions, variants, outcomes
   - Statistical significance tracking

3. **customer_journey_snapshots** - Funnel analysis
   - Stage transitions, conversion rates
   - Drop-off analysis

4. **predictive_insights** - ML-generated insights
   - Churn predictions, LTV predictions
   - Product recommendation scores
   - Dynamic pricing recommendations

**Reused Tables:**
- campaigns, campaign_performance (attribution source)
- customer_interactions (journey events)
- marketing_content (content variants)
- products (recommendation targets)

**Workflow Examples:**
- Multi-touch campaign attribution
- A/B testing platform content
- Customer lifetime value prediction
- Dynamic pricing optimization

---

### Cross-Domain Integration Strategy

**Shared Entities Continue to Scale:**
- `customer_segments` - Used by Product, Marketing, CRM, Analytics
- `industries` - Used by Product, Marketing, CRM
- `marketing_content` - Used by Product, Marketing, CRM (personalization)
- `products` - Used by Product, Marketing, CRM (orders), Inventory

**Data Flow Patterns:**
- **Product → CRM:** Customer purchases tracked in customer_orders
- **CRM → Marketing:** Customer segments drive campaign targeting
- **Marketing → Analytics:** Campaign performance feeds attribution
- **Inventory → CRM:** Stock availability impacts customer experience

**Extensibility Principles:**
- New domains add tables without breaking existing workflows
- Foreign keys maintain referential integrity
- Temporal tracking (history tables) for all critical entities
- Automatic audit_log triggers for compliance

---

## Summary Statistics

**Implementation Status (v3.1.0):**

**Phase 1 - Product Onboarding: ✅ COMPLETE**
- **14 Tables Implemented** (categories, industries, product_families, variant_axes, variant_values, products, product_variant_values, product_images, product_family_industries, customer_segments, marketing_content, product_price_history, product_inventory_history, audit_log)
- **9 Automatic Triggers** (price history, inventory history, audit log)
- **Production Data:** 64 SKUs, 7 families, 24 variant axes, 102 variant values, 74 industries

**Phase 2 - Marketing Campaigns: ❌ NOT IMPLEMENTED**
- **4 New Tables Designed:** campaigns, campaign_products, campaign_assets, campaign_channels
- **2 Table Extensions Needed:** customer_segments (add campaign_id), marketing_content (add campaign_id, campaign_asset_id)
- **Status:** Schema complete, migration SQL ready, awaiting approval and implementation

**Phase 3 - Platform Integration: 🚀 FUTURE**
- **7 Tables Designed:** platform_credentials, platform_rate_limits, platform_api_errors, platform_webhook_events, campaign_performance, campaign_performance_raw, platform_campaign_mapping
- **4 Table Extensions Designed:** campaigns, campaign_channels, campaign_assets, marketing_content
- **Status:** Depends on Phase 2 completion

**Phase 4+ - Future Domains: 🔮 REQUIREMENTS DOCUMENTED**
- **CRM Domain:** 4 core tables (customers, customer_interactions, customer_orders, customer_preferences)
- **Inventory Domain:** 4 core tables (inventory_locations, inventory_movements, inventory_counts, inventory_forecasts)
- **Analytics Domain:** 4 core tables (attribution_events, content_ab_tests, customer_journey_snapshots, predictive_insights)
- **Status:** Requirements documented, ready for design when needed

**Current Infrastructure:**
- **34 Tables Live** (20 infrastructure/framework, 14 product domain)
- **Companies:** 1 row (single-tenant)
- **Workflows Executed:** 1,111 total (859 successful, 252 failed)
- **Messages Processed:** Via processed_messages deduplication table
- **Framework Tables:** LangGraph checkpoints, DeepAgents store, audit_log all operational

---

## Key Architectural Strengths

1. **Single Source of Truth** - No data duplication, normalized to 3NF
2. **Multi-Workflow Reuse** - Shared entities (customer_segments, industries, marketing_content)
3. **Temporal Integrity** - Complete history tracking via automatic triggers
4. **Referential Integrity** - Foreign keys enforce relationships
5. **Type Safety** - Check constraints validate enumerations and formats
6. **Extensible** - New workflows add tables without breaking existing schema
7. **Observable** - Comprehensive audit trail, workflow tracking, performance metrics
8. **Performant** - Strategic indexes on high-volume query patterns

---

## Next Steps - Marketing Campaign Implementation

**Phase 2 Priority Actions:**

1. **Schema Approval Discussion** - Review this updated schema document
2. **Migration SQL Generation** - Create Supabase migrations for 4 new tables + 2 extensions
3. **Migration Execution** - Apply migrations via Supabase MCP
4. **Verification** - Validate schema, indexes, constraints
5. **Marketing Domain Implementation** - Build 5 specialists + persistence tool
6. **Testing** - Workflow validation and trace analysis

**Discussion Points:**
- Approve marketing table schema as designed?
- Confirm customer_segments and marketing_content extensions?
- Review infrastructure table consolidation recommendations?
- Validate future domain requirements (CRM, Inventory, Analytics)?

---

**Document Metadata:**

**Version:** 3.1.0
**Last Updated:** 2025-10-25
**Status:** Ready for Marketing Phase 2 - Awaiting Approval
**Next Review:** After Marketing Campaign implementation complete

**Change Log:**
- **v3.1.0 (2025-10-25):** Added implementation status markers, marketing readiness assessment, future domain requirements (CRM/Inventory/Analytics), phase prioritization
- **v3.0.0 (2025-01-25):** LangSmith-First Architecture, comprehensive schema design

**Related Documents:**
- `DOMAIN_DESIGN_GUIDELINES.md` - Architectural standards for new workflows
- `ACTUAL_IMPLEMENTATION_ARCHITECTURE.md` - Implementation patterns
- `PRODUCT_ONBOARDING_BUILD_SUMMARY.md` - Product domain reference implementation
- `MARKETING_DOMAIN_ANALYSIS.md` - Marketing workflow design
- `COMPREHENSIVE_ARCHITECTURAL_REVIEW.md` - Complete system audit
