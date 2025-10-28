# Complete Database Schema - AutifyME

**Exported**: 2025-10-28
**Database**: PostgreSQL (Supabase)
**Total Tables**: 31

---

## Table Overview

| Category | Tables | Purpose |
|----------|--------|---------|
| **Core Company** | companies, company_intelligence | Single-tenant company data and auto-discovered intelligence |
| **Product Catalog** | product_families, products, variant_axes, variant_values, product_variant_values | Hierarchical product structure with variants |
| **Taxonomy** | categories, industries | Hierarchical categorization and NAICS industry codes |
| **Marketing** | marketing_content, customer_segments, product_family_industries, product_images | Multi-channel content and targeting |
| **Campaigns** | campaigns, campaign_products, campaign_channels, campaign_assets | Marketing campaign management |
| **History/Audit** | product_price_history, product_inventory_history, audit_log | Temporal tracking and audit trail |
| **Workflow** | workflow_outcomes, routing_history, pending_approvals, processed_messages | Execution tracking and HITL |
| **LangGraph** | checkpoints, checkpoint_writes, checkpoint_blobs, checkpoint_migrations, store, store_migrations | Agent state persistence |

---

## Core Product Catalog Schema

### product_families
**Parent product concepts with variants (e.g., "Nike Air Max" with size/color variants)**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK, DEFAULT gen_random_uuid() | Primary key |
| product_group_id | text | UNIQUE, NOT NULL | Business identifier (e.g., 'SHOE-AIR-MAX') |
| sku_prefix | text | UNIQUE, NOT NULL | SKU prefix for all variants (e.g., 'SHOE') |
| name | text | NOT NULL | Product family name |
| description | text | NOT NULL | Family-level description |
| brand | text | NOT NULL | Brand name |
| category_id | uuid | FK → categories.id | Category classification |
| base_price | numeric | NOT NULL, >= 0 | Base price before variant adjustments |
| price_currency | text | NOT NULL, DEFAULT 'INR' | 3-letter currency code (e.g., INR, USD) |
| material | text | NULL | Material composition |
| condition | text | NOT NULL, DEFAULT 'new' | new, refurbished, used |
| lifecycle_stage | text | NOT NULL, DEFAULT 'regular' | new_arrival, regular, clearance, discontinued |
| tags | text[] | NULL, DEFAULT '{}' | Searchable tags array |
| google_product_category | text | NULL | Google taxonomy category |
| custom_attributes | jsonb | NULL, DEFAULT '{}' | Flexible key-value attributes |
| is_active | boolean | NOT NULL, DEFAULT true | Soft delete flag |
| created_at | timestamptz | NOT NULL, DEFAULT now() | Creation timestamp |
| updated_at | timestamptz | NOT NULL, DEFAULT now() | Last update timestamp |
| created_by | text | NULL | User/agent identifier |
| updated_by | text | NULL | Last updater identifier |

**Indexes**:
- `product_families_pkey` (id) - Primary key
- `product_families_product_group_id_key` (product_group_id) - Unique business ID
- `product_families_sku_prefix_key` (sku_prefix) - Unique SKU prefix
- `idx_product_families_brand` (brand) - Brand search
- `idx_product_families_category` (category_id) - Category filtering
- `idx_product_families_lifecycle` (lifecycle_stage) WHERE is_active - Active lifecycle products
- `idx_product_families_tags` (tags) GIN - Tag search
- `idx_product_families_custom` (custom_attributes) GIN - Custom attribute search

---

### products
**Individual product SKUs/variants**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK, DEFAULT gen_random_uuid() | Primary key |
| product_family_id | uuid | FK → product_families.id | Parent family |
| sku | text | UNIQUE | Unique SKU identifier (e.g., SHOE-M-RED) |
| name | text | NULL | Variant-specific name |
| description | text | NULL | Variant description |
| price | numeric | NULL | Specific price for this variant |
| stock_quantity | integer | NULL, DEFAULT 0 | Current inventory |
| availability | text | NOT NULL, DEFAULT 'in_stock' | in_stock, out_of_stock, preorder, backorder, discontinued |
| is_primary_variant | boolean | NULL, DEFAULT false | Hero variant shown first (one per family) |
| sale_price | numeric | NULL | Promotional price |
| sale_price_start | date | NULL | Sale start date |
| sale_price_end | date | NULL | Sale end date |
| link | text | NULL | Product URL |
| sizes | text[] | NULL | Legacy field |
| colors | text[] | NULL | Legacy field |
| image_urls | text[] | NULL | Legacy field |
| created_at | timestamptz | NULL, DEFAULT now() | Creation timestamp |

**Indexes**:
- `products_pkey` (id) - Primary key
- `products_sku_key` (sku) - Unique SKU
- `products_family_id_idx` (product_family_id) - Family lookup
- `products_sku_idx` (sku) - SKU search
- `products_availability_idx` (availability) - Availability filtering
- `products_one_primary_per_family` (product_family_id) WHERE is_primary_variant - One primary per family

**Constraints**:
- `products_sale_dates_check`: If sale_price set, must have start/end dates

---

### variant_axes
**Defines dimensions along which a product family varies (e.g., size, color)**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK, DEFAULT gen_random_uuid() | Primary key |
| product_family_id | uuid | FK → product_families.id, NOT NULL | Parent family |
| name | text | NOT NULL, UNIQUE per family | Snake_case name (e.g., 'size', 'color') |
| display_label | text | NOT NULL | Human-readable label (e.g., 'Size', 'Color') |
| sort_order | integer | NOT NULL, DEFAULT 0 | Display order in variant selector |
| schema_property | text | NULL | Schema.org property mapping |

**Indexes**:
- `variant_axes_pkey` (id) - Primary key
- `variant_axes_product_family_id_name_key` (product_family_id, name) - Unique axis per family
- `idx_variant_axes_family` (product_family_id) - Family lookup

**Constraints**:
- `variant_axes_name_valid`: name must match `^[a-z_]+$` (snake_case)

---

### variant_values
**Specific values for each variant axis (e.g., "Red", "Blue" for color axis)**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK, DEFAULT gen_random_uuid() | Primary key |
| variant_axis_id | uuid | FK → variant_axes.id, NOT NULL | Parent axis |
| value | text | NOT NULL, UNIQUE per axis | Actual value (e.g., 'Medium', 'Red') |
| display_label | text | NULL | Override display label if needed |
| sku_code | text | NOT NULL, UNIQUE per axis | SKU component code (e.g., 'M', 'RED') |
| color_hex | text | NULL | Hex color code if axis is 'color' (e.g., #FF0000) |
| image_url | text | NULL | Swatch image if needed |
| price_adjustment | numeric | NULL, DEFAULT 0 | Price delta vs base price |
| sort_order | integer | NOT NULL, DEFAULT 0 | Display order |
| is_active | boolean | NOT NULL, DEFAULT true | Soft delete flag |

**Indexes**:
- `variant_values_pkey` (id) - Primary key
- `variant_values_variant_axis_id_value_key` (variant_axis_id, value) - Unique value per axis
- `variant_values_variant_axis_id_sku_code_key` (variant_axis_id, sku_code) - Unique SKU code per axis
- `idx_variant_values_axis` (variant_axis_id) - Axis lookup
- `idx_variant_values_active` (is_active) WHERE is_active - Active values

**Constraints**:
- `variant_values_sku_code_valid`: sku_code must match `^[A-Z0-9-]+$` (uppercase)
- `variant_values_color_hex_valid`: color_hex must match `^#[0-9A-Fa-f]{6}$`

---

### product_variant_values
**M:N junction linking products to their variant dimension values**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK, DEFAULT gen_random_uuid() | Primary key |
| product_id | uuid | FK → products.id, NOT NULL | Product SKU |
| variant_value_id | uuid | FK → variant_values.id, NOT NULL | Variant value |
| created_at | timestamptz | NOT NULL, DEFAULT now() | Creation timestamp |

**Indexes**:
- `product_variant_values_pkey` (id) - Primary key
- `product_variant_values_product_id_variant_value_id_key` (product_id, variant_value_id) - Unique junction
- `product_variant_values_product_idx` (product_id) - Product lookup
- `product_variant_values_value_idx` (variant_value_id) - Value lookup

---

## Marketing & Content Schema

### marketing_content
**Platform-specific marketing content with versioning and performance tracking**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK, DEFAULT gen_random_uuid() | Primary key |
| product_family_id | uuid | FK → product_families.id | Family-level content |
| product_id | uuid | FK → products.id | SKU-specific content |
| customer_segment_id | uuid | FK → customer_segments.id | Segment-targeted content |
| industry_naics_code | text | FK → industries.naics_code | Industry-targeted content |
| campaign_id | uuid | FK → campaigns.id | Campaign content |
| campaign_asset_id | uuid | FK → campaign_assets.id | Campaign asset reference |
| platform | text | NOT NULL | instagram, facebook, twitter, linkedin, youtube, tiktok, website, email, catalog |
| content_type | text | NOT NULL | post, story, reel, video, carousel, ad, description, title, caption, subject_line, catalog_description |
| content_text | text | NOT NULL | Actual content text |
| content_metadata | jsonb | NULL, DEFAULT '{}' | Platform-specific metadata (aspect_ratio, duration, CTA) |
| hashtags | text[] | NULL, DEFAULT '{}' | Hashtags array |
| keywords | text[] | NULL, DEFAULT '{}' | Keywords for SEO |
| meta_title | text | NULL | SEO title |
| meta_description | text | NULL | SEO description |
| version | integer | NOT NULL, DEFAULT 1 | Auto-incremented version for A/B testing |
| is_active | boolean | NULL, DEFAULT true | Only one active version per combo |
| impressions | integer | NULL, DEFAULT 0 | View count |
| clicks | integer | NULL, DEFAULT 0 | Click count |
| conversions | integer | NULL, DEFAULT 0 | Conversion count |
| generated_by | text | NULL | User/agent identifier |
| generation_prompt_version | text | NULL | AI prompt version tracker |
| created_at | timestamptz | NOT NULL, DEFAULT now() | Creation timestamp |
| updated_at | timestamptz | NOT NULL, DEFAULT now() | Last update timestamp |
| published_at | timestamptz | NULL | Publication timestamp |

**Indexes**: 15+ indexes for performance (family, product, platform, segment, industry, campaign, hashtags, keywords, metadata, published date)

**Constraints**:
- `chk_marketing_content_target`: At least ONE of product_family_id, product_id, customer_segment_id, industry_naics_code, campaign_id must be set
- `marketing_content_exclusive_parent`: product_id and product_family_id are mutually exclusive (XOR)
- `marketing_content_active_version`: Only one active version per (product_family_id, product_id, platform, content_type, customer_segment_id, industry_naics_code) WHERE is_active

---

### customer_segments
**B2B/B2C/D2C messaging strategies per product family or campaign**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK, DEFAULT gen_random_uuid() | Primary key |
| product_family_id | uuid | FK → product_families.id | Product segment |
| campaign_id | uuid | FK → campaigns.id | Campaign segment |
| segment_type | text | NOT NULL, UNIQUE per family | b2b, b2c, d2c, wholesale, enterprise, retail |
| segment_label | text | NOT NULL | Human-readable label |
| tone | text | NOT NULL | professional, casual, technical, emotional, educational, aspirational |
| key_benefits | text[] | NOT NULL, DEFAULT '{}' | Benefits array |
| pain_points | text[] | NOT NULL, DEFAULT '{}' | Pain points array |
| primary_channels | text[] | NOT NULL, DEFAULT '{}' | Preferred channels (linkedin, instagram, email) |
| content_formats | text[] | NOT NULL, DEFAULT '{}' | Preferred formats (carousel, video, infographic) |
| pricing_notes | text | NULL | Pricing strategy notes |
| created_at | timestamptz | NOT NULL, DEFAULT now() | Creation timestamp |
| updated_at | timestamptz | NOT NULL, DEFAULT now() | Last update timestamp |

**Indexes**:
- `customer_segments_pkey` (id) - Primary key
- `customer_segments_product_family_id_segment_type_key` (product_family_id, segment_type) - Unique segment per family
- `customer_segments_family_idx` (product_family_id) - Family lookup
- `customer_segments_type_idx` (segment_type) - Type filtering
- `idx_customer_segments_campaign` (campaign_id) WHERE campaign_id IS NOT NULL - Campaign segments

**Constraints**:
- `chk_segment_ownership`: Exactly ONE of product_family_id or campaign_id must be set (XOR)

---

### product_family_industries
**M:N junction for multi-industry targeting (e.g., water bottle → healthcare, sports, corporate)**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK, DEFAULT gen_random_uuid() | Primary key |
| product_family_id | uuid | FK → product_families.id, NOT NULL | Product family |
| industry_naics_code | text | FK → industries.naics_code, NOT NULL | NAICS industry code |
| industry_use_case | text | NULL | How product solves problems in this industry |
| industry_benefits | text[] | NOT NULL, DEFAULT '{}' | Industry-specific benefits |
| compliance_notes | text | NULL | Regulatory compliance notes |
| is_primary_industry | boolean | NULL, DEFAULT false | Primary target industry (one per family) |
| created_at | timestamptz | NOT NULL, DEFAULT now() | Creation timestamp |

**Indexes**:
- `product_family_industries_pkey` (id) - Primary key
- `product_family_industries_product_family_id_industry_naics__key` (product_family_id, industry_naics_code) - Unique junction
- `product_family_industries_family_idx` (product_family_id) - Family lookup
- `product_family_industries_naics_idx` (industry_naics_code) - NAICS lookup
- `product_family_industries_one_primary` (product_family_id) WHERE is_primary_industry - One primary per family

---

### product_images
**Multi-level image storage: family-level (shared) or variant-specific images**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK, DEFAULT gen_random_uuid() | Primary key |
| product_family_id | uuid | FK → product_families.id | Family-level image |
| product_id | uuid | FK → products.id | Variant-specific image |
| url | text | NOT NULL | Image URL or path |
| alt_text | text | NULL | Accessibility text |
| image_type | text | NOT NULL | primary, gallery, thumbnail, lifestyle, closeup, video_thumbnail |
| display_order | integer | NOT NULL, DEFAULT 0 | Sort order |
| width | integer | NULL | Image width in pixels |
| height | integer | NULL | Image height in pixels |
| file_size_bytes | integer | NULL | File size |
| whatsapp_media_id | text | NULL | WhatsApp media ID |
| is_primary | boolean | NULL, DEFAULT false | Hero image shown first |
| created_at | timestamptz | NOT NULL, DEFAULT now() | Creation timestamp |
| updated_at | timestamptz | NOT NULL, DEFAULT now() | Last update timestamp |

**Indexes**:
- `product_images_pkey` (id) - Primary key
- `product_images_family_idx` (product_family_id) - Family lookup
- `product_images_product_idx` (product_id) - Product lookup
- `product_images_order_idx` (display_order) - Sort order
- `product_images_whatsapp_idx` (whatsapp_media_id) - WhatsApp media lookup
- `product_images_one_primary_per_family` (product_family_id) WHERE is_primary AND product_family_id IS NOT NULL
- `product_images_one_primary_per_product` (product_id) WHERE is_primary AND product_id IS NOT NULL

**Constraints**:
- `product_images_exclusive_parent`: product_id and product_family_id are mutually exclusive (XOR)

---

## Taxonomy Schema

### categories
**Hierarchical product taxonomy**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK, DEFAULT gen_random_uuid() | Primary key |
| parent_id | uuid | FK → categories.id, SELF-REFERENCING | Parent category |
| name | text | NOT NULL | Category name |
| slug | text | UNIQUE, NOT NULL | URL-friendly slug |
| description | text | NULL | Category description |
| google_product_category | text | NULL | Google taxonomy mapping |
| sort_order | integer | NOT NULL, DEFAULT 0 | Display order |
| is_active | boolean | NOT NULL, DEFAULT true | Soft delete flag |
| created_at | timestamptz | NOT NULL, DEFAULT now() | Creation timestamp |
| updated_at | timestamptz | NOT NULL, DEFAULT now() | Last update timestamp |

**Indexes**:
- `categories_pkey` (id) - Primary key
- `categories_slug_key` (slug) - Unique slug
- `idx_categories_parent` (parent_id) - Hierarchy traversal
- `idx_categories_slug` (slug) - Slug lookup
- `idx_categories_active` (is_active) WHERE is_active - Active categories

**Constraints**:
- `categories_no_self_reference`: parent_id != id (no self-loops)

---

### industries
**NAICS 2022 industry classification (hierarchical taxonomy)**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| naics_code | text | PK | 2-6 digit NAICS code (e.g., 311, 31199, 311999) |
| parent_code | text | FK → industries.naics_code, SELF-REFERENCING | Parent NAICS code |
| label | text | NOT NULL | Industry name |
| description | text | NULL | Industry description |
| level | integer | NOT NULL | Hierarchy level (1-6) |
| is_active | boolean | NOT NULL, DEFAULT true | Active flag |
| naics_year | integer | NOT NULL, DEFAULT 2022 | NAICS taxonomy year |

**Indexes**:
- `industries_pkey` (naics_code) - Primary key
- `idx_industries_parent` (parent_code) - Hierarchy traversal
- `idx_industries_level` (level) - Level filtering
- `idx_industries_label` (label) - Label search

**Constraints**:
- `industries_naics_code_check`: length(naics_code) BETWEEN 2 AND 6
- `industries_level_check`: level BETWEEN 1 AND 6
- `industries_check`: If parent_code IS NOT NULL, parent_code != naics_code

---

## Temporal & Audit Schema

### product_price_history
**Temporal table tracking all price changes with valid_from/valid_to intervals**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK, DEFAULT gen_random_uuid() | Primary key |
| product_id | uuid | FK → products.id, NOT NULL | Product SKU |
| price | numeric | NOT NULL | Regular price |
| sale_price | numeric | NULL | Promotional price |
| sale_price_start | date | NULL | Sale start date |
| sale_price_end | date | NULL | Sale end date |
| valid_from | timestamptz | NOT NULL, DEFAULT now() | Validity start |
| valid_to | timestamptz | NULL | Validity end (NULL = current) |
| changed_by | text | NULL | User/agent identifier |
| change_reason | text | NULL | Change justification |
| created_at | timestamptz | NOT NULL, DEFAULT now() | Creation timestamp |

**Indexes**:
- `product_price_history_pkey` (id) - Primary key
- `product_price_history_product_idx` (product_id) - Product lookup
- `product_price_history_valid_idx` (valid_from, valid_to) - Temporal queries

**Note**: Automatically populated by database trigger on products.price UPDATE

---

### product_inventory_history
**Temporal table tracking all inventory changes with valid_from/valid_to intervals**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK, DEFAULT gen_random_uuid() | Primary key |
| product_id | uuid | FK → products.id, NOT NULL | Product SKU |
| stock_quantity | integer | NOT NULL | Stock quantity |
| availability | text | NOT NULL | in_stock, out_of_stock, preorder, backorder, discontinued |
| valid_from | timestamptz | NOT NULL, DEFAULT now() | Validity start |
| valid_to | timestamptz | NULL | Validity end (NULL = current) |
| changed_by | text | NULL | User/agent identifier |
| change_reason | text | NULL | Change justification |
| created_at | timestamptz | NOT NULL, DEFAULT now() | Creation timestamp |

**Indexes**:
- `product_inventory_history_pkey` (id) - Primary key
- `product_inventory_history_product_idx` (product_id) - Product lookup
- `product_inventory_history_valid_idx` (valid_from, valid_to) - Temporal queries

**Note**: Automatically populated by database trigger on products.stock_quantity UPDATE

---

### audit_log
**Universal audit trail for all table changes with full JSONB snapshots**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK, DEFAULT gen_random_uuid() | Primary key |
| table_name | text | NOT NULL | Table being audited |
| record_id | uuid | NOT NULL | Record primary key |
| operation | text | NOT NULL | INSERT, UPDATE, DELETE |
| old_values | jsonb | NULL | Complete JSONB snapshot before change |
| new_values | jsonb | NULL | Complete JSONB snapshot after change |
| changed_fields | text[] | NULL, DEFAULT '{}' | Array of field names that changed (UPDATE only) |
| changed_by | text | NULL | User/agent identifier |
| changed_at | timestamptz | NOT NULL, DEFAULT now() | Change timestamp |
| change_reason | text | NULL | Change justification |
| session_id | text | NULL | Session identifier |
| ip_address | inet | NULL | Client IP address |
| user_agent | text | NULL | Client user agent |

**Indexes**:
- `audit_log_pkey` (id) - Primary key
- `audit_log_table_idx` (table_name) - Table filtering
- `audit_log_record_idx` (record_id) - Record history
- `audit_log_changed_at_idx` (changed_at) - Temporal queries
- `audit_log_changed_by_idx` (changed_by) - User activity
- `audit_log_old_values_idx` (old_values) GIN - JSONB queries
- `audit_log_new_values_idx` (new_values) GIN - JSONB queries

**Note**: Automatically populated by database triggers on ALL tables

---

## Campaign Schema

### campaigns
**Marketing campaigns with budget, timeline, and performance tracking**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK, DEFAULT gen_random_uuid() | Primary key |
| campaign_id | text | UNIQUE, NOT NULL | Business-friendly campaign identifier |
| name | text | NOT NULL | Campaign name |
| description | text | NULL | Campaign description |
| campaign_type | text | NOT NULL | product_launch, seasonal, promotional, awareness, retention, acquisition |
| campaign_category | text | NULL | Custom category |
| primary_objective | text | NOT NULL | sales, awareness, engagement, traffic, leads, retention |
| secondary_objectives | text[] | NULL | Additional objectives |
| target_audience_description | text | NULL | Audience description |
| total_budget | numeric | NULL, >= 0 | Total campaign budget |
| budget_currency | text | NULL, DEFAULT 'INR' | Currency code |
| budget_allocation | jsonb | NULL, DEFAULT '{}' | Per-channel budget breakdown |
| planned_start_date | date | NOT NULL | Planned start |
| planned_end_date | date | NOT NULL | Planned end |
| actual_start_date | date | NULL | Actual start |
| actual_end_date | date | NULL | Actual end |
| status | text | NULL, DEFAULT 'draft' | draft, approved, scheduled, active, paused, completed, cancelled |
| approval_status | text | NULL, DEFAULT 'pending' | pending, approved, rejected, revision_requested |
| approved_by | text | NULL | Approver identifier |
| approved_at | timestamptz | NULL | Approval timestamp |
| target_metrics | jsonb | NULL, DEFAULT '{}' | KPI targets (impressions, conversions) |
| total_impressions | bigint | NULL, DEFAULT 0 | Total impressions |
| total_clicks | bigint | NULL, DEFAULT 0 | Total clicks |
| total_conversions | integer | NULL, DEFAULT 0 | Total conversions |
| total_spend | numeric | NULL, DEFAULT 0 | Total spend |
| generated_by | text | NULL | Creator identifier |
| generation_prompt_version | text | NULL | AI prompt version |
| specialist_versions | jsonb | NULL, DEFAULT '{}' | Specialist version tracking |
| created_at | timestamptz | NULL, DEFAULT now() | Creation timestamp |
| updated_at | timestamptz | NULL, DEFAULT now() | Last update timestamp |
| created_by | text | NULL | Creator |
| updated_by | text | NULL | Last updater |

**Indexes**: 5 indexes for status, type, dates, start date

**Constraints**:
- `campaigns_check`: planned_end_date >= planned_start_date

---

## Workflow & HITL Schema

### workflow_outcomes
**Complete workflow execution records for agentic learning**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK, DEFAULT gen_random_uuid() | Primary key |
| tracking_id | text | UNIQUE, NOT NULL | Unique execution identifier |
| thread_id | text | NOT NULL | LangGraph thread ID |
| sender_id | text | NOT NULL | User/sender identifier |
| message_text | text | NULL | Input message |
| message_hash | text | NOT NULL | SHA-256 hash for deduplication |
| media_id | text | NULL | Media identifier |
| media_type | text | NULL | Media type |
| platform | text | NULL, DEFAULT 'whatsapp' | Source platform |
| received_at | timestamptz | NOT NULL | Message received timestamp |
| intent | text | NULL | Detected intent |
| department | text | NULL | Routed department |
| routing_reasoning | text | NULL | Routing explanation |
| routing_confidence | float | NULL | Routing confidence score |
| alternative_departments | text[] | NULL | Alternative routing options |
| routed_at | timestamptz | NULL | Routing timestamp |
| success | boolean | NOT NULL | Execution success flag |
| error_type | text | NULL | Error classification |
| error_message | text | NULL | Error details |
| resolution_strategy | text | NULL | Error resolution approach |
| result_data | jsonb | NULL | Execution results |
| duration_seconds | float | NULL | Execution duration |
| started_at | timestamptz | NOT NULL | Execution start |
| ended_at | timestamptz | NULL | Execution end |
| learned_patterns | jsonb | NULL, DEFAULT '[]' | Success patterns for learning |
| failure_warnings | jsonb | NULL, DEFAULT '[]' | Failure cases for learning |
| applied_strategies | text[] | NULL | Applied strategies |
| created_at | timestamptz | NULL, DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| updated_at | timestamptz | NULL, DEFAULT CURRENT_TIMESTAMP | Last update timestamp |
| trace_id | text | NULL | LangSmith trace ID |

**Indexes**: 10+ indexes for thread, tracking, message hash, intent, department, success, failures, trace

---

### pending_approvals
**HITL interrupt context to survive server restarts**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK, DEFAULT gen_random_uuid() | Primary key |
| thread_id | text | NOT NULL, UNIQUE with interrupt_id | LangGraph thread_id |
| interrupt_id | text | NOT NULL, UNIQUE with thread_id | LangGraph Interrupt.id |
| checkpoint_id | text | NOT NULL | Checkpoint ID where interrupt occurred |
| checkpoint_ns | text | NULL | Checkpoint namespace for resumption |
| tool_call | jsonb | NOT NULL | Tool call that triggered interrupt |
| draft_summary | text | NOT NULL | Human-readable summary for approval |
| ai_message | jsonb | NULL | AIMessage that initiated tool call |
| agent_source | text | NOT NULL, DEFAULT 'cataloging_department' | Agent that triggered interrupt |
| image_path | text | NULL | Temporary image file path |
| created_at | timestamptz | NOT NULL, DEFAULT now() | Creation timestamp |
| expires_at | timestamptz | NOT NULL, DEFAULT now() + 24 hours | Auto-cleanup after 24 hours |

**Indexes**:
- `pending_approvals_pkey` (id) - Primary key
- `pending_approvals_thread_id_interrupt_id_key` (thread_id, interrupt_id) - Unique per thread
- `idx_pending_approvals_thread_id` (thread_id) - Thread lookup
- `idx_pending_approvals_expires_at` (expires_at) - Cleanup queries

---

## Company & Intelligence Schema

### companies
**Single-tenant: exactly 1 company (enforced by unique index on `true`)**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK, DEFAULT gen_random_uuid() | Primary key |
| name | text | NOT NULL | Company name |
| legal_name | text | NULL | Legal entity name |
| domain | text | NULL | Primary domain |
| description | text | NULL | Company description |
| brand_voice | text | NULL | Brand voice description |
| brand_attributes | jsonb | NULL | Brand attributes object |
| target_audience | text | NULL | Target audience description |
| target_markets | text[] | NULL | Target markets array |
| website | text | NULL | Website URL |
| email | text | NULL | Contact email (validated) |
| phone | text | NULL | Contact phone |
| address_line1 | text | NULL | Address line 1 |
| address_line2 | text | NULL | Address line 2 |
| city | text | NULL | City |
| state | text | NULL | State/province |
| postal_code | text | NULL | Postal/ZIP code |
| country | text | NOT NULL, DEFAULT 'IN' | Country code |
| default_currency | text | NOT NULL, DEFAULT 'INR' | Default currency |
| default_timezone | text | NOT NULL, DEFAULT 'Asia/Kolkata' | Default timezone |
| created_at | timestamptz | NULL, DEFAULT now() | Creation timestamp |

**Indexes**:
- `companies_pkey` (id) - Primary key
- `only_one_company` ((true)) - UNIQUE - Enforces single row

**Constraints**:
- `companies_email_valid`: email matches email regex pattern

---

### company_intelligence
**Auto-discovered company intelligence (single row)**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK, DEFAULT gen_random_uuid() | Primary key |
| business_models | text[] | NOT NULL, DEFAULT '{}' | B2B, B2C, D2C |
| brand_voice | text | NULL | Auto-discovered brand voice |
| brand_values | text[] | NULL, DEFAULT '{}' | Brand values array |
| target_audiences | jsonb | NULL, DEFAULT '[]' | Target audiences JSONB |
| visual_identity | jsonb | NULL, DEFAULT '{}' | Visual identity object |
| price_positioning | text | NULL | budget, mid-range, premium, luxury |
| competitors | jsonb | NULL, DEFAULT '[]' | Competitors JSONB array |
| confidence_score | real | NULL, 0-1 | Discovery confidence score |
| sources | text[] | NULL, DEFAULT '{}' | Discovery sources |
| discovered_at | timestamptz | NOT NULL, DEFAULT now() | Discovery timestamp |
| last_updated | timestamptz | NOT NULL, DEFAULT now() | Last update timestamp |

**Indexes**:
- `company_intelligence_pkey` (id) - Primary key
- `only_one_company_intelligence` ((true)) - UNIQUE - Enforces single row
- `idx_company_intelligence_brand_voice` (brand_voice) - Brand voice search
- `idx_company_intelligence_target_audiences` (target_audiences) GIN - Audience search
- `idx_company_intelligence_competitors` (competitors) GIN - Competitor search

---

## LangGraph Persistence Schema

### checkpoints
**LangGraph agent state checkpoints**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| thread_id | text | PK (composite) | Thread identifier |
| checkpoint_ns | text | PK (composite), DEFAULT '' | Checkpoint namespace |
| checkpoint_id | text | PK (composite) | Checkpoint identifier |
| parent_checkpoint_id | text | NULL | Parent checkpoint |
| type | text | NULL | Checkpoint type |
| checkpoint | jsonb | NOT NULL | State snapshot |
| metadata | jsonb | NOT NULL, DEFAULT '{}' | Metadata object |

**Indexes**:
- `checkpoints_pkey` (thread_id, checkpoint_ns, checkpoint_id) - Composite primary key
- `checkpoints_thread_id_idx` (thread_id) - Thread lookup

---

### checkpoint_writes
**Pending writes for checkpoints**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| thread_id | text | PK (composite) | Thread identifier |
| checkpoint_ns | text | PK (composite), DEFAULT '' | Checkpoint namespace |
| checkpoint_id | text | PK (composite) | Checkpoint identifier |
| task_id | text | PK (composite) | Task identifier |
| idx | integer | PK (composite) | Write index |
| channel | text | NOT NULL | Channel name |
| task_path | text | NOT NULL, DEFAULT '' | Task path |
| type | text | NULL | Write type |
| blob | bytea | NOT NULL | Write data |

**Indexes**:
- `checkpoint_writes_pkey` (thread_id, checkpoint_ns, checkpoint_id, task_id, idx) - Composite primary key
- `checkpoint_writes_thread_id_idx` (thread_id) - Thread lookup

---

### checkpoint_blobs
**Binary blob storage for checkpoints**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| thread_id | text | PK (composite) | Thread identifier |
| checkpoint_ns | text | PK (composite), DEFAULT '' | Checkpoint namespace |
| channel | text | PK (composite) | Channel name |
| version | text | PK (composite) | Version identifier |
| type | text | NOT NULL | Blob type |
| blob | bytea | NULL | Binary data |

**Indexes**:
- `checkpoint_blobs_pkey` (thread_id, checkpoint_ns, channel, version) - Composite primary key
- `checkpoint_blobs_thread_id_idx` (thread_id) - Thread lookup

---

### store
**LangGraph key-value store**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| prefix | text | PK (composite) | Key prefix |
| key | text | PK (composite) | Key |
| value | jsonb | NOT NULL | Value object |
| created_at | timestamptz | NULL, DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| updated_at | timestamptz | NULL, DEFAULT CURRENT_TIMESTAMP | Last update timestamp |
| expires_at | timestamptz | NULL | Expiration timestamp |
| ttl_minutes | integer | NULL | TTL in minutes |

**Indexes**:
- `store_pkey` (prefix, key) - Composite primary key
- `store_prefix_idx` (prefix text_pattern_ops) - Prefix pattern matching
- `idx_store_expires_at` (expires_at) WHERE expires_at IS NOT NULL - Expiration cleanup

---

## Message Processing Schema

### processed_messages
**Idempotency tracking for WhatsApp webhook deduplication**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| message_id | text | PK | WhatsApp unique message ID |
| sender_id | text | NOT NULL | Sender identifier |
| thread_id | text | NOT NULL | Thread identifier |
| received_at | timestamptz | NOT NULL | Receipt timestamp |
| processed_at | timestamptz | NULL, DEFAULT now() | Processing timestamp |
| expires_at | timestamptz | NULL, DEFAULT now() + 24 hours | Auto-cleanup after 24 hours |
| created_at | timestamptz | NULL, DEFAULT now() | Creation timestamp |

**Indexes**:
- `processed_messages_pkey` (message_id) - Primary key
- `idx_processed_messages_sender` (sender_id, created_at DESC) - Sender history
- `idx_processed_messages_expires` (expires_at) WHERE expires_at IS NOT NULL - Cleanup queries

---

## Key Database Features

### Automatic Triggers

1. **audit_log population**: ALL tables have triggers that populate audit_log on INSERT/UPDATE/DELETE
2. **product_price_history**: Trigger on products.price UPDATE
3. **product_inventory_history**: Trigger on products.stock_quantity UPDATE
4. **updated_at timestamps**: Auto-updated on row changes

### Single-Tenant Enforcement

- `companies` table: `only_one_company` index on `(true)` enforces single row
- `company_intelligence` table: `only_one_company_intelligence` index on `(true)` enforces single row

### Referential Integrity

- **Cascade deletes**: Most foreign keys use ON DELETE CASCADE
- **Hierarchical self-references**: categories.parent_id, industries.parent_code
- **Mutual exclusivity**: Check constraints enforce XOR relationships (e.g., product_images must reference EITHER family OR product, not both)

### Performance Optimizations

- **GIN indexes** for JSONB columns (custom_attributes, content_metadata, audit snapshots)
- **GIN indexes** for array columns (tags, hashtags, keywords)
- **Partial indexes** for common filters (is_active, is_primary, WHERE clauses)
- **Composite indexes** for common join patterns
- **Text pattern indexes** for LIKE queries

### Data Validation

- **Check constraints**: Enum-like validation (availability, status, platform, content_type)
- **Regex patterns**: SKU codes, color hex, email validation
- **Numeric ranges**: Confidence scores (0-1), positive prices
- **Date logic**: Sale dates, planned vs actual dates

---

## Schema Statistics

- **Total Tables**: 31
- **Core Product Tables**: 6 (families, products, axes, values, junctions, images)
- **Marketing Tables**: 4 (content, segments, industries, images)
- **Campaign Tables**: 4 (campaigns, products, channels, assets)
- **Temporal/Audit Tables**: 3 (price history, inventory history, audit log)
- **Workflow Tables**: 4 (outcomes, routing, approvals, processed messages)
- **LangGraph Tables**: 6 (checkpoints, writes, blobs, store, migrations x2)
- **System Tables**: 4 (companies, intelligence, categories, industries)

**Total Indexes**: 150+
**Total Foreign Keys**: 50+
**Total Check Constraints**: 60+
**Total Unique Constraints**: 40+

---

## Entity Relationship Summary

```
companies (1)
    └─> product_families (N)
            ├─> variant_axes (N)
            │       └─> variant_values (N)
            ├─> products (N)
            │       ├─> product_variant_values (M:N) ─> variant_values
            │       ├─> product_images (N)
            │       ├─> product_price_history (N)
            │       └─> product_inventory_history (N)
            ├─> product_family_industries (M:N) ─> industries
            ├─> customer_segments (N)
            ├─> product_images (N)
            └─> marketing_content (N)

campaigns (N)
    ├─> campaign_products (M:N) ─> product_families/products
    ├─> campaign_channels (N)
    ├─> campaign_assets (N)
    ├─> customer_segments (N)
    └─> marketing_content (N)

categories (hierarchical tree)
industries (hierarchical tree via NAICS)

workflow_outcomes (N)
    └─> routing_history (N)

LangGraph (thread-based state management)
    ├─> checkpoints
    ├─> checkpoint_writes
    ├─> checkpoint_blobs
    └─> store

audit_log (captures ALL table changes)
```

---

**End of Schema Document**
