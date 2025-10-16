"""Unit tests for specialist chains.

Tests the cataloging and image analysis specialists, including their
structured output generation and error handling.
"""

from unittest.mock import Mock, patch

import pytest

from autifyme_agents.schemas.agent_outputs import ImageAnalysisResult
from autifyme_agents.schemas.models import Product
from autifyme_agents.specialists.cataloging_specialist import create_cataloging_specialist
from autifyme_agents.specialists.image_analysis_specialist import (
    create_image_analysis_specialist,
)


class TestCatalogingSpecialist:
    """Test cataloging specialist chain creation and execution."""

    def test_create_cataloging_specialist_returns_callable(self):
        """Factory should return an agent graph with invoke method."""
        specialist = create_cataloging_specialist()
        # create_agent returns CompiledStateGraph which has invoke method
        assert hasattr(specialist, "invoke")
        assert callable(specialist.invoke)

    @pytest.mark.skip(reason="LCEL chain mocking complex - covered by integration tests")
    def test_cataloging_specialist_with_text_only(self, mock_product):
        """Specialist should process text-only requests."""
        # Create specialist (uses real LLM factory pattern but we'll mock the chain)
        with patch("autifyme_agents.specialists.cataloging_specialist.get_llm") as mock_llm_factory:
            # Create a mock runnable that returns the product
            mock_structured_chain = Mock()
            mock_structured_chain.invoke = Mock(return_value=mock_product)

            mock_llm = Mock()
            mock_llm.with_structured_output.return_value = mock_structured_chain
            mock_llm_factory.return_value = mock_llm

            specialist = create_cataloging_specialist()

            result = specialist.invoke({
                "input": {
                    "user_message": "Red t-shirt, size M, price $29.99",
                    "image_analysis": None,
                }
            })

            assert isinstance(result, Product)
            assert result.name == mock_product.name

    @pytest.mark.skip(reason="LCEL chain mocking complex - covered by integration tests")
    def test_cataloging_specialist_with_image_analysis(
        self,
        mock_product,
        mock_image_analysis,
    ):
        """Specialist should process requests with image analysis."""
        with patch("autifyme_agents.specialists.cataloging_specialist.get_llm") as mock_llm_factory:
            mock_structured_chain = Mock()
            mock_structured_chain.invoke = Mock(return_value=mock_product)

            mock_llm = Mock()
            mock_llm.with_structured_output.return_value = mock_structured_chain
            mock_llm_factory.return_value = mock_llm

            specialist = create_cataloging_specialist()

            result = specialist.invoke({
                "input": {
                    "user_message": "Catalog this product",
                    "image_analysis": mock_image_analysis.model_dump(),
                }
            })

            assert isinstance(result, Product)
            assert result.name == mock_product.name


class TestImageAnalysisSpecialist:
    """Test image analysis specialist chain creation and execution."""

    def test_create_image_analysis_specialist_returns_callable(self):
        """Factory should return an agent graph with invoke method."""
        specialist = create_image_analysis_specialist()
        # create_agent returns CompiledStateGraph which has invoke method
        assert hasattr(specialist, "invoke")
        assert callable(specialist.invoke)

    @pytest.mark.skip(reason="LCEL chain mocking complex - covered by integration tests")
    def test_image_analysis_specialist_with_web_url(
        self,
        mock_image_analysis,
        mock_company_profile,
    ):
        """Specialist should process web image URLs."""
        with patch("autifyme_agents.specialists.image_analysis_specialist.get_llm") as mock_llm_factory:
            mock_structured_chain = Mock()
            mock_structured_chain.invoke = Mock(return_value=mock_image_analysis)

            mock_llm = Mock()
            mock_llm.with_structured_output.return_value = mock_structured_chain
            mock_llm_factory.return_value = mock_llm

            specialist = create_image_analysis_specialist()

            result = specialist.invoke({
                "input": {
                    "image_url": "https://example.com/product.jpg",
                    "company_profile": mock_company_profile,
                }
            })

            assert isinstance(result, ImageAnalysisResult)
            assert result.visual_description == mock_image_analysis.visual_description

    # Note: Local file conversion test removed as _image_to_data_url is no longer needed
    # Current implementation uses direct image URLs or multimodal message content
