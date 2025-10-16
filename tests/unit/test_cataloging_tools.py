"""Unit tests for cataloging tools.

Tests the specialist tool wrappers, middleware injection, and error handling.
"""

from unittest.mock import Mock, patch

import pytest
from langchain_core.tools import ToolException

from autifyme_agents.schemas.agent_outputs import ImageAnalysisResult
from autifyme_agents.schemas.models import Product
from autifyme_agents.tools.cataloging_tools import (
    create_cataloging_specialist_tool,
    create_image_analysis_tool,
)


class TestImageAnalysisTool:
    """Test image_analysis_specialist tool creation and execution."""

    def test_create_image_analysis_tool_returns_callable(self, mock_storage):
        """Tool factory should return a callable tool."""
        tool = create_image_analysis_tool(mock_storage)
        assert hasattr(tool, "invoke")
        assert tool.name == "image_analysis_specialist"

    def test_create_image_analysis_tool_requires_storage(self):
        """Tool factory should raise error if storage is None."""
        with pytest.raises(ValueError) as exc_info:
            create_image_analysis_tool(storage=None)

        assert "storage adapter must be provided" in str(exc_info.value)

    @patch("autifyme_agents.specialists.image_analysis_specialist.image_analysis_specialist_invoke")
    def test_image_analysis_tool_invokes_specialist(
        self,
        mock_specialist_invoke,
        mock_storage,
        mock_company_profile,
        mock_image_analysis,
    ):
        """Tool should invoke specialist with correct payload."""
        # Mock specialist invoke to return result directly
        mock_specialist_invoke.return_value = mock_image_analysis

        tool = create_image_analysis_tool(mock_storage)

        # Middleware injects company_profile, so we pass it explicitly in tests
        result = tool.invoke({
            "image_url": "https://example.com/product.jpg",
            "company_profile": mock_company_profile,
        })

        # Verify specialist was invoked with correct arguments
        mock_specialist_invoke.assert_called_once_with(
            image_url="https://example.com/product.jpg",
            image_bytes=None,
            mime_type=None,
            company_profile=mock_company_profile,
            config=None,
        )

        # Verify result
        assert isinstance(result, ImageAnalysisResult)
        assert result == mock_image_analysis

    @patch("autifyme_agents.specialists.image_analysis_specialist.image_analysis_specialist_invoke")
    def test_image_analysis_tool_with_local_file_path(
        self,
        mock_specialist_invoke,
        mock_storage,
        mock_company_profile,
        temp_image_file,
        mock_image_analysis,
    ):
        """Tool should handle local file paths."""
        # Mock specialist invoke to return result directly
        mock_specialist_invoke.return_value = mock_image_analysis

        tool = create_image_analysis_tool(mock_storage)

        result = tool.invoke({
            "image_url": str(temp_image_file),
            "company_profile": mock_company_profile,
        })

        assert isinstance(result, ImageAnalysisResult)
        # Specialist should be called with the file path
        mock_specialist_invoke.assert_called_once()
        call_kwargs = mock_specialist_invoke.call_args.kwargs
        assert call_kwargs["image_url"] == str(temp_image_file)
        assert call_kwargs["company_profile"] == mock_company_profile


class TestCatalogingSpecialistTool:
    """Test cataloging_specialist tool creation and execution."""

    def test_create_cataloging_specialist_tool_returns_callable(self, mock_storage):
        """Tool factory should return a callable tool."""
        tool = create_cataloging_specialist_tool(mock_storage)
        assert hasattr(tool, "invoke")
        assert tool.name == "cataloging_specialist"

    def test_create_cataloging_specialist_tool_requires_storage(self):
        """Tool factory should raise error if storage is None."""
        with pytest.raises(ValueError) as exc_info:
            create_cataloging_specialist_tool(storage=None)

        assert "storage adapter must be provided" in str(exc_info.value)

    @patch("autifyme_agents.tools.cataloging_tools.create_cataloging_specialist")
    def test_cataloging_specialist_tool_success(
        self,
        mock_specialist_factory,
        mock_storage,
        mock_company_profile,
        mock_product,
    ):
        """Tool should invoke specialist and return Product."""
        # Mock specialist chain
        mock_chain = Mock()
        mock_chain.invoke.return_value = mock_product
        mock_specialist_factory.return_value = mock_chain

        tool = create_cataloging_specialist_tool(mock_storage)

        result = tool.invoke({
            "user_message": "Red t-shirt, size M, price $29.99",
            "company_profile": mock_company_profile,
        })

        # Verify specialist was invoked
        mock_chain.invoke.assert_called_once()
        call_args = mock_chain.invoke.call_args[0][0]
        assert "input" in call_args
        assert call_args["input"]["user_message"] == "Red t-shirt, size M, price $29.99"

        # Verify result structure - tool now returns Product directly
        assert isinstance(result, Product)
        assert result.name == mock_product.name
        assert result.id == mock_product.id

    @patch("autifyme_agents.tools.cataloging_tools.create_cataloging_specialist")
    def test_cataloging_specialist_tool_with_image_analysis(
        self,
        mock_specialist_factory,
        mock_storage,
        mock_company_profile,
        mock_product,
        mock_image_analysis,
    ):
        """Tool should integrate image analysis data."""
        mock_chain = Mock()
        mock_chain.invoke.return_value = mock_product
        mock_specialist_factory.return_value = mock_chain

        tool = create_cataloging_specialist_tool(mock_storage)

        result = tool.invoke({
            "user_message": "Catalog this product",
            "image_analysis": mock_image_analysis.model_dump(),
            "company_profile": mock_company_profile,
        })

        # Verify image analysis was passed to specialist
        call_args = mock_chain.invoke.call_args[0][0]
        assert call_args["input"]["image_analysis"] is not None

        # Verify result - tool now returns Product directly
        assert isinstance(result, Product)

    @patch("autifyme_agents.tools.cataloging_tools.create_cataloging_specialist")
    def test_cataloging_specialist_tool_raises_tool_exception_on_failure(
        self,
        mock_specialist_factory,
        mock_storage,
        mock_company_profile,
    ):
        """Tool should raise ToolException on specialist failure."""
        # Mock specialist to raise an error
        mock_chain = Mock()
        mock_chain.invoke.side_effect = ValueError("Invalid product data")
        mock_specialist_factory.return_value = mock_chain

        tool = create_cataloging_specialist_tool(mock_storage)

        with pytest.raises(ToolException) as exc_info:
            tool.invoke({
                "user_message": "Invalid data",
                "company_profile": mock_company_profile,
            })

        assert "Cataloging specialist failed" in str(exc_info.value)
        assert "Invalid product data" in str(exc_info.value)

    @patch("autifyme_agents.tools.cataloging_tools.create_cataloging_specialist")
    def test_cataloging_specialist_tool_without_image_analysis(
        self,
        mock_specialist_factory,
        mock_storage,
        mock_company_profile,
        mock_product,
    ):
        """Tool should handle missing image analysis gracefully."""
        mock_chain = Mock()
        mock_chain.invoke.return_value = mock_product
        mock_specialist_factory.return_value = mock_chain

        tool = create_cataloging_specialist_tool(mock_storage)

        result = tool.invoke({
            "user_message": "Blue jeans, size 32, price $59.99",
            "image_analysis": None,
            "company_profile": mock_company_profile,
        })

        # Verify specialist was invoked with None for image_analysis
        call_args = mock_chain.invoke.call_args[0][0]
        assert call_args["input"]["image_analysis"] is None

        # Verify result - tool now returns Product directly
        assert isinstance(result, Product)
