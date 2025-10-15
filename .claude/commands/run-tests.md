# Run Tests

Execute pytest test suite with coverage analysis.

## Usage

```
/run-tests [target]
```

**Targets**: `all`, `unit`, `integration`, `coverage`, `failed`, `specific`

## Task

Run pytest with coverage reporting, analyze results, identify coverage gaps in critical files (PM >80%, interrupt_coordinator >85%, runner >75%, departments >70%, specialists >70%), check for missing tests (HITL scenarios, PM delegation, department coordination, specialist invocations, state persistence, error recovery, media download).

Generate test results report with pass/fail/skip counts, coverage percentage, failed test details, coverage gaps with target percentages, missing test areas, and recommendations for improvement.
