# Testing Architecture

**Philosophy: Claude Code IS the intelligence. Tools provide visibility.**

## Architecture Overview

```
Claude Code (you)
    |
    +-- chat_with_pm(message, thread_id?, media_path?)
    |       |
    |       +---> PM Agent ---> Specialists ---> Tools
    |       |
    |       <--- PMChatResult (structured response)
    |
    +-- [Evaluate response in real-time]
    |
    +-- get_trace_overview(trace_id)     -- Level 0: ~500 tokens
    +-- get_run_details(run_id)          -- Level 1: ~1,500 tokens
    +-- get_llm_trace_tree(trace_id)     -- LLM reasoning: ~2-5k tokens
```

## Tools

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `chat_with_pm` | Send message to PM, get response | Every test interaction |
| `get_trace_overview` | Hierarchical trace structure | When issues detected |
| `get_run_details` | Specific run inputs/outputs | Drill into failures |
| `get_llm_trace_tree` | LLM reasoning and prompts | Debug prompt issues |
| `get_workflow_story` | Multi-trace HITL analysis | Complex approval flows |

## Testing Flow

1. **Interact**: Send message with `chat_with_pm()`
2. **Evaluate**: Check response quality, routing, HITL compliance
3. **Continue**: Respond naturally to PM's questions/requests
4. **Analyze**: Use trace tools when issues detected
5. **Fix**: Update prompts/code based on findings
6. **Validate**: Re-run scenario to confirm fix

## What to Evaluate

- **Intent**: Did PM understand correctly?
- **Routing**: Right specialist chosen?
- **HITL**: Approval requested when required?
- **Quality**: Response helpful and accurate?
- **Completion**: Workflow finished properly?

## Quick Start

```python
from tests.tools import chat_with_pm, get_trace_overview

# Start conversation
result = chat_with_pm("Catalog these sneakers for $79.99")
print(result.pm_response)

# Continue conversation
if result.is_approval_request:
    result = chat_with_pm("Approved", thread_id=result.thread_id)

# Analyze if issues
if result.error or not result.workflow_complete:
    overview = get_trace_overview(result.trace_id)
    # Debug from here...
```

## Related Documentation

- [Hierarchical Trace Analysis](HIERARCHICAL_TRACE_ANALYSIS.md) - Token-efficient trace analysis strategy
- [Workflow Evaluation Framework](WORKFLOW_EVALUATION_FRAMEWORK.md) - Systematic evaluation methodology

## Skills

- `autonomous-testing` - Primary testing workflow
- `workflow-evaluation` - Deep trace analysis
- `agent-improvement` - Diagnosing underperforming agents
