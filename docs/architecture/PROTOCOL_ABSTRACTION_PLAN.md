# Protocol Abstraction Plan

**Status:** PLANNED
**Date:** 2025-12-29
**Context:** Agent prompts abstracted; protocols have same copy-paste risk

---

## Problem

Protocols contain product-specific examples (PET jar, honeycomb, Rs prices) that LLMs copy-paste into outputs. Protocols are loaded into agent context via `load_protocol`, so they face identical risk as agent prompts.

---

## Scope

**Total:** 171 product-specific matches across 20 protocol files

**Exclude:** Tool mastery protocols (`shared/tool_mastery/`) - tool syntax is intentional

---

## Priority Order

| Phase | Files | Matches | Rationale |
|-------|-------|---------|-----------|
| **P0** | `pm/coordination_patterns` | 55 | PM loads every workflow |
| **P1** | `catalog/visual_analysis`, `catalog/variant_management`, `shared/hitl` | 43 | Core workflow + cross-cutting |
| **P2** | `catalog/attribute_extraction`, `pm/conflict_resolution`, `pm/hitl`, `product/market_intelligence` | 37 | Supporting protocols |
| **P3** | 12 remaining files | 36 | Lower frequency |

---

## Abstraction Patterns

| Current | Abstracted |
|---------|------------|
| `PET jar`, `glass jar` | `[product type]` |
| `honeycomb texture` | `[texture pattern]` |
| `Rs 38`, `Rs 45` | `[Currency] [Amount]` |
| `PET Kitchen Storage` | `[Family Name]` |
| `Pavisha` | `[Brand]` |
| `visual_analysis_pet_jar.md` | `visual_analysis_[product].md` |
| `500ml`, `1L` | `[Size A]`, `[Size B]` |

---

## Validation

After each phase:
1. `grep -ri "PET\|honeycomb\|Rs [0-9]\|Pavisha" protocols/` should show decreasing matches
2. Run autonomous testing framework
3. Verify agents still construct correct tool calls

---

## Execution

Each phase is a separate commit:
- `refactor(protocols): abstract P0 - coordination_patterns`
- `refactor(protocols): abstract P1 - visual_analysis, variant_management, hitl`
- etc.
