from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any

from ..schemas.models import CompanyProfile, Product

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

    # NOTE: Pending approval methods removed - architecture uses LangGraph checkpoints
    # for HITL state persistence instead of database storage. If restart recovery
    # is needed for approvals, use LangGraph checkpoint restoration.
    # Removed methods: save_pending_approval(), get_pending_approval(), delete_pending_approval()

    # ========================================================================
    # Webhook Idempotency (Duplicate Message Detection)
    # ========================================================================

    @abstractmethod
    def check_and_mark_message_processed(
        self,
        message_id: str,
        sender_id: str,
        thread_id: str,
        received_at: datetime,
    ) -> bool:
        """
        Atomically check if message is duplicate AND mark as processed.

        This prevents duplicate webhook processing by tracking message_id in database.
        Survives server restarts and works across distributed containers.

        Args:
            message_id: WhatsApp message ID (unique across retries)
            sender_id: Phone number
            thread_id: LangGraph thread ID
            received_at: When webhook was received

        Returns:
            True if duplicate (already processed), False if new (now marked as processed)
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
        time_window: timedelta | None = None,
        intent: str | None = None,
        department: str | None = None,
        success: bool | None = None,
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
    # Generic CRUD Operations (Hexagonal Architecture - Port Methods)
    # ========================================================================

    @abstractmethod
    async def query_entities(
        self,
        table: str,
        filters: dict[str, Any],
        columns: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query entities with filters.

        Args:
            table: Table name
            filters: WHERE conditions as dict (e.g., {"is_active": True})
            columns: Columns to select (default: all columns)

        Returns:
            List of matching rows as dicts

        Example:
            rows = await storage.query_entities(
                "products",
                {"product_family_id": family_id, "is_active": True},
                ["id", "sku_code", "name"]
            )
        """
        pass

    @abstractmethod
    async def check_existing_values(
        self,
        table: str,
        column: str,
        values: list[Any],
    ) -> list[Any]:
        """
        Batch check which values exist in a column.

        Eliminates N+1 queries for uniqueness validation.

        Args:
            table: Table name
            column: Column to check
            values: List of values to check for existence

        Returns:
            List of values that already exist in the table

        Example:
            # Check which SKUs already exist
            existing_skus = await storage.check_existing_values(
                "products", "sku_code", ["SKU-001", "SKU-002", "SKU-003"]
            )
            # Returns ["SKU-001"] if only SKU-001 exists
        """
        pass

    @abstractmethod
    async def insert_entity(
        self,
        table: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Insert single entity.

        Args:
            table: Table name
            data: Entity data to insert

        Returns:
            Inserted row with generated fields (id, created_at, etc.)

        Raises:
            StorageError: On insert failure
        """
        pass

    @abstractmethod
    async def insert_entities(
        self,
        table: str,
        data: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Batch insert multiple entities in single query.

        Args:
            table: Table name
            data: List of entity data to insert

        Returns:
            List of inserted rows with generated fields

        Raises:
            StorageError: On insert failure
        """
        pass

    @abstractmethod
    async def update_entities(
        self,
        table: str,
        filters: dict[str, Any],
        updates: dict[str, Any],
    ) -> int:
        """
        Update entities matching filters.

        Args:
            table: Table name
            filters: WHERE conditions as dict
            updates: Fields to update

        Returns:
            Count of updated rows

        Raises:
            StorageError: On update failure
        """
        pass

    @abstractmethod
    async def delete_entities(
        self,
        table: str,
        filters: dict[str, Any],
    ) -> int:
        """
        Delete entities matching filters.

        Args:
            table: Table name
            filters: WHERE conditions as dict

        Returns:
            Count of deleted rows

        Raises:
            StorageError: On delete failure
        """
        pass

    # ========================================================================
    # Transaction Support (Phase 3)
    # ========================================================================

    @abstractmethod
    def transaction(self):
        """
        Create a transaction context manager for atomic operations.

        Usage:
            async with storage.transaction():
                family = await storage.insert_entity("product_families", data)
                axes = await storage.insert_entities("variant_axes", axes_data)
                products = await storage.insert_entities("products", products_data)
                # Auto-rollback on any exception

        Returns:
            Async context manager for transaction handling

        Raises:
            StorageError: On transaction failure

        Notes:
            - All operations within the context are atomic (all-or-nothing)
            - Exceptions trigger automatic rollback
            - Nested transactions may not be supported (adapter-specific)
            - Adapters without transaction support should provide best-effort rollback
        """
        pass

    # ========================================================================
    # Lifecycle Management
    # ========================================================================

    @abstractmethod
    def cleanup(self) -> None:
        """
        Cleanup resources on shutdown (connections, file handles, etc.).

        This method is called during application shutdown via atexit handlers.
        Implementations should:
        - Close database connections gracefully
        - Release file handles and network resources
        - Be idempotent (safe to call multiple times)
        - Not raise exceptions (log errors instead)

        For in-memory adapters or adapters without persistent connections,
        this can be a no-op.
        """
        pass
