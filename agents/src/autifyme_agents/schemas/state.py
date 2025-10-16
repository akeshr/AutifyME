from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated, Literal

from deepagents.state import DeepAgentState  # type: ignore[import-untyped]
from langchain.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from autifyme_agents.schemas.models import CatalogingResult, CompanyProfile

# Use | instead of Union for type annotations (Python 3.10+)
MessageType = HumanMessage | SystemMessage | AIMessage


class DepartmentResults(TypedDict, total=False):
    cataloging: CatalogingResult


class ProjectMetadata(TypedDict, total=False):
    workflow_id: str
    workflow_type: str


class InterruptInfo(TypedDict, total=False):
    """Information about a pending HITL interrupt."""

    interrupt_id: str
    tool_name: str
    tool_args: dict[str, object]
    description: str


class ProjectManagerState(DeepAgentState):  # type: ignore[misc]
    """Structured state carried by the Project Manager deep agent."""

    messages: Annotated[Sequence[MessageType], add_messages]
    company_profile: CompanyProfile
    plan: list[dict[str, object]]
    current_step: int
    department_results: DepartmentResults
    status: Literal["idle", "planning", "awaiting_approval", "completed", "blocked"]
    last_error: str | None
    metadata: ProjectMetadata
    pending_interrupts: list[InterruptInfo]  # HITL interrupt context for PM
