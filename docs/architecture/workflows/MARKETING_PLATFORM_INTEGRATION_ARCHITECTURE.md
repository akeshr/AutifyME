# Marketing Platform Integration Architecture

**Created:** October 25, 2025
**Status:** ✅ Design Complete
**Purpose:** Enterprise-grade platform abstraction for multi-channel advertising automation
**Prerequisites:** PLATFORM_API_RESEARCH_ANALYSIS.md, DATABASE_SCHEMA_DESIGN.md

---

## Executive Summary

Complete architectural design for integrating 8 advertising platforms into AutifyME's autonomous marketing system. Balances generic abstraction with platform-specific flexibility via hybrid model.

**Core Strategy:** Platform Adapter Pattern + Unified Campaign Model + JSONB Extensions

**Phase 1 Platforms:** Meta (Facebook/Instagram), Google Ads, Amazon, YouTube - 80%+ digital ad spend + video dominance

**Phase 2+ Platforms:** X (Twitter), LinkedIn, TikTok

**Key Architectural Decisions:**
- Hybrid abstraction (generic + platform-specific JSONB)
- Encrypted credential management with auto-refresh
- State machine-driven campaign lifecycle
- Unified asset library with async platform upload
- Dual metrics storage (normalized + raw)
- Per-platform rate limit tracking with request queue
- Intelligent error classification with retry logic

---

## Architectural Decisions (8 Critical Questions Resolved)

### Decision 1: Platform Priority

**Recommendation:** Meta → Google Ads → Amazon → YouTube → X (Twitter) → LinkedIn → TikTok

**Rationale:**
- **Meta:** 25% global digital ad spend, mature API, native webhooks, Advantage+ AI (FB + Instagram)
- **Google Ads:** 29% market share, covers Search + Display + Shopping
- **Amazon:** E-commerce focus aligns with AutifyME's product catalog core, ASIN-based campaigns, high-intent buyers
- **YouTube:** Second-largest search engine, video advertising + organic video management (Google Ads API for ads, Data API for uploads/analytics)
- **X (Twitter):** Broad reach, real-time engagement, B2B + B2C versatility, promoted posts model
- **LinkedIn:** B2B dominance, premium targeting, enterprise campaigns
- **TikTok:** Gen Z/video-first specialization, emerging platform (future opportunity)

**Phase 1 Scope:** Meta + Google Ads + Amazon + YouTube (4 platforms, 80%+ digital ad spend + video dominance)

**Business Impact:** Maximum ROI coverage with minimal platform complexity

---

### Decision 2: Abstraction Layer Strategy

**Recommendation:** Hybrid Model (Generic Core + Platform Extensions)

**Generic Campaign Model (90% use cases):**
```
Campaign Attributes (Universal):
- name, objective, budget, schedule, status
- targeting (demographics, interests, behaviors)
- creative_assets (images, videos, copy)
- bidding_strategy (CPC, CPM, CPA, ROAS target)
- daily_budget, lifetime_budget
```

**Platform-Specific Extensions (JSONB):**
```sql
-- campaigns table
platform_config JSONB  -- Platform-specific advanced features

-- Example: Meta Advantage+ campaign
platform_config = {
  "advantage_shopping_campaign": true,
  "catalog_id": "12345",
  "optimization_goal": "PURCHASE",
  "pixel_id": "98765"
}

-- Example: Google Performance Max
platform_config = {
  "asset_group_type": "PERFORMANCE_MAX",
  "conversion_goals": ["PURCHASE", "ADD_TO_CART"],
  "budget_type": "DAILY",
  "bidding_strategy": "MAXIMIZE_CONVERSION_VALUE"
}
```

**Benefits:**
- 90% of campaigns use generic model (simple, maintainable)
- 10% advanced features via JSONB (flexible, no schema changes)
- Platform specialists know how to populate platform_config
- PM delegates to appropriate specialist based on user intent

---

### Decision 3: Credential Management

**Recommendation:** Encrypted Storage + Middleware Auto-Refresh

**Database Schema:**
```sql
CREATE TABLE platform_credentials (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  platform TEXT NOT NULL CHECK (platform IN (
    'meta', 'google_ads', 'tiktok', 'linkedin',
    'twitter', 'amazon', 'youtube'
  )),
  credential_type TEXT NOT NULL CHECK (credential_type IN (
    'oauth_token', 'api_key', 'developer_token', 'system_user'
  )),

  -- Encrypted columns (use pgcrypto or application-level encryption)
  access_token_encrypted TEXT NOT NULL,
  refresh_token_encrypted TEXT,

  -- Token lifecycle
  token_expires_at TIMESTAMPTZ,
  scopes TEXT[],  -- OAuth scopes granted

  -- Platform-specific identifiers
  account_id TEXT,  -- Ad account ID on platform
  business_id TEXT,  -- Meta Business Manager ID, Google Manager Account, etc.

  -- Metadata
  is_active BOOLEAN DEFAULT true,
  last_refreshed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),

  UNIQUE(company_id, platform, account_id)
);

CREATE INDEX idx_platform_credentials_company_platform
  ON platform_credentials(company_id, platform)
  WHERE is_active = true;
```

**Auto-Refresh Middleware:**
- Runs before each platform API call
- Checks `token_expires_at < now() + interval '5 minutes'`
- Triggers refresh flow if expiring soon
- Updates encrypted tokens atomically
- Logs refresh events to audit_log

**Security:**
- Application-level encryption (Fernet or AES-256-GCM)
- Encryption key stored in environment variable (not database)
- Refresh tokens never exposed to agents or prompts
- Service account pattern for Meta (system users with permanent tokens)

---

### Decision 4: Campaign Lifecycle Management

**Recommendation:** State Machine + Platform Sync Status

**Campaign States (Finite State Machine):**
```
DRAFT → PENDING_REVIEW → APPROVED → SYNCING → ACTIVE → PAUSED → COMPLETED → ARCHIVED

State Transitions:
- DRAFT → PENDING_REVIEW: Specialist completes campaign design
- PENDING_REVIEW → APPROVED: User approves via HITL
- APPROVED → SYNCING: Platform sync initiated
- SYNCING → ACTIVE: All platforms confirm campaign live
- ACTIVE → PAUSED: User pauses or platform policy violation
- ACTIVE → COMPLETED: End date reached or budget exhausted
- Any → ARCHIVED: User archives campaign
```

**Platform Sync Status Tracking:**
```sql
ALTER TABLE campaign_channels ADD COLUMN sync_status TEXT
  CHECK (sync_status IN (
    'pending', 'syncing', 'live', 'paused', 'rejected', 'error'
  )) DEFAULT 'pending';

ALTER TABLE campaign_channels ADD COLUMN sync_error_message TEXT;
ALTER TABLE campaign_channels ADD COLUMN last_synced_at TIMESTAMPTZ;
ALTER TABLE campaign_channels ADD COLUMN platform_campaign_id TEXT;  -- External ID
```

**Lifecycle Orchestration:**
- **Async Campaign Creation:** Specialist creates campaign → PM approves → Background worker syncs to platforms
- **Polling for Non-Webhook Platforms:** Scheduled task checks Google Ads, LinkedIn, Amazon status every 15 minutes
- **Webhook Ingestion:** Meta, TikTok send real-time updates via platform_webhook_events table
- **Error Recovery:** Transient errors trigger retry (3 attempts), permanent errors surface to user

---

### Decision 5: Creative/Asset Management

**Recommendation:** Unified Asset Library + Async Platform Upload

**Asset Flow:**
```
1. Visual Assets Specialist generates creative variants
2. Assets stored in campaign_assets table (S3/Supabase Storage URLs)
3. Background worker pre-uploads to platforms BEFORE campaign creation
4. Platform returns asset IDs (stored in platform_asset_id column)
5. Campaign creation references platform asset IDs (no upload during campaign sync)
```

**Benefits:**
- Decouples creative generation from campaign creation (faster specialist execution)
- Validates asset compliance BEFORE campaign approval (Meta has strict image rules)
- Enables asset reuse across campaigns (store once, reference many times)
- Reduces campaign creation latency (assets already uploaded)

**Database Schema Enhancement:**
```sql
ALTER TABLE campaign_assets ADD COLUMN platform_asset_id JSONB;
-- Example: {"meta": "123456", "google_ads": "789012", "tiktok": "345678"}

ALTER TABLE campaign_assets ADD COLUMN platform_upload_status JSONB;
-- Example: {"meta": "live", "google_ads": "pending", "tiktok": "rejected"}

ALTER TABLE campaign_assets ADD COLUMN compliance_check_results JSONB;
-- Example: {
--   "meta": {"compliant": false, "reason": "Text overlay > 20%"},
--   "google_ads": {"compliant": true}
-- }
```

**Async Upload Worker:**
- Triggered after HITL approval (user approves campaign)
- Uploads assets in parallel to all selected platforms
- Records platform_asset_id and compliance results
- Retries failed uploads with exponential backoff
- Surfaces non-compliant assets to user for revision

---

### Decision 6: Metrics Collection & Normalization

**Recommendation:** Dual Storage (Normalized + Raw JSONB)

**Normalized Metrics Table (Fast Queries, Aggregation):**
```sql
CREATE TABLE campaign_performance (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  channel_id UUID REFERENCES campaign_channels(id) ON DELETE CASCADE,

  -- Time dimension
  date DATE NOT NULL,
  hour INT,  -- NULL for daily aggregates, 0-23 for hourly

  -- Universal metrics (normalized across platforms)
  impressions BIGINT DEFAULT 0,
  clicks BIGINT DEFAULT 0,
  conversions INT DEFAULT 0,
  spend DECIMAL(10,2) DEFAULT 0.00,
  revenue DECIMAL(10,2) DEFAULT 0.00,

  -- Calculated metrics (materialized for performance)
  ctr DECIMAL(5,4),  -- Click-through rate
  cpc DECIMAL(10,2),  -- Cost per click
  cpa DECIMAL(10,2),  -- Cost per acquisition
  roas DECIMAL(10,2),  -- Return on ad spend

  -- Engagement metrics (social platforms)
  likes INT DEFAULT 0,
  shares INT DEFAULT 0,
  comments INT DEFAULT 0,

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),

  UNIQUE(campaign_id, channel_id, date, hour)
);

CREATE INDEX idx_campaign_performance_date
  ON campaign_performance(campaign_id, date DESC);
CREATE INDEX idx_campaign_performance_channel_date
  ON campaign_performance(channel_id, date DESC);
```

**Raw Metrics Table (Platform-Specific Data):**
```sql
CREATE TABLE campaign_performance_raw (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  performance_id UUID REFERENCES campaign_performance(id) ON DELETE CASCADE,
  platform TEXT NOT NULL,

  -- Raw platform metrics (platform-specific names and values)
  raw_metrics JSONB NOT NULL,
  -- Example Meta: {
  --   "reach": 50000,
  --   "frequency": 2.3,
  --   "video_play_actions": 1200,
  --   "video_avg_time_watched": 8.5,
  --   "cost_per_thruplay": 0.15
  -- }
  -- Example Amazon: {
  --   "attributedSales14d": 5000.00,
  --   "acos": 0.20,  -- Advertising Cost of Sales
  --   "attributed_units_ordered_14d": 150
  -- }

  fetched_at TIMESTAMPTZ DEFAULT now(),

  UNIQUE(performance_id, platform)
);
```

**Metrics Normalization Rules:**
```
Universal Mapping:
- impressions: Direct mapping (all platforms)
- clicks: Direct mapping (all platforms)
- conversions: Meta "purchases", Google "conversions", Amazon "attributed_units_ordered_14d"
- spend: Meta "spend", Google "cost_micros"/1M, Amazon "cost"
- revenue: Meta "purchase_value", Google "conversions_value", Amazon "attributedSales14d"

Platform-Specific (stored in raw only):
- Meta: reach, frequency, video metrics, engagement
- Google: quality_score, search_impression_share, average_position
- Amazon: ACOS, attributed sales with different attribution windows
- TikTok: video_views, video_watched_6s, engaged_view
```

**Collection Strategy:**
- **Webhook Platforms (Meta, TikTok):** Real-time updates on significant changes (>10% metric change)
- **Polling Platforms (Google, LinkedIn, Amazon):** Daily batch at 2 AM UTC (previous day's data)
- **Hourly Data:** Only for active campaigns with >$100/day spend (avoid API quota waste)
- **Aggregation:** Daily rollups for historical analysis, hourly for active monitoring

---

### Decision 7: Rate Limit Management

**Recommendation:** Per-Platform Quota Tracking + Request Queue

**Database Schema:**
```sql
CREATE TABLE platform_rate_limits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  platform TEXT NOT NULL,

  -- Rate limit tracking
  limit_type TEXT NOT NULL,  -- 'cpu_time', 'daily_quota', 'requests_per_hour', etc.
  current_usage BIGINT DEFAULT 0,
  limit_threshold BIGINT NOT NULL,
  reset_at TIMESTAMPTZ NOT NULL,

  -- Adaptive throttling
  throttle_enabled BOOLEAN DEFAULT false,
  throttle_factor DECIMAL(3,2) DEFAULT 1.0,  -- 1.0 = normal, 0.5 = half speed

  -- Metadata
  last_updated_at TIMESTAMPTZ DEFAULT now(),

  UNIQUE(company_id, platform, limit_type)
);

CREATE TABLE platform_api_errors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  platform TEXT NOT NULL,

  -- Error classification
  error_type TEXT NOT NULL CHECK (error_type IN (
    'rate_limit', 'authentication', 'authorization',
    'validation', 'platform_error', 'network', 'timeout'
  )),
  is_retryable BOOLEAN DEFAULT false,

  -- Error details
  endpoint TEXT,  -- API endpoint that failed
  http_status_code INT,
  error_message TEXT,
  error_code TEXT,  -- Platform-specific error code
  request_payload JSONB,

  -- Retry tracking
  retry_count INT DEFAULT 0,
  next_retry_at TIMESTAMPTZ,
  resolved_at TIMESTAMPTZ,

  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_platform_api_errors_unresolved
  ON platform_api_errors(company_id, platform, created_at DESC)
  WHERE resolved_at IS NULL;
```

**Platform-Specific Rate Limit Strategies:**

**Meta (CPU Time-Based):**
```
Limit: 100% CPU time per ad account per hour
Strategy:
- Track total_cputime from API response headers
- When usage > 75%, enable throttling (throttle_factor = 0.5)
- When usage > 90%, pause non-critical requests
- Reset every hour
```

**Google Ads (Operation-Based):**
```
Limit: Varies by operation type (no public threshold)
Strategy:
- Implement exponential backoff on RESOURCE_EXHAUSTED errors
- Batch read operations (retrieve multiple campaigns in single request)
- Use selective field masks (only request needed fields)
```

**YouTube (Daily Quota):**
```
Limit: 10,000 units/day (upload = 1,600 units = ~6 videos/day)
Strategy:
- Track daily quota usage in platform_rate_limits
- Reserve 2,000 units for critical operations
- Upload videos during off-peak hours (2-6 AM UTC)
- Request quota increase if needed (requires compliance audit)
```

**Amazon/TikTok/LinkedIn (Request Throttling):**
```
Limit: Platform-specific requests per second/minute
Strategy:
- Implement token bucket algorithm
- Queue requests during high-load periods
- Prioritize real-time operations (campaign status) over batch (historical metrics)
```

**Request Queue Implementation:**
- Priority queue: High (campaign creation), Medium (metric collection), Low (historical analysis)
- Exponential backoff: 1s, 2s, 4s, 8s, 16s, 32s (max 6 retries)
- Circuit breaker: If error rate > 50% over 5 minutes, pause platform for 15 minutes

---

### Decision 8: Error Handling & Retry Logic

**Recommendation:** Centralized Error Classification + Intelligent Retry

**Error Classification Rules:**
```python
# Transient (retryable) errors:
- Rate limiting (429, RATE_LIMIT_EXCEEDED)
- Timeouts (504, GATEWAY_TIMEOUT)
- Network errors (connection reset, DNS failures)
- Temporary platform issues (500, 503, INTERNAL_ERROR)

# Permanent (non-retryable) errors:
- Authentication failures (401, INVALID_TOKEN)
- Authorization errors (403, INSUFFICIENT_PERMISSIONS)
- Validation errors (400, INVALID_PARAMETER)
- Resource not found (404, CAMPAIGN_NOT_FOUND)
- Policy violations (CONTENT_REJECTED, ACCOUNT_DISABLED)
```

**Retry Strategy (Tenacity Pattern):**
```
Retryable Errors:
- Max attempts: 3
- Wait strategy: Exponential backoff (1s → 2s → 4s)
- Jitter: ±20% randomization (avoid thundering herd)
- Reraise: After 3 failures, log to platform_api_errors and surface to user

Non-Retryable Errors:
- No retry, immediate failure
- Log to platform_api_errors with is_retryable=false
- Surface to user with actionable error message
- Example: "Meta rejected campaign: Image text overlay exceeds 20%. Please reduce text and resubmit."
```

**Error Surfacing to User:**
- **Specialist Execution Errors:** Tool returns ToolException with user-friendly message
- **Background Sync Errors:** Update campaign_channels.sync_status = 'error', send notification
- **Metrics Collection Errors:** Log silently (don't interrupt campaign), retry next cycle
- **Critical Errors (auth failures):** Send immediate notification, pause all platform operations

**Error Recovery Workflows:**
- **Token Expired:** Auto-refresh via middleware, retry original request
- **Rate Limit Hit:** Wait for reset_at timestamp, auto-resume queue
- **Campaign Rejected:** Update status to 'rejected', provide rejection reason, offer edit flow
- **Platform Outage:** Detect via circuit breaker, pause operations, resume when healthy

---

## Platform Abstraction Layer Design

### AbstractPlatformAdapter (Base Interface)

**Core Responsibility:** Define uniform contract for all platform adapters

**Key Methods:**
```
Campaign Lifecycle:
- create_campaign(campaign: CampaignInput) → platform_campaign_id
- update_campaign(platform_campaign_id, updates: dict) → success
- pause_campaign(platform_campaign_id) → success
- delete_campaign(platform_campaign_id) → success
- get_campaign_status(platform_campaign_id) → status

Asset Management:
- upload_asset(asset: CampaignAsset) → platform_asset_id
- validate_asset(asset: CampaignAsset) → compliance_result
- delete_asset(platform_asset_id) → success

Metrics & Reporting:
- fetch_campaign_metrics(platform_campaign_id, date_range) → metrics
- fetch_realtime_metrics(platform_campaign_id) → metrics (for webhook platforms)

Account & Authentication:
- validate_credentials() → valid/invalid
- refresh_access_token() → new_token
- get_account_info() → account_metadata
```

**Adapter Implementations:**
- MetaPlatformAdapter (Facebook + Instagram via single API)
- GoogleAdsPlatformAdapter (Search, Display, Shopping, Performance Max)
- TikTokPlatformAdapter
- LinkedInPlatformAdapter
- TwitterPlatformAdapter
- AmazonPlatformAdapter
- YouTubePlatformAdapter (separate from Google Ads for video campaigns)

**Adapter Registration:**
```python
# agents/src/autifyme_agents/integrations/platforms/adapter_registry.py

PLATFORM_ADAPTERS = {
    "meta": MetaPlatformAdapter,
    "google_ads": GoogleAdsPlatformAdapter,
    "tiktok": TikTokPlatformAdapter,
    # ... others
}

def get_platform_adapter(platform: str, credentials: dict) -> AbstractPlatformAdapter:
    adapter_class = PLATFORM_ADAPTERS.get(platform)
    if not adapter_class:
        raise ValueError(f"Unsupported platform: {platform}")
    return adapter_class(credentials)
```

---

### Platform Specialist Design

**New Specialist:** Platform Sync Specialist

**Responsibility:** Translate generic campaign into platform-specific API calls

**Tools Available:**
- `create_platform_campaign` - Calls appropriate platform adapter
- `upload_campaign_assets` - Pre-uploads assets to platforms
- `validate_platform_config` - Checks platform-specific settings
- `sync_campaign_status` - Polls platform for status updates

**Output Model:**
```python
class PlatformSyncResult(BaseModel):
    campaign_id: UUID
    platform: str
    platform_campaign_id: str
    status: Literal["live", "pending_review", "rejected", "error"]
    error_message: Optional[str] = None
    sync_metadata: dict  # Platform-specific response data
```

**Integration with PM:**
```
User: "Launch this campaign on Meta and Google Ads"

PM delegates to:
1. Campaign Strategy Specialist → CampaignStrategyDraft
2. Marketing Content Specialist → MarketingContentDraft
3. Visual Assets Specialist → VisualAssetsDraft (reused from product onboarding)
4. Platform Adaptation Specialist → PlatformContentVariantsDraft

PM synthesizes into:
- CampaignInput (generic model for HITL approval)

After HITL approval, PM delegates to:
5. Platform Sync Specialist (NEW) → Creates campaigns on Meta + Google Ads

Platform Sync Specialist uses:
- MetaPlatformAdapter.create_campaign(campaign_input.to_meta_format())
- GoogleAdsPlatformAdapter.create_campaign(campaign_input.to_google_ads_format())
```

**HITL Checkpoint:** User approves CampaignInput BEFORE platform sync (prevents unauthorized spend)

---

## Phase 2 Database Schema (Complete)

### New Tables (7 Total)

**1. platform_credentials** (documented in Decision 3)

**2. platform_rate_limits** (documented in Decision 7)

**3. platform_api_errors** (documented in Decision 7)

**4. platform_webhook_events**
```sql
CREATE TABLE platform_webhook_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  platform TEXT NOT NULL CHECK (platform IN ('meta', 'tiktok')),

  -- Event identification
  event_type TEXT NOT NULL,  -- 'campaign_status_change', 'lead_created', 'conversion', etc.
  event_id TEXT,  -- Platform's unique event ID (for deduplication)

  -- Event payload
  payload JSONB NOT NULL,

  -- Processing status
  processed BOOLEAN DEFAULT false,
  processed_at TIMESTAMPTZ,
  processing_error TEXT,

  -- Metadata
  received_at TIMESTAMPTZ DEFAULT now(),

  UNIQUE(platform, event_id)  -- Prevent duplicate event processing
);

CREATE INDEX idx_webhook_events_unprocessed
  ON platform_webhook_events(company_id, platform, received_at)
  WHERE processed = false;

-- Auto-cleanup: Delete processed events older than 7 days
CREATE INDEX idx_webhook_events_cleanup
  ON platform_webhook_events(processed_at)
  WHERE processed = true;
```

**5. campaign_performance** (documented in Decision 6)

**6. campaign_performance_raw** (documented in Decision 6)

**7. platform_campaign_mapping**
```sql
CREATE TABLE platform_campaign_mapping (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  channel_id UUID NOT NULL REFERENCES campaign_channels(id) ON DELETE CASCADE,
  platform TEXT NOT NULL,

  -- Platform hierarchy IDs
  platform_campaign_id TEXT NOT NULL,  -- External campaign ID
  platform_adset_id TEXT,  -- Ad set/Ad group ID (if applicable)
  platform_ad_ids TEXT[],  -- Individual ad IDs

  -- Sync metadata
  created_on_platform_at TIMESTAMPTZ,
  last_synced_at TIMESTAMPTZ,
  sync_version INT DEFAULT 1,  -- Increment on each update

  -- Platform-specific metadata
  platform_metadata JSONB,
  -- Example: {
  --   "campaign_name_on_platform": "Spring Sale 2025 - Meta",
  --   "effective_status": "ACTIVE",
  --   "optimization_goal": "PURCHASE",
  --   "bid_strategy": "LOWEST_COST_WITH_BID_CAP"
  -- }

  created_at TIMESTAMPTZ DEFAULT now(),

  UNIQUE(channel_id, platform)
);
```

### Extended Tables (4 Modifications)

**1. campaigns** (add platform_config)
```sql
ALTER TABLE campaigns ADD COLUMN platform_config JSONB;
-- Stores platform-specific advanced settings (see Decision 2)
```

**2. campaign_channels** (add sync tracking)
```sql
ALTER TABLE campaign_channels ADD COLUMN sync_status TEXT
  CHECK (sync_status IN ('pending', 'syncing', 'live', 'paused', 'rejected', 'error'))
  DEFAULT 'pending';

ALTER TABLE campaign_channels ADD COLUMN sync_error_message TEXT;
ALTER TABLE campaign_channels ADD COLUMN last_synced_at TIMESTAMPTZ;
ALTER TABLE campaign_channels ADD COLUMN platform_campaign_id TEXT;  -- Quick reference
```

**3. campaign_assets** (add platform upload tracking)
```sql
ALTER TABLE campaign_assets ADD COLUMN platform_asset_id JSONB;
-- Example: {"meta": "123456", "google_ads": "789012", "tiktok": "345678"}

ALTER TABLE campaign_assets ADD COLUMN platform_upload_status JSONB;
-- Example: {"meta": "live", "google_ads": "pending", "tiktok": "rejected"}

ALTER TABLE campaign_assets ADD COLUMN compliance_check_results JSONB;
-- Example: {"meta": {"compliant": false, "reason": "Text overlay > 20%"}}
```

**4. marketing_content** (no changes - already supports campaign_id)

---

## Integration with 2-Level Architecture

### Specialist Assignment to PM

**Existing Specialists (Reused from Product Onboarding):**
- Visual Assets Specialist (generates images, videos, graphics)

**New Marketing Specialists:**
1. **Campaign Strategy Specialist** - Defines objectives, budget, timeline, KPIs
2. **Audience Intelligence Specialist** - Identifies target segments, behaviors, lookalikes
3. **Marketing Content Specialist** - Writes campaign narratives, value props, CTAs
4. **Platform Adaptation Specialist** - Tailors content for each platform's best practices
5. **Ad Copy Specialist** - Creates A/B test variants, ensures compliance
6. **Platform Sync Specialist** - Executes platform API calls, manages sync lifecycle (NEW for Phase 2)

**PM Configuration:**
```python
# workflows/project_manager.py

project_manager = create_deep_agent(
    tools=[],  # PM has no tools
    system_prompt=load_prompt("project_manager.prompt"),
    subagents=[
        # Product Onboarding Specialists
        cataloging_specialist_subagent,

        # Marketing Campaign Specialists
        campaign_strategy_specialist_subagent,
        audience_intelligence_specialist_subagent,
        marketing_content_specialist_subagent,
        platform_adaptation_specialist_subagent,
        ad_copy_specialist_subagent,
        visual_assets_specialist_subagent,  # Reused!
        platform_sync_specialist_subagent,  # NEW for Phase 2
    ],
    model=llm,
    checkpointer=checkpointer,
    store=store,
    use_longterm_memory=True,
    context_schema=CompanyContext,
)
```

### Workflow Orchestration Pattern

**User Request:** "Create a Meta and Google Ads campaign for our new Spring collection"

**PM Orchestration Flow:**

**Phase 1: Strategy & Intelligence (Sequential)**
```
1. PM → Campaign Strategy Specialist
   Input: "Spring collection campaign, Meta + Google Ads, $5000 budget"
   Output: CampaignStrategyDraft (objectives, budget split, timeline)

2. PM → Audience Intelligence Specialist
   Input: CampaignStrategyDraft + company_intelligence
   Output: AudienceTargetingDraft (segments, platform preferences)
```

**Phase 2: Content & Creative (Parallel)**
```
3a. PM → Marketing Content Specialist (parallel)
    Input: CampaignStrategyDraft + AudienceTargetingDraft
    Output: MarketingContentDraft (narratives, headlines, CTAs)

3b. PM → Visual Assets Specialist (parallel)
    Input: Spring collection product images + brand style
    Output: VisualAssetsDraft (image variants, video clips)
```

**Phase 3: Platform Optimization (Parallel)**
```
4a. PM → Platform Adaptation Specialist
    Input: MarketingContentDraft + platforms=['meta', 'google_ads']
    Output: PlatformContentVariantsDraft (Meta-optimized + Google-optimized content)

4b. PM → Ad Copy Specialist
    Input: MarketingContentDraft + platform requirements
    Output: AdCopyDraft (A/B variants, compliance-checked)
```

**Phase 4: Synthesis & HITL**
```
5. PM synthesizes all specialist outputs into CampaignInput
   - Combines strategy, targeting, content, assets, platform adaptations
   - Presents to user for approval via HITL

6. User approves (or edits and approves)
```

**Phase 5: Platform Sync (Asynchronous)**
```
7. PM → Platform Sync Specialist
   Input: Approved CampaignInput
   Actions:
   a. Upload assets to Meta + Google Ads (parallel, via adapters)
   b. Create campaigns on both platforms (via adapters)
   c. Monitor sync status, handle errors
   Output: PlatformSyncResult for each platform

8. PM confirms to user: "Campaign live on Meta (ID: 123456) and Google Ads (ID: 789012)"
```

**Error Handling:**
- If Meta sync fails but Google succeeds → Update campaign_channels.sync_status accordingly, notify user
- If asset upload fails → Retry 3 times, surface to user if persistent failure
- If compliance rejection → Update sync_error_message, allow user to edit and resubmit

---

## Implementation Sequencing

### Phase 1: Foundation (Weeks 1-3)

**Database:**
- Create 7 new tables (platform_credentials, rate_limits, api_errors, webhook_events, performance, performance_raw, campaign_mapping)
- Extend 4 existing tables (campaigns, campaign_channels, campaign_assets, marketing_content)
- Add encryption middleware for credentials
- Create cleanup jobs (webhook events, API errors)

**Platform Abstraction:**
- Implement AbstractPlatformAdapter interface
- Build MetaPlatformAdapter (Facebook + Instagram)
- Build credential auto-refresh middleware
- Implement error classification logic

**Specialists:**
- Platform Sync Specialist (uses MetaPlatformAdapter)
- Integrate with existing PM

**Validation:**
- Create test campaign on Meta
- Verify asset upload, campaign creation, status polling
- Validate error handling and retry logic

---

### Phase 2: Expansion (Weeks 4-6)

**Platform Adapters:**
- GoogleAdsPlatformAdapter (Search, Display, Shopping)
- AmazonPlatformAdapter (Sponsored Products/Brands/Display)
- YouTubePlatformAdapter (video ads via Google Ads + organic uploads via Data API)

**Metrics Collection:**
- Webhook receiver endpoint for Meta
- Daily polling jobs for Google Ads, Amazon, YouTube
- Normalization logic for campaign_performance (ACOS → ROAS conversion)
- YouTube-specific metrics (video views, watch time, engagement)

**Rate Limiting:**
- Platform-specific quota tracking
- YouTube quota management (10,000 units/day, 6 uploads/day limit)
- Request queue with priority handling
- Circuit breaker for platform outages

**Validation:**
- Multi-platform campaigns (Meta + Google + Amazon + YouTube)
- Video campaign workflows (YouTube ads + organic uploads)
- Metrics aggregation across platforms
- Rate limit handling under load

---

### Phase 3: Optimization (Weeks 7-9)

**Advanced Features:**
- Meta Advantage+ campaign support (via platform_config JSONB)
- Google Performance Max campaigns
- Amazon ASIN-based targeting with product catalog sync
- YouTube video SEO optimization (titles, descriptions, tags)
- Asset reuse across campaigns (product videos on YouTube + Meta + TikTok)
- A/B test variant creation

**Analytics:**
- Campaign performance dashboard queries
- Cross-platform metric comparison
- Budget optimization recommendations
- E-commerce attribution (Amazon sales tracking)
- Video engagement analytics (YouTube watch patterns)

**Resilience:**
- Graceful degradation (if one platform down, others continue)
- Automatic error recovery workflows
- Proactive compliance checking

---

### Phase 4: Remaining Platforms (Weeks 10-12)

**Platform Adapters:**
- TwitterPlatformAdapter (X Ads - promoted posts with organic creation)
- LinkedInPlatformAdapter (B2B campaigns, job/company targeting)
- TikTokPlatformAdapter (video-first creative, events API)

**Full Integration:**
- All 7 marketing specialists operational
- Multi-platform campaign orchestration (7 platforms)
- Complete metrics normalization
- Enterprise-grade error handling
- Social media campaign workflows (X, LinkedIn, TikTok)

---

## Summary: Architecture Principles

**Hybrid Abstraction:**
- Generic model handles 90% of use cases (simple, maintainable)
- JSONB extensions support platform-specific features (flexible, no schema changes)

**Security First:**
- Encrypted credential storage
- Auto-refresh tokens via middleware
- No secrets exposed to agents or prompts

**Resilience:**
- Intelligent error classification (retryable vs permanent)
- Per-platform rate limit tracking
- Circuit breakers for platform outages
- Graceful degradation (one platform failure doesn't break others)

**Observability:**
- Complete audit trail (platform_api_errors, webhook_events, sync status)
- Metrics normalized for cross-platform comparison
- Raw metrics preserved for platform-specific analysis

**Separation of Concerns:**
- Specialists analyze and generate content (no platform knowledge)
- Platform Sync Specialist handles API calls (isolated responsibility)
- PM orchestrates workflow (no implementation details)
- Adapters encapsulate platform complexity (clean interfaces)

**Enterprise-Grade:**
- Multi-platform support from day one
- Designed for scale (queue, rate limiting, async uploads)
- Production-ready error handling
- Future-proof (JSONB extensions, adapter pattern)

---

**Last Updated:** January 25, 2025
**Next Review:** After Phase 1 implementation (Meta adapter validation)
**Related Docs:** PLATFORM_API_RESEARCH_ANALYSIS.md, DATABASE_SCHEMA_DESIGN.md, MARKETING_DOMAIN_ANALYSIS.md
