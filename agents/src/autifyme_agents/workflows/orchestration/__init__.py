"""Workflow orchestration components.

This package contains channel-agnostic workflow coordination logic:
- WorkflowRunner: Generic orchestrator with native LangGraph HITL support

Design: Simplified architecture - removed 700+ lines of custom interrupt handling.
Framework handles all state management via checkpointers.
"""

from autifyme_agents.workflows.orchestration.runner import WorkflowRunner

__all__ = [
    "WorkflowRunner",
]
