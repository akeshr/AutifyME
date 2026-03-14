# Layer 1 — Tool Catalog (Canonical)

This is the canonical, **agent-facing** documentation for Layer 1 tools.

## Global Return-Contract Types

Agents must not assume every tool returns `{success: ...}`.

- **Type A — Success-wrapped dict**: `{ "success": true, ... }` on success; `{ "success": false, "error": ..., "error_type": ..., "Agent Action": ... }` on failure.
- **Type B — Plain dict**: a normal dict without `success` envelope.
- **Type C — Multimodal blocks**: a list of `{type: "text"|"image_url", ...}` blocks.

## Data Engine Tools (Universal DB)

### `inspect_schema` (Type A)

- **Purpose**: Discover tables/columns/relationships so you don't guess schema.
- **Use when**: You're unsure about table names, column names/types, foreign keys, relation join syntax.
- **Don't use**: To fetch actual entity rows (use `read_data`).
- **Returns**: Type A (success-wrapped dict) with table/schema details.
- **Notes**: Prefer `details=["relationships"]` before using `relations` in `read_data`.

### `read_data` (Type A)

- **Purpose**: Universal DB read: query + search + joins + batch by IDs + pagination + counts.
- **Use when**:
  - Duplicate checks before any create
  - Resolving foreign keys (get IDs)
  - Fetching current state before update/delete
- **Don't use**: GROUP BY analytics (use `aggregate_data`) or any writes (use `write_data`).
- **Inputs**:
  - `filters`: exact equality / IN matching (no wildcards)
  - `search_patterns`: text search using `%` wildcards (case-insensitive ILIKE)
- **Returns**: Type A with `operation` in `{query|batch_read|count}`.
- **Gotcha**: If you're searching human text and you didn't include `%`, you probably meant `search_patterns`.

### `aggregate_data` (Type A)

- **Purpose**: Analytics with aggregates, optional `group_by`, optional `having`.
- **Use when**: Counting/summing/averaging across many rows; finding outliers; grouping by families/categories.
- **Don't use**: Fetching entity details (use `read_data`).
- **Returns**: Type A with `results` and `count`.

### `write_data` (Type A, HITL-gated)

- **Purpose**: Atomic multi-operation writes using a validated `WriteIntent` (create/update/delete/upsert) with HITL approval.
- **Use when**: Any DB mutation is required.
- **Don't use**: As a discovery tool. Always `inspect_schema` + `read_data` first.
- **Filters (write operations)**:
  - Supported operator dicts: `in`, `eq`, `neq`, `gt`, `gte`, `lt`, `lte`
  - **Not supported**: `like/ilike` style string matching. Use `read_data(search_patterns=...)` to find IDs first, then update by `id in [...]`.
- **Returns**: Type A; on success includes created/updated/deleted entities and a summary.

## Media & Creative Tools

### `view_image` (Type C)

- **Purpose**: View an image in-context (gives the agent "eyes").
- **Use when**: You need to visually verify product/material/label/quality; before/after `image_studio`.
- **Don't use**: Metadata-only checks or bulk viewing.
- **Returns**: Type C (multimodal blocks: text + image_url). Not success-wrapped.

Example:
- `view_image(image_path="inbox/thread_123/photo.jpg")`

### `image_studio` (Type A)

- **Purpose**: Professional image processing/generation that reads/writes via storage paths.
- **Use when**: Background removal, enhancement, extraction, lifestyle generation.
- **Returns**: Type A with output metadata and storage paths.
- **Docs**: See also `docs/architecture/tools/IMAGE_STUDIO_TOOL.md`.

### `download_<platform>_media` (Type B)

- **Purpose**: Download media from a messaging platform and persist to `inbox/`.
- **Use when**: You have a platform media id and need a durable `storage_path`.
- **Returns**: Type B dict: `{storage_path, mime_type, size_bytes}`.

Example:
- `download_whatsapp_media(media_id="...")` → `{storage_path: "inbox/...", ...}`

## External Research Tools

### `research_product_tool` (Type A)

- **Purpose**: External web research for product specs, compliance, naming, etc.
- **Use when**: You need facts you don't have in DB.
- **Returns**: Type A with summary + sources.

### `extract_web_content_tool` (Type A)

- **Purpose**: Deep extraction from a specific URL.
- **Use when**: A source page has details that matter (tables/spec sheets).
- **Returns**: Type A with extracted content in markdown/text.
