# Product Onboarding Development Plan

**Date:** 2025-10-23
**Status:** 📋 Planning Phase
**Company:** PAVISHA PET INDUSTRIES
**Prerequisites:** ✅ Database schema implemented, company data populated

---

## Executive Summary

Systematic development plan for building product onboarding specialists and tools to leverage the normalized database schema. Focuses on single-product perfection for PAVISHA's B2B packaging catalog.

**Phase Objective:** Enable PAVISHA to onboard PET packaging products (bottles, jars, containers, preforms) with complete marketing intelligence for multi-platform distribution.

---

## Part I: Business Context - PAVISHA

### Company Profile
- **Name:** PAVISHA PET INDUSTRIES
- **Location:** Patna, Bihar, India
- **Scale:** 30,000m² facility, 36 automated production lines
- **Capacity:** 2 million units/day, 6.4 million units/annually
- **Certifications:** Food-grade (IS:12252), BPA-free, ISO compliance

### Business Model
- **Primary:** B2B manufacturing (enterprise solutions)
- **Target Customers:** Food processors, beverage manufacturers, FMCG companies, pharma, cosmetics
- **Pricing:** Quote-based, custom requirements
- **Positioning:** Premium quality-focused, automation-driven, compliance-first

### Product Portfolio (Examples)
1. **PET Bottles**: Various capacities (100ml-5L), custom shapes, food-grade
2. **PET Jars**: Wide-mouth, narrow-mouth, specialty closures
3. **PET Containers**: Cans, custom shapes, tamper-evident
4. **PET Preforms**: Various neck finishes, weight specs
5. **Accessories**: Sealing machines, lids, covers, closures

### Target Industries (NAICS)
- **311** - Food Manufacturing
- **312** - Beverage and Tobacco Product Manufacturing
- **325** - Chemical Manufacturing (cosmetics, household)
- **339** - Medical Equipment Manufacturing
- **445** - Food and Beverage Stores (wholesale)

### Competitive Landscape
- **National Leaders:** Mold-Tek Packaging (USD 500M cap), UFlex Limited (140+ countries)
- **Regional Players:** Hitech Plast, Jindal Poly Films, Sharvi Pet Patna
- **Differentiation:** 24/7 automation, three-tier QC, customization capabilities, food-grade compliance

---

## Part II: Architecture Foundation (Already Built)

### ✅ Database Schema (Implemented)
- **Single-Tenant:** Unique index enforcement, no company_id pollution
- **Product Families:** Composition pattern for variants
- **Variant System:** Axes → Values → Products → Junction table
- **Multi-Level Images:** Family-shared OR variant-specific
- **Customer Segments:** B2B/B2C/D2C messaging strategies
- **Industry Targeting:** M:N with product_family_industries
- **Marketing Content:** Platform-specific versioning, A/B testing
- **Temporal Tracking:** Automatic price/inventory history
- **Audit Trail:** Universal change logging

### ✅ Current Capabilities (MVP)
- **WhatsApp Integration:** Webhook handling, media download, idempotency
- **PM Agent:** Intent classification, department routing
- **Cataloging Department:** Basic product draft creation
- **HITL Workflow:** Approval flow via pending_approvals table
- **Storage Layer:** Supabase adapter with company context injection

---

## Part III: Development Roadmap

### Phase 1: Product Intelligence Specialist (Week 1)

**Objective:** Build specialist to extract comprehensive product data for the new schema.

#### 1.1 Update Product Model (Day 1)
**File:** `agents/src/autifyme_agents/schemas/models.py`

**Changes:**
```python
class ProductFamily(BaseModel):
    """Parent product concept (e.g., '500ml PET Bottle'"""
    id: UUID | None = None
    product_group_id: str  # Schema.org ProductGroup ID
    sku_prefix: str  # e.g., 'PAV-BTL-500'

    name: str
    description: str
    brand: str = "PAVISHA"

    category_id: UUID | None = None
    google_product_category: str | None = None

    base_price: Decimal
    price_currency: str = "INR"

    material: str | None = "PET"
    condition: Literal["new", "refurbished", "used"] = "new"

    tags: list[str] = Field(default_factory=list)
    custom_attributes: dict[str, Any] = Field(default_factory=dict)
    # Example custom_attributes for PET packaging:
    # {
    #   "neck_finish": "28mm PCO",
    #   "weight_grams": 24,
    #   "wall_thickness_mm": 0.35,
    #   "closure_type": "screw_cap",
    #   "food_grade_certified": true,
    #   "bpa_free": true,
    #   "recyclable": true
    # }

    lifecycle_stage: Literal["new_arrival", "regular", "clearance", "discontinued"] = "regular"

class VariantAxis(BaseModel):
    """Dimension along which product varies (e.g., 'capacity', 'color')"""
    id: UUID | None = None
    name: str  # 'capacity', 'color', 'neck_finish'
    display_label: str  # 'Capacity', 'Color', 'Neck Finish'
    sort_order: int = 0
    schema_property: str | None = None  # Schema.org property URL

class VariantValue(BaseModel):
    """Specific value for axis (e.g., '500ml', 'Clear', '28mm PCO')"""
    id: UUID | None = None
    variant_axis_id: UUID

    value: str  # '500ml', 'Clear', '28mm PCO'
    display_label: str | None = None  # 'Small (500ml)', 'Transparent'
    sku_code: str  # 'SM', 'CLR', '28PCO' (for SKU generation)

    color_hex: str | None = None  # For color swatches
    image_url: str | None = None
    price_adjustment: Decimal = Decimal('0.00')

    sort_order: int = 0

class Product(BaseModel):
    """Individual SKU (specific variant)"""
    id: UUID | None = None
    product_family_id: UUID

    sku: str  # 'PAV-BTL-500-CLR-28PCO'
    name: str | None = None  # Auto-generated if None

    price: Decimal | None = None  # Overrides base_price if set
    sale_price: Decimal | None = None
    sale_price_start: date | None = None
    sale_price_end: date | None = None

    availability: Literal["in_stock", "out_of_stock", "preorder", "backorder", "discontinued"] = "in_stock"
    stock_quantity: int | None = None

    link: str | None = None  # Product page URL

    is_primary_variant: bool = False  # Hero variant
    custom_attributes: dict[str, Any] = Field(default_factory=dict)

class CustomerSegment(BaseModel):
    """B2B/B2C/D2C messaging strategy"""
    id: UUID | None = None
    product_family_id: UUID

    segment_type: Literal["b2b", "b2c", "d2c", "wholesale", "enterprise", "retail"]
    segment_label: str  # 'Food & Beverage Manufacturers', 'Retail Distributors'

    tone: Literal["professional", "casual", "technical", "emotional", "educational", "aspirational"]
    key_benefits: list[str]
    pain_points: list[str]
    primary_channels: list[str]  # ['linkedin', 'email', 'trade_shows']
    content_formats: list[str]  # ['whitepapers', 'case_studies', 'spec_sheets']

    pricing_notes: str | None = None

class ProductFamilyIndustry(BaseModel):
    """M:N junction for multi-industry targeting"""
    id: UUID | None = None
    product_family_id: UUID
    industry_naics_code: str  # e.g., '311' (Food Manufacturing)

    industry_use_case: str  # 'Packaging for beverages, sauces, condiments'
    industry_benefits: list[str]  # ['Food-grade certified', 'Tamper-evident', 'Lightweight']
    compliance_notes: str | None = None  # 'FSSAI compliant, IS:12252 certified'

    is_primary_industry: bool = False
```

**Estimated Effort:** 4 hours (modeling + validation)

---

#### 1.2 Product Intelligence Specialist Prompt (Day 2)
**File:** `agents/src/autifyme_agents/prompts/product_intelligence_specialist.md`

**Prompt Structure:**
```xml
<role>
You are the Product Intelligence Specialist for PAVISHA PET INDUSTRIES, a leading B2B packaging manufacturer.

Your mission: Extract comprehensive product specifications from user input (text, images, documents) to populate the complete product catalog schema.
</role>

<company_context>
{{company_profile}}
{{company_intelligence}}
</company_context>

<capabilities>
You have access to these analysis tools:
- image_analysis: Analyze product images to extract visual specs (shape, color, dimensions)
- document_analysis: Extract specs from technical datasheets, catalogs
- web_search: Research competitive products, industry standards
</capabilities>

<output_schema>
Generate a ProductFamily with:

1. **Core Identification**
   - product_group_id: Unique identifier (e.g., 'PAV-PET-BOTTLE-500ML')
   - sku_prefix: SKU prefix for variants (e.g., 'PAV-BTL-500')
   - name: Concise product name (e.g., '500ml PET Bottle - Food Grade')
   - description: Detailed description emphasizing:
     * Technical specifications
     * Use cases / industries
     * Compliance / certifications
     * Competitive advantages

2. **Variant Axes** (if applicable)
   Identify dimensions along which this product varies:
   - Common for PET packaging: capacity, color, neck_finish, closure_type
   - Extract all possible values per axis
   - Generate SKU codes for each value

3. **Pricing Intelligence**
   - base_price: Starting price (if known)
   - pricing strategy: Quote-based vs fixed
   - price positioning: premium, mid-range, economy

4. **Custom Attributes** (JSONB)
   Extract PET packaging-specific fields:
   - neck_finish: '28mm PCO', '38mm PCO', etc.
   - weight_grams: Preform/container weight
   - wall_thickness_mm: Thickness specification
   - capacity_ml: Exact capacity
   - closure_type: 'screw_cap', 'flip_top', 'pump'
   - food_grade_certified: boolean
   - bpa_free: boolean
   - recyclable: boolean
   - manufacturing_process: 'injection_molding', 'blow_molding', etc.

5. **Industry Targeting**
   Map to NAICS codes and define use cases:
   - Primary industries (e.g., 311 Food Manufacturing)
   - Use case descriptions per industry
   - Industry-specific benefits
   - Compliance notes (FSSAI, IS:12252, etc.)

6. **Customer Segments**
   Define B2B messaging strategies:
   - Segment type (typically 'b2b' or 'wholesale' for PAVISHA)
   - Tone (professional, technical)
   - Key benefits (ROI-focused: "Reduces packaging costs by 15%")
   - Pain points addressed
   - Primary channels (LinkedIn, email, trade shows)
</output_schema>

<examples>
{{few_shot_examples}}
</examples>

<constraints>
- Default brand to "PAVISHA" unless explicitly different
- Default condition to "new"
- Default material to "PET" for packaging products
- Always include food_grade_certified in custom_attributes for food contact items
- Pricing: If unknown, note "quote_based" in pricing_notes
</constraints>
```

**Estimated Effort:** 6 hours (prompt engineering + testing)

---

#### 1.3 Product Intelligence Specialist Tool (Day 2-3)
**File:** `agents/src/autifyme_agents/tools/product_intelligence_tools.py`

```python
from langchain_core.tools import tool, ToolException
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from autifyme_agents.schemas.models import (
    ProductFamily,
    VariantAxis,
    VariantValue,
    CustomerSegment,
    ProductFamilyIndustry
)

class ProductIntelligenceInput(BaseModel):
    """Input for product intelligence extraction"""
    text: str | None = Field(None, description="User's text description of product")
    image_paths: list[str] = Field(default_factory=list, description="Paths to product images")
    document_paths: list[str] = Field(default_factory=list, description="Paths to spec sheets/catalogs")

class ProductIntelligenceOutput(BaseModel):
    """Comprehensive product intelligence"""
    product_family: ProductFamily
    variant_axes: list[VariantAxis] = Field(default_factory=list)
    variant_values: list[VariantValue] = Field(default_factory=list)
    customer_segments: list[CustomerSegment] = Field(default_factory=list)
    industry_mappings: list[ProductFamilyIndustry] = Field(default_factory=list)

    confidence_score: float = Field(ge=0.0, le=1.0, description="Overall extraction confidence")
    missing_fields: list[str] = Field(default_factory=list, description="Fields that need user clarification")

def create_product_intelligence_tool(
    llm: ChatOpenAI,
    company_profile: CompanyProfile,
    company_intelligence: CompanyIntelligence,
) -> Tool:
    """Create product intelligence specialist tool"""

    @tool("product_intelligence_specialist", args_schema=ProductIntelligenceInput)
    def product_intelligence_specialist(
        text: str | None = None,
        image_paths: list[str] | None = None,
        document_paths: list[str] | None = None,
    ) -> ProductIntelligenceOutput:
        """Extract comprehensive product specifications from user input.

        Analyzes text, images, and documents to generate complete ProductFamily
        with variants, segments, and industry mappings for B2B packaging products.
        """

        try:
            # Build context-rich payload
            context = {
                "company_profile": company_profile.model_dump(),
                "company_intelligence": company_intelligence.model_dump(),
                "input_text": text,
                "has_images": bool(image_paths),
                "has_documents": bool(document_paths),
            }

            # Load specialist prompt
            from pathlib import Path
            prompt_path = Path(__file__).parent.parent / "prompts" / "product_intelligence_specialist.md"
            prompt_template = prompt_path.read_text()

            # Inject context into prompt
            prompt = prompt_template.format(
                company_profile=json.dumps(context["company_profile"], indent=2),
                company_intelligence=json.dumps(context["company_intelligence"], indent=2),
                # few_shot_examples loaded from separate file
            )

            # Create structured output LLM
            structured_llm = llm.with_structured_output(ProductIntelligenceOutput)

            # Build messages with multimodal support
            messages = [
                ("system", prompt),
                ("human", text or "Analyze the provided product information"),
            ]

            # Add images if provided
            if image_paths:
                for img_path in image_paths:
                    # Load image as base64 for multimodal LLM
                    import base64
                    with open(img_path, "rb") as f:
                        img_data = base64.b64encode(f.read()).decode()
                    messages.append(("human", [{"type": "image_url", "image_url": f"data:image/jpeg;base64,{img_data}"}]))

            # Invoke specialist
            result: ProductIntelligenceOutput = structured_llm.invoke(messages)

            # Validate result
            if result.confidence_score < 0.6:
                raise ToolException(
                    f"Low confidence ({result.confidence_score:.2f}). Missing critical fields: {', '.join(result.missing_fields)}"
                )

            return result

        except Exception as e:
            raise ToolException(f"Product intelligence extraction failed: {str(e)}") from e

    return product_intelligence_specialist
```

**Estimated Effort:** 8 hours (tool creation + multimodal support + testing)

---

### Phase 2: Database Persistence Tools (Week 1)

#### 2.1 Product Family Persistence Tool (Day 4)
**File:** `agents/src/autifyme_agents/tools/product_persistence_tools.py`

```python
@tool("save_product_family")
def save_product_family(
    product_intelligence: ProductIntelligenceOutput,
) -> dict[str, Any]:
    """Persist ProductFamily and related entities to database.

    Transactionally creates:
    - product_families row
    - variant_axes rows
    - variant_values rows
    - customer_segments rows
    - product_family_industries rows

    Returns created IDs for subsequent product variant creation.
    """

    try:
        from supabase import create_client
        from autifyme_agents.core.config import settings

        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

        # 1. Insert product_family
        family_data = product_intelligence.product_family.model_dump(exclude_none=True)
        family_result = supabase.table("product_families").insert(family_data).execute()
        family_id = family_result.data[0]["id"]

        # 2. Insert variant_axes
        axis_id_map = {}
        for axis in product_intelligence.variant_axes:
            axis_data = axis.model_dump(exclude_none=True)
            axis_data["product_family_id"] = family_id
            axis_result = supabase.table("variant_axes").insert(axis_data).execute()
            axis_id_map[axis.name] = axis_result.data[0]["id"]

        # 3. Insert variant_values
        for value in product_intelligence.variant_values:
            value_data = value.model_dump(exclude_none=True)
            value_data["variant_axis_id"] = axis_id_map[value.variant_axis_id]  # Map axis name → ID
            supabase.table("variant_values").insert(value_data).execute()

        # 4. Insert customer_segments
        for segment in product_intelligence.customer_segments:
            segment_data = segment.model_dump(exclude_none=True)
            segment_data["product_family_id"] = family_id
            supabase.table("customer_segments").insert(segment_data).execute()

        # 5. Insert product_family_industries
        for industry in product_intelligence.industry_mappings:
            industry_data = industry.model_dump(exclude_none=True)
            industry_data["product_family_id"] = family_id
            supabase.table("product_family_industries").insert(industry_data).execute()

        return {
            "success": True,
            "product_family_id": family_id,
            "variant_axes_created": len(axis_id_map),
            "variant_values_created": len(product_intelligence.variant_values),
            "customer_segments_created": len(product_intelligence.customer_segments),
            "industries_mapped": len(product_intelligence.industry_mappings),
        }

    except Exception as e:
        raise ToolException(f"Failed to persist product family: {str(e)}") from e
```

**Estimated Effort:** 6 hours (transactional logic + error handling)

---

#### 2.2 Variant Generation Tool (Day 4-5)
**File:** `agents/src/autifyme_agents/tools/variant_generation_tools.py`

```python
@tool("generate_product_variants")
def generate_product_variants(
    product_family_id: UUID,
    generate_all_combinations: bool = True,
) -> dict[str, Any]:
    """Generate individual Product SKUs from ProductFamily variant axes.

    If generate_all_combinations=True:
        Generates Cartesian product of all variant values
        Example: 3 capacities × 2 colors × 2 neck finishes = 12 SKUs

    If generate_all_combinations=False:
        Generates only explicitly specified variants

    Returns list of created product IDs.
    """

    try:
        from itertools import product as cartesian_product
        from supabase import create_client
        from autifyme_agents.core.config import settings

        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

        # 1. Fetch product_family
        family = supabase.table("product_families").select("*").eq("id", str(product_family_id)).single().execute()

        # 2. Fetch all variant_axes for this family
        axes = supabase.table("variant_axes").select("*").eq("product_family_id", str(product_family_id)).execute()

        # 3. Fetch all variant_values for these axes
        axis_ids = [ax["id"] for ax in axes.data]
        values = supabase.table("variant_values").select("*").in_("variant_axis_id", axis_ids).execute()

        # 4. Group values by axis
        values_by_axis = {}
        for value in values.data:
            axis_id = value["variant_axis_id"]
            if axis_id not in values_by_axis:
                values_by_axis[axis_id] = []
            values_by_axis[axis_id].append(value)

        # 5. Generate combinations
        axis_list = [values_by_axis[ax["id"]] for ax in axes.data]
        combinations = list(cartesian_product(*axis_list))

        # 6. Create Product rows
        created_products = []
        for idx, combo in enumerate(combinations):
            # Build SKU
            sku_parts = [family.data["sku_prefix"]]
            sku_parts.extend([val["sku_code"] for val in combo])
            sku = "-".join(sku_parts)

            # Build name
            variant_labels = [val.get("display_label") or val["value"] for val in combo]
            name = f"{family.data['name']} - {', '.join(variant_labels)}"

            # Create product
            product_data = {
                "product_family_id": str(product_family_id),
                "sku": sku,
                "name": name,
                "price": family.data["base_price"],  # Inherit from family
                "availability": "in_stock",
                "is_primary_variant": idx == 0,  # First variant is primary
            }

            product_result = supabase.table("products").insert(product_data).execute()
            product_id = product_result.data[0]["id"]

            # Link product to variant_values via junction table
            for value in combo:
                supabase.table("product_variant_values").insert({
                    "product_id": product_id,
                    "variant_value_id": value["id"],
                }).execute()

            created_products.append(product_id)

        return {
            "success": True,
            "products_created": len(created_products),
            "product_ids": created_products,
            "message": f"Generated {len(created_products)} product variants from {len(combinations)} combinations",
        }

    except Exception as e:
        raise ToolException(f"Variant generation failed: {str(e)}") from e
```

**Estimated Effort:** 8 hours (combinatorial logic + junction table population)

---

### Phase 3: Marketing Content Generation Specialist (Week 2)

#### 3.1 Platform-Specific Content Generator (Day 6-7)
**File:** `agents/src/autifyme_agents/prompts/marketing_content_specialist.md`

**Objective:** Generate platform-optimized marketing content for each customer segment × industry combination.

**Prompt Structure:**
```xml
<role>
You are the Marketing Content Specialist for PAVISHA PET INDUSTRIES.

Your mission: Generate platform-optimized marketing content that resonates with specific customer segments and industries.
</role>

<context>
Product Family: {{product_family}}
Customer Segment: {{customer_segment}}
Target Industry: {{target_industry}}
Platform: {{platform}}
Content Type: {{content_type}}
</context>

<platform_requirements>
{{platform_guidelines}}
# Example for LinkedIn B2B post:
# - Tone: Professional, ROI-focused
# - Length: 1300 characters max
# - Hashtags: 3-5 industry-specific
# - Call-to-action: "Request a quote" / "Download spec sheet"
# - Content structure: Problem → Solution → Benefit → CTA
</platform_requirements>

<segment_strategy>
{{customer_segment.tone}}
{{customer_segment.key_benefits}}
{{customer_segment.pain_points}}
</segment_strategy>

<industry_customization>
{{industry_use_case}}
{{industry_benefits}}
{{compliance_notes}}
</industry_customization>

<output>
Generate marketing_content with:
- platform: '{{platform}}'
- content_type: '{{content_type}}'
- content_text: [optimized copy]
- content_metadata: {
    hashtags: [...],
    keywords: [...],
    call_to_action: "...",
    image_suggestions: [...],
  }
- meta_title: [SEO-optimized title]
- meta_description: [SEO meta description]
</output>
```

**Estimated Effort:** 6 hours (prompt per platform: LinkedIn, Instagram, Facebook, Website)

---

#### 3.2 Marketing Content Tool (Day 8)
**File:** `agents/src/autifyme_agents/tools/marketing_content_tools.py`

```python
@tool("generate_marketing_content")
def generate_marketing_content(
    product_family_id: UUID,
    platform: Literal["linkedin", "instagram", "facebook", "website", "email"],
    content_type: Literal["post", "ad", "catalog_description"],
    customer_segment_id: UUID | None = None,
    industry_naics_code: str | None = None,
) -> dict[str, Any]:
    """Generate platform-optimized marketing content.

    If customer_segment_id and industry_naics_code provided:
        Generates targeted content for specific segment × industry
    Else:
        Generates generic content using primary segment/industry

    Returns marketing_content record with versioning support.
    """
    # Implementation similar to previous tools
    # Uses marketing_content_specialist prompt
    # Persists to marketing_content table
```

**Estimated Effort:** 6 hours

---

### Phase 4: Integration & Testing (Week 2)

#### 4.1 Product Onboarding Orchestrator (Day 9)
**File:** `agents/src/autifyme_agents/workflows/product_onboarding_orchestrator.py`

**Workflow:**
```
1. User provides product info (text/image/doc)
   ↓
2. product_intelligence_specialist → ProductIntelligenceOutput
   ↓
3. HITL Approval: "Does this look correct?"
   ↓ (if approved)
4. save_product_family → Creates DB records
   ↓
5. generate_product_variants → Creates all SKUs
   ↓
6. For each (segment × industry) combination:
   generate_marketing_content → Platform-specific content
   ↓
7. Return summary with product_family_id, SKU count, content generated
```

**Estimated Effort:** 8 hours (orchestration + HITL integration)

---

#### 4.2 CLI Testing Tool (Day 10)
**File:** `tests/cli/onboard_product.py`

```python
"""
CLI tool for testing product onboarding workflow.

Usage:
    uv run python tests/cli/onboard_product.py --text "500ml PET bottle, food-grade, transparent"
    uv run python tests/cli/onboard_product.py --image "./bottle.jpg"
"""
```

**Estimated Effort:** 4 hours

---

#### 4.3 End-to-End Testing (Day 10)
- Test with PAVISHA product examples (bottles, jars, preforms)
- Validate variant generation (3 capacities × 2 colors = 6 SKUs)
- Verify marketing content for B2B segments
- Check temporal triggers (price history logging)
- Validate audit trail

**Estimated Effort:** 6 hours

---

## Part IV: Success Criteria

### Functional Requirements
- [  ] Product intelligence specialist extracts all required fields
- [  ] Variant generation creates correct SKU combinations
- [  ] Product families persist with all relationships
- [  ] Marketing content generated for primary platforms (LinkedIn, Website)
- [  ] HITL approval flow works end-to-end
- [  ] Temporal triggers log price/inventory changes
- [  ] Audit log captures all modifications

### Data Quality Requirements
- [  ] Confidence score > 0.8 for product intelligence extraction
- [  ] 100% NAICS code mapping accuracy
- [  ] Customer segment benefits align with B2B positioning
- [  ] Marketing content passes platform requirements (char limits, hashtags)

### Performance Requirements
- [  ] Product onboarding completes in < 60 seconds (excluding HITL wait)
- [  ] Variant generation handles 100+ combinations without timeout
- [  ] Database queries use indexes (no sequential scans)

---

## Part V: Risk Mitigation

### Risk 1: Complex Variant Combinations
**Example:** Bottle with 5 capacities × 3 colors × 4 neck finishes = 60 SKUs
**Mitigation:**
- Add `generate_all_combinations` flag (default: False)
- Require explicit user confirmation for >20 variants
- Batch insert products in transactions

### Risk 2: Low Confidence Extraction
**Issue:** LLM cannot extract all required fields from vague input
**Mitigation:**
- Return `missing_fields` list in ProductIntelligenceOutput
- Trigger HITL clarification request
- Provide guided input form for missing data

### Risk 3: Duplicate Product Families
**Issue:** User onboards same product twice
**Mitigation:**
- Check for existing product_group_id before insert
- Fuzzy match on name + sku_prefix
- Prompt user: "Similar product exists. Create variant or new family?"

---

## Part VI: Future Enhancements (Not in Scope)

### Bulk Onboarding
- CSV upload with column mapping
- Batch processing with progress tracking
- Validation rules per column

### Competitive Intelligence
- Auto-scrape competitor pricing
- Market positioning analysis
- Feature gap detection

### Image Generation
- AI-generated lifestyle images
- Product mockups for variants
- Social media templates

---

## Appendix A: Example Product Onboarding

### Input (WhatsApp)
```
User: "I want to add our 500ml transparent PET bottle with 28mm PCO neck finish.
       We offer it in clear and amber colors. Food-grade certified.
       Price: ₹8 per unit for bulk orders (1000+ units)."
```

### Output (Database)

**product_families:**
```json
{
  "id": "uuid-1",
  "product_group_id": "PAV-PET-BOTTLE-500ML",
  "sku_prefix": "PAV-BTL-500",
  "name": "500ml PET Bottle - Food Grade",
  "description": "Food-grade transparent PET bottle with 28mm PCO neck finish. Ideal for beverages, sauces, and condiments. BPA-free, recyclable. Certified to IS:12252 standards. Three-tier QC ensures consistent quality. 24/7 automated production for reliable supply.",
  "brand": "PAVISHA",
  "base_price": 8.00,
  "price_currency": "INR",
  "material": "PET",
  "condition": "new",
  "custom_attributes": {
    "capacity_ml": 500,
    "neck_finish": "28mm PCO",
    "food_grade_certified": true,
    "bpa_free": true,
    "recyclable": true,
    "min_order_quantity": 1000
  }
}
```

**variant_axes:**
```json
[
  {
    "id": "uuid-axis-1",
    "name": "color",
    "display_label": "Color",
    "sort_order": 0
  }
]
```

**variant_values:**
```json
[
  {
    "id": "uuid-val-1",
    "variant_axis_id": "uuid-axis-1",
    "value": "Clear",
    "display_label": "Transparent",
    "sku_code": "CLR",
    "color_hex": "#FFFFFF"
  },
  {
    "id": "uuid-val-2",
    "variant_axis_id": "uuid-axis-1",
    "value": "Amber",
    "display_label": "Amber",
    "sku_code": "AMB",
    "color_hex": "#FFBF00"
  }
]
```

**products (2 SKUs generated):**
```json
[
  {
    "id": "uuid-prod-1",
    "product_family_id": "uuid-1",
    "sku": "PAV-BTL-500-CLR",
    "name": "500ml PET Bottle - Food Grade - Transparent",
    "price": 8.00,
    "availability": "in_stock",
    "is_primary_variant": true
  },
  {
    "id": "uuid-prod-2",
    "product_family_id": "uuid-1",
    "sku": "PAV-BTL-500-AMB",
    "name": "500ml PET Bottle - Food Grade - Amber",
    "price": 8.00,
    "availability": "in_stock",
    "is_primary_variant": false
  }
]
```

**product_variant_values:**
```json
[
  {"product_id": "uuid-prod-1", "variant_value_id": "uuid-val-1"},
  {"product_id": "uuid-prod-2", "variant_value_id": "uuid-val-2"}
]
```

**customer_segments:**
```json
[
  {
    "id": "uuid-seg-1",
    "product_family_id": "uuid-1",
    "segment_type": "b2b",
    "segment_label": "Food & Beverage Manufacturers",
    "tone": "professional",
    "key_benefits": [
      "Reduces packaging costs by 15% vs glass",
      "Lightweight reduces shipping costs",
      "Food-grade certified to IS:12252",
      "Consistent quality via automated production"
    ],
    "pain_points": [
      "High packaging costs",
      "Inconsistent supplier quality",
      "Compliance concerns",
      "Long lead times"
    ],
    "primary_channels": ["linkedin", "email", "trade_shows"],
    "content_formats": ["case_studies", "spec_sheets", "whitepapers"],
    "pricing_notes": "Quote-based for bulk orders (1000+ units). Volume discounts available."
  }
]
```

**product_family_industries:**
```json
[
  {
    "id": "uuid-ind-1",
    "product_family_id": "uuid-1",
    "industry_naics_code": "311",
    "industry_use_case": "Packaging for beverages, sauces, condiments, and liquid food products",
    "industry_benefits": [
      "FSSAI compliant",
      "Tamper-evident options available",
      "Microwave-safe for reheating"
    ],
    "compliance_notes": "Certified to IS:12252 (Food Contact Materials). BPA-free.",
    "is_primary_industry": true
  },
  {
    "id": "uuid-ind-2",
    "product_family_id": "uuid-1",
    "industry_naics_code": "312",
    "industry_use_case": "Beverage bottling (juices, water, soft drinks, alcoholic beverages)",
    "industry_benefits": [
      "Pressure-tested for carbonated drinks",
      "UV-resistant amber option",
      "Lightweight for distribution"
    ],
    "compliance_notes": "Meets beverage industry standards",
    "is_primary_industry": false
  }
]
```

**marketing_content (LinkedIn B2B post):**
```json
{
  "id": "uuid-content-1",
  "product_family_id": "uuid-1",
  "customer_segment_id": "uuid-seg-1",
  "industry_naics_code": "311",
  "platform": "linkedin",
  "content_type": "post",
  "content_text": "🏭 Food & Beverage Manufacturers: Reduce packaging costs by 15% with PAVISHA's 500ml food-grade PET bottles.\n\nOur automated 24/7 production ensures consistent quality and reliable supply for your high-volume needs. IS:12252 certified for food contact safety. BPA-free and recyclable.\n\n✅ Three-tier QC system\n✅ Lightweight (reduces shipping costs)\n✅ Tamper-evident options\n✅ Bulk pricing for 1000+ units\n\nJoin leading food processors who trust PAVISHA for their packaging solutions.\n\n📞 Request a quote today → [link]\n\n#FoodPackaging #PETBottles #ManufacturingExcellence #PackagingSolutions #B2BPackaging",
  "content_metadata": {
    "hashtags": ["#FoodPackaging", "#PETBottles", "#ManufacturingExcellence", "#PackagingSolutions", "#B2BPackaging"],
    "keywords": ["food-grade", "PET bottles", "bulk packaging", "cost reduction", "quality assurance"],
    "call_to_action": "Request a quote",
    "character_count": 612,
    "image_suggestions": ["product_shot_clear_bottle", "manufacturing_facility", "quality_control_lab"]
  },
  "meta_title": "500ml Food-Grade PET Bottles - Bulk Packaging Solutions | PAVISHA",
  "meta_description": "Reduce packaging costs by 15% with PAVISHA's IS:12252 certified food-grade PET bottles. 24/7 automated production. Request a quote for bulk orders.",
  "version": 1,
  "is_active": true,
  "generated_by": "marketing_content_specialist_v1",
  "generation_prompt_version": "linkedin_b2b_v1.2"
}
```

---

**Total Estimated Effort:** 10 days (2 weeks)

**Prerequisites:**
- ✅ Database schema implemented
- ✅ Company data populated
- ✅ NAICS taxonomy seeded
- ✅ Supabase MCP available

**Deliverables:**
1. Updated Pydantic models
2. Product Intelligence Specialist (prompt + tool)
3. Product Persistence Tools (family + variants)
4. Marketing Content Specialist (prompt + tool)
5. Product Onboarding Orchestrator workflow
6. CLI testing tool
7. End-to-end test suite

**Next Phase:** Bulk onboarding via CSV, competitive intelligence scraping, automated image generation.

---

**Last Updated:** 2025-10-23
**Status:** Ready for implementation
**Owner:** Development Team
