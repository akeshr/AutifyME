"""Unit tests for Rich Output schemas."""

import pytest
from pydantic import ValidationError

from autifyme_agents.schemas.models import CompanyProfile
from autifyme_agents.tools.rich_output.schemas import (
    FieldHint,
    RichOutputInput,
    RichOutputResult,
)


class TestFieldHint:
    """Tests for FieldHint schema."""

    def test_minimal_field_hint(self):
        """Creates field hint with just label."""
        hint = FieldHint(label="SKU")

        assert hint.label == "SKU"
        assert hint.format == "text"  # default
        assert hint.currency == "USD"  # default

    def test_currency_format(self):
        """Creates field hint with currency format."""
        hint = FieldHint(label="Price", format="currency", currency="EUR")

        assert hint.label == "Price"
        assert hint.format == "currency"
        assert hint.currency == "EUR"

    def test_code_format(self):
        """Creates field hint with code format."""
        hint = FieldHint(label="SKU", format="code")

        assert hint.format == "code"

    def test_invalid_format_rejected(self):
        """Invalid format is rejected."""
        with pytest.raises(ValidationError):
            FieldHint(label="Test", format="invalid_format")


class TestRichOutputInput:
    """Tests for RichOutputInput schema."""

    @pytest.fixture
    def sample_company(self):
        """Create sample company profile."""
        return CompanyProfile(
            id="test-123",
            name="Test Company",
            brand_voice="Professional",
            target_audience="B2B",
            industry="Manufacturing",
        )

    def test_minimal_input(self, sample_company):
        """Creates input with required fields only."""
        input_data = RichOutputInput(
            title="Test Page",
            data={"item": "value"},
            context="Test context",
            company_profile=sample_company,
        )

        assert input_data.title == "Test Page"
        assert input_data.data == {"item": "value"}
        assert input_data.context == "Test context"
        assert input_data.ttl_days == 30  # default

    def test_list_data(self, sample_company):
        """Accepts list of dicts as data."""
        input_data = RichOutputInput(
            title="Items",
            data=[{"name": "A"}, {"name": "B"}],
            context="Item list",
            company_profile=sample_company,
        )

        assert len(input_data.data) == 2

    def test_with_field_hints(self, sample_company):
        """Creates input with field hints."""
        hints = {
            "sku": FieldHint(label="SKU", format="code"),
            "price": FieldHint(label="Price", format="currency"),
        }

        input_data = RichOutputInput(
            title="Products",
            data=[{"sku": "ABC", "price": 99}],
            context="Product list",
            company_profile=sample_company,
            field_hints=hints,
        )

        assert input_data.field_hints is not None
        assert input_data.field_hints["sku"].label == "SKU"

    def test_with_layout_hint(self, sample_company):
        """Creates input with layout hint."""
        input_data = RichOutputInput(
            title="Comparison",
            data=[{"a": 1}, {"b": 2}],
            context="Compare items",
            company_profile=sample_company,
            layout_hint="comparison",
        )

        assert input_data.layout_hint == "comparison"

    def test_invalid_layout_hint_rejected(self, sample_company):
        """Invalid layout hint is rejected."""
        with pytest.raises(ValidationError):
            RichOutputInput(
                title="Test",
                data={},
                context="Test",
                company_profile=sample_company,
                layout_hint="invalid_layout",
            )

    def test_ttl_days_bounds(self, sample_company):
        """TTL days must be 0-365."""
        # Valid: 0 (permanent)
        input_data = RichOutputInput(
            title="T",
            data={},
            context="C",
            company_profile=sample_company,
            ttl_days=0,
        )
        assert input_data.ttl_days == 0

        # Valid: 365
        input_data = RichOutputInput(
            title="T",
            data={},
            context="C",
            company_profile=sample_company,
            ttl_days=365,
        )
        assert input_data.ttl_days == 365

        # Invalid: negative
        with pytest.raises(ValidationError):
            RichOutputInput(
                title="T",
                data={},
                context="C",
                company_profile=sample_company,
                ttl_days=-1,
            )

        # Invalid: > 365
        with pytest.raises(ValidationError):
            RichOutputInput(
                title="T",
                data={},
                context="C",
                company_profile=sample_company,
                ttl_days=400,
            )


class TestRichOutputResult:
    """Tests for RichOutputResult schema."""

    def test_success_result(self):
        """Creates successful result."""
        result = RichOutputResult(
            success=True,
            url="https://example.com/output.html",
            filename="20251219_123456_abc.html",
            summary="5 items | $99 - $499",
            expires_at="2026-01-18T00:00:00Z",
        )

        assert result.success is True
        assert result.url is not None
        assert result.error is None

    def test_failure_result(self):
        """Creates failure result."""
        result = RichOutputResult(
            success=False,
            summary="",
            error="HTML generation failed: timeout",
        )

        assert result.success is False
        assert result.url is None
        assert result.error is not None

    def test_summary_required(self):
        """Summary is required even on failure."""
        result = RichOutputResult(
            success=False,
            summary="",
            error="Failed",
        )

        assert result.summary == ""
