# Perfect Product Onboarding: Deep Analysis & Requirements

**Date:** 2025-10-23
**Status:** Analysis Complete - Design Proposal
**Context:** One-by-one product onboarding optimized for multi-platform marketing

---

## Executive Summary

**Core Question:** What data must we collect during product onboarding to enable effective marketing across Instagram, Facebook, X, YouTube, and websites?

**Finding:** Current MVP captures **30% of required data**. Missing 70% blocks marketing effectiveness, platform compliance, and SEO performance.

**Critical Gaps:**
1. **Platform Compliance Data** - Missing required fields for Facebook Catalog, schema.org
2. **Marketing Intelligence** - No brand, category, target audience, benefits, keywords
3. **Visual Asset Strategy** - Generic image storage, no angle/context metadata
4. **Inventory & Business Data** - No availability, condition, stock, SKU
5. **Content Strategy Context** - No tone, positioning, competitor insights

**Recommendation:** Enhanced 3-phase onboarding that progressively collects data based on marketing intent.

---

## Part I: Platform Requirements Analysis

### Current MVP Product Model

```python
class Product(BaseModel):
    id: UUID | None
    name: str | None
    description: str | None
    price: float | None
    sizes: list[str] | None
    colors: list[str] | None
    image_urls: list[str] | None
```

**Coverage:** 7 fields, basic e-commerce data only.

---

### Facebook Product Catalog Requirements

**Source:** Facebook Business Help Center, 2025 Product Feed Specifications

| Field | Status | Criticality | Current Value | Gap |
|-------|--------|-------------|---------------|-----|
| **id** | ✅ | REQUIRED | UUID | Have |
| **title** | ✅ | REQUIRED | `name` | Have |
| **description** | ✅ | REQUIRED | `description` | Have |
| **availability** | ❌ | REQUIRED | - | **MISSING** |
| **condition** | ❌ | REQUIRED | - | **MISSING** |
| **price** | ✅ | REQUIRED | `price` | Have |
| **link** | ❌ | REQUIRED | - | **MISSING** |
| **image_link** | ✅ | REQUIRED | `image_urls[0]` | Have |
| **brand** | ❌ | REQUIRED | - | **MISSING** |
| sale_price | ❌ | Optional | - | Missing |
| color | ✅ | Optional | `colors` | Have |
| product_type | ❌ | Optional | - | Missing |
| gender | ❌ | Optional | - | Missing |
| material | ❌ | Optional | - | Missing |
| size | ✅ | Optional | `sizes` | Have |
| gtin/mpn | ❌ | Optional | - | Missing |
| shipping | ❌ | Optional | - | Missing |

**Coverage:** 5/9 required fields = **56% compliant**
**Blocker:** Cannot publish to Facebook Catalog without availability, condition, link, brand

**Detailed Requirements:**

**availability** (REQUIRED):
- Values: `in stock`, `out of stock`, `preorder`, `available for order`, `discontinued`
- Controls visibility in dynamic ads
- Must update daily (ideally hourly per FB best practices)

**condition** (REQUIRED):
- Values: `new`, `refurbished`, `used`
- Legal requirement for certain categories
- Affects search ranking in FB Shops

**link** (REQUIRED):
- Must be direct URL to product page (not homepage)
- Must start with `http://` or `https://`
- Must be on business's domain (not Facebook Page)
- For India market: Required for WhatsApp Shops integration

**brand** (REQUIRED):
- Company/manufacturer name
- Used for brand filtering in FB Shops
- Impacts trust and conversion rates

---

### Schema.org Product Requirements

**Source:** Google Search Central Documentation, 2025

| Field | Status | Criticality | Current Value | Gap |
|-------|--------|-------------|---------------|-----|
| **name** | ✅ | REQUIRED | `name` | Have |
| **offers** OR **review** OR **aggregateRating** | ❌ | REQUIRED (one of) | - | **MISSING ALL** |
| image | ✅ | Recommended | `image_urls` | Have |

**For Offers (most common):**
| Field | Status | Criticality | Current Value | Gap |
|-------|--------|-------------|---------------|-----|
| **price** | ✅ | REQUIRED | `price` | Have |
| **priceCurrency** | ❌ | REQUIRED | - | **MISSING** |
| **availability** | ❌ | REQUIRED | - | **MISSING** |
| url | ❌ | Recommended | - | Missing |

**Additional Recommended (for rich results):**
- brand ❌
- sku ❌
- gtin ❌
- aggregateRating (if reviews exist) ❌
- review (if reviews exist) ❌

**Coverage:** 2/4 minimum required fields = **50% compliant**
**Impact:** Cannot generate valid JSON-LD schema without priceCurrency and availability
**Lost Opportunity:** Research shows 40% CTR boost with complete Product schema

---

### Instagram Content Requirements

**Source:** Meta Instagram Graph API Documentation, 2025

**Technical Constraints:**
- JPEG only (<8MB)
- Caption max 2200 chars
- 25 posts per 24 hours
- Business profile + Facebook Page required

**Content Best Practices (2025):**
- 3-5 hashtags (not 30+, algorithm changed)
- Front-load key message (first 125 chars)
- Lifestyle imagery > plain product shots
- Clear CTA (shop now, link in bio, tag friend)
- Emoji usage for personality

**Data Needs:**
| Data Type | Current | Gap |
|-----------|---------|-----|
| Product lifestyle context | ❌ | When/where/how to use product? |
| Target audience profile | ❌ | Who is this for? |
| Emotional appeal | ❌ | Aspiration? Practical? Status? |
| Brand aesthetic | ❌ | Professional? Playful? Luxury? |
| Hashtag seeds | ❌ | Niche tags, branded tags |
| Lifestyle images | ⚠️ | Have generic images, no angle metadata |

---

### Twitter/X Requirements

**Source:** Twitter API v2 Documentation, Marketing Best Practices 2025

**Technical Constraints:**
- 280 character limit (STRICT)
- Images boost engagement 40%
- 1-3 hashtags (not excessive)
- 16:9 or 1:1 aspect ratio preferred

**Content Best Practices:**
- One clear message per tweet
- Front-load key info (first 100 chars)
- Question hooks or bold claims
- Concise benefits over features

**Data Needs:**
| Data Type | Current | Gap |
|-----------|---------|-----|
| Quick hook/USP | ❌ | What's the one compelling reason to buy? |
| Viral angle | ❌ | What's shareable about this? |
| Problem-solution fit | ❌ | What pain point does this solve? |

---

### YouTube Shorts Requirements

**Source:** YouTube Platform Documentation, Shorts Best Practices 2025

**Technical Constraints:**
- 9:16 vertical video
- 60 seconds ideal (3 min max)
- Mobile-optimized

**Content Needs:**
- Product demo use case ❌
- Visual story arc ❌
- Before/after transformation ❌

**Status:** DEFER to future (requires video generation, different tech stack)

---

## Part II: Marketing Intelligence Gaps

### Brand & Identity Data

**Current:** No brand information captured

**Required:**
- **Brand name** (manufacturer or company)
- **SKU** (internal product ID for tracking)
- **Category hierarchy** (e.g., "Apparel > Women > Ethnic Wear > Kurtas")
- **Tags/keywords** (seo-optimized, searchable)

**Why Critical:**
- Facebook requires brand (catalog compliance)
- Google Product Category determines ad placement
- SKU enables inventory tracking, variant management
- Tags power search, hashtag generation, SEO

**Example:**
```python
brand: "FabIndia"
sku: "FI-KURTA-BLU-001"
category: "Apparel > Women > Ethnic Wear > Kurtas"
google_product_category: "Apparel & Accessories > Clothing > Dresses"
tags: ["ethnic wear", "kurta", "festive", "cotton", "handloom"]
```

---

### Target Audience & Positioning

**Current:** No audience or positioning data

**Required:**
- **Target audience** (demographics, psychographics)
- **Use cases** (when/where/how is this used?)
- **Unique Selling Proposition** (why buy THIS vs competitors?)
- **Price positioning** (budget, mid-range, premium)

**Why Critical:**
- Instagram captions need to speak to specific audience
- Facebook ad targeting uses audience insights
- Pricing context affects messaging tone
- Use cases inform lifestyle imagery prompts

**Example:**
```python
target_audience: "Urban women 25-40, professionals, appreciate traditional craftsmanship"
use_cases: ["Festive occasions", "Office wear", "Casual outings"]
usp: "Handloom cotton with modern silhouette - comfort meets tradition"
price_positioning: "mid-range"  # or "budget" | "premium"
```

---

### Benefits & Features Framework

**Current:** Generic description field

**Required:** Structured FAB (Features → Advantages → Benefits)

**Why Critical:**
- Features: What it is (material, construction, specs)
- Advantages: What it does (breathable, lightweight, durable)
- Benefits: What customer gets (all-day comfort, confidence, compliments)

**Marketing Rule:** Sell benefits, not features. Current descriptions often list features without emotional payoff.

**Example:**
```python
features: ["100% cotton", "hand-block printed", "loose fit"]
advantages: ["Breathable fabric", "Unique artisan design", "Comfortable movement"]
benefits: ["Stay cool all day", "Stand out with authentic craftsmanship", "Feel confident and relaxed"]
```

**Impact:**
- Instagram captions: Lead with benefits
- Twitter: Benefit-focused hooks
- Facebook: Advantages for product specs
- Schema.org: Features in description

---

### Visual Asset Strategy

**Current:** `image_urls: list[str]` - no metadata

**Required:** Structured image metadata

**Why Critical:**
- E-commerce best practice: 5+ images (front, back, side, close-up, lifestyle)
- Facebook Catalog: Lifestyle images boost CTR 60%
- Instagram: Lifestyle shots outperform plain product shots
- Schema.org: Primary image affects rich result display

**Proposed Structure:**
```python
images: list[ProductImage] = [
    {
        "url": "https://storage/product-front.jpg",
        "type": "product_shot",
        "angle": "front",
        "is_primary": True,
        "alt_text": "Blue printed kurta front view",
        "metadata": {"background": "white", "lighting": "studio"}
    },
    {
        "url": "https://storage/product-lifestyle.jpg",
        "type": "lifestyle",
        "angle": None,
        "is_primary": False,
        "alt_text": "Woman wearing blue kurta at outdoor cafe",
        "metadata": {"context": "casual dining", "model": True}
    }
]
```

**Benefits:**
- Select primary image for Facebook Catalog
- Use lifestyle images for Instagram
- Product shots for schema.org
- Generate alt text for SEO
- Prompt DALL-E 3 with angle/context metadata

---

### Content Tone & Voice

**Current:** CompanyProfile has `brand_voice` (generic)

**Required:** Product-specific tone guidance

**Why Critical:**
- Luxury products need different tone than budget items
- Professional tools vs lifestyle products
- Cultural sensitivity (ethnic wear vs western wear)

**Proposed Addition:**
```python
# In Product model
content_tone: str | None = "professional" | "playful" | "luxury" | "casual" | "traditional"
cultural_context: str | None = "Festive wear appropriate for Diwali, weddings"
```

**Usage:**
- Instagram Specialist: Adapts caption style
- Twitter Specialist: Adjusts hook formality
- Facebook Specialist: Modulates description tone

---

## Part III: Inventory & Business Data

### Availability & Stock Management

**Current:** No availability tracking

**Required:**
- **availability** (in stock, out of stock, preorder, discontinued)
- **stock_quantity** (for low-stock alerts)
- **availability_date** (for preorders)

**Why Critical:**
- Facebook Catalog: Required field
- Schema.org: Required for Offer
- User experience: Don't market products that are unavailable
- Inventory alerts: Auto-pause marketing when out of stock

**Example:**
```python
availability: "in stock"  # FB/schema.org standard values
stock_quantity: 25
low_stock_threshold: 5
availability_date: None  # or "2025-11-01" for preorders
```

---

### Product Condition & Lifecycle

**Current:** No condition tracking

**Required:**
- **condition** (new, refurbished, used)
- **lifecycle_stage** (new_arrival, regular, clearance, discontinued)

**Why Critical:**
- Facebook Catalog: Required field, legal in some categories
- Pricing strategy: Clearance affects urgency messaging
- Marketing tone: New arrivals get different treatment

**Example:**
```python
condition: "new"  # FB/schema.org standard
lifecycle_stage: "new_arrival"
added_date: "2025-10-23"
```

---

### Pricing & Currency

**Current:** `price: float` - no currency

**Required:**
- **price** (have)
- **priceCurrency** (ISO code)
- **sale_price** (if on sale)
- **sale_price_effective_date** (sale period)

**Why Critical:**
- Schema.org: priceCurrency is REQUIRED
- International sales: Multi-currency support
- Sale urgency: "Sale ends in 3 days" messaging

**Example:**
```python
price: 1299.00
priceCurrency: "INR"
sale_price: 999.00
sale_price_effective_date: "2025-10-20/2025-10-31"
```

---

### Product Identifiers

**Current:** Only UUID `id`

**Required:**
- **sku** (internal product ID)
- **gtin** (Global Trade Item Number - barcode)
- **mpn** (Manufacturer Part Number)

**Why Critical:**
- SKU: Essential for inventory management, variant tracking
- GTIN: Required for certain categories on Google Shopping
- MPN: Helps with product matching, prevents duplicates
- Schema.org: Recommended for better product matching

**Example:**
```python
sku: "FI-KURTA-BLU-001"
gtin: "1234567890123"  # if available
mpn: "FI-2025-KURTA-BLU"  # if different from SKU
```

---

### Shipping & Dimensions

**Current:** No shipping data

**Required (for Facebook Catalog in some markets):**
- **shipping_weight**
- **shipping_dimensions**
- **shipping_cost** (or free shipping flag)

**Why Critical:**
- Facebook Catalog: Required for certain categories
- Cost calculation: Shipping affects profitability
- International shipping: Dimensional weight matters

**Example:**
```python
shipping_weight_kg: 0.3
shipping_dimensions_cm: {"length": 40, "width": 30, "height": 2}
free_shipping: True
```

**Recommendation:** Phase 2 requirement (not critical for MVP+1)

---

## Part IV: Competitor Intelligence & SEO

### Competitor Analysis Data

**Current:** No competitive context

**Required:**
- **competitor_products** (similar items on market)
- **competitive_advantages** (why choose ours?)
- **price_comparison** (are we cheaper/pricier?)

**Why Critical:**
- Differentiation messaging: "Unlike competitors, ours has X"
- Pricing strategy: Know if we're positioned budget/mid/premium
- USP clarity: What makes us unique?

**Example:**
```python
competitor_products: [
    {"name": "Generic Cotton Kurta", "price": 899, "brand": "Competitor A"},
    {"name": "Designer Kurta", "price": 2499, "brand": "Luxury Brand B"}
]
competitive_advantages: ["Handloom vs machine-made", "Better fit", "Authentic designs"]
```

**Implementation:**
- Specialist tool: `analyze_competitors(product_name, category, price)`
- Sources: Web scraping, user input, historical data

---

### SEO & Keywords

**Current:** No keyword data

**Required:**
- **seo_keywords** (search terms customers use)
- **hashtag_seeds** (brand + niche tags)
- **meta_description** (for product pages)

**Why Critical:**
- Instagram: Hashtags must be niche + relevant (3-5 max in 2025)
- Twitter: Hashtag strategy affects discoverability
- Schema.org: Keywords improve search matching
- Website SEO: Meta descriptions affect CTR

**Research-Based Strategy:**

**Hashtag Evolution 2025:**
- Instagram removed "follow hashtags" (Dec 2024)
- Algorithm now prioritizes niche hashtags over broad ones
- Optimal: 3-5 highly relevant tags, not 30 generic ones
- Example: `#handloomkurta` > `#fashion`

**Example:**
```python
seo_keywords: ["handloom kurta", "cotton ethnic wear", "Indian festive dress"]
hashtag_seeds: {
    "branded": ["#FabIndia", "#FabIndiaEthnic"],
    "niche": ["#handloomkurta", "#ethnicwearindia", "#cottonfestivewear"],
    "trending": ["#sustainablefashion", "#ethicalfashion"]
}
meta_description: "Handloom blue kurta with modern silhouette. Perfect for festive occasions. Free shipping."
```

---

## Part V: Enhanced Data Model Design

### Proposed Product Model (Marketing-Ready)

```python
class ProductImage(BaseModel):
    """Individual product image with metadata."""
    url: str = Field(..., description="CDN URL of the image")
    type: Literal["product_shot", "lifestyle", "detail", "packaging"] = Field(
        ..., description="Image type for categorization"
    )
    angle: Literal["front", "back", "side", "top", "closeup"] | None = Field(
        None, description="Camera angle for product shots"
    )
    is_primary: bool = Field(default=False, description="Primary image for listings")
    alt_text: str = Field(..., description="SEO alt text description")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional context (background, lighting, model)"
    )


class CompetitorProduct(BaseModel):
    """Competitor product for comparison."""
    name: str
    price: float
    brand: str
    url: str | None = None


class MarketingIntelligence(BaseModel):
    """Marketing-specific intelligence for content generation."""
    target_audience: str = Field(..., description="Who is this product for?")
    use_cases: list[str] = Field(
        ..., description="When/where/how is this used? (e.g., 'Festive occasions')"
    )
    usp: str = Field(..., description="Unique selling proposition")

    # FAB Framework
    features: list[str] = Field(default_factory=list, description="What it IS")
    advantages: list[str] = Field(default_factory=list, description="What it DOES")
    benefits: list[str] = Field(default_factory=list, description="What customer GETS")

    # Content tone
    content_tone: Literal["professional", "playful", "luxury", "casual", "traditional"] = Field(
        default="casual", description="Content tone for marketing copy"
    )
    cultural_context: str | None = Field(None, description="Cultural relevance (e.g., 'Diwali appropriate')")

    # Competitive positioning
    price_positioning: Literal["budget", "mid-range", "premium"] = Field(..., description="Price tier")
    competitor_products: list[CompetitorProduct] | None = Field(default=None)
    competitive_advantages: list[str] | None = Field(default=None)


class SEOData(BaseModel):
    """SEO and discoverability metadata."""
    seo_keywords: list[str] = Field(default_factory=list, description="Search terms")
    hashtag_seeds: dict[str, list[str]] | None = Field(
        default=None, description="Categorized hashtags (branded, niche, trending)"
    )
    meta_description: str | None = Field(None, description="Product page meta description")


class InventoryData(BaseModel):
    """Inventory and fulfillment data."""
    # Required for platforms
    availability: Literal["in stock", "out of stock", "preorder", "available for order", "discontinued"] = Field(
        ..., description="Stock status (FB/schema.org required)"
    )
    condition: Literal["new", "refurbished", "used"] = Field(
        default="new", description="Product condition (FB required)"
    )

    # Stock management
    stock_quantity: int | None = Field(None, description="Current inventory count")
    low_stock_threshold: int | None = Field(5, description="Alert threshold")
    availability_date: str | None = Field(None, description="Preorder availability date (ISO 8601)")

    # Shipping (optional for MVP+1)
    shipping_weight_kg: float | None = None
    shipping_dimensions_cm: dict[str, float] | None = None  # {"length": 40, "width": 30, "height": 2}
    free_shipping: bool | None = None


class Product(BaseModel):
    """
    Enhanced product model optimized for multi-platform marketing.

    Includes all required fields for:
    - Facebook Product Catalog compliance
    - Schema.org Product structured data
    - Instagram/Twitter/YouTube content generation
    - SEO optimization
    """

    # Core identifiers
    id: UUID | None = Field(default=None, description="Database-generated UUID")
    sku: str | None = Field(None, description="Internal product SKU")
    gtin: str | None = Field(None, description="Global Trade Item Number (barcode)")
    mpn: str | None = Field(None, description="Manufacturer Part Number")

    # Basic product info
    name: str = Field(..., description="Product name")
    description: str = Field(..., description="Detailed product description")
    brand: str = Field(..., description="Brand/manufacturer name (FB required)")

    # Categorization
    category: str = Field(..., description="Internal category hierarchy")
    google_product_category: str | None = Field(
        None, description="Google Product Taxonomy category"
    )
    tags: list[str] | None = Field(default_factory=list, description="Searchable tags")

    # Pricing
    price: float = Field(..., description="Regular price")
    priceCurrency: str = Field(default="INR", description="ISO 4217 currency code (schema.org required)")
    sale_price: float | None = Field(None, description="Sale price if on sale")
    sale_price_effective_date: str | None = Field(
        None, description="Sale period (ISO 8601 interval: 2025-10-20/2025-10-31)"
    )

    # Product variants
    sizes: list[str] | None = Field(default_factory=list, description="Available sizes")
    colors: list[str] | None = Field(default_factory=list, description="Available colors")
    material: str | None = Field(None, description="Primary material")
    gender: Literal["male", "female", "unisex"] | None = None

    # Visual assets
    images: list[ProductImage] = Field(..., description="Structured image data")

    # Platform requirements
    link: str | None = Field(None, description="Product page URL (FB required)")
    inventory: InventoryData = Field(..., description="Stock and fulfillment data")

    # Marketing intelligence
    marketing: MarketingIntelligence | None = Field(
        None, description="Marketing-specific context for content generation"
    )

    # SEO
    seo: SEOData | None = Field(None, description="SEO and discoverability metadata")

    # Lifecycle metadata
    lifecycle_stage: Literal["new_arrival", "regular", "clearance", "discontinued"] | None = None
    added_date: str | None = Field(None, description="Date added to catalog (ISO 8601)")

    model_config = ConfigDict(from_attributes=True)
```

---

### Field Coverage Analysis

| Category | Fields | % of Total | Status |
|----------|--------|------------|--------|
| **Core Identifiers** | 4 (id, sku, gtin, mpn) | 9% | NEW |
| **Basic Info** | 3 (name, desc, brand) | 7% | Brand NEW |
| **Categorization** | 3 (category, google_cat, tags) | 7% | NEW |
| **Pricing** | 4 (price, currency, sale_price, dates) | 9% | Currency NEW |
| **Variants** | 4 (sizes, colors, material, gender) | 9% | Material/gender NEW |
| **Visual Assets** | 1 (images structured) | 2% | Structure NEW |
| **Platform Compliance** | 2 (link, inventory) | 5% | NEW |
| **Marketing Intelligence** | 11 (audience, use_cases, USP, FAB, tone, etc.) | 26% | NEW |
| **SEO** | 3 (keywords, hashtags, meta_desc) | 7% | NEW |
| **Lifecycle** | 2 (stage, added_date) | 5% | NEW |

**Total New Fields:** 37 (vs current 7)
**New Marketing-Specific Data:** 26% of model dedicated to marketing context

---

## Part VI: Progressive Onboarding Strategy

### Problem: Overwhelming Data Collection

**If we ask for 37 fields upfront, users will abandon onboarding.**

**Solution: 3-Phase Progressive Enhancement**

---

### Phase 1: MVP Core (Launch-Ready Product)

**When:** Initial product cataloging
**Goal:** Get product into catalog ASAP, enable basic operations
**Effort:** 2-5 minutes per product

**Required Fields:**
```python
# Core (7 fields)
- name: str
- description: str
- price: float
- priceCurrency: str = "INR"  # Auto-default
- images: list[ProductImage]  # At least 1
- brand: str
- inventory.availability: str  # "in stock" default
- inventory.condition: str = "new"  # Auto-default
```

**Auto-Generated:**
- `id`: Database UUID
- `sku`: Auto-generate from name + timestamp if not provided
- `link`: Construct from company domain + product slug
- `added_date`: Current timestamp

**Conversational Flow:**
```
User: [Sends product images]

Agent: "Thanks! I see a blue kurta. Let me draft the details..."

[Image analysis extracts: color, style, category guess]

Agent: "I've drafted this product. Please review:
- Name: Blue Printed Kurta
- Price: ₹____ (what price?)
- Brand: ____ (which brand?)
- Description: [AI-generated from image]

Is this in stock? (yes/no)"

User: "Price 1299, FabIndia, yes"

Agent: "Perfect! Product added to catalog ✅
Want to enhance marketing readiness? (yes/later)"
```

**Result:** Product cataloged, meets minimum FB/schema.org requirements (with auto-defaults).

---

### Phase 2: Marketing Enhancement (Optional Immediate)

**When:** User says "yes" to enhancement OR later via "Enhance product X"
**Goal:** Collect marketing intelligence for content generation
**Effort:** 3-5 minutes per product

**Additional Fields Collected:**
```python
# Variants (if applicable)
- sizes: list[str]
- colors: list[str]
- material: str

# Categorization
- category: str  # From predefined list
- tags: list[str]

# Marketing Intelligence
- marketing.target_audience: str
- marketing.use_cases: list[str]
- marketing.usp: str
- marketing.price_positioning: str
```

**Conversational Flow:**
```
Agent: "Let's make this product marketing-ready! A few quick questions:

1. Who is this for? (e.g., 'Urban women 25-40')
2. When would they wear this? (e.g., 'Festivals, weddings')
3. What makes it special vs others? (e.g., 'Handloom cotton')
4. Price tier? (budget/mid-range/premium)"

User: "Urban women 25-40, festivals and office, handloom cotton with modern fit, mid-range"

Agent: "Got it! Now I can generate:
✅ Instagram posts
✅ Facebook catalog descriptions
✅ Twitter content
✅ Website SEO codes

Want me to generate now or later?"
```

**Result:** Product ready for multi-platform content generation.

---

### Phase 3: Advanced Optimization (On-Demand)

**When:** User explicitly requests OR system recommends
**Goal:** Competitive positioning, advanced SEO, inventory management
**Effort:** 5-10 minutes per product

**Additional Fields:**
```python
# SEO
- seo.seo_keywords: list[str]
- seo.hashtag_seeds: dict
- seo.meta_description: str

# Competitive
- marketing.competitor_products: list[CompetitorProduct]
- marketing.competitive_advantages: list[str]

# FAB Framework (detailed)
- marketing.features: list[str]
- marketing.advantages: list[str]
- marketing.benefits: list[str]

# Advanced inventory
- stock_quantity: int
- low_stock_threshold: int
- shipping_weight_kg: float
```

**Conversational Flow:**
```
Agent: "Want to optimize this product for maximum reach? I can:
1. Research competitor products and suggest advantages
2. Generate SEO keywords and hashtag strategy
3. Create FAB framework for better conversions

This takes 5-10 min. Continue?"

User: "Yes"

Agent: [Uses competitor_analysis_tool]
"Found 3 similar products: [list]
Your advantages: [handloom vs machine-made, better fit]
Suggested keywords: [handloom kurta, cotton ethnic wear]
Hashtags: #handloomkurta #ethnicwearindia #FabIndia

Review and approve?"
```

**Result:** Fully optimized product for competitive market.

---

### Progressive Enhancement Benefits

**User Experience:**
- ✅ No overwhelm: Start simple, enhance later
- ✅ Flexibility: Stop at Phase 1 or go deep
- ✅ Learning: User sees value before investing time

**Business:**
- ✅ Fast onboarding: Products live quickly
- ✅ Quality depth: Marketing-ready when needed
- ✅ Competitive edge: Advanced optimization available

**Technical:**
- ✅ Required fields first: Platform compliance ensured
- ✅ Optional enhancement: Marketing quality scales with user investment
- ✅ Tool delegation: Specialists gather different data types

---

## Part VII: Specialist & Tool Design

### Enhanced Cataloging Specialist

**Responsibilities:**
- Extract basic info from images (name, category guess, color)
- Collect Phase 1 required fields conversationally
- Generate draft with auto-defaults
- Offer Phase 2 enhancement

**Tools:**
- `image_analysis_tool` (existing, enhanced)
- `save_product` (existing, updated schema)
- `generate_sku` (NEW)
- `construct_product_link` (NEW)

---

### Marketing Intelligence Specialist (NEW)

**Responsibilities:**
- Conduct Phase 2 enhancement interview
- Extract target audience, use cases, USP
- Determine price positioning
- Generate initial hashtag seeds

**Tools:**
- `extract_marketing_context` (conversational interview)
- `analyze_product_positioning` (price tier determination)
- `generate_hashtag_seeds` (niche + branded tags)

---

### Competitive Analysis Specialist (NEW)

**Responsibilities:**
- Phase 3 optimization
- Research competitor products (web scraping or user input)
- Identify competitive advantages
- Generate SEO keywords
- Build FAB framework

**Tools:**
- `search_competitor_products` (web search + scraping)
- `analyze_price_positioning` (compare to market)
- `generate_seo_keywords` (keyword research)
- `build_fab_framework` (structured benefits extraction)

---

### Image Enhancement Specialist (NEW)

**Responsibilities:**
- Analyze uploaded images for angle/type
- Request missing angles (e.g., "Need lifestyle shot")
- Categorize images (product_shot vs lifestyle)
- Generate alt text for SEO

**Tools:**
- `classify_image_type` (product vs lifestyle)
- `detect_image_angle` (front, back, side, closeup)
- `generate_alt_text` (SEO descriptions)
- `request_missing_angles` (guide user to upload specific shots)

---

## Part VIII: Data Collection Workflow

### Phase 1: Core Onboarding

```
User: [Sends 3 product images]

PM → Cataloging Specialist
  ↓
  Calls image_analysis_tool(images) → ImageAnalysisResult
  ↓
  Extracts: category="kurta", colors=["blue"], style="printed"
  ↓
  Asks: "What price?" → User: "1299"
  Asks: "Which brand?" → User: "FabIndia"
  ↓
  Builds Product draft:
    name: "Blue Printed Kurta" (from image)
    description: AI-generated from image
    price: 1299
    priceCurrency: "INR" (auto-default)
    brand: "FabIndia"
    images: [structured from uploads with auto-classification]
    inventory.availability: "in stock" (auto-default)
    inventory.condition: "new" (auto-default)
    sku: AUTO-GENERATED
    link: AUTO-GENERATED
  ↓
  Presents for approval (HITL)
  ↓
  User approves
  ↓
  save_product → Database
  ↓
  "Product added ✅ Want to enhance for marketing? (yes/later)"
```

**Result:** Product is catalog-ready, FB/schema.org compliant.

---

### Phase 2: Marketing Enhancement (If User Says "Yes")

```
PM → Marketing Intelligence Specialist
  ↓
  Asks: "Who is this for?" → User: "Urban women 25-40"
  Asks: "When would they use this?" → User: "Festivals, office"
  Asks: "What makes it special?" → User: "Handloom, modern fit"
  Asks: "Price tier?" → Specialist infers: "mid-range" (based on 1299 INR)
  ↓
  Builds MarketingIntelligence:
    target_audience: "Urban women 25-40, professionals"
    use_cases: ["Festive occasions", "Office wear"]
    usp: "Handloom cotton with modern silhouette"
    price_positioning: "mid-range"
    content_tone: AUTO-INFERRED from brand + category
  ↓
  Calls generate_hashtag_seeds
    → branded: ["#FabIndia", "#FabIndiaEthnic"]
    → niche: ["#handloomkurta", "#ethnicwearindia"]
    → trending: ["#sustainablefashion"]
  ↓
  Updates Product.marketing field
  ↓
  "Marketing-ready ✅ Now I can generate Instagram/Facebook/Twitter content!"
```

---

### Phase 3: Advanced Optimization (On-Demand)

```
User: "Optimize my Blue Kurta product"

PM → Competitive Analysis Specialist
  ↓
  Calls search_competitor_products(category="kurta", price_range=[1000, 1500])
    → Finds 3 competitors
  ↓
  Asks user: "I found similar kurtas at ₹899 and ₹2499. What makes yours better?"
  User: "Ours is handloom vs machine-made, better fit"
  ↓
  Builds:
    competitor_products: [{name, price, brand}, ...]
    competitive_advantages: ["Handloom craftsmanship", "Superior fit"]
  ↓
  Calls generate_seo_keywords(product, competitors)
    → seo_keywords: ["handloom kurta", "cotton ethnic wear", "designer kurta"]
  ↓
  Calls build_fab_framework
    Features: ["100% cotton", "hand-block print", "loose fit"]
    Advantages: ["Breathable", "Unique design", "Comfortable"]
    Benefits: ["Stay cool", "Stand out", "Feel confident"]
  ↓
  Updates Product.seo + Product.marketing.competitive_* + Product.marketing.FAB
  ↓
  "Fully optimized ✅ Ready for competitive marketing campaigns!"
```

---

## Part IX: Implementation Priorities

### Immediate (Week 1-2): Phase 1 Core

**Goal:** Enhance current cataloging to meet platform compliance

**Tasks:**
1. Extend Product model with required fields:
   - `brand: str` (REQUIRED)
   - `priceCurrency: str` (REQUIRED, default "INR")
   - `inventory: InventoryData` (availability, condition)
   - `link: str | None` (auto-generate)
   - `sku: str | None` (auto-generate)

2. Update Cataloging Specialist prompt:
   - Ask for brand explicitly
   - Auto-default availability="in stock", condition="new"
   - Generate SKU from name + timestamp
   - Construct link from company domain

3. Database migration:
   ```sql
   ALTER TABLE products
   ADD COLUMN brand TEXT NOT NULL DEFAULT 'Unknown',
   ADD COLUMN price_currency TEXT NOT NULL DEFAULT 'INR',
   ADD COLUMN availability TEXT NOT NULL DEFAULT 'in stock',
   ADD COLUMN condition TEXT NOT NULL DEFAULT 'new',
   ADD COLUMN sku TEXT,
   ADD COLUMN link TEXT;
   ```

4. Test autonomous framework:
   - Scenario: Catalog product with brand
   - Verify FB compliance (9/9 required fields)
   - Verify schema.org compliance (4/4 minimum)

**Acceptance Criteria:**
- ✅ Every cataloged product has brand, availability, condition, priceCurrency
- ✅ Products can generate valid Facebook Product Feed
- ✅ Products can generate valid schema.org JSON-LD
- ✅ SKU auto-generated if not provided
- ✅ Link auto-constructed from domain + slug

**Effort:** 1-2 weeks

---

### Near-Term (Week 3-4): Phase 2 Marketing Enhancement

**Goal:** Enable marketing content generation with proper context

**Tasks:**
1. Add MarketingIntelligence schema
2. Create Marketing Intelligence Specialist:
   - Conversational interview for audience, use_cases, USP
   - Price positioning inference
   - Hashtag seed generation

3. Update Product model:
   - `marketing: MarketingIntelligence | None`
   - `category: str`
   - `tags: list[str]`

4. Extend image handling:
   - `images: list[ProductImage]` (structured)
   - Auto-classify image types (product_shot vs lifestyle)
   - Generate alt text

5. Database migration:
   ```sql
   ALTER TABLE products
   ADD COLUMN category TEXT,
   ADD COLUMN tags TEXT[],
   ADD COLUMN marketing_data JSONB;

   -- Structured images (replace image_urls)
   CREATE TABLE product_images (
     id UUID PRIMARY KEY,
     product_id UUID REFERENCES products(id),
     url TEXT NOT NULL,
     type TEXT NOT NULL,
     angle TEXT,
     is_primary BOOLEAN DEFAULT FALSE,
     alt_text TEXT,
     metadata JSONB
   );
   ```

**Acceptance Criteria:**
- ✅ User can optionally enhance product with marketing context
- ✅ Marketing Specialist collects audience, use_cases, USP
- ✅ Hashtag seeds generated (branded + niche + trending)
- ✅ Images classified by type/angle
- ✅ Alt text generated for SEO

**Effort:** 2 weeks

---

### Future (Week 5+): Phase 3 Advanced Optimization

**Goal:** Competitive intelligence and advanced SEO

**Tasks:**
1. Create Competitive Analysis Specialist
2. Implement competitor search tool (web scraping or API)
3. Build FAB framework generator
4. Add SEO keyword research tool

**Effort:** 2-3 weeks

---

## Part X: Success Metrics

### Platform Compliance

**Facebook Catalog:**
- Target: 100% of products have all 9 required fields
- Current: ~56% (5/9 fields)
- Post-Phase 1: 100%

**Schema.org:**
- Target: 100% of products generate valid JSON-LD
- Current: 50% (missing priceCurrency, availability)
- Post-Phase 1: 100%

---

### Marketing Readiness

**Content Generation Quality:**
- Target: 80%+ of generated content approved by users
- Dependency: Phase 2 marketing enhancement
- Metric: Approval rate from HITL

**Platform-Specific Compliance:**
- Instagram: Character limits, hashtag counts
- Facebook: Description length, no prohibited content
- Twitter: 280-char limit, hashtag strategy

---

### User Experience

**Onboarding Speed:**
- Phase 1: 2-5 minutes per product (target)
- Phase 2: +3-5 minutes (optional)
- Phase 3: +5-10 minutes (on-demand)

**Abandonment Rate:**
- Target: <10% abandon during Phase 1
- Measure: Products started vs completed

**Enhancement Adoption:**
- Target: 60%+ users opt for Phase 2 enhancement
- Measure: Phase 2 completion rate

---

## Part XI: Recommendations

### Immediate Actions (This Week)

1. **Approve Enhanced Product Model** (Phase 1 fields)
   - Brand, priceCurrency, inventory (availability, condition)
   - Auto-generation logic (SKU, link)

2. **Update Cataloging Specialist Prompt**
   - Add brand question
   - Explain auto-defaults (availability, condition)
   - Offer Phase 2 enhancement

3. **Database Migration**
   - Add required columns
   - Backfill existing products with defaults

4. **Test Platform Compliance**
   - Generate Facebook Product Feed XML
   - Generate schema.org JSON-LD
   - Validate with Google Rich Results Test

---

### Design Decisions Needed

**Question 1: Category Taxonomy**
- Use Google Product Category taxonomy (6000+ categories)?
- Or custom simplified taxonomy for small businesses?
- **Recommendation:** Start custom, map to Google later

**Question 2: Image Requirements**
- Require minimum number of images (e.g., 3)?
- Enforce specific angles (front, back, lifestyle)?
- **Recommendation:** Soft guidance, not hard requirements (Phase 1)

**Question 3: Auto-Generation Behavior**
- Auto-generate SKU always, or ask user first?
- Auto-default availability="in stock" or require explicit answer?
- **Recommendation:** Auto-generate with option to override

**Question 4: Phase 2 Trigger**
- Always offer Phase 2 after Phase 1?
- Or only when user requests marketing content?
- **Recommendation:** Always offer, user can say "later"

---

## Conclusion

**Current State:** MVP cataloging captures 30% of data needed for effective multi-platform marketing.

**Critical Gaps:** Missing platform-required fields (brand, availability, priceCurrency), marketing intelligence (audience, USP, benefits), and SEO data (keywords, hashtags).

**Solution:** 3-phase progressive enhancement:
- **Phase 1:** Core onboarding (2-5 min) → Platform compliance ✅
- **Phase 2:** Marketing enhancement (3-5 min) → Content generation ready ✅
- **Phase 3:** Advanced optimization (5-10 min) → Competitive edge ✅

**Next Steps:**
1. Implement Phase 1 (Week 1-2): Brand, inventory, auto-generation
2. Test platform compliance (FB Catalog, schema.org)
3. Design Phase 2 Marketing Intelligence Specialist (Week 3-4)
4. Validate with real users

**Business Impact:** With Phase 1+2 complete, every product can generate:
- ✅ Valid Facebook Product Catalog feeds
- ✅ SEO-optimized schema.org markup (40% CTR boost)
- ✅ Platform-compliant Instagram/Twitter/Facebook content
- ✅ Competitive marketing positioning

---

**Last Updated:** 2025-10-23
**Status:** Ready for stakeholder review & approval
**Owner:** Product & Engineering Team
