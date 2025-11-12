# Product Hierarchy & Relationships Architecture

**Date:** 2025-11-12
**Status:** 🔄 In Design - Active Q&A Session
**Last Updated:** 2025-11-12

---

## Executive Summary

Comprehensive data model for product composition, unit of measure (UOM) conversions, and packaging hierarchies to support autonomous agent decision-making across manufacturing, procurement, inventory, and sales workflows.

**Key Architectural Decisions:**
- **Unified relationship model:** Single `product_relationships` table handles manufacturing BOM, packaging hierarchy, and commercial relationships
- **Multi-UOM support:** Products tracked in multiple units with conversion factors (MT → KG → Pieces)
- **Three-system architecture:** Manufacturing BOM (how products are made) + UOM conversions (cross-unit tracking) + Packaging hierarchy (how products are sold)
- **Agent-optimized:** Supports dynamic planning, procurement optimization, inventory reservation, configuration validation

**Scope:**
- ✅ Manufacturing BOM (multi-level, phantom assemblies, effectivity dates)
- ✅ UOM conversions (fixed, batch-specific, catch weight)
- ✅ Packaging hierarchy (inner packs, master cases, pallets)
- ✅ Commercial relationships (bundles, accessories, substitutes, upgrades)
- ✅ Configurable products (modular BOM, 150% BOM pattern)

---

## Table of Contents

1. [Business Context](#business-context)
2. [Research Findings](#research-findings)
3. [Complete Relationship Taxonomy](#complete-relationship-taxonomy)
4. [Unit of Measure Architecture](#unit-of-measure-architecture)
5. [Unified Data Model](#unified-data-model)
6. [Real-World Scenario: Pet Jar Manufacturing](#real-world-scenario-pet-jar-manufacturing)
7. [Agent Decision Scenarios](#agent-decision-scenarios)
8. [Query Patterns](#query-patterns)
9. [Implementation Roadmap](#implementation-roadmap)
10. [Open Questions & Design Decisions](#open-questions--design-decisions)

---

## Business Context

### Problem Statement

Current product model handles **attribute-based variants** (size, color, capacity via VariantAxis/VariantValue) but lacks:
1. **Component relationships:** Finished goods made from components (jar = lid + preform)
2. **Multi-UOM tracking:** Raw materials in tons, components in kg, finished goods in pieces
3. **Packaging hierarchy:** Products sold in multiple pack sizes (6-pack, dozen, carton)
4. **Manufacturing intelligence:** BOM explosion, cost rollup, where-used analysis

### Business Requirements

**Manufacturing Scenarios:**
- Multi-level BOMs (jar ← preform ← resin)
- Phantom assemblies (intermediate subassemblies not stocked)
- Component substitution (approved alternates during shortages)
- Effectivity-based components (time/serial/configuration-specific)

**Inventory Scenarios:**
- Cross-UOM tracking (purchase in MT, stock in KG, sell in pieces)
- Batch-specific conversions (preform weight variance per manufacturing batch)
- Packaging hierarchy explosion (carton contains dozens contains 6-packs)

**Sales Scenarios:**
- Configurable products (customer selects options from modular BOM)
- Bundle pricing (marketing kits with discounts)
- Accessory recommendations (cross-sell related products)

**Procurement Scenarios:**
- Make vs buy decisions (assemble vs purchase finished goods)
- Component demand planning (MRP from finished good forecasts)
- Vendor alternative selection (cost/lead time optimization)

---

## Research Findings

### Industry Standards

**Bill of Materials (BOM) Patterns:**
- **Single-level BOM:** Flat component list (simple, not suited for troubleshooting)
- **Multi-level BOM:** Hierarchical parent-child relationships (detailed assembly structure)
- **Modular BOM:** Subassemblies usable across multiple parent products
- **Configurable BOM (150% approach):** Master BOM includes all possible components; configuration rules select subset at order time

**Manufacturing Strategies:**

| Strategy | Components Stocked? | Assembly Timing | BOM Type | Use Case |
|----------|---------------------|-----------------|----------|----------|
| Make-to-Stock (MTS) | Yes | Before order | Standard BOM | High-volume, predictable demand |
| Make-to-Order (MTO) | Yes | After order | Standard BOM | Custom products, low volume |
| Assemble-to-Order (ATO) | Yes | After order | Modular BOM | Stock common parts, configure on demand |
| Configure-to-Order (CTO) | Yes | After order | 150% BOM | Customer-selected options |
| Engineer-to-Order (ETO) | Varies | After design | Custom BOM | Unique designs per order |

**UOM Conversion Patterns:**
- **Base UOM + Alternate UOMs:** Each product has canonical unit; other units defined with conversion factors
- **UOM Categories:** Conversions only valid within dimensional family (weight, volume, count)
- **Conversion Types:** Standard (global), intra-class (product-specific), inter-class (between categories), batch-specific (variable per batch)
- **Catch Weight:** Variable weight per piece (meat, chemicals, steel) requiring dual UOM tracking

**Packaging Hierarchy Standards (GS1):**
- Each packaging level has unique GTIN/SKU
- Hierarchy: Base Unit (Each) → Inner Pack → Master Case → Pallet
- Parent-child relationships with quantity specifications

### Key Insights from Research

1. **Separation of concerns:** Manufacturing BOM (physical transformation) vs Packaging BOM (aggregation without transformation) vs Commercial relationships (selling strategies)
2. **Effectivity critical:** Components valid for specific time periods, serial ranges, or configurations
3. **Phantom assemblies common:** Intermediate subassemblies built but not stocked (components "explode through" to parent)
4. **UOM at relationship level:** BOM must specify quantity AND unit (not just "1 unit of X")
5. **Batch-specific conversions essential:** Manufacturing variance requires per-batch UOM conversion factors

---

## Complete Relationship Taxonomy

### 1. Structural Relationships (Manufacturing)

**A. Component/Assembly (Classic BOM)**
- Parent assembly contains child components
- Multi-level hierarchies supported
- Quantity-per specifications
- **Agent impact:** Procurement, inventory, costing, quality tracking

**B. Phantom Assemblies (Transient BOM)**
- Intermediate subassemblies physically built but NOT stocked
- Components "explode through" to parent assembly pick lists
- Zero lead time, lot-for-lot sizing
- **Agent impact:** Inventory skips phantom level; procurement plans components directly

**C. Modular/Configurable BOM (150% BOM)**
- Master BOM contains ALL possible components across variants
- Configuration rules select subset at order time
- Example: "Car BOM" includes V6 AND V8 engines; customer selects one
- **Agent impact:** Sales validates configurations; manufacturing filters to active components

**D. Effectivity-Based Relationships**
- Time-based: "Use Component A until 2025-06-30, then Component B"
- Serial-based: "Units 1-1000 use old lid, 1001+ use new lid"
- Configuration-based: "If color=red, use brass fittings"
- **Agent impact:** Planning selects components based on production date/serial/config

**E. Co-Products**
- Multiple products produced together (crude oil → gasoline + diesel)
- Shared production costs
- **Agent impact:** Costing allocates joint costs; planning schedules both outputs

**F. By-Products**
- Secondary output from primary production (sawdust from lumber)
- Often lower value
- **Agent impact:** Inventory tracks secondary outputs; pricing offsets primary cost

### 2. Alternative/Substitution Relationships

**A. Preferred Substitutes**
- "Use Component A; if unavailable, use Component B"
- Maintains equivalent functionality
- **Agent impact:** Procurement auto-substitutes during shortages; inventory checks alternatives

**B. Approved Vendor Alternatives**
- Same component from multiple suppliers
- **Agent impact:** Procurement optimizes by lead time, cost, quality scores

### 3. Commercial Relationships (Sales/Marketing)

**A. Accessory/Complementary**
- Products that enhance each other (printer + ink cartridges)
- Not assembled together, sold separately
- **Agent impact:** Sales cross-sells; catalog displays "Frequently Bought Together"

**B. Bundle/Kit**
- Multiple products sold as single SKU (gift baskets, starter kits)
- Pre-packaged, NOT manufactured together
- **Agent impact:** Inventory reserves all bundle components; pricing applies bundle discount

**C. Replacement Parts/Spare Parts**
- Components sold individually for repairs
- **Agent impact:** Service recommends parts; warranty tracks covered items

**D. Upgrade Path**
- Product evolution (iPhone 14 → iPhone 15)
- **Agent impact:** Sales suggests upgrades; marketing targets existing customers

### 4. Packaging Relationships

**A. Inner Pack**
- Contains smaller units (6-pack contains 6 bottles)
- **Agent impact:** Order fulfillment selects appropriate pack size

**B. Master Case**
- Contains inner packs (dozen pack contains 7 six-packs)
- **Agent impact:** Warehouse picking optimizes case quantities

**C. Pallet Load**
- Contains master cases for distribution
- **Agent impact:** Logistics plans shipping units

### 5. Variant Relationships (Existing Architecture)

Current VariantAxis/VariantValue architecture handles attribute-based variants (size, color, capacity) within product families. This remains unchanged and complements the new relationship model.

---

## Unit of Measure Architecture

### Core Concept: Base UOM + Alternate UOMs

Every product has:
- **Base UOM:** Canonical unit for inventory tracking (e.g., "piece" for bottles, "kg" for preforms, "MT" for resin)
- **Alternate UOMs:** Other units with conversion factors
- **Role-specific UOMs:** Different UOMs for purchase, stock, sales, production

### UOM Categories (Dimensional Families)

Conversions only valid within same category:

```sql
CREATE TABLE uom_categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(50) UNIQUE NOT NULL,  -- 'Weight', 'Volume', 'Count', 'Length', 'Area'
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO uom_categories (name, description) VALUES
  ('Weight', 'Mass and weight measurements'),
  ('Volume', 'Volume and capacity measurements'),
  ('Count', 'Discrete countable units'),
  ('Length', 'Linear distance measurements'),
  ('Area', 'Surface area measurements');
```

### UOM Definitions

```sql
CREATE TABLE units_of_measure (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  category_id UUID NOT NULL REFERENCES uom_categories(id),

  -- Identification
  code VARCHAR(20) UNIQUE NOT NULL,  -- 'MT', 'KG', 'PC', 'L', 'M'
  name VARCHAR(100) NOT NULL,        -- 'Metric Ton', 'Kilogram', 'Piece', 'Liter', 'Meter'
  symbol VARCHAR(10),                -- 't', 'kg', 'pc', 'L', 'm'

  -- Base unit flag
  is_base_unit BOOLEAN DEFAULT false, -- Only ONE base per category

  -- Conversion to category base unit
  conversion_factor DECIMAL(20,10),  -- How many base units = 1 of this unit
  conversion_offset DECIMAL(20,10) DEFAULT 0,  -- For temperature conversions (Celsius/Fahrenheit)

  -- Rounding rules
  rounding_precision INTEGER DEFAULT 2,

  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  CONSTRAINT one_base_per_category UNIQUE (category_id, is_base_unit)
    WHERE is_base_unit = true
);

-- Standard UOMs
INSERT INTO units_of_measure (category_id, code, name, symbol, is_base_unit, conversion_factor) VALUES
  -- Weight (base: kg)
  ((SELECT id FROM uom_categories WHERE name='Weight'), 'KG', 'Kilogram', 'kg', true, 1.0),
  ((SELECT id FROM uom_categories WHERE name='Weight'), 'MT', 'Metric Ton', 't', false, 1000.0),
  ((SELECT id FROM uom_categories WHERE name='Weight'), 'G', 'Gram', 'g', false, 0.001),
  ((SELECT id FROM uom_categories WHERE name='Weight'), 'LB', 'Pound', 'lb', false, 0.453592),

  -- Count (base: piece)
  ((SELECT id FROM uom_categories WHERE name='Count'), 'PC', 'Piece', 'pc', true, 1.0),
  ((SELECT id FROM uom_categories WHERE name='Count'), 'DZ', 'Dozen', 'dz', false, 12.0),
  ((SELECT id FROM uom_categories WHERE name='Count'), 'GR', 'Gross', 'gr', false, 144.0),

  -- Volume (base: liter)
  ((SELECT id FROM uom_categories WHERE name='Volume'), 'L', 'Liter', 'L', true, 1.0),
  ((SELECT id FROM uom_categories WHERE name='Volume'), 'ML', 'Milliliter', 'mL', false, 0.001),
  ((SELECT id FROM uom_categories WHERE name='Volume'), 'GAL', 'Gallon (US)', 'gal', false, 3.78541);
```

### Product-Specific UOM Mappings

Products can use multiple UOMs with item-specific conversions:

```sql
CREATE TABLE product_uoms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  uom_id UUID NOT NULL REFERENCES units_of_measure(id),

  -- Role in product lifecycle
  is_base_uom BOOLEAN DEFAULT false,           -- Primary inventory tracking unit
  is_purchase_uom BOOLEAN DEFAULT false,       -- Vendor sells in this unit
  is_stock_uom BOOLEAN DEFAULT false,          -- Warehouse tracks in this unit
  is_sales_uom BOOLEAN DEFAULT false,          -- Customer buys in this unit
  is_production_uom BOOLEAN DEFAULT false,     -- Manufacturing outputs in this unit

  -- Product-specific conversion (overrides standard if needed)
  conversion_factor DECIMAL(20,10),            -- To base UOM
  conversion_type VARCHAR(20) DEFAULT 'fixed', -- 'fixed', 'batch_specific', 'catch_weight'

  -- Packaging details (if this UOM represents a pack)
  contains_quantity DECIMAL(10,3),             -- 6-pack contains 6 pieces
  contained_uom_id UUID REFERENCES units_of_measure(id), -- The UOM being packed

  -- Physical attributes for this UOM
  barcode VARCHAR(100),                        -- EAN/UPC for this pack size
  weight_kg DECIMAL(10,3),                     -- Physical weight
  dimensions_cm VARCHAR(50),                   -- LxWxH for shipping

  -- Batch-specific tracking
  batch_id UUID,                               -- If conversion_type = 'batch_specific'

  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  CONSTRAINT unique_product_uom UNIQUE (product_id, uom_id),
  CONSTRAINT unique_product_uom_batch UNIQUE (product_id, uom_id, batch_id)
    WHERE batch_id IS NOT NULL,
  CONSTRAINT one_base_per_product UNIQUE (product_id, is_base_uom)
    WHERE is_base_uom = true
);

CREATE INDEX idx_product_uoms_product ON product_uoms(product_id);
CREATE INDEX idx_product_uoms_roles ON product_uoms(product_id)
  WHERE is_purchase_uom OR is_sales_uom OR is_production_uom;
CREATE INDEX idx_product_uoms_batch ON product_uoms(batch_id)
  WHERE batch_id IS NOT NULL;
```

**Conversion Logic:**

```python
def convert_quantity(
    product_id: str,
    quantity: Decimal,
    from_uom_code: str,
    to_uom_code: str,
    batch_id: Optional[str] = None
) -> Decimal:
    """Convert quantity from one UOM to another for a specific product."""

    # Get product UOM mappings
    from_uom = db.query("""
        SELECT pu.conversion_factor, pu.conversion_type, uom.category_id
        FROM product_uoms pu
        JOIN units_of_measure uom ON uom.id = pu.uom_id
        WHERE pu.product_id = %s AND uom.code = %s
          AND (pu.batch_id IS NULL OR pu.batch_id = %s)
        ORDER BY pu.batch_id NULLS LAST
        LIMIT 1
    """, (product_id, from_uom_code, batch_id))

    to_uom = db.query("""
        SELECT pu.conversion_factor, uom.category_id
        FROM product_uoms pu
        JOIN units_of_measure uom ON uom.id = pu.uom_id
        WHERE pu.product_id = %s AND uom.code = %s
        LIMIT 1
    """, (product_id, to_uom_code))

    # Validate same category
    if from_uom.category_id != to_uom.category_id:
        raise ValueError(f"Cannot convert between {from_uom_code} and {to_uom_code}: different categories")

    # Convert: quantity * (from_factor / to_factor)
    return quantity * (from_uom.conversion_factor / to_uom.conversion_factor)
```

---

## Unified Data Model

### Product Type Classification

```sql
-- Add product type to existing products table
ALTER TABLE products ADD COLUMN product_type VARCHAR(20) DEFAULT 'finished_good';

ALTER TABLE products ADD CONSTRAINT check_product_type
  CHECK (product_type IN (
    'finished_good',    -- Sellable end products
    'component',        -- Parts used in assembly
    'phantom',          -- Transient assemblies (not stocked)
    'raw_material',     -- Unprocessed materials
    'bundle',           -- Marketing bundles (pre-packaged)
    'service'           -- Non-physical products
  ));

CREATE INDEX idx_products_type ON products(product_type);

-- Migration: Classify existing products
UPDATE products SET product_type = 'finished_good' WHERE product_type IS NULL;
```

### Unified Relationship Table

```sql
CREATE TABLE product_relationships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Core relationship
  source_product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  target_product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
  relationship_type VARCHAR(50) NOT NULL,

  -- Quantity/specifications
  quantity DECIMAL(10,4),
  source_uom_id UUID REFERENCES units_of_measure(id),  -- UOM for source product
  target_uom_id UUID REFERENCES units_of_measure(id),  -- UOM for target product
  unit_of_measure VARCHAR(20),  -- Deprecated: for backward compatibility
  sort_order INTEGER,
  is_optional BOOLEAN DEFAULT false,
  is_phantom BOOLEAN DEFAULT false,  -- For phantom assemblies

  -- Substitution handling
  substitution_priority INTEGER,  -- 1=preferred, 2=secondary, etc.
  substitution_reason VARCHAR(100),  -- 'equivalent', 'cost_effective', 'availability'

  -- Effectivity (validity conditions)
  effective_from DATE,
  effective_to DATE,
  serial_number_from VARCHAR(50),
  serial_number_to VARCHAR(50),
  configuration_context JSONB,  -- {'engine': 'V8', 'color': 'red'}

  -- Commercial attributes
  price_adjustment DECIMAL(10,2),  -- For bundle discounts
  lead_time_days INTEGER,

  -- Metadata
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  created_by UUID,

  -- Constraints
  CONSTRAINT unique_relationship
    UNIQUE (source_product_id, target_product_id, relationship_type, effective_from),
  CONSTRAINT no_self_reference
    CHECK (source_product_id != target_product_id),
  CONSTRAINT valid_effectivity_dates
    CHECK (effective_to IS NULL OR effective_to >= effective_from),
  CONSTRAINT valid_quantity
    CHECK (quantity IS NULL OR quantity > 0)
);

-- Indexes for traversal
CREATE INDEX idx_relationships_source ON product_relationships(source_product_id, relationship_type);
CREATE INDEX idx_relationships_target ON product_relationships(target_product_id, relationship_type);
CREATE INDEX idx_relationships_effectivity ON product_relationships(effective_from, effective_to)
  WHERE effective_from IS NOT NULL;
CREATE INDEX idx_relationships_config ON product_relationships USING GIN (configuration_context)
  WHERE configuration_context IS NOT NULL;

-- Audit trigger
CREATE TRIGGER trg_relationships_updated
  BEFORE UPDATE ON product_relationships
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### Relationship Type Enumeration

```sql
ALTER TABLE product_relationships ADD CONSTRAINT check_relationship_type
  CHECK (relationship_type IN (
    -- Manufacturing BOM
    'component',              -- Standard BOM component
    'phantom_component',      -- Transient assembly component
    'alternate',              -- Substitutable component
    'co_product',             -- Joint production output
    'by_product',             -- Secondary production output

    -- Packaging Hierarchy
    'inner_pack',             -- Contains smaller packs (6-pack contains bottles)
    'master_case',            -- Contains inner packs (dozen contains 6-packs)
    'pallet_load',            -- Contains master cases

    -- Commercial
    'accessory',              -- Complementary product
    'bundle_item',            -- Item in marketing bundle
    'replacement_part',       -- Spare part
    'upgrade',                -- Newer version
    'cross_sell',             -- Related product recommendation
    'up_sell',                -- Higher-tier alternative

    -- Configuration
    'required_option',        -- Mandatory selection
    'optional_feature',       -- Customer-selectable add-on
    'mutually_exclusive'      -- XOR relationship (choose one)
  ));
```

---

## Real-World Scenario: Pet Jar Manufacturing

### Manufacturing Flow (with UOM Transitions)

```
PET Resin (metric tons)
  → Preform (kg)
    → Bottle (pieces) + Cap (pieces)
      → Assembly (pieces)
```

### Packaging Hierarchy

```
Bottle (1 piece)
  → 6-Pack (6 pieces)
    → Dozen Pack (7 × 6-packs = 42 pieces)
      → Carton (10 × dozen = 420 pieces)
```

### Product Definitions

#### 1. PET Resin (Raw Material)

```sql
-- Product
INSERT INTO products (id, sku, name, product_type, price) VALUES
  ('raw-pet-resin', 'RAW-PET-001', 'PET Resin Pellets', 'raw_material', 1200.00);

-- UOM mappings
INSERT INTO product_uoms (product_id, uom_id, is_base_uom, is_purchase_uom, is_stock_uom, conversion_factor) VALUES
  -- Base: MT (vendor sells in tons, we track in tons)
  ('raw-pet-resin', (SELECT id FROM units_of_measure WHERE code='MT'), true, true, true, 1.0),
  -- Alternate: KG (for BOM calculations)
  ('raw-pet-resin', (SELECT id FROM units_of_measure WHERE code='KG'), false, false, false, 0.001);
  -- Interpretation: 1 KG = 0.001 MT, or 1 MT = 1000 KG
```

**Agent logic:**
- **Procurement specialist:** "Vendor sells PET resin by metric ton; create PO for 5 MT"
- **Inventory specialist:** "Stock level: 2.5 MT = 2500 KG available"

#### 2. Preform (Component)

```sql
-- Product
INSERT INTO products (id, sku, name, product_type, price) VALUES
  ('comp-preform-500', 'COMP-PREFORM-500ML', 'PET Preform 500ml', 'component', 2.00);

-- UOM mappings
INSERT INTO product_uoms (product_id, uom_id, is_base_uom, is_stock_uom, is_production_uom, conversion_factor) VALUES
  -- Base: KG (manufactured and stocked in kg)
  ('comp-preform-500', (SELECT id FROM units_of_measure WHERE code='KG'), true, true, true, 1.0),
  -- Alternate: PC (for BOM to bottles)
  ('comp-preform-500', (SELECT id FROM units_of_measure WHERE code='PC'), false, false, false, 40.0);
  -- Interpretation: 1 piece weighs 25g = 0.025 kg, so 1 kg = 40 pieces

-- Manufacturing BOM
INSERT INTO product_relationships
  (source_product_id, target_product_id, relationship_type, quantity, target_uom_id) VALUES
  -- To make 1 kg of preforms, need 1.05 kg of resin (5% waste)
  ('comp-preform-500', 'raw-pet-resin', 'component', 1.05,
   (SELECT id FROM units_of_measure WHERE code='KG'));
```

**Agent logic:**
- **Production specialist:** "Manufacture 500 kg of preforms; need 525 kg of PET resin"
- **Inventory specialist:** "Stock: 300 kg preforms = 12,000 pieces available"

#### 3. Cap (Component)

```sql
-- Product
INSERT INTO products (id, sku, name, product_type, price) VALUES
  ('comp-cap-38mm', 'COMP-CAP-38MM', 'Screw Cap 38mm', 'component', 0.50);

-- UOM mappings
INSERT INTO product_uoms (product_id, uom_id, is_base_uom, is_stock_uom, conversion_factor) VALUES
  -- Base: PC (purchased and stocked in pieces)
  ('comp-cap-38mm', (SELECT id FROM units_of_measure WHERE code='PC'), true, true, 1.0);
```

#### 4. Bottle (Finished Good)

```sql
-- Product
INSERT INTO products (id, sku, name, product_type, price) VALUES
  ('bottle-pet-500', 'BOTTLE-PET-500ML', 'PET Bottle 500ml', 'finished_good', 5.00);

-- UOM mappings
INSERT INTO product_uoms (product_id, uom_id, is_base_uom, is_production_uom, is_stock_uom, is_sales_uom, conversion_factor) VALUES
  -- Base: PC (manufactured, stocked, sold in pieces)
  ('bottle-pet-500', (SELECT id FROM units_of_measure WHERE code='PC'), true, true, true, true, 1.0);

-- Manufacturing BOM
INSERT INTO product_relationships
  (source_product_id, target_product_id, relationship_type, quantity, target_uom_id) VALUES
  -- 1 bottle needs 1 preform (piece-to-piece)
  ('bottle-pet-500', 'comp-preform-500', 'component', 1,
   (SELECT id FROM units_of_measure WHERE code='PC')),
  -- 1 bottle needs 1 cap
  ('bottle-pet-500', 'comp-cap-38mm', 'component', 1,
   (SELECT id FROM units_of_measure WHERE code='PC'));
```

**Cross-UOM BOM explosion:** When calculating materials for 1000 bottles:
```python
# Need 1000 pieces of preforms
# Convert pieces to kg: 1000 PC ÷ 40 PC/KG = 25 KG preforms
# Check stock: "Do we have 25 KG preforms?"
```

#### 5. Packaging Hierarchy (Distribution SKUs)

**6-Pack:**

```sql
INSERT INTO products (id, sku, name, product_type, price) VALUES
  ('pack-6-bottle-500', '6PK-BOTTLE-500ML', '6-Pack PET Bottles 500ml', 'bundle', 28.00);

INSERT INTO product_uoms (product_id, uom_id, is_base_uom, is_sales_uom, conversion_factor,
                          contains_quantity, contained_uom_id, barcode, weight_kg) VALUES
  ('pack-6-bottle-500', (SELECT id FROM units_of_measure WHERE code='PC'), true, true, 1.0,
   6, (SELECT id FROM units_of_measure WHERE code='PC'), '5012345678901', 0.750);

-- Packaging relationship (NOT manufacturing)
INSERT INTO product_relationships
  (source_product_id, target_product_id, relationship_type, quantity, target_uom_id) VALUES
  ('pack-6-bottle-500', 'bottle-pet-500', 'inner_pack', 6,
   (SELECT id FROM units_of_measure WHERE code='PC'));
```

**Dozen Pack (7 × 6-packs = 42 bottles):**

```sql
INSERT INTO products (id, sku, name, product_type, price) VALUES
  ('pack-dz-bottle-500', 'DZ7-BOTTLE-500ML', 'Dozen Pack (7x6) PET Bottles', 'bundle', 190.00);

INSERT INTO product_relationships
  (source_product_id, target_product_id, relationship_type, quantity, target_uom_id) VALUES
  ('pack-dz-bottle-500', 'pack-6-bottle-500', 'master_case', 7,
   (SELECT id FROM units_of_measure WHERE code='PC'));
```

**Master Carton (10 × dozen = 420 bottles):**

```sql
INSERT INTO products (id, sku, name, product_type, price) VALUES
  ('carton-bottle-500', 'CTN-BOTTLE-500ML', 'Master Carton PET Bottles 500ml', 'bundle', 1800.00);

INSERT INTO product_relationships
  (source_product_id, target_product_id, relationship_type, quantity, target_uom_id) VALUES
  ('carton-bottle-500', 'pack-dz-bottle-500', 'pallet_load', 10,
   (SELECT id FROM units_of_measure WHERE code='PC'));
```

**Packaging hierarchy summary:**
```
Carton (1 CTN = 420 bottles)
  ├─ 10 × Dozen Packs (1 DZ = 42 bottles)
      └─ 7 × 6-Packs (1 6PK = 6 bottles)
          └─ 6 × Bottles (1 PC)
```

---

## Agent Decision Scenarios

### Scenario 1: Procurement Planning

**User request:** "We need to fulfill 10,000 bottle orders"

**Agent reasoning chain:**

1. **Sales UOM:** Customer orders 10,000 pieces bottles
2. **BOM explosion:**
   - Need 10,000 PC preforms
   - Need 10,000 PC caps
3. **Convert to stock UOM:**
   - Preforms: 10,000 PC ÷ 40 PC/KG = 250 KG
   - Caps: 10,000 PC (already in stock UOM)
4. **Check inventory:**
   - Preforms: Stock 180 KG (shortage: 70 KG)
   - Caps: Stock 8,000 PC (shortage: 2,000 PC)
5. **Calculate raw materials for preforms:**
   - To make 70 KG preforms, need 73.5 KG resin (5% waste)
   - Convert to purchase UOM: 73.5 KG = 0.0735 MT
6. **Procurement actions:**
   - "Order 0.1 MT PET resin (min order qty)"
   - "Order 2,000 PC caps from supplier"

### Scenario 2: Inventory Reservation

**User request:** "Reserve inventory for 50 carton order"

**Agent reasoning chain:**

1. **Sales UOM:** 50 cartons ordered
2. **Explode packaging hierarchy:**
   - 1 carton = 10 dozen packs
   - 1 dozen pack = 7 six-packs
   - 1 six-pack = 6 bottles
   - **Total:** 50 CTN × 10 DZ × 7 6PK × 6 PC = 21,000 bottles
3. **Check stock UOM:** "Do we have 21,000 PC in stock?"
4. **Reserve:** Lock 21,000 PC of `bottle-pet-500`
5. **Warehouse instruction:** "Pick 50 master cartons for shipment"

### Scenario 3: Batch-Specific Catch Weight

**Scenario:** Preforms have variable weight per batch (manufacturing variance)

```sql
-- Batch A: 1 kg = 38 pieces (heavier preforms)
INSERT INTO product_uoms (product_id, uom_id, conversion_type, conversion_factor, batch_id) VALUES
  ('comp-preform-500', (SELECT id FROM units_of_measure WHERE code='PC'),
   'batch_specific', 38.0, 'batch-a-001');

-- Batch B: 1 kg = 42 pieces (lighter preforms)
INSERT INTO product_uoms (product_id, uom_id, conversion_type, conversion_factor, batch_id) VALUES
  ('comp-preform-500', (SELECT id FROM units_of_measure WHERE code='PC'),
   'batch_specific', 42.0, 'batch-b-002');
```

**Agent logic:**
- **Inventory:** "Batch A: 100 KG = 3,800 PC; Batch B: 100 KG = 4,200 PC"
- **FIFO picking:** Use Batch A first (older); adjust piece count accordingly

### Scenario 4: Make vs Buy Decision

**Scenario:** Planning agent compares assembling jars vs purchasing finished goods

```sql
-- Alternative: Purchase complete jars
INSERT INTO products (id, sku, name, product_type, price) VALUES
  ('jar-purchase-500', 'JAR-VENDOR-500ML', 'Pet Jar 500ml (Purchased)', 'finished_good', 4.50);

INSERT INTO product_relationships
  (source_product_id, target_product_id, relationship_type, quantity, target_uom_id,
   substitution_priority, substitution_reason, lead_time_days) VALUES
  ('bottle-pet-500', 'jar-purchase-500', 'alternate', 1,
   (SELECT id FROM units_of_measure WHERE code='PC'), 2, 'cost_effective', 7);
```

**Agent decision matrix:**

| Option | Component Cost | Lead Time | Capacity Required | Decision Factor |
|--------|---------------|-----------|-------------------|-----------------|
| **Make** | $2.50 | 2 days | 70% | Preferred if capacity available |
| **Buy** | $4.50 | 7 days | 0% | Fallback during capacity constraints |

**Agent logic:**
```python
if current_capacity < 0.8 and lead_time_acceptable(order_date, 2):
    return "MAKE: Assemble from components ($2.50 cost, 2 day lead)"
elif vendor_available and lead_time_acceptable(order_date, 7):
    return "BUY: Purchase finished goods ($4.50 cost, 7 day lead)"
else:
    return "ALERT: Cannot fulfill order within required timeframe"
```

### Scenario 5: Quality Issue - Where-Used Analysis

**Scenario:** Defective lid batch detected; find all affected assemblies

**Agent query:**

```sql
WITH RECURSIVE assembly_tree AS (
  -- Base: Products using defective lid
  SELECT
    pr.source_product_id as assembly_id,
    'bottle-pet-500' as component_id,
    1 as level
  FROM product_relationships pr
  WHERE pr.target_product_id = 'comp-lid-batch-defective'
    AND pr.relationship_type = 'component'

  UNION

  -- Recursive: Products using affected assemblies
  SELECT
    pr.source_product_id,
    at.assembly_id,
    at.level + 1
  FROM product_relationships pr
  JOIN assembly_tree at ON pr.target_product_id = at.assembly_id
  WHERE pr.relationship_type IN ('component', 'inner_pack', 'master_case')
)
SELECT DISTINCT
  p.sku,
  p.name,
  p.product_type,
  at.level,
  inv.quantity_on_hand,
  inv.lot_number
FROM assembly_tree at
JOIN products p ON p.id = at.assembly_id
JOIN inventory inv ON inv.product_id = p.id
WHERE inv.quantity_on_hand > 0
ORDER BY at.level, p.sku;
```

**Agent action:**
- "FREEZE 1,500 bottles (Lot #ABC123) using defective lid batch"
- "NOTIFY quality team: 3 cartons already shipped (customer recall required)"

### Scenario 6: Configurable Product - Sales Validation

**Scenario:** Customer configures custom jar with optional lid colors

```sql
-- Base product
INSERT INTO products (id, sku, name, product_type) VALUES
  ('jar-configurable', 'JAR-CONFIG-500ML', 'Configurable Jar 500ml', 'finished_good');

-- Required components
INSERT INTO product_relationships (source_product_id, target_product_id, relationship_type,
                                   quantity, is_optional) VALUES
  ('jar-configurable', 'comp-preform-500', 'required_option', 1, false),
  ('jar-configurable', 'comp-bottle-body', 'required_option', 1, false);

-- Optional lid colors (mutually exclusive)
INSERT INTO product_relationships (source_product_id, target_product_id, relationship_type,
                                   quantity, is_optional, configuration_context) VALUES
  ('jar-configurable', 'lid-red', 'mutually_exclusive', 1, true, '{"option_group": "lid_color", "value": "red"}'),
  ('jar-configurable', 'lid-blue', 'mutually_exclusive', 1, true, '{"option_group": "lid_color", "value": "blue"}'),
  ('jar-configurable', 'lid-green', 'mutually_exclusive', 1, true, '{"option_group": "lid_color", "value": "green"}');
```

**Sales agent validation:**

```python
def validate_configuration(base_product_id: str, selected_options: List[str]) -> ValidationResult:
    # Check: Exactly one selection for mutually-exclusive groups
    exclusive_groups = db.query("""
        SELECT
            configuration_context->>'option_group' as group_name,
            COUNT(*) as selections
        FROM product_relationships
        WHERE source_product_id = %s
          AND relationship_type = 'mutually_exclusive'
          AND target_product_id = ANY(%s)
        GROUP BY group_name
        HAVING COUNT(*) != 1
    """, (base_product_id, selected_options))

    if exclusive_groups:
        return ValidationResult(
            valid=False,
            errors=[f"Must select exactly one option for: {', '.join(exclusive_groups)}"]
        )

    # Check: All required options present
    missing_required = db.query("""
        SELECT target_product_id
        FROM product_relationships
        WHERE source_product_id = %s
          AND relationship_type = 'required_option'
          AND target_product_id NOT IN (%s)
    """, (base_product_id, selected_options))

    if missing_required:
        return ValidationResult(
            valid=False,
            errors=[f"Missing required components: {', '.join(missing_required)}"]
        )

    return ValidationResult(valid=True)
```

---

## Query Patterns

### BOM Explosion with UOM Conversion

```sql
WITH RECURSIVE bom_explosion AS (
  -- Base: Finished good needed
  SELECT
    'bottle-pet-500'::UUID as product_id,
    10000 as quantity_needed,
    'PC' as uom_code,
    0 as level

  UNION ALL

  -- Recursive: Components needed
  SELECT
    pr.target_product_id,
    be.quantity_needed * pr.quantity as quantity_needed,
    uom.code as uom_code,
    be.level + 1
  FROM bom_explosion be
  JOIN product_relationships pr ON pr.source_product_id = be.product_id
    AND pr.relationship_type = 'component'
  JOIN units_of_measure uom ON uom.id = pr.target_uom_id
  WHERE be.level < 10  -- Prevent infinite loops
)
SELECT
  p.sku,
  p.name,
  be.quantity_needed,
  be.uom_code,
  be.level,
  -- Convert to stock UOM
  CASE
    WHEN puom.is_stock_uom THEN
      be.quantity_needed * puom.conversion_factor
    ELSE be.quantity_needed
  END as stock_quantity,
  stock_uom.code as stock_uom_code
FROM bom_explosion be
JOIN products p ON p.id = be.product_id
LEFT JOIN product_uoms puom ON puom.product_id = p.id AND puom.is_stock_uom = true
LEFT JOIN units_of_measure stock_uom ON stock_uom.id = puom.uom_id
ORDER BY be.level, p.sku;
```

**Expected Output:**

| SKU | Name | Qty Needed | UOM | Level | Stock Qty | Stock UOM |
|-----|------|------------|-----|-------|-----------|-----------|
| BOTTLE-PET-500ML | PET Bottle 500ml | 10000 | PC | 0 | 10000 | PC |
| COMP-PREFORM-500ML | PET Preform | 10000 | PC | 1 | 250 | KG |
| COMP-CAP-38MM | Screw Cap | 10000 | PC | 1 | 10000 | PC |
| RAW-PET-RESIN | PET Resin | 262.5 | KG | 2 | 0.2625 | MT |

### Packaging Hierarchy Explosion

```sql
WITH RECURSIVE pack_explosion AS (
  -- Base: Top-level packaging unit ordered
  SELECT
    'carton-bottle-500'::UUID as pack_id,
    50 as quantity,
    0 as level

  UNION ALL

  -- Recursive: Contained items
  SELECT
    pr.target_product_id,
    pe.quantity * pr.quantity,
    pe.level + 1
  FROM pack_explosion pe
  JOIN product_relationships pr ON pr.source_product_id = pe.pack_id
    AND pr.relationship_type IN ('inner_pack', 'master_case', 'pallet_load')
  WHERE pe.level < 5  -- Prevent infinite loops
)
SELECT
  p.sku,
  p.name,
  pe.quantity,
  pe.level,
  p.product_type
FROM pack_explosion pe
JOIN products p ON p.id = pe.pack_id
ORDER BY pe.level, p.sku;
```

**Expected Output:**

| SKU | Name | Quantity | Level | Type |
|-----|------|----------|-------|------|
| CTN-BOTTLE-500ML | Master Carton | 50 | 0 | bundle |
| DZ7-BOTTLE-500ML | Dozen Pack (7x6) | 500 | 1 | bundle |
| 6PK-BOTTLE-500ML | 6-Pack | 3500 | 2 | bundle |
| BOTTLE-PET-500ML | PET Bottle 500ml | 21000 | 3 | finished_good |

### Effectivity-Based Component Selection

```sql
SELECT
  p_parent.sku as parent_sku,
  p_component.sku as component_sku,
  pr.quantity,
  uom.code as uom,
  pr.effective_from,
  pr.effective_to,
  pr.serial_number_from,
  pr.serial_number_to,
  pr.configuration_context
FROM product_relationships pr
JOIN products p_parent ON p_parent.id = pr.source_product_id
JOIN products p_component ON p_component.id = pr.target_product_id
JOIN units_of_measure uom ON uom.id = pr.target_uom_id
WHERE pr.source_product_id = 'bottle-pet-500'
  AND pr.relationship_type = 'component'
  AND (pr.effective_from IS NULL OR pr.effective_from <= CURRENT_DATE)
  AND (pr.effective_to IS NULL OR pr.effective_to >= CURRENT_DATE)
  AND (pr.serial_number_from IS NULL OR pr.serial_number_from <= %s)  -- production_serial
  AND (pr.serial_number_to IS NULL OR pr.serial_number_to >= %s)
ORDER BY pr.sort_order;
```

### Cost Rollup (Bottom-Up BOM Costing)

```sql
WITH RECURSIVE bom_tree AS (
  -- Leaf nodes: raw materials/purchased components (no children)
  SELECT
    p.id as product_id,
    p.sku,
    p.price as component_cost,
    0 as level
  FROM products p
  WHERE NOT EXISTS (
    SELECT 1 FROM product_relationships pr
    WHERE pr.source_product_id = p.id AND pr.relationship_type = 'component'
  )

  UNION

  -- Recursive: assemblies with component costs rolled up
  SELECT
    pr.source_product_id as product_id,
    p.sku,
    SUM(bt.component_cost * pr.quantity) as component_cost,
    MAX(bt.level) + 1 as level
  FROM product_relationships pr
  JOIN bom_tree bt ON bt.product_id = pr.target_product_id
  JOIN products p ON p.id = pr.source_product_id
  WHERE pr.relationship_type = 'component'
  GROUP BY pr.source_product_id, p.sku
)
SELECT
  sku,
  component_cost,
  level
FROM bom_tree
ORDER BY level DESC, sku;
```

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1)

**Database Schema:**
- [x] Add `product_type` to existing `products` table
- [ ] Create `uom_categories` table
- [ ] Create `units_of_measure` table
- [ ] Create `product_uoms` table
- [ ] Create `product_relationships` table
- [ ] Add indexes for traversal queries
- [ ] Add audit triggers

**Data Migration:**
- [ ] Classify existing products by type (finished_good vs component)
- [ ] Insert standard UOMs (kg, MT, PC, L, etc.)
- [ ] Create product-UOM mappings for existing products

**Pydantic Models:**
- [ ] `UOMCategory` schema
- [ ] `UnitOfMeasure` schema
- [ ] `ProductUOM` schema
- [ ] `ProductRelationship` schema
- [ ] Update `Product` schema with `product_type`

### Phase 2: Basic BOM (Week 2)

**Features:**
- [ ] Model simple component relationships (jar → lid + preform)
- [ ] Implement BOM explosion queries (recursive CTEs)
- [ ] Implement where-used queries (reverse BOM)
- [ ] UOM conversion utilities

**Agent Updates:**
- [ ] Update procurement specialist to use BOM data
- [ ] Extend inventory specialist for multi-level reservations
- [ ] Add costing specialist for BOM cost rollup

**Testing:**
- [ ] Unit tests for BOM explosion logic
- [ ] Unit tests for UOM conversions
- [ ] Integration tests for procurement planning

### Phase 3: Advanced Manufacturing (Week 3-4)

**Features:**
- [ ] Effectivity support (time-based, serial-based, configuration-based)
- [ ] Phantom assembly handling
- [ ] Substitute/alternate relationships
- [ ] Batch-specific UOM conversions

**Agent Updates:**
- [ ] Planning specialist: effectivity-aware component selection
- [ ] Inventory specialist: phantom assembly skip logic
- [ ] Procurement specialist: automatic substitution during shortages

**Testing:**
- [ ] Test effectivity date filtering
- [ ] Test phantom assembly explosion
- [ ] Test substitute selection logic

### Phase 4: Packaging & Commercial (Week 5)

**Features:**
- [ ] Packaging hierarchy relationships (inner_pack, master_case, pallet_load)
- [ ] Bundle relationships with pricing adjustments
- [ ] Accessory/cross-sell relationships
- [ ] Upgrade path tracking

**Agent Updates:**
- [ ] Catalog specialist: sync packaging hierarchy to platforms
- [ ] Sales specialist: packaging-aware order fulfillment
- [ ] Marketing specialist: accessory recommendations

**Testing:**
- [ ] Test packaging hierarchy explosion
- [ ] Test bundle pricing calculations
- [ ] Test cross-sell recommendations

### Phase 5: Configuration Support (Week 6+)

**Features:**
- [ ] Modular BOM support (optional/required components)
- [ ] Mutually exclusive component groups
- [ ] Configuration validation logic
- [ ] 150% BOM pattern

**Agent Updates:**
- [ ] Sales specialist: configuration validation
- [ ] Manufacturing specialist: filter configured BOM
- [ ] Pricing specialist: dynamic pricing for configurations

**Testing:**
- [ ] Test configuration validation rules
- [ ] Test mutually exclusive constraints
- [ ] Test dynamic BOM filtering

### Phase 6: Optimization & Performance (Week 7+)

**Performance:**
- [ ] Materialized views for common BOM explosions
- [ ] Caching for UOM conversions
- [ ] Batch query optimizations
- [ ] Index tuning based on query patterns

**Observability:**
- [ ] LangSmith traces for agent BOM decisions
- [ ] Metrics: BOM explosion latency, conversion accuracy
- [ ] Alerts: circular BOM references, missing UOMs

---

## Open Questions & Design Decisions

### Q&A Session Log

#### Q1: Multi-UOM Transitions & Nested Packaging (2025-11-12)

**Question:** "Preform is made from pet resins (metric tons), manufactured and stored in kg, assembled into bottles (pieces), then packed in 6-pc sets → 7-dozen packages → big cartons. How is this covered?"

**Answer:** Three-system architecture:
1. **UOM Conversion:** Same product tracked in multiple units (resin: MT/KG, preforms: KG/PC)
2. **Manufacturing BOM:** Physical transformation (resin → preform → bottle)
3. **Packaging Hierarchy:** Aggregation without transformation (bottle → 6-pack → dozen → carton)

**Design Decision:**
- Each product has base UOM + alternate UOMs with conversion factors
- BOM relationships specify quantity AND UOM explicitly
- Packaging levels are separate products (not just UOMs) with own SKUs
- Agents convert quantities across UOMs during planning/procurement

**Implementation:** See [Real-World Scenario: Pet Jar Manufacturing](#real-world-scenario-pet-jar-manufacturing)

---

### Open Design Questions

**To be resolved during implementation:**

1. **Circular BOM Detection:** How should agents handle circular references?
   - Option A: Database constraint preventing cycles (strict)
   - Option B: Runtime detection during explosion (flexible for phantom/alternate patterns)
   - **Decision:** TBD

2. **Effectivity Overlap Validation:** Can multiple effectivity periods overlap?
   - Example: Component A valid 2025-01-01 to 2025-06-30, Component B valid 2025-06-01 to 2025-12-31
   - **Decision:** TBD (likely allow overlaps, agent selects based on production date)

3. **Multi-level Phantom Handling:** Can phantom assemblies contain other phantoms?
   - **Decision:** TBD (likely yes, but limit depth to prevent performance issues)

4. **Bundle vs BOM Distinction:** When is a relationship a bundle vs component?
   - **Rule of thumb:** If physical transformation occurs → component; if pre-packaged → bundle
   - **Edge case:** Kit assembly in warehouse (pick + shrink wrap) - which type?
   - **Decision:** TBD

5. **Cross-Family Relationships:** Can components belong to multiple product families?
   - Example: Same lid used across jar families (250ml, 500ml, 1L)
   - **Decision:** TBD (likely yes, components can be reused across families)

6. **UOM Rounding Rules:** How to handle fractional quantities during conversions?
   - Example: 1 MT resin = 40,000 preforms, but 1 preform = 0.000025 MT (rounding errors)
   - **Decision:** TBD (likely define precision per UOM, round at final step)

7. **Batch Tracking Integration:** Should batch IDs link to existing inventory batches?
   - **Decision:** TBD (likely foreign key to `batches` table if it exists)

8. **Relationship Versioning:** Track historical changes to BOM relationships?
   - **Decision:** TBD (likely use audit_log table or relationship history table)

9. **Component Lead Time Rollup:** Should parent lead time = max(component lead times)?
   - **Decision:** TBD (agent logic vs database constraint)

10. **Multi-Supplier Component Pricing:** How to model component cost when multiple vendors?
    - **Decision:** TBD (likely separate vendor_products table with pricing, procurement selects cheapest)

---

## Related Documentation

- [DATABASE_SCHEMA_DESIGN.md](./DATABASE_SCHEMA_DESIGN.md) - Current database schema
- [DYNAMIC_SCHEMA_DRIVEN_ARCHITECTURE.md](./DYNAMIC_SCHEMA_DRIVEN_ARCHITECTURE.md) - Dynamic CRUD architecture
- [PRODUCT_ONBOARDING_COMPLETE_DESIGN.md](../workflows/PRODUCT_ONBOARDING_COMPLETE_DESIGN.md) - Product onboarding workflow
- [DOMAIN_DESIGN_GUIDELINES.md](./DOMAIN_DESIGN_GUIDELINES.md) - Domain design standards

---

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2025-11-12 | Abhishek Keshri + Claude | Initial design document capturing complete relationship taxonomy, UOM architecture, and pet jar manufacturing scenario |

---

**Status:** 🔄 Living document - will be updated as Q&A session continues and design decisions are finalized.
