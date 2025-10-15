# Explain Workflow

Explain how a specific workflow executes through the codebase.

## Usage

```
/explain-workflow [workflow-name]
```

**Workflows**: `cataloging`, `inquiry`, `conversational`, `all`

## Task

Trace workflow execution from entrypoint to completion:

1. **Read workflow documentation** in `docs/architecture/workflows/`
2. **Trace code path** through relevant files:
   - Entrypoint (webhook or CLI)
   - Orchestrator (`workflows/orchestration/runner.py`)
   - Project Manager (`workflows/project_manager.py`)
   - Departments (`departments/`)
   - Specialists (`specialists/`)
   - Tools (`tools/`)

3. **Explain execution flow**:
   - Message reception and normalization
   - PM intent classification and delegation
   - Department coordination
   - Specialist tool calls
   - HITL interrupts (if applicable)
   - Response generation

4. **Visualize with diagram** showing component interactions

5. **Identify key decision points**:
   - Intent routing logic
   - Tool selection criteria
   - Interrupt triggers
   - Error recovery paths

6. **Show data transformations** at each stage

7. **Highlight architectural patterns**:
   - DeepAgents planning tools usage
   - Middleware stack (context injection, summarization, HITL)
   - HITL resume level (PM vs department)
   - Context flow (ascending/descending hierarchy)

## Notes

- Focus on actual code behavior, not just documentation
- Include `file:line` references for key logic
- Explain HITL interrupt/resume flow for cataloging workflow
- Show data flow from WhatsApp payload → database record
