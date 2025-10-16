"""Integration tests for WhatsApp webhook entry point.

Tests the FastAPI webhook endpoints with various WhatsApp event payloads,
idempotency handling, error recovery, and message processing.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from autifyme_agents.core.config import settings
from autifyme_agents.entrypoints.whatsapp_webhook import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_storage(mock_storage):
    """Use conftest mock_storage with reset check_and_mark_message_processed."""
    # Reset the idempotency check to return False (not duplicate) by default
    mock_storage.check_and_mark_message_processed = Mock(return_value=False)
    return mock_storage


@pytest.fixture(autouse=True)
def mock_runner_globally():
    """Mock WorkflowRunner globally to isolate webhook layer."""
    # Create mock storage first
    mock_storage = Mock()
    mock_storage.check_and_mark_message_processed = Mock(return_value=False)

    # Create mock runner
    mock_runner = Mock()
    mock_runner.handle_message = Mock()

    with patch('autifyme_agents.entrypoints.whatsapp_webhook.WorkflowRunner') as mock_runner_class:
        mock_runner_class.return_value = mock_runner

        with patch('autifyme_agents.entrypoints.whatsapp_webhook.get_storage') as mock_get_storage:
            mock_get_storage.return_value = mock_storage

            # Also patch the global _storage variable
            with patch('autifyme_agents.entrypoints.whatsapp_webhook._storage', mock_storage):

                # Patch the global _runner variable to avoid lazy initialization
                with patch('autifyme_agents.entrypoints.whatsapp_webhook._runner', mock_runner):

                    with patch('autifyme_agents.entrypoints.whatsapp_webhook.WhatsAppChannel') as mock_channel:
                        mock_channel_instance = Mock()
                        mock_channel_instance.format_thread_id = Mock(return_value="whatsapp:1234567890")
                        mock_channel.return_value = mock_channel_instance

                        # Also patch the global _whatsapp_channel variable
                        with patch('autifyme_agents.entrypoints.whatsapp_webhook._whatsapp_channel', mock_channel_instance):

                            yield {
                                'runner': mock_runner,
                                'runner_class': mock_runner_class,
                                'storage': mock_storage,
                                'channel': mock_channel_instance,
                            }


class TestHealthEndpoints:
    """Test health check and status endpoints."""

    def test_root_endpoint(self, client):
        """Root endpoint returns service status."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "service": "AutifyME WhatsApp Webhook"
        }

    def test_health_check(self, client):
        """Health check endpoint for load balancers."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "healthy",
            "service": "autifyme-webhook"
        }


class TestWebhookVerification:
    """Test GET /webhook verification endpoint."""

    def test_valid_verification_request(self, client):
        """Valid verification request returns challenge."""
        response = client.get(
            "/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "test_challenge_12345",
                "hub.verify_token": settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN,
            },
        )
        assert response.status_code == 200
        assert response.text == "test_challenge_12345"

    def test_invalid_verify_token(self, client):
        """Invalid token returns 403."""
        response = client.get(
            "/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "test_challenge_12345",
                "hub.verify_token": "wrong_token",
            },
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Verification failed"

    def test_missing_challenge(self, client):
        """Missing challenge parameter returns 403."""
        response = client.get(
            "/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN,
            },
        )
        assert response.status_code == 403

    def test_wrong_mode(self, client):
        """Wrong hub.mode returns 403."""
        response = client.get(
            "/webhook",
            params={
                "hub.mode": "unsubscribe",
                "hub.challenge": "test_challenge_12345",
                "hub.verify_token": settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN,
            },
        )
        assert response.status_code == 403


class TestMessageReception:
    """Test POST /webhook message processing."""

    def test_text_message(self, client, mock_runner_globally):
        """Text message is extracted and processed."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "entry123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "messages": [
                                    {
                                        "id": "msg_001",
                                        "from": "1234567890",
                                        "timestamp": "1234567890",
                                        "type": "text",
                                        "text": {"body": "Hello, I need help cataloging a product"},
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }

        with patch('autifyme_agents.entrypoints.whatsapp_webhook._persist_event') as mock_persist:
            mock_persist.return_value = Path("/tmp/test_event.json")
            response = client.post("/webhook", json=payload)

        assert response.status_code == 200
        assert response.json() == {"status": "processed"}

        # Verify handle_message was called with correct args
        mock_runner_globally['runner'].handle_message.assert_called_once_with(
            "1234567890",
            "Hello, I need help cataloging a product",
            None,  # No media
            sender_name=None,
        )

    def test_image_with_caption(self, client, mock_runner_globally):
        """Image with caption extracts both media_id and text."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "entry123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "messages": [
                                    {
                                        "id": "msg_002",
                                        "from": "1234567890",
                                        "timestamp": "1234567890",
                                        "type": "image",
                                        "image": {
                                            "id": "media_abc123",
                                            "caption": "Catalog this jar",
                                        },
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }

        with patch('autifyme_agents.entrypoints.whatsapp_webhook._persist_event') as mock_persist:
            mock_persist.return_value = Path("/tmp/test_event.json")
            response = client.post("/webhook", json=payload)

        assert response.status_code == 200
        mock_runner_globally['runner'].handle_message.assert_called_once_with(
            "1234567890",
            "Catalog this jar",
            "media_abc123",
            sender_name=None,
        )

    def test_image_without_caption(self, client, mock_runner_globally):
        """Image without caption sends media_id only."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "entry123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "messages": [
                                    {
                                        "id": "msg_003",
                                        "from": "1234567890",
                                        "timestamp": "1234567890",
                                        "type": "image",
                                        "image": {
                                            "id": "media_xyz789",
                                        },
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }

        with patch('autifyme_agents.entrypoints.whatsapp_webhook._persist_event') as mock_persist:
            mock_persist.return_value = Path("/tmp/test_event.json")
            response = client.post("/webhook", json=payload)

        assert response.status_code == 200
        mock_runner_globally['runner'].handle_message.assert_called_once_with(
            "1234567890",
            None,  # No caption
            "media_xyz789",
            sender_name=None,
        )

    def test_video_with_caption(self, client, mock_runner_globally):
        """Video with caption extracts both."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "entry123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "messages": [
                                    {
                                        "id": "msg_004",
                                        "from": "1234567890",
                                        "timestamp": "1234567890",
                                        "type": "video",
                                        "video": {
                                            "id": "video_123",
                                            "caption": "Product demo video",
                                        },
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }

        with patch('autifyme_agents.entrypoints.whatsapp_webhook._persist_event') as mock_persist:
            mock_persist.return_value = Path("/tmp/test_event.json")
            response = client.post("/webhook", json=payload)

        assert response.status_code == 200
        mock_runner_globally['runner'].handle_message.assert_called_once_with(
            "1234567890",
            "Product demo video",
            "video_123",
            sender_name=None,
        )

    def test_document_with_caption(self, client, mock_runner_globally):
        """Document with caption extracts both."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "entry123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "messages": [
                                    {
                                        "id": "msg_005",
                                        "from": "1234567890",
                                        "timestamp": "1234567890",
                                        "type": "document",
                                        "document": {
                                            "id": "doc_456",
                                            "caption": "Price list",
                                            "filename": "prices.pdf",
                                        },
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }

        with patch('autifyme_agents.entrypoints.whatsapp_webhook._persist_event') as mock_persist:
            mock_persist.return_value = Path("/tmp/test_event.json")
            response = client.post("/webhook", json=payload)

        assert response.status_code == 200
        mock_runner_globally['runner'].handle_message.assert_called_once_with(
            "1234567890",
            "Price list",
            "doc_456",
            sender_name=None,
        )

    def test_audio_message(self, client, mock_runner_globally):
        """Audio message (no caption support) sends media_id only."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "entry123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "messages": [
                                    {
                                        "id": "msg_006",
                                        "from": "1234567890",
                                        "timestamp": "1234567890",
                                        "type": "audio",
                                        "audio": {
                                            "id": "audio_789",
                                        },
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }

        with patch('autifyme_agents.entrypoints.whatsapp_webhook._persist_event') as mock_persist:
            mock_persist.return_value = Path("/tmp/test_event.json")
            response = client.post("/webhook", json=payload)

        assert response.status_code == 200
        mock_runner_globally['runner'].handle_message.assert_called_once_with(
            "1234567890",
            None,  # Audio has no caption
            "audio_789",
            sender_name=None,
        )

    def test_text_message_with_sender_name(self, client, mock_runner_globally):
        """Text message with contacts array extracts sender_name for personalization."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "entry123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "contacts": [
                                    {
                                        "profile": {
                                            "name": "Abhi"
                                        },
                                        "wa_id": "1234567890"
                                    }
                                ],
                                "messages": [
                                    {
                                        "id": "msg_007",
                                        "from": "1234567890",
                                        "timestamp": "1234567890",
                                        "type": "text",
                                        "text": {"body": "Hi, catalog this for me"},
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }

        with patch('autifyme_agents.entrypoints.whatsapp_webhook._persist_event') as mock_persist:
            mock_persist.return_value = Path("/tmp/test_event.json")
            response = client.post("/webhook", json=payload)

        assert response.status_code == 200
        # Verify sender_name was extracted from contacts array
        mock_runner_globally['runner'].handle_message.assert_called_once_with(
            "1234567890",
            "Hi, catalog this for me",
            None,
            sender_name="Abhi",
        )

    def test_image_with_sender_name(self, client, mock_runner_globally):
        """Image message with contacts array includes sender_name."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "entry123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "contacts": [
                                    {
                                        "profile": {
                                            "name": "John Doe"
                                        },
                                        "wa_id": "9876543210"
                                    }
                                ],
                                "messages": [
                                    {
                                        "id": "msg_008",
                                        "from": "9876543210",
                                        "timestamp": "1234567890",
                                        "type": "image",
                                        "image": {
                                            "id": "media_personalized",
                                            "caption": "Check out this product",
                                        },
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }

        with patch('autifyme_agents.entrypoints.whatsapp_webhook._persist_event') as mock_persist:
            mock_persist.return_value = Path("/tmp/test_event.json")
            response = client.post("/webhook", json=payload)

        assert response.status_code == 200
        # Verify sender_name was extracted
        mock_runner_globally['runner'].handle_message.assert_called_once_with(
            "9876543210",
            "Check out this product",
            "media_personalized",
            sender_name="John Doe",
        )


class TestEventFiltering:
    """Test filtering of non-message events."""

    def test_status_update_ignored(self, client, mock_runner_globally):
        """Status update events are ignored."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "entry123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "statuses": [
                                    {
                                        "id": "msg_001",
                                        "status": "delivered",
                                        "timestamp": "1234567890",
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }

        with patch('autifyme_agents.entrypoints.whatsapp_webhook._persist_event') as mock_persist:
            mock_persist.return_value = Path("/tmp/test_event.json")
            response = client.post("/webhook", json=payload)

        assert response.status_code == 200
        # handle_message should NOT be called for status updates
        mock_runner_globally['runner'].handle_message.assert_not_called()

    def test_non_message_event_ignored(self, client, mock_runner_globally):
        """Other event types without messages are ignored."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "entry123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                # No messages, no statuses - some other event type
                            },
                        }
                    ],
                }
            ],
        }

        with patch('autifyme_agents.entrypoints.whatsapp_webhook._persist_event') as mock_persist:
            mock_persist.return_value = Path("/tmp/test_event.json")
            response = client.post("/webhook", json=payload)

        assert response.status_code == 200
        mock_runner_globally['runner'].handle_message.assert_not_called()

    def test_multiple_messages_in_payload(self, client, mock_runner_globally):
        """Multiple messages in one payload are all processed."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "entry123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "messages": [
                                    {
                                        "id": "msg_001",
                                        "from": "1234567890",
                                        "timestamp": "1234567890",
                                        "type": "text",
                                        "text": {"body": "First message"},
                                    },
                                    {
                                        "id": "msg_002",
                                        "from": "1234567890",
                                        "timestamp": "1234567891",
                                        "type": "text",
                                        "text": {"body": "Second message"},
                                    },
                                ],
                            },
                        }
                    ],
                }
            ],
        }

        with patch('autifyme_agents.entrypoints.whatsapp_webhook._persist_event') as mock_persist:
            mock_persist.return_value = Path("/tmp/test_event.json")
            response = client.post("/webhook", json=payload)

        assert response.status_code == 200
        # Should be called twice
        assert mock_runner_globally['runner'].handle_message.call_count == 2


class TestIdempotency:
    """Test duplicate message handling with DB-backed idempotency."""

    def test_duplicate_message_skipped(self, client, mock_runner_globally):
        """Duplicate message_id is skipped (DB returns True)."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "entry123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "messages": [
                                    {
                                        "id": "msg_duplicate_123",
                                        "from": "1234567890",
                                        "timestamp": "1234567890",
                                        "type": "text",
                                        "text": {"body": "Duplicate message"},
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }

        # Mock storage to return True (duplicate)
        mock_runner_globally['storage'].check_and_mark_message_processed = Mock(return_value=True)

        with patch('autifyme_agents.entrypoints.whatsapp_webhook._persist_event') as mock_persist:
            mock_persist.return_value = Path("/tmp/test_event.json")
            response = client.post("/webhook", json=payload)

        assert response.status_code == 200
        # handle_message should NOT be called for duplicates
        mock_runner_globally['runner'].handle_message.assert_not_called()

    def test_missing_message_id_skipped(self, client, mock_runner_globally):
        """Message without message_id is skipped with warning."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "entry123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "messages": [
                                    {
                                        # Missing "id"
                                        "from": "1234567890",
                                        "timestamp": "1234567890",
                                        "type": "text",
                                        "text": {"body": "No ID message"},
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }

        with patch('autifyme_agents.entrypoints.whatsapp_webhook._persist_event') as mock_persist:
            mock_persist.return_value = Path("/tmp/test_event.json")
            response = client.post("/webhook", json=payload)

        assert response.status_code == 200
        # handle_message should NOT be called
        mock_runner_globally['runner'].handle_message.assert_not_called()

    def test_missing_sender_skipped(self, client, mock_runner_globally):
        """Message without sender is skipped with warning."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "entry123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "messages": [
                                    {
                                        "id": "msg_no_sender",
                                        # Missing "from"
                                        "timestamp": "1234567890",
                                        "type": "text",
                                        "text": {"body": "No sender message"},
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }

        with patch('autifyme_agents.entrypoints.whatsapp_webhook._persist_event') as mock_persist:
            mock_persist.return_value = Path("/tmp/test_event.json")
            response = client.post("/webhook", json=payload)

        assert response.status_code == 200
        mock_runner_globally['runner'].handle_message.assert_not_called()


class TestErrorRecovery:
    """Test error handling and recovery scenarios."""

    def test_workflow_exception_continues_processing(self, client, mock_runner_globally):
        """Workflow exception doesn't stop other messages from processing."""
        # Make handle_message raise exception
        mock_runner_globally['runner'].handle_message = Mock(side_effect=Exception("Workflow error"))

        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "entry123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "messages": [
                                    {
                                        "id": "msg_error",
                                        "from": "1234567890",
                                        "timestamp": "1234567890",
                                        "type": "text",
                                        "text": {"body": "This will error"},
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }

        with patch('autifyme_agents.entrypoints.whatsapp_webhook._persist_event') as mock_persist:
            mock_persist.return_value = Path("/tmp/test_event.json")
            response = client.post("/webhook", json=payload)

        # Should still return 200 (error logged, not raised)
        assert response.status_code == 200
        assert response.json() == {"status": "processed"}

    def test_generator_exit_continues_processing(self, client, mock_runner_globally):
        """GeneratorExit (timeout) doesn't stop processing."""
        # Make handle_message raise GeneratorExit
        mock_runner_globally['runner'].handle_message = Mock(side_effect=GeneratorExit())

        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "entry123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "messages": [
                                    {
                                        "id": "msg_timeout",
                                        "from": "1234567890",
                                        "timestamp": "1234567890",
                                        "type": "text",
                                        "text": {"body": "This will timeout"},
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }

        with patch('autifyme_agents.entrypoints.whatsapp_webhook._persist_event') as mock_persist:
            mock_persist.return_value = Path("/tmp/test_event.json")
            response = client.post("/webhook", json=payload)

        assert response.status_code == 200
        assert response.json() == {"status": "processed"}


class TestObservability:
    """Test event persistence and logging."""

    def test_event_persistence(self, client, mock_runner_globally):
        """Events are persisted to /tmp/whatsapp_events/."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "entry123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "messages": [
                                    {
                                        "id": "msg_persist",
                                        "from": "1234567890",
                                        "timestamp": "1234567890",
                                        "type": "text",
                                        "text": {"body": "Test persistence"},
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }

        with patch('autifyme_agents.entrypoints.whatsapp_webhook._persist_event') as mock_persist:
            mock_persist.return_value = Path("/tmp/whatsapp_events/event_test.json")
            response = client.post("/webhook", json=payload)

        assert response.status_code == 200
        # Verify _persist_event was called with payload
        mock_persist.assert_called_once_with(payload)
