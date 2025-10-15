# Analyze Traces

Analyze LangSmith traces to identify issues and patterns.

## Usage

```
/analyze-traces <trace-id-1> [trace-id-2] [trace-id-3] ...
```

## Task

For each trace: dump to file, analyze for common issues (HITL errors, image specialist hallucinations, tool coordination problems, PM delegation errors, state issues), extract key information (user input, workflow status, tool calls, errors), and identify root causes.

Present findings for each trace with status, user input, tool calls, root cause, evidence with line numbers, and recommended fix. For multiple traces, identify cross-trace patterns.

Focus on architectural issues: DeepAgents planning tools usage, HITL resume level, tool result passing, local file path conversion.
