"""Autonomous Testing Framework tools for Claude.

This package provides information-gathering tools for Claude to orchestrate
testing, analysis, and improvement of the AutifyME agentic system.

Core Philosophy: Tools provide visibility, Claude provides intelligence.

Tool count: 7 essential observation tools
- execute_scenario: Run workflow tests
- get_trace_overview: Level 0 hierarchical trace analysis (~500 tokens)
- get_run_details: Level 1 specific run analysis (~1,500 tokens)
- get_run_messages: Level 2 full conversation (~5K+ tokens, rare)
- get_workflow_story: Multi-trace HITL workflow analysis (~500 tokens per trace)
- get_llm_trace_tree: LLM-only trace tree for prompt analysis (~2-5k tokens)
- list_recent_tests: Test history for progress tracking
"""

# Execution tool
from .execution import execute_scenario

# Models (for type hints and return types)
from .models import (
    ExecutionResult,
    HITLDecision,
    LLMCallNode,
    LLMTraceTree,
    Message,
    RunDetails,
    RunMessages,
    RunMetadata,
    RunNode,
    TestExecution,
    TestHistory,
    ToolCall,
    ToolResult,
    TraceOverview,
    WorkflowStory,
    WorkflowTrace,
)

# Test history tools
from .test_history import clear_test_history, list_recent_tests, record_test_execution

# Trace analysis tools
from .trace_analysis import (
    get_llm_trace_tree,
    get_run_details,
    get_run_messages,
    get_trace_overview,
    get_workflow_story,
)

__all__ = [
    # Execution
    "execute_scenario",
    "ExecutionResult",
    # Trace Analysis
    "get_trace_overview",
    "get_run_details",
    "get_run_messages",
    "get_workflow_story",
    "get_llm_trace_tree",
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
    # Test History
    "list_recent_tests",
    "record_test_execution",
    "clear_test_history",
    "TestHistory",
    "TestExecution",
]
