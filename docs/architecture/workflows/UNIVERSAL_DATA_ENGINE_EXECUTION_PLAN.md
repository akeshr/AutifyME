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

**Refactor Existing Code:**
- `query_database_tool.py` → Absorb into Read Engine
- `universal_crud_tool.py` → Absorb into Write Engine
- Storage port → Extend with new methods
- Schema registry → Enhance with intelligence features

**Keep Backward Compatibility During Migration:**
- Old tools work alongside new engines
- Gradual specialist migration (one at a time)
- Deprecation warnings before removal
- Complete migration guide

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
**Status:** 🔲 Not Started
**Priority:** CRITICAL

### 1.1 Schema Engine - Core Features

**Status:** 🔲 Not Started

#### Tasks:

- [ ] **Schema Tool Factory** (`tools/schema_tools.py`)
  - [ ] Create `create_schema_tool()` factory with table restrictions
  - [ ] Support capability filtering (introspect, relationships, stats)
  - [ ] Integrate with existing SchemaRegistry
  - [ ] Add access control enforcement
  - [ ] **Tests:** 15+ tests (factory, access control, caching)

- [ ] **Schema Discovery** (`tools/schema_tools.py`)
  - [ ] `explore_schema(domain)` - List tables with metadata
  - [ ] `get_schema(tables, depth)` - Fetch targeted schema
  - [ ] Schema caching per session (avoid repeated fetches)
  - [ ] Minimal response format (token-efficient)
  - [ ] **Tests:** 10+ tests (depth levels, caching, performance)

- [ ] **Table Statistics** (`integrations/storage/supabase_client.py`)
  - [ ] `get_table_stats(table)` - Row counts, column stats
  - [ ] Index information retrieval
  - [ ] Last updated timestamp
  - [ ] Add to StorageInterface port
  - [ ] **Tests:** 8+ tests (all tables, empty tables, performance)

- [ ] **Data Sampling** (`integrations/storage/supabase_client.py`)
  - [ ] `sample_data(table, filters, limit)` - Real examples
  - [ ] Respect RLS policies (future-proof)
  - [ ] Add to StorageInterface port
  - [ ] **Tests:** 10+ tests (filters, limits, edge cases)

**Deliverables:**
- Schema tool factory with access control
- Schema discovery APIs
- Table statistics APIs
- Data sampling APIs
- 40+ tests (unit + integration)
- Documentation updates

---

### 1.2 Read Engine - Aggregations

**Status:** 🔲 Not Started

#### Tasks:

- [ ] **Aggregation Support** (`integrations/storage/supabase_client.py`)
  - [ ] Extend `query_advanced()` with aggregation support
  - [ ] Support metrics: count, sum, avg, min, max
  - [ ] GROUP BY support
  - [ ] HAVING clause support (filter aggregated results)
  - [ ] Add to StorageInterface port
  - [ ] **Tests:** 20+ tests (all metrics, GROUP BY, HAVING)

- [ ] **Read Tool Enhancement** (`tools/query_database_tool.py`)
  - [ ] Add `aggregate()` method to query_database tool
  - [ ] Integrate with existing query capabilities
  - [ ] Maintain backward compatibility
  - [ ] Add examples to docstrings
  - [ ] **Tests:** 15+ tests (specialist scenarios)

**Deliverables:**
- Aggregation support in storage layer
- Enhanced query_database tool
- 35+ tests
- Updated documentation

---

### 1.3 Read Engine - Batch Operations

**Status:** 🔲 Not Started

#### Tasks:

- [ ] **Batch Read** (`integrations/storage/supabase_client.py`)
  - [ ] `batch_read(table, ids, include)` - Fetch multiple by ID
  - [ ] Optimize with IN clause (single query)
  - [ ] Prefetch related entities (solve N+1)
  - [ ] Preserve ID order in results
  - [ ] Add to StorageInterface port
  - [ ] **Tests:** 12+ tests (100+ IDs, includes, order preservation)

- [ ] **Pagination** (`integrations/storage/supabase_client.py`)
  - [ ] `paginate(query, page, per_page, cursor)` - Smart pagination
  - [ ] Cursor-based pagination for large datasets
  - [ ] Optional total count (skip COUNT(*) if not needed)
  - [ ] Add to StorageInterface port
  - [ ] **Tests:** 15+ tests (offset, cursor, edge cases)

**Deliverables:**
- Batch read capabilities
- Pagination support (offset + cursor)
- 27+ tests
- Performance benchmarks

---

### 1.4 Write Engine - Upsert & Patch

**Status:** 🔲 Not Started

#### Tasks:

- [ ] **Upsert Support** (`integrations/storage/supabase_client.py`)
  - [ ] `upsert_entity(table, data, conflict_fields)` - Insert or update
  - [ ] Support conflict field specification
  - [ ] Return operation type (inserted vs. updated)
  - [ ] Add to StorageInterface port
  - [ ] **Tests:** 18+ tests (conflicts, multiple fields, edge cases)

- [ ] **Bulk Upsert** (`integrations/storage/supabase_client.py`)
  - [ ] `bulk_upsert(table, data, conflict_fields)` - Batch upsert
  - [ ] Optimize with single query
  - [ ] Return inserted/updated counts
  - [ ] Add to StorageInterface port
  - [ ] **Tests:** 12+ tests (1000+ entities, performance)

- [ ] **Partial Update (Patch)** (`integrations/storage/supabase_client.py`)
  - [ ] `patch_entity(table, id, partial_updates)` - Update specific fields
  - [ ] Support nested object merging (shallow/deep)
  - [ ] Preserve unspecified fields
  - [ ] Add to StorageInterface port
  - [ ] **Tests:** 15+ tests (nested objects, merge strategies)

- [ ] **Universal CRUD Tool Enhancement** (`tools/universal_crud_tool.py`)
  - [ ] Add upsert operation type
  - [ ] Add patch operation type
  - [ ] Integrate with existing OperationExecutor
  - [ ] Update OperationIntent schema
  - [ ] **Tests:** 20+ tests (integration with transactions)

**Deliverables:**
- Upsert capabilities (single + bulk)
- Patch support
- Enhanced universal_crud_tool
- 65+ tests
- Updated schemas

---

### 1.5 Write Engine - Dry-Run & Validation

**Status:** 🔲 Not Started

#### Tasks:

- [ ] **Dry-Run Mode** (`tools/universal_crud_tool.py`)
  - [ ] `dry_run(operations)` - Preview without executing
  - [ ] Calculate impact (entities affected)
  - [ ] Run validation checks
  - [ ] Estimate execution time
  - [ ] Return warnings and safe-to-execute flag
  - [ ] **Tests:** 20+ tests (all operation types, edge cases)

- [ ] **Validation Preview** (`tools/universal_crud_tool.py`)
  - [ ] `validate_before_write(operations)` - Pre-flight checks
  - [ ] Schema validation
  - [ ] Constraint checking
  - [ ] Permission verification
  - [ ] Conflict detection
  - [ ] **Tests:** 25+ tests (all validation types)

**Deliverables:**
- Dry-run capabilities
- Validation preview
- 45+ tests
- Updated tool documentation

---

### Phase 1 Summary

**Total Tasks:** 42 tasks across 5 workstreams
**Total Tests:** 212+ tests
**Estimated Duration:** 2-3 weeks
**Dependencies:** None (foundation phase)

**Key Deliverables:**
- Schema Engine with discovery, stats, sampling
- Read Engine with aggregations, batch read, pagination
- Write Engine with upsert, patch, dry-run, validation
- 200+ comprehensive tests
- Updated documentation

**Migration Impact:**
- Existing tools continue to work
- New capabilities available immediately
- No breaking changes

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
