"""Analytics mixin for workflow outcomes and schema intelligence."""

from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any

from autifyme_agents.schemas.models import CompanyProfile, WorkflowOutcome


class AnalyticsMixin(ABC):
    """Workflow outcome tracking and schema intelligence operations."""

    # ========================================================================
    # Company Profile
    # ========================================================================

    @abstractmethod
    def get_company_profile(self) -> CompanyProfile:
        """
        Retrieves the company profile from the storage layer.

        Since we operate in a single-tenant model, this fetches the one
        and only company profile for the instance.
        """
        pass

    # ========================================================================
    # Workflow Outcome Tracking (Agentic Evolution)
    # ========================================================================

    @abstractmethod
    def save_workflow_outcome(self, outcome: WorkflowOutcome) -> str:
        """
        Persist workflow outcome for learning and analytics.

        Args:
            outcome: WorkflowOutcome model with complete workflow execution data

        Returns:
            Outcome record ID (UUID)
        """
        pass

    @abstractmethod
    def get_workflow_outcomes(
        self,
        *,
        time_window: timedelta | None = None,
        intent: str | None = None,
        department: str | None = None,
        success: bool | None = None,
        limit: int = 100,
    ) -> list[WorkflowOutcome]:
        """
        Retrieve workflow outcomes for analysis.

        Args:
            time_window: Filter by time (e.g., last 7 days)
            intent: Filter by intent classification
            department: Filter by department
            success: Filter by success/failure
            limit: Maximum records to return

        Returns:
            List of WorkflowOutcome models ordered by received_at DESC
        """
        pass

    @abstractmethod
    def get_recent_failures(
        self,
        time_window: timedelta,
        limit: int = 10,
    ) -> list[WorkflowOutcome]:
        """
        Retrieve recent failures for regression test generation.

        Args:
            time_window: How far back to look
            limit: Maximum failures to return

        Returns:
            List of WorkflowOutcome models (failures only) ordered by received_at DESC
        """
        pass

    @abstractmethod
    def get_success_rates(
        self,
        time_window: timedelta | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get success rate analytics by department and intent.

        Args:
            time_window: Analysis window (default: 7 days)

        Returns:
            List of aggregated metrics:
                - department, intent
                - total_workflows, successful
                - success_rate_pct
                - avg_duration_seconds
        """
        pass

    @abstractmethod
    def get_edge_cases(
        self,
        time_window: timedelta | None = None,
        max_occurrence_count: int = 3,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Get low-frequency patterns (edge cases) for test synthesis.

        Args:
            time_window: Analysis window (default: 30 days)
            max_occurrence_count: Max occurrences to consider edge case
            limit: Maximum patterns to return

        Returns:
            List of edge case patterns with:
                - message_hash, sample_text
                - occurrence_count, last_seen
                - intent, department
                - avg_duration
        """
        pass

    # ========================================================================
    # Schema Intelligence
    # ========================================================================

    @abstractmethod
    async def get_table_stats(self, table: str) -> dict[str, Any]:
        """
        Get table statistics for schema intelligence.

        Provides runtime metadata about table size, last update, and index usage.
        Used by inspect_schema tool to give agents context about data volume.

        Args:
            table: Table name

        Returns:
            Dict with statistics:
                - row_count: Total rows in table
                - estimated_size_bytes: Approximate table size
                - last_updated: Timestamp of last modification (if available)
                - indexes: List of index names
                - primary_key: Primary key column name

        Raises:
            StorageError: On query failure or table not found
        """
        pass

    @abstractmethod
    async def sample_data(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Fetch sample data from table for schema intelligence.

        Provides real data examples to help agents understand schema usage patterns.

        Args:
            table: Table name
            filters: Optional filters to narrow samples
            limit: Maximum rows to return (default: 5)

        Returns:
            List of sample rows as dicts

        Raises:
            StorageError: On query failure or table not found
        """
        pass
