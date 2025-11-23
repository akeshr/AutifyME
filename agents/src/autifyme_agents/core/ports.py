from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Literal, overload

from ..schemas.models import CompanyProfile, WorkflowOutcome

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

    # NOTE: Legacy methods removed - use universal_crud_tool for all persistence
    # Removed methods: save_product() - use execute_database_operation instead
    #
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
    # Generic CRUD Operations (Hexagonal Architecture - Port Methods)
    # ========================================================================

    @abstractmethod
    async def query_entities(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        columns: list[str] | None = None,
        relations: list[str] | None = None,
        search_patterns: dict[str, str] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query entities with optional filters, relations, and search.

        Args:
            table: Table name
            filters: WHERE conditions as dict (e.g., {"is_active": True})
            columns: Columns to select (default: all columns)
            relations: Related tables to include (e.g., ["categories(*)", "variant_axes(*)"])
            search_patterns: Case-insensitive LIKE patterns (e.g., {"name": "%bottle%"})
            limit: Maximum rows to return

        Returns:
            List of matching rows as dicts (always a list, never int)

        Example:
            # Simple query
            rows = await storage.query_entities(
                "products",
                {"product_family_id": family_id, "is_active": True},
                ["id", "sku_code", "name"]
            )

            # With relations
            families = await storage.query_entities(
                "product_families",
                {"is_active": True},
                relations=["categories(*)", "variant_axes(*)"]
            )
        """
        pass

    @abstractmethod
    async def count_entities(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        search_patterns: dict[str, str] | None = None,
    ) -> int:
        """
        Count entities matching filters.

        Args:
            table: Table name
            filters: WHERE conditions as dict (e.g., {"is_active": True})
            search_patterns: Case-insensitive LIKE patterns (e.g., {"name": "%bottle%"})

        Returns:
            Count of matching rows (always an int, never a list)

        Example:
            # Count all active products
            total = await storage.count_entities(
                "products",
                {"is_active": True}
            )

            # Count with search
            matching = await storage.count_entities(
                "products",
                search_patterns={"name": "%bottle%"}
            )
        """
        pass

    @abstractmethod
    async def check_existing_values(
        self,
        table: str,
        column: str,
        values: list[Any],
        exclude_ids: list[Any] | None = None,
    ) -> list[Any]:
        """
        Batch check which values exist in a column.

        Eliminates N+1 queries for uniqueness validation.

        Args:
            table: Table name
            column: Column to check
            values: List of values to check for existence
            exclude_ids: Optional list of record IDs to exclude from check
                        (enables idempotent update validation)

        Returns:
            List of values that already exist in the table

        Example:
            # Check which SKUs already exist
            existing_skus = await storage.check_existing_values(
                "products", "sku_code", ["SKU-001", "SKU-002", "SKU-003"]
            )
            # Returns ["SKU-001"] if only SKU-001 exists

            # Check uniqueness for update (exclude record being updated)
            existing_skus = await storage.check_existing_values(
                "products", "sku_code", ["SKU-001"],
                exclude_ids=["uuid-123"]
            )
            # Returns [] if SKU-001 only exists on record uuid-123
        """
        pass

    @overload
    async def query_advanced(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        columns: list[str] | None = None,
        relations: list[str] | None = None,
        search_patterns: dict[str, str] | None = None,
        count_only: Literal[True] = ...,
        limit: int | None = None,
    ) -> int: ...

    @overload
    async def query_advanced(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        columns: list[str] | None = None,
        relations: list[str] | None = None,
        search_patterns: dict[str, str] | None = None,
        count_only: Literal[False] = ...,
        limit: int | None = None,
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def query_advanced(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        columns: list[str] | None = None,
        relations: list[str] | None = None,
        search_patterns: dict[str, str] | None = None,
        count_only: bool = False,
        limit: int | None = None,
    ) -> list[dict[str, Any]] | int:
        """
        Advanced query with relations, pattern matching, and counting.

        Supports complex queries needed by middleware and tools without
        requiring direct adapter access.

        Args:
            table: Table name
            filters: Exact match filters (e.g., {"is_active": True})
            columns: Columns to select (default: all columns)
            relations: Related tables to include using PostgREST syntax
                      (e.g., ["categories(*)", "variant_axes(variant_values(*))"])
            search_patterns: Case-insensitive LIKE patterns
                            (e.g., {"name": "%bottle%", "brand": "%acme%"})
            count_only: If True, return count instead of rows
            limit: Maximum rows to return

        Returns:
            List of matching rows (as dicts) if count_only=False, else int count

        Example:
            # Query with relations
            families = await storage.query_advanced(
                "product_families",
                filters={"is_active": True},
                relations=["categories(*)", "variant_axes(*)"],
                limit=10
            )

            # Search with ILIKE
            families = await storage.query_advanced(
                "product_families",
                search_patterns={"name": "%bottle%"},
                columns=["id", "name", "sku_prefix"]
            )

            # Get count
            count = await storage.query_advanced(
                "products",
                filters={"product_family_id": family_id},
                count_only=True
            )
        """
        pass

    @abstractmethod
    async def query_aggregate(
        self,
        table: str,
        aggregates: dict[str, str],
        filters: dict[str, Any] | None = None,
        search_patterns: dict[str, str] | None = None,
        group_by: list[str] | None = None,
        having: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query with aggregations (count, sum, avg, min, max) and GROUP BY.

        Universal Data Engine - Phase 1.2: Aggregation support for analytics queries.

        Enables agents to perform analytical queries like:
        - Count products by category
        - Sum sales by region
        - Average price by brand
        - Min/max values per group

        Args:
            table: Table name
            aggregates: Aggregation operations as {alias: "function(column)"}
                       Examples:
                       - {"total": "count(*)"} - count all rows
                       - {"total_price": "sum(price)"} - sum of prices
                       - {"avg_rating": "avg(rating)"} - average rating
                       - {"min_price": "min(price)", "max_price": "max(price)"}
            filters: Exact match filters applied before aggregation
            search_patterns: ILIKE patterns applied before aggregation
            group_by: Columns to group by (e.g., ["category", "brand"])
            having: Filters on aggregated results (e.g., {"total": {"gt": 100}})

        Returns:
            List of aggregated results, each row contains:
            - All group_by columns
            - All aggregate aliases with their computed values

        Examples:
            # Count products per category
            results = await storage.query_aggregate(
                "products",
                aggregates={"count": "count(*)"},
                group_by=["category_id"]
            )
            # Returns: [{"category_id": "cat1", "count": 15}, ...]

            # Average price per brand, only brands with >10 products
            results = await storage.query_aggregate(
                "products",
                aggregates={"avg_price": "avg(base_price)", "product_count": "count(*)"},
                group_by=["brand"],
                having={"product_count": {"gt": 10}}
            )

            # Total active products (no grouping)
            results = await storage.query_aggregate(
                "products",
                aggregates={"total_active": "count(*)"},
                filters={"is_active": True}
            )
            # Returns: [{"total_active": 42}]

        Raises:
            StorageError: On query failure or invalid aggregate syntax
        """
        pass

    @abstractmethod
    async def batch_read(
        self,
        table: str,
        ids: list[str],
        relations: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch multiple entities by ID in single query (batch operation).

        Universal Data Engine - Phase 1.3: Batch read to solve N+1 query problems.

        Optimizes multi-entity retrieval by:
        - Single query with IN clause (vs N individual queries)
        - Optional relation prefetching to avoid cascading queries
        - Preserves input ID order in results

        Args:
            table: Table name
            ids: List of entity IDs to fetch
            relations: Optional relations to prefetch (PostgREST syntax)
                      Examples: ["products(*)", "variants(*)"]

        Returns:
            List of entities matching the IDs, in the same order as input IDs.
            Missing IDs are omitted (no null placeholders).

        Examples:
            # Fetch 100 products by ID (single query)
            products = await storage.batch_read(
                "products",
                ids=["id1", "id2", ..., "id100"]
            )

            # Fetch products with prefetched families
            products = await storage.batch_read(
                "products",
                ids=product_ids,
                relations=["product_families(id,name)"]
            )

        Performance:
            - Efficiently handles 100+ IDs in single query
            - Prefetching relations eliminates N+1 queries
            - Result ordering preserved for consistent UX

        Raises:
            StorageError: On query failure
        """
        pass

    @abstractmethod
    async def paginate_query(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        search_patterns: dict[str, str] | None = None,
        relations: list[str] | None = None,
        order_by: str | None = None,
        page: int = 1,
        per_page: int = 20,
        cursor: str | None = None,
        include_count: bool = False,
    ) -> dict[str, Any]:
        """
        Paginate query results with offset or cursor-based pagination.

        Universal Data Engine - Phase 1.3: Smart pagination for large datasets.

        Supports two pagination modes:
        1. **Offset pagination** (traditional): page + per_page
        2. **Cursor pagination** (efficient for large sets): cursor + per_page

        Args:
            table: Table name
            filters: Exact match filters (e.g., {"is_active": True})
            search_patterns: ILIKE patterns (e.g., {"name": "%bottle%"})
            relations: Relations to include (PostgREST syntax)
            order_by: Sort specification (e.g., "created_at.desc", "name.asc")
            page: Page number (1-indexed, for offset pagination)
            per_page: Items per page (default 20, max 100)
            cursor: Cursor token for cursor-based pagination (overrides page)
            include_count: Whether to include total count (expensive for large tables)

        Returns:
            Dict with pagination metadata and results:
            {
                "data": [...],          # List of entities
                "page": 1,              # Current page (offset mode)
                "per_page": 20,         # Items per page
                "total": 150,           # Total count (if include_count=True)
                "has_next": True,       # Whether more pages exist
                "next_cursor": "xyz",   # Cursor for next page (cursor mode)
            }

        Examples:
            # Offset pagination - Page 2, 50 items per page
            result = await storage.paginate_query(
                "products",
                filters={"is_active": True},
                page=2,
                per_page=50,
                include_count=True
            )

            # Cursor pagination - Efficient for large datasets
            result = await storage.paginate_query(
                "products",
                cursor="eyJpZCI6IjEyMyJ9",
                per_page=100
            )

            # With relations prefetch
            result = await storage.paginate_query(
                "products",
                relations=["product_families(*)"],
                order_by="created_at.desc",
                page=1,
                per_page=20
            )

        Performance:
            - Cursor pagination is O(1) vs O(N) for large offsets
            - include_count=False skips expensive COUNT(*) query
            - per_page capped at 100 for safety

        Raises:
            StorageError: On query failure
            ValueError: If per_page > 100 or page < 1
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
    # Upsert & Patch Operations (Universal Data Engine - Phase 1.4)
    # ========================================================================

    @abstractmethod
    async def upsert_entity(
        self,
        table: str,
        data: dict[str, Any],
        conflict_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Insert or update entity (upsert) with conflict resolution.

        Universal Data Engine - Phase 1.4: Idempotent write operations.

        Provides PostgreSQL-style upsert semantics:
        - If conflict on unique constraint: UPDATE existing record
        - If no conflict: INSERT new record
        - Returns the final record state (inserted or updated)

        Args:
            table: Table name
            data: Entity data (must include fields for conflict detection)
            conflict_fields: Fields to check for conflicts (e.g., ["sku_code"])
                           If None, uses table's primary key (id)
                           For composite uniqueness, pass multiple fields

        Returns:
            Final entity state after upsert (with all generated fields)

        Examples:
            # Upsert by SKU code (idempotent product creation)
            product = await storage.upsert_entity(
                "products",
                {
                    "sku_code": "SKU-001",
                    "name": "Product A",
                    "base_price": 100.0
                },
                conflict_fields=["sku_code"]
            )

            # Upsert by ID (update if exists, insert if not)
            product = await storage.upsert_entity(
                "products",
                {
                    "id": "uuid-123",
                    "sku_code": "SKU-001",
                    "name": "Updated Product A"
                }
            )

            # Composite uniqueness (tenant + slug)
            category = await storage.upsert_entity(
                "categories",
                {"tenant_id": "t1", "slug": "bottles", "name": "Bottles"},
                conflict_fields=["tenant_id", "slug"]
            )

        Behavior:
            - ON CONFLICT: All fields in data are updated (full replace)
            - created_at preserved on update (if exists)
            - updated_at refreshed on update (if exists)
            - Returns inserted/updated record with generated fields

        Raises:
            StorageError: On upsert failure or constraint violation
            ValueError: If conflict_fields reference non-existent columns

        Notes:
            - Idempotent: multiple calls with same data converge to same state
            - Atomic: operation succeeds or fails completely
            - Safe for concurrent upserts on different conflict_fields
        """
        pass

    @abstractmethod
    async def bulk_upsert(
        self,
        table: str,
        data: list[dict[str, Any]],
        conflict_fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Batch upsert multiple entities with conflict resolution.

        Universal Data Engine - Phase 1.4: Efficient bulk idempotent writes.

        Performs upsert for multiple entities in single query:
        - Dramatically faster than N individual upserts
        - Maintains atomicity (all succeed or all fail)
        - Preserves order of input data in results

        Args:
            table: Table name
            data: List of entity data (each must include conflict_fields)
            conflict_fields: Fields to check for conflicts (e.g., ["sku_code"])
                           If None, uses table's primary key (id)

        Returns:
            List of final entity states after upserts (with generated fields)
            Ordered to match input data

        Examples:
            # Bulk upsert products by SKU
            products = await storage.bulk_upsert(
                "products",
                [
                    {"sku_code": "SKU-001", "name": "Product A", "price": 100},
                    {"sku_code": "SKU-002", "name": "Product B", "price": 200},
                    {"sku_code": "SKU-001", "name": "Product A Updated", "price": 150}
                ],
                conflict_fields=["sku_code"]
            )
            # Returns 2 records: SKU-001 (updated), SKU-002 (inserted)

            # Bulk upsert with composite uniqueness
            variants = await storage.bulk_upsert(
                "product_variants",
                [
                    {"product_id": "p1", "sku": "SKU-A", "size": "M"},
                    {"product_id": "p1", "sku": "SKU-B", "size": "L"}
                ],
                conflict_fields=["product_id", "sku"]
            )

        Performance:
            - Single query for N entities (vs N queries)
            - Efficient even for 100+ entities
            - Respects database constraints and indexes

        Behavior:
            - Maintains same semantics as upsert_entity()
            - Order of results matches order of input data
            - All operations atomic (transaction-based)

        Raises:
            StorageError: On upsert failure or constraint violation
            ValueError: If conflict_fields reference non-existent columns
            ValueError: If data list is empty

        Notes:
            - Idempotent: safe to retry on failure
            - Handles duplicates within data list (last occurrence wins)
            - Generated fields (id, timestamps) populated for all records
        """
        pass

    @abstractmethod
    async def patch_entity(
        self,
        table: str,
        id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Partially update entity (PATCH semantics).

        Universal Data Engine - Phase 1.4: Granular field updates.

        Updates only specified fields, leaving other fields unchanged:
        - More efficient than full entity replacement
        - Reduces risk of data loss from stale reads
        - Supports nested field updates (JSON columns)

        Args:
            table: Table name
            id: Entity ID to update
            updates: Fields to update (partial entity data)
                    Omitted fields are NOT modified

        Returns:
            Complete updated entity (all fields, not just updated ones)

        Examples:
            # Update only price field
            product = await storage.patch_entity(
                "products",
                "uuid-123",
                {"base_price": 150.0}
            )
            # Other fields (name, sku_code, etc.) unchanged

            # Update multiple fields
            product = await storage.patch_entity(
                "products",
                "uuid-123",
                {"base_price": 150.0, "is_active": True}
            )

            # Update nested JSON field (if supported by storage)
            product = await storage.patch_entity(
                "products",
                "uuid-123",
                {"metadata": {"color": "blue"}}  # Merges with existing metadata
            )

        Behavior:
            - Only updates fields present in updates dict
            - updated_at automatically refreshed (if column exists)
            - Returns full entity after update (not just updates)
            - Fails if entity with id doesn't exist

        Raises:
            StorageError: On update failure
            ValueError: If entity with id not found

        Notes:
            - NOT idempotent if updated_at changes on every call
            - For nested updates, behavior depends on storage adapter:
              - JSON columns may support deep merge vs shallow replace
              - See adapter docs for JSON update semantics
            - Use upsert_entity() if you need insert-or-update semantics
        """
        pass

    # ========================================================================
    # Dry-Run & Validation (Universal Data Engine - Phase 1.5)
    # ========================================================================

    @abstractmethod
    async def validate_entity_data(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        operation: Literal["insert", "update", "upsert", "delete"],
    ) -> dict[str, Any]:
        """
        Validate entity data against schema without executing operation.

        Universal Data Engine - Phase 1.5: Pre-flight validation for safe writes.

        Performs comprehensive validation checks:
        - Schema conformance (field types, required fields)
        - Data type validation (strings, numbers, booleans, dates)
        - Field length constraints
        - Enum value validation (if supported by schema)

        Args:
            table: Table name
            data: Entity data (single dict or list of dicts)
            operation: Operation type being validated

        Returns:
            Validation result dict:
            {
                "valid": bool,              # Overall validation status
                "errors": [                 # Critical errors (must fix)
                    {
                        "field": "sku_code",
                        "error": "Field is required but missing",
                        "severity": "error"
                    }
                ],
                "warnings": [               # Non-critical warnings
                    {
                        "field": "price",
                        "warning": "Value seems unusually high",
                        "severity": "warning"
                    }
                ],
                "entity_count": 1,          # Number of entities validated
            }

        Examples:
            # Validate single entity for insert
            result = await storage.validate_entity_data(
                "products",
                {"sku_code": "SKU-001", "name": "Product A"},
                operation="insert"
            )
            if not result["valid"]:
                print(f"Validation errors: {result['errors']}")

            # Validate batch for upsert
            result = await storage.validate_entity_data(
                "products",
                [
                    {"sku_code": "SKU-001", "name": "Product A"},
                    {"sku_code": "SKU-002"},  # Missing name
                ],
                operation="upsert"
            )

        Notes:
            - Does NOT check constraints (use check_constraint_violations)
            - Does NOT execute any writes
            - Schema validation only, not business logic
            - Useful for pre-flight checks before bulk operations

        Raises:
            StorageError: On validation system failure (not data errors)
            ValueError: If table doesn't exist
        """
        pass

    @abstractmethod
    async def check_constraint_violations(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        operation: Literal["insert", "update", "upsert"],
        exclude_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Check for constraint violations before write operation.

        Universal Data Engine - Phase 1.5: Detect conflicts before execution.

        Validates against database constraints:
        - Uniqueness constraints (duplicate detection)
        - Foreign key constraints (referential integrity)
        - Check constraints (value ranges, patterns)

        Args:
            table: Table name
            data: Entity data (single dict or list of dicts)
            operation: Operation type ("insert", "update", "upsert")
            exclude_ids: IDs to exclude from uniqueness check (for updates)

        Returns:
            Constraint check result:
            {
                "safe_to_proceed": bool,    # Can operation proceed safely
                "violations": [             # List of constraint violations
                    {
                        "type": "uniqueness",
                        "field": "sku_code",
                        "value": "SKU-001",
                        "message": "SKU code already exists",
                        "conflicting_id": "uuid-existing"
                    },
                    {
                        "type": "foreign_key",
                        "field": "category_id",
                        "value": "cat-999",
                        "message": "Referenced category does not exist"
                    }
                ],
                "warnings": [               # Non-blocking issues
                    {
                        "type": "performance",
                        "message": "Large batch may be slow"
                    }
                ],
                "checked_constraints": [    # Constraints that were checked
                    "sku_code_unique",
                    "category_id_fkey"
                ]
            }

        Examples:
            # Check uniqueness before insert
            result = await storage.check_constraint_violations(
                "products",
                {"sku_code": "SKU-001", "name": "Product A"},
                operation="insert"
            )
            if not result["safe_to_proceed"]:
                print(f"Violations: {result['violations']}")

            # Check batch with ID exclusion for update
            result = await storage.check_constraint_violations(
                "products",
                {"sku_code": "SKU-001"},  # Updating existing
                operation="update",
                exclude_ids=["uuid-123"]  # Exclude self from uniqueness check
            )

        Performance:
            - Uses indexes for efficient constraint checking
            - Batch operations checked in single query where possible
            - Foreign key checks may query related tables

        Notes:
            - Does NOT validate schema (use validate_entity_data)
            - Does NOT execute any writes
            - safe_to_proceed=True means no violations detected
            - Upsert operations typically skip uniqueness checks

        Raises:
            StorageError: On constraint check failure
            ValueError: If table doesn't exist
        """
        pass

    @abstractmethod
    async def preview_write_impact(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        operation: Literal["update", "delete"] = "update",
        sample_size: int = 5,
    ) -> dict[str, Any]:
        """
        Preview impact of update/delete operation before execution.

        Universal Data Engine - Phase 1.5: Dry-run impact analysis.

        Calculates operation impact without executing:
        - Number of entities affected
        - Sample of entities that would change
        - Estimated execution time
        - Potential risks and warnings

        Args:
            table: Table name
            filters: Filter conditions (same as update/delete filters)
            operation: Operation type ("update" or "delete")
            sample_size: Number of sample entities to return (default: 5)

        Returns:
            Impact preview:
            {
                "affected_count": 150,      # Entities that would be affected
                "sample_entities": [        # Sample of affected entities
                    {"id": "id1", "sku_code": "SKU-001", "name": "Product A"},
                    {"id": "id2", "sku_code": "SKU-002", "name": "Product B"},
                    ...
                ],
                "estimated_duration_ms": 250,  # Estimated operation time
                "warnings": [               # Potential issues
                    {
                        "type": "large_batch",
                        "message": "Operation affects 150+ entities"
                    }
                ],
                "safe_to_proceed": True,    # Recommendation
            }

        Examples:
            # Preview delete impact
            result = await storage.preview_write_impact(
                "products",
                filters={"is_active": False},
                operation="delete"
            )
            print(f"Would delete {result['affected_count']} entities")
            print(f"Sample: {result['sample_entities']}")

            # Preview update impact with no filters (dangerous!)
            result = await storage.preview_write_impact(
                "products",
                filters=None,
                operation="update"
            )
            if not result["safe_to_proceed"]:
                print("WARNING: Would affect ALL entities")

        Warnings Generated:
            - large_batch: >100 entities affected
            - no_filters: Operation affects all entities
            - cascading_deletes: Delete would cascade to related records

        Notes:
            - Does NOT execute any writes
            - Count and samples fetched in single query
            - Duration estimate based on affected_count heuristics
            - Insert operations don't need preview (no existing data affected)

        Raises:
            StorageError: On preview failure
            ValueError: If table doesn't exist or operation not supported
        """
        pass

    # ========================================================================
    # Schema Intelligence (Universal Data Engine - Phase 1.1)
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

        Example:
            stats = await storage.get_table_stats("products")
            # Returns:
            # {
            #     "row_count": 1523,
            #     "estimated_size_bytes": 2458624,
            #     "last_updated": "2025-01-23T10:30:00Z",
            #     "indexes": ["idx_products_sku", "idx_products_category"],
            #     "primary_key": "id"
            # }

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
        Used by inspect_schema tool when agents request sample data.

        Args:
            table: Table name
            filters: Optional filters to narrow samples (e.g., {"is_active": True})
            limit: Maximum rows to return (default: 5, max enforced by implementation)

        Returns:
            List of sample rows as dicts

        Example:
            # Get general samples
            samples = await storage.sample_data("products", limit=3)

            # Get filtered samples
            samples = await storage.sample_data(
                "products",
                filters={"is_active": True, "category": "bottles"},
                limit=5
            )

        Raises:
            StorageError: On query failure or table not found

        Notes:
            - Implementation should enforce reasonable limit (e.g., max 10-20 rows)
            - Should return diverse samples, not just first N rows
            - May use RANDOM() or TABLESAMPLE for better diversity
        """
        pass

    # ========================================================================
    # Transaction Support (Phase 3)
    # ========================================================================

    @abstractmethod
    def transaction(self) -> Any:
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
