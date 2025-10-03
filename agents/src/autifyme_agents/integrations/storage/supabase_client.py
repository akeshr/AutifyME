"""Supabase-backed implementation of the storage port."""

from __future__ import annotations

import logging
from typing import Optional

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
        supabase_url: Optional[str] = None,
        service_key: Optional[str] = None,
        client: Optional[Client] = None,
    ) -> None:
        """Configure the adapter with explicit or settings-derived credentials."""

        self._supabase_url = supabase_url or settings.SUPABASE_URL
        derived_key = service_key or settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
        if settings.SUPABASE_SERVICE_ROLE_KEY is None and service_key is None:
            logger.warning(
                "SUPABASE_SERVICE_ROLE_KEY not set; falling back to anon key which has restricted write access."
            )
        self._service_key = derived_key
        self._client: Optional[Client] = client

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
        """Persist a product record using an idempotent upsert operation."""

        client = self._ensure_client()
        product_payload = product.model_dump(mode="json")
        response = client.table("products").upsert(product_payload).execute()

        if not response.data:
            raise RuntimeError("Storage adapter failed to persist product; inspect Supabase response for details.")

        return Product.model_validate(response.data[0])

    def save_pending_approval(
        self,
        thread_id: str,
        interrupt_id: str,
        checkpoint_id: str,
        tool_call: dict,
        draft_summary: str,
        ai_message: Optional[dict] = None,
    ) -> str:
        """Persist a pending HITL approval to the pending_approvals table."""

        client = self._ensure_client()
        payload = {
            "thread_id": thread_id,
            "interrupt_id": interrupt_id,
            "checkpoint_id": checkpoint_id,
            "tool_call": tool_call,
            "draft_summary": draft_summary,
            "ai_message": ai_message,
        }
        
        # Upsert to handle duplicate interrupts (e.g., retry scenarios)
        response = (
            client.table("pending_approvals")
            .upsert(payload, on_conflict="thread_id,interrupt_id")
            .execute()
        )

        if not response.data:
            raise RuntimeError("Failed to persist pending approval; inspect Supabase response for details.")

        return response.data[0]["id"]

    def get_pending_approval(self, thread_id: str) -> Optional[dict]:
        """Retrieve the most recent pending approval for a thread."""

        client = self._ensure_client()
        response = (
            client.table("pending_approvals")
            .select("*")
            .eq("thread_id", thread_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        return response.data[0]

    def delete_pending_approval(self, thread_id: str) -> bool:
        """Delete all pending approvals for a thread (handles approve/reject)."""

        client = self._ensure_client()
        response = client.table("pending_approvals").delete().eq("thread_id", thread_id).execute()

        # Supabase delete returns the deleted rows; if empty, nothing was deleted
        return bool(response.data)