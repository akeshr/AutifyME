# Check Architecture

Validate architectural patterns and best practices compliance.

## Usage

```
/check-architecture [focus]
```

**Focus**: `all`, `deepagents`, `hitl`, `hexagonal`, `context`, `tools`

## Task

Scan codebase for architectural violations: missing DeepAgents patterns (write_todos, CustomSubAgent), incorrect HITL patterns (wrong resume level), Hexagonal violations (context leakage, imports from integrations), tool anti-patterns (no ToolException, missing structured outputs), and deprecated imports.

Generate architecture validation report with compliant patterns, violations (file:line, issue, fix), statistics (files scanned, compliance rate), and prioritized recommendations.
