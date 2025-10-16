"""Unit tests for image analysis specialist.

Tests base64 encoding, specialist invocation with various inputs,
graph wrapper for DeepAgents, and company profile handling.
"""

import base64
from unittest.mock import Mock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from autifyme_agents.schemas.agent_outputs import ImageAnalysisResult
from autifyme_agents.schemas.models import CompanyProfile
from autifyme_agents.specialists.image_analysis_specialist import (
    _encode_bytes_to_data_uri,
    _encode_image_to_data_uri,
    create_image_analysis_specialist_graph,
    image_analysis_specialist_invoke,
)

# Create minimal test images (1x1 pixel)
JPEG_1X1 = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb00430001010101010101"
    "01010101010101010101010101010101010101010101010101010101010101"
    "01010101010101010101010101ffc00011080001000103012200021101031101"
    "ffda000c03010002110311003f00f3b4ffd900"
)

PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c6300010000050001f14b1d240000000049454e44ae"
    "426082"
)


class TestBase64Encoding:
    """Test image encoding utilities."""

    def test_encode_bytes_to_data_uri_jpeg(self):
        """Encode JPEG bytes to base64 data URI."""
        data_uri = _encode_bytes_to_data_uri(JPEG_1X1, "image/jpeg")

        assert data_uri.startswith("data:image/jpeg;base64,")
        # Verify it's valid base64
        encoded_part = data_uri.split(",", 1)[1]
        decoded = base64.b64decode(encoded_part)
        assert decoded == JPEG_1X1

    def test_encode_bytes_to_data_uri_png(self):
        """Encode PNG bytes to base64 data URI."""
        data_uri = _encode_bytes_to_data_uri(PNG_1X1, "image/png")

        assert data_uri.startswith("data:image/png;base64,")
        encoded_part = data_uri.split(",", 1)[1]
        decoded = base64.b64decode(encoded_part)
        assert decoded == PNG_1X1

    def test_encode_image_to_data_uri_from_file(self, tmp_path):
        """Encode local image file to data URI."""
        # Create temp JPEG file
        image_path = tmp_path / "test.jpg"
        image_path.write_bytes(JPEG_1X1)

        data_uri = _encode_image_to_data_uri(str(image_path))

        assert data_uri.startswith("data:image/jpeg;base64,")
        encoded_part = data_uri.split(",", 1)[1]
        decoded = base64.b64decode(encoded_part)
        assert decoded == JPEG_1X1

    def test_encode_image_to_data_uri_png_extension(self, tmp_path):
        """PNG extension detected and used."""
        image_path = tmp_path / "test.png"
        image_path.write_bytes(PNG_1X1)

        data_uri = _encode_image_to_data_uri(str(image_path))

        assert data_uri.startswith("data:image/png;base64,")

    def test_encode_image_to_data_uri_file_not_found(self):
        """File not found raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Image file not found"):
            _encode_image_to_data_uri("/nonexistent/path/image.jpg")

    def test_encode_image_to_data_uri_unknown_extension(self, tmp_path):
        """Unknown extension defaults to image/jpeg."""
        image_path = tmp_path / "test.unknown"
        image_path.write_bytes(JPEG_1X1)

        data_uri = _encode_image_to_data_uri(str(image_path))

        # Should default to image/jpeg for unknown extensions
        assert data_uri.startswith("data:image/jpeg;base64,")


class TestSpecialistInvocation:
    """Test image_analysis_specialist_invoke with various inputs."""

    @pytest.fixture
    def mock_agent(self):
        """Mock agent that returns structured analysis result."""
        mock_result = ImageAnalysisResult(
            visual_description="A red ceramic mug with comfortable handle for daily use",
            identified_colors=["red", "white"],
            style_tags=["modern", "minimalist"],
        )

        mock_agent = Mock()
        mock_agent.invoke = Mock(return_value={
            "structured_response": mock_result
        })

        with patch('autifyme_agents.specialists.image_analysis_specialist.create_image_analysis_specialist',
                   return_value=mock_agent):
            yield mock_agent

    def test_invoke_with_image_bytes(self, mock_agent):
        """Invoke with image_bytes (preferred serverless method)."""
        result = image_analysis_specialist_invoke(
            image_bytes=JPEG_1X1,
            mime_type="image/jpeg",
        )

        assert isinstance(result, ImageAnalysisResult)
        assert "red ceramic mug" in result.visual_description
        assert "red" in result.identified_colors

        # Verify agent was invoked with data URI
        call_args = mock_agent.invoke.call_args
        messages = call_args[0][0]["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "human"

        # Check image_url in content
        content = messages[0]["content"]
        image_content = [c for c in content if c["type"] == "image_url"][0]
        assert image_content["image_url"]["url"].startswith("data:image/jpeg;base64,")

    def test_invoke_with_https_url(self, mock_agent):
        """Invoke with HTTPS URL."""
        result = image_analysis_specialist_invoke(
            image_url="https://example.com/product.jpg",
        )

        assert isinstance(result, ImageAnalysisResult)

        # Verify agent received HTTPS URL
        call_args = mock_agent.invoke.call_args
        messages = call_args[0][0]["messages"]
        content = messages[0]["content"]
        image_content = [c for c in content if c["type"] == "image_url"][0]
        assert image_content["image_url"]["url"] == "https://example.com/product.jpg"

    def test_invoke_with_data_uri(self, mock_agent):
        """Invoke with pre-encoded data URI."""
        data_uri = _encode_bytes_to_data_uri(JPEG_1X1, "image/jpeg")

        result = image_analysis_specialist_invoke(
            image_url=data_uri,
        )

        assert isinstance(result, ImageAnalysisResult)

        # Verify data URI passed through
        call_args = mock_agent.invoke.call_args
        messages = call_args[0][0]["messages"]
        content = messages[0]["content"]
        image_content = [c for c in content if c["type"] == "image_url"][0]
        assert image_content["image_url"]["url"] == data_uri

    def test_invoke_with_file_path(self, mock_agent, tmp_path):
        """Invoke with local file path (converts to data URI)."""
        image_path = tmp_path / "test.jpg"
        image_path.write_bytes(JPEG_1X1)

        result = image_analysis_specialist_invoke(
            image_url=str(image_path),
        )

        assert isinstance(result, ImageAnalysisResult)

        # Verify converted to data URI
        call_args = mock_agent.invoke.call_args
        messages = call_args[0][0]["messages"]
        content = messages[0]["content"]
        image_content = [c for c in content if c["type"] == "image_url"][0]
        assert image_content["image_url"]["url"].startswith("data:image/jpeg;base64,")

    def test_invoke_without_image_raises(self, mock_agent):
        """Invoke without image_url or image_bytes raises ValueError."""
        with pytest.raises(ValueError, match="Either image_url or image_bytes must be provided"):
            image_analysis_specialist_invoke()

    def test_invoke_with_company_profile_pydantic(self, mock_agent):
        """Invoke with CompanyProfile Pydantic model."""
        company_profile = CompanyProfile(
            id="test-001",
            name="Test Co",
            brand_voice="Friendly and approachable",
            target_audience="Young professionals",
            style_preferences=["modern"],
            industry="Fashion",
        )

        result = image_analysis_specialist_invoke(
            image_bytes=JPEG_1X1,
            mime_type="image/jpeg",
            company_profile=company_profile,
        )

        assert isinstance(result, ImageAnalysisResult)

        # Verify brand context injected into prompt
        call_args = mock_agent.invoke.call_args
        messages = call_args[0][0]["messages"]
        text_content = [c for c in messages[0]["content"] if c["type"] == "text"][0]
        assert "Friendly and approachable" in text_content["text"]
        assert "Young professionals" in text_content["text"]

    def test_invoke_with_company_profile_dict(self, mock_agent):
        """Invoke with company_profile as dict (backward compatibility)."""
        company_profile = {
            "brand_voice": "Professional",
            "target_audience": "Corporate buyers",
        }

        result = image_analysis_specialist_invoke(
            image_bytes=JPEG_1X1,
            mime_type="image/jpeg",
            company_profile=company_profile,
        )

        assert isinstance(result, ImageAnalysisResult)

        # Verify brand context from dict
        call_args = mock_agent.invoke.call_args
        messages = call_args[0][0]["messages"]
        text_content = [c for c in messages[0]["content"] if c["type"] == "text"][0]
        assert "Professional" in text_content["text"]
        assert "Corporate buyers" in text_content["text"]

    def test_invoke_without_company_profile_uses_defaults(self, mock_agent):
        """Invoke without company_profile uses default values."""
        result = image_analysis_specialist_invoke(
            image_bytes=JPEG_1X1,
            mime_type="image/jpeg",
        )

        assert isinstance(result, ImageAnalysisResult)

        # Verify defaults
        call_args = mock_agent.invoke.call_args
        messages = call_args[0][0]["messages"]
        text_content = [c for c in messages[0]["content"] if c["type"] == "text"][0]
        assert "professional" in text_content["text"]
        assert "general" in text_content["text"]

    def test_invoke_with_config(self, mock_agent):
        """Invoke with runtime config."""
        config = {"configurable": {"thread_id": "test_thread"}}

        result = image_analysis_specialist_invoke(
            image_bytes=JPEG_1X1,
            mime_type="image/jpeg",
            config=config,
        )

        assert isinstance(result, ImageAnalysisResult)

        # Verify config passed to agent
        call_kwargs = mock_agent.invoke.call_args[1]
        assert call_kwargs.get("config") == config


class TestGraphWrapper:
    """Test create_image_analysis_specialist_graph for DeepAgents."""

    @pytest.fixture
    def mock_invoke_function(self):
        """Mock image_analysis_specialist_invoke."""
        mock_result = ImageAnalysisResult(
            visual_description="A blue glass bottle with elegant design features",
            identified_colors=["blue", "transparent"],
            style_tags=["modern", "elegant"],
        )

        with patch('autifyme_agents.specialists.image_analysis_specialist.image_analysis_specialist_invoke',
                   return_value=mock_result) as mock_func:
            yield mock_func

    def test_graph_extracts_unix_path(self, mock_invoke_function):
        """Graph extracts Unix file path from delegation message."""
        graph = create_image_analysis_specialist_graph()

        state = {
            "messages": [
                HumanMessage(content="Analyze product image at /tmp/media_downloads/20250115_120000_media123.jpg")
            ]
        }

        # Mock file exists and read
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', create=True) as mock_open_func:
                mock_open_func.return_value.__enter__.return_value.read.return_value = JPEG_1X1

                result = graph.invoke(state)

        # Verify result
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)
        assert "blue glass bottle" in result["messages"][0].content.lower()

        assert "structured_response" in result
        assert isinstance(result["structured_response"], ImageAnalysisResult)

        # Verify invoke was called with correct path
        mock_invoke_function.assert_called_once()
        call_kwargs = mock_invoke_function.call_args[1]
        assert call_kwargs["image_bytes"] == JPEG_1X1
        assert call_kwargs["mime_type"] == "image/jpeg"

    def test_graph_extracts_windows_path(self, mock_invoke_function):
        """Graph extracts Windows file path from delegation message."""
        graph = create_image_analysis_specialist_graph()

        state = {
            "messages": [
                HumanMessage(content="Analyze product image at C:\\tmp\\media_downloads\\20250115_120000_media456.png")
            ]
        }

        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', create=True) as mock_open_func:
                mock_open_func.return_value.__enter__.return_value.read.return_value = PNG_1X1

                result = graph.invoke(state)

        assert "messages" in result
        assert "structured_response" in result

        # Verify PNG mime type detected
        call_kwargs = mock_invoke_function.call_args[1]
        assert call_kwargs["mime_type"] == "image/png"

    def test_graph_no_path_raises(self, mock_invoke_function):
        """Graph raises ValueError if no file path in message."""
        graph = create_image_analysis_specialist_graph()

        state = {
            "messages": [
                HumanMessage(content="Analyze this product image")  # No path
            ]
        }

        with pytest.raises(ValueError, match="No image file path found in delegation message"):
            graph.invoke(state)

    def test_graph_file_not_found_raises(self, mock_invoke_function):
        """Graph raises FileNotFoundError if file doesn't exist."""
        graph = create_image_analysis_specialist_graph()

        state = {
            "messages": [
                HumanMessage(content="Analyze /tmp/nonexistent.jpg")
            ]
        }

        with patch('pathlib.Path.exists', return_value=False):
            with pytest.raises(FileNotFoundError, match="Image file not found on filesystem"):
                graph.invoke(state)

    def test_graph_with_company_profile(self, mock_invoke_function):
        """Graph passes company profile to specialist."""
        company_profile = CompanyProfile(
            id="test-002",
            name="Test Brand",
            brand_voice="Luxury and premium",
            target_audience="High-end customers",
            style_preferences=["elegant"],
            industry="Jewelry",
        )

        graph = create_image_analysis_specialist_graph(company_profile=company_profile)

        state = {
            "messages": [
                HumanMessage(content="Analyze /tmp/media_downloads/product.jpg")
            ]
        }

        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', create=True) as mock_open_func:
                mock_open_func.return_value.__enter__.return_value.read.return_value = JPEG_1X1

                graph.invoke(state)

        # Verify company profile passed
        call_kwargs = mock_invoke_function.call_args[1]
        assert call_kwargs["company_profile"] == company_profile

    def test_graph_handles_multiple_path_patterns(self, mock_invoke_function):
        """Graph handles various path patterns."""
        test_cases = [
            "/tmp/media_downloads/image.jpg",  # Unix specific
            "C:\\tmp\\media_downloads\\image.png",  # Windows specific
            "/tmp/image.webp",  # Unix generic
            "D:\\tmp\\image.gif",  # Windows generic
            "E:\\Users\\test\\image.jpg",  # Windows any path
        ]

        graph = create_image_analysis_specialist_graph()

        for path in test_cases:
            mock_invoke_function.reset_mock()

            state = {"messages": [HumanMessage(content=f"Analyze {path}")]}

            with patch('pathlib.Path.exists', return_value=True):
                with patch('builtins.open', create=True) as mock_open_func:
                    mock_open_func.return_value.__enter__.return_value.read.return_value = JPEG_1X1

                    result = graph.invoke(state)

            assert "structured_response" in result
            mock_invoke_function.assert_called_once()


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_bytes_with_default_mime_type(self):
        """Image bytes without mime_type defaults to image/jpeg."""
        with patch('autifyme_agents.specialists.image_analysis_specialist.create_image_analysis_specialist') as mock_create:
            mock_agent = Mock()
            mock_agent.invoke = Mock(return_value={
                "structured_response": ImageAnalysisResult(
                    visual_description="A test product image with minimal visual content",
                    identified_colors=[],
                    style_tags=[],
                )
            })
            mock_create.return_value = mock_agent

            result = image_analysis_specialist_invoke(
                image_bytes=JPEG_1X1,
                # No mime_type provided
            )

            assert isinstance(result, ImageAnalysisResult)

            # Verify data URI used default mime type
            call_args = mock_agent.invoke.call_args
            messages = call_args[0][0]["messages"]
            content = messages[0]["content"]
            image_content = [c for c in content if c["type"] == "image_url"][0]
            assert "image/jpeg" in image_content["image_url"]["url"]

    def test_empty_state_messages_raises(self):
        """Graph with empty messages raises ValueError."""
        graph = create_image_analysis_specialist_graph()

        with pytest.raises(ValueError, match="No messages in state"):
            graph.invoke({"messages": []})

    def test_graph_with_dict_company_profile(self):
        """Graph accepts company_profile as dict."""
        company_dict = {
            "brand_voice": "Casual",
            "target_audience": "Students",
        }

        # Should not raise
        graph = create_image_analysis_specialist_graph(company_profile=company_dict)
        assert graph is not None
