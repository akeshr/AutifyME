"""Testing Tools for Claude Code.

This package provides tools for Claude Code to test and evaluate the AutifyME
PM agent. The architecture is simple:

1. **PM Interaction** - chat_with_pm() sends messages and gets structured responses
2. **Trace Analysis** - Hierarchical lazy-loading tools for deep debugging
3. **Evaluation Data Extraction** - Structured data for Claude to evaluate behavior
4. **LangSmith Integration** - Store evaluations, track history, manage baselines

Philosophy: Claude Code IS the evaluator. These tools provide structured data
for Claude to reason about and storage for continuous improvement.

Tool Inventory:
- chat_with_pm: Send message to PM, get structured response for evaluation
- get_trace_overview: Level 0 hierarchical trace analysis (~500 tokens)
- get_run_details: Level 1 specific run with inputs/outputs (~1,500 tokens)
- get_run_messages: Level 2 full conversation (~5K+ tokens, rare)
- get_workflow_story: Multi-trace HITL workflow analysis
- get_llm_trace_tree: LLM-only trace for prompt analysis (~2-5k tokens)

Evaluation Data Extraction:
- get_tool_call_sequence: Ordered tool calls with agent attribution
- get_delegation_graph: Agent delegation hierarchy and waves
- get_file_io_trace: File read/write operations by agent
- get_protocol_loads: Protocol loading by agent with compliance check
- get_agent_final_message: Final message analysis (open question, etc.)

LangSmith Feedback Integration:
- record_evaluation: Store evaluation results for history
- get_scenario_history: Query past runs and failure patterns
- get_baseline: Get known-good trace for comparison
- store_baseline: Save trace as reference baseline
- compare_to_baseline: Compare trace against baseline (matches/deviations)
"""

# PM Interaction
from .pm_interaction import chat_with_pm, clear_all_sessions, clear_session

# Models - Core
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

# Models - Evaluation
from .models import (
    AgentDelegation,
    AgentFinalMessage,
    DelegationGraph,
    EvaluationCriterion,
    EvaluationResult,
    FileIOTrace,
    FileOperation,
    ProtocolLoad,
    ProtocolLoadTrace,
    ScenarioHistory,
    ScenarioRunSummary,
    SequencedToolCall,
    ThreadTrace,
    ThreadTraces,
    ToolCallSequence,
    TraceBaseline,
)

# Trace Analysis - Core
from .trace_analysis import (
    get_llm_trace_tree,
    get_run_details,
    get_run_messages,
    get_trace_overview,
    get_workflow_story,
)

# Trace Analysis - Evaluation Data Extraction
from .trace_analysis import (
    get_agent_final_message,
    get_delegation_graph,
    get_file_io_trace,
    get_protocol_loads,
    get_tool_call_sequence,
)

# LangSmith Feedback Integration
from .trace_analysis import (
    compare_to_baseline,
    get_baseline,
    get_scenario_history,
    record_evaluation,
    store_baseline,
)

# Multi-Turn Thread Analysis
from .trace_analysis import get_thread_traces

# LangSmith Annotation Queue Integration
from .trace_analysis import add_to_evaluation_queue, get_evaluation_queue_url

__all__ = [
    # PM Interaction
    "chat_with_pm",
    "clear_session",
    "clear_all_sessions",
    "PMChatResult",
    # Trace Analysis - Core
    "get_trace_overview",
    "get_run_details",
    "get_run_messages",
    "get_workflow_story",
    "get_llm_trace_tree",
    # Trace Analysis - Evaluation Data Extraction
    "get_tool_call_sequence",
    "get_delegation_graph",
    "get_file_io_trace",
    "get_protocol_loads",
    "get_agent_final_message",
    # LangSmith Feedback Integration
    "record_evaluation",
    "get_scenario_history",
    "get_baseline",
    "store_baseline",
    "compare_to_baseline",
    # Multi-Turn Thread Analysis
    "get_thread_traces",
    "ThreadTrace",
    "ThreadTraces",
    # LangSmith Annotation Queue
    "add_to_evaluation_queue",
    "get_evaluation_queue_url",
    # Models - Core
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
    # Models - Evaluation
    "ToolCallSequence",
    "SequencedToolCall",
    "DelegationGraph",
    "AgentDelegation",
    "FileIOTrace",
    "FileOperation",
    "ProtocolLoadTrace",
    "ProtocolLoad",
    "AgentFinalMessage",
    "EvaluationResult",
    "EvaluationCriterion",
    "ScenarioHistory",
    "ScenarioRunSummary",
    "TraceBaseline",
]
