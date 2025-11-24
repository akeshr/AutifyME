# Legacy Phase 2C Tests (Universal CRUD Tool)

## Archived: 2025-01-24

These test files were archived during codebase cleanup as they test **deprecated architecture**:

### Files

1. **test_dynamic_crud_access_control.py** (568 lines)
   - Unit tests for dynamic schema generation in universal_crud_tool
   - Tests operation-scoped tool factory
   - 40+ tests for CRUD access control patterns

2. **test_phase2c_e2e.py** (1055 lines)
   - End-to-end integration tests for Phase 2C
   - Tests Specialist → OperationIntent → PM → Universal Tool → Database flow
   - 62 tests covering CREATE, READ, UPDATE, DELETE operations
   - Tests rollback, validation, schema enforcement

### Why Archived

**Old Architecture (deprecated):**
- Single `universal_crud_tool.py` handling all CRUD operations
- `OperationIntent` schema
- Monolithic tool with dynamic schema generation

**New Architecture (current):**
- Split into `read_data` and `write_data` tools
- `WriteIntent` schema with dependency resolution
- Clean separation of read/write concerns

**Test Coverage:**
- New tests provide equivalent coverage:
  - `tests/unit/tools/test_write_intent_execution.py` (55 tests)
  - `tests/unit/tools/test_data_engine_tools.py`
  - `tests/integration/test_pm_data_engine_integration.py`

### Status When Archived

✅ **All 62 tests passing** (as of archival date)

Test results showed:
```
62 passed, 1 warning in 5.35s
```

### Historical Reference

These tests validate critical Phase 2C requirements and can be referenced for:
- Understanding original CRUD patterns
- Verifying test coverage migration completeness
- Historical architecture documentation

### Running Archived Tests

To run these tests:
```bash
cd /home/user/AutifyME
uv run pytest tests/archived/phase2c_legacy/ -v
```

⚠️ **Warning**: These tests depend on `universal_crud_tool.py` which was deleted.
To run them, you would need to restore the tool from git history.

### Related Changes

- Deleted: `agents/src/autifyme_agents/tools/universal_crud_tool.py` (1662 lines)
- Deleted: `agents/src/autifyme_agents/tools/query_database_tool.py` (327 lines)
- Migrated: PM workflow to use new data_engine tools
- Active: New test suite in `tests/unit/tools/` and `tests/integration/`
