# Test Scenarios Catalog

Living document of all test scenarios. YAML is source of truth, synced to Supabase `test_scenarios` table.

**Last Updated:** 2025-01-08

---

## System Architecture Reference

**Before creating/evaluating scenarios, understand the two-phase architecture:**

```text
PHASE 1: INTELLIGENCE (Wave-based)
  1. PM loads discovery_mindset + resource_efficiency protocols
  2. PM downloads media if [media_id: xxx] present
  3. PM builds dependency graph from user intent
  4. PM delegates to analysts in waves:
     - Wave 1: visual_analyst (if image present)
     - Wave 2: product_analyst || catalog_analyst (parallel if both needed)
  5. Analysts load their protocols, write findings to files

APPROVAL GATE:
  6. PM loads synthesis protocol
  7. PM reads analysis files (read_file)
  8. PM synthesizes findings, detects conflicts
  9. PM presents to user with OPEN-ENDED question (no numbered options)
  10. PM waits for user response

PHASE 2: EXECUTION (Serial, after approval)
  11. PM loads execution_flows protocol
  12. PM delegates to specialists based on flow (A-E):
      - creative_specialist -> asset creation with HITL
      - catalog_specialist -> record creation with HITL
  13. Specialists verify analyst work, execute with HITL
```

---

## Schema

```yaml
scenario_id: string          # Unique ID (e.g., PM-01, HITL-01)
name: string                 # Human-readable name
category: string             # PM_ANALYSIS | PM_GATE | PM_EXECUTION | ANALYST | SPECIALIST | HITL | EDGE
type: string                 # static | data_driven | replay | image_based
priority: string             # P0 (critical) | P1 (high) | P2 (medium) | P3 (low)
regression: boolean          # Include in regression suite
tags: list[string]           # Searchable tags
description: string          # What this scenario tests
message: string              # User message to send
media_query: string          # Optional: Supabase query for media
data_query: string           # Optional: Supabase query for test data
expected:
  phase: string              # Which phase this tests
  protocols_loaded: list     # Protocols PM should load
  waves: list                # Expected wave execution
  approval_gate: boolean     # Should hit approval gate
  execution_flow: string     # A, B, C, D, or E (if execution phase)
success_criteria: list       # Specific criteria to check
```

---

## PM Analysis Phase Scenarios

### PM-01: Image + Unknown Product (Full Analysis Chain)

```yaml
scenario_id: PM-01
name: Image with Unknown Product - Full Analysis
category: PM_ANALYSIS
type: image_based
priority: P0
regression: true
tags: [analysis, image, full-chain, wave-execution]
description: |
  Tests PM's complete analysis phase with unknown product.
  PM should: load protocols -> download media -> V -> P || C in waves.
media_query: |
  SELECT storage_path FROM product_assets
  WHERE asset_type = 'image'
  ORDER BY RANDOM() LIMIT 1
message: "Add this to the catalog"
expected:
  phase: analysis
  protocols_loaded: [discovery_mindset, resource_efficiency]
  waves:
    - wave_1: [visual_analyst]
    - wave_2: [product_analyst, catalog_analyst]  # parallel
  approval_gate: true
  execution_flow: E  # images first (after approval)
success_criteria:
  - PM loads discovery_mindset protocol as FIRST action
  - PM loads resource_efficiency protocol
  - PM downloads media (if media_id present)
  - PM delegates to visual_analyst FIRST (Wave 1)
  - PM WAITS for visual_analyst to complete
  - PM delegates to product_analyst AND catalog_analyst (Wave 2, parallel)
  - PM reads analysis files at approval gate
  - PM synthesizes findings (not concatenates)
  - PM presents OPEN-ENDED question (no numbered options)
```

### PM-02: Image + Known Product (Skip Product Research)

```yaml
scenario_id: PM-02
name: Image with Known Product - Optimized Chain
category: PM_ANALYSIS
type: image_based
priority: P1
regression: true
tags: [analysis, image, optimized, known-product]
description: |
  Tests PM's optimization when product identity is known.
  Should skip product_analyst when user provides identity.
media_query: |
  SELECT pa.storage_path, p.name as product_name
  FROM product_assets pa
  JOIN products p ON pa.product_id = p.id
  ORDER BY RANDOM() LIMIT 1
message: "Add this [PRODUCT_NAME] variant to catalog"
expected:
  phase: analysis
  protocols_loaded: [discovery_mindset, resource_efficiency]
  waves:
    - wave_1: [visual_analyst]
    - wave_2: [catalog_analyst]  # product_analyst NOT needed
  approval_gate: true
success_criteria:
  - PM recognizes user provided product identity
  - PM skips product_analyst (not needed for known product)
  - PM delegates visual_analyst -> catalog_analyst
  - Catalog analyst verifies family fit
```

### PM-03: Text Only - Catalog Query

```yaml
scenario_id: PM-03
name: Text Only Catalog Query
category: PM_ANALYSIS
type: static
priority: P1
regression: true
tags: [analysis, text-only, catalog-query]
description: |
  Tests PM handling of text-only catalog queries.
  No image = no visual_analyst needed.
message: "What families do we have for glass bottles?"
expected:
  phase: analysis
  protocols_loaded: [discovery_mindset, resource_efficiency]
  waves:
    - wave_1: [catalog_analyst]
  approval_gate: false  # query, not action
success_criteria:
  - PM loads protocols first
  - PM identifies this as catalog query (no execution needed)
  - PM delegates to catalog_analyst only
  - PM presents findings directly (no approval gate for queries)
  - PM does NOT delegate to specialists (read-only query)
```

### PM-04: Text Only - Market Research

```yaml
scenario_id: PM-04
name: Text Only Market Research
category: PM_ANALYSIS
type: static
priority: P2
regression: true
tags: [analysis, text-only, product-research]
description: |
  Tests PM handling of external research requests.
message: "What's the HSN code for PET bottles?"
expected:
  phase: analysis
  protocols_loaded: [discovery_mindset, resource_efficiency]
  waves:
    - wave_1: [product_analyst]
  approval_gate: false  # query, not action
success_criteria:
  - PM identifies this as external research request
  - PM delegates to product_analyst only
  - PM presents findings directly
```

### PM-05: Image + Catalog First (Verification Before Visual)

```yaml
scenario_id: PM-05
name: Catalog Verification Before Visual
category: PM_ANALYSIS
type: image_based
priority: P2
regression: true
tags: [analysis, image, catalog-first, verification]
description: |
  Tests PM's ability to check catalog BEFORE visual when user
  references specific existing product.
media_query: |
  SELECT storage_path FROM product_assets
  WHERE asset_type = 'image'
  ORDER BY RANDOM() LIMIT 1
message: "Is this the same as our Premium Glass Jar?"
expected:
  phase: analysis
  protocols_loaded: [discovery_mindset, resource_efficiency]
  waves:
    - wave_1: [catalog_analyst]  # verify "Premium Glass Jar" first
    - wave_2: [visual_analyst]   # then compare
  approval_gate: false  # comparison query
success_criteria:
  - PM recognizes user references existing product
  - PM checks catalog FIRST (find Premium Glass Jar)
  - PM THEN delegates to visual_analyst with catalog context
  - PM compares and presents findings
```

### PM-06: Multiple Images - Relationship Detection

```yaml
scenario_id: PM-06
name: Multiple Images Relationship Detection
category: PM_ANALYSIS
type: data_driven
priority: P1
regression: true
tags: [analysis, multi-image, relationship]
description: |
  Tests PM's handling of multiple images.
  visual_analyst must determine relationship first.
data_query: |
  SELECT array_agg(storage_path) as paths
  FROM (
    SELECT storage_path FROM product_assets
    WHERE asset_type = 'image'
    ORDER BY RANDOM() LIMIT 3
  ) sub
message: "Add all of these"
expected:
  phase: analysis
  protocols_loaded: [discovery_mindset, resource_efficiency, multi_image]
  waves:
    - wave_1: [visual_analyst]  # relationship detection
    - wave_2: depends on relationship
  approval_gate: true
success_criteria:
  - PM downloads ALL media first
  - PM delegates to visual_analyst with ALL paths
  - visual_analyst determines relationship (angles/variants/different)
  - PM loads multi_image protocol after visual returns
  - PM routes based on relationship finding
```

### PM-07: Cold Start Query

```yaml
scenario_id: PM-07
name: Cold Start - Ambiguous Reference
category: PM_ANALYSIS
type: static
priority: P1
regression: true
tags: [analysis, cold-start, clarification]
description: |
  Tests PM's behavior when user references something vague.
  PM should research OR clarify, not assume.
message: "Help me with the bottles"
expected:
  phase: analysis
  protocols_loaded: [discovery_mindset, resource_efficiency]
  waves:
    - wave_1: [catalog_analyst]  # research what bottles exist
success_criteria:
  - PM does NOT assume specific bottles
  - PM delegates to catalog_analyst to research
  - PM presents findings with clarification request
  - PM does NOT hallucinate product details
```

---

## PM Approval Gate Scenarios

### GATE-01: Synthesis and Presentation

```yaml
scenario_id: GATE-01
name: Approval Gate - Proper Synthesis
category: PM_GATE
type: image_based
priority: P0
regression: true
tags: [approval-gate, synthesis, presentation]
description: |
  Tests PM's behavior at approval gate.
  Must read files, synthesize, present open-ended question.
media_query: |
  SELECT storage_path FROM product_assets
  WHERE asset_type = 'image'
  ORDER BY RANDOM() LIMIT 1
message: "Add this product"
expected:
  phase: approval_gate
  protocols_loaded: [synthesis]  # at gate
  approval_gate: true
success_criteria:
  - PM loads synthesis protocol at approval gate
  - PM calls read_file on analysis outputs (NOT relying on summaries)
  - PM synthesizes across dimensions (identity, placement, compliance, positioning)
  - PM detects any conflicts between analysts
  - PM presents with OPEN-ENDED question ("What would you like to do next?")
  - PM does NOT present numbered options (constrains user)
```

### GATE-02: Conflict Detection and Surfacing

```yaml
scenario_id: GATE-02
name: Approval Gate - Conflict Handling
category: PM_GATE
type: static
priority: P1
regression: true
tags: [approval-gate, conflict, synthesis]
description: |
  Tests PM's conflict detection when analysts disagree.
  Example: visual says "premium" but catalog matches "utility".
message: "[Simulated conflict scenario - use trace with known conflict]"
expected:
  phase: approval_gate
  protocols_loaded: [synthesis]
success_criteria:
  - PM detects positioning conflict
  - PM surfaces conflict to user (doesn't resolve silently)
  - PM presents options with rationale
  - PM waits for user direction
```

### GATE-03: User Context Contradiction

```yaml
scenario_id: GATE-03
name: Approval Gate - User Context Wins
category: PM_GATE
type: data_driven
priority: P1
regression: true
tags: [approval-gate, verification-pivot, user-context]
description: |
  Tests PM's handling when analyst findings contradict user's explicit context.
  User says "existing" but catalog says "not found".
data_query: |
  SELECT 'NonExistentProduct_' || gen_random_uuid()::text as fake_name
message: "Update our [FAKE_NAME] product"
expected:
  phase: approval_gate
success_criteria:
  - catalog_analyst reports product not found
  - PM does NOT proceed with creation
  - PM asks user about discrepancy
  - PM presents: "I couldn't find [product]. Did you mean...?"
```

---

## PM Execution Phase Scenarios

### EXEC-01: Flow E - Images First (Standard)

```yaml
scenario_id: EXEC-01
name: Execution Flow E - Images First
category: PM_EXECUTION
type: image_based
priority: P0
regression: true
tags: [execution, flow-e, creative-first]
description: |
  Tests standard execution flow: Creative -> Catalog.
  After user approves analysis, PM delegates to creative first.
message: "[Continue from approved analysis] Yes, proceed"
expected:
  phase: execution
  protocols_loaded: [execution_flows]
  execution_flow: E
success_criteria:
  - PM loads execution_flows protocol
  - PM delegates to creative_specialist FIRST
  - PM passes all analysis files + image path
  - PM waits for creative HITL (asset approval)
  - PM captures asset_id from creative response
  - PM delegates to catalog_specialist with asset_id
  - PM waits for catalog HITL (data approval)
  - Two-stage HITL maintained
```

### EXEC-02: Flow D - Catalog First

```yaml
scenario_id: EXEC-02
name: Execution Flow D - Catalog First
category: PM_EXECUTION
type: image_based
priority: P1
regression: true
tags: [execution, flow-d, catalog-first]
description: |
  Tests catalog-first flow when user explicitly requests.
message: "[At approval gate] Create the catalog entry first, then images"
expected:
  phase: execution
  protocols_loaded: [execution_flows]
  execution_flow: D
success_criteria:
  - PM recognizes user's explicit flow preference
  - PM delegates to catalog_specialist FIRST (no asset_id)
  - PM captures product_id from catalog response
  - PM delegates to creative_specialist with product_id
  - Creative creates asset AND product_assets junction
```

### EXEC-03: Flow A - Catalog Only

```yaml
scenario_id: EXEC-03
name: Execution Flow A - Catalog Only
category: PM_EXECUTION
type: image_based
priority: P1
regression: true
tags: [execution, flow-a, catalog-only]
description: |
  Tests catalog-only flow (no image processing).
message: "[At approval gate] Just add to catalog, skip the image"
expected:
  phase: execution
  protocols_loaded: [execution_flows]
  execution_flow: A
success_criteria:
  - PM recognizes user wants catalog only
  - PM delegates to catalog_specialist only
  - PM does NOT delegate to creative_specialist
  - Product created without asset link
```

### EXEC-04: Flow B - Asset Only

```yaml
scenario_id: EXEC-04
name: Execution Flow B - Asset Only
category: PM_EXECUTION
type: image_based
priority: P2
regression: false
tags: [execution, flow-b, asset-only]
description: |
  Tests asset-only flow (no catalog entry).
message: "[At approval gate] Just process the image, I'll catalog later"
expected:
  phase: execution
  protocols_loaded: [execution_flows]
  execution_flow: B
success_criteria:
  - PM recognizes user wants asset only
  - PM delegates to creative_specialist only
  - Asset created but not linked to catalog
```

### EXEC-05: Direct Update (Skip Analysis)

```yaml
scenario_id: EXEC-05
name: Direct Update - Complete Information
category: PM_EXECUTION
type: data_driven
priority: P1
regression: true
tags: [execution, direct, skip-analysis]
description: |
  Tests PM's optimization when user provides complete information.
  Should skip analysis phase entirely.
data_query: |
  SELECT id, name, sku, price FROM products
  WHERE is_active = true
  ORDER BY RANDOM() LIMIT 1
message: "Update product [SKU] price to Rs 599"
expected:
  phase: execution
  protocols_loaded: [execution_flows]
  approval_gate: false  # direct execution after confirmation
success_criteria:
  - PM recognizes complete information provided
  - PM does NOT delegate to analysts (all info available)
  - PM confirms with user before update
  - PM delegates to catalog_specialist directly
```

---

## Analyst Scenarios

### ANALYST-01: Visual Analyst Protocol Loading

```yaml
scenario_id: ANALYST-01
name: Visual Analyst - Protocol Loading
category: ANALYST
type: image_based
priority: P0
regression: true
tags: [analyst, visual, protocol-loading]
description: |
  Tests visual_analyst loads correct protocols before analysis.
media_query: |
  SELECT storage_path FROM product_assets
  WHERE asset_type = 'image' LIMIT 1
message: "[Delegated from PM] Analyze image for CATALOG domain"
expected:
  protocols_loaded: [visual_analysis, view_image, resource_efficiency, input_validation]
success_criteria:
  - visual_analyst loads visual_analysis protocol (domain='catalog') FIRST
  - visual_analyst loads view_image protocol
  - visual_analyst calls view_image tool
  - visual_analyst writes findings to file
  - visual_analyst returns file path to PM
```

### ANALYST-02: Catalog Analyst - Chain Link Behavior

```yaml
scenario_id: ANALYST-02
name: Catalog Analyst - Reads Upstream Files
category: ANALYST
type: image_based
priority: P0
regression: true
tags: [analyst, catalog, chain-link, file-reading]
description: |
  Tests catalog_analyst reads upstream analysis files before querying.
message: "[Delegated from PM with file paths] Find family fit"
expected:
  protocols_loaded: [business_context, family_fit, read_data, resource_efficiency]
success_criteria:
  - catalog_analyst loads protocols FIRST
  - catalog_analyst reads visual_analysis.md (upstream file)
  - catalog_analyst extracts search terms from visual findings
  - catalog_analyst queries catalog using extracted terms
  - catalog_analyst writes findings to file
```

### ANALYST-03: Multi-Item Detection

```yaml
scenario_id: ANALYST-03
name: Visual Analyst - Multi-Item Detection
category: ANALYST
type: image_based
priority: P1
regression: true
tags: [analyst, visual, multi-item, bbox]
description: |
  Tests visual_analyst properly detects multiple items and outputs bounding boxes.
media_query: |
  SELECT storage_path FROM product_assets
  WHERE asset_type = 'image'
  ORDER BY RANDOM() LIMIT 1
message: "[Image with multiple products] Analyze for CATALOG domain"
expected:
  protocols_loaded: [visual_analysis, view_image]
success_criteria:
  - visual_analyst detects multiple items
  - visual_analyst outputs MULTI-ITEM ASSESSMENT format
  - visual_analyst includes bounding box coordinates for EACH item
  - visual_analyst classifies relationship (VARIANTS/COLLECTION/COMPONENTS)
```

---

## Specialist Scenarios

### SPEC-01: Catalog Specialist - Verify Analyst Work

```yaml
scenario_id: SPEC-01
name: Catalog Specialist - Verifies Before Writing
category: SPECIALIST
type: data_driven
priority: P0
regression: true
tags: [specialist, catalog, verification, protocol]
description: |
  Tests catalog_specialist verifies analyst recommendations
  before writing to database.
message: "[Delegated from PM] Create product entry"
expected:
  protocols_loaded: [business_context, family_fit, duplicate_prevention, write_data, schema_discovery]
success_criteria:
  - catalog_specialist loads protocols FIRST
  - catalog_specialist reads analyst files
  - catalog_specialist runs OWN verification (family_fit, duplicate check)
  - catalog_specialist calls inspect_schema BEFORE write_data
  - catalog_specialist submits with HITL (write_data triggers approval)
```

### SPEC-02: Creative Specialist - Asset Creation with HITL

```yaml
scenario_id: SPEC-02
name: Creative Specialist - Asset HITL
category: SPECIALIST
type: image_based
priority: P0
regression: true
tags: [specialist, creative, hitl, asset]
description: |
  Tests creative_specialist creates asset with proper HITL.
media_query: |
  SELECT storage_path FROM product_assets
  WHERE asset_type = 'image' LIMIT 1
message: "[Delegated from PM] Create catalog hero shot"
expected:
  protocols_loaded: [catalog_visual, view_image, resource_efficiency]
success_criteria:
  - creative_specialist loads protocols FIRST
  - creative_specialist processes image
  - creative_specialist triggers HITL for image approval
  - creative_specialist returns asset_id to PM (not just path)
```

---

## HITL Scenarios

### HITL-01: Creative Asset Approval

```yaml
scenario_id: HITL-01
name: HITL - Approve Creative Asset
category: HITL
type: static
priority: P0
regression: true
tags: [hitl, creative, approval]
description: |
  Tests user approval of creative asset.
  Asset should be saved, asset_id returned.
message: "Looks good"
expected:
  phase: hitl_response
success_criteria:
  - creative_specialist receives approval
  - Asset record created in database
  - asset_id returned to PM
  - PM proceeds to catalog_specialist (if full flow)
```

### HITL-02: Creative Asset Rejection

```yaml
scenario_id: HITL-02
name: HITL - Reject Creative Asset
category: HITL
type: static
priority: P0
regression: true
tags: [hitl, creative, rejection, iteration]
description: |
  Tests user rejection of creative asset.
  Creative should iterate, not PM.
message: "No, the background should be white"
expected:
  phase: hitl_response
success_criteria:
  - creative_specialist receives rejection with reason
  - creative_specialist loads hitl protocol
  - creative_specialist parses feedback
  - creative_specialist iterates on image (fixes background)
  - creative_specialist resubmits for HITL
  - PM is NOT involved in iteration
```

### HITL-03: Catalog Data Approval

```yaml
scenario_id: HITL-03
name: HITL - Approve Catalog Data
category: HITL
type: static
priority: P0
regression: true
tags: [hitl, catalog, approval]
description: |
  Tests user approval of catalog data (second stage).
message: "Yes, save it"
expected:
  phase: hitl_response
success_criteria:
  - catalog_specialist receives approval
  - Product record created in database
  - product_assets junction created (if asset_id provided)
  - Workflow completes
```

### HITL-04: Catalog Data Rejection with Edit

```yaml
scenario_id: HITL-04
name: HITL - Reject Catalog with Edit
category: HITL
type: static
priority: P1
regression: true
tags: [hitl, catalog, rejection, edit]
description: |
  Tests user rejection of catalog data with specific edit request.
message: "Change the price to Rs 499"
expected:
  phase: hitl_response
success_criteria:
  - catalog_specialist receives rejection with reason
  - catalog_specialist loads hitl protocol
  - catalog_specialist identifies specific field to change
  - catalog_specialist updates ONLY that field
  - catalog_specialist resubmits with "REVISED:" marker
```

### HITL-05: Bare Cancellation

```yaml
scenario_id: HITL-05
name: HITL - Bare Cancel
category: HITL
type: static
priority: P1
regression: true
tags: [hitl, cancel, no-retry]
description: |
  Tests user cancellation without reason.
  Specialist should NOT retry.
message: "Cancel"
expected:
  phase: hitl_response
success_criteria:
  - Specialist receives cancellation
  - Specialist loads hitl protocol
  - Specialist returns [HITL CANCELED] to PM
  - Specialist does NOT retry
  - PM acknowledges cancellation to user
```

---

## Edge Case Scenarios

### EDGE-01: Missing Media Download

```yaml
scenario_id: EDGE-01
name: Edge - Media Not Downloaded
category: EDGE
type: static
priority: P1
regression: true
tags: [edge-case, media, download]
description: |
  Tests PM behavior when media_id present but not downloaded.
  PM MUST download before delegating.
message: "Add this [media_id: wamid_test123]"
expected:
  phase: analysis
success_criteria:
  - PM detects [media_id: xxx] in message
  - PM calls download_whatsapp_media BEFORE delegating
  - PM does NOT delegate to visual_analyst without storage_path
```

### EDGE-02: Protocol Not Loaded

```yaml
scenario_id: EDGE-02
name: Edge - Detect Protocol Skip
category: EDGE
type: static
priority: P0
regression: true
tags: [edge-case, protocol, violation]
description: |
  Monitors for protocol loading violations.
  Any agent that queries/writes without loading protocols is a bug.
message: "[Any standard scenario]"
success_criteria:
  - Trace shows load_protocol as FIRST tool call for every agent
  - No agent queries database before loading protocols
  - No agent writes before loading protocols + schema discovery
```

### EDGE-03: Ambiguous "Yes" Response

```yaml
scenario_id: EDGE-03
name: Edge - Ambiguous Confirmation
category: EDGE
type: static
priority: P2
regression: true
tags: [edge-case, ambiguous, confirmation]
description: |
  Tests PM handling of ambiguous "yes" after open-ended question.
message: "[After PM asks open-ended question] Yes"
expected:
  phase: approval_gate
success_criteria:
  - PM does NOT assume what user is approving
  - PM clarifies: "Just to confirm - you'd like me to [interpretation]?"
  - PM waits for explicit confirmation
```

### EDGE-04: Large Tool Results

```yaml
scenario_id: EDGE-04
name: Edge - Large Tool Result Handling
category: EDGE
type: static
priority: P2
regression: false
tags: [edge-case, large-result, truncation]
description: |
  Tests PM handling of truncated tool results.
  PM must read full file when results are truncated.
message: "[Scenario that produces large tool output]"
success_criteria:
  - PM detects "Tool result too large" message
  - PM calls read_file on the /large_tool_results/ path
  - PM does NOT proceed with only the 10-line preview
```

### EDGE-05: Empty or Invalid Input

```yaml
scenario_id: EDGE-05
name: Edge - Empty Message
category: EDGE
type: static
priority: P3
regression: true
tags: [edge-case, empty, validation]
description: |
  Tests PM handling of empty or whitespace messages.
message: "   "
success_criteria:
  - PM does NOT crash
  - PM asks user for input
  - PM does NOT delegate with empty context
```

### EDGE-06: Conflicting User Information

```yaml
scenario_id: EDGE-06
name: Edge - Contradictory User Input
category: EDGE
type: static
priority: P2
regression: true
tags: [edge-case, conflict, clarification]
description: |
  Tests PM handling of contradictory information from user.
message: "Add this new product with SKU ABC123 that already exists"
success_criteria:
  - PM detects contradiction ("new" vs "already exists")
  - PM clarifies with user before proceeding
  - PM does NOT guess user intent
```

---

## Integration Scenarios

### INT-01: Full Flow - Image to Catalog

```yaml
scenario_id: INT-01
name: Full Integration - Image to Catalog
category: INTEGRATION
type: image_based
priority: P0
regression: true
tags: [integration, full-flow, e2e]
description: |
  Tests complete flow from image to persisted catalog entry.
  Analysis -> Gate -> Creative HITL -> Catalog HITL -> Verify in DB.
media_query: |
  SELECT storage_path FROM product_assets
  WHERE asset_type = 'image'
  ORDER BY RANDOM() LIMIT 1
message: "Add this product to the catalog"
expected:
  phase: full_flow
  protocols_loaded: [discovery_mindset, synthesis, execution_flows]
  waves:
    - wave_1: [visual_analyst]
    - wave_2: [product_analyst, catalog_analyst]
  approval_gate: true
  execution_flow: E
success_criteria:
  - Phase 1 (Analysis) completes with all analysts
  - PM reaches approval gate with synthesis
  - [User approves]
  - Phase 2 (Execution) - Creative first
  - Creative HITL approved -> asset_id captured
  - Catalog second with asset_id
  - Catalog HITL approved -> product_id captured
  - Verify: product exists in Supabase
  - Verify: product_assets junction exists
```

### INT-02: Text-Only Update

```yaml
scenario_id: INT-02
name: Full Integration - Text Update
category: INTEGRATION
type: data_driven
priority: P1
regression: true
tags: [integration, text-only, update]
description: |
  Tests text-only update flow without image.
data_query: |
  SELECT id, name, sku, price FROM products
  WHERE is_active = true
  ORDER BY RANDOM() LIMIT 1
message: "Update [SKU] price to Rs [NEW_PRICE]"
expected:
  phase: execution
  approval_gate: false  # direct execution
success_criteria:
  - PM recognizes direct update (complete info)
  - PM confirms with user
  - [User confirms]
  - PM delegates to catalog_specialist
  - Catalog HITL approved
  - Verify: price updated in Supabase
```

---

## Replay Scenarios (From Production Failures)

### REPLAY-TEMPLATE

```yaml
scenario_id: REPLAY-[workflow_outcome_id]
name: Replay - [error_type] - [date]
category: REPLAY
type: replay
priority: P1
regression: false
tags: [replay, production-failure]
source_query: |
  SELECT trace_id, message_text, media_id, error_type, error_message
  FROM workflow_outcomes
  WHERE id = '[workflow_outcome_id]'
message: "[From workflow_outcomes.message_text]"
original_error:
  type: "[error_type]"
  message: "[error_message]"
success_criteria:
  - Same scenario no longer fails
  - Root cause addressed
```

---

## Data-Driven Templates

### Template: Random Product Test

```yaml
scenario_id: DD-RANDOM-[n]
name: Random Product Catalog Flow
category: PM_ANALYSIS
type: data_driven
priority: P2
regression: false
tags: [data-driven, random, full-flow]
data_query: |
  SELECT p.name, p.sku, pa.storage_path
  FROM products p
  JOIN product_assets pa ON pa.product_id = p.id
  WHERE p.is_active = true AND pa.asset_type = 'image'
  ORDER BY RANDOM() LIMIT 1
message: "Add a product similar to [PRODUCT_NAME]"
success_criteria:
  - Full analysis chain executes
  - Approval gate reached
  - No errors in trace
```

---

## Scenario Maintenance

### Adding New Scenarios

1. Understand which phase/behavior you're testing
2. Create scenario in appropriate category
3. Define expected protocols, waves, gates
4. Run scenario, capture trace
5. Verify against success criteria
6. Add to relevant suite in SUITES.md

### Promoting to Regression

When fix verified:

1. Set `regression: true`
2. Add to `regression` suite
3. Create GitHub issue linking scenario to fix

### Retiring Scenarios

1. Move to "Retired" section
2. Remove from all suites
3. Document retirement reason

---

## Retired Scenarios

<!-- Move retired scenarios here with retirement reason -->
