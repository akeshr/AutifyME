"""Unit tests for StateManager.

Testing strategy: Mock StorageInterface and verify StateManager delegates correctly.
"""

import pytest
from unittest.mock import create_autospec, MagicMock

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.workflows.orchestration.state_manager import StateManager
from autifyme_agents.schemas.models import Product


@pytest.fixture
def mock_storage():
    """Fixture providing a mock storage adapter."""
    return create_autospec(StorageInterface, instance=True)


@pytest.fixture
def state_manager(mock_storage):
    """Fixture providing a StateManager with mocked storage."""
    return StateManager(mock_storage)


@pytest.fixture
def sample_draft():
    """Fixture providing a sample product draft."""
    return Product(
        id="test-product-1",
        name="Test Product",
        description="A test product",
        price=99.99,
        sizes=["M", "L"],
    )


class TestStateManagerInit:
    """Tests for StateManager initialization."""

    def test_init_with_storage(self, mock_storage):
        """StateManager should initialize with storage adapter."""
        manager = StateManager(mock_storage)

        assert manager.storage is mock_storage

    def test_init_requires_storage(self):
        """StateManager should require storage adapter."""
        with pytest.raises(TypeError):
            StateManager()  # Missing required argument


class TestStateManagerSavePendingApproval:
    """Tests for save_pending_approval method."""

    def test_save_pending_approval_basic(self, state_manager, mock_storage, sample_draft):
        """Should delegate to storage with correct parameters."""
        thread_id = "test-thread-123"
        approval_data = MagicMock()
        approval_data.interrupt_id = "int-1"
        approval_data.checkpoint_id = "checkpoint-1"
        approval_data.tool_call = {"name": "save_product"}
        approval_data.draft = sample_draft
        approval_data.ai_message = {"type": "ai", "content": ""}

        state_manager.save_pending_approval(
            thread_id=thread_id,
            approval_data=approval_data,
            media_path=None,
        )

        # Verify storage was called
        mock_storage.save_pending_approval.assert_called_once()

        # Verify call arguments
        call_args = mock_storage.save_pending_approval.call_args
        assert call_args.kwargs["thread_id"] == thread_id
        assert call_args.kwargs["interrupt_id"] == "int-1"

    def test_save_pending_approval_with_media(self, state_manager, mock_storage, sample_draft):
        """Should handle media path parameter."""
        thread_id = "test-thread-123"
        approval_data = MagicMock()
        approval_data.interrupt_id = "int-1"
        approval_data.checkpoint_id = None
        approval_data.tool_call = {"name": "save_product"}
        approval_data.draft = sample_draft
        approval_data.ai_message = None

        state_manager.save_pending_approval(
            thread_id=thread_id,
            approval_data=approval_data,
            media_path="/tmp/image.jpg",
        )

        call_args = mock_storage.save_pending_approval.call_args
        assert call_args.kwargs["image_path"] == "/tmp/image.jpg"


class TestStateManagerGetPendingApproval:
    """Tests for get_pending_approval method."""

    def test_get_pending_approval_exists(self, state_manager, mock_storage):
        """Should return approval data when it exists."""
        thread_id = "test-thread-123"
        expected_data = {"interrupt_id": "int-1", "tool_call": {}}

        mock_storage.get_pending_approval.return_value = expected_data

        result = state_manager.get_pending_approval(thread_id)

        assert result == expected_data
        mock_storage.get_pending_approval.assert_called_once_with(thread_id)

    def test_get_pending_approval_not_exists(self, state_manager, mock_storage):
        """Should return None when no approval exists."""
        thread_id = "test-thread-123"
        mock_storage.get_pending_approval.return_value = None

        result = state_manager.get_pending_approval(thread_id)

        assert result is None


class TestStateManagerHasPendingApproval:
    """Tests for has_pending_approval method."""

    def test_has_pending_approval_true(self, state_manager, mock_storage):
        """Should return True when approval exists."""
        thread_id = "test-thread-123"
        mock_storage.get_pending_approval.return_value = {"interrupt_id": "int-1"}

        result = state_manager.has_pending_approval(thread_id)

        assert result is True

    def test_has_pending_approval_false(self, state_manager, mock_storage):
        """Should return False when no approval exists."""
        thread_id = "test-thread-123"
        mock_storage.get_pending_approval.return_value = None

        result = state_manager.has_pending_approval(thread_id)

        assert result is False


class TestStateManagerDeletePendingApproval:
    """Tests for delete_pending_approval method."""

    def test_delete_pending_approval(self, state_manager, mock_storage):
        """Should delegate to storage for deletion."""
        thread_id = "test-thread-123"

        state_manager.delete_pending_approval(thread_id)

        mock_storage.delete_pending_approval.assert_called_once_with(thread_id)


class TestStateManagerIntegration:
    """Integration-style tests verifying full workflows."""

    def test_save_retrieve_delete_cycle(self, state_manager, mock_storage, sample_draft):
        """Should handle full approval lifecycle."""
        thread_id = "test-thread-123"

        # Setup mock to return saved data after save
        saved_data = {"interrupt_id": "int-1"}
        mock_storage.get_pending_approval.return_value = saved_data

        # Save
        approval_data = MagicMock()
        approval_data.interrupt_id = "int-1"
        approval_data.checkpoint_id = None
        approval_data.tool_call = {"name": "save_product"}
        approval_data.draft = sample_draft
        approval_data.ai_message = None

        state_manager.save_pending_approval(thread_id, approval_data)

        # Retrieve
        result = state_manager.get_pending_approval(thread_id)
        assert result == saved_data

        # Check existence
        assert state_manager.has_pending_approval(thread_id) is True

        # Delete
        mock_storage.get_pending_approval.return_value = None
        state_manager.delete_pending_approval(thread_id)

        # Verify deleted
        assert state_manager.has_pending_approval(thread_id) is False
