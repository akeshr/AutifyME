# Product Scaling Roadmap: Bulk Onboarding & Multi-Platform Marketing

**Date:** 2025-10-23
**Status:** Planning Phase
**Prerequisites:** MVP cataloging workflow operational ✅

**Vision:** Enable users to onboard entire product catalogs and generate platform-optimized marketing content at scale.

---

## Executive Summary

**Business Context:** MVP proven. Users now need to:
1. Onboard ALL products efficiently (not one-by-one)
2. Generate marketing content for every platform (Instagram, Facebook, X, YouTube, Website)
3. Scale digital presence across social media and e-commerce channels

**Strategic Approach:** Sequence implementation by business impact and technical dependency. Prioritize bulk onboarding (unblock catalog growth), then website SEO (quick 40% CTR win), then social content generation (marketing activation).

**Timeline:** 8-12 weeks for Phases 1-4, deferred platform distribution and video for future phases.

---

## Research Synthesis

### Platform Requirements (2025 Standards)

| Platform | Format | Constraints | Key Benefit | API Complexity |
|----------|--------|-------------|-------------|----------------|
| **Instagram** | JPEG <8MB, caption + hashtags | Business profile + FB Page, 25 posts/24h, no shopping tags via API | Visual storytelling, 5.91% engagement | HIGH - Approval required |
| **Facebook Catalog** | Product feed (ID, title, desc 30-5000 chars, price, image) | Structured catalog format | Dynamic ads, retargeting | MEDIUM - Catalog API |
| **X/Twitter** | 280 chars + image | Images boost engagement 40% | Quick announcements, viral potential | MEDIUM - Ads API |
| **YouTube Shorts** | 9:16 vertical video, 60s ideal | Video generation required | Highest engagement (5.91%), product demos | VERY HIGH - Video gen |
| **Website/SEO** | JSON-LD schema.org Product markup | Name + (review OR rating OR offers) | **40% CTR boost** with rich snippets | LOW - JSON generation |

### Technical Capabilities Verified

**AI Image Generation:**
- DALL-E 3 (OpenAI API): Best for text rendering, product accuracy, realistic textures
- Midjourney: Best for artistic/emotional appeal (requires Discord/API wrapper)
- **Decision:** Start with DALL-E 3 (native OpenAI integration, proven text accuracy)

**Bulk Processing Patterns:**
- CSV upload → validate schema → batch process (10 products/batch) → progress tracking → error recovery
- Best practice: Test 1-3 products first, backup before import, handle partial success
- **Critical:** Need job tracking table, progress updates via WhatsApp, clear error reporting

**Schema.org Standards:**
- Format: JSON-LD (Google preferred)
- Types: Product, Offer, AggregateRating, Review
- **Impact:** 40% higher CTR with rich results
- **Complexity:** LOW - pure JSON generation, no API approvals

### Strategic Insights

1. **Content Generation ≠ Distribution:** Focus Phase 1-3 on GENERATING marketing assets; auto-posting (Phase 5) requires complex API approvals
2. **Schema.org = Quick Win:** Website embeddings deliver 40% CTR boost with minimal implementation complexity
3. **Video is Hard:** YouTube Shorts requires video generation (Runway/Pika integration) - defer to Phase 6
4. **Platform API Reality:** Instagram/Facebook Graph API requires business verification (weeks), Twitter API has costs - prioritize content generation first
5. **Bulk Processing = Critical Path:** Users blocked until they can onboard full catalog - highest priority

---

## Architectural Plan

### New Workflows

**1. Bulk Product Onboarding Workflow**
- **Input:** CSV file (via WhatsApp document) or batch of product images
- **Process:** Parse → validate → batch catalog (10 at a time) → track progress → handle errors
- **Output:** All products in database with structured data, detailed progress report
- **HITL:** Per-product approval OR batch approval (configurable)

**2. Marketing Content Generation Workflow**
- **Input:** Product ID(s) + platform selection (Instagram | Facebook | Twitter | All)
- **Process:** Generate platform-specific copy + DALL-E 3 images
- **Output:** Marketing assets stored in `marketing_content` table, ready for review/use
- **HITL:** Batch approval for generated content

**3. Website Schema Generation Workflow**
- **Input:** Product ID OR "all products"
- **Process:** Generate JSON-LD Product schema with Offer, AggregateRating (if reviews exist)
- **Output:** Copy-paste ready schema code, validation report
- **HITL:** None (automated validation against schema.org spec)

**4. Platform Distribution Workflow** (FUTURE - Phase 5)
- **Input:** Approved marketing content + schedule
- **Process:** Post via platform APIs (Instagram Graph, Twitter, Facebook Catalog)
- **Output:** Published content with analytics tracking

### New Departments & Specialists

#### Operations Department (NEW)
**Purpose:** Handle batch processing, validation, quality assurance

**Specialists:**
- **Bulk Processing Specialist:** Orchestrates CSV parsing, batch cataloging, progress tracking
- **Validation Specialist:** Schema validation, data quality checks, error detection
- **Reporting Specialist:** Generates batch job summaries, error reports

#### Marketing Content Department (NEW)
**Purpose:** Generate platform-optimized marketing content

**Specialists:**
- **Instagram Specialist:** Generates captions (hashtags, emojis, CTAs) + DALL-E 3 lifestyle images
- **Facebook Specialist:** Generates product catalog descriptions (30-5000 chars) optimized for dynamic ads
- **Twitter Specialist:** Generates concise 280-char tweets + hashtags + DALL-E 3 images
- **SEO Specialist:** Generates JSON-LD schema.org Product markup for websites
- **(Future) Video Specialist:** Generates YouTube Shorts using video generation tools

#### Existing Cataloging Department
**Enhancements:**
- Support batch mode (called repeatedly by Bulk Processing Specialist)
- Enhanced error recovery (partial success handling)
- Batch approval mode (approve 10 products at once)

### Data Model Changes

#### New Tables

```sql
-- Bulk job tracking
CREATE TABLE bulk_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id TEXT NOT NULL,
    user_id TEXT NOT NULL,  -- WhatsApp phone number
    job_type TEXT NOT NULL,  -- 'catalog_csv' | 'generate_marketing' | 'generate_schema'
    total_items INTEGER NOT NULL,
    processed_items INTEGER DEFAULT 0,
    successful_items INTEGER DEFAULT 0,
    failed_items INTEGER DEFAULT 0,
    status TEXT NOT NULL,  -- 'pending' | 'in_progress' | 'completed' | 'failed' | 'partial_success'
    input_data JSONB,  -- CSV path, product IDs, platform selections
    error_log JSONB,  -- Array of {item_id, error_message, timestamp}
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX idx_bulk_jobs_user_status ON bulk_jobs(user_id, status);
CREATE INDEX idx_bulk_jobs_created_at ON bulk_jobs(created_at DESC);

-- Marketing content storage
CREATE TABLE marketing_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    company_id TEXT NOT NULL,
    platform TEXT NOT NULL,  -- 'instagram' | 'facebook' | 'twitter' | 'youtube' | 'website'
    content_type TEXT NOT NULL,  -- 'post' | 'story' | 'reel' | 'ad' | 'schema'
    copy_text TEXT,
    image_url TEXT,
    video_url TEXT,
    metadata JSONB,  -- Platform-specific data (hashtags, char count, dimensions)
    status TEXT NOT NULL DEFAULT 'draft',  -- 'draft' | 'approved' | 'published' | 'archived'
    approved_by TEXT,
    approved_at TIMESTAMP,
    published_at TIMESTAMP,
    analytics JSONB,  -- Engagement metrics from platform APIs
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_marketing_content_product ON marketing_content(product_id);
CREATE INDEX idx_marketing_content_platform_status ON marketing_content(platform, status);
CREATE INDEX idx_marketing_content_company ON marketing_content(company_id);

-- Product schema cache
CREATE TABLE product_schemas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    schema_type TEXT NOT NULL,  -- 'json-ld' | 'opengraph' | 'twitter-card'
    schema_json JSONB NOT NULL,
    validation_status TEXT,  -- 'valid' | 'invalid' | 'warnings'
    validation_errors JSONB,
    generated_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP  -- Cache expiry for regeneration
);

CREATE UNIQUE INDEX idx_product_schemas_product_type ON product_schemas(product_id, schema_type);

-- CSV upload tracking
CREATE TABLE csv_uploads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    file_path TEXT NOT NULL,  -- Supabase Storage path
    file_size INTEGER,
    row_count INTEGER,
    headers JSONB,  -- CSV column headers
    validation_status TEXT,  -- 'pending' | 'valid' | 'invalid'
    validation_errors JSONB,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP
);

CREATE INDEX idx_csv_uploads_company ON csv_uploads(company_id);
```

#### Extended Tables

```sql
-- Add marketing fields to products
ALTER TABLE products
ADD COLUMN seo_keywords TEXT[],
ADD COLUMN marketing_approved BOOLEAN DEFAULT FALSE,
ADD COLUMN marketing_notes TEXT,
ADD COLUMN featured BOOLEAN DEFAULT FALSE;

-- Add batch processing metadata
ALTER TABLE products
ADD COLUMN batch_id UUID REFERENCES bulk_jobs(id),
ADD COLUMN import_source TEXT;  -- 'whatsapp_single' | 'csv_bulk' | 'api'
```

### Integration Points

| Service | Purpose | Phase | API Documentation |
|---------|---------|-------|-------------------|
| **OpenAI DALL-E 3** | Marketing image generation | Phase 3 | https://platform.openai.com/docs/guides/images |
| **Supabase Storage** | CSV files, generated images | Phase 1 | https://supabase.com/docs/guides/storage |
| **LangSmith** | Tracing all workflows | All Phases | https://docs.smith.langchain.com |
| **Meta Graph API** | Instagram/Facebook posting | Phase 5 (Future) | https://developers.facebook.com/docs/graph-api |
| **Twitter API v2** | X/Twitter posting | Phase 5 (Future) | https://developer.twitter.com/en/docs/twitter-api |
| **YouTube Data API** | Shorts upload | Phase 6 (Future) | https://developers.google.com/youtube/v3 |

---

## Implementation Phases

### PHASE 1: Bulk Product Onboarding (Weeks 1-3)

**Goal:** Users can upload CSV with 50+ products and onboard entire catalog efficiently.

**Business Impact:** CRITICAL - Unblocks catalog growth, enables bulk inventory management.

#### New Components

**1. CSV Upload Handler (WhatsApp Integration)**
```python
# integrations/communication/whatsapp_webhook.py - add document handler
async def handle_document_message(message: dict):
    """Handle CSV upload from WhatsApp."""
    document = message.get("document", {})
    mime_type = document.get("mime_type")

    if mime_type != "text/csv":
        return await whatsapp_client.send_text(
            sender, "Please upload a CSV file (.csv)"
        )

    # Download from WhatsApp Media API
    media_url = await whatsapp_client.get_media_url(document["id"])
    csv_content = await download_media(media_url)

    # Upload to Supabase Storage
    storage_path = f"csv_uploads/{company_id}/{uuid4()}.csv"
    await supabase_storage.upload(storage_path, csv_content)

    # Trigger bulk processing workflow
    await trigger_bulk_catalog_workflow(sender, storage_path)
```

**2. Bulk Processing Specialist (NEW)**
```python
# specialists/bulk_processing_specialist.py
def create_bulk_processing_specialist(
    cataloging_tool: Tool,
    storage: StorageInterface,
    progress_callback: Callable[[int, int], None],
) -> Runnable:
    """
    Orchestrates batch cataloging from CSV.

    Responsibilities:
    - Parse CSV and validate schema
    - Batch products (10 at a time) to respect timeouts
    - Call cataloging specialist for each product
    - Track progress, handle errors, enable recovery
    - Generate final report (success/failures)
    """

    system_prompt = """You are the Bulk Processing Specialist.

    Parse CSV uploads, validate product data, and orchestrate batch cataloging.

    Process:
    1. Validate CSV headers match expected schema (name, description, price, sizes, colors)
    2. Batch rows into groups of 10 to respect execution timeouts
    3. For each product, invoke cataloging_specialist tool
    4. Track: total, processed, successful, failed
    5. Send progress updates every 5 products
    6. Generate final report with error details

    Error Handling:
    - Invalid CSV: Report schema errors immediately
    - Product failures: Log and continue (partial success)
    - Timeout: Resume from last successful batch

    Output: BulkJobReport with success/failure counts and error log.
    """

    return create_agent(
        llm=ChatAnthropic(model="claude-3-5-sonnet-20241022"),
        tools=[cataloging_tool, create_progress_tracker_tool(progress_callback)],
        prompt=system_prompt,
        output_schema=BulkJobReport,
    )
```

**3. Operations Department (NEW)**
```python
# departments/operations_department.py
def create_operations_department(
    storage: StorageInterface,
    checkpointer: BaseCheckpointSaver,
) -> CompiledGraph:
    """
    Operations Department handles bulk processing, validation, reporting.

    Specialists:
    - Bulk Processing Specialist (CSV → batch catalog)
    - Validation Specialist (schema validation, quality checks)
    - Reporting Specialist (job summaries, error reports)
    """

    tools = [
        create_bulk_cataloging_tool(storage),
        create_csv_validation_tool(),
        create_job_tracker_tool(storage),
    ]

    return create_agent(
        llm=ChatAnthropic(model="claude-3-5-sonnet-20241022"),
        tools=tools,
        prompt=load_prompt("departments/operations_department.prompt"),
        checkpointer=checkpointer,
    )
```

**4. Progress Tracking (WhatsApp Updates)**
```python
# tools/progress_tracker_tool.py
@tool("update_bulk_progress")
def update_bulk_progress(
    job_id: str,
    processed: int,
    total: int,
    latest_success: str | None = None,
    latest_error: str | None = None,
) -> str:
    """
    Update bulk job progress and send WhatsApp notification.

    Sends update every 5 products:
    "Processing products... 15/50 complete ✅
    Latest: Nike Air Max cataloged successfully"
    """
    storage.update_bulk_job(job_id, processed=processed)

    if processed % 5 == 0:  # Update every 5 products
        message = f"Processing products... {processed}/{total} complete ✅"
        if latest_success:
            message += f"\nLatest: {latest_success}"
        whatsapp_client.send_text(user_id, message)

    return f"Progress updated: {processed}/{total}"
```

#### Database Migrations

```sql
-- Migration: 001_bulk_processing.sql
CREATE TABLE bulk_jobs (...);  -- See Data Model section above
CREATE TABLE csv_uploads (...);
ALTER TABLE products ADD COLUMN batch_id UUID;
```

#### Testing Scenarios (Autonomous Framework)

```python
# tests/scenarios/bulk_onboarding.py
SCENARIOS = [
    {
        "name": "bulk_csv_3_products_valid",
        "input": "csv_uploads/test_3_products_valid.csv",
        "expected": {
            "total_items": 3,
            "successful_items": 3,
            "failed_items": 0,
            "status": "completed",
        },
    },
    {
        "name": "bulk_csv_10_products_mixed",
        "input": "csv_uploads/test_10_products_2_invalid.csv",
        "expected": {
            "total_items": 10,
            "successful_items": 8,
            "failed_items": 2,
            "status": "partial_success",
        },
    },
    {
        "name": "bulk_csv_invalid_schema",
        "input": "csv_uploads/test_missing_headers.csv",
        "expected": {
            "status": "failed",
            "error_type": "validation_error",
        },
    },
]
```

#### Success Criteria

- [ ] User uploads CSV with 50 products via WhatsApp
- [ ] System validates schema, sends confirmation
- [ ] Batch processes 10 products at a time
- [ ] Sends progress updates every 5 products
- [ ] Handles partial failures gracefully (continues processing)
- [ ] Final report shows: 45 successful, 5 failed with error details
- [ ] Failed products logged in `bulk_jobs.error_log` for manual review
- [ ] Autonomous tests pass for 3 scenarios above

**Estimated Effort:** 2-3 weeks
**Dependencies:** None (builds on existing cataloging workflow)

---

### PHASE 2: Website SEO Embeddings (Week 4)

**Goal:** Generate schema.org markup for all products → 40% CTR boost on search results.

**Business Impact:** HIGH - Quick win, proven 40% CTR improvement, low implementation complexity.

#### New Components

**1. SEO Specialist (NEW)**
```python
# specialists/seo_specialist.py
def create_seo_specialist(storage: StorageInterface) -> Runnable:
    """
    Generates JSON-LD schema.org Product markup for e-commerce SEO.

    Inputs: Product data from database
    Outputs: Valid JSON-LD Product schema with:
    - Product (name, description, image, brand)
    - Offer (price, availability, currency)
    - AggregateRating (if reviews exist)
    - Review (if reviews exist)

    Validation: Ensures compliance with schema.org spec + Google Rich Results requirements
    """

    system_prompt = """You are the SEO Specialist.

    Generate JSON-LD schema.org Product markup for e-commerce websites.

    Required fields:
    - @context: "https://schema.org"
    - @type: "Product"
    - name, description, image, brand
    - offers (Offer type with price, availability, priceCurrency)

    Optional (include if data exists):
    - aggregateRating (if reviews exist)
    - review (if reviews exist)
    - sku, gtin, mpn (if available)

    Validation:
    - All required fields present
    - Valid schema.org types
    - Passes Google Rich Results Test

    Output format: Valid JSON-LD string, copy-paste ready for <script type="application/ld+json">
    """

    return create_agent(
        llm=ChatAnthropic(model="claude-3-5-sonnet-20241022"),
        tools=[create_product_fetcher_tool(storage)],
        prompt=system_prompt,
        output_schema=ProductSchema,
    )
```

**2. Schema Generation Tool**
```python
# tools/seo_tools.py
@tool("generate_product_schema")
def generate_product_schema(
    product_id: str,
    *,
    storage: StorageInterface,
) -> dict[str, Any]:
    """
    Generate and validate JSON-LD Product schema.

    Returns:
    - schema_json: Ready-to-use JSON-LD markup
    - validation_status: 'valid' | 'invalid' | 'warnings'
    - validation_errors: List of issues (if any)
    """
    product = storage.get_product(product_id)

    schema_json = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product.name,
        "description": product.description,
        "image": product.images[0] if product.images else None,
        "brand": {"@type": "Brand", "name": product.brand or "Unknown"},
        "offers": {
            "@type": "Offer",
            "price": str(product.price),
            "priceCurrency": "INR",
            "availability": "https://schema.org/InStock",
        },
    }

    # Add ratings if exist
    if product.reviews:
        schema_json["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": product.average_rating,
            "reviewCount": len(product.reviews),
        }

    # Validate against schema.org spec
    validation_result = validate_schema(schema_json)

    # Store in cache
    storage.save_product_schema(product_id, "json-ld", schema_json, validation_result)

    return {
        "schema_json": json.dumps(schema_json, indent=2),
        "validation_status": validation_result.status,
        "validation_errors": validation_result.errors,
    }
```

**3. Batch Schema Generation**
```python
# workflows/batch_schema_generation.py
async def generate_schemas_for_all_products(company_id: str):
    """Generate JSON-LD schema for all products in catalog."""
    products = storage.list_products(company_id)

    job = storage.create_bulk_job(
        job_type="generate_schema",
        total_items=len(products),
    )

    for product in products:
        try:
            generate_product_schema(product.id)
            job.successful_items += 1
        except Exception as e:
            job.failed_items += 1
            job.error_log.append({"product_id": product.id, "error": str(e)})

        job.processed_items += 1
        storage.update_bulk_job(job)

    return job
```

#### User Experience

**Single Product:**
```
User: "Generate website code for Nike Air Max"
PM → SEO Specialist → Returns:

```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Nike Air Max",
  ...
}
```

Copy this code and paste into your website's <head> section.
Validation: ✅ Valid (Passes Google Rich Results Test)
```

**Batch (All Products):**
```
User: "Generate website codes for all my products"
PM → Operations Dept → SEO Specialist (for each product)
→ Progress updates every 10 products
→ Final: "Generated schemas for 50 products ✅ Download ZIP file: [link]"
```

#### Success Criteria

- [ ] Generate valid JSON-LD for any product
- [ ] Include all required fields (Product, Offer)
- [ ] Include optional fields when data exists (AggregateRating, Review)
- [ ] Validate against schema.org spec
- [ ] Pass Google Rich Results Test
- [ ] Batch generation for entire catalog
- [ ] User receives copy-paste ready code
- [ ] Autonomous tests validate schema compliance

**Estimated Effort:** 1 week
**Dependencies:** Phase 1 (bulk job infrastructure)

---

### PHASE 3: Social Media Content Generation (Weeks 5-8)

**Goal:** Generate platform-optimized marketing content (copy + images) for Instagram, Facebook, Twitter.

**Business Impact:** HIGH - Enables aggressive marketing, scales digital presence across platforms.

#### New Components

**1. Marketing Content Department (NEW)**
```python
# departments/marketing_content_department.py
def create_marketing_content_department(
    storage: StorageInterface,
    checkpointer: BaseCheckpointSaver,
) -> CompiledGraph:
    """
    Marketing Content Department generates platform-optimized content.

    Specialists:
    - Instagram Specialist (caption + lifestyle image)
    - Facebook Specialist (catalog description)
    - Twitter Specialist (280-char tweet + image)
    - Image Generation Specialist (DALL-E 3 integration)

    HITL: Batch approval for generated content before publishing.
    """

    tools = [
        create_instagram_content_tool(storage),
        create_facebook_content_tool(storage),
        create_twitter_content_tool(storage),
        create_image_generation_tool(),  # DALL-E 3
    ]

    middleware = [
        create_hitl_middleware(),  # Batch approval
        create_company_context_middleware(storage),
    ]

    return create_agent(
        llm=ChatAnthropic(model="claude-3-5-sonnet-20241022"),
        tools=tools,
        prompt=load_prompt("departments/marketing_content_department.prompt"),
        middleware=tuple(middleware),
        checkpointer=checkpointer,
    )
```

**2. Instagram Specialist**
```python
# specialists/instagram_specialist.py
def create_instagram_specialist(storage: StorageInterface) -> Runnable:
    """
    Generates Instagram post content optimized for engagement.

    Outputs:
    - Caption: 150-200 chars, 5-10 hashtags, emoji usage, CTA
    - Image prompt: DALL-E 3 prompt for lifestyle product photo
    - Metadata: Char count, hashtag list, optimal post time

    Brand Voice: Uses company_profile.brand_voice from context.
    Best Practices:
    - Front-load key message (first 125 chars visible)
    - Mix branded + trending hashtags
    - Include clear CTA (shop now, link in bio, tag a friend)
    - Lifestyle imagery over plain product shots
    """

    system_prompt = """You are the Instagram Specialist.

    Generate Instagram post content optimized for {company_profile.target_audience}.

    Caption Structure:
    - Hook (first line, emoji, intrigue)
    - Product benefit (2-3 sentences)
    - CTA (shop now, link in bio)
    - Hashtags (5-10, mix branded + trending)

    Image Prompt for DALL-E 3:
    "Lifestyle product photography of {product.name}, {describe scene},
    natural lighting, Instagram aesthetic, high quality, 4k"

    Constraints:
    - Max 2200 chars (Instagram limit)
    - Avoid spammy language (!!!, CLICK NOW)
    - Match brand voice: {company_profile.brand_voice}

    Output: InstagramContent with caption, image_prompt, hashtags[], metadata.
    """

    return create_agent(
        llm=ChatAnthropic(model="claude-3-5-sonnet-20241022"),
        tools=[],
        prompt=system_prompt,
        output_schema=InstagramContent,
    )
```

**3. Image Generation Tool (DALL-E 3)**
```python
# tools/image_generation_tool.py
from openai import OpenAI

@tool("generate_marketing_image")
def generate_marketing_image(
    prompt: str,
    product_name: str,
    style: str = "lifestyle",  # 'lifestyle' | 'product' | 'artistic'
    *,
    storage: StorageInterface,
) -> str:
    """
    Generate marketing image using DALL-E 3.

    Args:
    - prompt: Detailed DALL-E 3 prompt from specialist
    - product_name: For filename and metadata
    - style: Image style (lifestyle, product shot, artistic)

    Returns: Supabase Storage URL of generated image
    """
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # Generate image via DALL-E 3
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="hd",  # Higher quality for marketing
        n=1,
    )

    image_url = response.data[0].url

    # Download and upload to Supabase Storage
    image_data = download_image(image_url)
    storage_path = f"marketing_images/{uuid4()}.png"
    storage_url = storage.upload_file(storage_path, image_data)

    # Log generation metadata
    log_image_generation(
        product_name=product_name,
        prompt=prompt,
        storage_url=storage_url,
        model="dall-e-3",
    )

    return storage_url
```

**4. Facebook Specialist**
```python
# specialists/facebook_specialist.py
def create_facebook_specialist() -> Runnable:
    """
    Generates Facebook product catalog description.

    Outputs:
    - Description: 30-5000 chars, sentence case, product-focused
    - No company info, no links, no contact details (per Meta specs)
    - Match title and image

    Best Practices:
    - 30-5000 chars (Meta requirement)
    - Correct grammar, avoid excessive punctuation (!!!)
    - Product-only information (no shipping, company info)
    - Optimize for dynamic ad targeting
    """

    system_prompt = """You are the Facebook Specialist.

    Generate product catalog descriptions for Facebook/Meta dynamic ads.

    Meta Requirements (STRICT):
    - Length: 30-5000 characters
    - Grammar: Sentence case, proper punctuation
    - Content: Product details ONLY (no company info, shipping, links)
    - Avoid: Excessive punctuation (!!!), spam keywords
    - Match: Title and image must align with description

    Structure:
    - Product name and key feature (first sentence)
    - Detailed benefits (2-4 sentences)
    - Use cases or target audience fit
    - Specifications (materials, dimensions, care)

    Output: FacebookContent with description, char_count, metadata.
    """

    return create_agent(
        llm=ChatAnthropic(model="claude-3-5-sonnet-20241022"),
        tools=[],
        prompt=system_prompt,
        output_schema=FacebookContent,
    )
```

**5. Twitter Specialist**
```python
# specialists/twitter_specialist.py
def create_twitter_specialist() -> Runnable:
    """
    Generates Twitter/X post content optimized for engagement.

    Outputs:
    - Tweet: Max 280 chars, clear message, hashtags
    - Image prompt: DALL-E 3 prompt for eye-catching visual

    Best Practices:
    - Concise message (one clear idea)
    - Front-load key info (first 100 chars)
    - 1-3 hashtags (not excessive)
    - Strong visuals (images boost engagement 40%)
    - CTA or engagement hook (question, poll, link)
    """

    system_prompt = """You are the Twitter/X Specialist.

    Generate Twitter posts optimized for engagement and virality.

    Constraints:
    - Max 280 characters (STRICT)
    - One clear message per tweet
    - 1-3 relevant hashtags
    - Strong hook (first 100 chars)

    Structure:
    - Hook (question, stat, bold claim)
    - Product mention with benefit
    - CTA or hashtag

    Image Prompt for DALL-E 3:
    "Eye-catching product photo of {product.name}, bold composition,
    high contrast, Twitter feed optimized, 16:9 aspect ratio"

    Output: TwitterContent with tweet_text, char_count, hashtags[], image_prompt.
    """

    return create_agent(
        llm=ChatAnthropic(model="claude-3-5-sonnet-20241022"),
        tools=[],
        prompt=system_prompt,
        output_schema=TwitterContent,
    )
```

**6. Batch Marketing Generation Workflow**
```python
# workflows/batch_marketing_generation.py
async def generate_marketing_for_products(
    product_ids: list[str],
    platforms: list[str],  # ['instagram', 'facebook', 'twitter']
    hitl_mode: str = "batch_approval",  # 'batch_approval' | 'auto_approve'
) -> BulkJobReport:
    """
    Generate marketing content for multiple products across platforms.

    Process:
    1. For each product × platform:
       - Generate copy (specialist)
       - Generate image (DALL-E 3)
       - Store in marketing_content table
    2. Present batch for approval (if hitl_mode=batch_approval)
    3. Store approved content
    4. Report: total generated, approved, rejected
    """

    job = storage.create_bulk_job(
        job_type="generate_marketing",
        total_items=len(product_ids) * len(platforms),
    )

    generated_content = []

    for product_id in product_ids:
        product = storage.get_product(product_id)

        for platform in platforms:
            specialist = get_specialist_for_platform(platform)

            # Generate content
            content = specialist.invoke({"product": product})

            # Generate image
            image_url = generate_marketing_image(
                prompt=content.image_prompt,
                product_name=product.name,
            )

            # Store
            marketing_content_id = storage.save_marketing_content(
                product_id=product_id,
                platform=platform,
                copy_text=content.copy_text,
                image_url=image_url,
                metadata=content.metadata,
                status="draft",
            )

            generated_content.append(marketing_content_id)
            job.processed_items += 1
            storage.update_bulk_job(job)

    # HITL batch approval
    if hitl_mode == "batch_approval":
        approved_ids = await request_batch_approval(generated_content)
        for content_id in approved_ids:
            storage.update_marketing_content_status(content_id, "approved")
        job.successful_items = len(approved_ids)
    else:
        job.successful_items = job.processed_items

    return job
```

#### User Experience

**Single Product, Single Platform:**
```
User: "Create Instagram post for Nike Air Max"
PM → Marketing Dept → Instagram Specialist
→ Generates caption + image prompt
→ Calls DALL-E 3 to generate image
→ Presents for approval:

[Generated Image]
Caption: "Step into comfort with Nike Air Max 👟✨
Lightweight, breathable, and built for all-day wear.
Perfect for your active lifestyle.
Shop now! Link in bio 🔗
#NikeAirMax #Sneakers #ComfortFirst #ActiveLifestyle"

Approve? (yes/no/edit)
```

**Batch Generation (10 Products × 3 Platforms):**
```
User: "Generate marketing content for all my sneakers - Instagram, Facebook, and Twitter"
PM → Operations Dept → Marketing Dept (for each product/platform)
→ Progress: "Generating content... 5/30 complete"
→ Progress: "Generating content... 15/30 complete"
→ Progress: "Generating content... 30/30 complete ✅"
→ "Review generated content: [WhatsApp carousel with 30 items]
   Approve all? (yes/no/review individually)"
```

#### Data Schemas

```python
# schemas/marketing_content.py
class InstagramContent(BaseModel):
    caption: str = Field(max_length=2200, description="Instagram caption")
    image_prompt: str = Field(description="DALL-E 3 prompt for lifestyle image")
    hashtags: list[str] = Field(max_items=10, description="Relevant hashtags")
    char_count: int
    estimated_engagement_rate: float | None = None

class FacebookContent(BaseModel):
    description: str = Field(min_length=30, max_length=5000)
    char_count: int
    keywords: list[str] = Field(description="SEO keywords for ad targeting")

class TwitterContent(BaseModel):
    tweet_text: str = Field(max_length=280)
    image_prompt: str = Field(description="DALL-E 3 prompt for bold visual")
    hashtags: list[str] = Field(max_items=3)
    char_count: int

class MarketingContentResponse(BaseModel):
    platform: str
    content_id: str
    copy_text: str
    image_url: str
    metadata: dict
    status: str
```

#### Success Criteria

- [ ] Generate Instagram content (caption + DALL-E 3 image) for any product
- [ ] Generate Facebook catalog description (30-5000 chars, compliant with Meta specs)
- [ ] Generate Twitter post (≤280 chars, hashtags, DALL-E 3 image)
- [ ] Batch generation: 10 products × 3 platforms = 30 marketing assets
- [ ] HITL batch approval workflow functional
- [ ] All content stored in `marketing_content` table with proper metadata
- [ ] Images stored in Supabase Storage with CDN URLs
- [ ] Autonomous tests validate platform compliance (char limits, required fields)

**Estimated Effort:** 3-4 weeks
**Dependencies:** Phase 1 (bulk job infrastructure), DALL-E 3 API access

---

### PHASE 4: Batch Marketing at Scale (Week 9)

**Goal:** Generate marketing content for entire catalog (100+ products) efficiently.

**Business Impact:** MEDIUM - Operational efficiency, enables large-scale campaigns.

#### New Components

**1. Batch Marketing Specialist**
```python
# specialists/batch_marketing_specialist.py
def create_batch_marketing_specialist(
    marketing_dept: CompiledGraph,
    storage: StorageInterface,
) -> Runnable:
    """
    Orchestrates large-scale marketing content generation.

    Responsibilities:
    - Filter products (category, tags, featured status)
    - Determine platform mix (all platforms OR user-selected)
    - Batch in chunks (10 products at a time) to respect rate limits
    - Handle DALL-E 3 rate limits (50 images/minute)
    - Track progress, enable pause/resume
    - Generate campaign report
    """

    system_prompt = """You are the Batch Marketing Specialist.

    Orchestrate large-scale marketing content generation for product catalogs.

    Responsibilities:
    1. Parse user request (all products OR filtered by category/tags)
    2. Determine platforms (Instagram, Facebook, Twitter, OR user-specified)
    3. Calculate total tasks (products × platforms)
    4. Batch in chunks of 10 to respect timeouts and rate limits
    5. Monitor DALL-E 3 rate limits (50 images/min, pause if needed)
    6. Send progress updates every 10 items
    7. Handle errors (log and continue for partial success)
    8. Generate final campaign report

    Output: BatchMarketingReport with:
    - Total products processed
    - Content generated per platform
    - Images generated
    - Failures and error log
    - Estimated reach (based on follower counts)
    """

    return create_agent(
        llm=ChatAnthropic(model="claude-3-5-sonnet-20241022"),
        tools=[
            create_product_filter_tool(storage),
            create_marketing_batch_tool(marketing_dept),
            create_rate_limiter_tool(),  # DALL-E 3 throttling
        ],
        prompt=system_prompt,
        output_schema=BatchMarketingReport,
    )
```

**2. Rate Limiter Tool (DALL-E 3)**
```python
# tools/rate_limiter_tool.py
from collections import deque
from datetime import datetime, timedelta

class RateLimiter:
    """
    Rate limiter for DALL-E 3 API (50 images/minute).
    """
    def __init__(self, max_requests: int = 50, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()

    def acquire(self):
        """Wait if necessary to respect rate limit."""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.window_seconds)

        # Remove old requests outside window
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()

        # Wait if at limit
        if len(self.requests) >= self.max_requests:
            sleep_time = (self.requests[0] - cutoff).total_seconds()
            logger.info(f"Rate limit reached, waiting {sleep_time}s")
            time.sleep(sleep_time)
            self.requests.popleft()

        # Record this request
        self.requests.append(now)

@tool("check_rate_limit")
def check_rate_limit(service: str = "dalle3") -> dict:
    """Check if we can proceed or need to wait for rate limit."""
    limiter = get_rate_limiter(service)
    limiter.acquire()
    return {"status": "ok", "remaining": limiter.max_requests - len(limiter.requests)}
```

**3. Campaign Report Generator**
```python
# tools/campaign_report_tool.py
@tool("generate_campaign_report")
def generate_campaign_report(
    job_id: str,
    *,
    storage: StorageInterface,
) -> str:
    """
    Generate comprehensive campaign report for batch marketing job.

    Includes:
    - Total products processed
    - Content generated per platform (Instagram: 45, Facebook: 45, Twitter: 45)
    - Images generated (135 total)
    - Success/failure breakdown
    - Estimated reach (if analytics connected)
    - Next steps (review content, schedule posts)
    """
    job = storage.get_bulk_job(job_id)
    content = storage.list_marketing_content(
        filters={"batch_id": job_id},
        group_by="platform",
    )

    report = f"""
🎯 Campaign Generation Complete

📊 Summary:
- Products: {job.successful_items}/{job.total_items}
- Platforms: {", ".join(content.keys())}
- Images Generated: {sum(c.count for c in content.values())}
- Status: {job.status}

📈 Content Breakdown:
"""
    for platform, count in content.items():
        report += f"- {platform.title()}: {count} posts\n"

    if job.failed_items > 0:
        report += f"\n⚠️ Failures: {job.failed_items} (see error log)\n"

    report += "\n✅ Next Steps:\n"
    report += "1. Review generated content\n"
    report += "2. Approve batch for publishing\n"
    report += "3. Schedule posts or download for manual upload\n"

    return report
```

#### User Experience

```
User: "Generate marketing content for all my sneakers on Instagram and Twitter"

PM → Operations Dept → Batch Marketing Specialist

"Analyzing catalog... Found 50 sneakers
Platforms: Instagram, Twitter
Total tasks: 100 (50 products × 2 platforms)

Starting batch generation..."

[5 minutes later]
"Progress: 20/100 complete ✅
Latest: Nike Air Force 1 - Instagram + Twitter content generated"

[10 minutes later]
"Progress: 50/100 complete ✅
Rate limit pause (DALL-E 3) - resuming in 30s..."

[20 minutes later]
"Progress: 100/100 complete ✅

🎯 Campaign Generation Complete

📊 Summary:
- Products: 50/50
- Platforms: Instagram, Twitter
- Images Generated: 100
- Status: completed

📈 Content Breakdown:
- Instagram: 50 posts
- Twitter: 50 posts

✅ Next Steps:
1. Review generated content: [link to approval dashboard]
2. Approve batch for publishing
3. Schedule posts or download for manual upload"
```

#### Success Criteria

- [ ] Generate content for 50+ products across multiple platforms
- [ ] Handle DALL-E 3 rate limits gracefully (pause/resume)
- [ ] Send progress updates every 10 items
- [ ] Partial success handling (continue on individual failures)
- [ ] Generate comprehensive campaign report
- [ ] Enable batch approval (approve all, reject all, review individually)
- [ ] Autonomous tests validate 50-product batch

**Estimated Effort:** 1-2 weeks
**Dependencies:** Phase 3 (marketing content generation)

---

### PHASE 5: Platform Distribution (Weeks 10-16) [FUTURE]

**Goal:** Auto-post approved marketing content to Instagram, Facebook, Twitter.

**Business Impact:** MEDIUM - Convenience, automation (but requires complex API approvals).

**Status:** DEFERRED - Focus Phases 1-4 on content GENERATION first.

#### Challenges

1. **Meta Graph API Approval:**
   - Requires Facebook Business verification (2-4 weeks)
   - Instagram Business account + Facebook Page required
   - App Review process for `instagram_content_publish` permission
   - 25 posts/24h rate limit

2. **Twitter API Costs:**
   - Basic tier: $100/month (posting capability)
   - Need Twitter Developer account approval

3. **Complex Error Handling:**
   - Platform outages
   - Content policy violations (auto-rejection)
   - Rate limit management per platform

#### Components (When Implemented)

- **Platform Integration Specialists** (Instagram, Facebook, Twitter)
- **Scheduling System** (cron jobs or queue-based)
- **Publishing Status Tracker** (pending, published, failed)
- **Analytics Integration** (fetch engagement metrics post-publish)

**Recommendation:** Implement after Phases 1-4 prove content generation value. Users can manually upload generated content initially.

---

### PHASE 6: Video Content (YouTube Shorts) [FUTURE]

**Goal:** Generate YouTube Shorts (60s product videos).

**Business Impact:** HIGH potential (5.91% engagement), but VERY HIGH complexity.

**Status:** DEFERRED - Video generation requires different tech stack.

#### Challenges

1. **Video Generation Complexity:**
   - No native LangChain/OpenAI video generation
   - Need Runway ML, Pika Labs, or custom solution
   - Much more expensive than DALL-E 3 images ($6-10 per video)

2. **Content Creation:**
   - Requires video editing (transitions, text overlays, music)
   - Product demonstration scripting
   - Voice-over generation (ElevenLabs, etc.)

3. **YouTube API:**
   - OAuth flow for user authorization
   - Video upload (large file sizes)
   - Thumbnail generation
   - Metadata optimization (title, description, tags)

#### Recommended Approach (When Ready)

1. **Phase 6a:** Static image slideshow videos (simpler)
   - Use DALL-E 3 images + transitions
   - Text overlays for product info
   - Royalty-free music
   - Tools: `moviepy` or `ffmpeg`

2. **Phase 6b:** AI-generated video (advanced)
   - Integrate Runway ML or Pika
   - Product demonstration scripts
   - Voice-over narration
   - Full video editing pipeline

**Recommendation:** Defer until Phases 1-4 operational and generating revenue to fund video generation costs.

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| DALL-E 3 rate limits | Medium | Implement rate limiter, batch processing, pause/resume |
| DALL-E 3 costs ($0.04/image) | Medium | Start with single-platform, estimate costs upfront, HITL approval |
| CSV parsing errors | Low | Robust validation, clear error messages, test fixtures |
| Bulk job timeouts | Medium | Batch in chunks of 10, checkpoint progress, enable resume |
| Platform API changes | High (Phase 5) | Abstract platform clients, version API calls, monitor changelogs |
| Schema.org spec changes | Low | Validate on generation, periodic re-validation job |

### Business Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| User overwhelm (too much content) | Medium | Phased rollout, clear UI/UX, batch approval workflow |
| Generated content quality | High | HITL approval mandatory, A/B test prompts, user feedback loop |
| Platform policy violations | High (Phase 5) | Content moderation layer, policy compliance checks, manual review option |
| Cost overruns (DALL-E 3) | Medium | Usage tracking, cost alerts, user quotas, preview before generate |

### Architectural Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Data model complexity | Low | Follow existing patterns, document schemas, migration tooling (Alembic) |
| Middleware conflicts | Low | Test middleware combinations, clear precedence rules |
| Context overflow (long workflows) | Medium | Implement summarization middleware, strict context discipline |
| Testing coverage gaps | Medium | Autonomous testing framework, scenario-based tests, CI/CD integration |

---

## Success Metrics

### Phase 1 (Bulk Onboarding)
- **Operational:** 90%+ CSV uploads succeed without errors
- **Performance:** Process 50 products in <10 minutes
- **User Satisfaction:** Positive feedback on progress updates
- **Technical:** <5% error rate in batch processing

### Phase 2 (Schema Generation)
- **Quality:** 100% of schemas pass Google Rich Results Test
- **Coverage:** Schema generated for 100% of catalog
- **Impact:** Track CTR improvement (target 40% based on research)

### Phase 3 (Content Generation)
- **Quality:** 80%+ generated content approved by users
- **Compliance:** 100% compliance with platform specs (char limits, formats)
- **Cost:** DALL-E 3 costs <$0.10 per product per platform
- **User Satisfaction:** Positive feedback on content quality

### Phase 4 (Batch Marketing)
- **Scale:** Generate content for 100+ products without failures
- **Performance:** <30 minutes for 50 products × 3 platforms
- **Rate Limits:** Zero DALL-E 3 rate limit errors (graceful handling)

---

## Resource Requirements

### Development Team
- **Phase 1:** 1 engineer, 2-3 weeks
- **Phase 2:** 1 engineer, 1 week
- **Phase 3:** 1-2 engineers, 3-4 weeks
- **Phase 4:** 1 engineer, 1-2 weeks
- **Total:** ~8-10 weeks engineering time

### Infrastructure
- **Supabase Storage:** ~$5/month (10GB for images/CSVs)
- **OpenAI API (DALL-E 3):** $0.04/image × volume
  - Example: 100 products × 3 platforms = 300 images = $12
- **PostgreSQL:** Existing (no additional cost)
- **LangSmith:** Existing (covered by usage tier)

### API Access
- ✅ OpenAI API (DALL-E 3) - Available
- ✅ Supabase Storage - Available
- 🔜 Meta Graph API - Approval needed (Phase 5)
- 🔜 Twitter API - $100/month (Phase 5)
- 🔜 YouTube API - Free tier available (Phase 6)

---

## Next Steps (Week 1)

### Immediate Actions

1. **Review & Approve Roadmap**
   - Stakeholder alignment on priorities
   - Confirm Phase 1-4 sequence
   - Budget approval for DALL-E 3 costs

2. **Design Phase 1 Architecture**
   - Create `docs/architecture/workflows/BULK_ONBOARDING_WORKFLOW.md`
   - Detailed component design (CSV parser, bulk specialist, progress tracker)
   - Database migration scripts

3. **Prototype CSV Upload**
   - WhatsApp document handler
   - Supabase Storage integration
   - Basic validation

4. **DALL-E 3 API Testing**
   - Generate test images
   - Validate prompt engineering
   - Measure costs and quality

5. **Update Autonomous Testing Framework**
   - Add bulk onboarding scenarios
   - CSV test fixtures (valid, invalid, mixed)
   - Extend testing tools for batch jobs

### Decision Points

**Before Phase 1 Implementation:**
- [ ] CSV schema finalized (required columns, optional columns)
- [ ] Batch size confirmed (10 products recommended)
- [ ] Progress update frequency (every 5 products recommended)
- [ ] HITL mode: per-product OR batch approval?

**Before Phase 3 Implementation:**
- [ ] Platform priority (all 3 OR start with 1-2?)
- [ ] DALL-E 3 budget limit per user/company
- [ ] Image style preferences (lifestyle vs product shots)
- [ ] Brand voice documentation complete

---

## Appendix

### CSV Schema Specification (Phase 1)

**Required Columns:**
- `name` (TEXT, max 200 chars)
- `description` (TEXT, min 50 chars)
- `price` (DECIMAL, positive)
- `category` (TEXT, from predefined list)

**Optional Columns:**
- `brand` (TEXT)
- `sizes` (TEXT, comma-separated: "S,M,L,XL")
- `colors` (TEXT, comma-separated: "Red,Blue,Green")
- `materials` (TEXT)
- `sku` (TEXT, unique)
- `stock_quantity` (INTEGER)
- `images` (TEXT, comma-separated URLs)
- `tags` (TEXT, comma-separated: "featured,sale,new")

**Validation Rules:**
- Price: Must be positive decimal
- Category: Must exist in company's category list
- Sizes/Colors: Must be valid values from predefined options
- Images: Must be valid URLs or empty

**Error Handling:**
- Invalid row: Log error, skip row, continue processing
- Missing required field: Log error, skip row
- Invalid data type: Log error, attempt coercion, skip if fails

### Platform Content Specifications Summary

| Platform | Copy Length | Image Format | Key Requirements |
|----------|-------------|--------------|------------------|
| Instagram | 2200 chars max | JPEG <8MB, 1080×1080 or 1080×1350 | Hashtags (5-10), emoji usage, CTA |
| Facebook | 30-5000 chars | JPEG/PNG <8MB | Product-only content, proper grammar, no spam |
| Twitter | 280 chars max | JPEG/PNG, 16:9 or 1:1 | Concise message, 1-3 hashtags, strong visuals |
| YouTube Shorts | Title + description | 9:16 vertical video, 60s | Engaging hook, product demo, CTA |
| Website | Schema.org | JSON-LD | Required: Product, Offer; Optional: Rating, Review |

### Estimated Costs (50 Products)

**Phase 1 (Bulk Onboarding):**
- Development: $0 (internal)
- Infrastructure: $0 (existing Supabase)
- Total: $0

**Phase 2 (Schema Generation):**
- Development: $0 (internal)
- Infrastructure: $0 (JSON generation)
- Total: $0

**Phase 3 (Content Generation - 3 Platforms):**
- Development: $0 (internal)
- DALL-E 3: 50 products × 3 platforms × $0.04 = $6
- Infrastructure: $1 (Supabase Storage for images)
- Total: **$7 per batch**

**Phase 4 (Batch Marketing):**
- Same as Phase 3, scaled to volume
- 100 products × 3 platforms = $12

**Ongoing (Per Month):**
- Supabase Storage: ~$5/month
- DALL-E 3: Variable (depends on content generation volume)
- Estimated: $20-50/month for moderate usage

---

**Last Updated:** 2025-10-23
**Review Cadence:** Bi-weekly sprint planning
**Owner:** Product & Engineering Team
**Status:** Ready for stakeholder review & approval
