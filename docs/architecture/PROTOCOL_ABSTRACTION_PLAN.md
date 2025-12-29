# Protocol Abstraction Plan

**Status:** PLANNED
**Date:** 2025-12-29

---

## Problem

Protocols contain product-specific examples that LLMs copy-paste into outputs.

---

## Three Content Types

| Type | Action | Example |
|------|--------|---------|
| **Example DATA** | ABSTRACT | `"PET jar"` -> `[product]`, `"Rs 45"` -> `[price]` |
| **Domain KNOWLEDGE** | KEEP | `"HSN 3923 for plastic"`, `"PET needs rake light"` |
| **Tool SYNTAX** | KEEP | `view_image(path="inbox/item.jpg")` |

**Key distinction:** Domain knowledge teaches correct patterns. Example data just fills slots.

---

## Scope

- **171 matches** across 20 files (including 3 in tool_mastery)
- Abstract example DATA only
- Keep domain knowledge tables, HSN references, material properties

---

## Priority

| Phase | Protocol | Matches |
|-------|----------|---------|
| P0 | `pm/coordination_patterns` | 55 |
| P1 | `catalog/visual_analysis`, `catalog/variant_management`, `shared/hitl` | 43 |
| P2 | Remaining 16 files | 73 |

---

## Placeholder Standards (match agent prompts)

| Current | Abstracted |
|---------|------------|
| `PET jar`, `glass bottle` | `[product]` |
| `Rs 38`, `Rs 45` | `[price]` |
| `Pavisha` | `[brand]` |
| `visual_analysis_pet_jar.md` | `visual_analysis_[product].md` |
| `500ml`, `1L` | `[size]` |
| `PET Kitchen Storage` | `[family]` |

---

## Validation

After abstraction: agents should still learn correct patterns from domain knowledge while not copying specific product names/prices.
