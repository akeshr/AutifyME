# Universal Data Engine - Execution Plan

**Status:** Planning Phase
**Created:** 2025-01-23
**Owner:** Architecture Team
**Priority:** CRITICAL

---

## Executive Summary

Phased implementation plan for transforming AutifyME's data layer into a Universal Data Engine. Each phase builds upon previous phases, maintaining backward compatibility while adding new capabilities. Approach: Build from scratch mindset with existing code streamlining.

**Design Reference:** [UNIVERSAL_DATA_ENGINE_DESIGN.md](../core/UNIVERSAL_DATA_ENGINE_DESIGN.md)

---

## Table of Contents

- [Development Approach](#development-approach)
- [Phase Overview](#phase-overview)
- [Phase 1: Foundation Enhancement](#phase-1-foundation-enhancement)
- [Phase 2: Intelligence Layer](#phase-2-intelligence-layer)
- [Phase 3: Advanced Operations](#phase-3-advanced-operations)
- [Phase 4: Security & RLS](#phase-4-security--rls)
- [Dependencies & Prerequisites](#dependencies--prerequisites)
- [Testing Strategy](#testing-strategy)
- [Migration Strategy](#migration-strategy)
- [Success Metrics](#success-metrics)

---

## Development Approach

### Build From Scratch Mindset

**Principles:**
- Question existing patterns, refactor fearlessly
- Design ideal solution first, then implement
- Eliminate technical debt proactively
- No "we'll fix it later" compromises
- Clean, production-ready from first principles

### Code Quality Standards

**Every Change Must:**
- Be production-grade from start (resilience, observability, recovery)
- Follow hexagonal architecture (ports, adapters, core)
- Include comprehensive tests (unit + integration)
- Update documentation in lockstep
- Pass linting (ruff check, mypy)

### Existing Code Streamlining

**Build From Scratch, Not Extend:**
- Design ideal `inspect_schema`, `read_data`, `write_data` tools
- Absorb useful patterns from existing code:
  - `query_database_tool.py` → Best patterns → `read_data`
  - `universal_crud_tool.py` → Core engine logic → `write_data`
  - Discard technical debt, over-complexity, confusing naming
- Refactor storage port with clean new methods
- Enhance schema registry with intelligence features

**Migration Strategy:**
- New tools (ideal architecture) implemented fresh
- Old tools marked deprecated but functional
- Specialists migrated one-by-one to new tools
- Old tools removed after full migration (6+ months)

**Tool Naming (Agent-Centric):**
- `inspect_schema` - Understand data structure
- `read_data` - Fetch, search, analyze
- `write_data` - Create, update, delete

---

## Phase Overview

| Phase | Focus | Duration | Status | Dependencies |
|-------|-------|----------|--------|--------------|
| **Phase 1** | Foundation Enhancement | 2-3 weeks | 🔲 Not Started | None |
| **Phase 2** | Intelligence Layer | 2-3 weeks | 🔲 Not Started | Phase 1 |
| **Phase 3** | Advanced Operations | 3-4 weeks | 🔲 Not Started | Phase 1, 2 |
| **Phase 4** | Security & RLS | 2-3 weeks | 🔲 Not Started | Phase 1, 2, 3 |

**Total Estimated Duration:** 9-13 weeks (sequential) or 6-9 weeks (with parallelization)

---

## Phase 1: Foundation Enhancement

**Goal:** Enhance existing capabilities and build Schema Engine foundation

**Duration:** 2-3 weeks
**Status:** 🔄 In Progress (Phase 1.5 Complete)
**Priority:** CRITICAL

### 1.1 Schema Engine - Core Features

**Status:** ✅ Complete (2025-01-23)

**Architecture Note:** Schema stored in single JSON file (`schemas/database_schema_v1.json`) containing ALL tables. SchemaRegistry loads once at startup (in-memory), filters to requested tables at runtime. Token-efficient: agents receive only requested subset.

#### Tasks:

- [x] **Schema Tool Factory** (`tools/data_engine_tools.py`)
  - [x] Created `create_inspect_schema_tool()` factory with table restrictions
  - [x] Support multi-detail inspection (structure, relationships, stats, samples)
  - [x] Integrated with existing SchemaRegistry (single-file, in-memory)
  - [x] Access control enforcement (table-level filtering)
  - [x] **Tests:** 15 tests (factory, access control, configuration)

- [x] **Schema Discovery** (`tools/data_engine_tools.py`)
  - [x] `inspect_schema(tables, details)` - Fetch targeted schema metadata
  - [x] On-demand filtering (runtime, not prompt-time)
  - [x] Graceful partial failures (per-table error isolation)
  - [x] Token-efficient response format
  - [x] **Tests:** 10 tests (multi-table, details filtering, edge cases)

- [x] **Table Statistics** (`integrations/storage/supabase_client.py`)
  - [x] `get_table_stats(table)` - Row counts, indexes, primary key
  - [x] Index information retrieval
  - [x] Future-ready (estimated_size_bytes, last_updated placeholders)
  - [x] Added to StorageInterface port
  - [x] **Tests:** 8 tests (all tables, empty tables, errors)

- [x] **Data Sampling** (`integrations/storage/supabase_client.py`)
  - [x] `sample_data(table, filters, limit)` - Real data examples
  - [x] Safety limit (max 20 rows)
  - [x] Filter support for targeted sampling
  - [x] Added to StorageInterface port
  - [x] **Tests:** 10 tests (filters, limits, validation, edge cases)

**Deliverables:**
- ✅ Schema tool factory with access control
- ✅ inspect_schema tool with multi-detail support
- ✅ Table statistics APIs (get_table_stats)
- ✅ Data sampling APIs (sample_data)
- ✅ 50 comprehensive tests (all passing)
- ✅ Quality: Ruff + Mypy clean
- ✅ Documentation: Inline docstrings + test coverage

---

### 1.2 Read Engine - Aggregations

**Status:** ✅ Complete (2025-01-23)

#### Tasks:

- [x] **Aggregation Support** (`integrations/storage/supabase_client.py`)
  - [x] Added `query_aggregate()` port method to StorageInterface
  - [x] Implemented in SupabaseClient with PostgREST syntax translation
  - [x] Support metrics: count, sum, avg, min, max
  - [x] GROUP BY support (single/multiple columns)
  - [x] HAVING clause support (Python-side filtering, all operators: gt, gte, lt, lte, eq, neq)
  - [x] **Tests:** 35 tests total (comprehensive coverage)

- [x] **Aggregate Data Tool** (`tools/data_engine_tools.py`)
  - [x] Created `create_aggregate_data_tool()` factory
  - [x] Access control with table restrictions
  - [x] Agent-centric naming: `aggregate_data`
  - [x] Comprehensive docstrings with USE WHEN guidance
  - [x] **Tests:** Included in 35-test suite

**Deliverables:**
- ✅ Aggregation support in storage layer (query_aggregate method)
- ✅ New aggregate_data tool with factory pattern
- ✅ 35 comprehensive tests (all passing)
- ✅ Quality: Ruff + Mypy clean
- ✅ Documentation: Inline docstrings + test coverage

---

### 1.3 Read Engine - Batch Operations

**Status:** ✅ Complete (2025-01-23)

#### Tasks:

- [x] **Batch Read** (`integrations/storage/supabase_client.py`)
  - [x] `batch_read(table, ids, include)` - Fetch multiple by ID
  - [x] Optimize with IN clause (single query)
  - [x] Prefetch related entities (solve N+1)
  - [x] Preserve ID order in results
  - [x] Add to StorageInterface port
  - [x] **Tests:** 16 tests (100+ IDs, includes, order preservation)

- [x] **Pagination** (`integrations/storage/supabase_client.py`)
  - [x] `paginate_entities(table, filters, page_size, offset, cursor)` - Smart pagination
  - [x] Cursor-based pagination for large datasets
  - [x] Offset-based pagination for smaller datasets
  - [x] Add to StorageInterface port
  - [x] **Tests:** 15 tests (offset, cursor, edge cases, large datasets)

**Deliverables:**
- ✅ Batch read capabilities (batch_read method)
- ✅ Pagination support (offset + cursor)
- ✅ 31 comprehensive tests (all passing)
- ✅ Quality: Ruff + Mypy clean
- ✅ Documentation: Inline docstrings + test coverage

---

### 1.4 Write Engine - Upsert & Patch

**Status:** ✅ Complete (2025-01-23) - Storage Layer Implementation

#### Tasks:

- [x] **Upsert Support** (`integrations/storage/supabase_client.py`)
  - [x] `upsert_entity(table, data, conflict_fields)` - Insert or update
  - [x] Support conflict field specification (defaults to 'id')
  - [x] PostgreSQL INSERT ON CONFLICT DO UPDATE semantics
  - [x] Transaction tracking integration
  - [x] Add to StorageInterface port
  - [x] **Tests:** 14 tests (conflicts, multiple fields, edge cases)

- [x] **Bulk Upsert** (`integrations/storage/supabase_client.py`)
  - [x] `bulk_upsert(table, data, conflict_fields)` - Batch upsert
  - [x] Optimize with single PostgREST query
  - [x] Numeric normalization (whole-number floats → ints)
  - [x] Transaction tracking integration
  - [x] Add to StorageInterface port
  - [x] **Tests:** 20 tests (large batches, performance, normalization)

- [x] **Partial Update (Patch)** (`integrations/storage/supabase_client.py`)
  - [x] `patch_entity(table, id, updates)` - Update specific fields
  - [x] PATCH semantics (partial updates)
  - [x] Preserve unspecified fields
  - [x] Transaction tracking integration
  - [x] Add to StorageInterface port
  - [x] **Tests:** 15 tests (nested objects, field preservation)

- [x] **Conflict Resolution & Transaction Tracking** (Multiple test groups)
  - [x] 10 tests for conflict resolution scenarios
  - [x] 5 tests for transaction tracking integration
  - [x] 10 tests for edge cases and error handling

**Deliverables:**
- ✅ Upsert capabilities (single + bulk)
- ✅ Patch support with PATCH semantics
- ✅ 73 comprehensive tests (all passing)
- ✅ Quality: Ruff + Mypy clean
- ✅ Documentation: Inline docstrings + test coverage

**Note:** Tool-layer integration (`universal_crud_tool.py` upsert/patch operations) will be completed in Phase 1.6 alongside agent refactoring.

---

### 1.5 Write Engine - Dry-Run & Validation

**Status:** ✅ Complete (2025-01-23) - Storage Layer Implementation

#### Tasks:

- [x] **Storage Layer Methods** (`integrations/storage/supabase_client.py`)
  - [x] Added `validate_entity_data()` - Schema validation without execution
  - [x] Added `check_constraint_violations()` - Pre-flight constraint checking
  - [x] Added `preview_write_impact()` - Dry-run impact analysis
  - [x] Comprehensive error/warning generation
  - [x] Support for single entities and batches
  - [x] Add to StorageInterface port
  - [x] **Tests:** 48 tests total (18 validation + 17 constraints + 13 preview)

**Deliverables:**
- ✅ Validation capabilities in storage layer (validate_entity_data method)
- ✅ Constraint checking (check_constraint_violations method)
- ✅ Impact preview (preview_write_impact method)
- ✅ 48 comprehensive tests (all passing)
- ✅ Quality: Ruff + Mypy clean (test files)
- ✅ Documentation: Inline docstrings + test coverage

**Note:** Tool-layer integration (`universal_crud_tool.py` dry-run features) will be completed in Phase 1.6 alongside agent refactoring.

---

### 1.6 Agent & Prompt Refactoring

**Status:** 🔲 Not Started

**Goal:** Migrate agents from old tools to new Universal Data Engine tools with streamlined prompts

#### Tasks:

- [ ] **Create New Tool Factories** (`tools/data_engine_tools.py`)
  - [ ] `create_inspect_schema_tool(storage, tables)` - Schema engine
  - [ ] `create_read_data_tool(storage, tables)` - Read engine
  - [ ] `create_write_data_tool(storage, tables, operations)` - Write engine
  - [ ] Specialist-scoped access control (table + operation restrictions)
  - [ ] Agent-centric tool descriptions with USE WHEN guidelines
  - [ ] **Tests:** 25+ tests (factory, access control, all specialists)

- [ ] **Refactor Cataloging Specialist** (`agents/cataloging_specialist.py`)
  - [ ] Replace `query_database_tool` with `read_data`
  - [ ] Replace `universal_crud_tool` with `write_data`
  - [ ] Add `inspect_schema` for schema discovery
  - [ ] Update prompt to use new tool names and patterns
  - [ ] Test full cataloging workflow end-to-end
  - [ ] **Tests:** 30+ tests (all scenarios, HITL integration)

- [ ] **Update Agent Prompts** (`prompts/specialists/`)
  - [ ] Cataloging specialist prompt - streamlined tool usage
  - [ ] Remove database implementation details
  - [ ] Focus on business intent and goals
  - [ ] Add examples with new tool syntax (@name.field references)
  - [ ] Document agent mental model (Discovery → Planning → Execution)
  - [ ] **Tests:** Prompt validation, example verification

- [ ] **Middleware Integration** (`core/middleware/`)
  - [ ] Update tool access control middleware for new tools
  - [ ] Ensure table restrictions enforced correctly
  - [ ] Add audit logging for schema/data access
  - [ ] Test access denial scenarios
  - [ ] **Tests:** 15+ tests (access control, logging, edge cases)

- [ ] **Migration Documentation** (`docs/architecture/workflows/`)
  - [ ] Agent migration guide (old tools → new tools)
  - [ ] Prompt engineering guide for new tools
  - [ ] Tool usage examples per specialist type
  - [ ] Testing checklist for migrated agents
  - [ ] Rollback procedure

**Deliverables:**
- New tool factories with specialist-scoped access
- Cataloging specialist fully migrated
- Updated prompts for all specialists
- Middleware integration complete
- 70+ tests (integration + unit)
- Migration documentation

**Migration Strategy:**
- Phase 1.1-1.5 build capabilities (old tools still work)
- Phase 1.6 migrates agents to new tools
- Old tools deprecated but functional (6-month sunset)
- Gradual rollout: Cataloging → Campaign → Market Intel → Others

---

### Phase 1 Summary

**Total Tasks:** 47 tasks across 6 workstreams
**Total Tests:** 282+ tests
**Estimated Duration:** 3-4 weeks
**Dependencies:** None (foundation phase)

**Key Deliverables:**
- Schema Engine with discovery, stats, sampling
- Read Engine with aggregations, batch read, pagination
- Write Engine with upsert, patch, dry-run, validation
- Agent-centric tool factories with access control
- Cataloging specialist migrated to new tools
- Streamlined agent prompts
- 280+ comprehensive tests
- Complete migration documentation

**Migration Impact:**
- Existing tools continue to work (backward compatible)
- New capabilities available immediately
- Cataloging specialist fully migrated
- No breaking changes for non-migrated specialists

---

## Phase 2: Intelligence Layer

**Goal:** Add auto-optimizations and intelligent features

**Duration:** 2-3 weeks
**Status:** 🔲 Not Started
**Priority:** HIGH
**Dependencies:** Phase 1

### 2.1 Auto-Batching Optimizer

**Status:** 🔲 Not Started

#### Tasks:

- [ ] **Operation Detector** (`core/optimizers.py`)
  - [ ] Detect repeated insert calls within time window
  - [ ] Collect operations for batching
  - [ ] Trigger batch execution on threshold
  - [ ] **Tests:** 15+ tests (detection, thresholds, edge cases)

- [ ] **Batch Executor** (`core/optimizers.py`)
  - [ ] Convert multiple inserts → bulk_insert
  - [ ] Maintain operation order guarantees
  - [ ] Handle errors per-operation
  - [ ] **Tests:** 12+ tests (errors, ordering, rollback)

**Deliverables:**
- Auto-batching for inserts
- 27+ tests
- Performance benchmarks (10x improvement expected)

---

### 2.2 Intelligent Caching

**Status:** 🔲 Not Started

#### Tasks:

- [ ] **Cache Layer** (`core/cache.py`)
  - [ ] LRU cache with TTL support
  - [ ] Cache key generation (query fingerprint)
  - [ ] Invalidation on write operations
  - [ ] Per-table invalidation tracking
  - [ ] **Tests:** 20+ tests (TTL, invalidation, memory limits)

- [ ] **Query Caching** (`integrations/storage/supabase_client.py`)
  - [ ] `query_cached()` wrapper
  - [ ] Auto-cache for repeated queries
  - [ ] Configurable TTL per query
  - [ ] Manual cache control
  - [ ] **Tests:** 15+ tests (cache hits, misses, invalidation)

**Deliverables:**
- Intelligent caching layer
- Query cache integration
- 35+ tests
- Cache hit rate monitoring

---

### 2.3 N+1 Query Detection & Prefetch

**Status:** 🔲 Not Started

#### Tasks:

- [ ] **Pattern Detector** (`core/optimizers.py`)
  - [ ] Detect N+1 query patterns
  - [ ] Track query sequences
  - [ ] Identify prefetch opportunities
  - [ ] **Tests:** 18+ tests (pattern detection, false positives)

- [ ] **Auto-Prefetch** (`integrations/storage/supabase_client.py`)
  - [ ] Modify query to include related entities
  - [ ] Use batch_read for multiple IDs
  - [ ] Cache prefetched entities
  - [ ] **Tests:** 15+ tests (prefetch accuracy, performance)

**Deliverables:**
- N+1 detection
- Auto-prefetch capabilities
- 33+ tests
- Performance benchmarks (50x improvement expected)

---

### 2.4 Error Recovery & Suggestions

**Status:** 🔲 Not Started

#### Tasks:

- [ ] **Error Analyzer** (`core/error_recovery.py`)
  - [ ] Parse database errors
  - [ ] Detect common mistakes (typos, constraint violations)
  - [ ] Generate suggestions
  - [ ] **Tests:** 20+ tests (all error types, suggestions)

- [ ] **Auto-Correction** (`core/error_recovery.py`)
  - [ ] Typo correction for field names (Levenshtein distance)
  - [ ] Suggest valid values for enums
  - [ ] Recommend upsert for duplicate errors
  - [ ] **Tests:** 15+ tests (corrections, edge cases)

- [ ] **Retry Logic** (`core/error_recovery.py`)
  - [ ] Exponential backoff for transient errors
  - [ ] Detect deadlocks, network timeouts
  - [ ] Max retry limits
  - [ ] **Tests:** 12+ tests (retry scenarios, limits)

**Deliverables:**
- Error analysis and suggestions
- Auto-correction for typos
- Retry logic for transient errors
- 47+ tests

---

### 2.5 Query Optimization Hints

**Status:** 🔲 Not Started

#### Tasks:

- [ ] **Query Analyzer** (`core/optimizers.py`)
  - [ ] Track slow queries (>1s)
  - [ ] Analyze query plans
  - [ ] Identify missing indexes
  - [ ] **Tests:** 15+ tests (slow query detection, analysis)

- [ ] **Index Suggester** (`core/optimizers.py`)
  - [ ] Generate CREATE INDEX recommendations
  - [ ] Estimate performance improvement
  - [ ] Log suggestions with query patterns
  - [ ] **Tests:** 10+ tests (suggestions, accuracy)

**Deliverables:**
- Query performance monitoring
- Index suggestions
- 25+ tests
- Optimization reports

---

### Phase 2 Summary

**Total Tasks:** 33 tasks across 5 workstreams
**Total Tests:** 167+ tests
**Estimated Duration:** 2-3 weeks
**Dependencies:** Phase 1

**Key Deliverables:**
- Auto-batching optimizer
- Intelligent caching layer
- N+1 detection and auto-prefetch
- Error recovery with suggestions
- Query optimization hints
- 167+ comprehensive tests

**Performance Impact:**
- 10x faster inserts (auto-batching)
- 50x faster reads (N+1 elimination)
- 100x faster repeated queries (caching)

---

## Phase 3: Advanced Operations

**Goal:** Add advanced features (joins, search, clone, merge)

**Duration:** 3-4 weeks
**Status:** 🔲 Not Started
**Priority:** MEDIUM
**Dependencies:** Phase 1, 2

### 3.1 Advanced Joins

**Status:** 🔲 Not Started

#### Tasks:

- [ ] **Multi-Table Join** (`integrations/storage/supabase_client.py`)
  - [ ] `join(tables, select, filters, sort)` - Complex joins
  - [ ] Support INNER, LEFT, RIGHT joins
  - [ ] Multi-level joins (3+ tables)
  - [ ] Add to StorageInterface port
  - [ ] **Tests:** 25+ tests (all join types, 3+ tables)

- [ ] **Join Optimizer** (`core/optimizers.py`)
  - [ ] Optimize join order
  - [ ] Push filters to subqueries
  - [ ] Detect unnecessary joins
  - [ ] **Tests:** 15+ tests (optimization accuracy)

**Deliverables:**
- Advanced join capabilities
- Join optimizer
- 40+ tests

---

### 3.2 Full-Text Search

**Status:** 🔲 Not Started

#### Tasks:

- [ ] **Full-Text Search** (`integrations/storage/supabase_client.py`)
  - [ ] `search_full_text(tables, query, fields, ranking)` - Natural language search
  - [ ] Support multiple tables
  - [ ] Relevance ranking
  - [ ] Recent ranking option
  - [ ] Add to StorageInterface port
  - [ ] **Tests:** 20+ tests (multi-table, ranking, edge cases)

- [ ] **Search Index Management** (Database)
  - [ ] Create GIN indexes for full-text search
  - [ ] Migration script for indexes
  - [ ] Performance benchmarks
  - [ ] **Tests:** 10+ tests (index usage, performance)

**Deliverables:**
- Full-text search capabilities
- Search indexes
- 30+ tests
- Performance benchmarks

---

### 3.3 Streaming & Large Results

**Status:** 🔲 Not Started

#### Tasks:

- [ ] **Result Streaming** (`integrations/storage/supabase_client.py`)
  - [ ] `stream_results(query, chunk_size)` - Generator for large datasets
  - [ ] Memory-efficient iteration
  - [ ] Support for 100K+ rows
  - [ ] Add to StorageInterface port
  - [ ] **Tests:** 15+ tests (large datasets, memory usage)

- [ ] **Count Estimation** (`integrations/storage/supabase_client.py`)
  - [ ] `estimate_count(table, filters)` - Fast count for large tables
  - [ ] Use PostgreSQL statistics
  - [ ] Trade accuracy for speed
  - [ ] **Tests:** 10+ tests (accuracy, performance)

**Deliverables:**
- Streaming support
- Count estimation
- 25+ tests
- Memory benchmarks

---

### 3.4 Clone & Template Operations

**Status:** 🔲 Not Started

#### Tasks:

- [ ] **Clone Entity** (`integrations/storage/supabase_client.py`)
  - [ ] `clone_entity(table, source_id, overrides)` - Duplicate with changes
  - [ ] Support relation cloning
  - [ ] Exclude auto-generated fields
  - [ ] Add to StorageInterface port
  - [ ] **Tests:** 20+ tests (relations, overrides, exclusions)

- [ ] **Clone Integration** (`tools/universal_crud_tool.py`)
  - [ ] Add clone operation type
  - [ ] Support in OperationIntent
  - [ ] Transaction support
  - [ ] **Tests:** 15+ tests (integration scenarios)

**Deliverables:**
- Clone capabilities
- Universal CRUD integration
- 35+ tests

---

### 3.5 Merge & Deduplication

**Status:** 🔲 Not Started

#### Tasks:

- [ ] **Merge Entities** (`integrations/storage/supabase_client.py`)
  - [ ] `merge_entities(table, source_ids, target_id, strategy)` - Deduplication
  - [ ] Merge strategies (prefer_target, prefer_source, manual)
  - [ ] Update foreign key references
  - [ ] Add to StorageInterface port
  - [ ] **Tests:** 25+ tests (all strategies, FK updates)

- [ ] **Merge Integration** (`tools/universal_crud_tool.py`)
  - [ ] Add merge operation type
  - [ ] Support in OperationIntent
  - [ ] Transaction support
  - [ ] **Tests:** 15+ tests (integration scenarios)

**Deliverables:**
- Merge capabilities
- FK reference updates
- 40+ tests

---

### 3.6 Entity History & Comparison

**Status:** 🔲 Not Started

#### Tasks:

- [ ] **Change Tracking** (Database)
  - [ ] Create audit tables (trigger-based)
  - [ ] Capture all changes (INSERT, UPDATE, DELETE)
  - [ ] Store user context, timestamps, diffs
  - [ ] Migration script
  - [ ] **Tests:** 20+ tests (all operations, diffs)

- [ ] **History Retrieval** (`integrations/storage/supabase_client.py`)
  - [ ] `get_entity_history(table, id, time_range)` - Audit trail
  - [ ] Include diffs (before/after)
  - [ ] Filter by time range
  - [ ] Add to StorageInterface port
  - [ ] **Tests:** 15+ tests (time ranges, diffs, edge cases)

- [ ] **Entity Comparison** (`integrations/storage/supabase_client.py`)
  - [ ] `compare_entities(table, ids, diff_mode)` - Side-by-side diff
  - [ ] Support side-by-side and unified modes
  - [ ] Highlight differences
  - [ ] **Tests:** 12+ tests (modes, nested objects)

**Deliverables:**
- Change tracking infrastructure
- History retrieval
- Entity comparison
- 47+ tests

---

### Phase 3 Summary

**Total Tasks:** 48 tasks across 6 workstreams
**Total Tests:** 217+ tests
**Estimated Duration:** 3-4 weeks
**Dependencies:** Phase 1, 2

**Key Deliverables:**
- Advanced joins with optimizer
- Full-text search with indexes
- Streaming for large datasets
- Clone operations
- Merge and deduplication
- Entity history and comparison
- 217+ comprehensive tests

---

## Phase 4: Security & RLS

**Goal:** Implement Row-Level Security and access control

**Duration:** 2-3 weeks
**Status:** 🔲 Not Started
**Priority:** MEDIUM
**Dependencies:** Phase 1, 2, 3

### 4.1 RLS Policy Framework

**Status:** 🔲 Not Started

#### Tasks:

- [ ] **Policy Engine** (`core/rls.py`)
  - [ ] Policy definition schema (user, role, tenant, agent)
  - [ ] Policy evaluation engine
  - [ ] Policy caching
  - [ ] **Tests:** 25+ tests (all policy types, caching)

- [ ] **Policy Storage** (Database)
  - [ ] Create policies table
  - [ ] Policy versioning
  - [ ] Migration script
  - [ ] **Tests:** 10+ tests (CRUD on policies)

**Deliverables:**
- RLS policy framework
- Policy storage
- 35+ tests

---

### 4.2 Query-Time Policy Enforcement

**Status:** 🔲 Not Started

#### Tasks:

- [ ] **Query Rewriter** (`core/rls.py`)
  - [ ] Inject WHERE clauses from policies
  - [ ] Support multiple policy combination (AND/OR)
  - [ ] Optimize policy queries
  - [ ] **Tests:** 30+ tests (all policy types, combinations)

- [ ] **Storage Integration** (`integrations/storage/supabase_client.py`)
  - [ ] Apply policies to query_entities
  - [ ] Apply policies to insert/update/delete
  - [ ] Policy bypass for admin operations
  - [ ] **Tests:** 25+ tests (all operations, bypass)

**Deliverables:**
- Query rewriting with policies
- Storage integration
- 55+ tests

---

### 4.3 Attribute-Level Masking

**Status:** 🔲 Not Started

#### Tasks:

- [ ] **Field Masker** (`core/rls.py`)
  - [ ] Hide sensitive fields based on role
  - [ ] Support masking strategies (null, redacted, partial)
  - [ ] Apply at query time
  - [ ] **Tests:** 20+ tests (strategies, nested objects)

- [ ] **Masking Integration** (`integrations/storage/supabase_client.py`)
  - [ ] Apply masking to query results
  - [ ] Support nested field masking
  - [ ] **Tests:** 15+ tests (nested objects, edge cases)

**Deliverables:**
- Field masking capabilities
- 35+ tests

---

### 4.4 Audit Logging

**Status:** 🔲 Not Started

#### Tasks:

- [ ] **Audit Logger** (`core/audit.py`)
  - [ ] Log all data access (read, write, delete)
  - [ ] Capture user context, timestamp, filters
  - [ ] Structured logging format
  - [ ] **Tests:** 20+ tests (all operations, context)

- [ ] **Audit Storage** (Database)
  - [ ] Create audit_logs table
  - [ ] Retention policy (90 days)
  - [ ] Index for query performance
  - [ ] Migration script
  - [ ] **Tests:** 15+ tests (storage, retention, queries)

**Deliverables:**
- Audit logging infrastructure
- Audit storage with retention
- 35+ tests

---

### 4.5 Security Context Middleware

**Status:** 🔲 Not Started

#### Tasks:

- [ ] **Context Injector** (`core/middleware/security_context.py`)
  - [ ] Extract user context from request
  - [ ] Inject into operation context
  - [ ] Support multiple sources (JWT, session, API key)
  - [ ] **Tests:** 20+ tests (all sources, edge cases)

- [ ] **LangGraph Integration** (`workflows/`)
  - [ ] Add security context to workflow state
  - [ ] Propagate through specialist calls
  - [ ] **Tests:** 15+ tests (propagation, isolation)

**Deliverables:**
- Security context middleware
- LangGraph integration
- 35+ tests

---

### Phase 4 Summary

**Total Tasks:** 35 tasks across 5 workstreams
**Total Tests:** 195+ tests
**Estimated Duration:** 2-3 weeks
**Dependencies:** Phase 1, 2, 3

**Key Deliverables:**
- RLS policy framework
- Query-time policy enforcement
- Attribute-level masking
- Comprehensive audit logging
- Security context middleware
- 195+ comprehensive tests

**Security Impact:**
- Row-level access control
- Field-level masking
- Complete audit trail
- Multi-tenant support

---

## Dependencies & Prerequisites

### Phase Dependencies

```
Phase 1 (Foundation)
    │
    ├──> Phase 2 (Intelligence) ───┐
    │                               │
    └──> Phase 3 (Advanced) ────────┤
                                    │
                                    └──> Phase 4 (Security)
```

**Parallel Execution Opportunities:**
- Phase 2 and Phase 3 can run partially in parallel (independent workstreams)
- Phase 4 must wait for all previous phases

### Technical Prerequisites

**Required:**
- PostgreSQL 14+ (for advanced features)
- Supabase Python SDK 2.0+
- Python 3.12+
- Pydantic 2.0+
- LangChain v1.0+

**Optional:**
- Redis (for distributed caching in Phase 2)
- Elasticsearch (for advanced full-text search in Phase 3)

---

## Testing Strategy

### Test Coverage Targets

| Phase | Unit Tests | Integration Tests | Total | Coverage Target |
|-------|-----------|------------------|-------|----------------|
| Phase 1 | 170+ | 42+ | 212+ | 95%+ |
| Phase 2 | 134+ | 33+ | 167+ | 95%+ |
| Phase 3 | 174+ | 43+ | 217+ | 95%+ |
| Phase 4 | 156+ | 39+ | 195+ | 95%+ |
| **Total** | **634+** | **157+** | **791+** | **95%+** |

### Test Categories

**Unit Tests:**
- Engine logic (schema, read, write)
- Optimizers (batching, caching, prefetch)
- Policy evaluation
- Error recovery

**Integration Tests:**
- Storage adapter integration
- Tool integration
- LangGraph workflow integration
- End-to-end specialist scenarios

**Performance Tests:**
- Batch operation benchmarks (10x improvement)
- Cache hit rate (80%+ target)
- N+1 elimination (50x improvement)
- Query optimization (index usage)

**Security Tests:**
- RLS policy enforcement
- Field masking correctness
- Audit log completeness
- Context propagation

### Test Automation

**Continuous Integration:**
- Run all tests on every commit
- Performance regression detection
- Coverage enforcement (95%+ required)
- Linting (ruff check, mypy)

**Test Framework:**
- pytest for all tests
- pytest-asyncio for async tests
- pytest-cov for coverage
- hypothesis for property-based testing

---

## Migration Strategy

### Backward Compatibility

**Approach:** Gradual migration with dual-mode support

**Phase 1-3:**
- Old tools (query_database, universal_crud) continue to work
- New engines available alongside old tools
- Specialists can use either (preference for new)

**Phase 4 (Deprecation):**
- Mark old tools as deprecated
- Add deprecation warnings
- Migration guide published

**Phase 5 (Removal - Future):**
- Remove old tools
- All specialists migrated to new engines

### Specialist Migration Order

**Priority Order:**
1. Cataloging Specialist (uses most features)
2. Campaign Specialist (needs upsert, clone)
3. Market Intelligence Specialist (read-only, simpler)

**Per-Specialist Migration:**
1. Add new tools to specialist
2. Update prompts with new tool usage
3. Run comprehensive tests
4. Monitor in production (1 week)
5. Remove old tools if stable

### Data Migration

**No database schema changes required in Phase 1-3**

**Phase 4 (RLS):**
- Add policies table
- Add audit_logs table
- Backfill user context (if needed)
- Create indexes

**Migration Script:**
```sql
-- Phase 4 migration
-- See: migrations/004_rls_infrastructure.sql
```

---

## Success Metrics

### Phase 1 Success Criteria

**Functionality:**
✅ Schema tools accessible to all specialists
✅ Aggregations work across all tables
✅ Batch read handles 100+ IDs efficiently
✅ Upsert prevents duplicate errors
✅ Dry-run accurately predicts impact

**Performance:**
✅ Batch read 10x faster than N queries
✅ Pagination handles 100K+ rows
✅ Upsert 5x faster than check-then-insert

**Quality:**
✅ 212+ tests passing
✅ 95%+ code coverage
✅ Zero regressions

---

### Phase 2 Success Criteria

**Functionality:**
✅ Auto-batching works transparently
✅ Cache hit rate 80%+
✅ N+1 queries auto-detected and prefetched
✅ Error suggestions accurate (90%+ cases)

**Performance:**
✅ Auto-batching 10x faster than individual ops
✅ Cache 100x faster for repeated queries
✅ N+1 elimination 50x improvement
✅ Query optimizer reduces slow queries 80%

**Quality:**
✅ 167+ tests passing
✅ 95%+ code coverage
✅ Zero regressions

---

### Phase 3 Success Criteria

**Functionality:**
✅ Complex joins (3+ tables) work correctly
✅ Full-text search returns relevant results
✅ Streaming handles 1M+ rows
✅ Clone operations preserve relationships
✅ Merge operations update all FK references
✅ Entity history complete and accurate

**Performance:**
✅ Full-text search 100x faster than ILIKE
✅ Streaming constant memory usage
✅ Clone operations 5x faster than manual

**Quality:**
✅ 217+ tests passing
✅ 95%+ code coverage
✅ Zero regressions

---

### Phase 4 Success Criteria

**Functionality:**
✅ RLS policies enforced on all queries
✅ Field masking works for nested objects
✅ Audit logs capture all operations
✅ Security context propagates through workflows

**Security:**
✅ Zero policy bypass vulnerabilities
✅ Complete audit trail (100% operations)
✅ Context isolation (no cross-tenant leaks)

**Performance:**
✅ Policy evaluation <5ms overhead
✅ Audit logging <10ms overhead

**Quality:**
✅ 195+ tests passing
✅ 95%+ code coverage
✅ Security audit passed
✅ Zero regressions

---

## Risk Management

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| PostgreSQL performance degradation with RLS | HIGH | MEDIUM | Benchmark early, optimize policy queries, use indexes |
| Cache invalidation bugs | MEDIUM | MEDIUM | Comprehensive tests, conservative invalidation strategy |
| N+1 detection false positives | LOW | MEDIUM | Tunable thresholds, monitoring, manual override |
| Migration breaks existing specialists | HIGH | LOW | Backward compatibility, gradual rollout, comprehensive testing |

### Schedule Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Phase 1 takes longer (complex refactoring) | MEDIUM | MEDIUM | Buffer time in estimates, prioritize critical features |
| Testing takes longer than dev | MEDIUM | LOW | Parallel test development, automated test generation |
| Specialist migration delays | LOW | MEDIUM | Migration guide, automation scripts, dedicated support |

---

## Next Steps

### Immediate Actions

1. **Review & Approve Design** (This Week)
   - Architecture review with team
   - Q&A session on design decisions
   - Finalize phase priorities

2. **Spike: Schema Engine Prototype** (Week 1)
   - Build minimal schema tool
   - Test with cataloging specialist
   - Validate token efficiency

3. **Phase 1 Kickoff** (Week 2)
   - Create feature branches
   - Set up CI/CD for new code
   - Begin implementation

### Weekly Milestones

**Week 1-2:** Phase 1.1-1.2 (Schema Engine, Aggregations)
**Week 3-4:** Phase 1.3-1.5 (Batch, Upsert, Dry-Run)
**Week 5-6:** Phase 2.1-2.3 (Auto-Batching, Caching, N+1)
**Week 7-8:** Phase 2.4-2.5 + Phase 3.1 (Error Recovery, Joins)
**Week 9-10:** Phase 3.2-3.4 (Search, Streaming, Clone)
**Week 11-12:** Phase 3.5-3.6 + Phase 4.1 (Merge, History, RLS Foundation)
**Week 13:** Phase 4.2-4.5 (RLS Enforcement, Audit, Security Context)

---

## Status Tracking

**Last Updated:** 2025-01-23
**Next Review:** TBD (after Q&A session)

### Phase Status Legend

- 🔲 Not Started
- 🔄 In Progress
- ✅ Completed
- ⚠️ Blocked
- ❌ Cancelled

### Progress Tracking

| Phase | Tasks Complete | Tests Complete | Status | % Complete |
|-------|---------------|----------------|--------|-----------|
| Phase 1 | 0 / 42 | 0 / 212 | 🔲 | 0% |
| Phase 2 | 0 / 33 | 0 / 167 | 🔲 | 0% |
| Phase 3 | 0 / 48 | 0 / 217 | 🔲 | 0% |
| Phase 4 | 0 / 35 | 0 / 195 | 🔲 | 0% |
| **Total** | **0 / 158** | **0 / 791** | **🔲** | **0%** |

---

## Appendix

### Related Documents

- **Design:** [UNIVERSAL_DATA_ENGINE_DESIGN.md](../core/UNIVERSAL_DATA_ENGINE_DESIGN.md)
- **Current Architecture:** [ACTUAL_IMPLEMENTATION_ARCHITECTURE.md](../core/ACTUAL_IMPLEMENTATION_ARCHITECTURE.md)
- **Schema Design:** [DYNAMIC_SCHEMA_DRIVEN_ARCHITECTURE.md](../core/DYNAMIC_SCHEMA_DRIVEN_ARCHITECTURE.md)
- **CRUD Access Control:** [DYNAMIC_CRUD_ACCESS_CONTROL.md](../tech/DYNAMIC_CRUD_ACCESS_CONTROL.md)

### Glossary

- **RLS:** Row-Level Security (filter data by user/role/tenant)
- **N+1:** Anti-pattern where N queries execute in loop instead of batch
- **Upsert:** Insert or update (idempotent operation)
- **Dry-Run:** Preview operation impact without executing
- **ACID:** Atomicity, Consistency, Isolation, Durability (transaction guarantees)
