# Update Docs

Sync documentation with code changes.

## Usage

```
/update-docs [doc-type]
```

**Types**: `architecture`, `workflows`, `api`, `all`, `check`

## Task

Update documentation to reflect current codebase state:

### 1. Check Documentation Drift
Compare docs with actual implementation:
- **AGENTS_DESIGN.md**: Check if DeepAgents patterns documented, planning tools mentioned
- **PROJECT_MANAGER_DESIGN.md**: Verify PM capabilities current
- **HITL docs**: Check if PM-level resume pattern documented
- **Workflow docs**: Verify sequential execution vs parallel documented correctly

### 2. Update Architecture Docs
Update if hierarchy changed:
- **AGENTS_DESIGN.md**: Current PM → Department → Specialist structure, DeepAgents integration, planning tools, HITL pattern
- **PROJECT_MANAGER_DESIGN.md**: PM tools (write_todos, task delegation), implementation with create_deep_agent
- **ACTUAL_IMPLEMENTATION_ARCHITECTURE.md**: As-built architecture verification

### 3. Update Workflow Documentation
**WHATSAPP_CATALOGING_WORKFLOW.md** - Update flow if changed:
- PM planning step (write_todos)
- Department planning step
- Sequential vs parallel execution
- HITL interrupt location
- PM-level resume pattern

### 4. Update API Documentation
- Generate API docs from code (inspect docstrings)
- Create/update API_REFERENCE.md with function signatures
- Include examples

### 5. Update Workflow Diagrams
- Update Mermaid diagrams if flow changed
- Ensure diagrams show: planning steps, sequential execution, HITL points

### 6. Check for Outdated Examples
- Find all code examples in docs (`grep -r "\`\`\`python"`)
- Verify examples still work with current API
- Update deprecated patterns (AgentExecutor → create_agent, etc.)

### 7. Update CLAUDE.md
Update project instructions if patterns changed:
- LangChain v1 patterns
- DeepAgents integration
- Planning tools usage
- HITL patterns

### 8. Update README
Sync with current features:
- Feature list (architecture, HITL, multimodal, etc.)
- Quick start instructions
- Architecture overview

## Output

Generate documentation update summary:
- **Critical Updates**: Code drift issues (with specific sections)
- **Minor Updates**: Examples, diagrams
- **New Documentation Needed**: Topics not yet documented
- **Outdated Sections**: What needs removal/replacement
- **Verification Checklist**: Examples tested, diagrams current, no deprecated refs
- **Priority**: High / Medium / Low
- **Estimated Effort**: Hours

## Quick Check

Search for outdated terms:
- AgentExecutor, ReAct, chain (deprecated LangChain patterns)
- Old file paths (if structure changed)
- Deprecated APIs

## Notes

- Update docs when architecture changes
- Keep examples tested and working
- Date-stamp major doc updates
- Link related docs
- Use consistent terminology
