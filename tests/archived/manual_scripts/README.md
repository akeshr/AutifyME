# Archived Manual Test Scripts

## Archived: 2025-01-24

These scripts were moved from `tests/` root during codebase cleanup. They are **manual test scripts** or **outdated validation scripts**, not part of the organized pytest test suite.

### Files

1. **phase1_behavior_test.py** (4.7KB)
   - Manual PM behavior validation script
   - Tests conversational behavior without manual input
   - NOT a pytest test file (no `test_` functions)
   - Usage: Run directly with `python tests/archived/manual_scripts/phase1_behavior_test.py`

2. **phase1_validation.py** (9.4KB)
   - Phase 1 validation with 5 pytest tests
   - **Status when archived**: All 5 tests failing
   - Errors: async function issues, tool invocation errors
   - Tests: PM initialization, base context loading, query tools, scenario matrix

3. **phase2c_intelligent_tests.py** (13KB)
   - Intelligent testing framework for Phase 2C
   - Manual test script with AI-powered validation
   - NOT a pytest test file

4. **test_update_variant_with_image_intelligent.py** (4.5KB)
   - Specific UPDATE test scenario with intelligent monitoring
   - Manual test script
   - Tests variant update with image handling

### Why Archived

**Issues:**
- Not part of organized test structure (tests/unit/, tests/integration/)
- Manual scripts mixed with pytest tests
- phase1_validation.py tests were failing (5/5 failed)
- Duplicate coverage with modern test suite

**Modern Test Organization:**
```
tests/
├── unit/           # Unit tests (organized by module)
├── integration/    # Integration tests
├── fixtures/       # Shared test fixtures
├── conftest.py     # Pytest configuration
└── archived/       # Historical/deprecated tests
```

### Current Test Coverage

The functionality tested by these scripts is now covered by:
- **489 passing tests** in organized structure
- `tests/unit/tools/test_write_intent_execution.py` (55 tests)
- `tests/unit/tools/test_data_engine_tools.py`
- `tests/integration/test_pm_data_engine_integration.py`
- Full agent integration test suite

### Usage (If Needed)

**Manual Scripts:**
```bash
cd /home/user/AutifyME
# Run manual behavior test
python tests/archived/manual_scripts/phase1_behavior_test.py

# Run intelligent tests
python tests/archived/manual_scripts/phase2c_intelligent_tests.py
```

**pytest Tests (failing):**
```bash
# These will fail - archived for reference only
uv run pytest tests/archived/manual_scripts/phase1_validation.py -v
```

### Restoration

To restore functionality from these scripts:
1. Review modern test suite first (may already cover requirements)
2. Extract unique test scenarios
3. Integrate into organized test structure (tests/unit/ or tests/integration/)
4. Follow current pytest patterns and conventions

### Related Documentation

- Testing framework: `docs/architecture/tech/TESTING_FRAMEWORK.md`
- Test organization: `tests/README.md` (if exists)
- Intelligent testing: `docs/architecture/testing/` (check for docs on AI-powered testing)
