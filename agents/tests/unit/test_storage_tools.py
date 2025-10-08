"""Unit tests for storage tools.

Tests the tool factories and their error handling, retry logic, and
integration with the StorageInterface port.
"""

import uuid
from unittest.mock import Mock, patch

import pytest
from langchain_core.tools import ToolException

from autifyme_agents.core.exceptions import (
    ConfigurationError,
    DataNotFoundError,
    ExternalAPIError,
    StorageError,
)
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.schemas.models import CatalogingResult, CompanyProfile, Product
from autifyme_agents.tools.storage_tools import (
    create_save_product_tool,
    create_get_company_profile_tool,
)


class TestSaveProductTool:
    """Test save_product tool creation and execution."""

    def test_create_save_product_tool_returns_callable(self, mock_storage):
        """Tool factory should return a callable tool."""
        tool = create_save_product_tool(mock_storage)
        assert hasattr(tool, "invoke")
        assert tool.name == "save_product"

    def test_save_product_success(self, mock_storage, mock_product):
        """Tool should successfully save product and return CatalogingResult."""
        tool = create_save_product_tool(mock_storage)

        result = tool.invoke({
            "name": mock_product.name,
            "description": mock_product.description,
            "price": mock_product.price,
            "sizes": mock_product.sizes,
            "colors": mock_product.colors,
            "image_urls": mock_product.image_urls,
        })

        assert isinstance(result, CatalogingResult)
        assert result.success is True
        assert result.stage == "saved"
        assert result.product_name == mock_product.name
        assert len(mock_storage.saved_products) == 1

    def test_save_product_without_storage_raises_configuration_error(self):
        """Tool should raise ConfigurationError when storage is None."""
        tool = create_save_product_tool(storage=None)

        with pytest.raises(ConfigurationError) as exc_info:
            tool.invoke({"name": "Test", "description": "Test", "price": 10.0})

        assert "Storage client not provided" in str(exc_info.value)
        assert exc_info.value.config_key == "storage_client"

    def test_save_product_retry_on_transient_error(self, mock_storage):
        """Tool should retry on transient ExternalAPIError."""
        tool = create_save_product_tool(mock_storage)

        # Mock save_product to fail twice with retryable error, then succeed
        call_count = 0

        def side_effect(product):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("connection timeout")  # Triggers ExternalAPIError path
            return product

        mock_storage.save_product = Mock(side_effect=side_effect)

        result = tool.invoke({
            "name": "Test Product",
            "description": "Test",
            "price": 99.99,
        })

        assert isinstance(result, CatalogingResult)
        assert result.success is True
        assert call_count == 3  # 2 retries + 1 success

    def test_save_product_with_minimal_fields(self, mock_storage):
        """Tool should work with only required fields."""
        tool = create_save_product_tool(mock_storage)

        result = tool.invoke({
            "name": "Minimal Product",
            "description": "A minimal test",
            "price": 19.99,
        })

        assert result.success is True
        assert result.product_name == "Minimal Product"

    def test_save_product_generates_uuid(self, mock_storage):
        """Tool should preserve/generate UUID for products."""
        tool = create_save_product_tool(mock_storage)

        result = tool.invoke({
            "name": "UUID Test",
            "description": "Test UUID generation",
            "price": 49.99,
        })

        assert result.product_id is not None
        assert isinstance(result.product_id, uuid.UUID)


class TestGetCompanyProfileTool:
    """Test get_company_profile tool creation and execution."""

    def test_create_get_company_profile_tool_returns_callable(self, mock_storage):
        """Tool factory should return a callable tool."""
        tool = create_get_company_profile_tool(mock_storage)
        assert hasattr(tool, "invoke")
        assert tool.name == "get_company_profile"

    def test_get_company_profile_success(self, mock_storage, mock_company_profile):
        """Tool should retrieve company profile successfully."""
        tool = create_get_company_profile_tool(mock_storage)

        result = tool.invoke({})

        assert isinstance(result, CompanyProfile)
        assert result.id == mock_company_profile.id
        assert result.name == mock_company_profile.name
        assert result.brand_voice == mock_company_profile.brand_voice

    def test_get_company_profile_without_storage_raises_configuration_error(self):
        """Tool should raise ConfigurationError when storage is None."""
        tool = create_get_company_profile_tool(storage=None)

        with pytest.raises(ConfigurationError) as exc_info:
            tool.invoke({})

        assert "Storage client not provided" in str(exc_info.value)

    def test_get_company_profile_not_found_raises_data_not_found_error(self):
        """Tool should raise DataNotFoundError when profile doesn't exist."""

        class EmptyStorage(StorageInterface):
            def get_company_profile(self):
                return None  # Simulate missing profile

            def save_product(self, product):
                pass

            def get_product(self, product_id):
                return None

            def list_products(self, limit=100, offset=0):
                return []

            def save_pending_approval(self, **kwargs):
                pass

            def get_pending_approval(self, thread_id):
                return None

            def delete_pending_approval(self, thread_id):
                pass

        tool = create_get_company_profile_tool(EmptyStorage())

        with pytest.raises(DataNotFoundError) as exc_info:
            tool.invoke({})

        assert exc_info.value.resource_type == "CompanyProfile"
        assert exc_info.value.identifier == "default"

    def test_get_company_profile_retry_on_timeout(self, mock_storage):
        """Tool should retry on transient connection errors."""
        tool = create_get_company_profile_tool(mock_storage)

        call_count = 0
        original_profile = mock_storage.get_company_profile()

        def side_effect():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("connection timeout")
            return original_profile

        mock_storage.get_company_profile = Mock(side_effect=side_effect)

        result = tool.invoke({})

        assert isinstance(result, CompanyProfile)
        assert call_count == 2  # 1 retry + 1 success
