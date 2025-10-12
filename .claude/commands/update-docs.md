# Update Docs

Sync documentation with code changes.

## Usage

```
/update-docs [doc-type]
```

**Types**: `architecture`, `workflows`, `api`, `all`, `check`

## Task

Update documentation to reflect current codebase state.

### 1. Check Documentation Drift

Compare documentation with actual implementation:

**Check AGENTS_DESIGN.md**:
```bash
cd docs/architecture

# Check if PM uses DeepAgents
if grep -q "DeepAgents" AGENTS_DESIGN.md; then
    echo "✅ AGENTS_DESIGN mentions DeepAgents"
else
    echo "⚠️  AGENTS_DESIGN.md may need update for DeepAgents"
fi

# Check if write_todos is documented
if grep -q "write_todos\|planning tool" AGENTS_DESIGN.md; then
    echo "✅ Planning tools documented"
else
    echo "⚠️  Planning tools not documented"
fi
```

**Check HITL documentation**:
```bash
# Check if HITL resume pattern is documented
if grep -q "resume.*PM level\|pm_factory" docs/architecture/*.md; then
    echo "✅ HITL resume pattern documented"
else
    echo "⚠️  HITL documentation may be outdated"
fi
```

### 2. Update Architecture Docs

**AGENTS_DESIGN.md** - Update if hierarchy changed:
```markdown
## Current Hierarchy

```
PM (DeepAgent)
  ├─ write_todos (planning tool)
  └─ Cataloging Department (CustomSubAgent)
       ├─ write_todos (planning tool)
       ├─ image_analysis_specialist (tool)
       ├─ cataloging_specialist (tool)
       └─ save_product (tool, HITL-enabled)
```

## Key Patterns

### DeepAgents Integration
- PM and departments use `create_deep_agent`
- Planning via `write_todos` tool
- Departments as CustomSubAgent for PM
- Specialists as tools with structured outputs

### HITL Pattern
- HITL via ToolConfig on save_product
- Interrupt at PM level (task tool)
- Resume using Command.resume at PM level
- State persisted to pending_approvals table
```

**PROJECT_MANAGER_DESIGN.md** - Update PM capabilities:
```markdown
## Tools

### Planning
- `write_todos`: Break down multi-step workflows

### Delegation
- `task`: Delegate to departments (built-in via subagents)

## Implementation

```python
from deepagents import create_deep_agent
from deepagents.tools import write_todos

pm = create_deep_agent(
    tools=[write_todos],
    instructions=pm_prompt,
    subagents=[cataloging_dept],  # CustomSubAgent
    checkpointer=checkpointer
)
```
```

### 3. Update Workflow Documentation

**WHATSAPP_CATALOGING_WORKFLOW.md** - Update flow:

Add planning steps:
```markdown
## Workflow Steps

### 1. PM Receives Message
- Classifies intent: cataloging
- **Optional**: Uses write_todos to plan

### 2. PM Delegates to Department
- Calls task tool with semantic description
- Department receives: text + media path

### 3. Department Plans Work
- **Calls write_todos** to create plan:
  1. Analyze image
  2. Structure product (using analysis)
  3. Save product
- Updates todos as it progresses

### 4. Department Executes
- **Sequential execution** (not parallel)
- Passes image analysis to cataloging specialist
- Calls save_product with individual fields

### 5. HITL Approval
- Interrupt triggers before save_product executes
- Approval request sent to user
- State persisted with media path

### 6. Resume After Approval
- **Resume at PM level** using pm_factory
- PM continues from checkpoint
- save_product executes with approval
```

### 4. Update API Documentation

Generate API docs from code:
```bash
cd agents

# Generate docs for key modules
uv run python -c "
import inspect
from autifyme_agents.workflows.project_manager import create_project_manager
from autifyme_agents.departments.cataloging_department import create_cataloging_department

print('## Project Manager')
print(inspect.getdoc(create_project_manager))
print()
print('## Cataloging Department')
print(inspect.getdoc(create_cataloging_department))
" > ../docs/API_REFERENCE.md
```

### 5. Update Workflow Diagrams

Update Mermaid diagrams if flow changed:

**Before** (parallel tools):
```mermaid
Department --> image_analysis
Department --> cataloging_specialist
```

**After** (sequential with planning):
```mermaid
Department --> write_todos: Plan
Department --> image_analysis: Execute step 1
Department --> cataloging_specialist: Execute step 2 (uses analysis)
Department --> save_product: Execute step 3
```

### 6. Check for Outdated Examples

```bash
cd docs/architecture

# Find code examples in docs
grep -r "```python" . | cut -d: -f1 | sort -u

# Check if examples still work
for file in $(grep -r "```python" . | cut -d: -f1 | sort -u); do
    echo "Checking examples in: $file"
    # Extract and test code blocks (manual review)
done
```

### 7. Update CLAUDE.md

Update project instructions if patterns changed:

```markdown
### LangChain & Agent Patterns
- Default to LangChain v1 native patterns
- Use `create_deep_agent` for PM and departments
- **Add planning tools**: `write_todos` for multi-step coordination
- Use `CustomSubAgent` for pre-built department graphs
- HITL via ToolConfig, resume at PM level with pm_factory
```

### 8. Update README

Sync README with current features:
```markdown
## Features

- ✅ **Hierarchical Agent Architecture**: PM → Departments → Specialists
- ✅ **DeepAgents Integration**: Planning tools and delegation
- ✅ **HITL Approval**: Human-in-the-loop for product saving
- ✅ **Multi-modal**: Text + images/videos
- ✅ **Base64 Vision**: Automatic local file conversion
- ✅ **State Persistence**: Checkpoint-based recovery
```

### 9. Generate Update Summary

```markdown
## Documentation Updates Needed

### Critical Updates (Code Drift)
- [ ] AGENTS_DESIGN.md: Add DeepAgents patterns
- [ ] PROJECT_MANAGER_DESIGN.md: Document planning tools
- [ ] WHATSAPP_CATALOGING_WORKFLOW.md: Update sequential flow
- [ ] HITL documentation: PM-level resume pattern

### Minor Updates
- [ ] Update API examples with write_todos
- [ ] Refresh workflow diagrams
- [ ] Update CLAUDE.md with latest patterns

### New Documentation Needed
- [ ] DeepAgents integration guide
- [ ] Planning tool best practices
- [ ] HITL troubleshooting guide

### Outdated Sections
- [Section in doc X]: Needs update because [reason]

### Verification
- [ ] All code examples tested
- [ ] Diagrams match current flow
- [ ] No references to deprecated patterns

---

**Priority**: High / Medium / Low
**Estimated Effort**: [hours]
```

## Quick Doc Check

```bash
# Check for common outdated terms
cd docs/architecture
grep -r "AgentExecutor\|ReAct\|chain" . --include="*.md" | \
    grep -v "supply chain" | \
    head -10

echo "Found references to deprecated patterns above"
```

## Notes

- Update docs when architecture changes
- Keep examples tested and working
- Date-stamp major doc updates
- Link related docs
- Use consistent terminology
