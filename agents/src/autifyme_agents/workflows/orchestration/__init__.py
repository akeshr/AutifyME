"""Workflow orchestration components.

This package contains channel-agnostic workflow coordination logic:
- WorkflowRunner: Generic orchestrator
- InterruptCoordinator: HITL interrupt handling
- StateManager: Approval state persistence
- RecoveryStrategy: Error recovery and abandonment detection
"""

from autifyme_agents.workflows.orchestration.state_manager import StateManager

# RecoveryStrategy and InterruptCoordinator will be added as we implement them
__all__ = [
    "StateManager",
]
