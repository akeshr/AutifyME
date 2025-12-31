# Database Migrations

This directory contains SQL migration scripts for AutifyME database schema evolution.

## Current Migrations

### 001_workflow_outcomes.sql (Phase 1.2 - Agentic Learning)

**Purpose**: Enables workflow outcome tracking for continuous learning

**Tables**:
- `workflow_outcomes` - Complete workflow execution records
- `routing_history` - Lightweight routing metrics

**Views**:
- `v_success_rates` - Success analytics by department/intent
- `v_recent_failures` - Recent failures for regression tests
- `v_edge_cases` - Low-frequency patterns for test synthesis

**Dependencies**:
- PostgreSQL 12+
- Future: pgvector extension (Phase 2 for embeddings)

---

## How to Apply Migrations

### Local Development (Supabase)

1. **Access Supabase SQL Editor**:
   - Go to your Supabase project dashboard
   - Navigate to SQL Editor

2. **Run Migration**:
   ```sql
   -- Copy/paste content of migration file
   -- Or use "New Query" and paste the SQL
   ```

3. **Verify Tables Created**:
   ```sql
   SELECT table_name
   FROM information_schema.tables
   WHERE table_schema = 'public'
     AND table_name LIKE 'workflow%';
   ```

4. **Verify Views Created**:
   ```sql
   SELECT table_name
   FROM information_schema.views
   WHERE table_schema = 'public'
     AND table_name LIKE 'v_%';
   ```

### Production (Future)

TODO: Set up migration management with:
- Alembic (Python migration tool)
- OR Flyway (Java-based, database-agnostic)
- OR Supabase Migration API

---

## Migration Naming Convention

Format: `{number}_{description}.sql`

- **Number**: 3-digit sequential (001, 002, 003)
- **Description**: Short kebab-case summary
- **Example**: `001_workflow_outcomes.sql`

---

## Rollback Strategy

For each migration, document rollback steps:

### 001_workflow_outcomes.sql Rollback

```sql
-- Drop views
DROP VIEW IF EXISTS v_edge_cases;
DROP VIEW IF EXISTS v_recent_failures;
DROP VIEW IF EXISTS v_success_rates;

-- Drop tables (CASCADE to handle foreign keys)
DROP TABLE IF EXISTS routing_history CASCADE;
DROP TABLE IF EXISTS workflow_outcomes CASCADE;

-- Drop trigger function
DROP FUNCTION IF EXISTS update_workflow_outcomes_timestamp();
```

---

## Testing Migrations

Before applying to production:

1. **Test on local Supabase instance**
2. **Verify no errors in SQL Editor**
3. **Run sample queries to test views**:
   ```sql
   SELECT * FROM v_success_rates LIMIT 5;
   SELECT * FROM v_recent_failures LIMIT 5;
   SELECT * FROM v_edge_cases LIMIT 5;
   ```
4. **Test rollback script**
5. **Document any issues encountered**

---

### 007_fix_array_type_handling.sql (Array Type Helper)

**Purpose**: Adds helper function for text[] column updates via `execute_write_intent` RPC

**Problem**: When updating array columns like `tags`, the RPC passes JSONB arrays directly, but PostgreSQL cannot implicitly cast `jsonb` to `text[]`.

**Error Fixed**: `column 'tags' is of type text[] but expression is of type jsonb` (Error 42804)

**Functions Added**:
- `jsonb_to_text_array(jsonb)` - Converts JSONB array to PostgreSQL text[]

**Next Step**: Patch `execute_write_intent` function to use this helper for text[] columns. See migration file for instructions.

**Rollback**:
```sql
DROP FUNCTION IF EXISTS jsonb_to_text_array(jsonb);
```

---

## Phase Roadmap

- [x] **Phase 1.2**: Outcome tracking tables and views
- [ ] **Phase 1.7**: WriteIntent RPC with array type support (helper added, patch pending)
- [ ] **Phase 2.1**: pgvector extension + embedding columns
- [ ] **Phase 2.2**: Routing optimization tables
- [ ] **Phase 3**: Auto-healing workflow tables

---

## Notes

- All timestamps use `TIMESTAMP WITH TIME ZONE` for UTC consistency
- JSON columns use `JSONB` for indexing and query performance
- Views auto-refresh (not materialized) - materialize in Phase 2 if needed
- Indexes optimized for read-heavy analytics workload
