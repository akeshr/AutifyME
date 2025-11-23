# Universal Data Engine - Design Specification

**Status:** Design Phase
**Created:** 2025-01-23
**Owner:** Architecture Team
**Priority:** CRITICAL - Foundation for all agent data operations

---

## Executive Summary

Transform AutifyME's data layer into a **Universal Data Engine** - three powerful, intelligent engines (Schema, Read, Write) that become agent superpowers. Vision: Agents access any data need through simple, token-efficient interfaces while the engine handles complexity (schema validation, transactions, optimization, access control).

**Core Principle:** Intelligence-first design - trust agents with rich context, empower engines to handle complexity.

---

## Table of Contents

- [Vision](#vision)
- [Current State](#current-state)
- [Target Architecture](#target-architecture)
- [Agent Mental Model](#agent-mental-model)
- [Engine Specifications](#engine-specifications)
  - [Schema Engine](#schema-engine)
  - [Read Engine](#read-engine)
  - [Write Engine](#write-engine)
- [Cross-Engine Intelligence](#cross-engine-intelligence)
- [Row-Level Security (RLS)](#row-level-security-rls)
- [Access Control Architecture](#access-control-architecture)
- [Success Criteria](#success-criteria)

---

## Vision

**Two-Tool Superpower Model:**
- Consolidate data operations into THREE powerful engines
- Each engine handles entire categories of operations autonomously
- Token-efficient (schema fetched on-demand, not in prompts)
- Role-based access control (specialist-scoped table permissions)
- Production-grade safety (transactions, rollback, validation)

**Intelligence-First:**
- Give agents schema context when they need it
- Trust agents to express intent clearly
- Engine validates, optimizes, and executes
- Auto-correct common mistakes
- Transparent error messages with fix suggestions

**Ultimate Goal:** Make data operations invisible - agents think about business logic, engine handles data mechanics.

---

## Current State

### Existing Tools

**query_database_tool** (Read Operations)
- Filters (exact match)
- Search patterns (ILIKE with wildcards)
- Relations (PostgREST joins)
- Count optimization
- Column projection
- Limit controls

**universal_crud_tool** (Write Operations)
- Schema-driven validation
- Dependency resolution (topological sorting)
- Foreign key reference resolution ($step_N.field, $ref:name)
- Atomic transactions with rollback
- Batch operations
- Entity reference tracking
- Impact analysis

**Storage Port** (Hexagonal Architecture)
- Clean abstraction over Supabase
- Generic CRUD (insert_entity, update_entities, delete_entities)
- Advanced query (query_advanced with relations + search)
- Transaction support
- Workflow-specific methods (outcomes, idempotency)

### Capabilities Already Present

✅ Table-level access control (factory pattern in universal_crud_tool)
✅ Operation-level permissions (read/create/update/delete)
✅ Schema registry with validation
✅ Transaction support with rollback
✅ Dependency resolution
✅ Reference resolution ($step_N.field)

### What's Missing

❌ Schema introspection tool (agents can't fetch schema on-demand)
❌ Aggregations (COUNT, SUM, AVG, GROUP BY)
❌ Complex joins (multi-table queries)
❌ Upsert operations (insert or update)
❌ Partial updates (PATCH semantics)
❌ Clone operations (template-based creation)
❌ Merge operations (deduplication)
❌ Dry-run mode (preview impact)
❌ Query caching (intelligent cache invalidation)
❌ Auto-batching optimization
❌ Full-text search (beyond ILIKE)
❌ Entity history tracking
❌ Row-level security (RLS) policies

---

## Target Architecture

### Three-Engine Model

```
┌─────────────────────────────────────────────────────────────┐
│                     AGENT INTERFACE                         │
│                  (Token-Efficient, Simple)                  │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│    SCHEMA     │   │     READ      │   │     WRITE     │
│    ENGINE     │   │    ENGINE     │   │    ENGINE     │
│               │   │               │   │               │
│ • Introspect │   │ • Query       │   │ • Insert      │
│ • Sample     │   │ • Aggregate   │   │ • Update      │
│ • Stats      │   │ • Join        │   │ • Delete      │
│ • Validate   │   │ • Search      │   │ • Upsert      │
│ • Suggest    │   │ • Cache       │   │ • Transaction │
│              │   │ • Stream      │   │ • Dry-Run     │
└───────────────┘   └───────────────┘   └───────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
        ┌───────────────┐       ┌───────────────┐
        │  STORAGE PORT │       │   RLS LAYER   │
        │  (Hexagonal)  │       │  (Policies)   │
        └───────────────┘       └───────────────┘
                │                       │
                └───────────┬───────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │   SUPABASE    │
                    │   (Postgres)  │
                    └───────────────┘
```

### Specialist-Scoped Configuration

Each specialist gets three engines with domain-specific restrictions:

```python
# Cataloging Specialist - Full CRUD on product domain
cataloging_tools = [
    create_schema_engine(
        storage,
        tables=["product_families", "products", "variant_axes", "variant_values"],
        capabilities=["introspect", "relationships", "constraints", "stats"]
    ),
    create_read_engine(
        storage,
        tables=["product_families", "products", "variant_axes", "variant_values"],
        capabilities=["query", "count", "search", "join", "aggregate", "cache"]
    ),
    create_write_engine(
        storage,
        tables=["product_families", "products", "variant_axes", "variant_values"],
        operations=["create", "update", "delete", "upsert"],
        capabilities=["transaction", "dependency_resolution", "bulk", "dry_run"]
    ),
]

# Market Intelligence - Read-only, all tables
market_intel_tools = [
    create_schema_engine(storage),  # All tables
    create_read_engine(storage),    # Read-only, all tables
    # No write engine
]

# Campaign Specialist - Read all, write campaigns only
campaign_tools = [
    create_schema_engine(storage),
    create_read_engine(storage),
    create_write_engine(
        storage,
        tables=["campaigns", "ad_copies"],
        operations=["create", "update"],  # No delete
        capabilities=["transaction", "bulk", "dry_run"]
    ),
]
```

---

## Agent Mental Model

### Data Operation Lifecycle

**Phase 1: DISCOVERY** ("What exists?")
- I don't know the schema → `get_schema(tables)`
- I don't know relationships → `explain_relationship(from_table, to_table)`
- I don't know data quality → `sample_data(table, limit=5)`
- I don't know volume → `get_table_stats(table)`

**Phase 2: PLANNING** ("Will this work?")
- Preview impact → `dry_run(operations)`
- Validate constraints → `validate_before_write(operations)`
- Understand dependencies → `get_dependency_graph(table)`
- Estimate performance → `explain_query_plan(query)`

**Phase 3: EXECUTION** ("Make it happen")
- Atomic operations → `execute_transaction(operations)`
- Batch processing → `bulk_insert(table, data)`
- Error handling → Auto-retry with rollback
- Idempotency → `upsert()` safe for retries

**Phase 4: VERIFICATION** ("Did it work?")
- Confirmation → Return created IDs
- Audit trail → `get_entity_history(table, id)`
- Comparison → `compare_entities(id1, id2)`
- Metrics → Execution time, affected rows

---

## Engine Specifications

### Schema Engine

**Purpose:** Discovery, validation, and schema intelligence (token-efficient, on-demand)

**Core Capabilities:**

#### 1. Schema Discovery
```python
# Interactive schema exploration
explore_schema(domain=None)
# Returns: List of tables with high-level metadata

# Targeted schema fetch
get_schema(
    tables: list[str],
    depth: str = "relationships"  # "basic", "relationships", "full"
)
# Returns: Table structures, columns, types, constraints, FKs

# Table statistics
get_table_stats(table: str)
# Returns: Row count, column stats, index info, last updated

# Data sampling
sample_data(
    table: str,
    filters: dict = {},
    limit: int = 5
)
# Returns: Real data examples matching filters
```

#### 2. Relationship Intelligence
```python
# Explain FK relationships
explain_relationship(
    from_table: str,
    to_table: str
)
# Returns: FK path, join conditions, cardinality

# Dependency graph
get_dependency_graph(table: str)
# Returns: Visual graph of FK dependencies, cascade impact

# Suggest related tables
suggest_related_tables(table: str)
# Returns: AI-suggested relevant tables for joins
```

#### 3. Validation Preview
```python
# Validate value against constraints
validate_value(
    table: str,
    column: str,
    value: Any
)
# Returns: Valid/invalid, constraint violations

# Batch uniqueness check
check_uniqueness(
    table: str,
    column: str,
    values: list[Any]
)
# Returns: Which values already exist

# Preview constraint violations
preview_constraints(
    table: str,
    operation: str,  # "insert", "update", "delete"
    data: dict | list[dict]
)
# Returns: Predicted constraint violations before execution
```

#### 4. Query Intelligence
```python
# Query execution plan
explain_query_plan(query: dict)
# Returns: Execution plan, index usage, estimated cost

# Performance prediction
estimate_query_cost(query: dict)
# Returns: Estimated execution time, rows scanned

# Index suggestions
suggest_indexes(query_pattern: dict)
# Returns: Missing indexes that would improve performance
```

**Token Efficiency:**
- Schema fetched only when agent needs it (not in every prompt)
- Cached per session (avoid repeated fetches)
- Minimal response (only requested depth)

**Access Control:**
- Respects table restrictions (specialist-scoped)
- Returns "Access Denied" for restricted tables
- Logs schema access for audit

---

### Read Engine

**Purpose:** Query, retrieval, aggregation (comprehensive read operations)

**Core Capabilities:**

#### 1. Basic Query (Enhanced)
```python
query(
    table: str,
    filters: dict = {},           # Exact match + operators
    search: dict = {},            # ILIKE patterns
    include: list[str] = [],      # Related tables (auto-join)
    select: list[str] = [],       # Column projection
    sort: list[str] = [],         # Multi-column sort
    limit: int | None = None,
    offset: int | None = None
)
# Returns: List of matching rows

# Filter operators
filters = {
    "price": {"gte": 10, "lte": 100},  # Range
    "status": {"in": ["active", "pending"]},  # IN clause
    "category_id": {"not_in": [uuid1, uuid2]},  # NOT IN
    "is_active": True  # Simple equality
}

# Search patterns (ILIKE)
search = {
    "name": "%bottle%",  # Contains
    "sku": "PET%"  # Starts with
}
```

#### 2. Aggregations (NEW)
```python
aggregate(
    table: str,
    metrics: list[str],  # ["count", "sum(price)", "avg(rating)"]
    group_by: list[str] = [],
    filters: dict = {},
    having: dict = {},  # Filter aggregated results
    sort: list[str] = [],
    limit: int | None = None
)
# Returns: Aggregated results

# Example: Products per category with avg price
aggregate(
    table="products",
    metrics=["count", "avg(price)", "min(price)", "max(price)"],
    group_by=["category_id"],
    filters={"is_active": True},
    having={"count": {"gte": 10}},  # Categories with 10+ products
    sort=["count DESC"]
)
```

#### 3. Advanced Joins (NEW)
```python
join(
    tables: list[dict],  # List of table definitions
    select: list[str],
    filters: dict = {},
    sort: list[str] = [],
    limit: int | None = None
)
# Returns: Joined result set

# Example: Products with family and category
join(
    tables=[
        {"table": "products", "alias": "p"},
        {"table": "product_families", "alias": "f", "on": "p.family_id = f.id"},
        {"table": "categories", "alias": "c", "on": "f.category_id = c.id"}
    ],
    select=["p.name", "p.sku_code", "f.sku_prefix", "c.name as category"],
    filters={"p.is_active": True},
    sort=["c.name", "p.name"]
)
```

#### 4. Full-Text Search (NEW)
```python
search_full_text(
    tables: list[str],
    query: str,  # Natural language query
    fields: list[str],  # Fields to search
    ranking: str = "relevance",  # "relevance" or "recent"
    limit: int = 50
)
# Returns: Ranked search results

# Example: Search products and families
search_full_text(
    tables=["products", "product_families"],
    query="eco-friendly plastic bottles",
    fields=["name", "description", "tags"],
    ranking="relevance"
)
```

#### 5. Smart Pagination (NEW)
```python
paginate(
    query: dict,  # Query spec from query()
    page: int = 1,
    per_page: int = 50,
    cursor: str | None = None,  # Cursor-based for large datasets
    total_count: bool = False  # Skip COUNT(*) if not needed
)
# Returns: {rows, page, per_page, total_count?, next_cursor?}

# Cursor-based pagination (efficient for large datasets)
result = paginate(query, per_page=100, cursor=None)
# ... process result.rows ...
next_result = paginate(query, per_page=100, cursor=result.next_cursor)
```

#### 6. Batch Read (NEW - Avoid N+1)
```python
batch_read(
    table: str,
    ids: list[str],  # 100+ entity IDs
    include: list[str] = []  # Prefetch related entities
)
# Returns: List of entities (preserves ID order)

# Example: Fetch 200 products with their families
batch_read(
    table="products",
    ids=[uuid1, uuid2, ..., uuid200],
    include=["product_family", "variant_values"]
)
# Single query instead of 200 queries
```

#### 7. Streaming (NEW - Large Results)
```python
stream_results(
    query: dict,  # Query spec from query()
    chunk_size: int = 1000
)
# Returns: Generator yielding chunks

# Example: Process 100K products
for chunk in stream_results(query, chunk_size=1000):
    process_products(chunk)  # Process 1000 at a time
```

#### 8. Query History (NEW)
```python
get_entity_history(
    table: str,
    entity_id: str,
    time_range: tuple[datetime, datetime] | None = None,
    include_diffs: bool = True
)
# Returns: List of changes with timestamps, user, diffs

# Example: Audit trail for product
get_entity_history(
    table="products",
    entity_id=uuid,
    include_diffs=True
)
# Returns: [{timestamp, user, operation, diff}, ...]
```

#### 9. Entity Comparison (NEW)
```python
compare_entities(
    table: str,
    entity_ids: list[str],
    diff_mode: str = "side_by_side"  # or "unified"
)
# Returns: Comparison view highlighting differences

# Example: Compare two product variants
compare_entities(
    table="products",
    entity_ids=[uuid1, uuid2],
    diff_mode="side_by_side"
)
```

#### 10. Query Caching (NEW)
```python
query_cached(
    query: dict,
    ttl: int = 300,  # 5 minutes
    cache_key: str | None = None,  # Custom cache key
    invalidate_on_write: list[str] = []  # Tables that invalidate cache
)
# Returns: Cached result if available, else executes and caches

# Example: Expensive aggregation with caching
query_cached(
    query=aggregate_query,
    ttl=600,  # 10 minutes
    invalidate_on_write=["products", "product_families"]
)
```

**Performance Optimizations:**
- Auto-prefetch related entities (avoid N+1)
- Intelligent caching with invalidation
- Batch operations when possible
- Streaming for large datasets
- Count estimation for large tables

**Access Control:**
- Table-level restrictions enforced
- RLS policies applied automatically
- Audit logging for sensitive queries

---

### Write Engine

**Purpose:** Create, update, delete operations with transactions and validation

**Core Capabilities:**

#### 1. Single Insert (Enhanced)
```python
insert(
    table: str,
    data: dict,
    return_fields: list[str] = ["id", "created_at"],
    on_conflict: str = "error"  # "error", "skip", "update"
)
# Returns: Inserted entity with specified fields

# Example
insert(
    table="products",
    data={"name": "PET Bottle 500ml", "sku_code": "PET-BTL-500ML-001"},
    return_fields=["id", "sku_code", "created_at"]
)
```

#### 2. Bulk Insert (Enhanced)
```python
bulk_insert(
    table: str,
    data: list[dict],
    batch_size: int = 100,  # Auto-batch for performance
    on_conflict: str = "skip",  # Handle duplicates
    return_ids: bool = True
)
# Returns: List of created IDs (or full entities)

# Example: Insert 500 products
bulk_insert(
    table="products",
    data=products_list,  # 500 products
    batch_size=100,  # 5 batches of 100
    on_conflict="skip"
)
```

#### 3. Update (Enhanced)
```python
update(
    table: str,
    filters: dict,
    updates: dict,
    conditions: dict = {},  # Additional WHERE conditions
    return_updated: bool = True
)
# Returns: Count of updated rows + updated entities

# Example: Conditional update
update(
    table="products",
    filters={"id": uuid},
    updates={"status": "active"},
    conditions={"current_status": "draft"},  # Only update if status = draft
    return_updated=True
)
```

#### 4. Partial Update / Patch (NEW)
```python
patch(
    table: str,
    entity_id: str,
    partial_updates: dict,  # Only fields to update
    merge_strategy: str = "shallow"  # "shallow" or "deep" for nested
)
# Returns: Updated entity

# Example: Update only price (not full product)
patch(
    table="products",
    entity_id=uuid,
    partial_updates={"price": 99.99, "updated_at": "now()"}
)
```

#### 5. Upsert (NEW - Insert or Update)
```python
upsert(
    table: str,
    data: dict,
    conflict_fields: list[str],  # Unique constraint fields
    update_fields: list[str] | str = "*",  # Fields to update on conflict
    insert_fields: str = "*"  # Fields to insert if new
)
# Returns: Created or updated entity + operation ("inserted" or "updated")

# Example: Upsert by SKU
upsert(
    table="products",
    data={"sku_code": "PET-BTL-500ML-001", "price": 99.99, "name": "PET Bottle"},
    conflict_fields=["sku_code"],
    update_fields=["price"],  # Update price if exists
)
```

#### 6. Bulk Upsert (NEW)
```python
bulk_upsert(
    table: str,
    data: list[dict],
    conflict_fields: list[str],
    batch_size: int = 100
)
# Returns: {inserted: count, updated: count, ids: [...]}

# Example: Sync 1000 products from external source
bulk_upsert(
    table="products",
    data=external_products,  # Mix of new + existing
    conflict_fields=["sku_code"],
    batch_size=100
)
```

#### 7. Conditional Update (NEW - Optimistic Locking)
```python
conditional_update(
    table: str,
    entity_id: str,
    updates: dict,
    if_version: int,  # Expected version
    increment_version: bool = True
)
# Returns: Updated entity or ConflictError if version mismatch

# Example: Prevent concurrent modification
conditional_update(
    table="campaigns",
    entity_id=uuid,
    updates={"budget": 5000},
    if_version=current_version,  # Only update if version matches
    increment_version=True  # Auto-increment version
)
```

#### 8. Delete (Enhanced)
```python
delete(
    table: str,
    filters: dict,
    cascade: bool = True,  # Auto-delete dependent entities
    soft_delete: bool = True,  # Mark as deleted (don't remove)
    return_deleted: bool = True
)
# Returns: Count + deleted entity IDs

# Example: Soft delete with cascade
delete(
    table="product_families",
    filters={"id": uuid},
    cascade=True,  # Delete products, variants
    soft_delete=True,  # Set is_active=False
    return_deleted=True
)
```

#### 9. Clone Entity (NEW)
```python
clone_entity(
    table: str,
    source_id: str,
    overrides: dict = {},  # Fields to change
    include_relations: list[str] = [],  # Clone related entities
    exclude_fields: list[str] = ["id", "created_at"]  # Auto-generate
)
# Returns: Cloned entity with new ID

# Example: Clone campaign with new name
clone_entity(
    table="campaigns",
    source_id=uuid,
    overrides={"name": "Campaign Copy", "status": "draft"},
    include_relations=["ad_copies"],  # Clone ad copies too
)
```

#### 10. Merge Entities (NEW - Deduplication)
```python
merge_entities(
    table: str,
    source_ids: list[str],  # Duplicate entities
    target_id: str,  # Keep this one
    strategy: str = "prefer_target",  # "prefer_target", "prefer_source", "manual"
    update_references: bool = True  # Update FKs pointing to sources
)
# Returns: Merged entity + merge report

# Example: Merge duplicate products
merge_entities(
    table="products",
    source_ids=[uuid1, uuid2],  # Duplicates
    target_id=uuid3,  # Canonical
    strategy="prefer_target",
    update_references=True  # Update order_items.product_id
)
```

#### 11. Multi-Table Transaction (Enhanced)
```python
execute_transaction(
    operations: list[dict],  # List of operations
    auto_resolve_deps: bool = True,  # Auto-sort by dependencies
    rollback_on_error: bool = True
)
# Returns: ExecutionResult with created IDs, affected entities

# Example: Atomic product family creation
execute_transaction(
    operations=[
        {"op": "insert", "table": "product_families", "data": {...}, "ref": "family"},
        {"op": "insert", "table": "variant_axes", "data": [...], "depends_on": ["family"]},
        {"op": "insert", "table": "products", "data": [...], "depends_on": ["family"]}
    ],
    auto_resolve_deps=True  # Engine sorts by dependencies
)
```

#### 12. Dry-Run (NEW - Preview Impact)
```python
dry_run(
    operations: list[dict]
)
# Returns: Preview without executing
{
    "entities_affected": {
        "product_families": {"new": 1},
        "products": {"new": 36},
        "variant_values": {"new": 18}
    },
    "validation_errors": [],
    "warnings": ["High insert volume: 36 products"],
    "estimated_duration_ms": 250,
    "safe_to_execute": True
}

# Example: Preview before creating 100 products
preview = dry_run(operations)
if preview["safe_to_execute"]:
    execute_transaction(operations)
```

#### 13. Validate Before Write (NEW)
```python
validate_before_write(
    operations: list[dict],
    checks: list[str] = ["schema", "constraints", "permissions", "conflicts"],
    fail_fast: bool = True
)
# Returns: Validation report

{
    "valid": False,
    "errors": [
        {
            "operation_index": 2,
            "error": "Unique constraint violation: sku_code 'PET-BTL-500ML-001' already exists",
            "suggestion": "Use upsert() instead of insert() for idempotency"
        }
    ],
    "warnings": []
}
```

#### 14. Archive / Restore (NEW)
```python
# Archive old data
archive(
    table: str,
    filters: dict,
    archive_table: str | None = None  # Auto-create if needed
)
# Returns: Archived entity count

# Restore archived data
restore(
    table: str,
    filters: dict,
    from_archive: str
)
# Returns: Restored entity count
```

**Transaction Safety:**
- All multi-step operations atomic (ACID)
- Auto-rollback on any error
- Reference resolution ($step_N.field, $ref:name)
- Dependency sorting (topological order)

**Access Control:**
- Table + operation restrictions enforced
- RLS policies applied
- Audit logging for all writes

---

## Cross-Engine Intelligence

**Auto-Optimizations (Transparent to Agents):**

### 1. Auto-Batching
```python
# Agent code
for product in products:
    insert("products", product)

# Engine optimizes to
bulk_insert("products", products)  # Single query
```

### 2. Auto-Caching
```python
# Agent code
result1 = query("products", filters={"category": "bottles"})
# ... later ...
result2 = query("products", filters={"category": "bottles"})

# Engine returns cached result for result2 (if within TTL)
```

### 3. Auto-Prefetch (Solve N+1)
```python
# Agent code
products = query("products", limit=100)
for product in products:
    family = query("product_families", {"id": product.family_id})

# Engine detects pattern and prefetches
products = query("products", limit=100, include=["product_family"])
```

### 4. Auto-Retry
```python
# Agent code
insert("products", data)

# Engine handles transient errors
# - Deadlock: Retry with exponential backoff
# - Network timeout: Retry up to 3 times
# - Success: Agent sees no error
```

### 5. Auto-Dependency Resolution
```python
# Agent provides operations out of order
operations = [
    {"op": "insert", "table": "products", ...},  # Needs family_id
    {"op": "insert", "table": "product_families", ...}  # Should come first
]

# Engine sorts topologically
execute_transaction(operations, auto_resolve_deps=True)
```

### 6. Auto-Error Recovery
```python
# Agent typo
query("products", select=["id", "nam"])  # Typo: "nam"

# Engine suggests correction
{
    "error": "Column 'nam' not found",
    "suggestion": "Did you mean 'name'?",
    "valid_columns": ["id", "name", "sku_code", ...]
}
```

### 7. Auto-Indexing Hints
```python
# Engine tracks slow queries
query("products", filters={"supplier_id": uuid})  # 2000ms

# Engine logs recommendation
logger.warning(
    "Slow query detected on products.supplier_id",
    extra={
        "suggestion": "CREATE INDEX idx_products_supplier_id ON products(supplier_id)",
        "estimated_improvement": "10x faster"
    }
)
```

---

## Row-Level Security (RLS)

**Future Architecture for Multi-Tenant and User-Based Access Control**

### Context Injection

Every operation tagged with security context:
```python
{
    "user_id": "uuid",
    "role": "cataloging_specialist",
    "tenant_id": "company_uuid",
    "agent_type": "cataloging",
    "permissions": ["read:products", "write:products"]
}
```

### Policy Types

#### 1. User-Based Policies
```python
# Users see only their own data
"products": {
    "read": "created_by = $user_id OR assigned_to = $user_id",
    "write": "created_by = $user_id",
    "delete": False
}
```

#### 2. Role-Based Policies
```python
# Admins see all, specialists see domain
"products": {
    "read": "$role IN ['admin', 'cataloging_specialist'] OR created_by = $user_id",
    "write": "$role IN ['admin', 'cataloging_specialist']"
}
```

#### 3. Tenant-Based Policies (Multi-Tenancy)
```python
# Each company sees only their data
"*": {  # All tables
    "read": "company_id = $tenant_id",
    "write": "company_id = $tenant_id"
}
```

#### 4. Agent-Based Policies
```python
# Specialists access only domain tables
"cataloging_specialist": {
    "allowed_tables": ["products", "product_families", "variant_axes"],
    "denied_tables": ["campaigns", "analytics"]
},
"campaign_specialist": {
    "allowed_tables": ["campaigns", "ad_copies", "products:read_only"],
    "denied_tables": ["analytics"]
}
```

#### 5. Attribute-Level Masking
```python
# Hide sensitive fields based on role
"products": {
    "mask_fields": {
        "cost_price": "$role != 'admin'",  # Only admins see cost
        "supplier_id": "$role NOT IN ['admin', 'procurement']"
    }
}
```

### Policy Enforcement

**Query-Time Rewriting (Performance-Critical):**
```sql
-- Agent query
SELECT * FROM products WHERE category = 'bottles'

-- RLS policy injects WHERE clause
SELECT * FROM products
WHERE category = 'bottles'
  AND company_id = $tenant_id
  AND (created_by = $user_id OR is_public = true)
```

**Performance Optimizations:**
- Policies compiled to SQL (not app-level filtering)
- Policy evaluation cached per session
- Indexes on RLS columns (company_id, created_by)
- Policy decisions logged for audit

---

## Access Control Architecture

### Table-Level Access Control

**Specialist-Scoped Tool Creation:**
```python
# Factory pattern creates specialist-specific tools
cataloging_tools = create_tools(
    specialist="cataloging",
    allowed_tables=["products", "product_families", "variant_axes"],
    allowed_operations=["read", "create", "update", "delete"]
)

# Enforced at runtime
query("campaigns", ...)  # Error: "campaigns not accessible by cataloging specialist"
```

### Operation-Level Access Control

**Per-Table Operation Restrictions:**
```python
market_intel_tools = create_tools(
    specialist="market_intelligence",
    allowed_tables=None,  # All tables
    allowed_operations=["read"]  # Read-only
)

# Enforced at runtime
insert("products", ...)  # Error: "Write operations not allowed"
```

### Row-Level Security (RLS)

**User Context Propagation:**
```python
# Middleware injects context into every operation
@inject_security_context
async def operation_wrapper(operation, user_context):
    # Context available to RLS policies
    result = await execute_with_rls(operation, user_context)
    return result
```

### Audit Logging

**All Data Access Logged:**
```python
{
    "timestamp": "2025-01-23T10:30:00Z",
    "user_id": "uuid",
    "agent_type": "cataloging_specialist",
    "operation": "read",
    "table": "products",
    "filters": {"category": "bottles"},
    "row_count": 42,
    "execution_time_ms": 15
}
```

---

## Success Criteria

### Agent Perspective

**As an agent, I can:**
✅ Discover schema without documentation
✅ Plan operations with confidence (preview impact)
✅ Execute complex transactions safely (auto-rollback)
✅ Handle errors gracefully (auto-retry, suggestions)
✅ Optimize performance automatically (batching, caching)
✅ Access only permitted data (RLS enforced)
✅ Audit all changes (who, what, when)
✅ Recover from mistakes (history, restore)
✅ Work across domains (cross-table joins)
✅ Scale to large datasets (streaming, pagination)

**As an agent, I never worry about:**
❌ N+1 queries (auto-prefetch handles it)
❌ Manual batching (engine batches automatically)
❌ Typos in field names (engine suggests corrections)
❌ Dependency ordering (engine sorts topologically)
❌ Cache invalidation (engine handles it)
❌ Index optimization (engine logs hints)
❌ Permission checks (RLS enforces automatically)

### Engineering Perspective

**Production-Grade Qualities:**
✅ ACID transactions (all-or-nothing)
✅ Automatic rollback on errors
✅ Schema-driven validation
✅ Type safety (Pydantic models)
✅ Comprehensive error messages
✅ Performance monitoring
✅ Audit logging
✅ Security enforcement (RLS)
✅ Hexagonal architecture (storage adapter agnostic)

### Business Perspective

**Value Delivered:**
✅ Faster specialist development (reusable engine)
✅ Fewer data bugs (validation + transactions)
✅ Better performance (auto-optimization)
✅ Stronger security (RLS + audit)
✅ Easier debugging (history + diffs)
✅ Lower maintenance (centralized data logic)

---

## Architecture Alignment

### Hexagonal Architecture
- **Port:** StorageInterface (unchanged)
- **Adapters:** SupabaseStorageClient (enhanced with new methods)
- **Core:** Engine implementations (schema/read/write)

### Intelligence-First Design
- Rich context (schema on-demand)
- Trust agents to reason
- Engine handles complexity
- Transparent optimizations

### Token Efficiency
- Schema fetched only when needed
- Cached per session
- Minimal API surface (three tools vs. many)

### Production-Grade Standards
- Transactions with rollback
- Schema-driven validation
- Comprehensive error handling
- Performance monitoring
- Audit logging
- Security enforcement

---

## Next Steps

See **[UNIVERSAL_DATA_ENGINE_EXECUTION_PLAN.md](../workflows/UNIVERSAL_DATA_ENGINE_EXECUTION_PLAN.md)** for phased development plan.
