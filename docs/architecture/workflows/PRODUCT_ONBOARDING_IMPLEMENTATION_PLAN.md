# Product Onboarding - Implementation Plan

**Date:** 2025-10-23
**Status:** Ready for Implementation
**Based On:** WORKFLOW_DESIGN_STRATEGY.md principles
**Priority:** Product Intelligence + Visual Content specialists

---

## Executive Summary

**Goal:** Enable PAVISHA to onboard products via WhatsApp (text + images) → Complete product in database with professional images

**Approach:** 2 domain specialists + 1 HITL point

**Design Validation (per WORKFLOW_DESIGN_STRATEGY.md):**
- ✅ Domain-based (not workflow-specific)
- ✅ Reusable across multiple workflows
- ✅ LLM factory pattern
- ✅ Minimal HITL (1 point)
- ✅ Latest AI models (Nano Banana FREE, Veo 3.1, Imagen 3)

---

## Part I: Architecture

### Specialists

```
┌─────────────────────────────────────────────────────────────┐
│                  PROJECT MANAGER AGENT                       │
│  Orchestrates: Product Intelligence → Visual Content        │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        ▼                                       ▼
┌───────────────────────────────┐   ┌───────────────────────────────┐
│ Product Intelligence          │   │ Visual Content                │
│ Specialist                    │   │ Specialist                    │
│                               │   │                               │
│ Domain: Product Understanding │   │ Domain: Visual Assets         │
│                               │   │                               │
│ Does:                         │   │ Does:                         │
│ • Vision analysis (multimodal)│   │ • Enhance (Nano Banana FREE)  │
│ • Spec extraction             │   │ • Generate (Imagen 3 $0.03)   │
│ • Category mapping            │   │ • Video (Veo 3.1 $0.15/sec)   │
│ • Variant detection (inline)  │   │ • Consistency management      │
│ • SEO generation (inline)     │   │ • Quality decisions           │
│ • Image classification        │   │                               │
│                               │   │ Tools:                        │
│ Tools:                        │   │ • enhance_nano_banana         │
│ • multimodal_analysis         │   │ • generate_imagen3            │
│ • category_mapper             │   │ • generate_veo31              │
│                               │   │ • create_graphic              │
│ Output:                       │   │                               │
│ ProductDraft (structured)     │   │ Output:                       │
│                               │   │ VisualAssets (CDN URLs)       │
└───────────────────────────────┘   └───────────────────────────────┘
```

### Workflow Flow

```
User (WhatsApp): "Add 500ml bottle, clear/amber, ₹12" + 2 images
   ↓
PM classifies intent: Product onboarding
   ↓
PM → Product Intelligence Specialist
   Input: {text, images, company_context}
   ↓
   Product Intelligence calls multimodal_analysis tool
   → Vision API analyzes 2 images + text in ONE call
   → Extracts: specs, suggests categories, detects variants
   ↓
   Product Intelligence inline logic:
   → Variant detection: "clear/amber" → color axis → 2 SKUs
   → Category mapping: Calls category_mapper tool
   → SEO generation: URL slug, meta tags (inline)
   → Image classification: type, angle (from Vision API)
   ↓
   Returns: ProductDraft {
     product_family: {...},
     variant_axes: [{name: "color", ...}],
     variant_values: [{value: "Clear"}, {value: "Amber"}],
     sku_preview: ["PAV-BTL-500-CLR", "PAV-BTL-500-AMB"],
     images_metadata: [{type: "product_shot", angle: "front", ...}],
     category_id: UUID,
     url_slug: "500ml-pet-bottle-food-grade",
     confidence_score: 0.92,
   }
   ↓
PM → Visual Content Specialist
   Input: {product_draft, raw_images}
   ↓
   Visual Content analyzes quality:
   → Image 1: Quality 6/10 → Decision: Enhance with Nano Banana
   → Image 2: Quality 4/10 → Decision: Regenerate with Imagen 3
   ↓
   Visual Content calls tools:
   → enhance_nano_banana(image1) → CDN URL (FREE!)
   → generate_imagen3({
       reference: image2,
       prompt: "500ml PET bottle, white background, professional",
       angles: ["front", "side", "top"],
     }) → 3 CDN URLs ($0.09)
   ↓
   Visual Content ensures consistency:
   → Check existing PAVISHA products
   → Match style (white background, centered, soft shadows)
   ↓
   Returns: VisualAssets {
     enhanced_images: [CDN_URL_1],
     generated_images: [CDN_URL_2, CDN_URL_3, CDN_URL_4],
     primary_image_url: CDN_URL_2,
     total_cost: $0.09,
   }
   ↓
PM combines outputs
   ↓
───────────────────────────────────────────────────────
HITL: User reviews ONE screen
───────────────────────────────────────────────────────

📦 Product: 500ml PET Bottle - Food Grade
💰 Price: ₹12.00 (base price)
📂 Category: Packaging > PET Products > Bottles
🔗 URL: /products/500ml-pet-bottle-food-grade

🏷️ Variants (2 SKUs):
  ✓ Clear (PAV-BTL-500-CLR) - ₹12.00
  ✓ Amber (PAV-BTL-500-AMB) - ₹12.00

🖼️ Images (4 professional images):
  [CDN_URL_2] ⭐ Primary - Front view (white bg)
  [CDN_URL_1] Enhanced original - Side view
  [CDN_URL_3] Generated - Top view
  [CDN_URL_4] Generated - 45° angle

💵 Image generation cost: ₹7.50 ($0.09)

───────────────────────────────────────────────────────
✅ Approve & Save  ✏️ Edit Details  ❌ Cancel
───────────────────────────────────────────────────────
   ↓
User: ✅ Approve
   ↓
PM → Persistence Tool
   Atomic transaction:
   1. product_families
   2. variant_axes, variant_values
   3. products (2 SKUs)
   4. product_variant_values
   5. customer_segments (B2B inferred)
   6. product_family_industries (Food=311, Beverage=312)
   7. product_images (4 images with metadata)
   8. Initial history records
   ↓
Success: Product saved with 2 SKUs and 4 professional images
```

---

## Part II: Implementation Phases

### Phase 1: Foundation (Week 1)

**Goal:** LLM factory + Core tools

#### Day 1-2: LLM Factory

**File:** `agents/src/autifyme_agents/core/llm_factory.py`

```python
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

class LLMFactory:
    """Centralized LLM instantiation - no hardcoded models."""

    @staticmethod
    def get_llm(
        provider: Literal["openai", "anthropic", "google"],
        model: str,
        temperature: float = 0,
        **kwargs
    ) -> BaseChatModel:
        """Get LLM instance from configuration.

        Examples:
        - get_llm("openai", "gpt-4o", temperature=0)
        - get_llm("anthropic", "claude-3-5-sonnet-20241022", temperature=0.7)
        - get_llm("google", "gemini-2.0-flash-exp", temperature=0)
        """

        if provider == "openai":
            return ChatOpenAI(model=model, temperature=temperature, **kwargs)
        elif provider == "anthropic":
            return ChatAnthropic(model=model, temperature=temperature, **kwargs)
        elif provider == "google":
            return ChatGoogleGenerativeAI(model=model, temperature=temperature, **kwargs)
        else:
            raise ValueError(f"Unknown provider: {provider}")

# Usage in specialists
llm = LLMFactory.get_llm("openai", "gpt-4o", temperature=0)
specialist = ProductIntelligenceSpecialist(llm=llm)
```

**Testing:**
- Verify all 3 providers work
- Test model switching
- Validate temperature control

---

#### Day 3-4: Core Tools

**File:** `agents/src/autifyme_agents/tools/vision_tools.py`

```python
@tool
def multimodal_analysis(
    image_paths: list[str],
    user_text: str,
    company_context: dict,
) -> MultimodalAnalysisResult:
    """Analyze images and text together using Vision API.

    ONE API CALL returns:
    - Product specifications (name, price, dimensions, materials, etc.)
    - Image classifications (type: product_shot/lifestyle, angle: front/side/top)
    - Alt text for each image (SEO-optimized, <125 chars)
    - Suggested category
    - Variant hints ("clear and amber" detected)

    Uses: GPT-4V or Claude 3.5 Sonnet (configured via LLM factory)
    """

    llm = LLMFactory.get_llm("openai", "gpt-4o", temperature=0)
    structured_llm = llm.with_structured_output(MultimodalAnalysisResult)

    # Build multimodal messages
    messages = [
        ("system", MULTIMODAL_ANALYSIS_PROMPT),
        ("human", [
            {"type": "text", "text": f"User input: {user_text}\n\nCompany: {company_context}"},
            *[{"type": "image_url", "image_url": encode_image(path)} for path in image_paths],
        ]),
    ]

    result = structured_llm.invoke(messages)
    return result
```

**File:** `agents/src/autifyme_agents/tools/category_tools.py`

```python
@tool
def category_mapper(
    product_name: str,
    product_type: str,
    material: str,
    existing_categories: list[Category],
) -> CategoryMapping:
    """Map product to category tree and generate SEO fields.

    Returns:
    - category_id (if match found in existing categories)
    - category_path (hierarchical breadcrumb)
    - google_product_category (Google taxonomy code)
    - url_slug (SEO-friendly slug)
    """
```

**Testing:**
- Test with PAVISHA bottle images
- Validate structured output
- Verify confidence scoring

---

### Phase 2: Product Intelligence Specialist (Week 1-2)

**Goal:** Complete product understanding domain

#### Day 5-7: Specialist Implementation

**File:** `agents/src/autifyme_agents/specialists/product_intelligence_specialist.py`

```python
class ProductIntelligenceSpecialist:
    """Domain: Product Understanding

    Reusable across:
    - Product onboarding
    - Product updates
    - Competitive analysis
    - Inventory audits
    """

    def __init__(self, llm: BaseChatModel, storage: StorageInterface):
        self.llm = llm
        self.storage = storage
        self.tools = [
            multimodal_analysis,
            category_mapper,
        ]

    async def process(
        self,
        user_text: str,
        image_paths: list[str],
        company_context: dict,
    ) -> ProductDraft:
        """Transform user input into database-ready product structure."""

        # Step 1: Multimodal analysis
        analysis = await self._call_tool(
            "multimodal_analysis",
            image_paths=image_paths,
            user_text=user_text,
            company_context=company_context,
        )

        # Step 2: Inline variant detection
        variant_structure = self._detect_variants(analysis, user_text)

        # Step 3: Category mapping
        category_info = await self._call_tool(
            "category_mapper",
            product_name=analysis.product_name,
            product_type=analysis.product_type,
            material=analysis.material,
            existing_categories=self.storage.get_categories(),
        )

        # Step 4: Inline SEO generation
        seo_fields = self._generate_seo_fields(
            analysis.product_name,
            analysis.product_description,
            category_info.category_path,
        )

        # Step 5: Assemble ProductDraft
        return ProductDraft(
            product_family=self._build_product_family(analysis, category_info, seo_fields),
            variant_axes=variant_structure.axes,
            variant_values=variant_structure.values,
            sku_preview=variant_structure.sku_preview,
            images_metadata=analysis.images_metadata,
            category_id=category_info.category_id,
            url_slug=seo_fields.url_slug,
            confidence_score=analysis.confidence_score,
            missing_fields=analysis.missing_fields,
        )

    def _detect_variants(self, analysis, user_text) -> VariantStructure:
        """Inline variant detection logic (not a separate specialist)."""
        # Parse user text for variant mentions
        # "clear and amber" → color axis with 2 values
        # Calculate combinations
        # Generate SKU preview
        pass

    def _generate_seo_fields(self, name, description, category_path) -> SEOFields:
        """Inline SEO generation (not a separate specialist)."""
        # URL slug: lowercase, hyphens, unique
        # Meta title: <60 chars
        # Meta description: <155 chars
        pass
```

**Prompt:** `agents/src/autifyme_agents/prompts/product_intelligence_specialist.md`

```xml
<role>
You are the Product Intelligence Specialist for PAVISHA PET INDUSTRIES.

Domain: Understanding products (specifications, categories, attributes).
</role>

<capabilities>
Tools available:
- multimodal_analysis: Analyze images and text together (Vision API)
- category_mapper: Map products to taxonomy

Inline logic:
- Variant detection from user input
- SEO field generation
- SKU calculations
</capabilities>

<workflow>
1. Call multimodal_analysis with all images + user text
2. Detect variants inline (parse user mentions)
3. Call category_mapper for taxonomy
4. Generate SEO fields inline
5. Return ProductDraft (complete, structured)
</workflow>

<output>
ProductDraft with:
- product_family (all fields including category, pricing, tags)
- variant_axes, variant_values (if detected)
- sku_preview (list of SKU strings)
- images_metadata (classifications from Vision API)
- seo_fields (url_slug, meta_title, meta_description)
- confidence_score, missing_fields
</output>
```

**Testing:**
- Test with 5 PAVISHA products
- Validate variant detection accuracy
- Verify SEO field quality
- Test confidence scoring

---

### Phase 3: Visual Content Specialist (Week 2)

**Goal:** Professional visual assets generation

#### Day 8-10: Visual Tools

**File:** `agents/src/autifyme_agents/tools/visual_tools.py`

```python
@tool
def enhance_nano_banana(
    image_path: str,
    enhancement_instructions: str,
) -> str:
    """Enhance image using Nano Banana (Gemini 2.5 Flash Image).

    Examples:
    - "Remove background, make white studio background"
    - "Improve lighting, enhance colors, make professional"
    - "Fix color balance and increase sharpness"

    Cost: FREE (Gemini free tier)
    Quality: #1 ranked image editing model

    Returns: CDN URL to enhanced image
    """

    # Use Google Gemini API (Nano Banana)
    # Upload image, apply enhancements
    # Download result, upload to Supabase Storage
    # Return CDN URL

@tool
def generate_imagen3_product_shot(
    reference_image_url: str,
    product_name: str,
    material: str,
    style: Literal["white_background", "studio", "floating"] = "white_background",
    angle: Literal["front", "side", "top", "45_degree"] = "front",
) -> str:
    """Generate professional product photo using Google Imagen 3.

    Prompt template:
    "Professional product photography of a {product_name}, made of {material},
     {angle} view, on a {style} background, studio lighting, high resolution,
     commercial quality, sharp focus, 8K"

    Cost: $0.03 per image
    Returns: CDN URL
    """

    # Call Google Imagen 3 API
    # Download generated image
    # Upload to Supabase Storage
    # Return CDN URL

@tool
def generate_veo31_video(
    product_image_url: str,
    scene_description: str,
    duration_seconds: int = 30,
    include_audio: bool = True,
) -> str:
    """Generate product video using Google Veo 3.1.

    Features:
    - Up to 60 seconds @ 1080p
    - Native audio (ambient sounds, narration)
    - Image-to-video animation

    Cost: $4.50 (Fast, 30s) or $12 (Standard, 30s)
    Returns: CDN URL to video
    """
```

**Testing:**
- Test Nano Banana enhancement (FREE!)
- Test Imagen 3 generation ($0.03)
- Test Veo 3.1 video ($4.50)
- Validate CDN uploads

---

#### Day 11-13: Visual Content Specialist

**File:** `agents/src/autifyme_agents/specialists/visual_content_specialist.py`

```python
class VisualContentSpecialist:
    """Domain: Visual Assets (images, videos, graphics)

    Reusable across:
    - Product onboarding
    - Marketing campaigns
    - Catalog generation
    - Social media posts
    - Ad creatives
    """

    def __init__(self, llm: BaseChatModel, storage: StorageInterface):
        self.llm = llm
        self.storage = storage
        self.tools = [
            enhance_nano_banana,
            generate_imagen3_product_shot,
            generate_veo31_video,
        ]

    async def generate(
        self,
        product_draft: ProductDraft,
        raw_images: list[str],
        options: dict,
    ) -> VisualAssets:
        """Generate professional visual assets."""

        # Step 1: Analyze quality of raw images
        quality_scores = await self._analyze_quality(raw_images)

        # Step 2: Decision making
        decisions = []
        for img, score in zip(raw_images, quality_scores):
            if score > 7:
                decision = "use_as_is"
            elif score > 4:
                decision = "enhance_nano_banana"  # FREE!
            else:
                decision = "regenerate_imagen3"  # $0.03

            decisions.append({"image": img, "score": score, "action": decision})

        # Step 3: Execute enhancements/generation
        enhanced_images = []
        generated_images = []
        total_cost = Decimal("0.00")

        for decision in decisions:
            if decision["action"] == "use_as_is":
                cdn_url = await self._upload_to_cdn(decision["image"])
                enhanced_images.append(cdn_url)

            elif decision["action"] == "enhance_nano_banana":
                cdn_url = await self._call_tool(
                    "enhance_nano_banana",
                    image_path=decision["image"],
                    enhancement_instructions="Professional product photo quality",
                )
                enhanced_images.append(cdn_url)
                # Cost: FREE!

            elif decision["action"] == "regenerate_imagen3":
                # Generate multiple angles
                for angle in ["front", "side", "top"]:
                    cdn_url = await self._call_tool(
                        "generate_imagen3_product_shot",
                        reference_image_url=decision["image"],
                        product_name=product_draft.product_family.name,
                        material=product_draft.product_family.material,
                        angle=angle,
                    )
                    generated_images.append(cdn_url)
                    total_cost += Decimal("0.03")

        # Step 4: Consistency check
        if len(self.storage.get_products()) > 0:
            # Match style of existing products
            await self._ensure_consistency(enhanced_images + generated_images)

        # Step 5: Select primary image
        primary_image = self._select_primary(enhanced_images + generated_images)

        return VisualAssets(
            enhanced_images=enhanced_images,
            generated_images=generated_images,
            primary_image_url=primary_image,
            total_cost=total_cost,
        )
```

**Prompt:** `agents/src/autifyme_agents/prompts/visual_content_specialist.md`

```xml
<role>
You are the Visual Content Specialist for PAVISHA PET INDUSTRIES.

Domain: Professional visual assets (images, videos, graphics).
</role>

<capabilities>
Tools available:
- enhance_nano_banana: FREE image enhancement (Google Gemini)
- generate_imagen3_product_shot: Generate professional photos ($0.03/image)
- generate_veo31_video: Generate product videos ($4.50-24/video)

Decision making:
- Analyze image quality (1-10 score)
- Choose enhancement vs regeneration strategy
- Ensure consistency across product family
- Select primary image
</capabilities>

<decision_framework>
Image quality score:
- 8-10: Use as-is (upload to CDN)
- 5-7: Enhance with Nano Banana (FREE!)
- 1-4: Regenerate with Imagen 3 ($0.03)

Style consistency:
- If >10 products exist, match existing style
- If first product, establish style baseline
</decision_framework>

<output>
VisualAssets with:
- enhanced_images (CDN URLs)
- generated_images (CDN URLs)
- primary_image_url (hero image)
- total_cost (transparency for user)
</output>
```

**Testing:**
- Test quality scoring logic
- Test decision tree (enhance vs regenerate)
- Test consistency matching
- Validate cost calculations

---

### Phase 4: PM Orchestration (Week 3)

**Goal:** Wire specialists together

#### Day 14-16: Workflow Orchestrator

**File:** `agents/src/autifyme_agents/workflows/product_onboarding_workflow.py`

```python
async def product_onboarding_workflow(
    user_text: str,
    image_paths: list[str],
    company_profile: CompanyProfile,
    company_intelligence: CompanyIntelligence,
) -> ProductOnboardingResult:
    """Complete product onboarding workflow.

    Orchestrates: Product Intelligence → Visual Content → Persistence
    """

    # Phase 1: Product Intelligence
    product_draft = await pm.delegate_to(
        specialist="product_intelligence",
        input={
            "user_text": user_text,
            "image_paths": image_paths,
            "company_context": {
                "profile": company_profile.model_dump(),
                "intelligence": company_intelligence.model_dump(),
            },
        },
    )

    # Phase 2: Visual Content
    visual_assets = await pm.delegate_to(
        specialist="visual_content",
        input={
            "product_draft": product_draft,
            "raw_images": image_paths,
            "options": {"generate_videos": False},  # Optional
        },
    )

    # Phase 3: HITL (1 approval point)
    approval = await pm.hitl_approve(
        screen="product_review",
        data={
            "product_draft": product_draft,
            "visual_assets": visual_assets,
        },
    )

    if not approval.approved:
        if approval.action == "edit":
            # Apply user edits
            product_draft = apply_edits(product_draft, approval.edits)
        elif approval.action == "cancel":
            return ProductOnboardingResult(success=False, message="Cancelled by user")

    # Phase 4: Atomic Persistence
    result = await pm.call_tool(
        tool="save_complete_product",
        args={
            "product_draft": product_draft,
            "visual_assets": visual_assets,
        },
    )

    return ProductOnboardingResult(
        success=True,
        product_family_id=result.product_family_id,
        sku_count=len(result.product_ids),
        image_count=len(visual_assets.enhanced_images + visual_assets.generated_images),
        total_cost=visual_assets.total_cost,
        message=f"Product onboarded: {product_draft.product_family.name}",
    )
```

**Testing:**
- End-to-end test with PAVISHA bottle
- Test HITL approval flow
- Test edit/cancel paths
- Validate atomic persistence

---

#### Day 17-21: Integration & Testing

**WhatsApp Integration:**
- Update webhook to route to product_onboarding_workflow
- Test HITL via WhatsApp messages
- Validate media handling

**Autonomous Testing:**
```python
from tests.tools import execute_scenario

result = execute_scenario(
    "Catalog 500ml bottle, clear and amber colors, Rs 12",
    images=["bottle_front.jpg", "bottle_side.jpg"],
    hitl_mode="auto_approve",
)

assert result.success
assert result.sku_count == 2
assert result.image_count >= 2
```

---

## Part III: Success Metrics

### Product Intelligence Quality

| Metric | Target | Measurement |
|--------|--------|-------------|
| Confidence Score | > 0.8 | Average across products |
| Variant Detection Accuracy | > 90% | Manual validation |
| Category Mapping Accuracy | > 90% | Manual validation |
| SEO Slug Quality | 100% | Uniqueness + format validation |

### Visual Content Quality

| Metric | Target | Measurement |
|--------|--------|-------------|
| Image Quality Score | > 7/10 | Average after processing |
| Cost per Product | < $0.20 | Average (mostly Nano Banana FREE) |
| User Approval Rate | > 85% | % approved without edits |
| Consistency Score | > 90% | Style matching across products |

### Workflow Performance

| Metric | Target | Measurement |
|--------|--------|-------------|
| Total Time (excluding HITL) | < 60 seconds | Product Intelligence + Visual Content |
| HITL Edit Rate | < 20% | % of products user edits before approval |
| Persistence Success Rate | > 99% | Atomic transaction success |
| User Satisfaction | > 4.5/5 | Post-workflow survey |

---

## Part IV: Cost Analysis

### Per Product (100 products)

**Minimal Path (Enhance only):**
- Vision analysis (GPT-4V): $0.02
- Nano Banana enhancement: $0.00 (FREE!)
- **Total: $2 for 100 products**

**Standard Path (Enhance + Generate):**
- Vision analysis: $0.02
- Nano Banana enhancement: $0.00 (FREE!)
- Imagen 3 (3 new angles): $0.09
- **Total: $11 for 100 products**

**Premium Path (with Video):**
- Vision analysis: $0.02
- Nano Banana enhancement: $0.00
- Imagen 3 (3 angles): $0.09
- Veo 3.1 video (30s): $4.50
- **Total: $461 for 100 products**

**vs Professional Photography:**
- ₹5L-20L ($6,000-$24,000) for 100 products
- **Savings: 99.8% (minimal) to 98% (with video)**

---

## Part V: Future Enhancements (Post-MVP)

### Marketing Content Specialist (Separate Workflow)
- Not part of onboarding
- Separate trigger: "Generate marketing for product X"
- Reuses Visual Content Specialist outputs

### Bulk Operations
- CSV import
- Batch processing
- Progress tracking

### Advanced Video
- 60-second product showcases
- Multiple scenes
- Custom audio/narration

---

## Summary: Implementation Checklist

### Week 1: Foundation
- [ ] LLM factory implementation
- [ ] multimodal_analysis tool
- [ ] category_mapper tool
- [ ] Testing with real PAVISHA data

### Week 2: Specialists
- [ ] Product Intelligence Specialist
- [ ] Visual Content Specialist
- [ ] Tool integrations (Nano Banana, Imagen 3, Veo 3.1)
- [ ] Individual specialist testing

### Week 3: Integration
- [ ] PM orchestration
- [ ] HITL implementation
- [ ] Atomic persistence
- [ ] WhatsApp integration
- [ ] End-to-end testing

### Success Criteria
- [ ] 2 specialists working
- [ ] 1 HITL approval point
- [ ] < 60 seconds processing
- [ ] < $0.20 per product average cost
- [ ] > 85% user approval rate

---

**Last Updated:** 2025-10-23
**Status:** Ready for Week 1 Implementation
**Next Step:** Begin LLM Factory + Core Tools (Day 1-4)
