from abc import ABC, abstractmethod
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
