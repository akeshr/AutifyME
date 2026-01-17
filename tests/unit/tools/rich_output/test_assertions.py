"""Unit tests for Rich Output assertion helpers."""

import pytest

from autifyme_agents.tools.rich_output.utils.assertions import RichOutputAssertions


class TestAssertBranded:
    """Tests for assert_branded."""

    def test_passes_with_company_name(self):
        """Passes when company name is in HTML."""
        html = "<h1>Pavisha Packaging</h1><p>Welcome</p>"
        # Should not raise
        RichOutputAssertions.assert_branded(html, "Pavisha Packaging")

    def test_fails_when_company_name_missing(self):
        """Fails when company name is not in HTML."""
        html = "<h1>Welcome</h1><p>Content</p>"
        with pytest.raises(AssertionError, match="Company name"):
            RichOutputAssertions.assert_branded(html, "Pavisha Packaging")

    def test_fails_when_autifyme_present(self):
        """Fails when AutifyME is in HTML (platform branding leak)."""
        html = "<h1>Pavisha Packaging</h1><footer>Powered by AutifyME</footer>"
        with pytest.raises(AssertionError, match="AutifyME"):
            RichOutputAssertions.assert_branded(html, "Pavisha Packaging")


class TestAssertDataRendered:
    """Tests for assert_data_rendered."""

    def test_passes_with_keys_present(self):
        """Passes when all data keys are in HTML."""
        html = "<div>name: Test</div><div>price: 100</div>"
        data = {"name": "Test", "price": 100}
        # Should not raise
        RichOutputAssertions.assert_data_rendered(html, data)

    def test_passes_with_readable_keys(self):
        """Passes when human-readable versions of keys are present."""
        html = "<div>Product Name: Test</div><div>Unit Price: 100</div>"
        data = {"product_name": "Test", "unit_price": 100}
        # Should not raise
        RichOutputAssertions.assert_data_rendered(html, data)

    def test_fails_when_key_missing(self):
        """Fails when a key is not rendered."""
        html = "<div>name: Test</div>"
        data = {"name": "Test", "price": 100}
        with pytest.raises(AssertionError, match="price"):
            RichOutputAssertions.assert_data_rendered(html, data)

    def test_handles_list_data(self):
        """Works with list of dicts (uses first item)."""
        html = "<div>sku: ABC</div><div>status: active</div>"
        data = [
            {"sku": "ABC", "status": "active"},
            {"sku": "DEF", "status": "draft"},
        ]
        # Should not raise
        RichOutputAssertions.assert_data_rendered(html, data)

    def test_handles_empty_list(self):
        """Handles empty list gracefully."""
        html = "<p>No items</p>"
        data = []
        # Should not raise
        RichOutputAssertions.assert_data_rendered(html, data)


class TestAssertMobileReady:
    """Tests for assert_mobile_ready."""

    def test_passes_with_viewport(self):
        """Passes when viewport meta tag is present."""
        html = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        # Should not raise
        RichOutputAssertions.assert_mobile_ready(html)

    def test_fails_without_viewport(self):
        """Fails when viewport is missing."""
        html = '<meta charset="UTF-8">'
        with pytest.raises(AssertionError, match="viewport"):
            RichOutputAssertions.assert_mobile_ready(html)

    def test_fails_without_device_width(self):
        """Fails when device-width is missing."""
        html = '<meta name="viewport" content="width=1024">'
        with pytest.raises(AssertionError, match="device-width"):
            RichOutputAssertions.assert_mobile_ready(html)


class TestAssertNoScripts:
    """Tests for assert_no_scripts."""

    def test_passes_with_clean_html(self):
        """Passes when no scripts or handlers are present."""
        html = "<div><p>Safe content</p></div>"
        # Should not raise
        RichOutputAssertions.assert_no_scripts(html)

    def test_fails_with_script_tag(self):
        """Fails when script tag is present."""
        html = "<script>alert(1)</script>"
        with pytest.raises(AssertionError, match="Script"):
            RichOutputAssertions.assert_no_scripts(html)

    def test_fails_with_javascript_url(self):
        """Fails when javascript: URL is present."""
        html = '<a href="javascript:void(0)">Link</a>'
        with pytest.raises(AssertionError, match="javascript"):
            RichOutputAssertions.assert_no_scripts(html)

    def test_fails_with_onclick(self):
        """Fails when onclick handler is present."""
        html = '<button onclick="doSomething()">Click</button>'
        with pytest.raises(AssertionError, match="onclick"):
            RichOutputAssertions.assert_no_scripts(html)

    def test_fails_with_onerror(self):
        """Fails when onerror handler is present."""
        html = '<img src="x" onerror="alert(1)">'
        with pytest.raises(AssertionError, match="onerror"):
            RichOutputAssertions.assert_no_scripts(html)

    def test_fails_with_onload(self):
        """Fails when onload handler is present."""
        html = '<body onload="init()">'
        with pytest.raises(AssertionError, match="onload"):
            RichOutputAssertions.assert_no_scripts(html)


class TestAssertValidStructure:
    """Tests for assert_valid_structure."""

    def test_passes_with_valid_html(self):
        """Passes with valid HTML structure."""
        html = """<!DOCTYPE html>
<html><head><title>Test</title></head><body></body></html>"""
        # Should not raise
        RichOutputAssertions.assert_valid_structure(html)

    def test_fails_without_doctype(self):
        """Fails without DOCTYPE."""
        html = "<html><head><title>Test</title></head><body></body></html>"
        with pytest.raises(AssertionError, match="DOCTYPE"):
            RichOutputAssertions.assert_valid_structure(html)

    def test_fails_without_closing_html(self):
        """Fails without closing html tag."""
        html = "<!DOCTYPE html><html><head><title>Test</title></head><body>"
        with pytest.raises(AssertionError, match="</html>"):
            RichOutputAssertions.assert_valid_structure(html)


class TestAssertOgTags:
    """Tests for assert_og_tags."""

    def test_passes_with_og_title(self):
        """Passes when og:title is present."""
        html = '<meta property="og:title" content="Test Page"><title>Test Page</title>'
        # Should not raise
        RichOutputAssertions.assert_og_tags(html, "Test Page")

    def test_fails_without_og_title(self):
        """Fails when og:title is missing."""
        html = "<title>Test Page</title>"
        with pytest.raises(AssertionError, match="og:title"):
            RichOutputAssertions.assert_og_tags(html, "Test Page")

    def test_fails_when_title_not_in_html(self):
        """Fails when title is not in HTML."""
        html = '<meta property="og:title" content="Different"><title>Different</title>'
        with pytest.raises(AssertionError, match="Test Page"):
            RichOutputAssertions.assert_og_tags(html, "Test Page")


class TestAssertFieldHintsApplied:
    """Tests for assert_field_hints_applied."""

    def test_passes_when_hints_applied(self):
        """Passes when field hint labels are in HTML."""
        html = "<th>SKU</th><th>Price</th><th>Min Order Qty</th>"
        hints = {
            "sku_code": {"label": "SKU"},
            "unit_price": {"label": "Price"},
            "moq": {"label": "Min Order Qty"},
        }
        # Should not raise
        RichOutputAssertions.assert_field_hints_applied(html, hints)

    def test_fails_when_hint_missing(self):
        """Fails when a hint label is not in HTML."""
        html = "<th>SKU</th><th>unit_price</th>"
        hints = {
            "sku_code": {"label": "SKU"},
            "unit_price": {"label": "Price"},
        }
        with pytest.raises(AssertionError, match="Price"):
            RichOutputAssertions.assert_field_hints_applied(html, hints)
