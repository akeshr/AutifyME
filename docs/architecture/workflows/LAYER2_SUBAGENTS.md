# Layer 2 — SubAgent Descriptions (Canonical)

This document defines the **SubAgent roster** used by the PM and the exact boundaries that keep delegation clean.

In runtime, the PM “sees” these as the `name` + `description` fields on each subagent spec returned by the factories in:

- `agents/src/autifyme_agents/analysts/*.py`
- `agents/src/autifyme_agents/specialists/*.py`

Layer 2 depends on the Layer 1 tool contract catalog:

- `docs/architecture/tools/LAYER1_TOOL_CATALOG.md`

## Analysts (Read-only)

### `visual_analyst`

- **ROLE**: Analyst (read-only)
- **MISSION**: Describe what is visible in images with high precision.
- **INPUTS**: Image path(s) when available (`inbox/...`, `pending/...`).
- **OUTPUTS**: Observations + uncertainties (no recommendations); write a report to thread dir if long.
- **TOOLS**: `view_image` (Type C)
- **GUARDRAILS**: No DB access; no pricing/taxonomy/action recommendations; no image editing.

### `product_analyst`

- **ROLE**: Analyst (read-only)
- **MISSION**: Convert an unknown product into market-grounded facts (name, specs, standards).
- **INPUTS**: Brand/model/keywords or an image path; jurisdiction/market when compliance matters.
- **OUTPUTS**: Source-backed brief with links + clear unknowns/assumptions; write report to thread dir if long.
- **TOOLS**: `research_product_tool` (Type A), `extract_web_content_tool` (Type A), `view_image` (Type C)
- **GUARDRAILS**: No internal DB reads/writes; no record creation; no image editing.

### `catalog_analyst`

- **ROLE**: Analyst (read-only)
- **MISSION**: Answer “What do we already have?” from our catalog database.
- **INPUTS**: What to compare against (keywords/attributes) and any candidate IDs; optional image paths.
- **OUTPUTS**: Ranked similar items + evidence (IDs/fields/aggregates); write results to thread dir if long.
- **TOOLS**: `inspect_schema` (Type A), `read_data` (Type A), `aggregate_data` (Type A), `view_image` (Type C)
- **GUARDRAILS**: No writes (`write_data`); no deep external research; no image editing.
- **Access scope**: Restricted to `CATALOG_ANALYST_TABLES` in `agents/src/autifyme_agents/analysts/catalog_analyst.py`.

## Specialists (Execution)

### `creative_specialist`

- **ROLE**: Specialist (execution)
- **MISSION**: Turn raw photos into marketplace-ready visuals (and optionally persist asset records).
- **INPUTS**: Source image `storage_path` (typically `inbox/...`) + creative intent (hero vs lifestyle) + constraints.
- **OUTPUTS**: Processed images (always local temp path; `pending/...` `storage_path` when storage configured) + production notes.
- **HITL**: If DB writes are enabled, proposes `write_data` and handles reject feedback (often prefixed `[HITL_FEEDBACK]`) by revising and resubmitting.
- **TOOLS**: `view_image` (Type C), `image_studio` (Type A); if storage enabled: `inspect_schema`/`read_data`/`write_data` (HITL, scoped).
- **GUARDRAILS**: No catalog/product/pricing/taxonomy CRUD; delegate catalog changes to `catalog_specialist`.
- **Access scope (authoritative)**: `CREATIVE_READ_TABLES` / `CREATIVE_WRITE_TABLES` in `agents/src/autifyme_agents/specialists/creative_specialist.py`.

### `catalog_specialist`

- **ROLE**: Specialist (execution)
- **MISSION**: Safely mutate the product catalog (schema-driven CRUD) with HITL approval.
- **INPUTS**: Target intent (create/update/delete), business goal, and IDs (or enough attributes to find them).
- **OUTPUTS**: A write plan + proposed `write_data` intent; after approval, executed results + created/updated IDs.
- **HITL**: Treats rejection feedback (often prefixed `[HITL_FEEDBACK]`) as requirements; revises and resubmits `write_data`.
- **TOOLS**: `inspect_schema`, `read_data`, `aggregate_data`, `write_data` (HITL), `view_image`, plus external research tools when needed.
- **GUARDRAILS**: No image processing; no ad-hoc SQL; always read-before-write.
- **Access scope (authoritative)**: `CATALOG_TABLES_CRUD` / `CATALOG_TABLES_READ_ONLY` / `CATALOG_TABLES_ALL` in `agents/src/autifyme_agents/specialists/catalog_specialist.py`.

## Delegation Output Expectations (Filesystem Protocol)

For any subagent (analyst or specialist):

- Return a short summary in-message.
- Write any long-form deliverable into the task thread directory (e.g., `workspace/thread_<id>/...`) and include the primary file path in the summary.
