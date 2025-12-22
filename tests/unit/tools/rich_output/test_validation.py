"""Unit tests for Rich Output validation utilities."""

import pytest

from autifyme_agents.tools.rich_output.utils.validation import (
    validate_html_structure,
    validate_image_url,
)


class TestHtmlStructureValidation:
    """Tests for HTML structure validation."""

    def test_valid_html_passes(self):
        """Valid HTML structure passes validation."""
        html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <title>Test</title>
</head>
<body>
    <p>Content</p>
</body>
</html>'''
        is_valid, error = validate_html_structure(html)

        assert is_valid is True
        assert error is None

    def test_missing_doctype_fails(self):
        """Missing DOCTYPE fails validation."""
        html = '<html><head><title>Test</title></head><body></body></html>'
        is_valid, error = validate_html_structure(html)

        assert is_valid is False
        assert "DOCTYPE" in error

    def test_missing_closing_html_fails(self):
        """Missing closing </html> fails validation."""
        html = '<!DOCTYPE html><html><head><title>Test</title></head><body>'
        is_valid, error = validate_html_structure(html)

        assert is_valid is False
        assert "</html>" in error

    def test_missing_head_fails(self):
        """Missing <head> fails validation."""
        html = '<!DOCTYPE html><html><title>Test</title><body></body></html>'
        is_valid, error = validate_html_structure(html)

        assert is_valid is False
        assert "<head>" in error

    def test_missing_body_fails(self):
        """Missing <body> fails validation."""
        html = '<!DOCTYPE html><html><head><title>Test</title></head></html>'
        is_valid, error = validate_html_structure(html)

        assert is_valid is False
        assert "<body>" in error

    def test_missing_title_fails(self):
        """Missing <title> fails validation."""
        html = '<!DOCTYPE html><html><head></head><body></body></html>'
        is_valid, error = validate_html_structure(html)

        assert is_valid is False
        assert "<title>" in error

    def test_handles_whitespace(self):
        """Leading/trailing whitespace is handled."""
        html = '''   <!DOCTYPE html>
<html><head><title>Test</title></head><body></body></html>   '''
        is_valid, error = validate_html_structure(html)

        assert is_valid is True

    def test_case_insensitive(self):
        """Validation is case-insensitive."""
        html = '<!doctype HTML><HTML><HEAD><TITLE>Test</TITLE></HEAD><BODY></BODY></HTML>'
        is_valid, error = validate_html_structure(html)

        assert is_valid is True


class TestImageUrlValidation:
    """Tests for image URL validation."""

    def test_valid_https_url_passes(self):
        """Valid HTTPS URL passes."""
        url = "https://example.com/image.jpg"
        assert validate_image_url(url) is True

    def test_http_url_fails(self):
        """HTTP URL fails (not secure)."""
        url = "http://example.com/image.jpg"
        assert validate_image_url(url) is False

    def test_javascript_url_fails(self):
        """javascript: URL fails."""
        url = "javascript:alert('xss')"
        assert validate_image_url(url) is False

    def test_javascript_url_case_insensitive(self):
        """JAVASCRIPT: URL also fails."""
        url = "JAVASCRIPT:alert('xss')"
        assert validate_image_url(url) is False

    def test_data_url_fails(self):
        """data: URL fails (no HTTPS scheme)."""
        url = "data:image/png;base64,..."
        assert validate_image_url(url) is False

    def test_file_url_fails(self):
        """file: URL fails."""
        url = "file:///etc/passwd"
        assert validate_image_url(url) is False

    def test_missing_host_fails(self):
        """URL without host fails."""
        url = "https:///path/image.jpg"
        assert validate_image_url(url) is False

    def test_url_with_query_params_passes(self):
        """URL with query parameters passes."""
        url = "https://example.com/image.jpg?size=large&format=webp"
        assert validate_image_url(url) is True

    def test_url_with_port_passes(self):
        """URL with port number passes."""
        url = "https://example.com:8080/image.jpg"
        assert validate_image_url(url) is True

    def test_subdomain_url_passes(self):
        """URL with subdomain passes."""
        url = "https://cdn.images.example.com/image.jpg"
        assert validate_image_url(url) is True
