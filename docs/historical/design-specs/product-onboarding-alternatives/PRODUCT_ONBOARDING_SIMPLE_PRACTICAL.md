# Product Onboarding - Simple & Practical Architecture

**Date:** 2025-10-23
**Status:** Final - Research-Backed, Production-Ready
**Based On:** Deep research of modern LLM capabilities + real e-commerce flows
**Priority:** Maximum simplicity, minimum HITL points, fast time-to-market

---

## Executive Summary: What Was Wrong with Previous Designs

### Over-Engineering Analysis

**v1.0 + v2.0 Mistakes:**
- ❌ 5 specialists (Product Intelligence, Image Processing, Media Generation, Variant Strategy, Marketing & SEO)
- ❌ 4-5 HITL approval points (user fatigue)
- ❌ Separate "specialists" for logic that doesn't need orchestration
- ❌ Ignored modern LLM capabilities (vision models can do everything in ONE call)
- ❌ Ignored real-world UX (Shopify = ONE page, ONE save button)

**Research Findings:**

1. **Modern Vision LLMs (GPT-4V, Claude 3.5 Sonnet) Can Do:**
   - Image analysis + product extraction + classification + alt text in **ONE API call**
   - Structured output with Pydantic
   - Multiple images (up to 100) in single request
   - Text extraction (OCR built-in)

2. **Real E-Commerce (Shopify 2024):**
   - Single product page with ALL fields
   - AI-assisted attribute suggestions (inline, not separate specialist)
   - Variants managed inline with bulk editing
   - Media in one picker
   - **ONE save button**

3. **Variant Logic Doesn't Need a Specialist:**
   - Parse user input → Map to axes → Calculate combinations → Generate SKUs
   - This is 50 lines of code, not a domain
   - Should be inline in product specialist

4. **Latest Generative AI (2025):**
   - **Imagen 3**: $0.03/image (cheapest), excellent quality, Gemini API
   - **Veo 2**: Video generation from images, 8s @ 720p, Gemini API
   - **DALL-E 3**: $0.04/image, best prompt following
   - **Key insight**: Call these as TOOLS, not separate specialists

---

## Part I: The Correct Architecture (2 Specialists)

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  PROJECT MANAGER AGENT                       │
│  - Intent classification                                     │
│  - Workflow orchestration                                    │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        ▼                                       ▼
┌───────────────────────────────┐   ┌───────────────────────────────┐
│ Product Onboarding            │   │ Marketing Content             │
│ Specialist                    │   │ Generator                     │
│                               │   │ (Optional - Async)            │
│ Does EVERYTHING:              │   │                               │
│ - Image analysis (Vision API) │   │ Does:                         │
│ - Product extraction          │   │ - Platform content            │
│ - Variant logic (inline)      │   │ - AI image/video generation   │
│ - Category mapping            │   │ - SEO optimization            │
│ - SEO fields                  │   │                               │
│ - Image classification        │   │ Tools:                        │
│ - Alt text generation         │   │ - generate_imagen3            │
│                               │   │ - generate_veo2               │
│ Tools:                        │   │ - generate_content            │
│ - multimodal_analysis         │   │                               │
│ - category_mapper             │   │ HITL: Review marketing        │
│ - (optional) generate_images  │   │                               │
│                               │   │                               │
│ HITL: Review product draft    │   │                               │
└───────────────────────────────┘   └───────────────────────────────┘
```

**Total Specialists:** 2
**Total HITL Points:** 1-2 (Product approval + optional marketing approval)

---

## Part II: Specialist 1 - Product Onboarding Specialist (The ONE Specialist That Matters)

### Responsibilities (EVERYTHING)

**Input Processing:**
- Receive user text + multiple images
- Call multimodal_analysis tool (Vision API) → **ONE call for:**
  - Product specifications (dimensions, colors, materials)
  - Image classification (product_shot, lifestyle, detail, etc.)
  - Image angles (front, side, top)
  - Alt text generation (SEO-optimized)
  - Suggested product name
  - Suggested category

**Inline Logic (No Separate Specialists Needed):**
- **Variant Detection**: Parse user input for variant mentions ("clear and amber" → color axis)
- **Variant Structure**: Map to standard axes (capacity, color, size, neck_finish)
- **SKU Calculation**: Simple combinatorics (3 capacities × 2 colors = 6 SKUs)
- **SKU Generation**: String templating (PAV-BTL-500-CLR)
- **Primary Variant**: First combination = primary

**Category & Taxonomy:**
- Call category_mapper tool → matches to existing categories or suggests new path
- Generate google_product_category code
- Generate SEO-friendly URL slug

**Industry & Segment Mapping:**
- Based on product type + company intelligence
- Map to NAICS codes
- Define B2B/B2C segments

**Output (Single Structured Model):**
```python
class ProductOnboardingDraft(BaseModel):
    """Complete product draft - EVERYTHING in one model."""

    # Core product
    product_family: ProductFamily  # With all fields including category_id, google_product_category

    # Variants (if any)
    variant_axes: list[VariantAxis]
    variant_values: list[VariantValue]
    sku_preview: list[str]  # ["PAV-BTL-500-CLR", "PAV-BTL-500-AMB"]
    total_skus: int

    # Images (classified by Vision API in ONE call)
    processed_images: list[ProcessedImage]  # With type, angle, alt_text from Vision API

    # Taxonomy
    category_path: list[str]  # ["Packaging", "PET Products", "Bottles"]
    category_id: UUID | None
    url_slug: str

    # Intelligence
    customer_segments: list[CustomerSegment]
    industries: list[IndustryMapping]

    # Quality
    confidence_score: float
    missing_fields: list[str]
```

### Tools

```python
@tool
def multimodal_analysis(
    image_paths: list[str],
    user_text: str,
    company_context: dict,
) -> MultimodalAnalysisResult:
    """Analyze images and text together using Vision API (GPT-4V or Claude 3.5 Sonnet).

    ONE API CALL RETURNS:
    - Product specifications (extracted from images + text)
    - Image classifications (type: product_shot/lifestyle/detail, angle: front/side/top)
    - Alt text for each image (SEO-optimized)
    - Suggested product name
    - Suggested category
    - Variant hints (if user mentions colors/sizes)

    Uses: GPT-4V or Claude 3.5 Sonnet with structured output (Pydantic)
    """

@tool
def category_mapper(
    product_name: str,
    product_type: str,
    material: str,
    existing_categories: list[Category],
) -> CategoryMapping:
    """Map product to category tree and generate SEO fields.

    Returns:
    - category_id (if match found)
    - category_path (hierarchical)
    - google_product_category
    - url_slug (SEO-friendly)
    """
```

**Optional Tool (if user wants enhanced images):**
```python
@tool
def generate_professional_images(
    reference_image_path: str,
    product_name: str,
    num_variants: int = 5,
) -> list[str]:
    """Generate professional product shots using Imagen 3.

    Generates:
    - White background studio shot
    - Multiple angles (front, side, 45°)

    Uses: Google Imagen 3 ($0.03/image)
    Returns: CDN URLs
    """
```

### HITL Approval Point (ONE Screen)

**What User Reviews:**
```
📦 Product: 500ml PET Bottle - Food Grade
💰 Price: ₹12.00 (base price)
📂 Category: Packaging > PET Products > Bottles > Food-Grade
🔗 URL: /products/500ml-pet-bottle-food-grade

🏷️ Variants (2 SKUs):
  ✓ Clear (PAV-BTL-500-CLR) - ₹12.00
  ✓ Amber (PAV-BTL-500-AMB) - ₹12.00

🖼️ Images (2 provided + classifications):
  [image] Product shot - front view
    Alt: "500ml clear PET food-grade bottle with 28mm PCO neck, front view"

  [image] Product shot - side view
    Alt: "500ml PET bottle side profile showing capacity markings and certifications"

🏢 Industries:
  ✓ Food Manufacturing (NAICS 311)
  ✓ Beverage Manufacturing (NAICS 312)

👥 Customer Segments:
  ✓ B2B - Food & Beverage Manufacturers

📋 Tags: food-grade, bpa-free, recyclable, 28mm-pco

───────────────────────────────────────
✅ Approve & Save
✏️ Edit Details
❌ Cancel
```

**User Actions:**
- **Approve**: Save to database (atomic transaction)
- **Edit**: Modify any field inline (name, price, variants, tags)
- **Cancel**: Discard draft

**That's it. ONE approval screen. All decisions together. Just like Shopify.**

---

## Part III: Specialist 2 - Marketing Content Generator (Optional, Async)

### When This Runs

**Option A (Async):**
- Runs AFTER product is saved
- User doesn't wait
- Results appear in marketing dashboard later

**Option B (Synchronous):**
- Only if user explicitly requests: "Also generate marketing content"
- Adds 30-60 seconds to workflow

### Responsibilities

**Platform Content Generation:**
- LinkedIn, Instagram, Website content (text only)
- Leverage saved product data + images

**AI Media Generation (Optional Enhancement):**
- Generate professional product shots (Imagen 3: $0.03/image)
- Generate product videos (Veo 2: ~$0.50/video)
- Generate marketing graphics (template-based or Imagen 3)

### Tools

```python
@tool
def generate_imagen3_product_shot(
    reference_image_url: str,
    product_name: str,
    style: Literal["white_background", "studio", "floating"] = "white_background",
) -> str:
    """Generate professional product photo using Google Imagen 3.

    Cost: $0.03 per image
    Quality: Photorealistic, 1024x1024
    Features: Text rendering, SynthID watermarking

    Returns: CDN URL
    """

@tool
def generate_veo2_product_video(
    product_image_url: str,
    motion_description: str,
    duration_seconds: int = 8,
) -> str:
    """Generate product showcase video using Google Veo 2.

    Features:
    - Image-to-video (animate product shot)
    - 8 seconds @ 720p
    - Realistic physics

    Example motion: "Smooth 360° rotation with zoom-in on certification label"

    Returns: CDN URL to video
    """

@tool
def generate_platform_content(
    product: Product,
    platform: Literal["linkedin", "instagram", "website"],
    customer_segment: CustomerSegment,
) -> MarketingContent:
    """Generate platform-specific marketing content.

    Uses: LLM with platform guidelines prompt
    Returns: MarketingContent with copy, metadata, SEO fields
    """
```

### HITL Approval (Optional)

If synchronous, user reviews generated content:
```
📢 Marketing Content Generated

LinkedIn Post (B2B):
  [generated text preview]

Instagram Post:
  [generated text preview]

Website SEO:
  Title: "500ml PET Bottle - Food Grade | PAVISHA"
  Meta: "Buy food-grade 500ml PET bottles..."

🎨 Enhanced Media (Optional):
  [ ] Generate professional product shots (5 images @ $0.15)
  [ ] Generate product video (1 video @ $0.50)

───────────────────────────────────────
✅ Approve & Publish
✏️ Edit Content
⏭️ Skip Marketing (Save Product Only)
```

---

## Part IV: Complete Workflow (Simple)

### User Journey

```
User (WhatsApp): "Add 500ml bottle, clear/amber, ₹12" + 2 images
   ↓
PM Routes to: Product Onboarding Specialist
   ↓
Specialist calls multimodal_analysis tool:
   - GPT-4V analyzes 2 images + text in ONE call
   - Extracts specs, classifies images, generates alt text
   - Returns complete analysis (~5 seconds)
   ↓
Specialist inline logic:
   - Detects variants: "clear/amber" → color axis
   - Calculates: 2 SKUs
   - Generates: PAV-BTL-500-CLR, PAV-BTL-500-AMB
   - Maps category via category_mapper tool
   - Generates SEO slug
   ↓
Specialist returns: ProductOnboardingDraft (complete)
   ↓
HITL: User reviews ONE screen (~30 seconds)
   - Sees product, variants, images, taxonomy, all together
   - Approves with one button
   ↓
PM persists to database (atomic transaction):
   - product_families
   - variant_axes, variant_values
   - products (2 SKUs)
   - product_variant_values
   - customer_segments
   - product_family_industries
   - product_images (with classifications, alt text)
   (~2 seconds)
   ↓
Optional (Async): Marketing Content Generator runs
   - Generates platform content
   - Optionally generates enhanced images/videos
   - User reviews later in dashboard
   ↓
Done! Total user time: ~40 seconds (excluding HITL wait)
```

---

## Part V: Database Persistence (Atomic Transaction)

```python
@tool
def save_product_onboarding_draft(
    draft: ProductOnboardingDraft
) -> PersistenceResult:
    """Save complete product with all relationships.

    Atomic transaction (all or nothing):
    1. product_families
    2. variant_axes, variant_values (if variants exist)
    3. products (all SKUs)
    4. product_variant_values (junction)
    5. customer_segments
    6. product_family_industries
    7. product_images (with type, angle, alt_text from Vision API)
    8. Initial history records (price, inventory)

    Returns: All created IDs
    """

    try:
        supabase = get_storage()

        with supabase.transaction():
            # Insert all tables atomically
            # (Same logic as before, just one tool call)

            return PersistenceResult(
                success=True,
                product_family_id=family_id,
                product_ids=product_ids,
                message=f"Created {len(product_ids)} SKUs successfully"
            )

    except Exception as e:
        # Rollback automatic
        raise ToolException(f"Persistence failed: {str(e)}") from e
```

---

## Part VI: Cost Analysis (Real Numbers)

### Per Product Costs

**Vision Analysis:**
- GPT-4V: $0.01 per image × 2 images = $0.02
- OR Claude 3.5 Sonnet: Similar pricing

**AI Image Generation (Optional):**
- Imagen 3: $0.03 per image
- 5 professional product shots = $0.15

**AI Video Generation (Optional):**
- Veo 2: ~$0.50 per 8-second video

**Total per Product:**
- Base (no AI generation): $0.02
- With images: $0.17
- With images + video: $0.67

**100 Products:**
- Base: $2
- With images: $17
- With images + video: $67

**vs Professional Photography:**
- Single product photoshoot: ₹5k-20k ($60-$240)
- 100 products: ₹5L-20L ($6,000-$24,000)
- **Savings: 99.7% cost reduction**

---

## Part VII: Why This Is The Right Architecture

### 1. Aligns with Modern LLM Capabilities

**Vision models can do EVERYTHING in one call:**
- Product extraction
- Image classification
- Alt text generation
- Category suggestions

**No need to split into multiple specialists.**

### 2. Matches Real E-Commerce UX

**Shopify approach:**
- Single product page
- All fields together
- One save button
- AI assists inline (not separate stages)

**Our approach mirrors this.**

### 3. Minimizes User Friction

**1 HITL point vs 5 HITL points:**
- User reviews everything together
- Single decision moment
- No workflow fatigue

### 4. Reduces System Complexity

**2 specialists vs 5 specialists:**
- Fewer coordination points
- Fewer prompts to maintain
- Faster debugging
- Less can go wrong

### 5. Variant Logic Is Just Logic

**Why no Variant Strategy Specialist:**
- Parse input → Map to axes → Calculate combinations
- This is 50 lines of code, not a domain
- Inline in Product Onboarding Specialist is correct

### 6. Latest Generative AI as Tools

**Imagen 3, Veo 2 are TOOLS:**
- Marketing Specialist calls them when needed
- No separate Media Generation Specialist needed
- Tools are reusable across specialists

---

## Part VIII: Implementation Phases

### Week 1: Product Onboarding Specialist (Core)

**Days 1-3: Multimodal Analysis Tool**
- Integrate GPT-4V or Claude 3.5 Sonnet
- Structured output with Pydantic
- Test with PAVISHA bottle images

**Days 4-5: Inline Variant Logic**
- Variant detection from user input
- SKU generation
- Combination calculation

**Days 6-7: Category Mapping & SEO**
- Category mapper tool
- URL slug generation
- Google Product Category assignment

### Week 2: Database Persistence & Testing

**Days 8-10: Atomic Persistence**
- Complete transaction logic
- Error handling
- Rollback testing

**Days 11-14: End-to-End Testing**
- Autonomous testing framework
- HITL simulation
- WhatsApp integration

### Week 3: Marketing Content Generator (Optional)

**Days 15-17: Platform Content**
- LinkedIn, Instagram, Website content
- SEO optimization

**Days 18-21: AI Media Generation (Optional)**
- Imagen 3 integration
- Veo 2 integration (if available)
- Template-based graphics

---

## Part IX: Success Metrics

### Product Onboarding Quality

| Metric | Target |
|--------|--------|
| Confidence Score | > 0.8 |
| Category Mapping Accuracy | > 90% |
| Variant Detection Accuracy | > 85% |
| Alt Text Quality | > 90% |
| User Approval Rate (First Time) | > 80% |
| Time to Complete (excluding HITL) | < 30 seconds |

### User Experience

| Metric | Target |
|--------|--------|
| HITL Approval Points | 1-2 max |
| User Edit Rate | < 20% |
| User Abandonment Rate | < 5% |
| User Satisfaction | > 4.5/5 |

---

## Part X: What We're NOT Building (And Why)

### ❌ Image Processing Specialist
**Why:** Vision API does everything in ONE call. No orchestration needed.

### ❌ Variant Strategy Specialist
**Why:** It's 50 lines of logic, not a domain. Inline is correct.

### ❌ Media Generation Specialist
**Why:** Tools (Imagen 3, Veo 2) are called by Marketing Specialist. No separate specialist needed.

### ❌ SEO Optimization Specialist
**Why:** SEO fields (slug, meta tags) generated inline. Schema.org can be template-based.

### ❌ 5 HITL Approval Points
**Why:** User fatigue. Shopify has ONE save button. We should too.

---

## Appendix: Prompt Example (Product Onboarding Specialist)

```xml
<role>
You are the Product Onboarding Specialist for PAVISHA PET INDUSTRIES.

Your mission: Transform user input (text + images) into a complete, database-ready product structure.
</role>

<capabilities>
You have access to tools:
- multimodal_analysis: Analyzes images and text together (Vision API)
- category_mapper: Maps product to taxonomy
- (optional) generate_professional_images: Enhances images with AI

You have inline logic for:
- Variant detection and SKU generation
- SEO field generation (slug, meta)
- Industry and segment mapping
</capabilities>

<workflow>
1. Call multimodal_analysis with all images + user text
   → Receive complete analysis (specs, classifications, alt text)

2. Detect variants inline:
   - Parse user input for variant mentions
   - Map to standard axes (capacity, color, size, neck_finish)
   - Calculate SKU combinations
   - Warn if > 20 SKUs

3. Call category_mapper to assign taxonomy
   → Receive category_id, google_product_category, url_slug

4. Map industries and segments based on product type + company intelligence

5. Return ProductOnboardingDraft with EVERYTHING
</workflow>

<output>
Return ProductOnboardingDraft with:
- product_family (complete with all fields)
- variant_axes, variant_values (if variants detected)
- processed_images (with classifications from Vision API)
- category_path, category_id, google_product_category
- url_slug
- customer_segments
- industries
- confidence_score, missing_fields
</output>

<constraints>
- If confidence < 0.7, request missing fields from user
- If SKU combinations > 20, warn user and request confirmation
- Always generate SEO-friendly URL slugs (lowercase, hyphens)
- Always include food_grade_certified in custom_attributes for food-contact products
</constraints>
```

---

**Last Updated:** 2025-10-23
**Status:** Final - Ready for Implementation
**Research Sources:** GPT-4V capabilities, Claude 3.5 Sonnet vision, Shopify 2024 UX, Imagen 3, Veo 2
**Next Step:** Begin Week 1 - Product Onboarding Specialist implementation
