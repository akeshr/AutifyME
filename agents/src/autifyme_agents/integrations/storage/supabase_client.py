"""Supabase-backed implementation of the storage port."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from supabase import AsyncClient, Client, create_async_client, create_client
from supabase.lib.client_options import AsyncClientOptions, SyncClientOptions

from autifyme_agents.core.config import settings
from autifyme_agents.core.exceptions import ConfigurationError, StorageError
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.schemas.models import CompanyProfile, Product

logger = logging.getLogger(__name__)


class SupabaseStorageClient(StorageInterface):
    """Concrete adapter that persists and retrieves catalog data via Supabase.

    The class adheres to the `StorageInterface` contract so the rest of the
    application depends on a stable port rather than Supabase specifics. A
    single instance should be reused within a workflow run to avoid creating
    redundant network clients.

    Supports context manager protocol for automatic resource cleanup:
        with SupabaseStorageClient() as storage:
            storage.save_product(product)
        # HTTP connections automatically closed
    """

    def __init__(
        self,
        *,
        supabase_url: str | None = None,
        service_key: str | None = None,
        client: Client | None = None,
    ) -> None:
        """Configure the adapter with explicit or settings-derived credentials."""

        self._supabase_url = supabase_url or settings.SUPABASE_URL
        derived_key = service_key or settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
        if settings.SUPABASE_SERVICE_ROLE_KEY is None and service_key is None:
            logger.warning(
                "SUPABASE_SERVICE_ROLE_KEY not set; falling back to anon key which has restricted write access."
            )
        self._service_key = derived_key
        self._client: Client | None = client
        self._async_client: AsyncClient | None = None  # Async client for non-blocking ops
        self._async_client_loop: asyncio.AbstractEventLoop | None = None  # Track which loop owns client
        self._current_transaction: SupabaseTransaction | None = None  # Track active transaction

    def __enter__(self) -> SupabaseStorageClient:
        """Enter context manager - ensures client is initialized.

        Returns:
            Self for context manager protocol
        """
        self._ensure_client()
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        """Exit context manager - performs automatic cleanup.

        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred
        """
        self.cleanup()

    def _ensure_client(self) -> Client:
        """Create and validate the Supabase client lazily.

        Validates credentials and tests connection on first initialization
        to catch configuration issues early rather than on first query.

        Returns:
            Initialized and validated Supabase client

        Raises:
            ConfigurationError: If credentials are missing or invalid
            ConfigurationError: If connection test fails
        """
        if self._client is None:
            # Validate credentials before attempting connection
            if not self._supabase_url:
                raise ConfigurationError(
                    "SUPABASE_URL not configured. Set environment variable or pass to constructor.",
                    config_key="SUPABASE_URL"
                )

            if not self._service_key:
                raise ConfigurationError(
                    "Neither SUPABASE_SERVICE_ROLE_KEY nor SUPABASE_ANON_KEY configured. "
                    "Set at least one environment variable.",
                    config_key="SUPABASE_SERVICE_ROLE_KEY"
                )

            try:
                # Configure HTTP client to use HTTP/1.1 instead of HTTP/2
                # This prevents "ConnectionTerminated" errors from stale HTTP/2 connections
                http_client = httpx.Client(
                    http2=False,  # Disable HTTP/2 to avoid connection multiplexing issues
                    limits=httpx.Limits(
                        max_keepalive_connections=5,  # Limit keep-alive connections
                        max_connections=10,
                    ),
                    timeout=httpx.Timeout(120.0, connect=10.0),  # Explicit timeouts
                )

                # Create client with custom HTTP configuration
                options = SyncClientOptions(
                    httpx_client=http_client,
                    postgrest_client_timeout=120,
                )
                self._client = create_client(self._supabase_url, self._service_key, options=options)

                # Test connection with simple query to validate credentials
                # Use companies table as it's fundamental to single-tenant architecture
                _ = self._client.table("companies").select("id").limit(1).execute()

                # If we get here, connection is valid (even if no data exists yet)
                logger.info(
                    "Supabase client initialized and connection validated",
                    extra={
                        "url": self._supabase_url[:30] + "...",  # Log partial URL for security
                        "has_service_key": bool(self._service_key),
                        "http_version": "HTTP/1.1",  # Log protocol version
                    }
                )

            except Exception as e:
                logger.error(
                    "Failed to initialize or validate Supabase client",
                    exc_info=True,
                    extra={
                        "url": self._supabase_url[:30] + "..." if self._supabase_url else None,
                        "error_type": type(e).__name__,
                        "error_msg": str(e),
                    }
                )
                raise ConfigurationError(
                    f"Cannot connect to Supabase or validate credentials: {str(e)}",
                    config_key="SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY"
                ) from e

        return self._client

    async def _ensure_async_client(self) -> AsyncClient:
        """Create and validate the async Supabase client lazily.

        Async client enables non-blocking I/O for CRUD operations in LangGraph workflows.
        Uses same credentials as sync client but with async/await semantics.

        Event Loop Awareness:
        Detects when running in a different event loop (e.g., Lambda container reuse)
        and automatically recreates the client to prevent "Event loop is closed" errors.

        Returns:
            Initialized and validated async Supabase client

        Raises:
            ConfigurationError: If credentials are missing or invalid
        """
        # Get current event loop
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop - this shouldn't happen in async context
            current_loop = None

        # Check if client exists AND was created in current loop
        needs_new_client = (
            self._async_client is None
            or self._async_client_loop is None
            or self._async_client_loop != current_loop
        )

        if needs_new_client:
            # Cleanup old client if exists (from different loop)
            if self._async_client is not None:
                logger.debug(
                    "Event loop changed - cleaning up old async client",
                    extra={
                        "old_loop": id(self._async_client_loop) if self._async_client_loop else None,
                        "new_loop": id(current_loop) if current_loop else None
                    }
                )
                # Safe cleanup: just nullify, let GC handle httpx connections
                # (avoid calling aclose() on closed loop)
                self._async_client = None
                self._async_client_loop = None
            # Validate credentials (same validation as sync client)
            if not self._supabase_url:
                raise ConfigurationError(
                    "SUPABASE_URL not configured. Set environment variable or pass to constructor.",
                    config_key="SUPABASE_URL"
                )

            if not self._service_key:
                raise ConfigurationError(
                    "Neither SUPABASE_SERVICE_ROLE_KEY nor SUPABASE_ANON_KEY configured. "
                    "Set at least one environment variable.",
                    config_key="SUPABASE_SERVICE_ROLE_KEY"
                )

            try:
                # Configure async HTTP client with same settings as sync
                async_http_client = httpx.AsyncClient(
                    http2=False,  # Disable HTTP/2 for consistency
                    limits=httpx.Limits(
                        max_keepalive_connections=5,
                        max_connections=10,
                    ),
                    timeout=httpx.Timeout(120.0, connect=10.0),
                )

                # Create async client with custom HTTP configuration
                options = AsyncClientOptions(
                    httpx_client=async_http_client,
                    postgrest_client_timeout=120,
                )
                self._async_client = await create_async_client(
                    self._supabase_url, self._service_key, options=options
                )

                # Store which loop owns this client
                self._async_client_loop = current_loop

                # Test connection with simple query
                _ = await self._async_client.table("companies").select("id").limit(1).execute()

                logger.info(
                    "Async Supabase client initialized and connection validated",
                    extra={
                        "url": self._supabase_url[:30] + "...",
                        "has_service_key": bool(self._service_key),
                        "http_version": "HTTP/1.1",
                        "event_loop_id": id(current_loop) if current_loop else None,
                    }
                )

            except Exception as e:
                logger.error(
                    "Failed to initialize or validate async Supabase client",
                    exc_info=True,
                    extra={
                        "url": self._supabase_url[:30] + "..." if self._supabase_url else None,
                        "error_type": type(e).__name__,
                        "error_msg": str(e),
                    }
                )
                raise ConfigurationError(
                    f"Cannot connect to Supabase async client or validate credentials: {str(e)}",
                    config_key="SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY"
                ) from e

        return self._async_client

    def get_company_profile(self) -> CompanyProfile:
        """Return the single-tenant company profile from storage."""

        client = self._ensure_client()
        response = client.table("companies").select("*").limit(1).single().execute()

        if not response.data:
            raise ValueError(
                "No company profile found in storage. Populate the `companies` table before running workflows."
            )

        return CompanyProfile.model_validate(response.data)

    def save_product(self, product: Product) -> Product:
        """Persist a product record using insert for new products or update for existing."""

        client = self._ensure_client()
        product_payload = product.model_dump(mode="json")

        # For new products (no ID), use insert and let database generate UUID
        # For existing products (with ID), use upsert for idempotency
        if product.id is None:
            # Remove None id from payload - database will generate it
            product_payload.pop("id", None)
            response = client.table("products").insert(product_payload).execute()
        else:
            # Existing product - use upsert for idempotency
            response = client.table("products").upsert(product_payload).execute()

        if not response.data:
            raise RuntimeError("Storage adapter failed to persist product; inspect Supabase response for details.")

        return Product.model_validate(response.data[0])

    # NOTE: Pending approval methods removed - unused in production code
    # Architecture uses LangGraph checkpoints for HITL state persistence.
    # Removed: save_pending_approval(), get_pending_approval(), delete_pending_approval()
    # If restart recovery is needed, implement via checkpoint restoration.

    # ========================================================================
    # Webhook Idempotency (Duplicate Message Detection)
    # ========================================================================

    def check_and_mark_message_processed(
        self,
        message_id: str,
        sender_id: str,
        thread_id: str,
        received_at: datetime,
    ) -> bool:
        """Atomically check if message is duplicate AND mark as processed.

        Uses PostgreSQL stored procedure for atomic INSERT ON CONFLICT to prevent
        race conditions. Fail-closed strategy: if DB check fails, raise error to
        prevent duplicate processing and signal system issues.

        Args:
            message_id: WhatsApp message ID (unique across retries)
            sender_id: Phone number
            thread_id: LangGraph thread ID
            received_at: When webhook was received

        Returns:
            True if duplicate (already processed), False if new (now marked as processed)

        Raises:
            StorageError: If idempotency check fails (database unavailable, query error)
        """
        try:
            client = self._ensure_client()
            result = client.rpc("check_and_mark_processed", {
                "p_message_id": message_id,
                "p_sender_id": sender_id,
                "p_thread_id": thread_id,
                "p_received_at": received_at.isoformat(),
            }).execute()

            result_data: dict[str, Any] = result.data
            is_duplicate: bool = result_data.get("is_duplicate", False)

            if is_duplicate:
                logger.info(
                    "Duplicate message detected (DB idempotency)",
                    extra={
                        "message_id": message_id,
                        "sender_id": sender_id,
                        "thread_id": thread_id,
                    },
                )
            else:
                logger.debug(
                    "New message marked as processed",
                    extra={"message_id": message_id},
                )

            return is_duplicate

        except Exception as exc:
            # Fail CLOSED (raise error) to prevent duplicate processing
            # This signals that the system cannot safely verify message uniqueness
            logger.error(
                "CRITICAL: Idempotency check failed - cannot verify message uniqueness",
                exc_info=True,
                extra={
                    "message_id": message_id,
                    "sender_id": sender_id,
                    "thread_id": thread_id,
                    "error_type": type(exc).__name__,
                    "error_msg": str(exc),
                },
            )
            # Raise StorageError to prevent processing (fail-closed)
            # Webhook will return error; WhatsApp will retry later when DB is healthy
            raise StorageError(
                message=f"Cannot verify message idempotency: {str(exc)}",
                operation="check_and_mark_processed",
                original_error=exc,
            ) from exc

    # ========================================================================
    # Phase 1.2: Workflow Outcome Tracking (Agentic Evolution)
    # ========================================================================

    def save_workflow_outcome(self, outcome: dict[str, Any]) -> str:
        """Persist workflow outcome for learning and analytics.

        Args:
            outcome: Workflow outcome payload with required fields:
                - tracking_id, thread_id, sender_id (required)
                - message_hash, success, started_at (required)
                - trace_id, intent, department (optional)

        Returns:
            Outcome ID from database

        Raises:
            ValueError: If required fields are missing
            RuntimeError: If database insertion fails
        """
        client = self._ensure_client()

        # Validate required fields before attempting insert
        required_fields = ["tracking_id", "thread_id", "sender_id", "message_hash", "success", "started_at"]
        missing_fields = [field for field in required_fields if field not in outcome or outcome[field] is None]

        if missing_fields:
            error_msg = f"Cannot persist workflow outcome - missing required fields: {missing_fields}"
            logger.error(
                error_msg,
                extra={
                    "missing_fields": missing_fields,
                    "tracking_id": outcome.get("tracking_id"),
                    "thread_id": outcome.get("thread_id"),
                }
            )
            raise ValueError(error_msg)

        # Ensure timestamps are ISO strings for Supabase
        payload = outcome.copy()
        for ts_field in ["received_at", "routed_at", "started_at", "ended_at"]:
            if ts_field in payload and isinstance(payload[ts_field], datetime):
                payload[ts_field] = payload[ts_field].isoformat()

        try:
            response = client.table("workflow_outcomes").insert(payload).execute()

            if not response.data or len(response.data) == 0:
                raise RuntimeError(
                    "Supabase returned empty response for workflow outcome insert. "
                    "Check table schema and permissions."
                )

            logger.info(
                "Persisted workflow outcome",
                extra={
                    "tracking_id": outcome.get("tracking_id"),
                    "success": outcome.get("success"),
                    "intent": outcome.get("intent"),
                    "department": outcome.get("department"),
                },
            )

            outcome_id: str = response.data[0]["id"]
            return outcome_id

        except Exception as e:
            logger.error(
                "Failed to persist workflow outcome to database",
                extra={
                    "tracking_id": outcome.get("tracking_id"),
                    "thread_id": outcome.get("thread_id"),
                    "error_type": type(e).__name__,
                    "error_msg": str(e),
                    "payload_keys": list(payload.keys()),
                },
                exc_info=True
            )
            raise

    def get_workflow_outcomes(
        self,
        *,
        time_window: timedelta | None = None,
        intent: str | None = None,
        department: str | None = None,
        success: bool | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Retrieve workflow outcomes for analysis."""
        client = self._ensure_client()

        query = client.table("workflow_outcomes").select("*")

        # Apply filters
        if time_window:
            cutoff = (datetime.now(UTC) - time_window).isoformat()
            query = query.gte("created_at", cutoff)

        if intent:
            query = query.eq("intent", intent)

        if department:
            query = query.eq("department", department)

        if success is not None:
            query = query.eq("success", success)

        # Order and limit
        query = query.order("created_at", desc=True).limit(limit)

        response = query.execute()
        return response.data if response.data else []

    def get_recent_failures(
        self,
        time_window: timedelta,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Retrieve recent failures for regression test generation."""
        client = self._ensure_client()

        cutoff = (datetime.now(UTC) - time_window).isoformat()

        response = (
            client.table("workflow_outcomes")
            .select("tracking_id, thread_id, message_text, media_id, media_type, "
                    "error_type, error_message, resolution_strategy, duration_seconds, created_at")
            .eq("success", False)
            .gte("created_at", cutoff)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return response.data if response.data else []

    def get_success_rates(
        self,
        time_window: timedelta | None = None,
    ) -> list[dict[str, Any]]:
        """Get success rate analytics by department and intent."""
        client = self._ensure_client()

        # Use the pre-built view
        # Note: View filters by 7 days by default; we'll use the view as-is for Phase 1
        # TODO: Make view parameterizable in Phase 2

        response = (
            client.table("v_success_rates")
            .select("*")
            .execute()
        )

        return response.data if response.data else []

    def get_edge_cases(
        self,
        time_window: timedelta | None = None,
        max_occurrence_count: int = 3,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get low-frequency patterns (edge cases) for test synthesis."""
        client = self._ensure_client()

        # Use the pre-built view
        # Note: View uses 30-day window and occurrence_count <= 3 by default
        # TODO: Make view parameterizable in Phase 2

        response = (
            client.table("v_edge_cases")
            .select("*")
            .limit(limit)
            .execute()
        )

        return response.data if response.data else []

    # ========================================================================
    # Generic CRUD Operations (Async Port Implementation)
    # ========================================================================

    async def query_entities(
        self,
        table: str,
        filters: dict[str, Any],
        columns: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Query entities with filters using async client.

        Args:
            table: Table name
            filters: WHERE conditions as dict
            columns: Columns to select (default: all)

        Returns:
            List of matching rows

        Raises:
            StorageError: On query failure
        """
        try:
            client = await self._ensure_async_client()

            # Build select clause
            select_clause = ",".join(columns) if columns else "*"
            query = client.table(table).select(select_clause)

            # Apply filters (support both simple and operator-based)
            for key, value in filters.items():
                if isinstance(value, dict):
                    # Advanced filter with operator: {"in": [...], "gt": ..., etc.}
                    for operator, operand in value.items():
                        if operator == "in":
                            query = query.in_(key, operand)
                        elif operator == "eq":
                            query = query.eq(key, operand)
                        elif operator == "neq":
                            query = query.neq(key, operand)
                        elif operator == "gt":
                            query = query.gt(key, operand)
                        elif operator == "gte":
                            query = query.gte(key, operand)
                        elif operator == "lt":
                            query = query.lt(key, operand)
                        elif operator == "lte":
                            query = query.lte(key, operand)
                        elif operator == "like":
                            query = query.like(key, operand)
                        elif operator == "ilike":
                            query = query.ilike(key, operand)
                        else:
                            raise ValueError(f"Unsupported filter operator: {operator}")
                else:
                    # Simple equality filter
                    query = query.eq(key, value)

            response = await query.execute()
            return response.data if response.data else []

        except Exception as e:
            logger.error(
                f"Failed to query {table}",
                exc_info=True,
                extra={"table": table, "filters": filters}
            )
            raise StorageError(
                message=f"Query failed for {table}: {str(e)}",
                operation="query_entities",
                original_error=e,
            ) from e

    async def check_existing_values(
        self,
        table: str,
        column: str,
        values: list[Any],
        exclude_ids: list[Any] | None = None,
    ) -> list[Any]:
        """Batch check which values exist in column.

        Args:
            table: Table name
            column: Column to check
            values: Values to check for existence
            exclude_ids: Optional list of record IDs to exclude from check
                        (enables idempotent update validation)

        Returns:
            List of values that exist

        Raises:
            StorageError: On query failure
        """
        if not values:
            return []

        try:
            client = await self._ensure_async_client()

            # Use PostgREST's 'in' operator for batch check
            query = client.table(table).select(column).in_(column, values)

            # Exclude specific IDs from check (for update validation)
            if exclude_ids:
                query = query.not_.in_("id", exclude_ids)

            response = await query.execute()

            if not response.data:
                return []

            # Extract the column values from response
            existing = [row[column] for row in response.data if column in row]
            return existing

        except Exception as e:
            logger.error(
                f"Failed to check existing values in {table}.{column}",
                exc_info=True,
                extra={"table": table, "column": column, "value_count": len(values)}
            )
            raise StorageError(
                message=f"Existence check failed for {table}.{column}: {str(e)}",
                operation="check_existing_values",
                original_error=e,
            ) from e

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
        """Advanced query with relations, pattern matching, and counting.

        Args:
            table: Table name
            filters: Exact match filters
            columns: Columns to select
            relations: Related tables using PostgREST syntax
            search_patterns: ILIKE patterns for search
            count_only: Return count instead of rows
            limit: Maximum rows to return

        Returns:
            List of rows or count

        Raises:
            StorageError: On query failure
        """
        try:
            client = await self._ensure_async_client()

            # Build select clause with relations
            if count_only:
                select_clause = "*"  # Count needs at least one column
            elif columns and not relations:
                select_clause = ",".join(columns)
            elif relations:
                # Include columns and relations
                base_cols = ",".join(columns) if columns else "*"
                relation_clauses = [f"{rel}" for rel in relations]
                select_clause = f"{base_cols},{','.join(relation_clauses)}"
            else:
                select_clause = "*"

            query = client.table(table).select(
                select_clause,
                count="exact" if count_only else None
            )

            # Apply exact match filters
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)

            # Apply ILIKE search patterns
            if search_patterns:
                for key, pattern in search_patterns.items():
                    query = query.ilike(key, pattern)

            # Apply limit
            if limit:
                query = query.limit(limit)

            response = await query.execute()

            # Return count or rows
            if count_only:
                return response.count if response.count is not None else 0

            return response.data if response.data else []

        except Exception as e:
            logger.error(
                f"Advanced query failed for {table}",
                exc_info=True,
                extra={
                    "table": table,
                    "filters": filters,
                    "search_patterns": search_patterns,
                }
            )
            raise StorageError(
                message=f"Advanced query failed for {table}: {str(e)}",
                operation="query_advanced",
                original_error=e,
            ) from e

    async def insert_entity(
        self,
        table: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Insert single entity using async client.

        Args:
            table: Table name
            data: Entity data

        Returns:
            Inserted row with generated fields

        Raises:
            StorageError: On insert failure
        """
        try:
            client = await self._ensure_async_client()
            response = await client.table(table).insert(data).execute()

            if not response.data or len(response.data) == 0:
                raise StorageError(
                    message=f"Insert to {table} returned no data",
                    operation="insert_entity",
                )

            inserted = response.data[0]

            # Track operation for transaction rollback
            if self._current_transaction is not None:
                self._current_transaction.operations.append({
                    "type": "insert",
                    "table": table,
                    "ids": [inserted.get("id")],
                })

            return inserted

        except Exception as e:
            logger.error(
                f"Failed to insert into {table}",
                exc_info=True,
                extra={"table": table, "data_keys": list(data.keys())}
            )
            raise StorageError(
                message=f"Insert failed for {table}: {str(e)}",
                operation="insert_entity",
                original_error=e,
            ) from e

    async def insert_entities(
        self,
        table: str,
        data: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Batch insert multiple entities in single query.

        Args:
            table: Table name
            data: List of entity data

        Returns:
            List of inserted rows

        Raises:
            StorageError: On insert failure
        """
        if not data:
            return []

        try:
            client = await self._ensure_async_client()
            response = await client.table(table).insert(data).execute()

            if not response.data:
                raise StorageError(
                    message=f"Batch insert to {table} returned no data",
                    operation="insert_entities",
                )

            inserted = response.data

            # Track operation for transaction rollback
            if self._current_transaction is not None:
                entity_ids = [entity.get("id") for entity in inserted if entity.get("id")]
                if entity_ids:
                    self._current_transaction.operations.append({
                        "type": "insert",
                        "table": table,
                        "ids": entity_ids,
                    })

            return inserted

        except Exception as e:
            logger.error(
                f"Failed to batch insert into {table}",
                exc_info=True,
                extra={"table": table, "entity_count": len(data)}
            )
            raise StorageError(
                message=f"Batch insert failed for {table}: {str(e)}",
                operation="insert_entities",
                original_error=e,
            ) from e

    async def update_entities(
        self,
        table: str,
        filters: dict[str, Any],
        updates: dict[str, Any],
    ) -> int:
        """Update entities matching filters.

        Args:
            table: Table name
            filters: WHERE conditions (supports nested dict for operators)
            updates: Fields to update

        Returns:
            Count of updated rows

        Raises:
            StorageError: On update failure
        """
        try:
            client = await self._ensure_async_client()
            query = client.table(table).update(updates)

            # Apply filters with operator support
            for key, value in filters.items():
                if isinstance(value, dict):
                    # Handle operator syntax
                    for operator, operand in value.items():
                        if operator == "in":
                            query = query.in_(key, operand)
                        elif operator == "eq":
                            query = query.eq(key, operand)
                        elif operator == "neq":
                            query = query.neq(key, operand)
                        elif operator == "gt":
                            query = query.gt(key, operand)
                        elif operator == "gte":
                            query = query.gte(key, operand)
                        elif operator == "lt":
                            query = query.lt(key, operand)
                        elif operator == "lte":
                            query = query.lte(key, operand)
                        else:
                            logger.warning(f"Unsupported operator '{operator}' in filter")
                else:
                    # Simple equality filter
                    query = query.eq(key, value)

            response = await query.execute()
            count = len(response.data) if response.data else 0

            # Track operation for transaction (limited rollback capability)
            if self._current_transaction is not None:
                self._current_transaction.operations.append({
                    "type": "update",
                    "table": table,
                    "filters": filters,
                    "count": count,
                })

            return count

        except Exception as e:
            logger.error(
                f"Failed to update {table}",
                exc_info=True,
                extra={"table": table, "filters": filters, "updates": updates}
            )
            raise StorageError(
                message=f"Update failed for {table}: {str(e)}",
                operation="update_entities",
                original_error=e,
            ) from e

    async def delete_entities(
        self,
        table: str,
        filters: dict[str, Any],
    ) -> int:
        """Delete entities matching filters.

        Args:
            table: Table name
            filters: WHERE conditions (supports nested dict for operators like {"id": {"in": [1,2,3]}})

        Returns:
            Count of deleted rows

        Raises:
            StorageError: On delete failure
        """
        try:
            client = await self._ensure_async_client()
            query = client.table(table).delete()

            # Apply filters with operator support
            for key, value in filters.items():
                if isinstance(value, dict):
                    # Handle operator syntax: {"id": {"in": [1,2,3]}}
                    for operator, operand in value.items():
                        if operator == "in":
                            query = query.in_(key, operand)
                        elif operator == "eq":
                            query = query.eq(key, operand)
                        elif operator == "neq":
                            query = query.neq(key, operand)
                        elif operator == "gt":
                            query = query.gt(key, operand)
                        elif operator == "gte":
                            query = query.gte(key, operand)
                        elif operator == "lt":
                            query = query.lt(key, operand)
                        elif operator == "lte":
                            query = query.lte(key, operand)
                        else:
                            logger.warning(f"Unsupported operator '{operator}' in filter")
                else:
                    # Simple equality filter
                    query = query.eq(key, value)

            response = await query.execute()
            count = len(response.data) if response.data else 0

            # Track operation for transaction (no rollback capability for deletes)
            if self._current_transaction is not None:
                self._current_transaction.operations.append({
                    "type": "delete",
                    "table": table,
                    "filters": filters,
                    "count": count,
                })

            return count

        except Exception as e:
            logger.error(
                f"Failed to delete from {table}",
                exc_info=True,
                extra={"table": table, "filters": filters}
            )
            raise StorageError(
                message=f"Delete failed for {table}: {str(e)}",
                operation="delete_entities",
                original_error=e,
            ) from e

    # ========================================================================
    # Transaction Support (Phase 3)
    # ========================================================================

    def transaction(self) -> "SupabaseTransaction":
        """
        Create a transaction context manager for atomic operations.

        Uses Postgres transactions via Supabase for true atomicity.

        Note: Supabase Python SDK doesn't natively support transactions,
        so we implement best-effort rollback tracking. For true atomic
        transactions, consider using direct Postgres connection or
        implementing transaction-aware operations at application level.
        """
        return SupabaseTransaction(self)

    # ========================================================================
    # Lifecycle Management
    # ========================================================================

    def cleanup(self) -> None:
        """Close internal HTTP connections gracefully.

        Closes both sync and async Supabase clients to prevent connection leaks.
        Safe to call multiple times (idempotent).

        Call this on application shutdown or when the storage adapter is no
        longer needed.
        """
        # Cleanup sync client
        if self._client is not None:
            try:
                # Close PostgREST client (database operations)
                if hasattr(self._client.postgrest, 'session'):
                    self._client.postgrest.session.close()
                    logger.debug("Closed sync PostgREST HTTP client")
            except Exception as e:
                logger.warning(f"Failed to close sync PostgREST client: {e}")

            try:
                # Close Storage client (file operations)
                if hasattr(self._client.storage, '_client'):
                    self._client.storage._client.close()
                    logger.debug("Closed sync Storage HTTP client")
            except Exception as e:
                logger.warning(f"Failed to close sync Storage client: {e}")

            try:
                # Close Functions client (edge function operations)
                if hasattr(self._client.functions, '_client'):
                    self._client.functions._client.close()
                    logger.debug("Closed sync Functions HTTP client")
            except Exception as e:
                logger.warning(f"Failed to close sync Functions client: {e}")

        # Cleanup async client - safe nullification (GC handles httpx connections)
        # Explicit cleanup via _cleanup_async() is better but not required
        if self._async_client is not None:
            logger.debug(
                "Async client cleanup - nullifying references for GC"
            )
            self._async_client = None
            self._async_client_loop = None

        logger.info("Supabase storage client cleanup completed")

    async def _cleanup_async(self) -> None:
        """Async cleanup for async client connections.

        Call this from async context before application shutdown if async
        client was used.
        """
        if self._async_client is not None:
            try:
                # Close async PostgREST client
                if hasattr(self._async_client.postgrest, 'session'):
                    await self._async_client.postgrest.session.aclose()
                    logger.debug("Closed async PostgREST HTTP client")
            except Exception as e:
                logger.warning(f"Failed to close async PostgREST client: {e}")

            try:
                # Close async Storage client
                if hasattr(self._async_client.storage, '_client'):
                    await self._async_client.storage._client.aclose()
                    logger.debug("Closed async Storage HTTP client")
            except Exception as e:
                logger.warning(f"Failed to close async Storage client: {e}")

            try:
                # Close async Functions client
                if hasattr(self._async_client.functions, '_client'):
                    await self._async_client.functions._client.aclose()
                    logger.debug("Closed async Functions HTTP client")
            except Exception as e:
                logger.warning(f"Failed to close async Functions client: {e}")

            self._async_client = None
            self._async_client_loop = None
            logger.info("Async Supabase client cleanup completed")


class SupabaseTransaction:
    """Transaction context manager for SupabaseStorageClient.

    Provides best-effort rollback tracking for Supabase operations.

    Note: Supabase Python SDK uses HTTP/REST API which doesn't support
    traditional database transactions. This implementation tracks operations
    and attempts compensating rollback on error, but cannot guarantee
    true atomicity like native Postgres transactions.

    For production-critical atomic operations, consider:
    1. Using Supabase RPC functions with Postgres transactions
    2. Direct Postgres connection with psycopg3
    3. Application-level saga pattern with compensation
    """

    def __init__(self, storage: SupabaseStorageClient):
        """Initialize transaction with storage reference."""
        self.storage = storage
        self.operations: list[dict[str, Any]] = []
        self.in_transaction = False

    async def __aenter__(self) -> "SupabaseTransaction":
        """Start transaction - begin tracking operations."""
        self.in_transaction = True
        self.operations = []
        self.storage._current_transaction = self  # Set active transaction
        logger.debug("Starting Supabase transaction (best-effort rollback)")
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """End transaction - rollback on exception, commit on success."""
        try:
            if exc_type is not None:
                # Exception occurred - attempt rollback
                logger.warning(
                    f"Transaction failed with {exc_type.__name__}: {exc_val}. "
                    f"Attempting best-effort rollback of {len(self.operations)} operations..."
                )
                await self._rollback()
                # Don't suppress the exception
                return False

            # Success - commit (no-op, changes already applied)
            logger.debug(f"Transaction completed successfully ({len(self.operations)} operations)")
            return False
        finally:
            # Always clear transaction state
            self.in_transaction = False
            self.storage._current_transaction = None

    async def _rollback(self) -> None:
        """Attempt best-effort rollback of tracked operations.

        Rolls back in reverse order (LIFO). Not guaranteed to succeed
        as Supabase REST API doesn't support true transactions.
        """
        # Temporarily clear transaction context to prevent tracking rollback operations
        original_transaction = self.storage._current_transaction
        self.storage._current_transaction = None

        try:
            for operation in reversed(self.operations):
                try:
                    op_type = operation.get("type")
                    if op_type == "insert":
                        # Delete inserted entities
                        table = operation["table"]
                        entity_ids = operation["ids"]
                        await self.storage.delete_entities(table, {"id": {"in": entity_ids}})
                        logger.debug(f"Rolled back insert to {table}: {entity_ids}")

                    elif op_type == "update":
                        # Cannot reliably rollback updates without storing previous values
                        logger.warning(f"Cannot rollback update to {operation['table']} (no snapshot)")

                    elif op_type == "delete":
                        # Cannot rollback deletes (data lost)
                        logger.warning(f"Cannot rollback delete from {operation['table']} (data lost)")

                except Exception as e:
                    logger.error(f"Rollback operation failed: {e}", exc_info=True)
        finally:
            # Restore transaction context (will be cleared by __aexit__)
            self.storage._current_transaction = original_transaction
