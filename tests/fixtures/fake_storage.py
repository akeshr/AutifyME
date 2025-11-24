"""Fake storage implementation for testing.

Implements StorageInterface with in-memory storage for test isolation.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.schemas.models import CompanyProfile, Product, WorkflowOutcome


class FakeStorage(StorageInterface):
    """In-memory storage adapter implementing the port interface.

    Provides clean, testable storage without database dependencies.
    All CRUD operations are async to match production interface.
    """

    def __init__(self):
        """Initialize in-memory tables."""
        # In-memory database tables
        self.tables: dict[str, list[dict[str, Any]]] = {
            "companies": [],
            "product_families": [],
            "variant_axes": [],
            "variant_values": [],
            "products": [],
            "product_variant_values": [],
            "product_family_industries": [],
            "customer_segments": [],
            "product_images": [],
            "marketing_content": [],
        }

        # Track processed messages for idempotency
        self.processed_messages: set[str] = set()

        # Track workflow outcomes
        self.workflow_outcomes: list[dict[str, Any]] = []

    # ========================================================================
    # Legacy Methods (Sync)
    # ========================================================================

    def get_company_profile(self) -> CompanyProfile:
        """Return first company or create default."""
        companies = self.tables.get("companies", [])
        if not companies:
            # Create default company for tests
            default_company = {
                "id": str(uuid.uuid4()),
                "name": "Test Company",
                "brand_voice": "Professional and friendly",
                "target_audience": "B2B SaaS companies",
                "created_at": datetime.now(UTC).isoformat(),
            }
            self.tables["companies"].append(default_company)
            return CompanyProfile.model_validate(default_company)

        return CompanyProfile.model_validate(companies[0])

    def save_product(self, product: Product) -> Product:
        """Save product to in-memory table."""
        product_dict = product.model_dump(mode="json")

        if product.id is None:
            product_dict["id"] = str(uuid.uuid4())
            product_dict["created_at"] = datetime.now(UTC).isoformat()
            self.tables["products"].append(product_dict)
        else:
            # Update existing
            for i, p in enumerate(self.tables["products"]):
                if p.get("id") == str(product.id):
                    self.tables["products"][i] = product_dict
                    break
            else:
                self.tables["products"].append(product_dict)

        return Product.model_validate(product_dict)

    def check_and_mark_message_processed(
        self,
        message_id: str,
        sender_id: str,
        thread_id: str,
        received_at: datetime,
    ) -> bool:
        """Check if message is duplicate."""
        if message_id in self.processed_messages:
            return True  # Duplicate

        self.processed_messages.add(message_id)
        return False  # New message

    def save_workflow_outcome(self, outcome: WorkflowOutcome) -> str:
        """Save workflow outcome to in-memory list."""
        outcome_id = str(uuid.uuid4())
        # Convert Pydantic model to dict for storage
        outcome_dict = outcome.model_dump(mode="json")
        outcome_with_id = {**outcome_dict, "id": outcome_id}
        self.workflow_outcomes.append(outcome_with_id)
        return outcome_id

    def get_workflow_outcomes(
        self,
        *,
        time_window: timedelta | None = None,
        intent: str | None = None,
        department: str | None = None,
        success: bool | None = None,
        limit: int = 100,
    ) -> list[WorkflowOutcome]:
        """Get workflow outcomes with filters."""
        results = self.workflow_outcomes[:]

        # Apply filters (simplified for testing)
        if intent:
            results = [r for r in results if r.get("intent") == intent]
        if department:
            results = [r for r in results if r.get("department") == department]
        if success is not None:
            results = [r for r in results if r.get("success") == success]

        # Convert dicts back to WorkflowOutcome models
        return [WorkflowOutcome.model_validate(r) for r in results[:limit]]

    def get_recent_failures(
        self,
        time_window: timedelta,
        limit: int = 10,
    ) -> list[WorkflowOutcome]:
        """Get recent workflow failures."""
        failures = [o for o in self.workflow_outcomes if not o.get("success", True)]
        # Convert dicts back to WorkflowOutcome models
        return [WorkflowOutcome.model_validate(f) for f in failures[:limit]]

    def get_success_rates(
        self,
        time_window: timedelta | None = None,
    ) -> list[dict[str, Any]]:
        """Get success rate analytics."""
        # Simplified for testing
        return []

    def get_edge_cases(
        self,
        time_window: timedelta | None = None,
        max_occurrence_count: int = 3,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get edge cases for test synthesis."""
        # Simplified for testing
        return []

    # ========================================================================
    # Async CRUD Methods (New Port Interface)
    # ========================================================================

    async def query_entities(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        columns: list[str] | None = None,
        relations: list[str] | None = None,
        search_patterns: dict[str, str] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Query entities with filters, relations, and search patterns."""
        table_data = self.tables.get(table, [])

        # Apply filters and search patterns
        results = []
        for row in table_data:
            # Exact match filters
            if filters:
                match = all(row.get(k) == v for k, v in filters.items())
                if not match:
                    continue

            # ILIKE search patterns (simplified case-insensitive substring match)
            if search_patterns:
                pattern_match = all(
                    pattern.strip("%").lower() in str(row.get(k, "")).lower()
                    for k, pattern in search_patterns.items()
                )
                if not pattern_match:
                    continue

            # Column filtering
            if columns:
                filtered_row = {k: row.get(k) for k in columns}
                results.append(filtered_row)
            else:
                results.append(row.copy())

        # Apply limit
        if limit:
            results = results[:limit]

        return results

    async def count_entities(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        search_patterns: dict[str, str] | None = None,
    ) -> int:
        """Count entities matching filters and search patterns."""
        table_data = self.tables.get(table, [])
        count = 0

        for row in table_data:
            # Exact match filters
            if filters:
                match = all(row.get(k) == v for k, v in filters.items())
                if not match:
                    continue

            # ILIKE search patterns (simplified case-insensitive substring match)
            if search_patterns:
                pattern_match = all(
                    pattern.strip("%").lower() in str(row.get(k, "")).lower()
                    for k, pattern in search_patterns.items()
                )
                if not pattern_match:
                    continue

            count += 1

        return count

    async def check_existing_values(
        self,
        table: str,
        column: str,
        values: list[Any],
        exclude_ids: list[Any] | None = None,
    ) -> list[Any]:
        """Batch check which values exist, optionally excluding specific IDs."""
        table_data = self.tables.get(table, [])
        existing_values = []

        for row in table_data:
            # Skip excluded IDs (for idempotent update validation)
            if exclude_ids and row.get("id") in exclude_ids:
                continue

            value = row.get(column)
            if value in values and value not in existing_values:
                existing_values.append(value)

        return existing_values

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
        """Advanced query with simplified implementation for testing.

        Note: Relations are not fully implemented - just returns base data.
        """
        table_data = self.tables.get(table, [])

        # Apply filters
        results = []
        for row in table_data:
            # Exact match filters
            if filters:
                match = all(row.get(k) == v for k, v in filters.items())
                if not match:
                    continue

            # ILIKE search patterns (simplified case-insensitive substring match)
            if search_patterns:
                pattern_match = all(
                    pattern.strip("%").lower() in str(row.get(k, "")).lower()
                    for k, pattern in search_patterns.items()
                )
                if not pattern_match:
                    continue

            # Column filtering
            if columns:
                filtered_row = {k: row.get(k) for k in columns}
                results.append(filtered_row)
            else:
                results.append(row.copy())

        # Apply limit
        if limit and not count_only:
            results = results[:limit]

        # Return count or rows
        if count_only:
            return len(results)

        return results

    async def insert_entity(
        self,
        table: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Insert single entity."""
        entity = data.copy()

        # Generate ID if missing
        if "id" not in entity:
            entity["id"] = str(uuid.uuid4())

        # Add timestamps
        if "created_at" not in entity:
            entity["created_at"] = datetime.now(UTC).isoformat()
        if "updated_at" not in entity:
            entity["updated_at"] = datetime.now(UTC).isoformat()

        # Add to table
        if table not in self.tables:
            self.tables[table] = []
        self.tables[table].append(entity)

        return entity

    async def insert_entities(
        self,
        table: str,
        data: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Batch insert entities."""
        results = []
        for entity_data in data:
            result = await self.insert_entity(table, entity_data)
            results.append(result)
        return results

    async def update_entities(
        self,
        table: str,
        filters: dict[str, Any],
        updates: dict[str, Any],
    ) -> int:
        """Update entities matching filters."""
        table_data = self.tables.get(table, [])
        count = 0

        for row in table_data:
            match = all(row.get(k) == v for k, v in filters.items())
            if match:
                row.update(updates)
                row["updated_at"] = datetime.now(UTC).isoformat()
                count += 1

        return count

    async def delete_entities(
        self,
        table: str,
        filters: dict[str, Any],
        soft_delete: bool = True,
    ) -> int:
        """Delete entities matching filters."""
        table_data = self.tables.get(table, [])

        if soft_delete:
            # Soft delete: Set is_active=False and deleted_at=now()
            count = 0
            for row in table_data:
                match = all(row.get(k) == v for k, v in filters.items())
                if match:
                    row["is_active"] = False
                    row["deleted_at"] = datetime.now(UTC).isoformat()
                    row["updated_at"] = datetime.now(UTC).isoformat()
                    count += 1
            return count
        else:
            # Hard delete: Remove from storage
            to_remove = []
            for row in table_data:
                match = all(row.get(k) == v for k, v in filters.items())
                if match:
                    to_remove.append(row)

            count = len(to_remove)
            for row in to_remove:
                table_data.remove(row)

            return count

    # ========================================================================
    # Lifecycle Management
    # ========================================================================

    # ========================================================================
    # Transaction Support (Phase 3)
    # ========================================================================

    def transaction(self):
        """
        Create a transaction context manager for atomic operations.

        For in-memory storage, creates a snapshot of tables and rolls back on error.
        """
        return FakeTransaction(self)

    # ========================================================================
    # Lifecycle Management
    # ========================================================================

    def cleanup(self) -> None:
        """Cleanup (no-op for in-memory storage)."""
        pass


class FakeTransaction:
    """Transaction context manager for FakeStorage.

    Creates a snapshot of table state and rolls back on exception.
    """

    def __init__(self, storage: FakeStorage):
        """Initialize transaction with storage reference."""
        self.storage = storage
        self.snapshot: dict[str, list[dict[str, Any]]] | None = None

    async def __aenter__(self):
        """Start transaction - create snapshot of current state."""
        import copy

        # Deep copy all tables to create snapshot
        self.snapshot = {}
        for table_name, table_data in self.storage.tables.items():
            self.snapshot[table_name] = copy.deepcopy(table_data)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """End transaction - rollback on exception, commit on success."""
        if exc_type is not None and self.snapshot is not None:
            # Exception occurred - rollback to snapshot
            self.storage.tables = self.snapshot
            # Don't suppress the exception
            return False

        # Success - commit (no-op for in-memory, changes already applied)
        self.snapshot = None
        return False
