# Explain Workflow

Trace and explain how a workflow executes through the codebase.

## Usage

```
/explain-workflow [workflow-name]
```

**Workflows**: `cataloging`, `inquiry`, `conversational`, `all`

## Task

Read workflow documentation, trace code path from entrypoint through orchestrator/PM/departments/specialists/tools, explain execution flow (message reception, PM intent classification, department coordination, specialist tool calls, HITL interrupts, response generation), visualize with component interaction diagram, identify key decision points (intent routing, tool selection, interrupt triggers, error recovery), show data transformations at each stage, and highlight architectural patterns (DeepAgents planning, middleware stack, HITL resume level, context flow).

Focus on actual code behavior with file:line references, not just documentation.
