"""Supabase-backed implementation of the storage port."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, overload

import httpx
from supabase import AsyncClient, Client, create_async_client, create_client
from supabase.lib.client_options import AsyncClientOptions, SyncClientOptions

from autifyme_agents.core.config import settings
from autifyme_agents.core.exceptions import ConfigurationError, StorageError
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.storage_utils import sanitize_for_path
from autifyme_agents.schemas.models import (
    CompanyProfile,
    Product,
    SKUNamingConvention,
    VisualIdentity,
    WorkflowOutcome,
)

logger = logging.getLogger(__name__)


def _normalize_numeric_types(data: dict[str, Any] | list[dict[str, Any]]) -> dict[str, Any] | list[dict[str, Any]]:
    """
    Normalize whole-number floats to integers for PostgreSQL compatibility.

    When LLMs generate JSON with float notation (e.g., "sort_order": 1.0),
    Python's JSON parser creates float types. PostgreSQL integer columns
    reject float values, causing insertion failures.

    This normalizes all whole-number floats (1.0 → 1) before database insertion.
    Handles both single entities and batches.

    Args:
        data: Single entity dict or list of entity dicts

    Returns:
        Normalized data with whole-number floats converted to ints
    """
    def normalize_value(value: Any) -> Any:
        """Recursively normalize a single value."""
        if isinstance(value, float) and value.is_integer():
            return int(value)
        elif isinstance(value, dict):
            return {k: normalize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [normalize_value(item) for item in value]
        else:
            return value

    if isinstance(data, list):
        normalized_list: list[dict[str, Any]] = [normalize_value(item) for item in data]
        return normalized_list
    else:
        normalized_dict: dict[str, Any] = normalize_value(data)
        return normalized_dict


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

    @staticmethod
    def _is_uuid(value: str) -> bool:
        """
        Check if a string is a valid UUID format.

        UUIDs should use exact case-sensitive matching (not case-insensitive).
        This prevents converting UUID filters to ILIKE which would be incorrect.

        Args:
            value: String to check

        Returns:
            True if value matches UUID format (8-4-4-4-12 hex pattern)
        """
        import re
        # UUID pattern: 8-4-4-4-12 hex digits
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, value.lower()))

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

        # Type guaranteed: if client was None, we initialized it above or raised exception
        assert self._async_client is not None, "Async client should be initialized"
        return self._async_client

    def get_company_profile(self) -> CompanyProfile:
        """Return the single-tenant company profile from storage.

        Loads data from:
        - companies: Core company info, brand voice, currency
        - company_intelligence: Visual identity, competitive intel
        - assets: Logo storage path (if logo_asset_id in visual_identity)

        Returns:
            Enriched CompanyProfile with visual identity and all context
        """
        client = self._ensure_client()

        # Load core company data
        company_response = client.table("companies").select("*").limit(1).single().execute()
        if not company_response.data:
            raise ValueError(
                "No company profile found in storage. Populate the `companies` table before running workflows."
            )
        company_data = company_response.data

        # Load company intelligence (visual identity, brand values, etc.)
        intel_response = client.table("company_intelligence").select("*").limit(1).execute()
        intel_data = intel_response.data[0] if intel_response.data else {}

        # Build VisualIdentity from company_intelligence.visual_identity JSONB
        visual_identity = VisualIdentity()
        if intel_data.get("visual_identity"):
            vi = intel_data["visual_identity"]
            logo_asset_path: str | None = None

            # Resolve logo_asset_id to storage path
            if vi.get("logo_asset_id"):
                try:
                    asset_response = client.table("assets").select("storage_url").eq(
                        "id", vi["logo_asset_id"]
                    ).limit(1).single().execute()
                    if asset_response.data and asset_response.data.get("storage_url"):
                        # Extract relative path from full URL
                        # URL: https://...supabase.co/storage/v1/object/public/assets/brands/file.jpg
                        # Path: brands/file.jpg
                        storage_url = asset_response.data["storage_url"]
                        if "/assets/" in storage_url:
                            logo_asset_path = storage_url.split("/assets/", 1)[1]
                except Exception as e:
                    logger.warning(f"Failed to resolve logo asset: {e}")

            visual_identity = VisualIdentity(
                primary_color=vi.get("primary_color", "#d32f2f"),
                secondary_color=vi.get("secondary_color", "#000000"),
                accent_color=vi.get("accent_color"),
                font_family=vi.get("font_family", "sans-serif"),
                logo_asset_path=logo_asset_path,
            )

        # Build SKUNamingConvention from brand_attributes.sku_naming
        sku_naming: SKUNamingConvention | None = None
        brand_attrs = company_data.get("brand_attributes") or {}
        if brand_attrs.get("sku_naming"):
            sku_data = brand_attrs["sku_naming"]
            sku_naming = SKUNamingConvention(
                prefix=sku_data.get("prefix", "SKU"),
                pattern=sku_data.get("pattern", "PREFIX-CATEGORY-SIZE-VARIANT"),
                separator=sku_data.get("separator", "-"),
                uppercase=sku_data.get("uppercase", True),
                examples=sku_data.get("examples", []),
            )

        # Extract style_preferences from brand_attributes or brand_values
        style_preferences: list[str] = []
        if brand_attrs.get("competitive_advantages"):
            style_preferences = brand_attrs["competitive_advantages"][:5]
        elif intel_data.get("brand_values"):
            style_preferences = intel_data["brand_values"][:5]

        # Extract business context from company_intelligence
        business_models: list[str] = intel_data.get("business_models", [])
        target_markets: list[str] = company_data.get("target_markets") or []
        price_positioning: str = intel_data.get("price_positioning", "mid-range")

        # Build enriched CompanyProfile
        return CompanyProfile(
            id=company_data["id"],
            name=company_data["name"],
            brand_voice=company_data.get("brand_voice", ""),
            target_audience=company_data.get("target_audience", ""),
            style_preferences=style_preferences,
            industry=company_data.get("industry") or brand_attrs.get("industry_focus"),
            business_models=business_models,
            target_markets=target_markets,
            price_positioning=price_positioning,
            sku_naming_convention=sku_naming,
            visual_identity=visual_identity,
            default_currency=company_data.get("default_currency", "INR"),
            currency_symbol=company_data.get("currency_symbol", "₹"),
            default_price_list_id=company_data.get("default_retail_price_list_id"),
        )

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

    def save_workflow_outcome(self, outcome: WorkflowOutcome) -> str:
        """Persist workflow outcome for learning and analytics.

        Args:
            outcome: WorkflowOutcome model with tracking data

        Returns:
            Outcome ID from database

        Raises:
            ValueError: If required fields are missing
            RuntimeError: If database insertion fails
        """
        client = self._ensure_client()

        # Convert Pydantic model to dict for database insertion
        outcome_dict = outcome.model_dump(mode="json")

        # Validate required fields before attempting insert
        # Must match NOT NULL columns in workflow_outcomes table
        required_fields = ["tracking_id", "thread_id", "sender_id", "message_hash", "success", "received_at", "started_at"]
        missing_fields = [field for field in required_fields if field not in outcome_dict or outcome_dict[field] is None]

        if missing_fields:
            error_msg = f"Cannot persist workflow outcome - missing required fields: {missing_fields}"
            logger.error(
                error_msg,
                extra={
                    "missing_fields": missing_fields,
                    "tracking_id": outcome_dict.get("tracking_id"),
                    "thread_id": outcome_dict.get("thread_id"),
                }
            )
            raise ValueError(error_msg)

        # Ensure timestamps are ISO strings for Supabase
        payload = outcome_dict.copy()
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

            # Validate response structure before accessing
            first_row = response.data[0]
            if "id" not in first_row:
                raise RuntimeError(
                    f"Supabase response missing 'id' field. Got keys: {list(first_row.keys())}"
                )

            outcome_id: str = first_row["id"]

            logger.info(
                "Persisted workflow outcome",
                extra={
                    "tracking_id": outcome_dict.get("tracking_id"),
                    "success": outcome_dict.get("success"),
                    "intent": outcome_dict.get("intent"),
                    "department": outcome_dict.get("department"),
                    "outcome_id": outcome_id,
                },
            )

            return outcome_id

        except Exception as e:
            logger.error(
                "Failed to persist workflow outcome to database",
                extra={
                    "tracking_id": outcome_dict.get("tracking_id"),
                    "thread_id": outcome_dict.get("thread_id"),
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
    ) -> list[WorkflowOutcome]:
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
        # Convert dicts to WorkflowOutcome models
        if response.data:
            return [WorkflowOutcome.model_validate(row) for row in response.data]
        return []

    def get_recent_failures(
        self,
        time_window: timedelta,
        limit: int = 10,
    ) -> list[WorkflowOutcome]:
        """Retrieve recent failures for regression test generation."""
        client = self._ensure_client()

        cutoff = (datetime.now(UTC) - time_window).isoformat()

        response = (
            client.table("workflow_outcomes")
            .select("*")  # Select all columns to build full WorkflowOutcome model
            .eq("success", False)
            .gte("created_at", cutoff)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        # Convert dicts to WorkflowOutcome models
        if response.data:
            return [WorkflowOutcome.model_validate(row) for row in response.data]
        return []

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
        filters: dict[str, Any] | None = None,
        columns: list[str] | None = None,
        relations: list[str] | None = None,
        search_patterns: dict[str, str | list[str]] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query entities - always returns list of rows.

        Type-safe wrapper over query_advanced with count_only=False.

        Args:
            table: Table name
            filters: WHERE conditions as dict
            columns: Columns to select (default: all)
            relations: Related tables to include
            search_patterns: Case-insensitive LIKE patterns
            limit: Maximum rows to return

        Returns:
            List of matching rows (guaranteed list, never int)

        Raises:
            StorageError: On query failure
        """
        result = await self.query_advanced(
            table=table,
            filters=filters,
            columns=columns,
            relations=relations,
            search_patterns=search_patterns,
            count_only=False,  # Always return rows
            limit=limit
        )
        # Type guaranteed by @overload: count_only=False → list
        assert isinstance(result, list)  # Runtime assertion for type safety
        return result

    async def count_entities(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        search_patterns: dict[str, str | list[str]] | None = None,
    ) -> int:
        """
        Count entities - always returns int count.

        Type-safe wrapper over query_advanced with count_only=True.

        Args:
            table: Table name
            filters: WHERE conditions as dict
            search_patterns: Case-insensitive LIKE patterns

        Returns:
            Count of matching rows (guaranteed int, never list)

        Raises:
            StorageError: On query failure
        """
        result = await self.query_advanced(
            table=table,
            filters=filters,
            search_patterns=search_patterns,
            count_only=True,  # Always return count
        )
        # Type guaranteed by @overload: count_only=True → int
        assert isinstance(result, int)  # Runtime assertion for type safety
        return result

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

    @overload
    async def query_advanced(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        columns: list[str] | None = None,
        relations: list[str] | None = None,
        search_patterns: dict[str, str | list[str]] | None = None,
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
        search_patterns: dict[str, str | list[str]] | None = None,
        count_only: Literal[False] = ...,
        limit: int | None = None,
    ) -> list[dict[str, Any]]: ...

    async def query_advanced(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        columns: list[str] | None = None,
        relations: list[str] | None = None,
        search_patterns: dict[str, str | list[str]] | None = None,
        count_only: bool = False,
        limit: int | None = None,
    ) -> list[dict[str, Any]] | int:
        """Advanced query with relations, pattern matching, and counting.

        Args:
            table: Table name
            filters: Exact match filters
            columns: Columns to select
            relations: Related tables using PostgREST syntax
            search_patterns: ILIKE patterns for search. Supports:
                - Single pattern (AND): {'name': '%jar%'}
                - Multiple patterns (OR): {'name': ['%jar%', '%container%']}
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

            # Apply filters with case-insensitive matching for text fields
            if filters:
                for key, value in filters.items():
                    if isinstance(value, list):
                        # List value - use IN operator
                        query = query.in_(key, value)
                    elif isinstance(value, str) and not self._is_uuid(value):
                        # String value (non-UUID) - use case-insensitive match
                        # This prevents "neck type" vs "Neck Type" mismatches
                        query = query.ilike(key, value)
                    else:
                        # UUID, number, boolean - use exact match
                        query = query.eq(key, value)

            # Apply ILIKE search patterns (supports OR via list values)
            if search_patterns:
                for key, patterns in search_patterns.items():
                    if isinstance(patterns, list):
                        # OR between multiple patterns for same column
                        # PostgREST syntax: column.ilike.pattern1,column.ilike.pattern2
                        or_conditions = ",".join(f"{key}.ilike.{p}" for p in patterns)
                        query = query.or_(or_conditions)
                    else:
                        # Single pattern - AND with other conditions
                        query = query.ilike(key, patterns)

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

    async def query_aggregate(
        self,
        table: str,
        aggregates: dict[str, str],
        filters: dict[str, Any] | None = None,
        search_patterns: dict[str, str | list[str]] | None = None,
        group_by: list[str] | None = None,
        having: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Query with aggregations and GROUP BY.

        Universal Data Engine - Phase 1.2: Aggregation support.

        Uses RPC function (dynamic_aggregate) to bypass PostgREST aggregate
        restrictions (PGRST123). Falls back to PostgREST if RPC unavailable.

        Args:
            table: Table name
            aggregates: Aggregation operations as {alias: "function(column)"}
            filters: Exact match filters before aggregation
            search_patterns: ILIKE patterns before aggregation
            group_by: Columns to group by
            having: Filters on aggregated results

        Returns:
            List of aggregated results

        Raises:
            StorageError: On query failure
        """
        try:
            client = await self._ensure_async_client()

            # Try RPC function first (bypasses PostgREST aggregate restrictions)
            try:
                return await self._query_aggregate_via_rpc(
                    client, table, aggregates, filters, search_patterns, group_by, having
                )
            except Exception as rpc_error:
                # Check if RPC function doesn't exist - fall back to PostgREST
                error_msg = str(rpc_error).lower()
                rpc_not_found = (
                    ("function" in error_msg and "does not exist" in error_msg)
                    or ("could not find" in error_msg and "function" in error_msg)
                    or "pgrst202" in error_msg  # PostgREST function not found code
                )
                if rpc_not_found:
                    logger.info(
                        "dynamic_aggregate RPC not found - will raise error"
                    )
                else:
                    # RPC exists but failed - re-raise
                    raise

            # RPC not available - fail with actionable error
            raise StorageError(
                message=f"Aggregate queries require dynamic_aggregate RPC function for table '{table}'. "
                        "Run migration 006_dynamic_aggregate_rpc.sql to enable.",
                operation="query_aggregate",
            )

        except Exception as e:
            logger.error(
                f"Aggregate query failed for {table}",
                exc_info=True,
                extra={
                    "table": table,
                    "aggregates": aggregates,
                    "group_by": group_by,
                }
            )
            raise StorageError(
                message=f"Aggregate query failed for {table}: {str(e)}",
                operation="query_aggregate",
                original_error=e,
            ) from e

    async def _query_aggregate_via_rpc(
        self,
        client: Any,
        table: str,
        aggregates: dict[str, str],
        filters: dict[str, Any] | None,
        search_patterns: dict[str, str] | None,
        group_by: list[str] | None,
        having: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """Execute aggregate query via dynamic_aggregate RPC function.

        This bypasses PostgREST's aggregate restrictions (PGRST123).
        """
        # Removed json import - pass dicts directly

        # Merge filters and search_patterns for RPC
        combined_filters = dict(filters or {})
        if search_patterns:
            # Add ILIKE patterns with special prefix for RPC to recognize
            for col, pattern in search_patterns.items():
                combined_filters[f"__ilike__{col}"] = pattern

        response = await client.rpc(
            "dynamic_aggregate",
            {
                "p_table": table,
                "p_aggregates": aggregates,
                "p_filters": combined_filters if combined_filters else {},
                "p_group_by": group_by,
                "p_having": having,
            }
        ).execute()

        results = response.data if response.data else []

        # RPC returns JSONB which is already a list
        if isinstance(results, list):
            return results
        elif results is None:
            return []
        else:
            return [results] if isinstance(results, dict) else list(results)

    async def batch_read(
        self,
        table: str,
        ids: list[str],
        relations: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch multiple entities by ID in single query.

        Universal Data Engine - Phase 1.3: Batch read for N+1 optimization.

        Uses PostgREST IN clause to fetch all entities in single query,
        with optional relation prefetching to eliminate cascading queries.

        Args:
            table: Table name
            ids: List of entity IDs to fetch
            relations: Optional relations to prefetch

        Returns:
            List of entities in the same order as input IDs (missing IDs omitted)

        Raises:
            StorageError: On query failure
        """
        try:
            if not ids:
                return []

            client = await self._ensure_async_client()

            # Build select clause with relations
            select = "*"
            if relations:
                # PostgREST syntax: "*, products(*), variants(*)"
                select = "*," + ",".join(relations)

            # Fetch all entities with IN clause
            query = client.table(table).select(select).in_("id", ids)
            response = await query.execute()

            results = response.data if response.data else []

            # Preserve input order: create ID->entity map, then rebuild list
            entity_map = {entity["id"]: entity for entity in results}
            ordered_results = [entity_map[id] for id in ids if id in entity_map]

            logger.debug(
                f"Batch read {len(ordered_results)}/{len(ids)} entities from {table}",
                extra={
                    "table": table,
                    "requested": len(ids),
                    "found": len(ordered_results),
                    "missing": len(ids) - len(ordered_results),
                }
            )

            return ordered_results

        except Exception as e:
            logger.error(
                f"Batch read failed for {table}",
                exc_info=True,
                extra={"table": table, "id_count": len(ids)}
            )
            raise StorageError(
                message=f"Batch read failed for {table}: {str(e)}",
                operation="batch_read",
                original_error=e,
            ) from e

    async def paginate_query(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        search_patterns: dict[str, str | list[str]] | None = None,
        relations: list[str] | None = None,
        order_by: str | None = None,
        page: int = 1,
        per_page: int = 20,
        cursor: str | None = None,
        include_count: bool = False,
    ) -> dict[str, Any]:
        """Paginate query results with offset or cursor-based pagination.

        Universal Data Engine - Phase 1.3: Smart pagination.

        Supports:
        - Offset pagination (page + per_page) for traditional UX
        - Cursor pagination (cursor + per_page) for efficient large datasets
        - Optional total count (skipped by default for performance)

        Args:
            table: Table name
            filters: Exact match filters
            search_patterns: ILIKE patterns
            relations: Relations to prefetch
            order_by: Sort specification (e.g., "created_at.desc")
            page: Page number (1-indexed, for offset pagination)
            per_page: Items per page (default 20, max 100)
            cursor: Cursor token (overrides page-based pagination)
            include_count: Whether to include total count

        Returns:
            Dict with pagination metadata and results

        Raises:
            StorageError: On query failure
            ValueError: If per_page > 100 or page < 1
        """
        try:
            # Validate pagination parameters
            if per_page > 100:
                raise ValueError("per_page must not exceed 100")
            if page < 1:
                raise ValueError("page must be >= 1")

            client = await self._ensure_async_client()

            # Build select clause
            select = "*"
            if relations:
                select = "*," + ",".join(relations)

            # Start building query
            query = client.table(table).select(select)

            # Apply filters
            if filters:
                for key, value in filters.items():
                    if isinstance(value, list):
                        query = query.in_(key, value)
                    else:
                        query = query.eq(key, value)

            # Apply search patterns (supports OR via list values)
            if search_patterns:
                for column, patterns in search_patterns.items():
                    if isinstance(patterns, list):
                        or_conditions = ",".join(f"{column}.ilike.{p}" for p in patterns)
                        query = query.or_(or_conditions)
                    else:
                        query = query.ilike(column, patterns)

            # Apply ordering (default to id.asc for consistency)
            if order_by:
                # Parse "column.direction" format
                if "." in order_by:
                    column, direction = order_by.rsplit(".", 1)
                    query = query.order(column, desc=(direction.lower() == "desc"))
                else:
                    query = query.order(order_by)
            else:
                query = query.order("id")

            # Cursor vs Offset pagination
            if cursor:
                # Cursor-based: Use range header with cursor
                # PostgREST cursor format is base64-encoded JSON with continuation token
                # For simplicity, we'll implement offset-based first and add cursor later
                # Cursor pagination requires PostgREST 11+ and specific configuration
                import base64
                import json

                try:
                    decoded = json.loads(base64.b64decode(cursor).decode("utf-8"))
                    last_id = decoded.get("last_id")
                    if last_id:
                        # Continue from last ID (requires order by id)
                        query = query.gt("id", last_id)
                except Exception:
                    logger.warning(f"Invalid cursor format: {cursor}, falling back to offset pagination")

            else:
                # Offset-based: Calculate offset from page
                offset = (page - 1) * per_page
                query = query.range(offset, offset + per_page - 1)

            # Execute main query
            response = await query.execute()
            results = response.data if response.data else []

            # Get total count if requested (separate query for performance)
            total = None
            if include_count:
                count_query = client.table(table).select("*", count="exact").limit(0)

                # Apply same filters to count query
                if filters:
                    for key, value in filters.items():
                        if isinstance(value, list):
                            count_query = count_query.in_(key, value)
                        else:
                            count_query = count_query.eq(key, value)

                if search_patterns:
                    for column, patterns in search_patterns.items():
                        if isinstance(patterns, list):
                            or_conditions = ",".join(f"{column}.ilike.{p}" for p in patterns)
                            count_query = count_query.or_(or_conditions)
                        else:
                            count_query = count_query.ilike(column, patterns)

                count_response = await count_query.execute()
                total = count_response.count if count_response.count is not None else 0

            # Determine if there are more pages
            has_next = len(results) == per_page

            # Generate next cursor for cursor-based pagination
            next_cursor = None
            if cursor and results and has_next:
                import base64
                import json
                last_entity = results[-1]
                cursor_data = {"last_id": last_entity.get("id")}
                next_cursor = base64.b64encode(json.dumps(cursor_data).encode("utf-8")).decode("utf-8")

            # Build response
            result = {
                "data": results,
                "page": page if not cursor else None,
                "per_page": per_page,
                "has_next": has_next,
            }

            if include_count and total is not None:
                result["total"] = total

            if next_cursor:
                result["next_cursor"] = next_cursor

            logger.debug(
                f"Paginated query returned {len(results)} results from {table}",
                extra={
                    "table": table,
                    "page": page,
                    "per_page": per_page,
                    "cursor": bool(cursor),
                    "has_next": has_next,
                }
            )

            return result

        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(
                f"Paginated query failed for {table}",
                exc_info=True,
                extra={"table": table, "page": page, "per_page": per_page}
            )
            raise StorageError(
                message=f"Paginated query failed for {table}: {str(e)}",
                operation="paginate_query",
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
            # Normalize whole-number floats to ints for PostgreSQL compatibility
            normalized_data = _normalize_numeric_types(data)
            response = await client.table(table).insert(normalized_data).execute()

            if not response.data or len(response.data) == 0:
                raise StorageError(
                    message=f"Insert to {table} returned no data",
                    operation="insert_entity",
                )

            inserted: dict[str, Any] = response.data[0]

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
            # Normalize whole-number floats to ints for PostgreSQL compatibility
            normalized_data = _normalize_numeric_types(data)
            response = await client.table(table).insert(normalized_data).execute()

            if not response.data:
                raise StorageError(
                    message=f"Batch insert to {table} returned no data",
                    operation="insert_entities",
                )

            inserted: list[dict[str, Any]] = response.data

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
            # Normalize whole-number floats to ints for PostgreSQL compatibility
            normalized_updates = _normalize_numeric_types(updates)
            query = client.table(table).update(normalized_updates)

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
                elif isinstance(value, list):
                    # List value - use IN operator
                    query = query.in_(key, value)
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
        soft_delete: bool = True,
    ) -> int:
        """Delete entities matching filters.

        Args:
            table: Table name
            filters: WHERE conditions (supports nested dict for operators like {"id": {"in": [1,2,3]}})
            soft_delete: If True, sets is_active=False and deleted_at=now().
                        If False, performs hard delete (permanent removal).
                        Defaults to True for data safety.

        Returns:
            Count of deleted/deactivated rows

        Raises:
            StorageError: On delete failure
        """
        try:
            client = await self._ensure_async_client()

            if soft_delete:
                # Soft delete: UPDATE is_active=False and deleted_at=now()
                from datetime import UTC, datetime
                updates = {
                    "is_active": False,
                    "deleted_at": datetime.now(UTC).isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                }

                # Use update_entities for soft delete
                count = await self.update_entities(
                    table=table,
                    filters=filters,
                    updates=updates
                )

                # Track operation for transaction
                if self._current_transaction is not None:
                    self._current_transaction.operations.append({
                        "type": "soft_delete",
                        "table": table,
                        "filters": filters,
                        "count": count,
                    })

                return count
            else:
                # Hard delete: Permanent removal
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
                    elif isinstance(value, list):
                        # List value - use IN operator
                        query = query.in_(key, value)
                    else:
                        # Simple equality filter
                        query = query.eq(key, value)

                response = await query.execute()
                count = len(response.data) if response.data else 0

                # Track operation for transaction (no rollback capability for hard deletes)
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
    # Upsert & Patch Operations (Universal Data Engine - Phase 1.4)
    # ========================================================================

    async def upsert_entity(
        self,
        table: str,
        data: dict[str, Any],
        conflict_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Insert or update entity with PostgreSQL upsert semantics.

        Uses PostgREST's upsert (INSERT ... ON CONFLICT DO UPDATE) for idempotent writes.

        Args:
            table: Table name
            data: Entity data
            conflict_fields: Columns for conflict detection (default: ["id"])

        Returns:
            Final entity state after upsert

        Raises:
            StorageError: On upsert failure
        """
        try:
            client = await self._ensure_async_client()
            normalized_data = _normalize_numeric_types(data)

            # Default to primary key if no conflict fields specified
            on_conflict = ",".join(conflict_fields) if conflict_fields else "id"

            # Execute upsert: INSERT with ON CONFLICT DO UPDATE
            response = await client.table(table).upsert(
                normalized_data,
                on_conflict=on_conflict,
                ignore_duplicates=False,  # DO UPDATE on conflict
                returning="representation",
            ).execute()

            if not response.data or len(response.data) == 0:
                raise StorageError(
                    message=f"Upsert returned no data for {table}",
                    operation="upsert_entity",
                )

            upserted = response.data[0]

            # Track operation for transaction
            if self._current_transaction is not None:
                self._current_transaction.operations.append({
                    "type": "upsert",
                    "table": table,
                    "ids": [upserted.get("id")],
                    "conflict_fields": conflict_fields or ["id"],
                })

            return upserted

        except Exception as e:
            logger.error(
                f"Failed to upsert into {table}",
                exc_info=True,
                extra={"table": table, "conflict_fields": conflict_fields, "data_keys": list(data.keys())}
            )
            raise StorageError(
                message=f"Upsert failed for {table}: {str(e)}",
                operation="upsert_entity",
                original_error=e,
            ) from e

    async def bulk_upsert(
        self,
        table: str,
        data: list[dict[str, Any]],
        conflict_fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Batch upsert multiple entities with conflict resolution.

        Uses PostgREST's bulk upsert for efficient idempotent batch writes.

        Args:
            table: Table name
            data: List of entity data
            conflict_fields: Columns for conflict detection (default: ["id"])

        Returns:
            List of final entity states after upserts

        Raises:
            StorageError: On upsert failure
            ValueError: If data list is empty
        """
        if not data:
            raise ValueError("Data list cannot be empty for bulk_upsert")

        try:
            client = await self._ensure_async_client()
            normalized_data = _normalize_numeric_types(data)

            # Default to primary key if no conflict fields specified
            on_conflict = ",".join(conflict_fields) if conflict_fields else "id"

            # Execute bulk upsert
            response = await client.table(table).upsert(
                normalized_data,
                on_conflict=on_conflict,
                ignore_duplicates=False,  # DO UPDATE on conflict
                returning="representation",
                default_to_null=True,  # Missing fields default to NULL on INSERT
            ).execute()

            if not response.data:
                raise StorageError(
                    message=f"Bulk upsert returned no data for {table}",
                    operation="bulk_upsert",
                )

            upserted = response.data
            entity_ids = [entity.get("id") for entity in upserted if entity.get("id")]

            # Track operation for transaction
            if self._current_transaction is not None:
                self._current_transaction.operations.append({
                    "type": "bulk_upsert",
                    "table": table,
                    "ids": entity_ids,
                    "conflict_fields": conflict_fields or ["id"],
                    "count": len(upserted),
                })

            return upserted

        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(
                f"Failed to bulk upsert into {table}",
                exc_info=True,
                extra={"table": table, "conflict_fields": conflict_fields, "entity_count": len(data)}
            )
            raise StorageError(
                message=f"Bulk upsert failed for {table}: {str(e)}",
                operation="bulk_upsert",
                original_error=e,
            ) from e

    async def patch_entity(
        self,
        table: str,
        id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Partially update entity (PATCH semantics).

        Updates only specified fields using UPDATE query.

        Args:
            table: Table name
            id: Entity ID
            updates: Fields to update (partial data)

        Returns:
            Complete updated entity

        Raises:
            StorageError: On update failure
            ValueError: If entity not found
        """
        try:
            client = await self._ensure_async_client()
            normalized_updates = _normalize_numeric_types(updates)

            # Execute update with ID filter
            response = await client.table(table).update(normalized_updates).eq("id", id).execute()

            if not response.data or len(response.data) == 0:
                raise ValueError(f"Entity with id '{id}' not found in {table}")

            patched = response.data[0]

            # Track operation for transaction
            if self._current_transaction is not None:
                self._current_transaction.operations.append({
                    "type": "patch",
                    "table": table,
                    "ids": [id],
                    "updates": updates,
                })

            return patched

        except ValueError:
            # Re-raise validation errors (entity not found)
            raise
        except Exception as e:
            logger.error(
                f"Failed to patch entity in {table}",
                exc_info=True,
                extra={"table": table, "id": id, "updates": updates}
            )
            raise StorageError(
                message=f"Patch failed for {table}: {str(e)}",
                operation="patch_entity",
                original_error=e,
            ) from e

    # ========================================================================
    # Dry-Run & Validation (Universal Data Engine - Phase 1.5)
    # ========================================================================

    async def validate_entity_data(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        operation: Literal["insert", "update", "upsert", "delete"],
    ) -> dict[str, Any]:
        """
        Validate entity data against schema without executing operation.

        Performs basic schema validation:
        - Checks for required fields (basic validation)
        - Type checking for common field types
        - Returns errors/warnings without executing writes

        Args:
            table: Table name
            data: Entity data (single dict or list of dicts)
            operation: Operation type being validated

        Returns:
            Validation result with valid flag, errors, and warnings
        """
        try:
            # Normalize to list for consistent processing
            entities = data if isinstance(data, list) else [data]

            errors: list[dict[str, Any]] = []
            warnings: list[dict[str, Any]] = []

            # Basic validation rules for common fields
            # In production, these would come from schema registry
            required_fields_by_table = {
                "products": ["sku_code", "name"] if operation == "insert" else [],
                "product_families": ["name", "sku_prefix"] if operation == "insert" else [],
                "categories": ["name"] if operation == "insert" else [],
            }

            required_fields = required_fields_by_table.get(table, [])

            # Validate each entity
            for idx, entity in enumerate(entities):
                # Check required fields
                for field in required_fields:
                    if field not in entity or entity[field] is None or entity[field] == "":
                        errors.append({
                            "entity_index": idx,
                            "field": field,
                            "error": f"Field '{field}' is required but missing or empty",
                            "severity": "error"
                        })

                # Type validation for common fields
                if "base_price" in entity and entity["base_price"] is not None:
                    if not isinstance(entity["base_price"], (int, float)):
                        errors.append({
                            "entity_index": idx,
                            "field": "base_price",
                            "error": "Field 'base_price' must be a number",
                            "severity": "error"
                        })
                    elif entity["base_price"] < 0:
                        warnings.append({
                            "entity_index": idx,
                            "field": "base_price",
                            "warning": "Negative price detected",
                            "severity": "warning"
                        })

                # Check for unusually long strings (potential data issues)
                for key, value in entity.items():
                    if isinstance(value, str) and len(value) > 1000:
                        warnings.append({
                            "entity_index": idx,
                            "field": key,
                            "warning": f"String value exceeds 1000 characters ({len(value)} chars)",
                            "severity": "warning"
                        })

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "entity_count": len(entities),
            }

        except Exception as e:
            logger.error(
                f"Validation failed for {table}",
                exc_info=True,
                extra={"table": table, "operation": operation}
            )
            raise StorageError(
                message=f"Validation failed for {table}: {str(e)}",
                operation="validate_entity_data",
                original_error=e,
            ) from e

    async def check_constraint_violations(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        operation: Literal["insert", "update", "upsert"],
        exclude_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Check for constraint violations before write operation.

        Checks uniqueness constraints using existing storage methods.
        Leverages check_existing_values for efficient batch checking.

        Args:
            table: Table name
            data: Entity data (single dict or list of dicts)
            operation: Operation type
            exclude_ids: IDs to exclude from uniqueness check

        Returns:
            Constraint check result with safe_to_proceed flag and violations
        """
        try:
            # Normalize to list
            entities = data if isinstance(data, list) else [data]

            violations: list[dict[str, Any]] = []
            warnings: list[dict[str, Any]] = []
            checked_constraints: list[str] = []

            # Define unique fields per table
            # In production, these would come from schema registry
            unique_fields_by_table = {
                "products": ["sku_code"],
                "product_families": ["sku_prefix"],
                "categories": ["slug"],
                "variant_axes": ["axis_name"],
            }

            unique_fields = unique_fields_by_table.get(table, [])

            # Check uniqueness constraints (skip for upsert as it handles conflicts)
            if operation != "upsert":
                for field in unique_fields:
                    # Collect values to check
                    values_to_check = [
                        entity[field]
                        for entity in entities
                        if field in entity and entity[field] is not None
                    ]

                    if values_to_check:
                        # Use existing check_existing_values method
                        existing_values = await self.check_existing_values(
                            table, field, values_to_check, exclude_ids
                        )

                        # Report violations for existing values
                        for value in existing_values:
                            violations.append({
                                "type": "uniqueness",
                                "field": field,
                                "value": value,
                                "message": f"{field} '{value}' already exists",
                            })

                        checked_constraints.append(f"{field}_unique")

            # Check for large batches (performance warning)
            if len(entities) > 100:
                warnings.append({
                    "type": "performance",
                    "message": f"Large batch ({len(entities)} entities) may be slow"
                })

            # Check for duplicate values within the batch itself
            for field in unique_fields:
                field_values = [
                    entity[field]
                    for entity in entities
                    if field in entity and entity[field] is not None
                ]

                duplicates = {v for v in field_values if field_values.count(v) > 1}

                for dup_value in duplicates:
                    violations.append({
                        "type": "duplicate_in_batch",
                        "field": field,
                        "value": dup_value,
                        "message": f"Duplicate {field} '{dup_value}' within batch"
                    })

            return {
                "safe_to_proceed": len(violations) == 0,
                "violations": violations,
                "warnings": warnings,
                "checked_constraints": checked_constraints,
            }

        except Exception as e:
            logger.error(
                f"Constraint check failed for {table}",
                exc_info=True,
                extra={"table": table, "operation": operation}
            )
            raise StorageError(
                message=f"Constraint check failed for {table}: {str(e)}",
                operation="check_constraint_violations",
                original_error=e,
            ) from e

    async def preview_write_impact(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        operation: Literal["update", "delete"] = "update",
        sample_size: int = 5,
    ) -> dict[str, Any]:
        """
        Preview impact of update/delete operation before execution.

        Uses existing count_entities and query_entities for efficient preview.

        Args:
            table: Table name
            filters: Filter conditions
            operation: Operation type ("update" or "delete")
            sample_size: Number of sample entities to return

        Returns:
            Impact preview with affected_count, samples, and warnings
        """
        try:
            # Get affected count
            affected_count = await self.count_entities(table, filters=filters)

            # Get sample entities
            sample_entities: list[dict[str, Any]] = []
            if affected_count > 0:
                sample_entities = await self.query_entities(
                    table,
                    filters=filters,
                    limit=sample_size
                )

            # Calculate estimated duration (heuristic: ~2ms per entity)
            estimated_duration_ms = max(10, affected_count * 2)

            # Generate warnings
            warnings: list[dict[str, Any]] = []
            safe_to_proceed = True

            if filters is None or len(filters) == 0:
                warnings.append({
                    "type": "no_filters",
                    "message": "Operation affects ALL entities in table"
                })
                safe_to_proceed = False  # Dangerous operation

            if affected_count > 100:
                warnings.append({
                    "type": "large_batch",
                    "message": f"Operation affects {affected_count} entities"
                })

            if affected_count == 0:
                warnings.append({
                    "type": "no_effect",
                    "message": "No entities match the filter criteria"
                })

            return {
                "affected_count": affected_count,
                "sample_entities": sample_entities,
                "estimated_duration_ms": estimated_duration_ms,
                "warnings": warnings,
                "safe_to_proceed": safe_to_proceed,
            }

        except Exception as e:
            logger.error(
                f"Preview failed for {table}",
                exc_info=True,
                extra={"table": table, "operation": operation, "filters": filters}
            )
            raise StorageError(
                message=f"Preview failed for {table}: {str(e)}",
                operation="preview_write_impact",
                original_error=e,
            ) from e

    # ========================================================================
    # Schema Intelligence (Universal Data Engine - Phase 1.1)
    # ========================================================================

    async def get_table_stats(self, table: str) -> dict[str, Any]:
        """Get table statistics for schema intelligence.

        Provides runtime metadata about table size, last update, and index usage.

        Args:
            table: Table name

        Returns:
            Dict with statistics (row_count, estimated_size_bytes, last_updated, indexes, primary_key)

        Raises:
            StorageError: On query failure or table not found
        """
        try:
            client = await self._ensure_async_client()

            # Get row count
            count_response = await client.table(table).select("*", count="exact").limit(0).execute()
            row_count = count_response.count if count_response.count is not None else 0

            # Get table metadata from PostgreSQL information_schema
            # Note: Supabase PostgREST doesn't expose pg_catalog directly,
            # so we use RPC call or query information_schema if available
            # For now, provide basic stats from count query

            # TODO: Add RPC function in database to fetch:
            # - pg_total_relation_size for accurate size
            # - pg_stat_user_tables for last_updated
            # - pg_indexes for index list

            stats: dict[str, Any] = {
                "row_count": row_count,
                "estimated_size_bytes": None,  # Requires database function
                "last_updated": None,  # Requires pg_stat_user_tables access
                "indexes": [],  # Requires pg_indexes access
                "primary_key": "id",  # Convention - most tables use 'id'
            }

            logger.debug(
                f"Fetched stats for {table}",
                extra={"table": table, "row_count": row_count}
            )

            return stats

        except Exception as e:
            logger.error(
                f"Failed to get stats for {table}",
                exc_info=True,
                extra={"table": table}
            )
            raise StorageError(
                message=f"Failed to get table stats for {table}: {str(e)}",
                operation="get_table_stats",
                original_error=e,
            ) from e

    async def sample_data(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Fetch sample data from table for schema intelligence.

        Provides real data examples to help agents understand schema usage patterns.

        Args:
            table: Table name
            filters: Optional filters to narrow samples
            limit: Maximum rows to return (capped at 20)

        Returns:
            List of sample rows as dicts

        Raises:
            StorageError: On query failure or table not found
        """
        try:
            # Cap limit at 20 for safety
            safe_limit = min(limit, 20)

            client = await self._ensure_async_client()
            query = client.table(table).select("*")

            # Apply filters if provided
            if filters:
                for key, value in filters.items():
                    if isinstance(value, list):
                        query = query.in_(key, value)
                    else:
                        query = query.eq(key, value)

            # Fetch samples with limit
            response = await query.limit(safe_limit).execute()
            samples = response.data if response.data else []

            logger.debug(
                f"Fetched {len(samples)} samples from {table}",
                extra={"table": table, "filters": filters, "limit": safe_limit}
            )

            return samples

        except Exception as e:
            logger.error(
                f"Failed to sample data from {table}",
                exc_info=True,
                extra={"table": table, "filters": filters}
            )
            raise StorageError(
                message=f"Failed to sample data from {table}: {str(e)}",
                operation="sample_data",
                original_error=e,
            ) from e

    # ========================================================================
    # Transaction Support (Phase 3)
    # ========================================================================

    def transaction(self) -> SupabaseTransaction:
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
    # File Storage (Supabase Storage Buckets)
    # ========================================================================

    async def upload_asset(
        self,
        file_path: str,
        bucket: str = "assets",
        folder: str = "products",
        content_type: str | None = None,
    ) -> dict[str, Any]:
        """Upload file to Supabase Storage bucket.

        Used for persisting processed images after HITL approval.
        Follows pattern: bucket/folder/timestamp_uuid.ext

        Args:
            file_path: Local file path to upload
            bucket: Storage bucket name (default: "assets")
            folder: Folder within bucket (default: "products")
            content_type: MIME type (auto-detected if None)

        Returns:
            Dict with storage_path, public_url, size_bytes

        Raises:
            StorageError: On upload failure
            FileNotFoundError: If local file doesn't exist
        """
        import mimetypes
        import uuid
        from datetime import datetime
        from pathlib import Path

        try:
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

            # Upload to Supabase Storage
            client = self._ensure_client()
            client.storage.from_(bucket).upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": content_type},
            )

            # Get public URL
            public_url = client.storage.from_(bucket).get_public_url(storage_path)

            logger.info(
                f"Uploaded asset to {bucket}/{storage_path}",
                extra={
                    "bucket": bucket,
                    "storage_path": storage_path,
                    "size_bytes": len(file_content),
                    "content_type": content_type,
                }
            )

            return {
                "success": True,
                "storage_path": storage_path,
                "bucket": bucket,
                "public_url": public_url,
                "size_bytes": len(file_content),
                "content_type": content_type,
            }

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to upload asset to {bucket}/{folder}",
                exc_info=True,
                extra={"file_path": file_path, "bucket": bucket, "folder": folder}
            )
            raise StorageError(
                message=f"Asset upload failed: {str(e)}",
                operation="upload_asset",
                original_error=e,
            ) from e

    async def delete_asset(
        self,
        storage_path: str,
        bucket: str = "assets",
    ) -> bool:
        """Delete file from Supabase Storage bucket.

        Used for cleanup on HITL rejection or error recovery.

        Args:
            storage_path: Path within bucket (e.g., "products/20251130_abc123.png")
            bucket: Storage bucket name (default: "assets")

        Returns:
            True if deleted successfully

        Raises:
            StorageError: On delete failure
        """
        try:
            client = self._ensure_client()
            client.storage.from_(bucket).remove([storage_path])

            logger.info(
                f"Deleted asset from {bucket}/{storage_path}",
                extra={"bucket": bucket, "storage_path": storage_path}
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to delete asset from {bucket}/{storage_path}",
                exc_info=True,
                extra={"storage_path": storage_path, "bucket": bucket}
            )
            raise StorageError(
                message=f"Asset delete failed: {str(e)}",
                operation="delete_asset",
                original_error=e,
            ) from e

    def get_asset_public_url(
        self,
        storage_path: str,
        bucket: str = "assets",
    ) -> str:
        """Get public URL for stored asset.

        Args:
            storage_path: Path within bucket
            bucket: Storage bucket name

        Returns:
            Public URL for the asset
        """
        client = self._ensure_client()
        return client.storage.from_(bucket).get_public_url(storage_path)

    async def upload_to_inbox(
        self,
        file_bytes: bytes,
        thread_id: str,
        filename: str,
        content_type: str,
        bucket: str = "assets",
    ) -> dict[str, Any]:
        """Upload user-provided media to inbox folder.

        Used by WhatsApp channel for immediate persistence of user-uploaded images.
        No HITL required - user provided the image.

        Storage path: inbox/{sanitized_thread_id}/{filename}

        Args:
            file_bytes: Raw file content
            thread_id: Conversation thread ID (e.g., "whatsapp:123:919...")
            filename: Original or generated filename with extension
            content_type: MIME type (e.g., "image/jpeg")
            bucket: Storage bucket name (default: "assets")

        Returns:
            Dict with success, storage_path, bucket, public_url, size_bytes, content_type

        Raises:
            StorageError: On upload failure
        """
        return await self._upload_to_zone(
            zone="inbox",
            file_bytes=file_bytes,
            thread_id=thread_id,
            filename=filename,
            content_type=content_type,
            bucket=bucket,
        )

    async def upload_to_pending(
        self,
        file_bytes: bytes,
        thread_id: str,
        filename: str,
        content_type: str,
        bucket: str = "assets",
    ) -> dict[str, Any]:
        """Upload AI-generated media to pending folder.

        Used by Image Studio for generated/edited images awaiting HITL approval.
        Images in pending/ are moved to products/ on approval or deleted on rejection.

        Storage path: pending/{sanitized_thread_id}/{filename}

        Args:
            file_bytes: Raw file content
            thread_id: Conversation thread ID (e.g., "whatsapp:123:919...")
            filename: Generated filename with extension
            content_type: MIME type (e.g., "image/png")
            bucket: Storage bucket name (default: "assets")

        Returns:
            Dict with success, storage_path, bucket, public_url, size_bytes, content_type

        Raises:
            StorageError: On upload failure
        """
        return await self._upload_to_zone(
            zone="pending",
            file_bytes=file_bytes,
            thread_id=thread_id,
            filename=filename,
            content_type=content_type,
            bucket=bucket,
        )

    def _get_versioned_filename(
        self,
        client: Any,
        bucket: str,
        folder_path: str,
        filename: str,
    ) -> str:
        """Find next available versioned filename.

        Given 'image.png', checks for existing files and returns next version
        like 'image-v2.png', 'image-v3.png', etc.

        Args:
            client: Supabase client
            bucket: Storage bucket name
            folder_path: Folder path within bucket
            filename: Original filename

        Returns:
            Next available versioned filename
        """
        # Split filename into base and extension
        if "." in filename:
            base, ext = filename.rsplit(".", 1)
            ext = f".{ext}"
        else:
            base = filename
            ext = ""

        # List existing files in folder
        try:
            response = client.storage.from_(bucket).list(folder_path)
            existing_files = {item["name"] for item in response} if response else set()
        except Exception:
            existing_files = set()

        # Find next available version
        version = 2
        while version <= 100:  # Safety limit
            versioned_name = f"{base}-v{version}{ext}"
            if versioned_name not in existing_files:
                return versioned_name
            version += 1

        # Fallback to timestamp if too many versions
        import time
        return f"{base}-{int(time.time())}{ext}"

    async def _upload_to_zone(
        self,
        zone: str,
        file_bytes: bytes,
        thread_id: str,
        filename: str,
        content_type: str,
        bucket: str = "assets",
    ) -> dict[str, Any]:
        """Internal helper to upload to a specific zone (inbox or pending).

        Handles duplicates by appending version numbers (-v2, -v3, etc.) and
        returns metadata to inform the agent of the versioning.

        Args:
            zone: Storage zone ("inbox" or "pending")
            file_bytes: Raw file content
            thread_id: Conversation thread ID
            filename: Filename with extension
            content_type: MIME type
            bucket: Storage bucket name

        Returns:
            Dict with upload result including:
            - success, storage_path, bucket, public_url, size_bytes, content_type
            - filename: Actual filename used (may differ from input if versioned)
            - duplicate_detected: True if original filename already existed
            - original_filename: Original requested filename (if versioned)
            - warning: Human-readable message about versioning (if versioned)

        Raises:
            StorageError: On upload failure
        """
        try:
            # Sanitize thread_id for use as folder name
            sanitized_thread_id = sanitize_for_path(thread_id)
            folder_path = f"{zone}/{sanitized_thread_id}"
            storage_path = f"{folder_path}/{filename}"

            client = self._ensure_client()

            # Track if we need to version the filename
            duplicate_detected = False
            original_filename = filename
            actual_filename = filename

            # Try upload - if duplicate, version the filename
            try:
                client.storage.from_(bucket).upload(
                    path=storage_path,
                    file=file_bytes,
                    file_options={"content-type": content_type},
                )
            except Exception as upload_error:
                # Check if it's a duplicate error (409)
                error_str = str(upload_error)
                if "409" in error_str or "Duplicate" in error_str or "already exists" in error_str.lower():
                    duplicate_detected = True

                    # Find next available version
                    actual_filename = self._get_versioned_filename(
                        client, bucket, folder_path, filename
                    )
                    storage_path = f"{folder_path}/{actual_filename}"

                    # Upload with versioned filename
                    client.storage.from_(bucket).upload(
                        path=storage_path,
                        file=file_bytes,
                        file_options={"content-type": content_type},
                    )

                    logger.warning(
                        "Duplicate detected, using versioned filename",
                        extra={
                            "original_filename": original_filename,
                            "versioned_filename": actual_filename,
                            "folder_path": folder_path,
                        }
                    )
                else:
                    raise  # Re-raise if it's not a duplicate error

            # Get public URL
            public_url = client.storage.from_(bucket).get_public_url(storage_path)

            logger.info(
                f"Uploaded to {zone}: {bucket}/{storage_path}",
                extra={
                    "zone": zone,
                    "bucket": bucket,
                    "storage_path": storage_path,
                    "thread_id": thread_id,
                    "size_bytes": len(file_bytes),
                    "content_type": content_type,
                    "duplicate_detected": duplicate_detected,
                }
            )

            result: dict[str, Any] = {
                "success": True,
                "storage_path": storage_path,
                "bucket": bucket,
                "public_url": public_url,
                "size_bytes": len(file_bytes),
                "content_type": content_type,
                "filename": actual_filename,
            }

            if duplicate_detected:
                result["duplicate_detected"] = True
                result["original_filename"] = original_filename
                result["warning"] = (
                    f"File '{original_filename}' already existed. "
                    f"Saved as '{actual_filename}' instead."
                )

            return result

        except Exception as e:
            logger.error(
                f"Failed to upload to {zone}: {bucket}/{zone}/{thread_id}",
                exc_info=True,
                extra={
                    "zone": zone,
                    "thread_id": thread_id,
                    "file_name": filename,  # Renamed: 'filename' conflicts with LogRecord
                    "bucket": bucket,
                }
            )
            raise StorageError(
                message=f"Upload to {zone} failed: {str(e)}",
                operation=f"upload_to_{zone}",
                original_error=e,
            ) from e

    async def move_asset(
        self,
        source_path: str,
        target_folder: str,
        bucket: str = "assets",
    ) -> dict[str, Any]:
        """Move asset from one folder to another within same bucket.

        Used by WriteIntent executor to move approved images:
        - pending/{thread_id}/file.png -> products/file.png

        Implementation: Download + Upload + Delete (Supabase doesn't have native move)

        Args:
            source_path: Current path within bucket (e.g., "pending/thread/file.png")
            target_folder: Target folder (e.g., "products")
            bucket: Storage bucket name (default: "assets")

        Returns:
            Dict with success, storage_path, bucket, public_url, size_bytes, content_type, file_name

        Raises:
            StorageError: On move failure
            FileNotFoundError: If source doesn't exist
        """
        import mimetypes
        import uuid
        from datetime import datetime
        from pathlib import Path

        try:
            client = self._ensure_client()

            # Download the source file
            try:
                file_bytes = client.storage.from_(bucket).download(source_path)
            except Exception as download_error:
                if "not found" in str(download_error).lower():
                    raise FileNotFoundError(f"Source file not found: {source_path}") from download_error
                raise

            # Generate new filename in target folder
            source_filename = Path(source_path).name
            extension = Path(source_filename).suffix.lower()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            new_filename = f"{timestamp}_{unique_id}{extension}"
            target_path = f"{target_folder}/{new_filename}"

            # Detect content type
            content_type, _ = mimetypes.guess_type(source_filename)
            content_type = content_type or "application/octet-stream"

            # Upload to target location
            client.storage.from_(bucket).upload(
                path=target_path,
                file=file_bytes,
                file_options={"content-type": content_type},
            )

            # Delete source file
            client.storage.from_(bucket).remove([source_path])

            # Get public URL
            public_url = client.storage.from_(bucket).get_public_url(target_path)

            logger.info(
                f"Moved asset: {source_path} -> {target_path}",
                extra={
                    "source_path": source_path,
                    "target_path": target_path,
                    "bucket": bucket,
                    "size_bytes": len(file_bytes),
                }
            )

            return {
                "success": True,
                "storage_path": target_path,
                "bucket": bucket,
                "public_url": public_url,
                "size_bytes": len(file_bytes),
                "content_type": content_type,
                "file_name": new_filename,
            }

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to move asset: {source_path} -> {target_folder}",
                exc_info=True,
                extra={
                    "source_path": source_path,
                    "target_folder": target_folder,
                    "bucket": bucket,
                }
            )
            raise StorageError(
                message=f"Asset move failed: {str(e)}",
                operation="move_asset",
                original_error=e,
            ) from e

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

    async def __aenter__(self) -> SupabaseTransaction:
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
