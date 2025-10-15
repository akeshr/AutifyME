# Test Suite Organization

## Test Types

### Pytest Tests (`test_*.py`)
Proper pytest tests collected and run by `uv run pytest tests/`:

**Unit Tests** (`tests/unit/`):
- `test_cataloging_tools.py` - Tool function tests
- `test_middleware.py` - Middleware logic tests
- `test_specialists.py` - Specialist agent tests
- `test_storage_tools.py` - Storage adapter tests

**Integration Tests** (`tests/integration/`):
- `test_cataloging_department.py` - Department-level workflows
- `test_project_manager.py` - PM intent classification
- `test_workflow.py` - Multi-component integration

**E2E Tests** (`tests/e2e/`):
- `test_batch_approval.py` - Batch HITL approval flows
- `test_department_parallel_interrupts.py` - Parallel department HITL
- `test_e2e_batch.py` - Full batch cataloging workflows
- `test_runner_parallel_extraction.py` - Parallel action extraction

**Synthesizer Tests** (`tests/synthesizer/`):
- `test_synthesizer.py` - Synthesizer component tests

### Standalone Scripts (`run_*.py`)
Executable scripts with CLI output, NOT collected by pytest:

**E2E Standalone** (`tests/e2e/`):
- `run_comprehensive_tests.py` - Full workflow scenarios
- `run_hitl_comprehensive.py` - Generic HITL comprehensive test
- `run_hitl_extended.py` - Extended HITL phrasing variations
- `run_hitl_simple.py` - Simple HITL approval/rejection
- `run_hitl_with_db_validation.py` - HITL + Supabase validation
- `run_hitl_with_images.py` - Image-based HITL workflows
- `run_interactive_tests.py` - Interactive terminal testing
- `run_live_monitor.py` - Live workflow monitoring

Execute directly: `uv run python tests/e2e/run_hitl_with_images.py`

### CLI Testing Tools (`tests/cli/`)
Interactive terminal-based testing (not pytest):

- `pm_chat.py` - Direct PM agent testing
- `simulate.py` - Full workflow simulation with HITL
- `debug.py` - Debug helpers
- `permutation_test.py` - Scenario permutation testing

See `docs/architecture/LOCAL_TESTING_STRATEGY.md` for usage.

## Running Tests

**CI/CD Command:**
```bash
uv run pytest tests --cov=autifyme_agents --cov-report=xml
```

**Quick Validation:**
```bash
uv run pytest tests/unit -v          # Fast unit tests
uv run pytest tests/integration -v   # Integration tests
uv run pytest tests/e2e -v           # E2E pytest tests
```

**Standalone Scripts:**
```bash
uv run python tests/e2e/run_hitl_with_images.py
```

**Interactive CLI:**
```bash
uv run python -m tests.cli.pm_chat --interactive
uv run python -m tests.cli.simulate
```

## Key Distinction

- **`test_*.py`**: Pytest tests (no `sys.exit()`, use pytest fixtures/assertions)
- **`run_*.py`**: Standalone scripts (have `sys.exit()`, print CLI output)

This separation prevents pytest collection errors (`INTERNALERROR: SystemExit`) when standalone scripts execute at import time.
