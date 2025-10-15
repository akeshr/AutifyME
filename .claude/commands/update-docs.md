# Update Docs

Sync documentation with current codebase state.

## Usage

```
/update-docs [doc-type]
```

**Types**: `architecture`, `workflows`, `api`, `all`, `check`

## Task

Check for documentation drift (DeepAgents patterns, planning tools, HITL resume, sequential execution), update architecture docs if hierarchy changed, update workflow documentation if flow changed, generate API docs from code, update diagrams if flow changed, check for outdated code examples and deprecated patterns, update CLAUDE.md and README with current features.

Generate documentation update summary with critical updates needed (specific sections), minor updates, new documentation needed, outdated sections to remove, verification checklist, priority level, and estimated effort.
