# Pavisha Product Database Architecture

**Created:** 2025-11-25
**Status:** Draft - Design Phase
**Domain:** Manufacturing ERP - Multi-level BOM with UoM complexity

---

## Executive Summary

Database architecture for Pavisha's plastic manufacturing business covering:
- Raw materials (granules) -> Semi-finished (preforms, caps) -> Finished (bottles, jars) -> Packaged SKUs
- Multi-level Bill of Materials with UoM conversions at each stage
- Dual-use items (internal consumption + external sales)
- Variant management (color, material type, size)
- Digital asset composition for SKU visualization

---

## 1. Core Product Hierarchy

### 1.1 Product Categories

```
PRODUCT_CATEGORY
-----------------
RAW_MATERIAL      # Pet granules, PP granules
SEMI_FINISHED     # Preforms, Caps (intermediate)
FINISHED_GOOD     # Bottles, Jars (complete items)
PACKAGED_SKU      # Sellable packaged units
PACKAGING_MATERIAL # Boxes, shrink wrap, labels
```

### 1.2 Material Types

```
MATERIAL_TYPE
-------------
PET    # Polyethylene terephthalate
PP     # Polypropylene
HDPE   # High-density polyethylene (future)
```

---

## 2. Database Schema

### 2.1 Unit of Measure (UoM) System

```sql
-- Base UoM definitions
CREATE TABLE uom (
    id UUID PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,      -- 'MT', 'KG', 'G', 'PCS', 'PACK', 'CARTON'
    name VARCHAR(100) NOT NULL,
    uom_type VARCHAR(20) NOT NULL,          -- 'WEIGHT', 'COUNT', 'VOLUME', 'PACKAGE'
    is_base_unit BOOLEAN DEFAULT FALSE,     -- Base unit for its type
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- UoM conversion factors (within same type)
CREATE TABLE uom_conversion (
    id UUID PRIMARY KEY,
    from_uom_id UUID REFERENCES uom(id),
    to_uom_id UUID REFERENCES uom(id),
    conversion_factor DECIMAL(18,6) NOT NULL,  -- from * factor = to
    is_bidirectional BOOLEAN DEFAULT TRUE,
    UNIQUE(from_uom_id, to_uom_id)
);

-- Example conversions:
-- MT -> KG: factor = 1000
-- KG -> G: factor = 1000
-- CARTON -> PACK: factor = 12 (product-specific, see product_uom_conversion)
```

### 2.2 Product Master

```sql
-- Core product definition
CREATE TABLE product (
    id UUID PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Classification
    category VARCHAR(30) NOT NULL,          -- RAW_MATERIAL, SEMI_FINISHED, FINISHED_GOOD, PACKAGED_SKU
    product_type VARCHAR(50) NOT NULL,      -- GRANULE, PREFORM, CAP, BOTTLE, JAR, SKU
    material_type VARCHAR(20),              -- PET, PP, HDPE (nullable for non-plastic items)

    -- Usage flags
    is_purchasable BOOLEAN DEFAULT FALSE,   -- Can be purchased from suppliers
    is_manufacturable BOOLEAN DEFAULT FALSE, -- Can be manufactured in-house
    is_sellable BOOLEAN DEFAULT FALSE,      -- Can be sold to customers
    is_internal_use BOOLEAN DEFAULT FALSE,  -- Used internally in production

    -- Default UoM (can be overridden per context)
    purchase_uom_id UUID REFERENCES uom(id),
    inventory_uom_id UUID REFERENCES uom(id),
    sales_uom_id UUID REFERENCES uom(id),
    production_uom_id UUID REFERENCES uom(id),

    -- Status
    status VARCHAR(20) DEFAULT 'ACTIVE',    -- ACTIVE, DISCONTINUED, DRAFT

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_category CHECK (category IN ('RAW_MATERIAL', 'SEMI_FINISHED', 'FINISHED_GOOD', 'PACKAGED_SKU', 'PACKAGING_MATERIAL'))
);

-- Product-specific UoM conversions (e.g., this specific bottle: 6 PCS = 1 PACK)
CREATE TABLE product_uom_conversion (
    id UUID PRIMARY KEY,
    product_id UUID REFERENCES product(id),
    from_uom_id UUID REFERENCES uom(id),
    to_uom_id UUID REFERENCES uom(id),
    conversion_factor DECIMAL(18,6) NOT NULL,
    context VARCHAR(30),                    -- 'PURCHASE', 'INVENTORY', 'SALES', 'ALL'
    UNIQUE(product_id, from_uom_id, to_uom_id, context)
);
```

### 2.3 Variant Management

```sql
-- Variant attributes (color, size, capacity, neck size, etc.)
CREATE TABLE variant_attribute (
    id UUID PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,       -- 'COLOR', 'SIZE', 'CAPACITY_ML', 'NECK_SIZE'
    name VARCHAR(100) NOT NULL,
    data_type VARCHAR(20) NOT NULL,         -- 'STRING', 'NUMBER', 'ENUM'
    applicable_to JSONB,                    -- ['CAP', 'BOTTLE', 'JAR'] - which product types
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Allowed values for ENUM attributes
CREATE TABLE variant_attribute_value (
    id UUID PRIMARY KEY,
    attribute_id UUID REFERENCES variant_attribute(id),
    value VARCHAR(100) NOT NULL,
    display_name VARCHAR(100),
    sort_order INT DEFAULT 0,
    UNIQUE(attribute_id, value)
);

-- Product variants (specific color/size combinations)
CREATE TABLE product_variant (
    id UUID PRIMARY KEY,
    product_id UUID REFERENCES product(id),
    variant_sku VARCHAR(50) UNIQUE NOT NULL,
    variant_name VARCHAR(255),

    -- Variant can override parent UoMs if needed
    inventory_uom_id UUID REFERENCES uom(id),

    -- Status
    status VARCHAR(20) DEFAULT 'ACTIVE',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Variant attribute values (many-to-many with values)
CREATE TABLE product_variant_attribute (
    id UUID PRIMARY KEY,
    variant_id UUID REFERENCES product_variant(id),
    attribute_id UUID REFERENCES variant_attribute(id),
    value_id UUID REFERENCES variant_attribute_value(id),
    custom_value VARCHAR(255),              -- For non-enum attributes
    UNIQUE(variant_id, attribute_id)
);
```

### 2.4 Bill of Materials (Multi-Level)

```sql
-- BOM header (recipe for making a product)
CREATE TABLE bom (
    id UUID PRIMARY KEY,
    product_id UUID REFERENCES product(id), -- What we're making
    variant_id UUID REFERENCES product_variant(id), -- Optional: variant-specific BOM
    version VARCHAR(20) DEFAULT '1.0',
    name VARCHAR(255),

    -- Output
    output_qty DECIMAL(18,6) NOT NULL,
    output_uom_id UUID REFERENCES uom(id),

    -- Status
    status VARCHAR(20) DEFAULT 'ACTIVE',    -- DRAFT, ACTIVE, OBSOLETE
    effective_from DATE,
    effective_to DATE,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(product_id, variant_id, version)
);

-- BOM lines (components needed)
CREATE TABLE bom_line (
    id UUID PRIMARY KEY,
    bom_id UUID REFERENCES bom(id),
    line_number INT NOT NULL,

    -- Component
    component_product_id UUID REFERENCES product(id),
    component_variant_id UUID REFERENCES product_variant(id), -- Optional

    -- Quantity
    quantity DECIMAL(18,6) NOT NULL,
    uom_id UUID REFERENCES uom(id),

    -- Wastage/scrap allowance
    scrap_percentage DECIMAL(5,2) DEFAULT 0,

    -- Optional: substitute components
    is_optional BOOLEAN DEFAULT FALSE,
    substitute_group VARCHAR(50),           -- Group ID for interchangeable components

    UNIQUE(bom_id, line_number)
);

-- Example BOM: 500ml PET Bottle
-- Output: 1 PCS of 500ml PET Bottle
-- Components:
--   Line 1: 1 PCS of 500ml PET Preform
--   Line 2: 1 PCS of 28mm PET Cap (Blue)

-- Example BOM: 500ml PET Preform
-- Output: 1000 PCS of 500ml PET Preform
-- Components:
--   Line 1: 25 KG of PET Granules (with 2% scrap)
```

### 2.5 Packaging Hierarchy

```sql
-- Packaging configurations (how products are packed for sale)
CREATE TABLE packaging_config (
    id UUID PRIMARY KEY,
    product_id UUID REFERENCES product(id),
    variant_id UUID REFERENCES product_variant(id),
    name VARCHAR(255) NOT NULL,             -- '6-Pack Shrink', 'Master Carton 72pcs'

    -- Hierarchy level
    level INT NOT NULL,                     -- 1=inner pack, 2=outer carton, 3=pallet
    parent_config_id UUID REFERENCES packaging_config(id), -- For nested packaging

    -- Contents
    quantity_per_pack INT NOT NULL,         -- How many items/inner packs fit
    content_uom_id UUID REFERENCES uom(id), -- UoM of contents

    -- Package itself
    package_uom_id UUID REFERENCES uom(id), -- UoM of this package (PACK, CARTON, PALLET)

    -- Physical specs (for logistics)
    gross_weight_kg DECIMAL(10,3),
    net_weight_kg DECIMAL(10,3),
    length_cm DECIMAL(10,2),
    width_cm DECIMAL(10,2),
    height_cm DECIMAL(10,2),

    -- Barcode
    barcode VARCHAR(50),
    barcode_type VARCHAR(20),               -- EAN13, UPC, ITF14

    is_default BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'ACTIVE',

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Example for 500ml PET Bottle:
-- Level 1: 6-Pack Shrink (6 bottles per pack)
-- Level 2: Master Carton (12 packs = 72 bottles per carton)
-- Level 3: Pallet (48 cartons = 3456 bottles per pallet)
```

### 2.6 Digital Asset Management

```sql
-- Asset types
CREATE TYPE asset_type AS ENUM (
    'PRODUCT_IMAGE',      -- Main product photo
    'VARIANT_IMAGE',      -- Color/variant specific
    'TECHNICAL_DRAWING',  -- CAD/engineering drawings
    'PACKAGING_ARTWORK',  -- Label/box designs
    'COMPOSITE_RENDER',   -- AI-generated composite
    'LIFESTYLE_IMAGE',    -- Marketing/lifestyle shots
    'VIDEO',
    'DOCUMENT'
);

-- Asset storage
CREATE TABLE asset (
    id UUID PRIMARY KEY,
    asset_type asset_type NOT NULL,

    -- File info
    filename VARCHAR(255) NOT NULL,
    storage_path VARCHAR(500) NOT NULL,     -- S3/storage path
    mime_type VARCHAR(100),
    file_size_bytes BIGINT,

    -- Image-specific
    width_px INT,
    height_px INT,
    is_transparent BOOLEAN DEFAULT FALSE,   -- For compositing

    -- Metadata
    alt_text VARCHAR(500),
    tags JSONB,                             -- ['front', 'hero', 'white-background']

    -- AI-generation metadata
    is_ai_generated BOOLEAN DEFAULT FALSE,
    generation_prompt TEXT,
    source_asset_ids UUID[],                -- Parent assets used for composition

    -- Status
    status VARCHAR(20) DEFAULT 'ACTIVE',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Link assets to products/variants
CREATE TABLE product_asset (
    id UUID PRIMARY KEY,
    product_id UUID REFERENCES product(id),
    variant_id UUID REFERENCES product_variant(id), -- Optional: variant-specific
    asset_id UUID REFERENCES asset(id),

    -- Usage context
    usage_context VARCHAR(50),              -- 'CATALOG', 'WEBSITE', 'MARKETING', 'INTERNAL'
    is_primary BOOLEAN DEFAULT FALSE,
    sort_order INT DEFAULT 0,

    -- View angle (for compositing)
    view_angle VARCHAR(30),                 -- 'FRONT', 'SIDE', 'TOP', 'ISOMETRIC', '45DEG'

    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(product_id, variant_id, asset_id, usage_context)
);

-- Asset composition rules (for AI generation)
CREATE TABLE asset_composition_rule (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Target
    target_product_type VARCHAR(50),        -- 'PACKAGED_SKU' - what we're generating for

    -- Component slots (what assets to pull)
    composition_slots JSONB NOT NULL,
    /* Example:
    {
        "base": {"product_type": "BOTTLE", "view_angle": "FRONT", "required": true},
        "cap": {"product_type": "CAP", "view_angle": "FRONT", "required": true},
        "label": {"asset_type": "PACKAGING_ARTWORK", "required": false}
    }
    */

    -- Generation settings
    output_dimensions JSONB,                -- {"width": 1024, "height": 1024}
    background_settings JSONB,              -- {"type": "transparent"} or {"type": "color", "hex": "#FFFFFF"}

    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.7 Inventory Tracking (Multi-Stage)

```sql
-- Warehouse/location hierarchy
CREATE TABLE location (
    id UUID PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    location_type VARCHAR(30) NOT NULL,     -- 'WAREHOUSE', 'ZONE', 'RACK', 'BIN'
    parent_location_id UUID REFERENCES location(id),

    -- What can be stored here
    allowed_categories VARCHAR(30)[],        -- ['RAW_MATERIAL', 'SEMI_FINISHED']

    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Current inventory (real-time stock)
CREATE TABLE inventory (
    id UUID PRIMARY KEY,
    product_id UUID REFERENCES product(id),
    variant_id UUID REFERENCES product_variant(id),
    location_id UUID REFERENCES location(id),

    -- Quantities (in inventory UoM)
    quantity_on_hand DECIMAL(18,6) NOT NULL DEFAULT 0,
    quantity_reserved DECIMAL(18,6) NOT NULL DEFAULT 0,  -- For orders
    quantity_available DECIMAL(18,6) GENERATED ALWAYS AS (quantity_on_hand - quantity_reserved) STORED,

    -- UoM (defaults to product.inventory_uom but can differ by location)
    uom_id UUID REFERENCES uom(id),

    -- Batch/lot tracking (important for raw materials)
    batch_number VARCHAR(100),
    lot_number VARCHAR(100),
    expiry_date DATE,

    -- Cost tracking
    unit_cost DECIMAL(18,4),
    currency VARCHAR(3) DEFAULT 'INR',

    last_count_date TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(product_id, variant_id, location_id, batch_number)
);

-- Inventory transactions (audit trail)
CREATE TABLE inventory_transaction (
    id UUID PRIMARY KEY,
    transaction_type VARCHAR(30) NOT NULL,  -- 'RECEIPT', 'ISSUE', 'TRANSFER', 'ADJUSTMENT', 'PRODUCTION_IN', 'PRODUCTION_OUT'

    -- What moved
    product_id UUID REFERENCES product(id),
    variant_id UUID REFERENCES product_variant(id),

    -- Quantity (positive = in, negative = out)
    quantity DECIMAL(18,6) NOT NULL,
    uom_id UUID REFERENCES uom(id),

    -- Locations
    from_location_id UUID REFERENCES location(id),
    to_location_id UUID REFERENCES location(id),

    -- Reference
    reference_type VARCHAR(30),             -- 'PURCHASE_ORDER', 'SALES_ORDER', 'PRODUCTION_ORDER', 'MANUAL'
    reference_id UUID,

    -- Batch info
    batch_number VARCHAR(100),
    lot_number VARCHAR(100),

    -- Cost
    unit_cost DECIMAL(18,4),
    total_cost DECIMAL(18,4),
    currency VARCHAR(3) DEFAULT 'INR',

    -- Audit
    performed_by UUID,
    performed_at TIMESTAMPTZ DEFAULT NOW(),
    notes TEXT
);
```

### 2.8 Supplier & Purchase Management

```sql
-- Supplier master
CREATE TABLE supplier (
    id UUID PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,

    -- Contact
    contact_person VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),

    -- Address
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    postal_code VARCHAR(20),

    -- Tax info
    gstin VARCHAR(20),
    pan VARCHAR(20),

    -- Payment terms
    payment_terms_days INT DEFAULT 30,
    credit_limit DECIMAL(18,2),
    currency VARCHAR(3) DEFAULT 'INR',

    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Products supplied by each supplier
CREATE TABLE supplier_product (
    id UUID PRIMARY KEY,
    supplier_id UUID REFERENCES supplier(id),
    product_id UUID REFERENCES product(id),
    variant_id UUID REFERENCES product_variant(id),

    -- Supplier's identifiers
    supplier_sku VARCHAR(100),
    supplier_product_name VARCHAR(255),

    -- Pricing
    unit_price DECIMAL(18,4),
    currency VARCHAR(3) DEFAULT 'INR',
    price_uom_id UUID REFERENCES uom(id),   -- Price per this UoM
    min_order_qty DECIMAL(18,6),
    min_order_uom_id UUID REFERENCES uom(id),

    -- Lead time
    lead_time_days INT,

    -- Preference
    is_preferred BOOLEAN DEFAULT FALSE,
    priority INT DEFAULT 0,                 -- Lower = higher priority

    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(supplier_id, product_id, variant_id)
);
```

---

## 3. Key Relationships Diagram

```
                            +------------------+
                            |       UoM        |
                            +------------------+
                                    |
                    +---------------+---------------+
                    |               |               |
            +-------v------+ +------v-------+ +----v-----+
            |   Product    | | UoM Conversion | | Location |
            +-------+------+ +--------------+ +----+-----+
                    |                              |
        +-----------+-----------+                  |
        |           |           |                  |
+-------v---+ +-----v-----+ +---v--------+   +-----v------+
|  Variant  | |    BOM    | | Packaging  |   | Inventory  |
+-------+---+ +-----+-----+ +------------+   +------------+
        |           |
        |     +-----v-----+
        |     | BOM Line  |
        |     +-----------+
        |
+-------v--------+
| Variant Asset  |
+----------------+
        |
+-------v--------+
|     Asset      |
+----------------+
```

---

## 4. Example Data Flow

### 4.1 Raw Material to Finished Product

```
1. PURCHASE: PET Granules (1 MT = 1000 KG)
   - Product: PET-GRAN-001
   - Purchase UoM: MT
   - Inventory UoM: KG
   - Conversion: 1 MT = 1000 KG

2. PRODUCTION: Preforms (from Granules)
   - Product: PREFORM-500ML-PET
   - BOM: 25 KG granules -> 1000 PCS preforms (with 2% scrap)
   - Inventory UoM: PCS (but can track weight too)

3. PRODUCTION: Bottles (from Preforms + Caps)
   - Product: BOTTLE-500ML-PET
   - BOM: 1 PCS preform + 1 PCS cap -> 1 PCS bottle
   - Inventory UoM: PCS

4. PACKAGING: Final SKU
   - Product: SKU-BOTTLE-500ML-6PK
   - Packaging Config: 6 PCS -> 1 PACK
   - Master Carton: 12 PACKS -> 1 CARTON
   - Sales UoM: CARTON or PACK
```

### 4.2 Asset Composition for SKU

```
When generating visual for SKU-BOTTLE-500ML-BLUE-6PK:

1. Fetch base bottle asset:
   - Product: BOTTLE-500ML-PET
   - View: FRONT
   - Asset: bottle_500ml_front.png

2. Fetch cap variant asset:
   - Product: CAP-28MM-PET
   - Variant: BLUE
   - View: FRONT
   - Asset: cap_28mm_blue_front.png

3. Apply composition rule:
   - Overlay cap on bottle
   - Duplicate for 6-pack arrangement
   - Add shrink wrap effect
   - Generate: SKU-BOTTLE-500ML-BLUE-6PK_composite.png
```

---

## 5. Key Design Decisions

### 5.1 Why Separate Product vs Variant?

| Aspect | Product | Variant |
|--------|---------|---------|
| Scope | Base definition | Specific configuration |
| Example | "500ml PET Bottle" | "500ml PET Bottle - Blue Cap" |
| BOM | Can have default BOM | Can override with variant-specific BOM |
| Assets | Generic product images | Color/variant-specific images |
| Inventory | Aggregated view | Actual stock tracking |

### 5.2 Why Product-Specific UoM Conversions?

Different products have different packaging:
- Bottle A: 6 PCS = 1 PACK
- Bottle B: 12 PCS = 1 PACK
- Jar A: 4 PCS = 1 PACK

Global UoM conversions (MT->KG) are universal, but packaging is product-specific.

### 5.3 Dual-Use Products

Products like preforms can be:
- **Sold externally**: `is_sellable = true`, has sales_uom, pricing
- **Used internally**: `is_internal_use = true`, appears in BOMs

Both flags can be true simultaneously.

### 5.4 Multi-Level BOM Traversal

To calculate raw material needs for a final SKU:
1. Start with SKU -> packaging config -> base product
2. Explode BOM recursively until reaching raw materials
3. Apply scrap percentages at each level
4. Convert UoMs at each transition

---

## 6. Indexes for Performance

```sql
-- Product lookups
CREATE INDEX idx_product_category ON product(category);
CREATE INDEX idx_product_type ON product(product_type);
CREATE INDEX idx_product_status ON product(status);

-- Variant lookups
CREATE INDEX idx_variant_product ON product_variant(product_id);
CREATE INDEX idx_variant_attribute ON product_variant_attribute(variant_id);

-- BOM traversal
CREATE INDEX idx_bom_product ON bom(product_id);
CREATE INDEX idx_bom_line_component ON bom_line(component_product_id);

-- Inventory queries
CREATE INDEX idx_inventory_product ON inventory(product_id);
CREATE INDEX idx_inventory_location ON inventory(location_id);
CREATE INDEX idx_inventory_variant ON inventory(variant_id);

-- Asset retrieval
CREATE INDEX idx_product_asset_product ON product_asset(product_id);
CREATE INDEX idx_product_asset_variant ON product_asset(variant_id);
CREATE INDEX idx_asset_type ON asset(asset_type);
```

---

## 7. Extension Points

### 7.1 Future Considerations

1. **Quality Control**: Add quality parameters, test results per batch
2. **Costing**: Full cost rollup through BOM levels
3. **Production Planning**: MRP calculations, work orders
4. **Multi-Company**: Tenant isolation if needed
5. **Audit Trail**: Full change tracking on master data

### 7.2 Agent Integration Points

| Agent Need | Data Source |
|------------|-------------|
| Product catalog generation | product + variant + asset |
| BOM explosion for planning | bom + bom_line (recursive) |
| Inventory availability | inventory + uom_conversion |
| Asset composition | asset + product_asset + composition_rule |
| Supplier recommendations | supplier_product + pricing |

---

## 8. Open Questions

1. **Batch/Lot Traceability**: How strict? Full genealogy or simple tracking?
2. **Multi-Warehouse**: How many locations? Transfer workflows?
3. **Pricing Complexity**: Customer-specific pricing? Volume discounts?
4. **Quality Grades**: Different grades of same product?
5. **Waste Management**: Track scrap/waste as separate inventory?
