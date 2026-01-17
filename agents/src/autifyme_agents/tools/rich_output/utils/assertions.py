"""Test assertion helpers for Rich Output Engine.

Reusable assertions for validating LLM-generated HTML output.
Used in both unit tests and integration tests.
"""

from __future__ import annotations

from typing import Any


class RichOutputAssertions:
    """Assertions for validating LLM-generated HTML."""

    @staticmethod
    def assert_branded(html: str, company_name: str) -> None:
        """Assert output shows client company, not platform.

        Args:
            html: Generated HTML content
            company_name: Expected client company name

        Raises:
            AssertionError: If branding is incorrect
        """
        assert company_name in html, f"Company name '{company_name}' not found in HTML"
        assert "AutifyME" not in html, (
            "Platform name 'AutifyME' should not appear in client-facing output"
        )

    @staticmethod
    def assert_data_rendered(html: str, data: dict[str, Any] | list[dict[str, Any]]) -> None:
        """Assert all data fields are represented in output.

        Checks that each top-level field key (or a human-readable version)
        appears in the HTML output.

        Args:
            html: Generated HTML content
            data: Original data passed to tool

        Raises:
            AssertionError: If any field is not rendered
        """
        if isinstance(data, list) and data:
            sample = data[0]
        elif isinstance(data, dict):
            sample = data
        else:
            return  # Empty data, nothing to check

        for key in sample:
            # Either the key or a human-readable version should appear
            readable = key.replace("_", " ").title()
            assert key in html or readable in html, f"Field '{key}' not rendered in HTML"

    @staticmethod
    def assert_mobile_ready(html: str) -> None:
        """Assert output is mobile-optimized.

        Checks for viewport meta tag with device-width.

        Args:
            html: Generated HTML content

        Raises:
            AssertionError: If mobile optimization is missing
        """
        assert "viewport" in html.lower(), "Missing viewport meta tag"
        assert "width=device-width" in html.lower(), "Missing device-width in viewport"

    @staticmethod
    def assert_no_scripts(html: str) -> None:
        """Assert output contains no executable code.

        Checks for script tags, javascript: URLs, and event handlers.

        Args:
            html: Generated HTML content

        Raises:
            AssertionError: If executable code is found
        """
        html_lower = html.lower()
        assert "<script" not in html_lower, "Script tags found in output"
        assert "javascript:" not in html_lower, "javascript: URLs found in output"
        assert "onclick=" not in html_lower, "onclick handler found in output"
        assert "onerror=" not in html_lower, "onerror handler found in output"
        assert "onload=" not in html_lower, "onload handler found in output"

    @staticmethod
    def assert_valid_structure(html: str) -> None:
        """Assert output has valid HTML structure.

        Checks for DOCTYPE, html tags, head, body, and title.

        Args:
            html: Generated HTML content

        Raises:
            AssertionError: If structure is invalid
        """
        html_stripped = html.strip()
        html_lower = html_stripped.lower()

        assert html_lower.startswith("<!doctype html>"), "Missing DOCTYPE declaration"
        assert html_lower.endswith("</html>"), "Missing closing </html> tag"
        assert "<head>" in html_lower, "Missing <head> section"
        assert "<body>" in html_lower, "Missing <body> section"
        assert "<title>" in html_lower, "Missing <title> tag"

    @staticmethod
    def assert_og_tags(html: str, title: str) -> None:
        """Assert output has Open Graph meta tags for link previews.

        Args:
            html: Generated HTML content
            title: Expected title

        Raises:
            AssertionError: If OG tags are missing
        """
        assert "og:title" in html, "Missing og:title meta tag"
        assert title in html, f"Title '{title}' not found in HTML"

    @staticmethod
    def assert_field_hints_applied(
        html: str,
        field_hints: dict[str, dict[str, Any]],
    ) -> None:
        """Assert field hints are used for labels.

        Args:
            html: Generated HTML content
            field_hints: Field hints that were provided

        Raises:
            AssertionError: If hints are not applied
        """
        for field_name, hint in field_hints.items():
            label = hint.get("label", field_name)
            assert label in html, f"Field hint label '{label}' for '{field_name}' not found"
