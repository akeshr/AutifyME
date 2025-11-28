# Product Data Model v2

**Created:** 2025-11-25
**Status:** Draft - Design Phase
**Last Updated:** 2025-11-25
**Authors:** Abhishek, Jarvis (AI)

---

## Executive Summary

Universal product data model for Indian MSMEs supporting:
- **All business types**: Manufacturers, assemblers, traders, mixed
- **All sales channels**: B2B, D2C, online, offline, wholesale, retail
- **All product types**: Raw materials, components, finished goods, packs, bundles, services
- **Complete lifecycle**: Cataloging, manufacturing (BOM), inventory, pricing, marketing assets

**Design Principles:**
1. "Product" terminology (SAP S/4HANA standard)
2. SKU-level BOM for maximum flexibility
3. Universal UoM system with product-specific conversions
4. Sales packs as products, logistics packaging as configuration
5. Single-tenant architecture
6. Extensible via JSONB custom attributes

---

## Table of Contents

1. [Domain Overview](#1-domain-overview)
2. [Domain 1: Product Master](#2-domain-1-product-master)
3. [Domain 2: Variant System](#3-domain-2-variant-system)
4. [Domain 3: Unit of Measure](#4-domain-3-unit-of-measure)
5. [Domain 4: Bill of Materials](#5-domain-4-bill-of-materials)
6. [Domain 5: Packaging Configuration](#6-domain-5-packaging-configuration)
7. [Domain 6: Pricing](#7-domain-6-pricing)
8. [Domain 7: Inventory](#8-domain-7-inventory)
9. [Domain 8: Suppliers](#9-domain-8-suppliers)
10. [Domain 9: Digital Assets](#10-domain-9-digital-assets)
11. [Relationships Diagram](#11-relationships-diagram)
12. [Example Scenarios](#12-example-scenarios)
13. [Open Questions](#13-open-questions)
14. [Decision Log](#14-decision-log)

---

## 1. Domain Overview

### 1.1 Business Models Supported

| Business Type | Description | Example |
|---------------|-------------|---------|
| **Manufacturer** | Makes products from raw materials | Pavisha (bottles from granules) |
| **Assembler** | Buys components, assembles final products | Electronics company |
| **Trader** | Buys finished goods, resells | Wholesaler, distributor |
| **Mixed** | Combination of above | Most MSMEs |

### 1.2 Product Lifecycle

```
RAW_MATERIAL --> COMPONENT --> FINISHED_GOOD --> PACK --> BUNDLE
    |               |              |              |          |
(PET granules) (Preforms)     (Bottles)      (6-pack)   (Gift set)
    |               |              |              |          |
 Purchased      Manufactured   Manufactured   Manufactured  Assembled
                or Purchased   or Assembled   (BOM: 6x bottle)
```

### 1.3 Schema Domains

| Domain | Tables | Purpose |
|--------|--------|---------|
| **Product Master** | products, product_families, product_categories | Core product data |
| **Variants** | variant_axes, variant_values, product_variant_values | Product variations |
| **UoM** | uom, uom_conversion, product_uom_conversion | Unit handling |
| **BOM** | bom, bom_lines | Manufacturing recipes |
| **Packaging** | packaging_configs | Logistics packaging |
| **Pricing** | price_lists, product_prices, customer_prices | Complex pricing |
| **Inventory** | locations, batches, inventory, inventory_transactions | Stock management |
| **Suppliers** | suppliers, supplier_products | Procurement |
| **Assets** | assets, product_assets, asset_composition_rules | Digital assets |

**Total Tables: 22**

---

## 2. Domain 1: Product Master

### 2.1 Enumerations

```sql
-- Product type classification
CREATE TYPE product_type AS ENUM (
    'RAW_MATERIAL',      -- Inputs (granules, fabrics, chemicals)
    'COMPONENT',         -- Intermediate (preforms, caps, labels)
    'FINISHED_GOOD',     -- Complete products (bottles, jars)
    'PACK',              -- Sales packaging (6-pack, 12-pack)
    'BUNDLE',            -- Multiple different products (gift set)
    'SERVICE'            -- Future: installation, consultation
);

-- Product lifecycle status
CREATE TYPE product_status AS ENUM (
    'DRAFT',             -- Being created, not ready
    'ACTIVE',            -- Available for use
    'DISCONTINUED',      -- No longer produced/sold
    'ARCHIVED'           -- Historical, hidden from lists
);

-- Lifecycle stage for marketing
CREATE TYPE lifecycle_stage AS ENUM (
    'NEW_ARRIVAL',       -- Recently launched
    'REGULAR',           -- Standard product
    'CLEARANCE',         -- Being cleared out
    'END_OF_LIFE'        -- Final stock
);
```

### 2.2 Table: product_categories

Hierarchical categorization for catalog organization.

```sql
CREATE TABLE product_categories (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Hierarchy
    parent_id UUID REFERENCES product_categories(id),

    -- Core fields
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,

    -- Display
    image_url VARCHAR(2048),
    sort_order INT DEFAULT 0,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_category_parent ON product_categories(parent_id);
CREATE INDEX idx_category_slug ON product_categories(slug);
```

**Example Data:**
```
- Packaging (root)
  - Bottles
    - PET Bottles
    - Glass Bottles
  - Jars
  - Caps & Closures
- Raw Materials (root)
  - Polymers
    - PET
    - PP
    - HDPE
```

### 2.3 Table: product_families

Groups related products (variants) together. Optional - standalone products don't need a family.

```sql
CREATE TABLE product_families (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_group_id VARCHAR(100) NOT NULL UNIQUE,  -- Business ID: BOTTLE-500ML

    -- Core fields
    name VARCHAR(255) NOT NULL,
    description TEXT,
    sku_prefix VARCHAR(50) NOT NULL,                -- SKU prefix: PAV-BTL-500

    -- Classification
    category_id UUID REFERENCES product_categories(id),
    brand VARCHAR(100),

    -- Base pricing (variants adjust from this)
    base_price DECIMAL(18,4),
    price_currency VARCHAR(3) DEFAULT 'INR',

    -- E-commerce
    google_product_category VARCHAR(255),

    -- Extensibility
    custom_attributes JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255),
    updated_by VARCHAR(255)
);

-- Indexes
CREATE INDEX idx_family_category ON product_families(category_id);
CREATE INDEX idx_family_brand ON product_families(brand);
CREATE INDEX idx_family_sku_prefix ON product_families(sku_prefix);
```

### 2.4 Table: products

**Unified product master - ALL product types in one table.**

This is the core table. Every SKU is a row here, regardless of whether it's raw material, component, finished good, or pack.

```sql
CREATE TABLE products (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(500) NOT NULL,
    description TEXT,

    -- Classification
    product_type product_type NOT NULL,
    product_family_id UUID REFERENCES product_families(id),  -- NULL for standalone
    category_id UUID REFERENCES product_categories(id),
    brand VARCHAR(100),

    -- Material/Physical info (for physical products)
    material VARCHAR(100),                  -- PET, PP, Cotton, etc.
    weight_grams DECIMAL(10,3),             -- Unit weight
    dimensions_json JSONB,                  -- {length, width, height, unit}

    -- UoM Configuration
    base_uom_id UUID NOT NULL REFERENCES uom(id),       -- Base unit for this product
    purchase_uom_id UUID REFERENCES uom(id),            -- How we buy it
    inventory_uom_id UUID REFERENCES uom(id),           -- How we count stock
    sales_uom_id UUID REFERENCES uom(id),               -- How we sell it

    -- Pricing
    base_price DECIMAL(18,4),               -- Base selling price
    cost_price DECIMAL(18,4),               -- Standard cost
    price_currency VARCHAR(3) DEFAULT 'INR',

    -- Behavior flags
    is_purchasable BOOLEAN DEFAULT FALSE,   -- Can be bought from suppliers
    is_manufacturable BOOLEAN DEFAULT FALSE, -- Has BOM, can be produced
    is_sellable BOOLEAN DEFAULT FALSE,      -- Can be sold to customers
    is_stockable BOOLEAN DEFAULT TRUE,      -- Tracked in inventory

    -- Lifecycle
    status product_status DEFAULT 'DRAFT',
    lifecycle_stage lifecycle_stage DEFAULT 'REGULAR',

    -- Extensibility
    custom_attributes JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',

    -- E-commerce
    google_product_category VARCHAR(255),
    link VARCHAR(2048),                     -- Product page URL

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255),
    updated_by VARCHAR(255)
);

-- Indexes
CREATE INDEX idx_product_sku ON products(sku);
CREATE INDEX idx_product_type ON products(product_type);
CREATE INDEX idx_product_family ON products(product_family_id);
CREATE INDEX idx_product_category ON products(category_id);
CREATE INDEX idx_product_status ON products(status);
CREATE INDEX idx_product_brand ON products(brand);
```

### 2.5 Product Flags Matrix

How flags combine for different product types:

| Product Type | is_purchasable | is_manufacturable | is_sellable | is_stockable | Example |
|--------------|----------------|-------------------|-------------|--------------|---------|
| RAW_MATERIAL | TRUE | FALSE | FALSE | TRUE | PET Granules |
| RAW_MATERIAL | TRUE | FALSE | TRUE | TRUE | PET Granules (sold to others) |
| COMPONENT | FALSE | TRUE | FALSE | TRUE | Preform (internal use) |
| COMPONENT | FALSE | TRUE | TRUE | TRUE | Preform (also sold) |
| COMPONENT | TRUE | FALSE | FALSE | TRUE | Purchased cap |
| FINISHED_GOOD | FALSE | TRUE | TRUE | TRUE | Bottle |
| PACK | FALSE | TRUE | TRUE | TRUE | 6-pack |
| BUNDLE | FALSE | TRUE | TRUE | TRUE | Gift set |
| SERVICE | FALSE | FALSE | TRUE | FALSE | Installation |

---

## 3. Domain 2: Variant System

### 3.1 Table: variant_axes

Dimensions along which products vary within a family.

```sql
CREATE TABLE variant_axes (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_family_id UUID NOT NULL REFERENCES product_families(id) ON DELETE CASCADE,

    -- Core fields
    name VARCHAR(100) NOT NULL,             -- Internal: color, size, neck_type
    display_label VARCHAR(200) NOT NULL,    -- UI: Color, Size, Neck Type

    -- Behavior
    sort_order INT DEFAULT 0,
    is_required BOOLEAN DEFAULT TRUE,       -- Must select a value

    -- Schema.org mapping
    schema_property VARCHAR(100),           -- https://schema.org/color

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(product_family_id, name)
);

-- Indexes
CREATE INDEX idx_axis_family ON variant_axes(product_family_id);
```

### 3.2 Table: variant_values

Specific values for each axis.

```sql
CREATE TABLE variant_values (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    variant_axis_id UUID NOT NULL REFERENCES variant_axes(id) ON DELETE CASCADE,

    -- Core fields
    value VARCHAR(255) NOT NULL,            -- Internal: blue, 500ml
    display_label VARCHAR(255) NOT NULL,    -- UI: Blue, 500 ML
    sku_code VARCHAR(50) NOT NULL,          -- SKU segment: BLU, 500ML

    -- Visual (for swatches)
    color_hex VARCHAR(7),                   -- #0000FF
    image_url VARCHAR(2048),                -- Swatch image

    -- Pricing
    price_adjustment DECIMAL(18,4) DEFAULT 0,  -- +/- from base price

    -- Display
    sort_order INT DEFAULT 0,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(variant_axis_id, value),
    UNIQUE(variant_axis_id, sku_code)
);

-- Indexes
CREATE INDEX idx_value_axis ON variant_values(variant_axis_id);
CREATE INDEX idx_value_sku_code ON variant_values(sku_code);
```

### 3.3 Table: product_variant_values

Junction table: which variant values apply to which product.

```sql
CREATE TABLE product_variant_values (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- References
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    variant_value_id UUID NOT NULL REFERENCES variant_values(id) ON DELETE CASCADE,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(product_id, variant_value_id)
);

-- Indexes
CREATE INDEX idx_pvv_product ON product_variant_values(product_id);
CREATE INDEX idx_pvv_value ON product_variant_values(variant_value_id);
```

### 3.4 Variant Example

```
Product Family: "500ml PET Bottle" (PAV-BTL-500)

Axes:
  - color (Color): [Clear/CLR, Blue/BLU, Green/GRN]
  - neck_type (Neck Type): [28mm PCO/28PCO, 38mm PCO/38PCO]

Products generated (6 SKUs):
  PAV-BTL-500-CLR-28PCO  -> variant_values: Clear, 28mm PCO
  PAV-BTL-500-CLR-38PCO  -> variant_values: Clear, 38mm PCO
  PAV-BTL-500-BLU-28PCO  -> variant_values: Blue, 28mm PCO
  PAV-BTL-500-BLU-38PCO  -> variant_values: Blue, 38mm PCO
  PAV-BTL-500-GRN-28PCO  -> variant_values: Green, 28mm PCO
  PAV-BTL-500-GRN-38PCO  -> variant_values: Green, 38mm PCO
```

---

## 4. Domain 3: Unit of Measure

### 4.1 Enumerations

```sql
CREATE TYPE uom_category AS ENUM (
    'WEIGHT',    -- MT, KG, G, MG
    'COUNT',     -- PCS, DOZEN
    'VOLUME',    -- L, ML, KL
    'LENGTH',    -- M, CM, MM
    'PACKAGE'    -- PACK, CARTON, PALLET
);
```

### 4.2 Table: uom

Unit of measure definitions.

```sql
CREATE TABLE uom (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(20) NOT NULL UNIQUE,       -- MT, KG, PCS, PACK
    name VARCHAR(100) NOT NULL,             -- Metric Ton, Kilogram

    -- Classification
    uom_category uom_category NOT NULL,

    -- Behavior
    is_base_unit BOOLEAN DEFAULT FALSE,     -- Base unit for category
    decimal_places INT DEFAULT 2,           -- Precision (0 for PCS)

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Standard UoMs to seed
-- Weight: MT, KG, G
-- Count: PCS, DOZEN
-- Volume: KL, L, ML
-- Package: PACK, CARTON, PALLET
```

### 4.3 Table: uom_conversion

Global UoM conversions (not product-specific).

```sql
CREATE TABLE uom_conversion (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Conversion
    from_uom_id UUID NOT NULL REFERENCES uom(id),
    to_uom_id UUID NOT NULL REFERENCES uom(id),
    conversion_factor DECIMAL(18,6) NOT NULL,   -- from * factor = to

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Constraints
    UNIQUE(from_uom_id, to_uom_id)
);

-- Standard conversions to seed
-- MT -> KG: 1000
-- KG -> G: 1000
-- KL -> L: 1000
-- L -> ML: 1000
-- DOZEN -> PCS: 12
```

### 4.4 Table: product_uom_conversion

Product-specific UoM conversions (e.g., how many bottles in a pack).

```sql
CREATE TABLE product_uom_conversion (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- References
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,

    -- Conversion
    from_uom_id UUID NOT NULL REFERENCES uom(id),
    to_uom_id UUID NOT NULL REFERENCES uom(id),
    conversion_factor DECIMAL(18,6) NOT NULL,

    -- Context
    context VARCHAR(20) DEFAULT 'ALL',      -- PURCHASE, INVENTORY, SALES, ALL

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(product_id, from_uom_id, to_uom_id, context)
);

-- Indexes
CREATE INDEX idx_puc_product ON product_uom_conversion(product_id);
```

### 4.5 UoM Example

```
Product: BOTTLE-500ML-6PK (6-pack of bottles)

Product UoM config:
  base_uom: PACK
  purchase_uom: NULL (not purchased)
  inventory_uom: PACK
  sales_uom: PACK

Product-specific conversions:
  PCS -> PACK: 6 (6 bottles = 1 pack)
  PACK -> CARTON: 12 (12 packs = 1 carton)
  CARTON -> PALLET: 48 (48 cartons = 1 pallet)

So: 1 PALLET = 48 CARTONS = 576 PACKS = 3456 PCS
```

---

## 5. Domain 4: Bill of Materials

### 5.1 Enumerations

```sql
CREATE TYPE bom_status AS ENUM (
    'DRAFT',        -- Being created
    'ACTIVE',       -- In production use
    'OBSOLETE'      -- Replaced by newer version
);
```

### 5.2 Table: bom

BOM header - one per product that can be manufactured. **SKU-level** (not family-level).

```sql
CREATE TABLE bom (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- What we're making
    product_id UUID NOT NULL REFERENCES products(id),

    -- Versioning
    version VARCHAR(20) DEFAULT '1.0',
    name VARCHAR(255),

    -- Output
    output_qty DECIMAL(18,6) NOT NULL DEFAULT 1,
    output_uom_id UUID NOT NULL REFERENCES uom(id),

    -- Lifecycle
    status bom_status DEFAULT 'DRAFT',
    effective_from DATE,
    effective_to DATE,

    -- Notes
    notes TEXT,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255),

    -- Constraints: One ACTIVE BOM per product
    UNIQUE(product_id, version)
);

-- Indexes
CREATE INDEX idx_bom_product ON bom(product_id);
CREATE INDEX idx_bom_status ON bom(status);

-- Partial unique index: only one ACTIVE per product
CREATE UNIQUE INDEX idx_bom_active_per_product
ON bom(product_id)
WHERE status = 'ACTIVE';
```

### 5.3 Table: bom_lines

BOM components/ingredients.

```sql
CREATE TABLE bom_lines (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bom_id UUID NOT NULL REFERENCES bom(id) ON DELETE CASCADE,

    -- Sequence
    line_number INT NOT NULL,

    -- Component
    component_product_id UUID NOT NULL REFERENCES products(id),

    -- Quantity
    quantity DECIMAL(18,6) NOT NULL,
    uom_id UUID NOT NULL REFERENCES uom(id),

    -- Wastage
    scrap_percentage DECIMAL(5,2) DEFAULT 0,    -- 2.5 = 2.5%

    -- Behavior
    is_critical BOOLEAN DEFAULT TRUE,           -- Production stops if unavailable

    -- Notes
    notes TEXT,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(bom_id, line_number),
    UNIQUE(bom_id, component_product_id)
);

-- Indexes
CREATE INDEX idx_bomline_bom ON bom_lines(bom_id);
CREATE INDEX idx_bomline_component ON bom_lines(component_product_id);
```

### 5.4 BOM Example - Multi-Level

```
Level 3: RAW_MATERIAL
-------------------------
Product: PET-GRANULES
  - No BOM (purchased)
  - is_purchasable: TRUE
  - purchase_uom: MT, inventory_uom: KG

Product: BLUE-PIGMENT
  - No BOM (purchased)
  - is_purchasable: TRUE


Level 2: COMPONENT
-------------------------
Product: PREFORM-500ML-28MM (output: 1000 PCS)
  BOM Lines:
    1. PET-GRANULES     | 25 KG    | scrap: 2%

Product: CAP-28MM-BLU (output: 1000 PCS)
  BOM Lines:
    1. PP-GRANULES      | 3 KG     | scrap: 1%
    2. BLUE-PIGMENT     | 0.05 KG  | scrap: 5%


Level 1: FINISHED_GOOD
-------------------------
Product: BOTTLE-500ML-BLU-28PCO (output: 1 PCS)
  BOM Lines:
    1. PREFORM-500ML-28MM  | 1 PCS   | scrap: 1%
    2. CAP-28MM-BLU        | 1 PCS   | scrap: 0.5%
    3. LABEL-500ML         | 1 PCS   | scrap: 2%


Level 0: PACK
-------------------------
Product: BOTTLE-500ML-BLU-28PCO-6PK (output: 1 PACK)
  BOM Lines:
    1. BOTTLE-500ML-BLU-28PCO  | 6 PCS    | scrap: 0%
    2. SHRINK-WRAP-6PK         | 1 PCS    | scrap: 3%
```

---

## 6. Domain 5: Packaging Configuration

For **logistics packaging only** (how products ship). Sales units (6-pack) are products with BOM.

### 6.1 Table: packaging_configs

```sql
CREATE TABLE packaging_configs (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- References
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,

    -- Hierarchy
    packaging_level INT NOT NULL,               -- 1=inner, 2=outer, 3=pallet
    parent_config_id UUID REFERENCES packaging_configs(id),

    -- Description
    name VARCHAR(255) NOT NULL,                 -- "Inner Carton", "Master Carton"

    -- Contents
    quantity_per_pack INT NOT NULL,             -- How many fit
    content_uom_id UUID NOT NULL REFERENCES uom(id),
    package_uom_id UUID NOT NULL REFERENCES uom(id),

    -- Physical specs
    gross_weight_kg DECIMAL(10,3),
    net_weight_kg DECIMAL(10,3),
    length_cm DECIMAL(10,2),
    width_cm DECIMAL(10,2),
    height_cm DECIMAL(10,2),
    volume_cbm DECIMAL(10,6),                   -- Cubic meters

    -- Identification
    barcode VARCHAR(50),
    barcode_type VARCHAR(20),                   -- EAN13, ITF14, SSCC

    -- Behavior
    is_default BOOLEAN DEFAULT FALSE,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(product_id, packaging_level)
);

-- Indexes
CREATE INDEX idx_pkgconfig_product ON packaging_configs(product_id);
```

### 6.2 Packaging Example

```
Product: BOTTLE-500ML-BLU-6PK (6-pack)

Packaging Configs:
  Level 1 - Inner Carton:
    - 4 packs per carton (24 bottles)
    - content_uom: PACK, package_uom: CARTON
    - Dimensions: 40x30x20 cm
    - Weight: 5.5 kg gross
    - Barcode: ITF-14

  Level 2 - Master Carton:
    - 3 inner cartons (12 packs, 72 bottles)
    - content_uom: CARTON, package_uom: CARTON
    - Dimensions: 60x40x45 cm
    - Weight: 18 kg gross

  Level 3 - Pallet:
    - 48 master cartons (576 packs, 3456 bottles)
    - content_uom: CARTON, package_uom: PALLET
    - Dimensions: 120x100x180 cm
    - Weight: 900 kg gross
```

---

## 7. Domain 6: Pricing

### 7.1 Table: price_lists

Named price lists for different channels/customer groups.

```sql
CREATE TABLE price_lists (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) NOT NULL UNIQUE,           -- MRP, WHOLESALE, DISTRIBUTOR
    name VARCHAR(255) NOT NULL,

    -- Details
    description TEXT,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',

    -- Behavior
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,

    -- Validity
    valid_from DATE,
    valid_to DATE,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 7.2 Table: product_prices

Product prices with volume tiers.

```sql
CREATE TABLE product_prices (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- References
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    price_list_id UUID NOT NULL REFERENCES price_lists(id) ON DELETE CASCADE,

    -- Quantity tier
    min_quantity DECIMAL(18,6) DEFAULT 1,       -- Tier start
    max_quantity DECIMAL(18,6),                 -- Tier end (NULL = unlimited)

    -- Price
    price DECIMAL(18,4) NOT NULL,               -- Unit price
    discount_percentage DECIMAL(5,2),           -- Alternative to fixed price

    -- Validity
    valid_from DATE,
    valid_to DATE,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(product_id, price_list_id, min_quantity)
);

-- Indexes
CREATE INDEX idx_prodprice_product ON product_prices(product_id);
CREATE INDEX idx_prodprice_pricelist ON product_prices(price_list_id);
```

### 7.3 Table: customer_prices

Customer-specific price overrides.

```sql
CREATE TABLE customer_prices (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- References
    customer_id UUID NOT NULL,                  -- FK to customers table (TBD)
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,

    -- Price
    price DECIMAL(18,4),                        -- Fixed price
    discount_percentage DECIMAL(5,2),           -- Or discount off list

    -- Quantity
    min_quantity DECIMAL(18,6) DEFAULT 1,

    -- Validity
    valid_from DATE,
    valid_to DATE,

    -- Notes
    notes TEXT,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(customer_id, product_id, min_quantity)
);

-- Indexes
CREATE INDEX idx_custprice_customer ON customer_prices(customer_id);
CREATE INDEX idx_custprice_product ON customer_prices(product_id);
```

### 7.4 Pricing Example

```
Product: BOTTLE-500ML-6PK

Price Lists:
  MRP (default): Rs 180/pack
  WHOLESALE:
    - Qty 1-99: Rs 150/pack
    - Qty 100-499: Rs 140/pack
    - Qty 500+: Rs 130/pack
  DISTRIBUTOR:
    - Qty 1-999: Rs 125/pack
    - Qty 1000+: Rs 120/pack

Customer Override:
  Customer: "ABC Beverages"
  - Rs 118/pack (special rate)
  - Min qty: 500
```

---

## 8. Domain 7: Inventory

### 8.1 Enumerations

```sql
CREATE TYPE location_type AS ENUM (
    'WAREHOUSE',    -- Physical warehouse
    'ZONE',         -- Zone within warehouse
    'AISLE',        -- Aisle
    'RACK',         -- Storage rack
    'BIN'           -- Specific bin location
);

CREATE TYPE quality_status AS ENUM (
    'PENDING',      -- Awaiting inspection
    'APPROVED',     -- Passed QC
    'REJECTED',     -- Failed QC
    'QUARANTINE'    -- Held for review
);

CREATE TYPE transaction_type AS ENUM (
    'RECEIPT',          -- Goods received
    'ISSUE',            -- Goods issued
    'TRANSFER',         -- Location transfer
    'ADJUSTMENT',       -- Stock adjustment
    'PRODUCTION_IN',    -- Production output
    'PRODUCTION_OUT',   -- Production consumption
    'SCRAP',            -- Scrapped/damaged
    'RETURN'            -- Customer return
);
```

### 8.2 Table: locations

Warehouse/storage location hierarchy.

```sql
CREATE TABLE locations (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) NOT NULL UNIQUE,           -- WH-01, WH-01-A-01-01
    name VARCHAR(255) NOT NULL,

    -- Hierarchy
    location_type location_type NOT NULL,
    parent_location_id UUID REFERENCES locations(id),

    -- Address (for warehouses)
    address_json JSONB,                         -- Full address

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_location_parent ON locations(parent_location_id);
CREATE INDEX idx_location_type ON locations(location_type);
```

### 8.3 Table: batches

Batch/lot tracking for traceability.

```sql
CREATE TABLE batches (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_number VARCHAR(100) NOT NULL,

    -- References
    product_id UUID NOT NULL REFERENCES products(id),

    -- Dates
    manufactured_date DATE,
    expiry_date DATE,
    received_date DATE,

    -- Supplier info
    supplier_id UUID REFERENCES suppliers(id),
    supplier_batch VARCHAR(100),

    -- Quality
    quality_status quality_status DEFAULT 'PENDING',

    -- Notes
    notes TEXT,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(product_id, batch_number)
);

-- Indexes
CREATE INDEX idx_batch_product ON batches(product_id);
CREATE INDEX idx_batch_number ON batches(batch_number);
CREATE INDEX idx_batch_expiry ON batches(expiry_date);
```

### 8.4 Table: inventory

Current stock levels.

```sql
CREATE TABLE inventory (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- What
    product_id UUID NOT NULL REFERENCES products(id),
    batch_id UUID REFERENCES batches(id),       -- NULL if not batch-tracked

    -- Where
    location_id UUID NOT NULL REFERENCES locations(id),

    -- Quantities
    quantity_on_hand DECIMAL(18,6) NOT NULL DEFAULT 0,
    quantity_reserved DECIMAL(18,6) NOT NULL DEFAULT 0,
    quantity_available DECIMAL(18,6) GENERATED ALWAYS AS (quantity_on_hand - quantity_reserved) STORED,

    -- UoM
    uom_id UUID NOT NULL REFERENCES uom(id),

    -- Costing
    unit_cost DECIMAL(18,4),

    -- Tracking
    last_count_date TIMESTAMPTZ,

    -- Audit
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(product_id, location_id, batch_id)
);

-- Indexes
CREATE INDEX idx_inv_product ON inventory(product_id);
CREATE INDEX idx_inv_location ON inventory(location_id);
CREATE INDEX idx_inv_batch ON inventory(batch_id);
```

### 8.5 Table: inventory_transactions

Stock movement audit trail.

```sql
CREATE TABLE inventory_transactions (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Type
    transaction_type transaction_type NOT NULL,

    -- What
    product_id UUID NOT NULL REFERENCES products(id),
    batch_id UUID REFERENCES batches(id),

    -- Where
    from_location_id UUID REFERENCES locations(id),
    to_location_id UUID REFERENCES locations(id),

    -- Quantity
    quantity DECIMAL(18,6) NOT NULL,            -- Positive = in, Negative = out
    uom_id UUID NOT NULL REFERENCES uom(id),

    -- Costing
    unit_cost DECIMAL(18,4),
    total_cost DECIMAL(18,4),

    -- Reference
    reference_type VARCHAR(50),                 -- PURCHASE_ORDER, SALES_ORDER, etc.
    reference_id UUID,
    reference_number VARCHAR(100),              -- PO-2024-001, SO-2024-100

    -- Execution
    performed_by VARCHAR(255),
    performed_at TIMESTAMPTZ DEFAULT NOW(),

    -- Notes
    notes TEXT
);

-- Indexes
CREATE INDEX idx_invtxn_product ON inventory_transactions(product_id);
CREATE INDEX idx_invtxn_type ON inventory_transactions(transaction_type);
CREATE INDEX idx_invtxn_date ON inventory_transactions(performed_at);
CREATE INDEX idx_invtxn_reference ON inventory_transactions(reference_type, reference_id);
```

---

## 9. Domain 8: Suppliers

### 9.1 Table: suppliers

Supplier master.

```sql
CREATE TABLE suppliers (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,

    -- Contact
    contact_name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),

    -- Address
    address_json JSONB,                         -- {line1, line2, city, state, country, postal_code}

    -- Tax info
    gstin VARCHAR(20),
    pan VARCHAR(20),

    -- Terms
    payment_terms_days INT DEFAULT 30,
    credit_limit DECIMAL(18,2),
    currency VARCHAR(3) DEFAULT 'INR',

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_supplier_name ON suppliers(name);
CREATE INDEX idx_supplier_gstin ON suppliers(gstin);
```

### 9.2 Table: supplier_products

What each supplier sells, with pricing.

```sql
CREATE TABLE supplier_products (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- References
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,

    -- Supplier's identifiers
    supplier_sku VARCHAR(100),
    supplier_product_name VARCHAR(255),

    -- Pricing
    unit_price DECIMAL(18,4),
    currency VARCHAR(3) DEFAULT 'INR',
    price_uom_id UUID REFERENCES uom(id),

    -- Ordering
    min_order_qty DECIMAL(18,6),
    min_order_uom_id UUID REFERENCES uom(id),
    lead_time_days INT,

    -- Preference
    is_preferred BOOLEAN DEFAULT FALSE,
    priority INT DEFAULT 0,                     -- Lower = higher priority

    -- Validity
    valid_from DATE,
    valid_to DATE,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(supplier_id, product_id)
);

-- Indexes
CREATE INDEX idx_supprod_supplier ON supplier_products(supplier_id);
CREATE INDEX idx_supprod_product ON supplier_products(product_id);
```

---

## 10. Domain 9: Digital Assets

### 10.1 Enumerations

```sql
CREATE TYPE asset_type AS ENUM (
    'PRODUCT_IMAGE',        -- Main product photo
    'COMPONENT_IMAGE',      -- Component for composition
    'LIFESTYLE',            -- Lifestyle/context shots
    'TECHNICAL_DRAWING',    -- CAD, engineering drawings
    'PACKAGING_ARTWORK',    -- Label designs, box art
    'VIDEO',                -- Product videos
    'DOCUMENT',             -- Spec sheets, manuals
    'COMPOSITE'             -- AI-generated composite
);

CREATE TYPE asset_status AS ENUM (
    'PROCESSING',           -- Being uploaded/processed
    'ACTIVE',               -- Ready for use
    'ARCHIVED'              -- No longer active
);

CREATE TYPE view_angle AS ENUM (
    'FRONT',
    'BACK',
    'LEFT',
    'RIGHT',
    'TOP',
    'BOTTOM',
    'ISOMETRIC',
    '45_DEG',
    'DETAIL',
    'LIFESTYLE'
);

CREATE TYPE background_type AS ENUM (
    'WHITE',
    'TRANSPARENT',
    'LIFESTYLE',
    'CUSTOM'
);
```

### 10.2 Table: assets

Central asset storage.

```sql
CREATE TABLE assets (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Classification
    asset_type asset_type NOT NULL,

    -- Storage
    filename VARCHAR(255) NOT NULL,
    storage_path VARCHAR(500) NOT NULL,
    storage_provider VARCHAR(50) DEFAULT 'S3', -- S3, GCS, LOCAL

    -- File info
    mime_type VARCHAR(100),
    file_size_bytes BIGINT,

    -- Image dimensions
    width_px INT,
    height_px INT,

    -- Video duration
    duration_seconds INT,

    -- Visual properties
    is_transparent BOOLEAN DEFAULT FALSE,
    view_angle view_angle,
    background_type background_type,

    -- SEO/Accessibility
    alt_text VARCHAR(500),
    tags TEXT[] DEFAULT '{}',

    -- AI generation
    is_ai_generated BOOLEAN DEFAULT FALSE,
    generation_prompt TEXT,
    source_asset_ids UUID[],                    -- Parent assets for composites

    -- Status
    status asset_status DEFAULT 'PROCESSING',

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_asset_type ON assets(asset_type);
CREATE INDEX idx_asset_status ON assets(status);
```

### 10.3 Table: product_assets

Link assets to products.

```sql
CREATE TABLE product_assets (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- References (one of these should be set)
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    product_family_id UUID REFERENCES product_families(id) ON DELETE CASCADE,

    -- Asset
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,

    -- Usage
    usage_context VARCHAR(50) DEFAULT 'CATALOG',  -- CATALOG, MARKETING, INTERNAL, WEBSITE

    -- Display
    is_primary BOOLEAN DEFAULT FALSE,
    sort_order INT DEFAULT 0,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(product_id, asset_id, usage_context),
    UNIQUE(product_family_id, asset_id, usage_context),
    CHECK (product_id IS NOT NULL OR product_family_id IS NOT NULL)
);

-- Indexes
CREATE INDEX idx_prodasset_product ON product_assets(product_id);
CREATE INDEX idx_prodasset_family ON product_assets(product_family_id);
CREATE INDEX idx_prodasset_asset ON product_assets(asset_id);
```

### 10.4 Table: asset_composition_rules

Rules for AI-generated composite images.

```sql
CREATE TABLE asset_composition_rules (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Description
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Target
    target_product_type product_type,           -- Which product types this applies to
    target_category_id UUID REFERENCES product_categories(id),

    -- Composition config
    composition_config JSONB NOT NULL,
    /*
    Example:
    {
      "layers": [
        {"slot": "base", "source": "FINISHED_GOOD", "view_angle": "FRONT", "required": true},
        {"slot": "cap", "source": "COMPONENT", "category": "caps", "view_angle": "FRONT", "position": "top", "required": true},
        {"slot": "label", "source": "PACKAGING_ARTWORK", "position": "center", "required": false}
      ],
      "variant_matching": {
        "cap.color": "base.color"
      }
    }
    */

    -- Output settings
    output_settings JSONB DEFAULT '{}',
    /*
    {
      "width": 1024,
      "height": 1024,
      "format": "PNG",
      "background": "transparent"
    }
    */

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_acr_type ON asset_composition_rules(target_product_type);
CREATE INDEX idx_acr_category ON asset_composition_rules(target_category_id);
```

---

## 11. Relationships Diagram

```
                                    +-------------------+
                                    | product_categories|
                                    +-------------------+
                                            |
                                            | (parent/child)
                                            v
+------------------+               +-------------------+
| price_lists      |               | product_families  |
+------------------+               +-------------------+
        |                                   |
        |                                   |
        v                                   v
+------------------+     +----------+-------------------+----------+
| product_prices   |<--->| products |<----------------->| bom      |
+------------------+     +----------+                   +----------+
        ^                     ^  |                           |
        |                     |  |                           v
+------------------+          |  |                      +----------+
| customer_prices  |          |  |                      | bom_lines|
+------------------+          |  |                      +----------+
                              |  |
        +---------------------+  +----------------------+
        |                                               |
        v                                               v
+------------------+                           +------------------+
| variant_axes     |                           | inventory        |
+------------------+                           +------------------+
        |                                               ^
        v                                               |
+------------------+                           +------------------+
| variant_values   |                           | inv_transactions |
+------------------+                           +------------------+
        |
        v                                      +------------------+
+----------------------+                       | suppliers        |
| product_variant_values|                      +------------------+
+----------------------+                               |
                                                       v
+------------------+                           +------------------+
| assets           |                           | supplier_products|
+------------------+                           +------------------+
        |
        v
+------------------+
| product_assets   |
+------------------+

+------------------------+
| packaging_configs      |
+------------------------+

+------------------------+
| asset_composition_rules|
+------------------------+
```

---

## 12. Example Scenarios

### 12.1 Scenario: Manufacturer (Pavisha)

```
Products:
  RAW_MATERIAL:
    - PET-GRANULES (purchase: MT, inventory: KG)
    - PP-GRANULES
    - BLUE-PIGMENT

  COMPONENT:
    - PREFORM-500ML-28MM (manufacturable, sellable)
    - CAP-28MM-BLU (manufacturable)
    - CAP-28MM-CLR (manufacturable)
    - LABEL-500ML

  FINISHED_GOOD (Product Family: 500ml PET Bottle):
    - BOTTLE-500ML-BLU-28PCO
    - BOTTLE-500ML-CLR-28PCO

  PACK:
    - BOTTLE-500ML-BLU-28PCO-6PK
    - BOTTLE-500ML-CLR-28PCO-6PK
```

### 12.2 Scenario: Trader (Wholesaler)

```
Products:
  FINISHED_GOOD:
    - IMPORTED-BOTTLE-500ML (purchasable, sellable, NOT manufacturable)

  PACK:
    - IMPORTED-BOTTLE-500ML-6PK (purchasable OR manufacturable)
```

### 12.3 Scenario: Mixed Business

```
Products:
  Some manufactured (has BOM)
  Some purchased and resold (no BOM, is_purchasable)
  Some assembled from purchased components
```

---

## 13. Open Questions

### Status Legend
- **PENDING** - Not yet discussed
- **DISCUSSING** - Currently in discussion
- **DECIDED** - Decision made, documented in Decision Log

---

### Q1: Quality Grades (DECIDED)

**Context:** Products can have quality variations (A-grade, B-grade, rejected/seconds). Where should quality grade live in the data model?

**Options:**
| Option | Description | Example |
|--------|-------------|---------|
| A) On Product | Different SKU per grade | `BOTTLE-500ML-A`, `BOTTLE-500ML-B` as separate products |
| B) On Batch | Same SKU, grade assigned after production/QC | Batch 2024-001 is A-grade, Batch 2024-002 is B-grade |
| C) Both | Product has target grade, batch has actual grade | Product targets A-grade, some batches downgraded |

**Decision:** Option B - Quality grade on batch (optional/nullable field).
- Businesses that recycle defects (plastics, metals) track scrap as a separate product (RECYCLED-PET)
- Businesses that sell B-grade (textiles, ceramics) use the grade field on batches
- Grade assigned after production/QC (realistic flow)
- No SKU explosion

**Date:** 2025-11-28

---

### Q2: Products Without Variants (DECIDED)

**Context:** Can a product exist WITHOUT belonging to a product family? Examples: raw materials, one-off custom products, imported single-SKU items.

**Options:**
| Option | Description |
|--------|-------------|
| A) Yes | `product_family_id` is nullable, standalone products allowed |
| B) No | Every product must belong to a family (even if family has 1 product) |

**Current Design:** Option A (nullable)

**Decision:** Option A - Standalone products allowed. `product_family_id` is nullable.
- Raw materials (PET-GRANULES) don't need families
- Single-SKU traded products can exist without family overhead
- Recommendation: Sellable finished goods SHOULD have a family for catalog consistency

**Date:** 2025-11-28

---

### Q3: Substitute Components in BOM (DECIDED)

**Context:** During production, can alternative components be used if primary is unavailable?

**Example:** BOM specifies "CAP-28MM-BLU" but stock is empty. Can we use "CAP-28MM-BLU-SUPPLIER2" (same spec, different supplier)?

**Options:**
| Option | Description |
|--------|-------------|
| A) No substitutes | BOM is fixed, production waits for exact component |
| B) Substitute groups | Define interchangeable components in BOM line |
| C) Production decision | Handled at production time, not modeled in BOM |

**Decision:** Hybrid approach with configurable products support:

1. **Standard products (pre-defined variants):**
   - Each variant has fixed BOM
   - `substitution_policy` on BOM line: `FIXED` (default) or `FLEXIBLE`
   - `FLEXIBLE` = same spec, different source allowed (production decides)

2. **Configurable products (customer picks options at order):**
   - `is_configurable = TRUE` on product_family
   - BOM templates at family level (not SKU level)
   - BOM template lines reference component CATEGORY + axis to match
   - Actual components resolved at order/production time based on customer selection

3. **Substitution at order level:**
   - Customer can change variant if preferred option unavailable
   - "Red cap out of stock, use Blue?" -> Order changes to different variant

**Schema additions:**
- `product_families.is_configurable` (BOOLEAN)
- `bom_templates` table for configurable products
- `bom_template_lines` with category + axis matching
- `bom_lines.substitution_policy` (FIXED/FLEXIBLE)

**Date:** 2025-11-28

---

### Q4: Co-Products / By-Products (DECIDED)

**Context:** Does production ever create multiple outputs?

**Example:** Making preforms generates scrap plastic that can be reprocessed or sold.

**Options:**
| Option | Description |
|--------|-------------|
| A) Ignore | Scrap is waste, not tracked as inventory |
| B) Track as product | SCRAP-PET is a product with its own SKU |
| C) Future scope | Design schema for it but implement later |

**Decision:** Option B - Track scrap/recyclables as a regular product.

- RECYCLED-PET, SCRAP-PLASTIC etc. are products (product_type: RAW_MATERIAL)
- `is_manufacturable: TRUE` (output of recycling/production process)
- When production generates scrap, inventory transaction creates scrap inventory
- Scrap can be used as input in other BOMs (mixed with virgin material)
- No complex co-product schema needed - just model as regular product
- `scrap_percentage` on BOM line handles expected waste

**Date:** 2025-11-28

---

### Q5: Tax Handling in Prices (DECIDED)

**Context:** How should prices be stored - with or without tax?

**Options:**
| Option | Description | Use Case |
|--------|-------------|----------|
| A) Tax exclusive | Prices without tax, calculated at sale | B2B transactions |
| B) Tax inclusive | Prices include tax (MRP) | B2C/retail |
| C) Both | Flag per price indicating inclusive/exclusive | Mixed business |

**Decision:** Option C - Both, with tax flag on price_list level.

Omni-channel MSMEs need both:
- B2B/Wholesale price lists: `is_tax_inclusive = FALSE`
- MRP/Retail/D2C price lists: `is_tax_inclusive = TRUE`

**Schema additions to `price_lists`:**
```sql
is_tax_inclusive BOOLEAN DEFAULT FALSE
default_tax_category VARCHAR(50)  -- 'GST_18', 'GST_12', 'GST_5', 'EXEMPT'
```

All prices in a list follow same tax treatment. Simpler than per-price flag.

**Date:** 2025-11-28

---

### Q6: Negative Inventory (DECIDED)

**Context:** Can inventory quantity go below zero?

**Options:**
| Option | Description | Use Case |
|--------|-------------|----------|
| A) Never allow | Block transactions causing negative | Strict control |
| B) Allow with warning | System warns but permits | Ship now, reconcile later |
| C) Configurable | Per location/product setting | Flexible |

**Decision:** Option C - Configurable per location.

- Raw materials: Allow negative (production consumption can exceed estimates)
- Finished goods: Block negative (can't ship what you don't have)
- Transit locations: Allow negative (timing differences)

**Schema addition to `locations`:**
```sql
allow_negative_inventory BOOLEAN DEFAULT FALSE
```

Default is strict (FALSE). Enable per location where flexibility needed.

**Date:** 2025-11-28

---

### Q7: Customer Master Table (DECIDED)

**Context:** Current design has `customer_prices` referencing `customer_id` but no customers table defined.

**Options:**
| Option | Description |
|--------|-------------|
| A) Include now | Add customers table to this design |
| B) Reference only | FK exists, table defined in separate CRM domain |
| C) Defer | Remove customer_prices, add when customers domain designed |

**Decision:** Option B - Reference only.

- Keep `customer_prices` table for B2B contract/negotiated pricing (volume deals, annual contracts, strategic accounts)
- `customer_id` references future `customers` table in CRM domain
- FK constraint added once CRM domain is designed
- Domain separation: Product catalog owns pricing, CRM owns customer master

**Date:** 2025-11-28

---

### Q8: Returnable Packaging (DECIDED)

**Context:** Some products use returnable containers (glass bottles in crates, drums, pallets).

**Options:**
| Option | Description |
|--------|-------------|
| A) Not needed | No returnable packaging in target MSMEs |
| B) Track as product | Crates/drums are products with own inventory |
| C) Future scope | Design for it later |

**Decision:** Option B - Track as product.

- Returnable containers (crates, drums, pallets) are products with `product_type = 'COMPONENT'`
- No new tables needed - reuse existing product/inventory infrastructure
- BOM can include returnables: "1 crate + 24 bottles = 1 beer case"
- Deposit pricing via `product_prices`
- Inventory tracks returnable stock levels

**Date:** 2025-11-28

---

### Q9: Serial Number Tracking (PENDING)

**Context:** Do any products need individual unit tracking beyond batch?

**Example:** Electronics with unique serial per unit, machinery with individual tracking.

**Options:**
| Option | Description |
|--------|-------------|
| A) Not needed | Batch tracking is sufficient for MSMEs |
| B) Include now | Add serial number support |
| C) Future scope | Design for it later |

**Decision:**
**Date:**

---

### Q10: Multi-Currency (PENDING)

**Context:** Do customers pay in different currencies?

**Options:**
| Option | Description |
|--------|-------------|
| A) Single (INR) | All prices in INR only |
| B) Multi-currency | Same product can have prices in different currencies |
| C) Conversion | Store base currency, convert at transaction time |

**Decision:**
**Date:**

---

### Q11: Consignment Stock (PENDING)

**Context:** Stock placed at customer location - customer holds it, pays only when they sell/use.

**Options:**
| Option | Description |
|--------|-------------|
| A) Not needed | No consignment model for target MSMEs |
| B) Include now | Track consignment locations and stock |
| C) Future scope | Design for it later |

**Decision:**
**Date:**

---

### Q12: Scope Boundaries (PENDING)

**Context:** Confirm what is OUT of scope for product data model (separate domains).

**Items to confirm:**
- [ ] Purchase Orders
- [ ] Sales Orders
- [ ] Production/Work Orders
- [ ] Invoicing/Billing
- [ ] Payments
- [ ] Shipping/Logistics
- [ ] CRM (leads, opportunities)

**Decision:**
**Date:**

---

## 14. Decision Log

| Date | Decision | Rationale | Decided By |
|------|----------|-----------|------------|
| 2025-11-25 | Use "Product" terminology | SAP S/4HANA standard, customer-facing | Abhishek |
| 2025-11-25 | SKU-level BOM | Variants need different components (colored cap on clear bottle) | Abhishek |
| 2025-11-25 | Sales packs as products | Own SKU, own pricing, own BOM (6x bottle + shrink wrap) | Abhishek |
| 2025-11-25 | Logistics packaging as config | Cartons/pallets are shipping units, not sellable SKUs | Abhishek |
| 2025-11-28 | Quality grade on batch (optional) | Supports both recycling pattern (scrap as product) and B-grade sales (grade on batch) | Abhishek |
| 2025-11-28 | Standalone products allowed | Raw materials and single-SKU items don't need family overhead | Abhishek |
| 2025-11-28 | Hybrid BOM: fixed + configurable | Standard products use fixed BOM per variant; configurable products use BOM templates with category/axis matching | Abhishek |
| 2025-11-28 | Scrap as product | Track recyclables (RECYCLED-PET) as regular products for material traceability and costing | Abhishek |
| 2025-11-28 | Tax flag on price_list | B2B lists tax-exclusive, MRP lists tax-inclusive; simpler than per-price flag | Abhishek |
| 2025-11-28 | Configurable negative inventory | Per-location setting; default FALSE, enable where needed (raw materials, transit) | Abhishek |
| 2025-11-28 | Customer master in CRM domain | Product domain references customer_id; CRM owns customers table | Abhishek |
| 2025-11-28 | Returnables as products | Crates/drums tracked as products; reuse existing inventory infrastructure | Abhishek |
| 2025-11-25 | Single tenant | Current architecture, no multi-company needed | Abhishek |

---

## Appendix A: Migration from v1

### Tables to Keep (Enhanced)
- product_families (minor enhancements)
- variant_axes (as-is)
- variant_values (as-is)
- products (major enhancement - was for variants only, now unified)
- product_variant_values (as-is)
- product_images -> migrate to assets + product_assets
- marketing_content (keep separate, not in this doc)
- customer_segments (keep separate, not in this doc)

### New Tables
- product_categories
- uom, uom_conversion, product_uom_conversion
- bom, bom_lines
- packaging_configs
- price_lists, product_prices, customer_prices
- locations, batches, inventory, inventory_transactions
- suppliers, supplier_products
- assets, product_assets, asset_composition_rules

---

## Appendix B: Seed Data

### UoM Seed Data

```sql
-- Weight
INSERT INTO uom (code, name, uom_category, is_base_unit, decimal_places) VALUES
('MT', 'Metric Ton', 'WEIGHT', false, 3),
('KG', 'Kilogram', 'WEIGHT', true, 3),
('G', 'Gram', 'WEIGHT', false, 0);

-- Count
INSERT INTO uom (code, name, uom_category, is_base_unit, decimal_places) VALUES
('PCS', 'Pieces', 'COUNT', true, 0),
('DOZEN', 'Dozen', 'COUNT', false, 0);

-- Volume
INSERT INTO uom (code, name, uom_category, is_base_unit, decimal_places) VALUES
('KL', 'Kiloliter', 'VOLUME', false, 3),
('L', 'Liter', 'VOLUME', true, 3),
('ML', 'Milliliter', 'VOLUME', false, 0);

-- Package
INSERT INTO uom (code, name, uom_category, is_base_unit, decimal_places) VALUES
('PACK', 'Pack', 'PACKAGE', true, 0),
('CARTON', 'Carton', 'PACKAGE', false, 0),
('PALLET', 'Pallet', 'PACKAGE', false, 0);

-- Conversions
INSERT INTO uom_conversion (from_uom_id, to_uom_id, conversion_factor) VALUES
((SELECT id FROM uom WHERE code = 'MT'), (SELECT id FROM uom WHERE code = 'KG'), 1000),
((SELECT id FROM uom WHERE code = 'KG'), (SELECT id FROM uom WHERE code = 'G'), 1000),
((SELECT id FROM uom WHERE code = 'KL'), (SELECT id FROM uom WHERE code = 'L'), 1000),
((SELECT id FROM uom WHERE code = 'L'), (SELECT id FROM uom WHERE code = 'ML'), 1000),
((SELECT id FROM uom WHERE code = 'DOZEN'), (SELECT id FROM uom WHERE code = 'PCS'), 12);
```

---

*End of Document*
