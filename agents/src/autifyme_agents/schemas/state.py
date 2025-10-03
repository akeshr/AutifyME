from __future__ import annotations

from typing import Annotated, Literal, Optional, Sequence
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from deepagents.state import DeepAgentState

from autifyme_agents.schemas.models import CatalogingResult, CompanyProfile


class DepartmentResults(TypedDict, total=False):
    cataloging: CatalogingResult


class ProjectMetadata(TypedDict, total=False):
    workflow_id: str
    workflow_type: str


class ProjectManagerState(DeepAgentState, total=False):
    """Structured state carried by the Project Manager deep agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    company_profile: CompanyProfile
    plan: list[dict]
    current_step: int
    department_results: DepartmentResults
    status: Literal["idle", "planning", "awaiting_approval", "completed", "blocked"]
    last_error: Optional[str]
    metadata: ProjectMetadata
