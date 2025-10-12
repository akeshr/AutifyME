# Run Tests

Run pytest test suite with coverage analysis.

## Usage

```
/run-tests [target]
```

**Targets**: `all`, `unit`, `integration`, `coverage`, `failed`, `specific`

## Task

Execute test suite and analyze results.

### 1. Run Full Suite with Coverage

```bash
cd agents
uv run pytest --cov=autifyme_agents --cov-report=term-missing --cov-report=html -v
```

### 2. Run Specific Test Categories

**Unit Tests Only**:
```bash
uv run pytest tests/unit/ -v
```

**Integration Tests**:
```bash
uv run pytest tests/integration/ -v
```

**Specific Module**:
```bash
uv run pytest tests/test_cataloging_department.py -v
```

**Failed Tests Only** (rerun last failures):
```bash
uv run pytest --lf -v
```

### 3. Analyze Coverage

```bash
# Generate coverage report
uv run pytest --cov=autifyme_agents --cov-report=html

# Open in browser (Windows)
start htmlcov/index.html

# Check critical files
uv run pytest --cov=autifyme_agents --cov-report=term-missing | grep -E "(project_manager|interrupt_coordinator|runner)"
```

### 4. Identify Gaps

Check coverage for:
- `workflows/project_manager.py` - Should be >80%
- `workflows/orchestration/interrupt_coordinator.py` - Should be >85%
- `workflows/orchestration/runner.py` - Should be >75%
- `departments/cataloging_department.py` - Should be >70%
- `specialists/` - Should be >70%

### 5. Run Specific Test Patterns

```bash
# All HITL tests
uv run pytest -k "hitl" -v

# All interrupt tests
uv run pytest -k "interrupt" -v

# All approval tests
uv run pytest -k "approval" -v

# All image analysis tests
uv run pytest -k "image_analysis" -v
```

### 6. Check Test Quality

Verify tests exist for:
- ✅ HITL interrupt triggering
- ✅ HITL approval/rejection
- ✅ PM delegation to departments
- ✅ Department tool coordination
- ✅ Image specialist base64 conversion
- ✅ State persistence
- ✅ Error recovery
- ✅ Media download

### 7. Report

```markdown
## Test Results

**Total Tests**: [count]
**Passed**: [count] ✅
**Failed**: [count] ❌
**Skipped**: [count] ⚠️

**Coverage**: [percentage]%

### Failed Tests
[List with failure reasons]

### Coverage Gaps
**Files Below Target**:
- `file.py`: [current]% (target: [target]%)

**Uncovered Critical Paths**:
- [List important uncovered code sections]

### Missing Tests
- [Areas that need test coverage]

### Recommendations
- [Suggested improvements]
```

## Notes

- Tests should pass before merging to main
- Coverage should not decrease
- Run tests locally before pushing
- Check `agents/tests/README.md` for test writing guidelines
