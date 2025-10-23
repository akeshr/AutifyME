# Workflow Design Strategy - Foundational Principles

**Date:** 2025-10-23
**Status:** Core Framework - Apply to ALL Workflow Designs
**Purpose:** Prevent over-engineering, ensure reusability, maintain simplicity

---

## Part I: The Meta-Strategy

### Core Question Framework

When designing ANY workflow, ask these questions IN ORDER:

#### 1. What are the DOMAINS (not workflows)?

❌ **Wrong thinking:** "Product onboarding workflow needs these steps..."
✅ **Right thinking:** "What business domains exist? Product understanding, visual content, marketing communication..."

**Why:** Domains are reusable. Workflows are specific. Design for domains.

#### 2. Which domains require ORCHESTRATION vs just TOOLS?

**Specialist = Domain Expert that:**
- Makes decisions based on context
- Orchestrates multiple tool calls
- Has adaptive workflows (if X then Y, else Z)
- Asks clarifying questions
- Returns structured domain models

**Tool = Utility Function that:**
- Single purpose, deterministic
- One input → one output
- No decision making
- Can be called by any specialist

**Test:** If you can write it in 50 lines of code with no conditionals, it's a TOOL not a SPECIALIST.

#### 3. Where does LOGIC belong?

**Inline Logic** (within specialist):
- Domain-specific calculations (SKU generation, price calculations)
- Simple conditionals (if variants exist, generate combinations)
- String transformations (URL slug generation)
- Data validation

**Separate Specialist** (orchestration needed):
- Cross-domain coordination
- Multiple HITL points
- Complex decision trees
- State management

**Example:**
```python
# ❌ Wrong: Variant Strategy Specialist
class VariantStrategySpecialist:
    def calculate_combinations(self, axes, values):
        # 20 lines of math
        return combinations

# ✅ Right: Inline in Product Intelligence Specialist
class ProductIntelligenceSpecialist:
    def process(self, input):
        # ...
        if self._has_variants(input):
            combinations = self._calculate_skus(axes, values)  # inline method
        # ...
```

#### 4. How will this be REUSED?

**Critical Test:** Can this specialist be called from multiple workflows?

**Examples:**
- ✅ **Visual Content Specialist:** Used in product onboarding, marketing campaigns, catalog generation, social media, ads
- ❌ **Variant Strategy Specialist:** Only used in product onboarding (should be inline)

**Design Rule:** If only used in 1 workflow, it's probably inline logic, not a specialist.

#### 5. What are the HITL points?

**Principle:** Minimize HITL points. Each approval adds user friction.

**Good HITL points:**
- Strategic decisions (approve complete product draft before saving)
- High-cost operations (approve $500 ad spend before launching)
- Irreversible actions (publish to production, send email to 10k users)

**Bad HITL points:**
- Every intermediate step
- Decisions the system can make
- Low-risk operations (save draft, classify image)

**Example:**
- ❌ 5 HITL points: Product specs → Variants → Images → SEO → Marketing
- ✅ 1 HITL point: Complete product draft (all together)

---

## Part II: Specialist Design Principles

### 1. Domain Boundaries

Each specialist owns ONE business domain:

**Product Intelligence Specialist:**
- Domain: Understanding products (specs, categories, attributes)
- NOT responsible for: Images, marketing copy, videos

**Visual Content Specialist:**
- Domain: Professional visual assets (images, videos, graphics)
- NOT responsible for: Product specs, marketing text

**Marketing Content Specialist:**
- Domain: Text/copy for marketing (posts, ads, descriptions)
- NOT responsible for: Product specs, images

### 2. LLM Factory Pattern

❌ **Wrong:** Hardcode model in specialist
```python
class ProductIntelligenceSpecialist:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o")  # WRONG!
```

✅ **Right:** Accept LLM from factory
```python
class ProductIntelligenceSpecialist:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm  # Injected by factory

# Factory handles model selection
llm = llm_factory.get_llm(
    provider="openai",  # or "anthropic", "google"
    model="gpt-4o",
    temperature=0,
)
specialist = ProductIntelligenceSpecialist(llm=llm)
```

**Why:** Model switching, testing, cost optimization without code changes.

### 3. Structured Outputs

Every specialist returns structured Pydantic models (not text):

```python
class ProductIntelligenceOutput(BaseModel):
    product_family: ProductFamily
    variant_axes: list[VariantAxis]
    images_metadata: list[ImageMetadata]
    confidence_score: float
    missing_fields: list[str]

class VisualContentOutput(BaseModel):
    enhanced_images: list[CDNAsset]
    generated_images: list[CDNAsset]
    videos: list[CDNAsset]
    primary_image_url: str
    total_cost: Decimal
```

**Why:** Type safety, composability, testability, observability.

### 4. Tool Design

Tools are stateless, single-purpose functions:

```python
@tool
def enhance_image_nano_banana(
    image_path: str,
    enhancement_instructions: str,
) -> str:
    """Enhance image using Nano Banana (FREE).

    Returns: CDN URL to enhanced image
    """

@tool
def generate_imagen3_product_shot(
    reference_image_url: str,
    product_name: str,
    style: str = "white_background",
) -> str:
    """Generate professional product photo.

    Cost: $0.03
    Returns: CDN URL
    """
```

**Why:** Reusable across specialists, testable in isolation, composable.

---

## Part III: Workflow Composition Patterns

### Pattern 1: Sequential Specialist Coordination

**When:** Specialists depend on each other's outputs

```python
# Product Onboarding Workflow
async def product_onboarding_workflow(input):
    # Step 1: Understand product
    product_draft = await pm.delegate_to(
        specialist="product_intelligence",
        input=input,
    )

    # Step 2: Generate professional visuals (uses product_draft)
    visual_assets = await pm.delegate_to(
        specialist="visual_content",
        input={"product_draft": product_draft, "raw_images": input.images},
    )

    # Step 3: Persist (uses both)
    result = await pm.persist(product_draft, visual_assets)

    return result
```

### Pattern 2: Parallel Specialist Execution

**When:** Specialists are independent

```python
# Marketing Campaign Workflow
async def marketing_campaign_workflow(product_ids):
    # Parallel execution
    visual_task = pm.delegate_to("visual_content", {"product_ids": product_ids})
    content_task = pm.delegate_to("marketing_content", {"product_ids": product_ids})

    visual_assets, content_pieces = await asyncio.gather(
        visual_task,
        content_task,
    )

    # Combine and return
    return combine_campaign(visual_assets, content_pieces)
```

### Pattern 3: Specialist Reuse Across Workflows

**Same specialist, different workflows:**

```python
# Workflow 1: Product Onboarding
visual_assets = await visual_content_specialist.generate({
    "input_type": "user_photos",
    "images": raw_images,
    "style": "professional_studio",
    "outputs": ["enhanced", "multi_angle"],
})

# Workflow 2: Marketing Campaign
visual_assets = await visual_content_specialist.generate({
    "input_type": "existing_product",
    "product_ids": [123, 456],
    "style": "branded_graphics",
    "outputs": ["social_media", "ads"],
})

# Workflow 3: Catalog Refresh
visual_assets = await visual_content_specialist.generate({
    "input_type": "bulk_products",
    "product_ids": range(1, 200),
    "style": "consistent_family",
    "outputs": ["product_shots"],
})
```

---

## Part IV: Anti-Patterns (What NOT to Do)

### ❌ Anti-Pattern 1: Workflow-Specific Specialists

```python
# WRONG: Specialist only used in 1 workflow
class ProductOnboardingImageProcessor:
    """Only processes images during onboarding"""
    # Can't be reused for marketing, catalogs, etc.
```

**Fix:** Domain-based specialist that works across workflows.

### ❌ Anti-Pattern 2: Over-Segmentation

```python
# WRONG: Too many specialists for simple logic
class VariantDetectionSpecialist: pass
class VariantCalculationSpecialist: pass
class SKUGenerationSpecialist: pass
class VariantValidationSpecialist: pass
```

**Fix:** Inline logic in Product Intelligence Specialist.

### ❌ Anti-Pattern 3: Tools Disguised as Specialists

```python
# WRONG: No orchestration, just tool calls
class SEOOptimizationSpecialist:
    def optimize(self, product):
        slug = self._generate_slug(product.name)  # simple transform
        meta = self._generate_meta(product.desc)  # template
        return {"slug": slug, "meta": meta}
```

**Fix:** These are inline methods or tools, not a specialist.

### ❌ Anti-Pattern 4: HITL Overload

```python
# WRONG: 5 approval points
await hitl_approve("product_specs")
await hitl_approve("variant_strategy")
await hitl_approve("images")
await hitl_approve("seo")
await hitl_approve("marketing")
```

**Fix:** 1 approval for complete product draft.

### ❌ Anti-Pattern 5: Hardcoded LLM Models

```python
# WRONG: Locked to specific provider/model
llm = ChatOpenAI(model="gpt-4o")
specialist = ProductIntelligenceSpecialist(llm)
```

**Fix:** LLM factory with configuration-based selection.

---

## Part V: Decision Tree for Specialist Design

```
┌─────────────────────────────────────┐
│ Need to design a workflow?          │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│ 1. What are the DOMAINS?            │
│    (not workflow steps)              │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│ 2. For each domain, ask:            │
│    - Orchestration needed?          │
│    - Decision making?               │
│    - Adaptive workflow?             │
│    - Multiple tool calls?           │
└─────────────────────────────────────┘
              │
         Yes  │  No
    ┌─────────┴─────────┐
    ▼                   ▼
┌──────────┐      ┌──────────┐
│Specialist│      │Tool or   │
│          │      │Inline    │
│          │      │Logic     │
└──────────┘      └──────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 3. Can this specialist be reused in │
│    other workflows?                  │
└─────────────────────────────────────┘
              │
         Yes  │  No
    ┌─────────┴─────────┐
    ▼                   ▼
┌──────────┐      ┌──────────┐
│Keep as   │      │Make it   │
│Specialist│      │inline    │
└──────────┘      └──────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 4. Where are HITL points?           │
│    (minimize to strategic decisions) │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 5. Design specialist:               │
│    - LLM injected from factory      │
│    - Structured Pydantic outputs    │
│    - Clear domain boundaries        │
│    - Composable with other specialists│
└─────────────────────────────────────┘
```

---

## Part VI: Checklist for Any Workflow Design

Before implementing ANY workflow, verify:

### Domain Analysis
- [ ] Identified all business domains (not workflow steps)
- [ ] Each domain has clear boundaries
- [ ] Domains are reusable across multiple workflows

### Specialist Design
- [ ] Each specialist orchestrates (not just tool calls)
- [ ] Specialists make decisions, not just execute
- [ ] No workflow-specific specialists
- [ ] No tools disguised as specialists
- [ ] Inline logic kept inline (not separate specialists)

### Technical Patterns
- [ ] LLM factory pattern (no hardcoded models)
- [ ] Structured Pydantic outputs
- [ ] Stateless tools
- [ ] Clear specialist → tool boundaries

### User Experience
- [ ] Minimal HITL points (ideally 1)
- [ ] Strategic HITL only (not every step)
- [ ] Fast user feedback loops

### Reusability
- [ ] Each specialist can be called from 3+ workflows
- [ ] Tools are stateless and reusable
- [ ] No cross-specialist dependencies

### Cost Optimization
- [ ] Latest/cheapest models considered (Nano Banana FREE, etc.)
- [ ] Expensive operations (video, images) are optional
- [ ] Cost transparency (show user: "This will cost $X")

---

## Part VII: Real-World Example - Product Onboarding

### Step 1: Identify Domains

**User goal:** Add product to catalog

**Domains involved:**
1. **Product Understanding** - What is this product? (specs, category, variants)
2. **Visual Content** - Professional images/videos for the product
3. **Marketing Communication** - Text content to promote the product

### Step 2: Specialist vs Inline Logic

**Product Understanding Domain:**
- Orchestration needed? ✅ Yes (vision analysis → category mapping → variant logic)
- Decision making? ✅ Yes ("Is this 1 product or family?", "What category fits?")
- Multiple tool calls? ✅ Yes (multimodal_analysis, category_mapper)
- **Decision: SPECIALIST** ✅

**Visual Content Domain:**
- Orchestration needed? ✅ Yes (enhance → generate → video → consistency check)
- Decision making? ✅ Yes ("Quality too poor, regenerate", "B2B needs studio shots")
- Multiple tool calls? ✅ Yes (nano_banana, imagen3, veo31)
- **Decision: SPECIALIST** ✅

**Variant Logic:**
- Orchestration needed? ❌ No (parse input → calculate → generate SKUs)
- Decision making? ⚠️ Minimal ("Warn if >20 SKUs")
- Multiple tool calls? ❌ No (pure calculation)
- **Decision: INLINE in Product Intelligence** ✅

**SEO Generation:**
- Orchestration needed? ❌ No (string transformations, templates)
- Decision making? ❌ No (deterministic)
- Multiple tool calls? ❌ No
- **Decision: INLINE in Product Intelligence** ✅

### Step 3: Reusability Check

**Product Intelligence Specialist:**
- Product onboarding ✅
- Product updates ✅
- Competitive analysis ✅
- Inventory audits ✅
- **Reusability: HIGH** ✅

**Visual Content Specialist:**
- Product onboarding ✅
- Marketing campaigns ✅
- Catalog generation ✅
- Social media posts ✅
- Ad creatives ✅
- **Reusability: VERY HIGH** ✅

### Step 4: HITL Points

**Option A (Wrong):** 5 HITL points
- Approve product specs
- Approve variant strategy
- Approve images
- Approve SEO
- Approve marketing

**Option B (Right):** 1 HITL point
- Approve complete product draft (specs + images + everything together)

**Decision: 1 HITL point** ✅

### Step 5: Final Design

**Specialists:** 2
1. Product Intelligence Specialist (product understanding domain)
2. Visual Content Specialist (visual assets domain)

**Workflow:**
```
User input (text + images)
  ↓
Product Intelligence Specialist
  → Output: ProductDraft (specs, variants, categories, SEO)
  ↓
Visual Content Specialist
  → Input: ProductDraft + raw images
  → Output: VisualAssets (enhanced + generated images, CDN URLs)
  ↓
HITL: Review ProductDraft + VisualAssets together
  ↓
Persist to database
  ↓
Done
```

**HITL:** 1 approval screen (all together, Shopify-style)

---

## Part VIII: Future Workflow Examples

### Marketing Campaign Workflow (Reuses Specialists)

**Domains:**
- Visual Content (reused!)
- Marketing Communication (new specialist if complex, or just tools)

**Specialists:**
- Visual Content Specialist (generate branded graphics)
- Marketing Content Specialist (write platform copy)

**Workflow:**
```
User: "Create LinkedIn campaign for 10 products"
  ↓
PM fetches 10 products from database
  ↓
Visual Content Specialist (parallel)
  → Generate 10 LinkedIn graphics
Marketing Content Specialist (parallel)
  → Generate 10 LinkedIn posts
  ↓
HITL: Review campaign
  ↓
Schedule posts
```

### Catalog Refresh Workflow (Reuses Specialists)

**Domains:**
- Visual Content (reused!)

**Specialists:**
- Visual Content Specialist (bulk generate consistent images)

**Workflow:**
```
User: "Refresh images for all 200 products"
  ↓
PM fetches 200 products
  ↓
Visual Content Specialist
  → Analyze existing style
  → Generate consistent images for all 200
  → Batch process ($6 total = 200 × $0.03)
  ↓
HITL: Review sample (10 images), approve all
  ↓
Bulk update database
```

---

## Summary: The Golden Rules

1. **Think Domains, Not Workflows** - Design for reusability
2. **Specialist = Orchestration** - If it's just logic, keep it inline
3. **LLM Factory Always** - No hardcoded models
4. **Minimize HITL** - Strategic approvals only
5. **Structured Outputs** - Pydantic models, not text
6. **Reusability Test** - Can this be used in 3+ workflows?
7. **Cost Transparency** - Show user what operations cost
8. **Latest Models** - Research latest (Nano Banana FREE, Veo 3.1, etc.)

---

**Last Updated:** 2025-10-23
**Status:** Core Framework - Apply to ALL Future Designs
**Next:** Apply this strategy to product onboarding implementation plan
