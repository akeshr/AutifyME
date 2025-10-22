"""Unit tests for image_analysis_tool.

Tests image resizing, base64 encoding, Vision API integration,
and error handling for the 2-level architecture tool.
"""

import base64
import io
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from autifyme_agents.schemas.agent_outputs import ImageAnalysisResult
from autifyme_agents.tools.image_analysis_tool import (
    _encode_image_to_base64_uri,
    _resize_image_for_vision_api,
    image_analysis_tool,
)

# Test image constants (minimal 1x1 pixel images)
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


class TestImageResizing:
    """Test _resize_image_for_vision_api function."""

    def test_resize_large_image_preserves_aspect_ratio(self, tmp_path):
        """Large image should be resized to max 2048px preserving aspect ratio."""
        # Create a 4000x3000 test image (exceeds MAX_DIMENSION)
        large_img = Image.new("RGB", (4000, 3000), color="red")
        image_path = tmp_path / "large.jpg"
        large_img.save(image_path, "JPEG")

        # Resize
        result_bytes = _resize_image_for_vision_api(str(image_path))

        # Verify result is JPEG and smaller
        result_img = Image.open(io.BytesIO(result_bytes))
        assert result_img.format == "JPEG"
        # Width should be 2048 (larger dimension)
        assert result_img.width == 2048
        # Height should be 1536 (preserves 4:3 ratio)
        assert result_img.height == 1536

    def test_resize_tall_image_preserves_aspect_ratio(self, tmp_path):
        """Tall image (height > width) should resize correctly."""
        # Create 1500x3000 image (height is larger)
        tall_img = Image.new("RGB", (1500, 3000), color="blue")
        image_path = tmp_path / "tall.jpg"
        tall_img.save(image_path, "JPEG")

        result_bytes = _resize_image_for_vision_api(str(image_path))

        result_img = Image.open(io.BytesIO(result_bytes))
        # Height should be 2048 (larger dimension)
        assert result_img.height == 2048
        # Width should be 1024 (preserves 1:2 ratio)
        assert result_img.width == 1024

    def test_small_image_not_resized(self, tmp_path):
        """Images under MAX_DIMENSION should not be resized."""
        # Create 500x500 image (under 2048)
        small_img = Image.new("RGB", (500, 500), color="green")
        image_path = tmp_path / "small.jpg"
        small_img.save(image_path, "JPEG")

        result_bytes = _resize_image_for_vision_api(str(image_path))

        result_img = Image.open(io.BytesIO(result_bytes))
        # Should remain 500x500
        assert result_img.width == 500
        assert result_img.height == 500

    def test_rgba_converted_to_rgb(self, tmp_path):
        """RGBA images should be converted to RGB."""
        # Create RGBA image with transparency
        rgba_img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
        image_path = tmp_path / "rgba.png"
        rgba_img.save(image_path, "PNG")

        result_bytes = _resize_image_for_vision_api(str(image_path))

        result_img = Image.open(io.BytesIO(result_bytes))
        # Should be RGB (Vision API requirement)
        assert result_img.mode == "RGB"
        assert result_img.format == "JPEG"

    def test_file_not_found_raises(self):
        """Non-existent file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Image file not found"):
            _resize_image_for_vision_api("/nonexistent/path/image.jpg")

    def test_output_is_optimized_jpeg(self, tmp_path):
        """Output should always be optimized JPEG."""
        # Create PNG image with complex pattern (not solid color)
        # Solid colors compress better in PNG than JPEG
        png_img = Image.new("RGB", (1000, 1000))
        pixels = png_img.load()
        for i in range(1000):
            for j in range(1000):
                # Create gradient pattern (compresses poorly in PNG, well in JPEG)
                pixels[i, j] = (i % 256, j % 256, (i + j) % 256)

        image_path = tmp_path / "test.png"
        png_img.save(image_path, "PNG")

        result_bytes = _resize_image_for_vision_api(str(image_path))

        # Verify it's JPEG
        result_img = Image.open(io.BytesIO(result_bytes))
        assert result_img.format == "JPEG"

        # Verify it's optimized (gradient should compress better as JPEG)
        compressed_size = len(result_bytes)
        # Should be reasonable size (not gigantic)
        assert compressed_size < 500_000  # Less than 500KB for 1000x1000 gradient


class TestBase64Encoding:
    """Test _encode_image_to_base64_uri function."""

    def test_encode_jpeg_to_data_uri(self, tmp_path):
        """JPEG file should encode to base64 data URI."""
        # Create proper JPEG using PIL
        test_img = Image.new("RGB", (10, 10), color="red")
        image_path = tmp_path / "test.jpg"
        test_img.save(image_path, "JPEG")

        data_uri = _encode_image_to_base64_uri(str(image_path))

        assert data_uri.startswith("data:image/jpeg;base64,")
        # Verify it's valid base64
        encoded_part = data_uri.split(",", 1)[1]
        decoded = base64.b64decode(encoded_part)
        # Should be optimized JPEG (may differ from original due to resizing pipeline)
        assert decoded[:2] == b"\xff\xd8"  # JPEG magic bytes

    def test_encode_png_to_data_uri(self, tmp_path):
        """PNG file should be converted to JPEG data URI."""
        image_path = tmp_path / "test.png"
        image_path.write_bytes(PNG_1X1)

        data_uri = _encode_image_to_base64_uri(str(image_path))

        # Should be JPEG (converted by resize pipeline)
        assert data_uri.startswith("data:image/jpeg;base64,")

    def test_encode_file_not_found_raises(self):
        """Non-existent file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            _encode_image_to_base64_uri("/nonexistent/image.jpg")


class TestImageAnalysisTool:
    """Test image_analysis_tool LangChain tool."""

    @pytest.fixture
    def mock_llm_response(self):
        """Mock Vision API response."""
        return ImageAnalysisResult(
            visual_description="Red canvas sneakers with white rubber sole and blue laces",
            identified_colors=["red", "white", "blue"],
            materials=["canvas", "rubber"],
            style_tags=["casual", "sporty", "modern"],
            estimated_dimensions="Standard adult shoe size",
        )

    def test_tool_analyzes_image_successfully(self, tmp_path, mock_llm_response):
        """Tool should invoke Vision API and return ImageAnalysisResult."""
        # Create test image
        test_img = Image.new("RGB", (100, 100), color="red")
        image_path = tmp_path / "sneakers.jpg"
        test_img.save(image_path, "JPEG")

        # Mock LLM
        with patch("autifyme_agents.tools.image_analysis_tool.get_llm") as mock_get_llm:
            mock_llm = Mock()
            mock_structured = Mock()
            mock_structured.invoke.return_value = mock_llm_response
            mock_llm.with_structured_output.return_value = mock_structured
            mock_get_llm.return_value = mock_llm

            # Invoke tool
            result = image_analysis_tool.invoke({"image_path": str(image_path)})

            # Verify result
            assert isinstance(result, ImageAnalysisResult)
            assert result.visual_description == mock_llm_response.visual_description
            assert "red" in result.identified_colors

            # Verify LLM was called with correct model
            mock_get_llm.assert_called_once_with(provider="openai", model="gpt-4.1-mini")

            # Verify with_structured_output was called with correct schema and parameters
            mock_llm.with_structured_output.assert_called_once_with(
                ImageAnalysisResult,
                method="json_schema",
                include_raw=False,
            )

            # Verify invoke was called with messages containing image
            call_args = mock_structured.invoke.call_args[0][0]
            assert len(call_args) == 1
            assert call_args[0]["role"] == "user"
            assert any(c["type"] == "image_url" for c in call_args[0]["content"])

    def test_tool_resizes_large_image_before_encoding(self, tmp_path, mock_llm_response):
        """Tool should resize large images to prevent token overflow."""
        # Create large 4000x3000 image
        large_img = Image.new("RGB", (4000, 3000), color="blue")
        image_path = tmp_path / "large_photo.jpg"
        large_img.save(image_path, "JPEG")

        with patch("autifyme_agents.tools.image_analysis_tool.get_llm") as mock_get_llm:
            mock_llm = Mock()
            mock_structured = Mock()
            mock_structured.invoke.return_value = mock_llm_response
            mock_llm.with_structured_output.return_value = mock_structured
            mock_get_llm.return_value = mock_llm

            # Invoke tool
            result = image_analysis_tool.invoke({"image_path": str(image_path)})

            assert isinstance(result, ImageAnalysisResult)

            # Verify the base64 data URI was created
            call_args = mock_structured.invoke.call_args[0][0]
            image_content = [c for c in call_args[0]["content"] if c["type"] == "image_url"][0]
            data_uri = image_content["image_url"]["url"]

            # Decode base64 and verify image was resized
            encoded_part = data_uri.split(",", 1)[1]
            decoded_bytes = base64.b64decode(encoded_part)
            resized_img = Image.open(io.BytesIO(decoded_bytes))

            # Should be resized to max 2048px
            assert max(resized_img.width, resized_img.height) == 2048
            # Should preserve aspect ratio (4:3 → 2048:1536)
            assert resized_img.width == 2048
            assert resized_img.height == 1536

    def test_tool_handles_file_not_found(self):
        """Tool should raise FileNotFoundError for missing images."""
        with pytest.raises(FileNotFoundError, match="Image file not found"):
            image_analysis_tool.invoke({"image_path": "/nonexistent/image.jpg"})

    def test_tool_returns_correct_type(self, tmp_path, mock_llm_response):
        """Tool should return ImageAnalysisResult, not dict."""
        test_img = Image.new("RGB", (50, 50), color="green")
        image_path = tmp_path / "test.jpg"
        test_img.save(image_path, "JPEG")

        with patch("autifyme_agents.tools.image_analysis_tool.get_llm") as mock_get_llm:
            mock_llm = Mock()
            mock_structured = Mock()
            mock_structured.invoke.return_value = mock_llm_response
            mock_llm.with_structured_output.return_value = mock_structured
            mock_get_llm.return_value = mock_llm

            result = image_analysis_tool.invoke({"image_path": str(image_path)})

            # Must be Pydantic model, not dict
            assert isinstance(result, ImageAnalysisResult)
            assert hasattr(result, "model_dump")

    def test_tool_raises_on_unexpected_type(self, tmp_path):
        """Tool should raise ValueError if LLM returns unexpected type."""
        test_img = Image.new("RGB", (50, 50), color="yellow")
        image_path = tmp_path / "test.jpg"
        test_img.save(image_path, "JPEG")

        with patch("autifyme_agents.tools.image_analysis_tool.get_llm") as mock_get_llm:
            mock_llm = Mock()
            mock_structured = Mock()
            # Return dict instead of ImageAnalysisResult
            mock_structured.invoke.return_value = {"invalid": "type"}
            mock_llm.with_structured_output.return_value = mock_structured
            mock_get_llm.return_value = mock_llm

            with pytest.raises(ValueError, match="Unexpected result type from Vision API"):
                image_analysis_tool.invoke({"image_path": str(image_path)})


class TestTokenOptimization:
    """Test that image optimization reduces token usage."""

    def test_large_image_encoding_size_reduction(self, tmp_path):
        """Verify large images result in manageable base64 size."""
        # Create 5000x4000 image (simulates large phone photo)
        large_img = Image.new("RGB", (5000, 4000), color=(128, 128, 128))
        image_path = tmp_path / "phone_photo.jpg"
        large_img.save(image_path, "JPEG", quality=95)

        # Get data URI
        data_uri = _encode_image_to_base64_uri(str(image_path))

        # Extract base64 portion
        encoded_part = data_uri.split(",", 1)[1]

        # Verify base64 length is reasonable (not 300k+ tokens)
        # Base64 encoding increases size by ~33%, and tokens are ~4 chars
        # Expected: 2048x1536 JPEG at quality 85 ≈ 100-200KB → 133-266KB base64 → ~10k-20k tokens
        base64_length = len(encoded_part)
        estimated_tokens = base64_length // 4  # Rough estimate

        # Should be well under 50k tokens (was ~300k before optimization)
        assert estimated_tokens < 50000, f"Token estimate {estimated_tokens} still too high"

        # Verify actual resized dimensions
        decoded_bytes = base64.b64decode(encoded_part)
        resized_img = Image.open(io.BytesIO(decoded_bytes))
        assert max(resized_img.width, resized_img.height) == 2048
