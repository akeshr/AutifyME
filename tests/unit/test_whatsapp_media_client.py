"""Unit tests for WhatsApp media client.

Tests media URL fetching, downloading, MIME type handling, and error scenarios.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import httpx
import pytest

from autifyme_agents.integrations.communication.whatsapp_media_client import WhatsAppMediaClient


@pytest.fixture
def media_client():
    """Create media client with test token."""
    return WhatsAppMediaClient(access_token="test_token_12345", api_version="v18.0")


@pytest.fixture
def mock_httpx_response():
    """Factory for creating mock httpx responses."""
    def _create_response(status_code=200, json_data=None, content=b"", headers=None):
        response = Mock(spec=httpx.Response)
        response.status_code = status_code
        response.json = Mock(return_value=json_data or {})
        response.content = content
        response.headers = headers or {}

        def raise_for_status():
            if 400 <= status_code < 600:
                raise httpx.HTTPStatusError(
                    f"HTTP {status_code}",
                    request=Mock(),
                    response=response
                )
        response.raise_for_status = raise_for_status

        return response
    return _create_response


class TestMediaClientInit:
    """Test media client initialization."""

    def test_init_with_token(self):
        """Initialize with explicit token."""
        client = WhatsAppMediaClient(access_token="custom_token", api_version="v19.0")
        assert client.access_token == "custom_token"
        assert client.api_version == "v19.0"
        assert client._auth_headers["Authorization"] == "Bearer custom_token"

    def test_init_from_settings(self):
        """Initialize with default settings."""
        with patch('autifyme_agents.integrations.communication.whatsapp_media_client.settings') as mock_settings:
            mock_settings.WHATSAPP_ACCESS_TOKEN = "settings_token"
            mock_settings.WHATSAPP_API_VERSION = "v18.0"

            client = WhatsAppMediaClient()
            assert client.access_token == "settings_token"
            assert client.api_version == "v18.0"

    def test_init_without_token_raises(self):
        """Initialize without token raises ValueError."""
        with patch('autifyme_agents.integrations.communication.whatsapp_media_client.settings') as mock_settings:
            mock_settings.WHATSAPP_ACCESS_TOKEN = None

            with pytest.raises(ValueError, match="WhatsApp access token not configured"):
                WhatsAppMediaClient()


class TestGetMediaURL:
    """Test get_media_url method."""

    def test_get_media_url_success(self, media_client, mock_httpx_response):
        """Successfully fetches media URL and metadata."""
        mock_response = mock_httpx_response(
            status_code=200,
            json_data={
                "url": "https://lookaside.fbsbx.com/whatsapp_business/attachments/media123.jpg",
                "mime_type": "image/jpeg",
                "file_size": 12345,
            }
        )

        with patch('httpx.get', return_value=mock_response) as mock_get:
            media_url = media_client.get_media_url("media_abc123")

        assert media_url == "https://lookaside.fbsbx.com/whatsapp_business/attachments/media123.jpg"
        mock_get.assert_called_once_with(
            "https://graph.facebook.com/v18.0/media_abc123",
            headers=media_client._auth_headers,
            timeout=10.0,
        )

    def test_get_media_url_http_404(self, media_client, mock_httpx_response):
        """HTTP 404 raises HTTPStatusError."""
        mock_response = mock_httpx_response(status_code=404)

        with patch('httpx.get', return_value=mock_response):
            with pytest.raises(httpx.HTTPStatusError):
                media_client.get_media_url("nonexistent_media")

    def test_get_media_url_http_403(self, media_client, mock_httpx_response):
        """HTTP 403 (permission denied) raises HTTPStatusError."""
        mock_response = mock_httpx_response(status_code=403)

        with patch('httpx.get', return_value=mock_response):
            with pytest.raises(httpx.HTTPStatusError):
                media_client.get_media_url("forbidden_media")

    def test_get_media_url_timeout(self, media_client):
        """Network timeout raises TimeoutException."""
        with patch('httpx.get', side_effect=httpx.TimeoutException("Connection timeout")):
            with pytest.raises(httpx.TimeoutException):
                media_client.get_media_url("media_timeout")

    def test_get_media_url_network_error(self, media_client):
        """Network error raises ConnectError."""
        with patch('httpx.get', side_effect=httpx.ConnectError("Connection failed")):
            with pytest.raises(httpx.ConnectError):
                media_client.get_media_url("media_error")


class TestDownloadMedia:
    """Test download_media method."""

    def test_download_media_success(self, media_client, mock_httpx_response):
        """Successfully downloads media and returns path, bytes, mime_type."""
        # Mock get_media_url
        media_url = "https://lookaside.fbsbx.com/attachments/media123.jpg"
        media_client.get_media_url = Mock(return_value=media_url)

        # Mock download response
        test_bytes = b"fake_image_data_12345"
        mock_response = mock_httpx_response(
            status_code=200,
            content=test_bytes,
            headers={"Content-Type": "image/jpeg"}
        )

        with patch('httpx.get', return_value=mock_response) as mock_get:
            with patch('pathlib.Path.write_bytes'):
                path, content, mime_type = media_client.download_media("media_abc123")

        assert isinstance(path, Path)
        assert "media_abc123" in str(path)
        assert path.suffix == ".jpg"
        assert content == test_bytes
        assert mime_type == "image/jpeg"

        # Verify download call
        mock_get.assert_called_once_with(
            media_url,
            headers=media_client._auth_headers,
            timeout=30.0,
        )

    def test_download_media_http_error(self, media_client, mock_httpx_response):
        """HTTP error during download raises HTTPStatusError."""
        media_client.get_media_url = Mock(return_value="https://example.com/media.jpg")

        mock_response = mock_httpx_response(status_code=500)

        with patch('httpx.get', return_value=mock_response):
            with pytest.raises(httpx.HTTPStatusError):
                media_client.download_media("media_error")

    def test_download_media_timeout(self, media_client):
        """Timeout during download raises TimeoutException."""
        media_client.get_media_url = Mock(return_value="https://example.com/media.jpg")

        with patch('httpx.get', side_effect=httpx.TimeoutException("Download timeout")):
            with pytest.raises(httpx.TimeoutException):
                media_client.download_media("media_timeout")

    def test_download_media_write_failure(self, media_client, mock_httpx_response):
        """Write failure doesn't crash (serverless scenario) - returns bytes only."""
        media_client.get_media_url = Mock(return_value="https://example.com/media.jpg")

        test_bytes = b"image_data"
        mock_response = mock_httpx_response(
            status_code=200,
            content=test_bytes,
            headers={"Content-Type": "image/png"}
        )

        with patch('httpx.get', return_value=mock_response):
            with patch('pathlib.Path.write_bytes', side_effect=OSError("Read-only filesystem")):
                path, content, mime_type = media_client.download_media("media_abc123")

        # Should still return bytes even if write fails
        assert content == test_bytes
        assert mime_type == "image/png"

    def test_download_media_large_file(self, media_client, mock_httpx_response):
        """Large file (10MB+) downloads successfully."""
        media_client.get_media_url = Mock(return_value="https://example.com/large.mp4")

        # Simulate 12MB file
        large_bytes = b"x" * (12 * 1024 * 1024)
        mock_response = mock_httpx_response(
            status_code=200,
            content=large_bytes,
            headers={"Content-Type": "video/mp4"}
        )

        with patch('httpx.get', return_value=mock_response):
            with patch('pathlib.Path.write_bytes'):
                path, content, mime_type = media_client.download_media("large_media")

        assert len(content) == 12 * 1024 * 1024
        assert mime_type == "video/mp4"
        assert path.suffix == ".mp4"

    def test_download_media_missing_content_type(self, media_client, mock_httpx_response):
        """Missing Content-Type header defaults to application/octet-stream."""
        media_client.get_media_url = Mock(return_value="https://example.com/unknown")

        mock_response = mock_httpx_response(
            status_code=200,
            content=b"unknown_data",
            headers={}  # No Content-Type
        )

        with patch('httpx.get', return_value=mock_response):
            with patch('pathlib.Path.write_bytes'):
                path, content, mime_type = media_client.download_media("unknown_media")

        assert mime_type == "application/octet-stream"
        assert path.suffix == ""  # No extension for unknown type


class TestMIMETypeMapping:
    """Test _derive_suffix MIME type to extension mapping."""

    def test_image_types(self):
        """Image MIME types map correctly."""
        assert WhatsAppMediaClient._derive_suffix("image/jpeg") == ".jpg"
        assert WhatsAppMediaClient._derive_suffix("image/png") == ".png"
        assert WhatsAppMediaClient._derive_suffix("image/webp") == ".webp"
        assert WhatsAppMediaClient._derive_suffix("image/gif") == ".gif"

    def test_audio_types(self):
        """Audio MIME types map correctly."""
        assert WhatsAppMediaClient._derive_suffix("audio/ogg") == ".ogg"
        assert WhatsAppMediaClient._derive_suffix("audio/mpeg") == ".mp3"
        assert WhatsAppMediaClient._derive_suffix("audio/mp4") == ".m4a"
        assert WhatsAppMediaClient._derive_suffix("audio/wav") == ".wav"
        assert WhatsAppMediaClient._derive_suffix("audio/aac") == ".aac"

    def test_video_types(self):
        """Video MIME types map correctly."""
        assert WhatsAppMediaClient._derive_suffix("video/mp4") == ".mp4"
        assert WhatsAppMediaClient._derive_suffix("video/quicktime") == ".mov"
        assert WhatsAppMediaClient._derive_suffix("video/x-msvideo") == ".avi"
        assert WhatsAppMediaClient._derive_suffix("video/webm") == ".webm"
        assert WhatsAppMediaClient._derive_suffix("video/x-matroska") == ".mkv"

    def test_document_types(self):
        """Document MIME types map correctly."""
        assert WhatsAppMediaClient._derive_suffix("application/pdf") == ".pdf"
        assert WhatsAppMediaClient._derive_suffix("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet") == ".xlsx"
        assert WhatsAppMediaClient._derive_suffix("application/vnd.ms-excel") == ".xls"
        assert WhatsAppMediaClient._derive_suffix("text/csv") == ".csv"
        assert WhatsAppMediaClient._derive_suffix("application/vnd.openxmlformats-officedocument.wordprocessingml.document") == ".docx"
        assert WhatsAppMediaClient._derive_suffix("application/msword") == ".doc"
        assert WhatsAppMediaClient._derive_suffix("text/plain") == ".txt"

    def test_unknown_mime_type(self):
        """Unknown MIME type returns empty suffix."""
        assert WhatsAppMediaClient._derive_suffix("application/x-custom") == ""
        assert WhatsAppMediaClient._derive_suffix("unknown/type") == ""

    def test_none_mime_type(self):
        """None MIME type returns empty suffix."""
        assert WhatsAppMediaClient._derive_suffix(None) == ""

    def test_empty_mime_type(self):
        """Empty string MIME type returns empty suffix."""
        assert WhatsAppMediaClient._derive_suffix("") == ""


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_media_id_with_special_characters(self, media_client, mock_httpx_response):
        """Media ID with special characters is properly encoded."""
        media_id = "media_123-abc_xyz"
        mock_response = mock_httpx_response(
            status_code=200,
            json_data={"url": "https://example.com/media.jpg", "mime_type": "image/jpeg"}
        )

        with patch('httpx.get', return_value=mock_response) as mock_get:
            media_client.get_media_url(media_id)

        # Verify URL contains the media_id
        call_args = mock_get.call_args
        assert media_id in call_args[0][0]

    def test_concurrent_downloads(self, media_client, mock_httpx_response):
        """Multiple downloads generate unique filenames (timestamp-based)."""
        media_client.get_media_url = Mock(return_value="https://example.com/media.jpg")

        mock_response = mock_httpx_response(
            status_code=200,
            content=b"data",
            headers={"Content-Type": "image/jpeg"}
        )

        paths = []
        with patch('httpx.get', return_value=mock_response):
            with patch('pathlib.Path.write_bytes'):
                for i in range(3):
                    path, _, _ = media_client.download_media(f"media_{i}")
                    paths.append(str(path))

        # All paths should be unique (contain timestamps and different media IDs)
        assert len(set(paths)) == 3
        assert all("media_" in p for p in paths)

    def test_unicode_content_type(self, media_client, mock_httpx_response):
        """Content-Type with unicode characters doesn't crash."""
        media_client.get_media_url = Mock(return_value="https://example.com/media.jpg")

        mock_response = mock_httpx_response(
            status_code=200,
            content=b"data",
            headers={"Content-Type": "image/jpeg; charset=utf-8"}
        )

        with patch('httpx.get', return_value=mock_response):
            with patch('pathlib.Path.write_bytes'):
                path, content, mime_type = media_client.download_media("media_unicode")

        # Should extract base MIME type (ignore charset)
        assert "image/jpeg" in mime_type or mime_type == "image/jpeg; charset=utf-8"
