# Marketing Domain - Initial Analysis & Specialist Design

**Date:** 2025-10-25
**Status:** 🔄 Analysis Phase - Pending Data Model Design
**Phase:** Specialist Identification Complete, Awaiting Database Architecture

---

## Executive Summary

Comprehensive marketing domain for multi-channel campaign orchestration across WhatsApp (primary), Facebook, Instagram, YouTube, X (Twitter), Amazon, own websites, and all possible advertising channels.

**Scope:** Campaign creation, audience targeting, content generation, multi-platform adaptation, paid advertising, organic social media.

**Architecture Approach:** Following `DOMAIN_DESIGN_GUIDELINES.md` - domain-specific specialists (NOT workflow-specific), reusable across campaign types, HITL at PM level, atomic persistence.

---

## Requirements Analysis

### Business Context

**Customer Communication Channels:**
- **Primary:** WhatsApp (maximum customer base)
- **Social Media:** Facebook, Instagram, YouTube, X (Twitter)
- **E-commerce:** Amazon, own websites
- **Advertising:** All possible paid and organic channels

**Marketing Workflow Types:**
1. Product launch campaigns
2. Seasonal promotions
3. Brand awareness
4. Customer retention
5. Cross-sell/upsell
6. Event marketing

**Key Challenge:** Single campaign needs content variants for 8+ platforms, each with different formats, character limits, audience expectations, and compliance requirements.

---

## Domain Specialist Design

Following guideline: **"Domain-specific specialists reusable across workflows, NOT workflow-specific"**

### Rejected Approaches

#### ❌ Approach 1: Workflow-Specific Specialists
```
Product Launch Specialist
Seasonal Promotion Specialist
Brand Awareness Specialist
```
**Rejection Reason:** Tied to specific campaign types, not reusable. Violates domain-driven design principle.

#### ❌ Approach 2: Platform-Specific Specialists
```
Facebook Specialist
Instagram Specialist
YouTube Specialist
X (Twitter) Specialist
```
**Rejection Reason:** Too granular, maintenance nightmare (10+ specialists), not domain expertise. Platforms change frequently.

---

### ✅ Recommended Approach: Domain Expertise Specialists

**5 New Marketing Specialists + 1 Reused from Product Onboarding**

---

### 1. Campaign Strategy Specialist

**Domain Expertise:** Campaign planning and orchestration

**Responsibilities:**
- Define campaign objectives (awareness, conversion, retention, engagement)
- Set measurable KPIs (reach, engagement, conversions, ROAS)
- Allocate budget across channels (paid social, organic, ads, influencers)
- Design timeline and scheduling (launch date, milestones, duration)
- Recommend channel mix based on audience and objectives
- Success metrics and benchmarks

**Reusable For:**
- Product launch campaigns
- Seasonal promotions
- Brand awareness
- Customer retention
- Event marketing
- Influencer campaigns
- Partnership announcements

**Output Model:** `CampaignStrategyDraft`

**Tools:**
- `analyze_campaign_objectives` - Suggest KPIs based on goals
- `recommend_channel_mix` - Optimal platform allocation
- `calculate_budget_allocation` - Budget distribution logic
- `design_campaign_timeline` - Scheduling recommendations

**Why First (Sequential):** All other specialists depend on campaign parameters (objectives, budget, timeline, channels).

---

### 2. Audience Intelligence Specialist

**Domain Expertise:** Customer segmentation and behavioral targeting

**Responsibilities:**
- Customer segmentation (demographics, behavior, purchase history, engagement)
- Persona matching to products and campaigns
- Channel preference detection (who's active on which platform)
- Behavioral targeting (browse history, cart abandonment, purchase patterns)
- Lookalike audience suggestions
- Custom audience creation for retargeting
- Geographic and temporal targeting

**Reusable For:**
- All marketing campaigns
- Customer retention strategies
- Personalization engines
- Loyalty programs
- Email marketing
- Retargeting campaigns

**Output Model:** `AudienceTargetingDraft`

**Tools:**
- `segment_customers` - Create customer segments from CRM/purchase data
- `analyze_channel_preferences` - Detect where audiences are active
- `identify_behavioral_patterns` - Purchase cycles, engagement patterns
- `generate_lookalike_audiences` - Expansion strategies

**Note:** Different from existing **Market Intelligence Specialist**:
- Market Intelligence: Product positioning, pricing strategy, B2B industries (product-centric)
- Audience Intelligence: Customer behavior, segments, channel preferences (customer-centric)

**Why Parallel with Marketing Content:** Independent analysis, doesn't depend on content.

---

### 3. Marketing Content Specialist

**Domain Expertise:** Marketing-specific content creation and storytelling

**Responsibilities:**
- Campaign narratives and storytelling
- Value propositions and messaging
- Headlines and hooks
- Call-to-actions (CTAs) optimized for conversion
- Email marketing copy
- Blog post content
- Social media organic posts
- Brand voice consistency across campaigns

**Reusable For:**
- All campaigns
- Organic social media content
- Blog posts and articles
- Newsletters
- Press releases
- Landing pages
- Content marketing

**Output Model:** `MarketingContentDraft`

**Tools:**
- `generate_campaign_narrative` - Story arc for campaign
- `create_value_propositions` - Benefit-focused messaging
- `generate_headlines` - Multiple headline variants
- `optimize_ctas` - Conversion-optimized CTAs

**Note:** Different from existing **Content & SEO Specialist**:
- Content & SEO: Product descriptions, feature bullets, meta tags (product-focused)
- Marketing Content: Campaign stories, value props, CTAs (campaign-focused)

**Why Parallel with Audience Intelligence:** Independent content creation, doesn't need audience data for base content.

---

### 4. Platform Adaptation Specialist

**Domain Expertise:** Multi-platform content formatting and optimization

**Responsibilities:**
- Platform-specific content formatting
- Character limit compliance
- Image size and format optimization
- Platform best practices (hashtags, @mentions, emojis)
- Compliance with platform advertising policies

**Platform Coverage:**

**Facebook:**
- Feed posts (text + image/video)
- Stories (9:16 vertical)
- Reels (up to 90s)
- Carousel ads
- Collection ads

**Instagram:**
- Feed posts (1:1 square, 4:5 portrait)
- Stories (9:16 vertical)
- Reels (9:16, up to 90s)
- Shopping tags
- Hashtag optimization (#30 limit)

**YouTube:**
- Video titles (100 chars)
- Descriptions (5000 chars, keyword placement)
- Tags (500 chars)
- Thumbnail recommendations
- Cards and end screens

**X (Twitter):**
- Tweets (280 chars)
- Threads (sequential tweets)
- Twitter Cards (image + text previews)
- Hashtag strategy

**WhatsApp Business:**
- Business messages (templates)
- Status updates (image/video)
- Broadcast lists
- Catalog integration

**Amazon:**
- A+ Content (brand stories)
- Enhanced product descriptions
- Storefront content
- Sponsored product ads

**Google Ads:**
- Search ads (headlines, descriptions)
- Display ads (responsive ads)
- Shopping ads (product data feed)
- YouTube ads (video ad scripts)

**Website/Landing Pages:**
- Hero sections
- CTAs and forms
- Product showcases
- Conversion-optimized layouts

**Reusable For:**
- All content distribution (marketing + product updates)
- Social media management
- Paid advertising
- Product announcements
- Customer communications

**Output Model:** `PlatformContentVariantsDraft`

**Tools:**
- `format_for_platform` - Platform-specific formatting
- `optimize_images_for_platform` - Size/format/aspect ratio
- `validate_platform_compliance` - Policy checks
- `generate_hashtag_strategy` - Platform-specific hashtag recommendations

**Why Sequential after Phase 2:** Needs base content from Marketing Content Specialist and audience insights for targeting parameters.

---

### 5. Ad Copy Specialist

**Domain Expertise:** Paid advertising copy optimization

**Responsibilities:**
- Ad headlines (multiple variants for A/B testing)
- Ad descriptions (platform-specific character limits)
- CTAs optimized for conversion
- A/B test variant generation (3-5 variants per element)
- Ad compliance (platform advertising policies)
- Persuasion techniques (urgency, scarcity, social proof)
- Landing page copy alignment

**Reusable For:**
- All paid advertising campaigns
- Retargeting campaigns
- Sponsored content
- Influencer partnership ads
- Google Ads
- Social media ads
- Display advertising

**Output Model:** `AdCopyDraft`

**Tools:**
- `generate_ad_headlines` - Multiple headline variants
- `create_ad_descriptions` - Platform-specific ad copy
- `optimize_ad_ctas` - Conversion-focused CTAs
- `generate_ab_test_variants` - Multiple variants for testing
- `validate_ad_compliance` - Policy compliance checks

**Note:** Different from **Marketing Content Specialist**:
- Marketing Content: Campaign narratives, organic posts, storytelling (engagement-focused)
- Ad Copy: Paid ad copy, conversion-optimized, compliance-checked (conversion-focused)

**Why Parallel with Platform Adaptation:** Both need Phase 2 data, but independent execution.

---

### 6. Visual Assets Specialist (REUSED)

**Existing Specialist:** From Product Onboarding domain

**Why Reuse:**
- Already organizes product images
- Quality assessment capabilities
- Alt text generation (SEO)
- Image categorization (primary, lifestyle, closeup)

**Marketing Use Cases:**
- Select product images for campaigns
- Organize campaign creative assets
- Quality control for marketing materials
- SEO optimization for campaign images

**Future Enhancement (Phase 2):**
- Consider adding **Creative Asset Specialist** for AI-generated marketing visuals (graphics, videos, custom designs)

---

## Orchestration Pattern

Following guideline: **"Sequential for dependencies, Parallel for independent tasks"**

### Phase 1: Campaign Strategy (Sequential - MUST complete first)

**Specialist:** `campaign_strategy_specialist`

**Input:**
- Campaign brief from user
- Product(s) to promote (from product_families table)
- Budget constraints
- Timeline requirements

**Output:** `CampaignStrategyDraft`
- Objectives and KPIs
- Budget allocation by channel
- Timeline and milestones
- Channel mix recommendations

**Why First:** Defines campaign parameters that all other specialists need (objectives, budget, channels, timeline).

**PM Validation:**
- Verify budget is realistic
- Check timeline feasibility
- Confirm channel mix aligns with objectives

---

### Phase 2: Content & Audience Analysis (Parallel - independent)

Run simultaneously:

**2A: Audience Intelligence Specialist**
- Input: Campaign strategy, company customer data
- Output: `AudienceTargetingDraft`
- Analyzes who to target, on which channels

**2B: Marketing Content Specialist**
- Input: Campaign strategy, product details, brand voice
- Output: `MarketingContentDraft`
- Creates base campaign content (narratives, CTAs, headlines)

**2C: Visual Assets Specialist**
- Input: Product IDs, campaign type
- Output: `VisualAssetsDraft`
- Selects and organizes images for campaign

**Why Parallel:** These three analyses are independent:
- Audience analysis doesn't need content
- Content creation doesn't need audience data (targeting comes later)
- Visual selection can happen independently

---

### Phase 3: Platform & Ads (Parallel - needs Phase 2 data)

Run simultaneously:

**3A: Platform Adaptation Specialist**
- Input: Marketing content (Phase 2B), Platform list (Phase 1)
- Output: `PlatformContentVariantsDraft`
- Formats content for each platform

**3B: Ad Copy Specialist**
- Input: Campaign strategy (Phase 1), Marketing content (Phase 2B), Audience insights (Phase 2A)
- Output: `AdCopyDraft`
- Creates paid ad variants

**Why Parallel:** Both need Phase 2 data but don't depend on each other.

**Why Sequential after Phase 2:** Need base content before formatting/optimizing.

---

### Phase 4: Synthesis (PM Responsibility)

**PM Combines:**
- Campaign strategy
- Audience targeting
- Marketing content
- Visual assets
- Platform variants
- Ad copy

**Output:** Unified `MarketingCampaignInput` (Pydantic model for persistence)

**Includes:**
- All campaign metadata
- All audience segments
- All content variants (8+ platforms)
- All ad copy variants
- Budget allocation
- Scheduling timeline

---

### Phase 5: HITL (PM Level)

**PM Presents:**
```
📢 Marketing Campaign Ready for Review

**Campaign:** [Name]
**Objective:** [Awareness/Conversion/Retention]
**Duration:** [Start] - [End]
**Budget:** $X,XXX

**Target Audience:**
- Segment 1: [Description] (Facebook, Instagram)
- Segment 2: [Description] (YouTube, X)
- Total reach: X,XXX customers

**Channel Mix:**
- Facebook: $XXX (Posts, Stories, Ads)
- Instagram: $XXX (Feed, Reels, Shopping)
- YouTube: $XXX (Video ads, Channel)
- X (Twitter): $XXX (Tweets, Ads)
- WhatsApp: $XXX (Business messages)
- Amazon: $XXX (Sponsored products)
- Google Ads: $XXX (Search, Display)

**Content Variants:** X platform-specific versions
**Ad Variants:** X A/B test variants

[Preview platform content...]

Approve / Edit / Reject?
```

**User Actions:**
- Approve → Proceed to persistence
- Edit → Modify fields, re-present
- Reject → Cancel workflow

---

### Phase 6: Atomic Persistence

**Tool:** `save_marketing_campaign`

**Persists Across Tables:**
- marketing_campaigns
- campaign_objectives
- campaign_audiences
- campaign_budget
- campaign_schedule
- campaign_content
- campaign_platform_variants
- campaign_ad_copy
- campaign_creative_assets
- campaign_channels

**All-or-Nothing Transaction:** Rollback on ANY failure.

**Returns:** `PersistenceResult` with campaign_id and all related IDs.

---

## Specialist Reusability Validation

Testing against: **"Which workflows will use this specialist?"**

| Specialist | Workflows | Reusable? |
|-----------|-----------|-----------|
| Campaign Strategy | Product launch, seasonal promo, brand awareness, retention, events, influencer campaigns | ✅ 6+ workflows |
| Audience Intelligence | All campaigns, retention, personalization, loyalty, email marketing, retargeting | ✅ 6+ workflows |
| Marketing Content | Campaigns, organic social, blogs, newsletters, PR, landing pages | ✅ 6+ workflows |
| Platform Adaptation | All content distribution (marketing + product updates + announcements) | ✅ 5+ workflows |
| Ad Copy | All paid advertising, retargeting, sponsored content, influencer ads, partnerships | ✅ 5+ workflows |
| Visual Assets | Product marketing, campaigns, social content, announcements | ✅ 5+ workflows |

**All specialists pass reusability test (3+ workflows minimum).**

---

## PM State After Marketing Integration

### Current Specialists (11 Total)

**Product Onboarding Domain (5):**
1. Product Architecture Specialist
2. Taxonomy Specialist
3. Market Intelligence Specialist
4. Visual Assets Specialist
5. Content & SEO Specialist

**Marketing Domain (6):**
6. Campaign Strategy Specialist
7. Audience Intelligence Specialist
8. Marketing Content Specialist
9. Platform Adaptation Specialist
10. Ad Copy Specialist
11. Visual Assets Specialist (shared/reused)

### PM Persistence Tools (2)

```python
pm_tools = [
    create_save_product_family_tool(storage),    # Product Onboarding
    create_save_marketing_campaign_tool(storage), # Marketing (NEW)
]
```

### HITL Configuration

```python
interrupt_configs = {
    "save_product_family": True,      # Product Onboarding
    "save_marketing_campaign": True,  # Marketing (NEW)
}
```

---

## Architecture Decisions & Trade-Offs

### Decision 1: Number of Marketing Specialists

**Option A:** 3 Combined Specialists
- Content Specialist (combines marketing content + ad copy)
- Platform Specialist (platform adaptation)
- Audience Specialist

**Option B:** 5 Focused Specialists (CHOSEN)
- Campaign Strategy
- Audience Intelligence
- Marketing Content
- Platform Adaptation
- Ad Copy

**Rationale for B:**
- Clear domain boundaries
- Marketing Content vs Ad Copy: Different expertise (storytelling vs conversion optimization)
- Better reusability across workflows
- Easier to maintain and extend
- Follows single responsibility principle

---

### Decision 2: Creative Asset Generation

**Option A:** Add Creative Asset Specialist (Phase 1)
- Generates custom graphics, videos, animations with AI (DALL-E, Midjourney, Runway)

**Option B:** Reuse Visual Assets Specialist (Phase 1) + Defer Creative Generation (Phase 2)

**Rationale for B:**
- Faster to market (reuse existing infrastructure)
- Visual Assets Specialist already handles product images
- Creative generation is complex (requires multiple AI integrations)
- Phase 1 focuses on campaign orchestration with existing assets
- Phase 2 can add custom creative generation

---

### Decision 3: Audience Intelligence vs Market Intelligence

**Question:** Why not combine into single Intelligence Specialist?

**Market Intelligence (Product Domain):**
- Product positioning
- Pricing strategy
- B2B industries
- Competitive analysis
- Product-market fit

**Audience Intelligence (Marketing Domain):**
- Customer segmentation
- Behavioral targeting
- Channel preferences
- Purchase patterns
- Customer-campaign fit

**Rationale for Separation:**
- Different data sources (product data vs customer data)
- Different use cases (product strategy vs campaign targeting)
- Reusable independently
- Clear domain separation

---

### Decision 4: Platform Coverage

**Included in Phase 1:**
- Facebook, Instagram, YouTube, X (Twitter), WhatsApp, Amazon, Google Ads, Website

**Deferred to Phase 2:**
- TikTok, LinkedIn, Pinterest, Snapchat, Reddit

**Rationale:**
- Phase 1 covers stated requirements (FB, IG, YT, X, WhatsApp, Amazon)
- 8 platforms is substantial for initial implementation
- Platform Adaptation Specialist is extensible (add platforms incrementally)
- Focus on quality over quantity

---

## Production-Grade Scope

Following guideline: **"Production-grade from day one, no MVP shortcuts"**

### Phase 1 Scope (In Scope)

✅ **Campaign Creation & Planning:**
- Objectives and KPIs
- Budget allocation
- Timeline and scheduling
- Channel mix optimization

✅ **Audience Targeting:**
- Customer segmentation
- Behavioral targeting
- Channel preference detection
- Lookalike audiences

✅ **Content Generation:**
- Campaign narratives
- Platform-specific formatting (8 platforms)
- Paid ad copy with A/B variants
- Visual asset organization

✅ **Persistence:**
- Atomic multi-table persistence
- HITL approval workflow
- Error handling and rollback

✅ **Quality Standards:**
- Platform compliance checks
- Brand voice alignment
- Budget validation
- Timeline feasibility checks

---

### Phase 2 Scope (Deferred)

**Performance & Analytics:**
- Campaign performance tracking
- Real-time metrics dashboard
- Conversion attribution
- ROAS calculation

**Optimization:**
- A/B test management and analysis
- Automated budget optimization
- Audience expansion recommendations
- Content performance insights

**Creative Generation:**
- AI-generated graphics (DALL-E, Midjourney)
- AI-generated videos (Runway, Synthesia)
- Custom animations and motion graphics
- Brand asset library

**Advanced Targeting:**
- Predictive customer lifetime value
- Churn prediction and prevention
- Dynamic audience creation
- Cross-campaign attribution

**Additional Platforms:**
- TikTok, LinkedIn, Pinterest, Snapchat, Reddit

---

## Open Questions for Data Model Design

1. **Customer Data Model:**
   - Do we have existing customer/user tables?
   - How do we link campaigns to customer segments?
   - Where do we store behavioral data (purchases, engagement)?

2. **Product-Campaign Relationships:**
   - How do campaigns reference products? (many-to-many?)
   - Can one campaign promote multiple products?
   - How do we handle product families vs individual SKUs in campaigns?

3. **Multi-Tenancy:**
   - Single company or multiple companies?
   - How do we isolate campaign data by company?

4. **Historical Data:**
   - Do we version campaigns (drafts vs published)?
   - Do we archive old campaigns?
   - How long do we retain campaign data?

5. **Performance Data:**
   - Where do we store metrics (separate from campaign data)?
   - Real-time vs batch updates?
   - Integration with platform APIs (Meta, Google, YouTube)?

---

## Next Steps

**CRITICAL:** Before implementation, we need to:

1. **Design Enterprise-Grade Data Model**
   - Analyze existing database schema
   - Identify reuse opportunities
   - Design normalized campaign tables
   - Define relationships (products, customers, campaigns)
   - Plan for future workflows (analytics, optimization)

2. **Discuss "Draft" Suffix Pattern**
   - Rationale for specialist output models ending in "Draft"
   - When to use Draft vs final models
   - Data flow from Draft → Input → Persisted

3. **Validate Against Future Workflows**
   - Ensure data model supports Phase 2 features
   - Plan for extensibility
   - Consider analytics and reporting requirements

---

**Status:** Analysis complete, pending data model architecture discussion.
