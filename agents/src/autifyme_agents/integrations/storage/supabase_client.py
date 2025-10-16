"""Supabase-backed implementation of the storage port."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from supabase import Client, create_client

from autifyme_agents.core.config import settings
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.schemas.models import CompanyProfile, Product

logger = logging.getLogger(__name__)


class SupabaseStorageClient(StorageInterface):
    """Concrete adapter that persists and retrieves catalog data via Supabase.

    The class adheres to the `StorageInterface` contract so the rest of the
    application depends on a stable port rather than Supabase specifics. A
    single instance should be reused within a workflow run to avoid creating
    redundant network clients.
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

    def _ensure_client(self) -> Client:
        """Create the Supabase client lazily to avoid side effects during import."""

        if self._client is None:
            self._client = create_client(self._supabase_url, self._service_key)
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

    def save_pending_approval(
        self,
        thread_id: str,
        interrupt_id: str,
        checkpoint_id: str,
        tool_call: dict[str, Any],
        draft_summary: str,
        ai_message: dict[str, Any] | None = None,
        image_path: str | None = None,
        agent_source: str = "cataloging_department",
        checkpoint_ns: str | None = None,
    ) -> str:
        """Persist a pending HITL approval to the pending_approvals table."""

        client = self._ensure_client()
        expires_at = datetime.now(UTC) + timedelta(hours=24)
        payload = {
            "thread_id": thread_id,
            "interrupt_id": interrupt_id,
            "checkpoint_id": checkpoint_id,
            "tool_call": tool_call,
            "draft_summary": draft_summary,
            "ai_message": ai_message,
            "image_path": image_path,
            "agent_source": agent_source,
            "checkpoint_ns": checkpoint_ns,
            "expires_at": expires_at.isoformat(),
        }

        # Upsert to handle duplicate interrupts (e.g., retry scenarios)
        response = (
            client.table("pending_approvals")
            .upsert(payload, on_conflict="thread_id,interrupt_id")
            .execute()
        )

        if not response.data:
            raise RuntimeError("Failed to persist pending approval; inspect Supabase response for details.")

        approval_id: str = response.data[0]["id"]
        return approval_id

    def get_pending_approval(self, thread_id: str) -> dict[str, Any] | None:
        """Retrieve the most recent non-expired pending approval for a thread.

        Filters out approvals past their expires_at timestamp (24h default) to prevent
        processing stale approval requests and ensure users get clear "no pending approval"
        messages instead of resuming outdated workflows.
        """

        client = self._ensure_client()
        now = datetime.now(UTC).isoformat()

        response = (
            client.table("pending_approvals")
            .select("*")
            .eq("thread_id", thread_id)
            .gt("expires_at", now)  # Only non-expired approvals
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        approval_data: dict[str, Any] = response.data[0]
        return approval_data

    def delete_pending_approval(self, thread_id: str) -> bool:
        """Delete all pending approvals for a thread (handles approve/reject)."""

        client = self._ensure_client()
        response = client.table("pending_approvals").delete().eq("thread_id", thread_id).execute()

        # Supabase delete returns the deleted rows; if empty, nothing was deleted
        return bool(response.data)

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
        race conditions. Fail-open strategy: if DB check fails, allow processing
        to prevent webhook blocking.

        Args:
            message_id: WhatsApp message ID (unique across retries)
            sender_id: Phone number
            thread_id: LangGraph thread ID
            received_at: When webhook was received

        Returns:
            True if duplicate (already processed), False if new (now marked as processed)
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
            # Fail OPEN (allow processing) if DB check fails to prevent webhook blocking
            logger.exception(
                "Idempotency check failed - allowing processing (fail open)",
                exc_info=exc,
                extra={
                    "message_id": message_id,
                    "error_type": type(exc).__name__,
                },
            )
            return False  # Process the message (risk: potential duplicate)

    # ========================================================================
    # Phase 1.2: Workflow Outcome Tracking (Agentic Evolution)
    # ========================================================================

    def save_workflow_outcome(self, outcome: dict[str, Any]) -> str:
        """Persist workflow outcome for learning and analytics."""
        client = self._ensure_client()

        # Ensure timestamps are ISO strings for Supabase
        payload = outcome.copy()
        for ts_field in ["received_at", "routed_at", "started_at", "ended_at"]:
            if ts_field in payload and isinstance(payload[ts_field], datetime):
                payload[ts_field] = payload[ts_field].isoformat()

        response = client.table("workflow_outcomes").insert(payload).execute()

        if not response.data:
            raise RuntimeError(
                "Failed to persist workflow outcome; inspect Supabase response for details."
            )

        logger.info(
            "Persisted workflow outcome",
            extra={
                "tracking_id": outcome.get("tracking_id"),
                "success": outcome.get("success"),
            },
        )

        outcome_id: str = response.data[0]["id"]
        return outcome_id

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
