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

    # ========================================================================
    # Pending Message Batching (PendingMessageMixin Implementation)
    # ========================================================================

    async def queue_pending_message(
        self,
        message_id: str,
        sender_id: str,
        thread_id: str,
        message_type: str,
        text_content: str | None,
        media_id: str | None,
        caption: str | None,
        sender_name: str | None,
        received_at: datetime,
    ) -> dict[str, Any]:
        """Queue a message for batch processing."""
        if "pending_messages" not in self.tables:
            self.tables["pending_messages"] = []

        message = {
            "id": str(uuid.uuid4()),
            "message_id": message_id,
            "sender_id": sender_id,
            "thread_id": thread_id,
            "batch_key": sender_id,
            "message_type": message_type,
            "text_content": text_content,
            "media_id": media_id,
            "caption": caption,
            "sender_name": sender_name,
            "received_at": received_at.isoformat() if isinstance(received_at, datetime) else received_at,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.tables["pending_messages"].append(message)
        return message

    async def fetch_and_clear_batch(self, batch_key: str) -> list[dict[str, Any]]:
        """Atomically fetch and delete all pending messages for a sender."""
        if "pending_messages" not in self.tables:
            return []

        # Find all messages for this batch_key
        batch = [
            msg for msg in self.tables["pending_messages"]
            if msg.get("batch_key") == batch_key or msg.get("sender_id") == batch_key
        ]

        # Remove from table
        self.tables["pending_messages"] = [
            msg for msg in self.tables["pending_messages"]
            if msg.get("batch_key") != batch_key and msg.get("sender_id") != batch_key
        ]

        # Sort by created_at
        batch.sort(key=lambda x: x.get("created_at", ""))
        return batch

    async def has_recent_activity(
        self, sender_id: str, window_seconds: int = 5
    ) -> bool:
        """Check if sender has recent activity within time window."""
        if "pending_messages" not in self.tables:
            return False

        cutoff = datetime.now(UTC) - timedelta(seconds=window_seconds)

        for msg in self.tables["pending_messages"]:
            if msg.get("sender_id") == sender_id:
                created_at = msg.get("created_at")
                if created_at:
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    if created_at > cutoff:
                        return True
        return False

    async def has_pending_messages(self, sender_id: str) -> bool:
        """Check if sender has any messages in the buffer."""
        if "pending_messages" not in self.tables:
            return False

        return any(
            msg.get("sender_id") == sender_id
            for msg in self.tables["pending_messages"]
        )

    async def get_orphaned_batches(
        self, age_seconds: int = 33
    ) -> list[dict[str, Any]]:
        """Get pending messages older than expected processing time."""
        if "pending_messages" not in self.tables:
            return []

        cutoff = datetime.now(UTC) - timedelta(seconds=age_seconds)
        orphaned = []

        for msg in self.tables["pending_messages"]:
            created_at = msg.get("created_at")
            if created_at:
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                if created_at < cutoff:
                    orphaned.append(msg)

        return orphaned

    def save_workflow_outcome(self, outcome: WorkflowOutcome) -> str:
        """Save workflow outcome to in-memory list."""
        outcome_id = str(uuid.uuid4())
        # Convert Pydantic model to dict for storage
        outcome_dict = outcome.model_dump(mode="json")
        outcome_with_id = {**outcome_dict, "id": outcome_id}
        self.workflow_outcomes.append(outcome_with_id)
        return outcome_id

    def save_workflow_outcome_dict(self, payload: dict[str, Any]) -> str:
        """Save workflow outcome from dict (bypasses Pydantic model).

        Args:
            payload: Dict matching workflow_outcomes table columns

        Returns:
            Generated outcome ID
        """
        outcome_id = str(uuid.uuid4())
        outcome_with_id = {**payload, "id": outcome_id}
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
            # Automatically filter out soft-deleted entities unless explicitly querying for them
            # Default: only return active entities
            if (not filters or ("is_active" not in filters and "deleted_at" not in filters)) and (
                row.get("is_active") is False or row.get("deleted_at") is not None
            ):
                continue

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
            # Automatically filter out soft-deleted entities unless explicitly querying for them
            # Default: only count active entities
            if (not filters or ("is_active" not in filters and "deleted_at" not in filters)) and (
                row.get("is_active") is False or row.get("deleted_at") is not None
            ):
                continue

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

    async def query_aggregate(
        self,
        table: str,
        aggregates: dict[str, Any],
        filters: dict[str, Any] | None = None,
        search_patterns: dict[str, str] | None = None,
        group_by: list[str] | None = None,
        having: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Query with aggregations - simplified implementation for testing."""
        table_data = self.tables.get(table, [])

        # Filter data
        filtered_data = []
        for row in table_data:
            if filters and not all(row.get(k) == v for k, v in filters.items()):
                continue
            if search_patterns:
                pattern_match = all(
                    pattern.strip("%").lower() in str(row.get(k, "")).lower()
                    for k, pattern in search_patterns.items()
                )
                if not pattern_match:
                    continue
            filtered_data.append(row)

        # Simple aggregation without grouping
        if not group_by:
            result = {}
            for alias, func in aggregates.items():
                if "count(*)" in func or "count" in func:
                    result[alias] = len(filtered_data)
                elif "sum" in func:
                    col = func.split("(")[1].split(")")[0]
                    result[alias] = sum(float(row.get(col, 0)) for row in filtered_data)
                elif "avg" in func:
                    col = func.split("(")[1].split(")")[0]
                    values = [float(row.get(col, 0)) for row in filtered_data if row.get(col) is not None]
                    result[alias] = sum(values) / len(values) if values else 0
                elif "min" in func:
                    col = func.split("(")[1].split(")")[0]
                    values = [row.get(col) for row in filtered_data if row.get(col) is not None]
                    result[alias] = min(values) if values else None
                elif "max" in func:
                    col = func.split("(")[1].split(")")[0]
                    values = [row.get(col) for row in filtered_data if row.get(col) is not None]
                    result[alias] = max(values) if values else None
            return [result]

        # Group by (simplified)
        from collections import defaultdict
        groups = defaultdict(list)
        for row in filtered_data:
            key = tuple(row.get(col) for col in group_by)
            groups[key].append(row)

        results = []
        for group_key, group_rows in groups.items():
            result = dict(zip(group_by, group_key, strict=True))
            for alias, func in aggregates.items():
                if "count" in func:
                    result[alias] = len(group_rows)
                elif "sum" in func:
                    col = func.split("(")[1].split(")")[0]
                    result[alias] = sum(float(row.get(col, 0)) for row in group_rows)
                elif "avg" in func:
                    col = func.split("(")[1].split(")")[0]
                    values = [float(row.get(col, 0)) for row in group_rows if row.get(col) is not None]
                    result[alias] = sum(values) / len(values) if values else 0
            results.append(result)

        return results

    async def batch_read(
        self,
        table: str,
        ids: list[str],
        relations: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch multiple entities by ID."""
        table_data = self.tables.get(table, [])
        results = []

        # Preserve input order
        for entity_id in ids:
            for row in table_data:
                if row.get("id") == entity_id:
                    results.append(row.copy())
                    break

        return results

    async def paginate_query(
        self,
        table: str,
        page: int = 1,
        per_page: int = 20,
        filters: dict[str, Any] | None = None,
        search_patterns: dict[str, str] | None = None,
        ordering: list[dict[str, str]] | None = None,
        include_total_count: bool = False,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Paginate query results."""
        # Get filtered data
        filtered_data = await self.query_entities(
            table, filters=filters, search_patterns=search_patterns
        )

        # Apply ordering (simplified)
        if ordering:
            for order_spec in reversed(ordering):
                col = order_spec.get("column")
                direction = order_spec.get("direction", "asc")
                if col:
                    filtered_data.sort(
                        key=lambda x: x.get(col, ""),
                        reverse=(direction == "desc")
                    )

        # Calculate pagination
        total_count = len(filtered_data) if include_total_count else None
        start = (page - 1) * per_page
        end = start + per_page
        page_data = filtered_data[start:end]

        return {
            "data": page_data,
            "page": page,
            "per_page": per_page,
            "total_count": total_count,
            "has_next": end < len(filtered_data),
            "next_cursor": None,  # Simplified - no cursor support
        }

    async def upsert_entity(
        self,
        table: str,
        data: dict[str, Any],
        conflict_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Insert or update entity based on conflict fields."""
        if not conflict_fields:
            conflict_fields = ["id"]

        table_data = self.tables.get(table, [])

        # Check for existing entity
        for row in table_data:
            if all(row.get(field) == data.get(field) for field in conflict_fields):
                # Update existing
                row.update(data)
                row["updated_at"] = datetime.now(UTC).isoformat()
                return row

        # Insert new
        return await self.insert_entity(table, data)

    async def bulk_upsert(
        self,
        table: str,
        data: list[dict[str, Any]],
        conflict_fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Bulk upsert entities."""
        results = []
        for entity_data in data:
            result = await self.upsert_entity(table, entity_data, conflict_fields)
            results.append(result)
        return results

    async def patch_entity(
        self,
        table: str,
        entity_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Partially update entity."""
        table_data = self.tables.get(table, [])

        for row in table_data:
            if row.get("id") == entity_id:
                row.update(updates)
                row["updated_at"] = datetime.now(UTC).isoformat()
                return row

        raise ValueError(f"Entity {entity_id} not found in {table}")

    async def validate_entity_data(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        operation: str = "insert",
    ) -> dict[str, Any]:
        """Validate entity data against schema."""
        # Simplified validation for testing
        errors = []
        warnings = []

        # Convert single entity to list
        entities = data if isinstance(data, list) else [data]

        # Basic validation: check required fields (simplified)
        required_fields = {
            "products": ["sku_code"],
            "product_families": ["name"],
        }

        for i, entity in enumerate(entities):
            if table in required_fields:
                for field in required_fields[table]:
                    if not entity.get(field):
                        errors.append(f"Entity {i}: Missing required field '{field}'")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    async def check_constraint_violations(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        operation: str = "insert",
        exclude_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Check for constraint violations (uniqueness, etc)."""
        # Simplified constraint checking for testing
        violations = []

        # Convert single entity to list
        entities = data if isinstance(data, list) else [data]

        # Check unique constraints (simplified - just check sku_code for products)
        if table == "products":
            for i, entity in enumerate(entities):
                sku = entity.get("sku_code")
                if sku:
                    existing = await self.query_entities(
                        table, filters={"sku_code": sku}
                    )
                    # Filter out excluded IDs
                    if exclude_ids:
                        existing = [e for e in existing if e.get("id") not in exclude_ids]
                    if existing:
                        violations.append({
                            "entity_index": i,
                            "constraint": "unique_sku_code",
                            "field": "sku_code",
                            "value": sku,
                        })

        return violations

    async def preview_write_impact(
        self,
        operations: list[dict[str, Any]],
        validate: bool = True,
    ) -> dict[str, Any]:
        """Preview impact of write operations without executing."""
        # Simplified preview for testing
        impact = {
            "creates": {},
            "updates": {},
            "deletes": {},
            "validation_errors": [],
            "warnings": [],
            "examples": [],
        }

        for op in operations:
            action = op.get("action")
            table = op.get("table")

            if action == "create":
                impact["creates"][table] = impact["creates"].get(table, 0) + 1
            elif action == "update":
                impact["updates"][table] = impact["updates"].get(table, 0) + 1
            elif action == "delete":
                impact["deletes"][table] = impact["deletes"].get(table, 0) + 1

        return impact

    async def get_table_stats(self, table: str) -> dict[str, Any]:
        """Get statistics about a table."""
        table_data = self.tables.get(table, [])

        return {
            "row_count": len(table_data),
            "columns": list(table_data[0].keys()) if table_data else [],
            "sample_row": table_data[0] if table_data else None,
        }

    async def sample_data(
        self,
        table: str,
        limit: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Get sample data from table."""
        return await self.query_entities(table, filters=filters, limit=limit)

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
    # File Storage (FileStorageMixin Implementation)
    # ========================================================================

    async def upload_asset(
        self,
        file_path: str,
        bucket: str = "assets",
        folder: str = "products",
        content_type: str | None = None,
    ) -> dict[str, Any]:
        """Upload file to in-memory storage.

        Simulates Supabase Storage bucket upload for testing.
        """
        import mimetypes
        from pathlib import Path

        local_path = Path(file_path)
        if not local_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Generate unique storage path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        extension = local_path.suffix.lower()
        storage_filename = f"{timestamp}_{unique_id}{extension}"
        storage_path = f"{folder}/{storage_filename}"

        # Auto-detect content type
        if content_type is None:
            content_type, _ = mimetypes.guess_type(str(local_path))
            content_type = content_type or "application/octet-stream"

        # Read file content
        file_content = local_path.read_bytes()

        # Store in in-memory storage
        if not hasattr(self, "_file_storage"):
            self._file_storage: dict[str, dict[str, Any]] = {}

        bucket_key = f"{bucket}/{storage_path}"
        self._file_storage[bucket_key] = {
            "content": file_content,
            "content_type": content_type,
            "size_bytes": len(file_content),
        }

        # Generate fake public URL
        public_url = f"https://fake-storage.test/{bucket}/{storage_path}"

        return {
            "success": True,
            "storage_path": storage_path,
            "bucket": bucket,
            "public_url": public_url,
            "size_bytes": len(file_content),
            "content_type": content_type,
        }

    async def delete_asset(
        self,
        storage_path: str,
        bucket: str = "assets",
    ) -> bool:
        """Delete file from in-memory storage."""
        if not hasattr(self, "_file_storage"):
            self._file_storage = {}

        bucket_key = f"{bucket}/{storage_path}"
        if bucket_key in self._file_storage:
            del self._file_storage[bucket_key]
            return True
        return True  # Idempotent - return True even if not found

    def get_asset_public_url(
        self,
        storage_path: str,
        bucket: str = "assets",
    ) -> str:
        """Get public URL for stored asset."""
        return f"https://fake-storage.test/{bucket}/{storage_path}"

    async def upload_to_inbox(
        self,
        file_bytes: bytes,
        thread_id: str,
        filename: str,
        content_type: str,
        bucket: str = "assets",
    ) -> dict[str, Any]:
        """Upload user-provided media to inbox folder.

        Simulates immediate persistence of WhatsApp-uploaded images.
        """
        # Sanitize thread_id for folder name
        sanitized_thread_id = thread_id.replace(":", "_")
        storage_path = f"inbox/{sanitized_thread_id}/{filename}"

        # Store in in-memory storage
        if not hasattr(self, "_file_storage"):
            self._file_storage: dict[str, dict[str, Any]] = {}

        bucket_key = f"{bucket}/{storage_path}"
        self._file_storage[bucket_key] = {
            "content": file_bytes,
            "content_type": content_type,
            "size_bytes": len(file_bytes),
        }

        public_url = f"https://fake-storage.test/{bucket}/{storage_path}"

        return {
            "success": True,
            "storage_path": storage_path,
            "bucket": bucket,
            "public_url": public_url,
            "size_bytes": len(file_bytes),
            "content_type": content_type,
        }

    async def upload_to_pending(
        self,
        file_bytes: bytes,
        thread_id: str,
        filename: str,
        content_type: str,
        bucket: str = "assets",
    ) -> dict[str, Any]:
        """Upload AI-generated media to pending folder.

        Simulates staging area for images awaiting HITL approval.
        """
        # Sanitize thread_id for folder name
        sanitized_thread_id = thread_id.replace(":", "_")
        storage_path = f"pending/{sanitized_thread_id}/{filename}"

        # Store in in-memory storage
        if not hasattr(self, "_file_storage"):
            self._file_storage = {}

        bucket_key = f"{bucket}/{storage_path}"
        self._file_storage[bucket_key] = {
            "content": file_bytes,
            "content_type": content_type,
            "size_bytes": len(file_bytes),
        }

        public_url = f"https://fake-storage.test/{bucket}/{storage_path}"

        return {
            "success": True,
            "storage_path": storage_path,
            "bucket": bucket,
            "public_url": public_url,
            "size_bytes": len(file_bytes),
            "content_type": content_type,
        }

    async def move_asset(
        self,
        source_path: str,
        target_folder: str,
        bucket: str = "assets",
    ) -> dict[str, Any]:
        """Move asset from one folder to another.

        Simulates moving from pending/ to products/ on approval.
        """
        import mimetypes
        from pathlib import Path

        if not hasattr(self, "_file_storage"):
            self._file_storage = {}

        source_key = f"{bucket}/{source_path}"

        # Check source exists
        if source_key not in self._file_storage:
            raise FileNotFoundError(f"Source file not found: {source_path}")

        # Get source data
        source_data = self._file_storage[source_key]

        # Generate new filename in target folder
        source_filename = Path(source_path).name
        extension = Path(source_filename).suffix.lower()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        new_filename = f"{timestamp}_{unique_id}{extension}"
        target_path = f"{target_folder}/{new_filename}"

        # Detect content type
        content_type = source_data.get("content_type")
        if not content_type:
            content_type, _ = mimetypes.guess_type(source_filename)
            content_type = content_type or "application/octet-stream"

        # Move to target
        target_key = f"{bucket}/{target_path}"
        self._file_storage[target_key] = source_data.copy()

        # Delete source
        del self._file_storage[source_key]

        public_url = f"https://fake-storage.test/{bucket}/{target_path}"

        return {
            "success": True,
            "storage_path": target_path,
            "bucket": bucket,
            "public_url": public_url,
            "size_bytes": source_data["size_bytes"],
            "content_type": content_type,
        }

    async def list_storage_files(
        self,
        folder: str,
        thread_id: str | None = None,
        bucket: str = "assets",
        limit: int = 50,
        offset: int = 0,
        extension_filter: list[str] | None = None,
        prefix_filter: str | None = None,
    ) -> dict[str, Any]:
        """List files in a storage folder.

        Simulates Supabase Storage list() for testing.
        """
        if not hasattr(self, "_file_storage"):
            self._file_storage = {}

        # Build folder path - thread-scoped for inbox/pending
        if folder in ("inbox", "pending"):
            if not thread_id:
                raise ValueError(f"thread_id required for {folder}/ folder")
            sanitized_thread_id = thread_id.replace(":", "_")
            folder_path = f"{folder}/{sanitized_thread_id}"
        else:
            folder_path = folder

        # Find matching files
        bucket_prefix = f"{bucket}/{folder_path}/"
        all_files = []

        for key, data in self._file_storage.items():
            if key.startswith(bucket_prefix):
                # Extract filename from full path
                relative_path = key[len(f"{bucket}/"):]
                filename = relative_path.split("/")[-1]

                file_info = {
                    "name": filename,
                    "storage_path": relative_path,
                    "public_url": f"https://fake-storage.test/{key}",
                    "size_bytes": data.get("size_bytes", 0),
                    "content_type": data.get("content_type", "application/octet-stream"),
                }
                all_files.append(file_info)

        # Apply extension filter
        if extension_filter:
            normalized_exts = [ext.lower().lstrip(".") for ext in extension_filter]
            all_files = [
                f for f in all_files
                if any(f["name"].lower().endswith(f".{ext}") for ext in normalized_exts)
            ]

        # Apply prefix filter
        if prefix_filter:
            all_files = [f for f in all_files if f["name"].startswith(prefix_filter)]

        # Calculate total before pagination
        total_count = len(all_files)

        # Apply offset and limit
        paginated_files = all_files[offset:offset + limit]

        # Add user_path for convenience
        for file_info in paginated_files:
            storage_path = file_info["storage_path"]
            parts = storage_path.split("/")
            if len(parts) >= 3 and parts[0] in ("inbox", "pending"):
                file_info["user_path"] = f"{parts[0]}/{parts[-1]}"
            else:
                file_info["user_path"] = storage_path

        return {
            "success": True,
            "folder": folder_path,
            "files": paginated_files,
            "count": len(paginated_files),
            "total": total_count,
            "has_more": (offset + limit) < total_count,
        }

    # ========================================================================
    # Atomic Write Intent RPC (LifecycleMixin Implementation)
    # ========================================================================

    async def execute_write_intent_rpc(
        self,
        operations: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute multi-operation write intent atomically.

        In-memory implementation with snapshot-based rollback.
        Supports @reference resolution between operations.
        """
        import copy
        import re

        # Create snapshot for rollback
        snapshot = {
            table_name: copy.deepcopy(table_data)
            for table_name, table_data in self.tables.items()
        }

        # Initialize context for @references
        ctx = dict(context) if context else {}
        results: list[dict[str, Any]] = []

        def resolve_references(value: Any) -> Any:
            """Recursively resolve @reference.field patterns."""
            if isinstance(value, str) and value.startswith("@"):
                # Parse @name.field or @batch[index].field
                match = re.match(r"@(\w+)(?:\[(\d+)\])?\.(\w+)", value)
                if match:
                    name, idx, field = match.groups()
                    if name in ctx:
                        ref_data = ctx[name]
                        if idx is not None:
                            ref_data = ref_data[int(idx)]
                        return ref_data.get(field)
                return value
            elif isinstance(value, dict):
                return {k: resolve_references(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_references(v) for v in value]
            return value

        try:
            for _i, op in enumerate(operations):
                action = op.get("action")
                table = op.get("table")
                returns = op.get("returns")

                if action == "create":
                    data = resolve_references(op.get("data", {}))
                    # Handle both single entity and batch inserts
                    if isinstance(data, list):
                        entities = await self.insert_entities(table, data)
                        result = {"action": action, "table": table, "data": entities, "count": len(entities)}
                        results.append(result)
                        if returns:
                            ctx[returns] = entities
                    else:
                        entity = await self.insert_entity(table, data)
                        result = {"action": action, "table": table, "data": entity, "count": 1}
                        results.append(result)
                        if returns:
                            ctx[returns] = entity

                elif action == "update":
                    filters = resolve_references(op.get("filters", {}))
                    updates = resolve_references(op.get("updates", {}))
                    count = await self.update_entities(table, filters, updates)
                    result = {"action": action, "table": table, "count": count}
                    results.append(result)
                    if returns:
                        ctx[returns] = {"updated_count": count}

                elif action == "delete":
                    filters = resolve_references(op.get("filters", {}))
                    soft_delete = op.get("soft_delete", True)
                    count = await self.delete_entities(table, filters, soft_delete=soft_delete)
                    result = {"action": action, "table": table, "count": count}
                    results.append(result)
                    if returns:
                        ctx[returns] = {"deleted_count": count}

                elif action == "upsert":
                    data = resolve_references(op.get("data", {}))
                    conflict_fields = op.get("conflict_fields")
                    entity = await self.upsert_entity(table, data, conflict_fields)
                    # Format result to match RPC response format
                    result = {"action": action, "table": table, "data": entity, "count": 1}
                    results.append(result)
                    if returns:
                        ctx[returns] = entity

                else:
                    raise ValueError(f"Unknown action: {action}")

            return {
                "success": True,
                "results": results,
                "context": ctx,
                "operations_executed": len(operations),
            }

        except Exception as e:
            # Rollback to snapshot
            self.tables = snapshot
            return {
                "success": False,
                "error": str(e),
                "error_code": "execution_error",
                "failed_operation_index": i,
                "failed_operation": op,
            }

    # ========================================================================
    # Lifecycle Management
    # ========================================================================

    def cleanup(self) -> None:
        """Cleanup (no-op for in-memory storage)."""
        pass

    async def cleanup_subagent_checkpoints(self, thread_id: str) -> dict[str, int]:
        """Delete subagent checkpoints for a thread (no-op for in-memory storage).

        FakeStorage doesn't persist checkpoints, so this is a no-op that returns zeros.
        """
        return {
            "deleted_checkpoints": 0,
            "deleted_blobs": 0,
            "deleted_writes": 0,
        }


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
