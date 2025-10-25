# AutifyME Enterprise Database Schema Design

**Version:** 2.0.0
**Date:** 2025-10-25
**Status:** ✅ Master Reference - Production + Marketing Domains
**Purpose:** Comprehensive enterprise-grade database architecture for all AutifyME workflows

---

## Executive Summary

This document defines the **complete enterprise database architecture** for AutifyME across all workflows and domains. The schema supports:

- ✅ **Product Onboarding** - Variant families, SKU architecture, multi-system taxonomy (9 tables)
- ✅ **Marketing Campaigns** - Multi-platform orchestration, creative management, performance tracking (4 new + 1 extended)
- 🚀 **Platform Integration (Phase 2)** - 8 advertising platforms prioritized: Meta, Google Ads, Amazon, YouTube (Phase 1) → X, LinkedIn, TikTok (Phase 2+). Includes credentials, rate limiting, metrics, webhooks (7 new + 4 extended)
- ✅ **Cataloging** - Simple product entry (legacy workflow)
- ✅ **Infrastructure** - Workflow orchestration, idempotency, audit trails (9 tables)
- 🔮 **Future Workflows** - Inventory, CRM, Analytics (extensible foundation)

**Design Principles:**
- **Normalized to 3NF** - No redundancy, referential integrity via foreign keys
- **Single-Tenant** - One company per database (simplified architecture)
- **Reusable Components** - Shared entities across workflows (customer_segments, industries, marketing_content)
- **Atomic Transactions** - All-or-nothing operations guarantee data integrity
- **Temporal Tracking** - Automatic history tables for price, inventory, audit changes
- **Extensible** - New workflows add tables without breaking existing schema
- **Hybrid Abstraction** - Generic models + JSONB extensions for platform-specific features

**Total Schema:**
- **41 Tables** across 5 categories (34 current + 7 Phase 2)
- **9 Automatic Triggers** for history and audit trails
- **Multiple Views** for analytics and monitoring

---

## Table Categories Overview

### Category 1: Infrastructure & System Tables (9 Tables)

Core platform functionality for workflow orchestration, message processing, and system operations.

| Table | Purpose | Current Rows |
|-------|---------|--------------|
| `companies` | Single-tenant company profile | 1 (exactly one) |
| `company_intelligence` | Auto-discovered brand intelligence | 1 (exactly one) |
| `workflow_outcomes` | Workflow execution tracking for learning | 1,111 |
| `routing_history` | Lightweight routing analytics | 0 |
| `processed_messages` | Webhook idempotency (24h TTL) | 86 |
| `pending_approvals` | HITL state persistence | 0 |
| `checkpoints` | LangGraph workflow state | 87 |
| `checkpoint_blobs` | LangGraph binary state | 73 |
| `checkpoint_writes` | LangGraph incremental writes | 153 |

---

### Category 2: Product Domain Tables (14 Tables)

Product catalog, variant management, and e-commerce operations.

| Table | Purpose | Current Rows |
|-------|---------|--------------|
| `categories` | Hierarchical product taxonomy | 10 |
| `industries` | NAICS 2022 industry classification | 74 |
| `product_families` | Parent products with variants | 7 |
| `variant_axes` | Variant dimensions (size, color, etc.) | 24 |
| `variant_values` | Specific variant values | 102 |
| `products` | Individual SKUs/variants | 64 |
| `product_variant_values` | M:N product-to-variant junctions | 45 |
| `product_images` | Product visual assets | 0 |
| `product_family_industries` | Multi-industry targeting | 0 |
| `customer_segments` | Audience messaging strategies | 0 |
| `marketing_content` | Platform-specific content | 0 |
| `product_price_history` | Temporal price tracking | 52 |
| `product_inventory_history` | Temporal stock tracking | 35 |
| `audit_log` | Universal change audit trail | 82 |

---

### Category 3: Marketing Domain Tables (4 New + 1 Extended)

Campaign management, creative assets, and multi-platform orchestration.

| Table | Purpose | Status |
|-------|---------|--------|
| `campaigns` | Campaign metadata, budget, timeline | **NEW** |
| `campaign_products` | M:N campaign-to-product links | **NEW** |
| `campaign_assets` | Creative asset library | **NEW** |
| `campaign_channels` | Platform-specific configurations | **NEW** |
| `marketing_content` | Platform content with campaign links | **EXTENDED** (added campaign_id, campaign_asset_id) |

---

### Category 4: Platform Integration Tables (Phase 2 - 7 New + 4 Extended)

External advertising platform integrations (Meta, Google Ads, Amazon, YouTube, X, LinkedIn, TikTok).

| Table | Purpose | Status |
|-------|---------|--------|
| `platform_credentials` | Encrypted OAuth tokens and API keys | **PHASE 2** |
| `platform_rate_limits` | Per-platform quota tracking | **PHASE 2** |
| `platform_api_errors` | Error logging and retry tracking | **PHASE 2** |
| `platform_webhook_events` | Real-time webhook event queue | **PHASE 2** |
| `campaign_performance` | Normalized cross-platform metrics | **PHASE 2** |
| `campaign_performance_raw` | Platform-specific metrics (JSONB) | **PHASE 2** |
| `platform_campaign_mapping` | AutifyME ↔ Platform ID mapping | **PHASE 2** |
| `campaigns` | Added platform_config (JSONB) | **EXTENDED** |
| `campaign_channels` | Added sync tracking columns | **EXTENDED** |
| `campaign_assets` | Added platform upload tracking | **EXTENDED** |
| `marketing_content` | No changes (ready for Phase 2) | **READY** |

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

### 1. Companies (Single-Tenant Core)

**Purpose:** Single-tenant company profile - exactly ONE row in production.

**Key Attributes:**
- Identity: id (UUID), name, legal_name, domain
- Branding: brand_voice, brand_attributes (JSONB), target_markets (array)
- Contact: website, email, phone, full address
- Defaults: default_currency (INR), default_timezone (Asia/Kolkata)

**Usage:** All workflows implicitly belong to this company. Loaded once at startup, injected via middleware.

**Single-Tenant Enforcement:** Unique index on (true) ensures exactly one row.

---

### 2. Company Intelligence (Auto-Discovered)

**Purpose:** Auto-discovered company intelligence from product analysis and market research.

**Key Attributes:**
- Business: business_models (B2B/B2C/D2C array), price_positioning (budget/mid-range/premium/luxury)
- Brand: brand_voice, brand_values (array), visual_identity (JSONB)
- Market: target_audiences (JSONB personas), competitors (JSONB)
- Metadata: confidence_score (0.0-1.0), sources (array), discovered_at, last_updated

**Usage:** Enhanced context for specialists (Market Intelligence, Campaign Strategy). Single row updated continuously.

---

### 3. Workflow Outcomes (Learning & Analytics)

**Purpose:** Workflow execution tracking for agentic learning and continuous improvement.

**Key Attributes:**
- Identification: id, tracking_id (unique), thread_id, trace_id (LangSmith)
- Message: sender_id, message_text, message_hash, media_id, platform
- Routing: intent, department, routing_reasoning, routing_confidence, alternative_departments
- Outcome: success, error_type, error_message, resolution_strategy, result_data (JSONB)
- Performance: duration_seconds, started_at, ended_at
- Learning: learned_patterns (JSONB), failure_warnings (JSONB), applied_strategies (array)

**Usage:** Post-workflow analysis, adaptive routing, test synthesis, pattern recognition.

**Views:**
- v_success_rates - Success rate by department/intent (7-day window)
- v_recent_failures - Last 50 failures for regression testing
- v_edge_cases - Low-frequency patterns for test coverage

---

### 4. Processed Messages (Webhook Idempotency)

**Purpose:** Prevent duplicate processing on webhook retry.

**Key Attributes:**
- Identity: message_id (WhatsApp wamid, PRIMARY KEY)
- Context: sender_id, thread_id, received_at
- Lifecycle: processed_at, expires_at (24h TTL)

**Usage:** Webhook handler checks message_id before processing. Automatic cleanup after 24 hours via scheduled function.

**Stored Procedure:** check_and_mark_processed() - Atomic check + insert in single DB call.

---

### 5. Pending Approvals (HITL State Persistence)

**Purpose:** HITL state persistence - survive server restarts during approval wait.

**Key Attributes:**
- Workflow: thread_id, checkpoint_id, checkpoint_ns
- Interrupt: interrupt_id (LangGraph ID for resumption), tool_call (JSONB arguments)
- Context: draft_summary (human-readable), ai_message (JSONB for Command), agent_source
- Lifecycle: created_at, expires_at (24h TTL)
- Cleanup: image_path (temporary file to delete after approval)

**Usage:** Runner stores HITL context before sending approval request. Retrieves on approval/rejection to resume workflow.

---

### 6-8. LangGraph Tables (Framework-Managed)

**checkpoints:** Workflow state snapshots (thread_id, checkpoint_id, checkpoint JSON).

**checkpoint_blobs:** Binary large state objects (bytea).

**checkpoint_writes:** Incremental state writes for performance.

**Usage:** LangGraph persistence layer. Managed by framework, not application code.

**Monitoring View:** v_checkpoint_forks - Detects concurrent workflow processing (race conditions).

---

### 9. Routing History (Lightweight Analytics)

**Purpose:** High-volume routing metrics without full workflow data overhead.

**Key Attributes:**
- Link: workflow_id (FK to workflow_outcomes)
- Routing: intent, department, confidence_score
- Outcome: success, duration_seconds

**Usage:** Fast routing analytics for performance dashboards.

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

**Constraint:** Exactly ONE of product_family_id OR product_id must be set.

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

**Purpose:** B2B/B2C/D2C messaging strategies per product family.

**Key Attributes:**
- Identity: id (UUID), product_family_id (FK)
- Segment: segment_type (b2b/b2c/d2c/wholesale/enterprise/retail), segment_label
- Messaging: tone (professional/casual/technical/emotional/educational/aspirational)
- Strategy: key_benefits (array), pain_points (array)
- Channels: primary_channels (array: linkedin, instagram, email), content_formats (array: carousel, video)
- Pricing: pricing_notes
- Audit: created_at, updated_at

**Usage:** Market Intelligence Specialist defines segments. Content & SEO Specialist tailors content per segment. Marketing campaigns select target segments.

**Relationships:**
- (N) ← (1) product_families
- (1) → (N) marketing_content (segment-specific content)

**Current Data:** 0 (ready for population).

---

### 11. Marketing Content (Platform-Specific Content)

**Purpose:** Platform-specific marketing content with versioning and performance tracking.

**Multi-Workflow Design:** Serves BOTH product onboarding and marketing campaigns.

**Key Attributes:**
- Identity: id (UUID)
- Links: product_family_id (FK), product_id (FK), customer_segment_id (FK), industry_naics_code (FK), **campaign_id (FK, NEW)**, **campaign_asset_id (FK, NEW)**
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

**Constraint:** At least ONE targeting field required (product_family, product, segment, industry, OR campaign).

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

### 1. Campaigns (Campaign Orchestration)

**Purpose:** Top-level campaign metadata, budget, timeline, and lifecycle management.

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

**Status:** NEW table for marketing domain.

**Constraint:** planned_end_date >= planned_start_date.

---

### 2. Campaign Products (Promoted Products Junction)

**Purpose:** M:N junction linking campaigns to products they promote.

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

**Status:** NEW table for marketing domain.

**Constraint:** Exactly ONE of product_family_id OR product_id must be set.

---

### 3. Campaign Assets (Creative Library)

**Purpose:** Campaign-specific creative asset library (images, videos, graphics).

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

**Status:** NEW table for marketing domain.

**Note:** Separate from product_images (product photography vs campaign creative).

---

### 4. Campaign Channels (Platform Configurations)

**Purpose:** Platform-specific campaign configurations and tracking IDs.

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

**Status:** NEW table for marketing domain.

**Constraint:** UNIQUE (campaign_id, platform) - one config per campaign per platform.

---

## Platform Integration Tables (Phase 2)

### 1. Platform Credentials (Encrypted Token Storage)

**Purpose:** Encrypted storage for OAuth tokens, API keys, and platform credentials with auto-refresh capability.

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

**Status:** PHASE 2 (platform integration implementation)

**Security:**
- Encryption key NEVER stored in database
- Refresh tokens NEVER exposed to agents or prompts
- Service account pattern for Meta (system users with permanent tokens)

**Constraint:** UNIQUE (company_id, platform, account_id)

---

### 2. Platform Rate Limits (Quota Tracking)

**Purpose:** Per-platform quota tracking with adaptive throttling to prevent rate limit violations.

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

**Status:** PHASE 2 (platform integration implementation)

**Constraint:** UNIQUE (company_id, platform, limit_type)

---

### 3. Platform API Errors (Error Logging & Retry)

**Purpose:** Centralized error logging with intelligent retry tracking for platform API failures.

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

**Status:** PHASE 2 (platform integration implementation)

**Index:** idx_platform_api_errors_unresolved ON (company_id, platform, created_at DESC) WHERE resolved_at IS NULL

---

### 4. Platform Webhook Events (Real-Time Event Queue)

**Purpose:** Real-time webhook event queue for platforms that support webhooks (Meta, TikTok).

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

**Status:** PHASE 2 (platform integration implementation)

**Index:** idx_webhook_events_unprocessed ON (company_id, platform, received_at) WHERE processed = false

---

### 5. Campaign Performance (Normalized Metrics)

**Purpose:** Normalized cross-platform metrics for fast queries, aggregation, and comparison.

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

**Status:** PHASE 2 (platform integration implementation)

**Constraint:** UNIQUE (campaign_id, channel_id, date, hour)

**Indexes:**
- idx_campaign_performance_date ON (campaign_id, date DESC)
- idx_campaign_performance_channel_date ON (channel_id, date DESC)

---

### 6. Campaign Performance Raw (Platform-Specific Metrics)

**Purpose:** Platform-specific metrics in JSONB for detailed analysis and platform-unique data.

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

**Status:** PHASE 2 (platform integration implementation)

**Constraint:** UNIQUE (performance_id, platform)

---

### 7. Platform Campaign Mapping (External ID Tracking)

**Purpose:** Bi-directional mapping between AutifyME campaigns and platform campaign IDs across hierarchies.

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

**Status:** PHASE 2 (platform integration implementation)

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

## Summary Statistics

**Total Schema:**
- **34 Tables** (9 infrastructure, 14 product, 4 marketing, 7 shared)
- **9 Automatic Triggers** (price history, inventory history, audit log)
- **Multiple Views** (success rates, failures, edge cases, checkpoint forks)

**Current Data Volume:**
- **Companies:** 1 row (single-tenant)
- **Products:** 64 SKUs across 7 families
- **Variants:** 24 axes, 102 values, 45 junctions
- **Industries:** 74 NAICS codes
- **Workflows:** 1,111 tracked executions
- **Messages:** 86 processed (24h window)

**Ready for Marketing:**
- **Campaigns:** 0 (schema ready)
- **Campaign Assets:** 0 (schema ready)
- **Marketing Content:** 0 (schema ready)
- All indexes created, constraints enforced

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

**Last Updated:** 2025-10-25
**Next Review:** After marketing campaign implementation
**Related Documents:**
- DOMAIN_DESIGN_GUIDELINES.md - Architectural standards for new workflows
- ACTUAL_IMPLEMENTATION_ARCHITECTURE.md - Implementation patterns
- PRODUCT_ONBOARDING_BUILD_SUMMARY.md - Product domain reference implementation
- MARKETING_DOMAIN_ANALYSIS.md - Marketing workflow design
