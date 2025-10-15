# Run Tests

Run pytest test suite with coverage analysis.

## Usage

```
/run-tests [target]
```

**Targets**: `all`, `unit`, `integration`, `coverage`, `failed`, `specific`

## Task

Execute test suite and analyze results:

### 1. Run Full Suite with Coverage
- Run pytest with `--cov=autifyme_agents --cov-report=term-missing --cov-report=html -v`
- Generate coverage report

### 2. Run Specific Test Categories
Options:
- Unit tests only: `tests/unit/`
- Integration tests: `tests/integration/`
- Specific module: `tests/test_cataloging_department.py`
- Failed tests only: `pytest --lf -v`

### 3. Analyze Coverage
- Generate HTML report
- Check critical files coverage:
  - PM >80%
  - interrupt_coordinator >85%
  - runner >75%
  - departments >70%
  - specialists >70%

### 4. Identify Gaps
List uncovered:
- Critical code paths
- Error handlers
- HITL scenarios
- Specialist invocations

### 5. Run Specific Test Patterns
Filter tests:
- HITL tests: `pytest -k "hitl"`
- Interrupt tests: `pytest -k "interrupt"`
- Approval tests: `pytest -k "approval"`
- Image analysis: `pytest -k "image_analysis"`

### 6. Check Test Quality
Verify tests exist for:
- HITL interrupt/approval/rejection
- PM delegation
- Department tool coordination
- Image specialist base64 conversion
- State persistence
- Error recovery
- Media download

## Output

Generate test results report with:
- **Total Tests**: Passed/Failed/Skipped counts
- **Coverage**: Percentage
- **Failed Tests**: List with failure reasons
- **Coverage Gaps**: Files below target with percentages
- **Missing Tests**: Areas needing coverage
- **Recommendations**: Suggested improvements

## Notes

- Tests should pass before merging
- Coverage should not decrease
- Run tests locally before pushing
- Check `tests/README.md` for writing guidelines
