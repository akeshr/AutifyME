# Deploy Check

Comprehensive pre-deployment validation.

## Usage

```
/deploy-check
```

## Task

Validate deployment readiness: code quality (linting, tests, coverage), architecture compliance (DeepAgents patterns, HITL resume, Hexagonal), environment variables, code hygiene (TODOs, unused imports), database connections, API access, and git status.

Generate checklist report with pass/fail for each category, blockers requiring fixes, warnings to monitor, and overall deploy status (Ready / With Caution / Not Ready) with clear recommendation.
