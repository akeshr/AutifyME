from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any, Optional

from ..schemas.models import Product, CompanyProfile

# Note for Abhi (from our discussion):
# This is the equivalent of a Java or TypeScript `interface`. It defines a
# contract that any storage provider we use *must* adhere to.
# The `@abstractmethod` decorator is like marking a method as abstract.


class StorageInterface(ABC):
    """
    Defines the abstract interface (the "Port") for all storage operations.

    Any concrete storage implementation (like Supabase, DynamoDB, etc.) must
    inherit from this class and implement all its abstract methods. This ensures
    that our application's core logic is decoupled from any specific
    database technology.
    """

    @abstractmethod
    def get_company_profile(self) -> CompanyProfile:
        """
        Retrieves the company profile from the storage layer.

        Since we operate in a single-tenant model, this fetches the one
        and only company profile for the instance.
        """
        pass

    @abstractmethod
    def save_product(self, product: Product) -> Product:
        """
        Saves a product to the storage layer.

        Args:
            product: The Product object to save.

        Returns:
            The saved Product object, potentially updated with new data
            from the database (like a creation timestamp).
        """
        pass

    @abstractmethod
    def save_pending_approval(
        self,
        thread_id: str,
        interrupt_id: str,
        checkpoint_id: str,
        tool_call: dict[str, Any],
        draft_summary: str,
        ai_message: Optional[dict[str, Any]] = None,
        image_path: Optional[str] = None,
    ) -> str:
        """
        Persists a pending HITL approval to survive server restarts.

        Args:
            thread_id: LangGraph thread ID (e.g., 'whatsapp:917258067800')
            interrupt_id: LangGraph Interrupt.id for resumption
            checkpoint_id: Checkpoint ID where the interrupt occurred
            tool_call: The tool call that triggered the interrupt (e.g., save_product)
            draft_summary: Human-readable summary sent to user
            ai_message: The AIMessage that initiated the tool call (for Command resume)
            image_path: Optional path to temp image file for cleanup after approval/rejection

        Returns:
            The approval record ID (UUID)
        """
        pass

    @abstractmethod
    def get_pending_approval(self, thread_id: str) -> Optional[dict[str, Any]]:
        """
        Retrieves a pending approval by thread ID.

        Args:
            thread_id: LangGraph thread ID

        Returns:
            Approval record dict or None if not found
        """
        pass

    @abstractmethod
    def delete_pending_approval(self, thread_id: str) -> bool:
        """
        Removes a pending approval after it's been handled (approved/rejected).

        Args:
            thread_id: LangGraph thread ID

        Returns:
            True if deleted, False if not found
        """
        pass

    # ========================================================================
    # Phase 1.2: Workflow Outcome Tracking (Agentic Evolution)
    # ========================================================================

    @abstractmethod
    def save_workflow_outcome(self, outcome: dict[str, Any]) -> str:
        """
        Persist workflow outcome for learning and analytics.

        Args:
            outcome: Complete workflow record with:
                - tracking_id: Unique identifier
                - thread_id: LangGraph thread ID
                - sender_id: User identifier
                - message_text: User's message
                - message_hash: Content hash for similarity
                - media_id, media_type, platform: Optional media info
                - received_at: When message was received
                - intent, department: Routing decision
                - routing_reasoning: PM's reasoning
                - routing_confidence: Optional confidence score
                - alternative_departments: Fallback options
                - routed_at: When routing occurred
                - success: Whether workflow succeeded
                - error_type, error_message: If failed
                - resolution_strategy: How error was handled
                - result_data: Structured result if successful
                - duration_seconds: Execution time
                - started_at, ended_at: Timestamps
                - learned_patterns, failure_warnings: Extracted learnings
                - applied_strategies: Which strategies were used

        Returns:
            Outcome record ID (UUID)
        """
        pass

    @abstractmethod
    def get_workflow_outcomes(
        self,
        *,
        time_window: Optional[timedelta] = None,
        intent: Optional[str] = None,
        department: Optional[str] = None,
        success: Optional[bool] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Retrieve workflow outcomes for analysis.

        Args:
            time_window: Filter by time (e.g., last 7 days)
            intent: Filter by intent classification
            department: Filter by department
            success: Filter by success/failure
            limit: Maximum records to return

        Returns:
            List of outcome records ordered by created_at DESC
        """
        pass

    @abstractmethod
    def get_recent_failures(
        self,
        time_window: timedelta,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Retrieve recent failures for regression test generation.

        Args:
            time_window: How far back to look
            limit: Maximum failures to return

        Returns:
            List of failure records ordered by recency
        """
        pass

    @abstractmethod
    def get_success_rates(
        self,
        time_window: Optional[timedelta] = None,
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
        time_window: Optional[timedelta] = None,
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
