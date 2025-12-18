"""Testing Tools for Claude Code.

This package provides tools for Claude Code to test and evaluate the AutifyME
PM agent. The architecture is simple:

1. **PM Interaction** - chat_with_pm() sends messages and gets structured responses
2. **Trace Analysis** - Hierarchical lazy-loading tools for deep debugging

Philosophy: Claude Code IS the intelligence. These tools provide visibility.

Tool Inventory:
- chat_with_pm: Send message to PM, get structured response for evaluation
- get_trace_overview: Level 0 hierarchical trace analysis (~500 tokens)
- get_run_details: Level 1 specific run with inputs/outputs (~1,500 tokens)
- get_run_messages: Level 2 full conversation (~5K+ tokens, rare)
- get_workflow_story: Multi-trace HITL workflow analysis
- get_llm_trace_tree: LLM-only trace for prompt analysis (~2-5k tokens)
"""

# PM Interaction
from .pm_interaction import chat_with_pm, clear_all_sessions, clear_session

# Models
from .models import (
    HITLDecision,
    LLMCallNode,
    LLMTraceTree,
    Message,
    PMChatResult,
    RunDetails,
    RunMessages,
    RunMetadata,
    RunNode,
    ToolCall,
    ToolResult,
    TraceOverview,
    WorkflowStory,
    WorkflowTrace,
)

# Trace Analysis
from .trace_analysis import (
    get_llm_trace_tree,
    get_run_details,
    get_run_messages,
    get_trace_overview,
    get_workflow_story,
)

__all__ = [
    # PM Interaction
    "chat_with_pm",
    "clear_session",
    "clear_all_sessions",
    "PMChatResult",
    # Trace Analysis
    "get_trace_overview",
    "get_run_details",
    "get_run_messages",
    "get_workflow_story",
    "get_llm_trace_tree",
    # Models
    "TraceOverview",
    "RunNode",
    "RunDetails",
    "RunMessages",
    "Message",
    "RunMetadata",
    "ToolCall",
    "ToolResult",
    "WorkflowStory",
    "WorkflowTrace",
    "HITLDecision",
    "LLMCallNode",
    "LLMTraceTree",
]
