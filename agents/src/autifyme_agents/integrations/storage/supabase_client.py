"""Supabase-backed implementation of the storage port."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from supabase import Client, create_client

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
                # Create client
                self._client = create_client(self._supabase_url, self._service_key)

                # Test connection with simple query to validate credentials
                # Use companies table as it's fundamental to single-tenant architecture
                _ = self._client.table("companies").select("id").limit(1).execute()

                # If we get here, connection is valid (even if no data exists yet)
                logger.info(
                    "Supabase client initialized and connection validated",
                    extra={
                        "url": self._supabase_url[:30] + "...",  # Log partial URL for security
                        "has_service_key": bool(self._service_key),
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

    def cleanup(self) -> None:
        """Close internal HTTP connections gracefully.

        The Supabase Python client doesn't provide native cleanup methods,
        but uses httpx.Client internally for all HTTP operations. This method
        closes those internal clients to prevent connection leaks.

        Call this on application shutdown or when the storage adapter is no
        longer needed. Safe to call multiple times (idempotent).
        """
        if self._client is None:
            return  # No client to cleanup

        try:
            # Close PostgREST client (database operations)
            if hasattr(self._client.postgrest, 'session'):
                self._client.postgrest.session.close()
                logger.debug("Closed PostgREST HTTP client")
        except Exception as e:
            logger.warning(f"Failed to close PostgREST client: {e}")

        try:
            # Close Storage client (file operations)
            if hasattr(self._client.storage, '_client'):
                self._client.storage._client.close()
                logger.debug("Closed Storage HTTP client")
        except Exception as e:
            logger.warning(f"Failed to close Storage client: {e}")

        try:
            # Close Functions client (edge function operations)
            if hasattr(self._client.functions, '_client'):
                self._client.functions._client.close()
                logger.debug("Closed Functions HTTP client")
        except Exception as e:
            logger.warning(f"Failed to close Functions client: {e}")

        logger.info("Supabase storage client cleanup completed")
