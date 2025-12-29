# PM Behavior Validation Matrix

**Date:** 2025-12-29
**Status:** VALIDATED
**Scope:** All domains, agents, and scenarios

---

## 1. Protocol Loading

| Task Type | PM Loads | Domain | Status |
|-----------|----------|--------|--------|
| Image workflow (first message) | domain_awareness, discovery_mindset, coordination_patterns, resource_efficiency | pm | VALIDATED |
| Text query (first message) | domain_awareness, discovery_mindset, resource_efficiency | pm | VALIDATED |
| Continuation ("yes", "proceed") | NONE - already in context | - | VALIDATED |
| Agent result processing | NONE - continue workflow | - | VALIDATED |
| HITL feedback in agent response | hitl | shared | VALIDATED |

**Key validation:** PM uses `domain='pm'` for its own protocols, not `domain='catalog'`.

---

## 2. Domain Routing

| User Request | Route To | Dependency | Status |
|--------------|----------|------------|--------|
| Image + "add to catalog" | Visual -> Product -> Catalog | Sequential | VALIDATED |
| Image + "what is this?" | Visual -> Product | No catalog | VALIDATED |
| Image + "do we have this?" | Visual -> Catalog | No product | VALIDATED |
| Image + "process/hero shot" | Visual (optional) -> Creative | Skip analysts | VALIDATED |
| Text + "what IS this?" | product_analyst | External knowledge | VALIDATED |
| Text + "do WE have?" | catalog_analyst | Internal data | VALIDATED |
| Text + "update/delete" | catalog_specialist | Direct action | VALIDATED |

---

## 3. Sequential Delegation (Analysis Phase)

```
1. visual_analyst   -> WAIT -> visual_analysis.md
2. product_analyst  -> WAIT -> product_research.md (uses visual)
3. catalog_analyst  -> WAIT -> catalog_analysis.md (uses visual + product)
```

**Why sequential:** Each analyst NEEDS previous analyst's output.
- Product needs visual to know WHAT to research
- Catalog needs product to search with RICH CONTEXT

**Status:** VALIDATED in PM prompt (lines 141-167) and coordination_patterns

---

## 4. Approval Gate

| Component | Location | Status |
|-----------|----------|--------|
| Synthesis template | coordination_patterns lines 279-298 | VALIDATED |
| Open-ended question | "What would you like to do next?" | VALIDATED |
| No numbered options | Explicitly forbidden | VALIDATED |
| Conflict detection | coordination_patterns lines 269-277 | VALIDATED |

**PM prompt reference:** Lines 218-232 point to coordination_patterns for all details.

---

## 5. Flexible Execution Flows

| Flow | User Says | Step 1 | Step 2 | Status |
|------|-----------|--------|--------|--------|
| A: Catalog Only | "Just add to catalog" | catalog_specialist (no asset_id) | - | VALIDATED |
| B: Image Only (asset) | "Process the image" | creative_specialist | - | VALIDATED |
| C: Image Only (ephemeral) | "Download only" | creative_specialist (standalone) | - | VALIDATED |
| D: Catalog First | "Catalog first, then images" | catalog_specialist -> product_id | creative_specialist (links) | VALIDATED |
| E: Images First | "Images first" / "yes" / "full flow" | creative_specialist -> asset_id | catalog_specialist (links) | VALIDATED |

**Location:** coordination_patterns lines 154-216

---

## 6. ID Tracking

| Flow | Step 1 Returns | Pass to Step 2 | Step 2 Creates |
|------|----------------|----------------|----------------|
| Catalog first | product_id | product_id -> creative | Asset + junction |
| Images first | asset_id | asset_id -> catalog | Product + junction |

**Junction rule:** Both specialists can create product_assets junctions. Whoever runs second receives the existing ID.

**Validated in:**
- PM prompt line 232
- coordination_patterns lines 207-216
- asset_management lines 587-619
- creative_specialist lines 487-512
- catalog_specialist lines 56-62

---

## 7. Context Propagation

| Agent | Gets Image? | Gets Upstream Files? | Status |
|-------|-------------|---------------------|--------|
| visual_analyst | YES | - | VALIDATED |
| product_analyst | YES | visual_analysis.md | VALIDATED |
| catalog_analyst | YES | visual + product | VALIDATED |
| creative_specialist | YES | visual + product + catalog | VALIDATED |
| catalog_specialist | YES | ALL files + asset_id | VALIDATED |

**Validated in:** PM prompt lines 202-216, domain_awareness lines 179-193

---

## 8. HITL Signal Handling

| Marker | PM Action | Status |
|--------|-----------|--------|
| `[HITL RESOLVED]` | Continue workflow | VALIDATED |
| `## HITL FEEDBACK REQUIRES PM DIRECTION` | Go to user | VALIDATED |
| `[HITL CANCELED]` | Task abandoned | VALIDATED |
| `[HITL REDIRECT]` | Task change needed | VALIDATED |

**Validated in:** PM prompt lines 236-245, hitl.protocol comprehensive

---

## 9. Agent Integration

| Agent | Protocol Loading | File Output | Status |
|-------|-----------------|-------------|--------|
| visual_analyst | visual_analysis (catalog) | visual_analysis_{image}.md | VALIDATED |
| product_analyst | research_orchestration, market_intelligence, compliance_research | product_research_{item}.md | VALIDATED |
| catalog_analyst | business_context, family_fit, pricing, duplicate_prevention | catalog_analysis_{item}.md | VALIDATED |
| creative_specialist | product_photography, image_studio, asset_management | asset_id | VALIDATED |
| catalog_specialist | business_context, family_fit, pricing, asset_management | product_id | VALIDATED |

---

## 10. Cross-Reference Validation

| PM References | Protocol Contains | Match |
|---------------|-------------------|-------|
| "Synthesis template" | coordination_patterns lines 279-298 | YES |
| "Routing table" | coordination_patterns lines 154-216 (Flows A-E) | YES |
| "ID tracking" | coordination_patterns lines 207-216 | YES |
| "Delegation templates" | coordination_patterns lines 701-747 | YES |
| "Junction rule" | asset_management lines 587-619 | YES |

---

## Summary

**All validation points PASS.**

The PM prompt correctly:
1. Loads appropriate protocols for each task type
2. Routes to correct agents based on user intent
3. Delegates sequentially during analysis phase
4. Presents findings with open-ended question at approval gate
5. Routes flexibly based on user's actual request (Flows A-E)
6. Tracks and passes IDs between specialists
7. Propagates context (image + files) to every agent
8. Handles HITL signals from agents

The architecture maintains:
- Separation of concerns (prompts = principles, protocols = details)
- Two-stage HITL (image quality -> creative, catalog data -> catalog)
- Symmetric junction creation (either specialist can create product_assets)
- Full user flexibility (what to do, in what order)
