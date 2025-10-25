# Platform API Research & Architectural Analysis

**Date:** 2025-10-25
**Purpose:** Comprehensive analysis of major advertising platform APIs for AutifyME marketing domain
**Status:** Research Complete - Ready for Architectural Discussion

---

## Executive Summary

This document presents findings from deep research into 8 major advertising platforms and their APIs. The analysis reveals **both surprising commonalities and critical differences** that will shape AutifyME's marketing architecture.

**Platforms Analyzed:**
1. Meta (Facebook + Instagram)
2. Google Ads
3. YouTube
4. X (Twitter)
5. LinkedIn
6. Amazon Advertising
7. TikTok For Business
8. WhatsApp Business (already integrated)

**Key Finding:** While all platforms follow OAuth 2.0 and REST patterns, their **campaign hierarchies, rate limiting strategies, and webhook capabilities differ dramatically**. A naive "one adapter per platform" approach will fail - we need intelligent abstraction layers.

---

## Platform-by-Platform Deep Dive

### 1. Meta Marketing API (Facebook + Instagram)

**Official Docs:** developers.facebook.com/docs/marketing-api

**Authentication:**
- OAuth 2.0 with System Users (permanent tokens for automation)
- Access tokens scoped to ad accounts
- Business Manager required for multi-account management
- Token expiration: 60 days (refreshable)

**Campaign Hierarchy:**
```
Ad Account
  └─ Campaign (objective, budget type)
      └─ Ad Set (targeting, placement, schedule, bid)
          └─ Ad (creative, copy, CTA)
```

**Key Objects:**
- Campaign: Defines objective (awareness, traffic, conversions, etc.)
- Ad Set: Targeting parameters, placement (Facebook, Instagram, Messenger, Audience Network), budget
- Ad: Creative (image, video, carousel), copy, CTA button
- Creative: Images, videos uploaded separately, referenced by ads

**2025 Major Update (Q1 2026 Breaking Change):**
- Advantage+ campaigns becoming mandatory
- Smart_promotion_type flag deprecated
- Campaigns auto-enter Advantage+ when using AI automation (budget, audience, placement)
- Legacy manual campaign APIs will be phased out

**Rate Limiting:**
- CPU time-based throttling (not simple request count)
- total_cputime metric tracks processing cost
- When total_cputime reaches 100, throttling begins
- Best practice: Batch operations, exponential backoff, monitor response headers
- Multiple ad accounts should split across connections to avoid overwhelming quota

**Webhooks & Events:**
- **Conversions API (CAPI)** - Server-side conversion tracking
- Real-time webhook subscriptions for:
  - Lead ads (instant form submissions)
  - Page changes
  - Instagram @mentions
  - Messenger messages
- Webhooks require HTTPS endpoint verification

**Metrics Available:**
- Impressions, reach, frequency
- Clicks, CTR, CPC
- Conversions, CPA, ROAS
- Video views, engagement
- Platform-specific: Instagram story exits, saves, shares

**Critical Considerations:**
- **Advantage+ AI is the future** - our system must support automated targeting (less manual control)
- **Multi-platform** - Single API manages Facebook, Instagram, Messenger, Audience Network
- **Creative management** - Separate upload flow before ad creation
- **Conversion tracking** - Must implement Conversions API for accurate attribution

---

### 2. Google Ads API

**Official Docs:** developers.google.com/google-ads/api

**Authentication:**
- OAuth 2.0 (required)
- Developer token (application-level credential)
- Manager account + individual customer accounts
- API access requires manager account structure

**Campaign Hierarchy:**
```
Customer (account)
  └─ Campaign (type, budget, bidding strategy)
      └─ Ad Group (targeting, bids)
          └─ Ad (creative)
      OR
      └─ Asset Group (for Performance Max)
          └─ Assets (images, videos, headlines, descriptions)
```

**Three Campaign Models:**
1. **Traditional:** Campaign → Ad Group → Ads (Search, Display, Video)
2. **Performance Max:** Campaign → Asset Group → Assets (AI-driven, all placements)
3. **Hybrid:** Mix of both depending on AdvertisingChannelType

**Key Objects:**
- Customer: Google Ads account (can nest up to 6 levels deep via Manager accounts)
- Campaign: Budget, bidding strategy, channel type (Search, Display, Video, Shopping, Performance Max)
- Ad Group: Keywords, audiences, demographics, bids
- Asset: Images, videos, headlines, descriptions (for responsive/Performance Max ads)

**Rate Limiting:**
- Operation-based quota (not time-based)
- Different operations cost different amounts
- Manager account operations aggregate across all child accounts
- Quota increases available via support request

**Webhooks & Events:**
- **No native webhooks** - must poll for changes
- Google Analytics 4 events can be sent to Google Ads for conversion tracking
- Change history API available for auditing

**Metrics Available:**
- Impressions, clicks, CTR, CPC
- Conversions, conversion rate, CPA
- ROAS, conversion value
- Quality Score, Ad Rank
- Search impression share, top impression share

**Critical Considerations:**
- **No webhook support** - requires polling for status updates
- **Complex hierarchy** - Manager accounts can nest 6 levels deep
- **Performance Max** - Black box AI campaigns (limited control, high performance)
- **Keyword management** - Search campaigns require keyword strategy
- **Asset-based creativity** - Responsive ads need multiple asset variations

---

### 3. YouTube Data API

**Official Docs:** developers.google.com/youtube/v3

**Authentication:**
- OAuth 2.0 for user-owned content
- API key for public data access
- Channel ownership verification required for uploads

**Quota System (Strict):**
- Default: 10,000 units/day
- Read operation: 1 unit
- Write operation: 50 units
- Search: 100 units
- **Video upload: 1,600 units** (only 6 videos/day with default quota!)
- Quota increase requires compliance audit

**Key Operations:**
- Video upload (MP4, MOV, AVI up to 256GB)
- Video metadata management (title, description, tags, category)
- Playlist management
- Comment management
- Analytics API (separate, no quota cost)

**Rate Limiting:**
- Strict daily quota (10,000 units)
- No hourly/minute limits
- Must request increase for high-volume use cases
- Audit required for quota > 10,000

**Metrics Available (via YouTube Analytics API):**
- Views, watch time, average view duration
- Subscribers gained/lost
- Likes, dislikes, comments, shares
- Traffic sources, demographics
- Revenue (for monetized channels)

**Critical Considerations:**
- **Extremely limited quota** - 6 videos/day is restrictive for automation
- **Separate from Google Ads** - YouTube ads managed via Google Ads API, not YouTube Data API
- **Upload time** - Large videos take significant time, must handle async
- **Content ID** - Copyright claims can block monetization

---

### 4. X (Twitter) Ads API

**Official Docs:** developer.twitter.com/en/docs/twitter-ads-api

**Authentication:**
- OAuth 2.0 (3-legged flow) or PIN-based OAuth (for non-web apps)
- X Premium subscription required for API access
- Account-level permissions (5 roles: Admin, Ad Manager, Campaign Analyst, Organic Analyst, Creative Manager)

**Campaign Hierarchy:**
```
Ads Account
  └─ Campaign (funding, objective)
      └─ Line Item (targeting, bid, budget, schedule)
          └─ Promoted Post (organic post promoted as ad)
```

**Key Objects:**
- Campaign: Funding source, objective (awareness, consideration, conversion)
- Line Item: Targeting (interests, keywords, followers, demographics), placement, bid strategy
- Promoted Post: Organic post (must exist first) linked to line item for promotion
- Card: Interactive media (image, video, app install, website) attached to posts

**Rate Limiting:**
- Not explicitly documented in search results
- Likely similar to organic API (15-min windows, varying limits per endpoint)

**Organic vs Paid:**
- **Organic:** Post creation via Twitter API v2 (separate from Ads API)
- **Paid:** Ads API promotes existing organic posts
- **Metrics:** Organic metrics available for 30 days only (requires OAuth user context)

**Metrics Available:**
- Impressions, engagements, engagement rate
- Clicks, CTR
- Follows, unfollows
- Video views, completion rate
- App installs, website conversions

**Critical Considerations:**
- **Premium subscription required** - Ad access tied to X Premium
- **Organic post first** - Cannot create ad-only content, must promote existing posts
- **30-day metrics limit** - Organic analytics expire after 30 days
- **User permissions** - Must check permissions API to determine access level

---

### 5. LinkedIn Marketing API

**Official Docs:** learn.microsoft.com/en-us/linkedin/marketing

**Authentication:**
- OAuth 2.0
- Scopes: r_basicprofile, r_ads (read), rw_ads (read/write)
- Campaign Manager ad account required
- Direct access token generation from Campaign Manager (2025 update)

**Campaign Hierarchy:**
```
Ad Account
  └─ Campaign Group (budget pool, shared across campaigns)
      └─ Campaign (objective, targeting, schedule, bid)
          └─ Creative (content + format)
```

**Key Objects:**
- Campaign Group: Budget pool shared across multiple campaigns
- Campaign: Targeting (job title, function, seniority, company, industry, skills), objective, bid strategy
- Creative: Sponsored Content (feed posts), Sponsored InMail (direct messages), Text Ads, Dynamic Ads
- Content: Organic posts that can be boosted to Sponsored Content

**Sponsored Content Types:**
- Single image
- Video
- Carousel (multiple images/videos)
- Event ads
- Document ads (native PDF/PPT viewer)

**Rate Limiting:**
- Not explicitly detailed in search results
- Likely per-account throttling

**Metrics Available:**
- Impressions, clicks, CTR
- Leads (LinkedIn Lead Gen Forms)
- Engagement (likes, comments, shares, follows)
- Video views, completion rate
- Demographics (job function, seniority, company, industry)

**API Version Management:**
- Marketing API v202410 sunset (October 2024)
- Must migrate to latest versioned APIs to avoid disruptions
- Breaking changes announced with deprecation timelines

**Critical Considerations:**
- **B2B focus** - Targeting by professional attributes (job title, company, seniority)
- **Lead Gen Forms** - Native LinkedIn forms for lead capture (high conversion)
- **Campaign Groups** - Budget pooling across campaigns (unique hierarchy)
- **Boost organic posts** - Can promote existing company page posts
- **Versioned API** - Must track version deprecations

---

### 6. Amazon Advertising API

**Official Docs:** advertising.amazon.com/API/docs

**Authentication:**
- OAuth 2.0
- Requires Amazon seller or vendor account
- Eligibility approval via developer portal
- Region-specific endpoints (US: advertising-api.amazon.com)

**Ad Types:**
1. **Sponsored Products** (PPC, keyword-targeted)
2. **Sponsored Brands** (headline ads, brand awareness)
3. **Sponsored Display** (retargeting, audience-based)
4. **DSP (Demand-Side Platform)** (programmatic, off-Amazon inventory)

**Campaign Hierarchy (Sponsored Products v3):**
```
Ad Account
  └─ Campaign (targeting type: auto vs manual, budget, start/end date)
      └─ Ad Group (bids)
          └─ Product Ads (individual ASINs)
          └─ Targeting (keywords or product targets)
```

**Key Objects:**
- Campaign: Daily budget, targeting type (automatic or manual keyword), placement (top of search, product pages, rest of search)
- Ad Group: Default bid, product selection
- Product Ad: Links to specific ASIN (Amazon product ID)
- Keyword/Product Target: For manual campaigns (keyword bidding or product targeting)

**Rate Limiting:**
- Request throttling (not quota-based)
- Batch operations available (create/modify multiple entities in single request)

**Metrics Available:**
- Impressions, clicks, CTR
- Spend, CPC
- Sales, ACOS (Advertising Cost of Sales - Amazon's version of ROAS)
- Orders, units sold
- Conversion rate

**Data Formats:**
- Supports JSON and XML
- REST API

**Critical Considerations:**
- **E-commerce focused** - Only for Amazon sellers/vendors promoting Amazon products
- **ASIN-based** - Ads tied to Amazon product catalog (ASINs)
- **ACOS metric** - Amazon's proprietary efficiency metric (spend ÷ sales)
- **Keyword vs Product targeting** - Manual campaigns support both
- **Automatic targeting** - Amazon's AI selects keywords/products

---

### 7. TikTok For Business API

**Official Docs:** business-api.tiktok.com

**Authentication:**
- OAuth 2.0
- Scopes: Ads Management, Reporting, Creator Marketplace
- Access tokens via auth_code from advertisers

**Campaign Hierarchy:**
```
Advertiser Account
  └─ Campaign (objective, budget type)
      └─ Ad Group (placement, targeting, budget, schedule, bid)
          └─ Ad (creative, identity, tracking)
```

**Key Objects:**
- Campaign: Advertising objective (reach, traffic, app installs, video views, conversions), budget type (daily, lifetime, no limit)
- Ad Group: Placement (TikTok, audience network, global apps), targeting (age, gender, location, interests, devices), bid strategy
- Ad: Video creative, ad text, CTA, tracking URL, TikTok Page/App identity
- Creative: Videos, images uploaded to creative library

**Creative Management:**
- Consolidated creative library
- Upload images, videos, manage all assets in one place
- Holistic creative reporting

**Webhooks:**
- Lead ad webhooks (instant lead notifications)
- Ad review status webhooks
- Creator Marketplace order webhooks

**Events API:**
- Server-side conversion tracking (similar to Meta CAPI)
- Supports web, app, offline conversions
- Payload converter available (auto-converts from Meta CAPI format)

**SDK Support:**
- Python, Java, JavaScript SDKs
- Official TikTok Business API SDK on GitHub

**Rate Limiting:**
- Not explicitly documented in search results
- Likely per-account throttling

**Metrics Available:**
- Impressions, reach, frequency
- Clicks, CTR, CPC
- Video views, view rate, average watch time
- Conversions, CPA, ROAS
- Engagement (likes, comments, shares)

**2025 Compliance Update:**
- EU advertisers must confirm politics/elections compliance by Jan 10, 2026
- Non-compliant advertisers blocked from API campaign management

**Critical Considerations:**
- **Video-first** - TikTok creative is primarily short-form video
- **Events API** - Server-side tracking critical for iOS 14+ attribution
- **Payload converter** - Easy migration from Meta CAPI
- **Creator Marketplace** - Influencer partnerships via API
- **EU compliance** - Political ad restrictions

---

### 8. WhatsApp Business API (Already Integrated)

**Status:** Currently integrated in AutifyME for 2-way messaging

**Current Capabilities:**
- Send/receive text messages
- Send/receive media (images, videos, documents)
- Interactive messages (buttons, lists)
- Message templates (pre-approved for marketing)

**Potential Marketing Enhancements:**
- **WhatsApp Business Platform API:** Catalog integration (product catalog in-chat)
- **Marketing messages:** Template messages for campaigns (limited frequency, opt-in required)
- **Click-to-WhatsApp ads:** Ads on Facebook/Instagram that open WhatsApp conversation
- **Shopping features:** Product catalog browsing, cart, checkout in WhatsApp

**Rate Limiting:**
- Tiered messaging limits based on phone number status (verified, quality)
- 24-hour customer service window (free messages)
- Template messages (paid) can be sent outside 24h window

**Critical Considerations:**
- **Opt-in required** - Cannot send marketing without user permission
- **Template approval** - Marketing messages must use pre-approved templates
- **Quality rating** - Poor quality (blocks, reports) reduces sending limits
- **Integration with Meta ads** - Click-to-WhatsApp ads managed via Meta Marketing API

---

## Cross-Platform Analysis

### Authentication Patterns

**Common Pattern: OAuth 2.0**
- All platforms use OAuth 2.0 for user authorization
- Most support permanent tokens for automation (Meta System Users, LinkedIn direct tokens)
- All require platform-specific app registration

**Divergence:**
- **Google Ads:** Requires manager account + developer token (application-level)
- **X/Twitter:** Requires X Premium subscription for ad access
- **Amazon:** Requires seller/vendor account approval

**Architectural Implication:**
- Unified OAuth flow handler
- Platform-specific credential storage (tokens, refresh tokens, developer tokens, account IDs)
- Token refresh automation (60-day expiration for Meta, etc.)

---

### Campaign Hierarchy Comparison

**Three Hierarchy Patterns:**

**1. Three-Level (Meta, Google traditional, TikTok, X, Amazon):**
```
Account → Campaign → Ad Set/Ad Group → Ad
```

**2. Four-Level (LinkedIn):**
```
Account → Campaign Group → Campaign → Creative
```

**3. Asset-Based (Google Performance Max):**
```
Account → Campaign → Asset Group → Assets
```

**Common Elements:**
- **Campaign level:** Objective, budget type
- **Targeting level:** Audience, placement, bid (Ad Set / Ad Group / Line Item)
- **Creative level:** Actual ad content (Ad / Creative / Promoted Post)

**Divergence:**
- LinkedIn's Campaign Groups (budget pooling)
- Google's Asset Groups (AI-driven creativity)
- X's promoted posts (must be organic first)
- Amazon's ASIN-based ads (product catalog dependency)

**Architectural Implication:**
- Abstract campaign hierarchy into generic model
- Map generic model to platform-specific structure
- Support both manual (traditional) and AI-driven (Advantage+, Performance Max) campaigns

---

### Rate Limiting Strategies

**Four Distinct Approaches:**

**1. CPU Time-Based (Meta):**
- Tracks processing cost, not request count
- total_cputime metric determines throttling
- Batch operations reduce CPU time

**2. Daily Quota (YouTube):**
- Fixed daily quota (10,000 units)
- Different operations cost different units
- Video upload = 1,600 units (only 6/day!)

**3. Request Throttling (Amazon, TikTok, LinkedIn):**
- Per-account throttling (limits not publicly documented)
- Batch operations available
- Exponential backoff recommended

**4. Operation-Based (Google Ads):**
- Quota per operation type
- Manager accounts aggregate child quotas
- Quota increase via support request

**Common Best Practices (applies to all):**
- Exponential backoff with jitter
- Batch operations when available
- Monitor response headers for rate limit indicators
- Distribute load across time (avoid peak hours)
- Split high-volume accounts across connections

**Architectural Implication:**
- Platform-specific rate limit tracking (database table: platform_rate_limits)
- Intelligent request queue with priority and throttling
- Retry logic with exponential backoff
- Quota monitoring and alerting

---

### Webhook & Event Support

**Two Categories:**

**1. Conversion/Event Tracking (Server-Side):**
- **Meta:** Conversions API (CAPI)
- **TikTok:** Events API (compatible with Meta CAPI payload)
- **Google:** Google Analytics 4 → Google Ads event import
- **Purpose:** Track conversions server-side (iOS 14+ privacy, accuracy)

**2. Real-Time Webhooks:**
- **Meta:** Lead ads, page changes, Instagram mentions, Messenger
- **TikTok:** Lead ads, ad review status, Creator Marketplace
- **X, LinkedIn, Amazon, YouTube:** No native webhook support

**Architectural Implication:**
- Implement Conversions API for Meta, TikTok (critical for attribution)
- Build webhook receiver endpoint (HTTPS, verification, signature validation)
- Event queue for processing asynchronous events
- Polling service for platforms without webhooks (Google Ads, X, LinkedIn, Amazon)

---

### Metrics Normalization Challenge

**Common Metrics (all platforms):**
- Impressions
- Clicks
- CTR (Click-Through Rate)
- Spend

**Platform-Specific Metrics:**
- **Meta:** Reach, Frequency, Engagement
- **Google Ads:** Quality Score, Ad Rank, Impression Share
- **Amazon:** ACOS (Advertising Cost of Sales), Units Sold
- **TikTok:** Video Views, Average Watch Time, Engagement (likes/comments/shares)
- **LinkedIn:** Leads (native forms), Demographics (job function, seniority)
- **X:** Engagements, Follows, Post Engagements
- **YouTube:** Watch Time, Average View Duration, Subscribers Gained

**Conversion Metrics (different names, same concept):**
- **CPA:** Cost Per Acquisition (Meta, Google, TikTok, LinkedIn)
- **ACOS:** Advertising Cost of Sales (Amazon) = Spend ÷ Sales (inverse of ROAS)
- **ROAS:** Return on Ad Spend (Meta, Google, TikTok) = Revenue ÷ Spend

**Architectural Implication:**
- Normalize metrics into common schema (impressions, clicks, conversions, spend, revenue)
- Store platform-specific metrics separately (platform_metrics JSONB column)
- Calculate derived metrics uniformly (CTR, CPA, ROAS, ACOS)
- Support cross-platform aggregated reporting

---

## Critical Architectural Decisions

### Decision 1: Abstraction Layer Strategy

**Options:**

**A. Thin Adapter Pattern (naive)**
- One adapter per platform
- Minimal abstraction
- ❌ **Problem:** Leaks platform-specific concepts into core domain

**B. Thick Abstraction Layer (recommended)**
- Generic campaign model (objective, budget, targeting, creative)
- Platform adapters map generic → platform-specific
- Core domain works with generic model only
- ✅ **Benefit:** Platform changes isolated to adapters

**C. Hybrid (best for complex scenarios)**
- Generic model for common operations (90% use cases)
- Platform-specific extensions for advanced features (Advantage+, Performance Max, LinkedIn Lead Forms)
- ✅ **Benefit:** Flexibility + abstraction

**Recommendation:** **Hybrid approach**
- Start with generic campaign model
- Support platform-specific configurations via JSONB fields
- Specialists understand generic model, adapters translate

---

### Decision 2: Credential Management

**Challenges:**
- OAuth tokens expire (Meta: 60 days, others vary)
- Multiple ad accounts per platform
- Refresh tokens, developer tokens, API keys
- Secure storage requirements

**Recommendation:**
- **Table:** platform_credentials
  - platform (facebook, google, linkedin, etc.)
  - account_id (ad account ID)
  - credential_type (oauth_token, refresh_token, developer_token, api_key)
  - credential_value (encrypted)
  - expires_at
  - created_at, updated_at
- **Encryption:** Database-level encryption for credential_value
- **Auto-refresh:** Scheduled job to refresh expiring tokens
- **Monitoring:** Alert on refresh failures

---

### Decision 3: Campaign Lifecycle Management

**Challenges:**
- Campaigns have multiple states (draft, pending review, active, paused, completed)
- Platform review times vary (instant to 24 hours)
- Async operations (campaign creation, creative upload)

**Recommendation:**
- **State machine:** campaigns.status with well-defined transitions
- **Platform sync status:** campaigns.platform_sync_status (not_synced, syncing, synced, failed)
- **Platform IDs:** campaign_channels.platform_campaign_id (stores external IDs)
- **Polling service:** For platforms without webhooks (Google, X, LinkedIn, Amazon)
- **Webhook receiver:** For platforms with webhooks (Meta, TikTok)

---

### Decision 4: Creative/Asset Management

**Challenges:**
- Different platforms support different formats (image, video, carousel, document)
- File size limits vary
- Upload APIs differ
- Creative must be uploaded before ad creation on most platforms

**Recommendation:**
- **Unified creative library:** campaign_assets table (already designed)
- **Format validation:** Per-platform validators
- **Asset optimization:** Resize/compress automatically to meet platform requirements
- **Pre-upload workflow:**
  1. Visual Assets Specialist selects/organizes assets
  2. PM validates against platform requirements
  3. Upload to AutifyME storage (S3/Supabase Storage)
  4. Platform adapters upload to platform on campaign creation
  5. Store platform creative IDs in campaign_assets.platform_metadata (JSONB)

---

### Decision 5: Metrics Collection & Normalization

**Challenges:**
- Metrics APIs vary (some real-time, some delayed 24-48 hours)
- Different metric names for same concepts
- Platform-specific metrics not available elsewhere

**Recommendation:**
- **Two-table strategy:**
  1. **campaign_performance:** Normalized metrics (impressions, clicks, spend, conversions, revenue)
  2. **campaign_performance_raw:** Platform-specific metrics (JSONB)
- **ETL pipeline:**
  - Fetch metrics from platform APIs (daily job)
  - Normalize into common schema
  - Store raw platform data for auditing
- **Aggregation levels:**
  - Campaign level
  - Ad Set/Ad Group level
  - Ad/Creative level
- **Time series:** Metrics snapshots daily (campaign_performance_snapshots)

---

### Decision 6: Rate Limit Management

**Challenges:**
- Different platforms use different rate limiting strategies
- Must avoid hitting limits (delays campaign launches)
- Multi-tenant scenario (future): Multiple companies sharing API quotas

**Recommendation:**
- **Table:** platform_rate_limits
  - platform
  - account_id
  - limit_type (daily_quota, hourly_requests, cpu_time)
  - current_usage
  - limit_max
  - reset_at
  - updated_at
- **Request queue:** Priority queue for API requests
- **Throttling logic:** Check rate limits before API calls
- **Backoff strategy:** Exponential backoff on 429 responses
- **Monitoring:** Alert when approaching limits (80% threshold)

---

### Decision 7: Error Handling & Retry

**Challenges:**
- Transient errors (network, platform downtime)
- Permanent errors (invalid credentials, policy violations)
- Partial failures (batch operations)

**Recommendation:**
- **Error classification:**
  - Retryable: 429 (rate limit), 500 (server error), network timeouts
  - Non-retryable: 401 (auth), 403 (forbidden), 400 (validation), policy violations
- **Retry strategy:** Tenacity with exponential backoff (already in use for storage)
- **Error logging:** platform_api_errors table
  - platform, operation, error_type, error_message, request_payload, response_payload, created_at
- **User notification:** Surface non-retryable errors to user via HITL

---

## Architectural Components

### Component 1: Platform Abstraction Layer

**Purpose:** Isolate platform-specific logic from core domain

**Structure:**
```
core/platform_adapters/
  ├─ base.py (AbstractPlatformAdapter interface)
  ├─ meta_adapter.py (Facebook + Instagram)
  ├─ google_ads_adapter.py
  ├─ youtube_adapter.py
  ├─ twitter_adapter.py
  ├─ linkedin_adapter.py
  ├─ amazon_adapter.py
  ├─ tiktok_adapter.py
  └─ whatsapp_adapter.py
```

**AbstractPlatformAdapter Interface:**
- create_campaign(campaign_input) → platform_campaign_id
- update_campaign(platform_campaign_id, updates)
- delete_campaign(platform_campaign_id)
- get_campaign_status(platform_campaign_id) → status
- upload_creative(asset) → platform_creative_id
- get_metrics(campaign_id, date_range) → normalized_metrics
- handle_webhook(payload) → processed_event

---

### Component 2: Campaign Strategy Specialist (Enhanced)

**Additional Responsibilities:**
- Platform selection (which platforms to use based on objectives, audience)
- Budget allocation across platforms
- Platform-specific recommendations (Advantage+ for Meta, Performance Max for Google)

**New Tools:**
- analyze_platform_fit(campaign_objectives, target_audience) → platform_recommendations
- allocate_budget_across_platforms(total_budget, platforms) → budget_allocation

---

### Component 3: Platform Adaptation Specialist (Enhanced)

**Additional Responsibilities:**
- Platform-specific content formatting (character limits, hashtag strategies)
- Platform-specific targeting parameters
- Creative format validation

**New Tools:**
- validate_creative_for_platform(asset, platform) → validation_result
- generate_platform_targeting(audience_draft, platform) → platform_targeting_config

---

### Component 4: Metrics Collection Service

**Purpose:** Fetch metrics from platform APIs, normalize, store

**Workflow:**
1. Daily cron job triggers metrics collection
2. For each active campaign:
   - Check campaign_channels for platforms
   - Call adapter.get_metrics(platform_campaign_id, date_range)
   - Normalize metrics
   - Store in campaign_performance + campaign_performance_raw
3. Aggregate metrics across platforms for cross-platform campaigns

---

### Component 5: Platform Sync Service

**Purpose:** Keep AutifyME campaigns in sync with platform state

**Workflow:**
1. Hourly job for platforms without webhooks (Google, X, LinkedIn, Amazon)
2. Poll campaign status
3. Update campaigns.platform_sync_status
4. Detect platform-side changes (budget exhausted, paused by platform)
5. Notify user if action required

---

### Component 6: Webhook Receiver

**Purpose:** Handle real-time events from platforms

**Endpoints:**
- /webhooks/meta
- /webhooks/tiktok

**Processing:**
1. Validate signature
2. Parse payload
3. Store in platform_webhook_events table
4. Queue for async processing
5. Update relevant campaigns/ads

---

### Component 7: Rate Limit Manager

**Purpose:** Track and enforce rate limits across platforms

**API:**
- check_rate_limit(platform, account_id, operation) → allowed: bool
- record_api_call(platform, account_id, operation, cpu_time?)
- wait_for_rate_limit_reset(platform, account_id)

---

## Data Model Extensions (Phase 2)

### New Tables Needed

**1. platform_credentials**
```
Columns:
- id (UUID, PK)
- platform (TEXT: facebook, google, linkedin, etc.)
- account_id (TEXT: platform ad account ID)
- credential_type (TEXT: oauth_token, refresh_token, developer_token, api_key)
- credential_value (TEXT, encrypted)
- expires_at (TIMESTAMPTZ, nullable)
- created_at, updated_at
```

**2. platform_rate_limits**
```
Columns:
- id (UUID, PK)
- platform (TEXT)
- account_id (TEXT)
- limit_type (TEXT: daily_quota, hourly_requests, cpu_time)
- current_usage (NUMERIC)
- limit_max (NUMERIC)
- reset_at (TIMESTAMPTZ)
- updated_at
```

**3. platform_api_errors**
```
Columns:
- id (UUID, PK)
- platform (TEXT)
- account_id (TEXT)
- operation (TEXT: create_campaign, upload_creative, etc.)
- error_type (TEXT: rate_limit, auth_failure, validation, platform_error)
- error_message (TEXT)
- request_payload (JSONB)
- response_payload (JSONB)
- is_retryable (BOOLEAN)
- retry_count (INTEGER)
- created_at
```

**4. platform_webhook_events**
```
Columns:
- id (UUID, PK)
- platform (TEXT)
- event_type (TEXT: lead_ad, conversion, ad_review, etc.)
- payload (JSONB)
- signature (TEXT, for verification)
- processed (BOOLEAN, default false)
- processed_at (TIMESTAMPTZ, nullable)
- created_at
```

**5. campaign_performance (normalized metrics)**
```
Columns:
- id (UUID, PK)
- campaign_id (UUID, FK to campaigns)
- campaign_channel_id (UUID, FK to campaign_channels, nullable)
- date (DATE)
- impressions (INTEGER)
- clicks (INTEGER)
- spend (NUMERIC)
- conversions (INTEGER)
- revenue (NUMERIC)
- video_views (INTEGER, nullable)
- engagement (INTEGER, nullable)
- created_at
- Composite unique: (campaign_channel_id, date) OR (campaign_id, date)
```

**6. campaign_performance_raw (platform-specific)**
```
Columns:
- id (UUID, PK)
- campaign_performance_id (UUID, FK)
- platform (TEXT)
- raw_metrics (JSONB: platform-specific metric names/values)
- created_at
```

**7. platform_campaign_mapping**
```
Columns:
- id (UUID, PK)
- campaign_id (UUID, FK to campaigns)
- platform (TEXT)
- platform_campaign_id (TEXT: external campaign ID)
- platform_ad_set_ids (JSONB: array of ad set/ad group IDs)
- platform_ad_ids (JSONB: array of ad IDs)
- platform_creative_ids (JSONB: array of creative IDs)
- sync_status (TEXT: not_synced, syncing, synced, failed)
- last_synced_at (TIMESTAMPTZ)
- created_at, updated_at
```

---

## Implementation Priority Recommendation

**Phase 1 (Foundation):**
1. Platform abstraction layer (AbstractPlatformAdapter interface)
2. Meta adapter (Facebook + Instagram) - Highest impact
3. Credential management (platform_credentials table + encryption)
4. Generic campaign model extensions
5. Campaign lifecycle sync (platform_sync_status)

**Phase 2 (Expansion):**
1. Google Ads adapter
2. TikTok adapter
3. Webhook receiver (Meta, TikTok)
4. Metrics collection service (basic)

**Phase 3 (Completeness):**
1. LinkedIn adapter
2. X/Twitter adapter
3. Amazon Advertising adapter
4. YouTube adapter (content upload)
5. Advanced metrics normalization
6. Cross-platform analytics

**Phase 4 (Optimization):**
1. Rate limit manager
2. Intelligent request queuing
3. Performance Max / Advantage+ AI campaign support
4. A/B testing framework
5. Budget optimization algorithms

---

## Open Questions for Discussion

**1. Platform Priority:**
- Which platforms are must-have for Phase 1?
- My recommendation: Meta (FB+IG), Google Ads, TikTok (covers 80% of digital ad spend)

**2. Campaign Creation Workflow:**
- Should specialists generate platform-ready configurations, or keep generic and let adapters translate?
- My recommendation: Generic in specialists, platform-specific translation in adapters (cleaner separation)

**3. Creative Upload Timing:**
- Upload creatives during campaign creation (sync), or pre-upload to library (async)?
- My recommendation: Pre-upload to campaign_assets, reference during campaign creation

**4. Webhook Infrastructure:**
- Build our own webhook receiver, or use third-party service (Zapier, n8n)?
- My recommendation: Build our own (more control, lower cost at scale)

**5. Metrics Freshness:**
- Real-time metrics (expensive, complex) vs daily batch (simple, delayed)?
- My recommendation: Start with daily batch, add real-time for critical metrics later

**6. Multi-Tenancy:**
- Design for single-tenant now, multi-tenant later, or build multi-tenant from start?
- My recommendation: Single-tenant architecture now (simplifies), plan migration path

**7. Error Handling:**
- Surface all errors to user, or auto-retry and only surface critical failures?
- My recommendation: Auto-retry transient, surface non-retryable via HITL

**8. Platform-Specific Features:**
- Support from day one (Advantage+, Performance Max, LinkedIn Lead Forms), or start generic?
- My recommendation: Generic first, add platform-specific features in Phase 2-3

---

## Next Steps

**Recommended Discussion Flow:**

1. **Platform Priority Decision** - Which platforms Phase 1 vs later?
2. **Abstraction Layer Design** - Review AbstractPlatformAdapter interface
3. **Data Model Review** - Review 7 new tables, finalize schema
4. **Credential Management** - Encryption strategy, token refresh workflow
5. **Campaign Lifecycle** - State machine design, sync strategy
6. **Metrics Strategy** - Normalization approach, aggregation levels
7. **Error Handling** - Classification, retry logic, user notification
8. **Implementation Roadmap** - Phased rollout plan

---

**Last Updated:** 2025-10-25
**Status:** Ready for Architectural Discussion
**Next Action:** Point-by-point discussion of decisions and open questions
