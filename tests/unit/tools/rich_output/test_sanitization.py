"""Unit tests for Rich Output sanitization utilities."""


from autifyme_agents.tools.rich_output.utils.input_sanitization import (
    sanitize_input_data,
)
from autifyme_agents.tools.rich_output.utils.output_sanitization import (
    sanitize_llm_html_output,
)


class TestInputSanitization:
    """Tests for input data sanitization."""

    def test_sanitizes_string_with_html(self):
        """HTML entities in strings are escaped."""
        result = sanitize_input_data("<script>alert('xss')</script>")
        assert "&lt;script&gt;" in result
        assert "<script>" not in result

    def test_sanitizes_dict_values(self):
        """Dict values with HTML are escaped."""
        data = {"name": "<b>Bold</b>", "description": "Normal text"}
        result = sanitize_input_data(data)

        assert "&lt;b&gt;" in result["name"]
        assert "<b>" not in result["name"]
        assert result["description"] == "Normal text"

    def test_sanitizes_nested_dicts(self):
        """Nested dict values are escaped."""
        data = {
            "outer": {
                "inner": "<script>bad</script>"
            }
        }
        result = sanitize_input_data(data)

        assert "&lt;script&gt;" in result["outer"]["inner"]

    def test_sanitizes_list_items(self):
        """List items with HTML are escaped."""
        data = [
            {"name": "<div>Item 1</div>"},
            {"name": "<div>Item 2</div>"},
        ]
        result = sanitize_input_data(data)

        for item in result:
            assert "&lt;div&gt;" in item["name"]

    def test_preserves_non_strings(self):
        """Non-string values (int, float, bool, None) are preserved."""
        data = {
            "count": 42,
            "price": 19.99,
            "active": True,
            "discount": None,
        }
        result = sanitize_input_data(data)

        assert result["count"] == 42
        assert result["price"] == 19.99
        assert result["active"] is True
        assert result["discount"] is None


class TestOutputSanitization:
    """Tests for LLM output sanitization."""

    def test_removes_script_tags(self):
        """Script tags and content are removed."""
        html = '<html><body><script>alert("xss")</script><p>Content</p></body></html>'
        result = sanitize_llm_html_output(html)

        assert "<script>" not in result.lower()
        assert "alert" not in result
        assert "<p>Content</p>" in result

    def test_removes_onclick_handlers(self):
        """onclick event handlers are removed."""
        html = '<div onclick="doEvil()">Click me</div>'
        result = sanitize_llm_html_output(html)

        assert 'onclick=' not in result.lower()
        assert 'doEvil' not in result

    def test_removes_onerror_handlers(self):
        """onerror event handlers are removed."""
        html = '<img src="x" onerror="alert(1)">'
        result = sanitize_llm_html_output(html)

        assert 'onerror=' not in result.lower()
        assert 'alert' not in result

    def test_removes_onload_handlers(self):
        """onload event handlers are removed."""
        html = '<body onload="init()">'
        result = sanitize_llm_html_output(html)

        assert 'onload=' not in result.lower()

    def test_removes_javascript_urls(self):
        """javascript: URLs are removed."""
        html = '<a href="javascript:alert(1)">Click</a>'
        result = sanitize_llm_html_output(html)

        assert 'javascript:' not in result.lower()

    def test_removes_data_html_urls(self):
        """data:text/html URLs are removed."""
        html = '<iframe src="data:text/html,<script>alert(1)</script>">'
        result = sanitize_llm_html_output(html)

        assert 'data:text/html' not in result.lower()

    def test_preserves_valid_content(self):
        """Valid HTML content is preserved."""
        html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <title>Test Page</title>
    <style>body { color: blue; }</style>
</head>
<body>
    <h1>Hello World</h1>
    <p>This is content.</p>
</body>
</html>'''
        result = sanitize_llm_html_output(html)

        assert "<!DOCTYPE html>" in result
        assert "<title>Test Page</title>" in result
        assert "<h1>Hello World</h1>" in result

    def test_case_insensitive_removal(self):
        """Dangerous content is removed case-insensitively."""
        html = '<SCRIPT>bad</SCRIPT><div ONCLICK="bad">text</div>'
        result = sanitize_llm_html_output(html)

        assert 'script' not in result.lower()
        assert 'onclick' not in result.lower()
