---
name: autonomous-testing
description: Execute autonomous testing where AI monitors PM behavior and triggers debugging when issues arise (project)
---

# Autonomous Testing

## Your Role

**You ARE the intelligent tester.** You interact with the PM like a real user, evaluate each response in real-time, and trigger deep analysis when issues arise.

No external AI monitors - you understand the architecture, you know what violations look like, you reason about quality.

## Core Workflow

**1. Interact with PM**
```python
from tests.tools import chat_with_pm

# Start conversation
result = chat_with_pm(
    message="Catalog these sneakers for $79.99",
    media_path="test_images/sneaker.jpg"  # optional
)

# Evaluate response
print(f"PM Response: {result.pm_response}")
print(f"Approval Request: {result.is_approval_request}")
print(f"Turn: {result.conversation_turn}")
```

**2. Evaluate Each Response**

As you receive each response, evaluate:
- **Intent understanding**: Did PM correctly understand what user wants?
- **Routing decision**: Did PM delegate to appropriate specialist?
- **Response quality**: Is the response helpful and accurate?
- **Architectural compliance**: Does PM follow HITL protocol?

**3. Continue Conversation**
```python
# PM asks clarifying question
result = chat_with_pm("It's a Nike Air Max, size 10", thread_id=result.thread_id)

# PM requests approval
result = chat_with_pm("Approved", thread_id=result.thread_id)

# Check completion
if result.workflow_complete:
    print("Workflow completed successfully")
```

**4. Deep Analysis (When Issues Detected)**

Use trace analysis when you detect problems:
```python
from tests.tools import get_trace_overview, get_llm_trace_tree, get_run_details

# Level 0: Overview (~500 tokens)
overview = get_trace_overview(result.trace_id)

# Find failures
def find_issues(node, issues=[]):
    if node.status == "error":
        issues.append(f"{node.name}: {node.error}")
    for child in node.children:
        find_issues(child, issues)
    return issues

# Level 1: LLM reasoning (~2-5k tokens)
llm_tree = get_llm_trace_tree(result.trace_id)
for node in llm_tree.llm_tree:
    if "project_manager" in node.agent_name.lower():
        print("PM reasoning:", node.assistant_output)
```

**5. Fix and Validate**

After fixing issues:
```python
# Re-run same scenario
result = chat_with_pm("Catalog these sneakers for $79.99", media_path="test_images/sneaker.jpg")
# Evaluate: Is the issue fixed?
```

## What to Evaluate

| Aspect | What to Check |
|--------|---------------|
| **Intent** | Did PM understand the request correctly? |
| **Routing** | Right specialist for the task? |
| **HITL** | Approval requested when required? |
| **Quality** | Response helpful, accurate, complete? |
| **Completion** | Workflow finished properly? |

## Architectural Violations to Catch

- **PM says "complete" but didn't persist**: Check trace for save_product tool call
- **PM stuck/silent**: Conversation stalled, no meaningful response
- **PM looping**: Repeating same response without progress
- **Skipped HITL**: PM saved without user approval
- **Wrong specialist**: Task delegated to incorrect domain expert

## Available Tools

| Tool | Purpose | Tokens |
|------|---------|--------|
| `chat_with_pm(message, thread_id?, media_path?)` | Send message, get response | N/A |
| `get_trace_overview(trace_id)` | Hierarchical trace structure | ~500 |
| `get_run_details(run_id)` | Specific run inputs/outputs | ~1,500 |
| `get_llm_trace_tree(trace_id)` | LLM reasoning and prompts | ~2-5k |
| `get_workflow_story(trace_ids)` | Multi-trace HITL analysis | ~500/trace |

## Testing Protocol

1. **Start with a scenario** - Real user request with clear intent
2. **Evaluate first response** - Did PM understand? Right direction?
3. **Continue naturally** - Respond as user would to PM's questions/requests
4. **Approve or reject** - When HITL requested, make informed decision
5. **Verify completion** - Check workflow_complete, validate in database
6. **Analyze if issues** - Use trace tools for deep debugging

## Success Criteria

- PM correctly understands user intent
- PM routes to appropriate specialists
- PM requests approval before persisting (HITL compliance)
- Workflow completes successfully
- Data persisted correctly (verify with Supabase MCP)

## Related Skills

- **Deep trace analysis**: Use `workflow-evaluation` for systematic investigation
- **Prompt fixes**: Use `prompt-engineering` when updating prompts
- **Agent diagnosis**: Use `agent-improvement` for gap analysis
