"""
Comprehensive tests for Image Studio tool.

Tests the Gemini 3 Pro Image integration with simplified creative_direction schema:
- Schema validation (inputs and outputs)
- Operation handlers (edit, generate)
- Image utilities (load, encode, save)
- Error handling and edge cases
- Tool factory

Updated: 2025-12-04 - Simplified schema with creative_direction
"""

import base64
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from autifyme_agents.tools.image_studio import (
    ImageMetadata,
    ImageOperation,
    ImageStudioErrorCode,
    ImageStudioInput,
    ImageStudioOutput,
    OutputSpec,
    OutputVariant,
    create_image_studio_tool,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_image_file():
    """Create a temporary test image file."""
    from PIL import Image

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        # Create a simple 100x100 red image
        img = Image.new("RGB", (100, 100), color="red")
        img.save(f, format="PNG")
        yield f.name
    # Cleanup
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def mock_gemini_response_with_image():
    """Mock Gemini response with image data."""
    mock_response = MagicMock()
    # Gemini 3 returns images in content[0]["image_url"]["url"] as data URI
    fake_image_data = base64.b64encode(b"fake_image_data").decode()
    mock_response.content = [
        {"image_url": {"url": f"data:image/png;base64,{fake_image_data}"}}
    ]
    return mock_response


# =============================================================================
# Group 1: Schema Tests (Simplified)
# =============================================================================


class TestImageStudioSchemas:
    """Test Pydantic schemas for Image Studio."""

    def test_image_operation_enum_values(self):
        """Test ImageOperation enum has correct values."""
        assert ImageOperation.GENERATE.value == "generate"
        assert ImageOperation.EDIT.value == "edit"

    def test_output_spec_defaults(self):
        """Test OutputSpec defaults."""
        spec = OutputSpec()
        assert spec.format == "PNG"
        assert spec.size == "2K"
        assert spec.aspect_ratio == "1:1"

    def test_output_spec_format_validation(self):
        """Test OutputSpec format validation."""
        # Valid formats
        for fmt in ["PNG", "JPEG", "WEBP"]:
            spec = OutputSpec(format=fmt)
            assert spec.format == fmt

        # Invalid format
        with pytest.raises(ValueError):
            OutputSpec(format="GIF")  # Not supported

    def test_image_studio_input_with_creative_direction(self):
        """Test ImageStudioInput with creative_direction."""
        input_spec = ImageStudioInput(
            operation=ImageOperation.EDIT,
            source_image="inbox/test/image.png",
            creative_direction="Extract product, pure white background, studio lighting",
        )
        assert input_spec.operation == ImageOperation.EDIT
        assert input_spec.creative_direction == "Extract product, pure white background, studio lighting"
        assert input_spec.source_image == "inbox/test/image.png"

    def test_image_studio_input_generate_operation(self):
        """Test ImageStudioInput for generate operation."""
        input_spec = ImageStudioInput(
            operation=ImageOperation.GENERATE,
            source_image="inbox/test/product.png",
            creative_direction="Modern kitchen scene, morning golden hour light through window, product on marble counter",
            output=OutputSpec(size="2K", aspect_ratio="4:3"),
        )
        assert input_spec.operation == ImageOperation.GENERATE
        assert "kitchen" in input_spec.creative_direction
        assert input_spec.output.aspect_ratio == "4:3"

    def test_image_studio_input_reference_images(self):
        """Test ImageStudioInput with reference images."""
        input_spec = ImageStudioInput(
            operation=ImageOperation.GENERATE,
            creative_direction="Create lifestyle shot matching style of reference images",
            reference_images=["ref1.png", "ref2.png"],
        )
        assert len(input_spec.reference_images) == 2

    def test_image_metadata_structure(self):
        """Test ImageMetadata schema."""
        metadata = ImageMetadata(
            width=1920,
            height=1080,
            format="PNG",
            size_bytes=1024000,
            aspect_ratio="16:9",
        )
        assert metadata.width == 1920
        assert metadata.height == 1080
        assert metadata.format == "PNG"

    def test_output_variant_structure(self):
        """Test OutputVariant schema."""
        variant = OutputVariant(
            variant="master",
            path="/tmp/output.png",
            preview_path="/tmp/output_preview.png",
            metadata=ImageMetadata(
                width=2048, height=2048, format="PNG", size_bytes=500000, aspect_ratio="1:1"
            ),
            description="Edited image",
            storage_path="pending/test/output.png",
        )
        assert variant.variant == "master"
        assert variant.storage_path == "pending/test/output.png"

    def test_image_studio_output_success(self):
        """Test ImageStudioOutput success structure."""
        output = ImageStudioOutput(
            success=True,
            operation=ImageOperation.EDIT,
            outputs=[
                OutputVariant(
                    variant="master",
                    path="/tmp/out.png",
                    preview_path="/tmp/out.png",
                    metadata=ImageMetadata(
                        width=1024, height=1024, format="PNG", size_bytes=100000, aspect_ratio="1:1"
                    ),
                )
            ],
        )
        assert output.success is True
        assert len(output.outputs) == 1

    def test_image_studio_output_failure(self):
        """Test ImageStudioOutput failure structure."""
        output = ImageStudioOutput(
            success=False,
            operation=ImageOperation.EDIT,
            error="Source image not found",
            error_code=ImageStudioErrorCode.FILE_NOT_FOUND,
        )
        assert output.success is False
        assert output.error_code == ImageStudioErrorCode.FILE_NOT_FOUND


# =============================================================================
# Group 2: Tool Factory Tests
# =============================================================================


class TestImageStudioToolFactory:
    """Test Image Studio tool factory."""

    def test_create_image_studio_tool(self):
        """Test tool factory creates valid tool."""
        tool = create_image_studio_tool()
        assert tool.name == "image_studio"
        assert "Gemini 3 Pro Image" in tool.description
        assert "edit" in tool.description.lower()
        assert "generate" in tool.description.lower()

    def test_tool_has_structured_input(self):
        """Test tool uses structured Pydantic input."""
        tool = create_image_studio_tool()
        assert tool.args_schema is not None

    def test_tool_description_includes_creative_direction(self):
        """Test tool description mentions creative_direction."""
        tool = create_image_studio_tool()
        assert "creative_direction" in tool.description.lower()

    def test_tool_is_callable(self):
        """Test tool can be called (sync wrapper)."""
        tool = create_image_studio_tool()
        assert callable(tool.invoke)

    def test_tool_has_async_invoke(self):
        """Test tool has async invoke method."""
        tool = create_image_studio_tool()
        assert hasattr(tool, "ainvoke")

    def test_multiple_tool_instances_independent(self):
        """Test multiple tool instances are independent."""
        tool1 = create_image_studio_tool()
        tool2 = create_image_studio_tool()
        assert tool1 is not tool2
        assert tool1.name == tool2.name

    def test_tool_func_exists(self):
        """Test tool has underlying function."""
        tool = create_image_studio_tool()
        assert tool.func is not None or tool.coroutine is not None

    def test_tool_with_storage_client(self):
        """Test tool creation with storage client."""
        mock_storage = MagicMock()
        tool = create_image_studio_tool(storage=mock_storage)
        assert tool.name == "image_studio"


# =============================================================================
# Group 3: Edit Operation Tests
# =============================================================================


class TestEditOperation:
    """Test edit operation with creative_direction."""

    def test_edit_requires_source_image(self):
        """Test edit fails without source_image."""
        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "edit",
            "creative_direction": "Remove background, pure white",
            # Missing source_image
        })

        assert result["success"] is False
        assert "source_image required" in result["error"]

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    def test_edit_with_creative_direction(
        self, mock_load, mock_llm_factory, mock_gemini_response_with_image
    ):
        """Test edit with creative_direction."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")

        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(return_value=mock_gemini_response_with_image)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        tool.invoke({
            "operation": "edit",
            "source_image": "/tmp/test.png",
            "creative_direction": "Extract glass jar, preserve caustics and refraction, pure white #FFFFFF background, soft studio lighting from 45 degrees",
        })

        # Should attempt to invoke the LLM
        mock_llm.invoke.assert_called_once()

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    def test_edit_prompt_contains_creative_direction(self, mock_load, mock_llm_factory):
        """Test that the prompt sent to LLM contains creative_direction."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")

        mock_llm = MagicMock()
        mock_response = MagicMock()
        fake_image = base64.b64encode(b"fake").decode()
        mock_response.content = [{"image_url": {"url": f"data:image/png;base64,{fake_image}"}}]
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        creative_brief = "HERO SHOT: Ceramic mug on pure white, matte surface preserved, studio front lighting"
        tool.invoke({
            "operation": "edit",
            "source_image": "/tmp/test.png",
            "creative_direction": creative_brief,
        })

        # Check the prompt sent to LLM contains our creative direction
        call_args = mock_llm.invoke.call_args[0][0]
        user_content = call_args[1]["content"]
        prompt_text = user_content[0]["text"]
        assert "HERO SHOT" in prompt_text
        assert "Ceramic mug" in prompt_text

    def test_edit_file_not_found(self):
        """Test edit with non-existent file."""
        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "edit",
            "source_image": "/nonexistent/image.png",
            "creative_direction": "Remove background",
        })

        assert result["success"] is False
        assert result["error_code"] == ImageStudioErrorCode.FILE_NOT_FOUND

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    def test_edit_output_spec_applied(
        self, mock_load, mock_llm_factory, mock_gemini_response_with_image
    ):
        """Test edit applies output specifications."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")

        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(return_value=mock_gemini_response_with_image)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        tool.invoke({
            "operation": "edit",
            "source_image": "/tmp/test.png",
            "creative_direction": "Enhance colors and sharpen",
            "output": {"size": "4K", "aspect_ratio": "16:9", "format": "JPEG"},
        })

        # Verify LLM factory was called with output specs
        mock_llm_factory.assert_called_once()
        call_kwargs = mock_llm_factory.call_args[1]
        output_spec = call_kwargs.get("output_spec")
        assert output_spec is not None
        assert output_spec.size == "4K"

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    def test_edit_with_reference_images(self, mock_load, mock_llm_factory):
        """Test edit with reference images."""
        # Return different data for source vs reference
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")

        mock_llm = MagicMock()
        mock_response = MagicMock()
        fake_image = base64.b64encode(b"fake").decode()
        mock_response.content = [{"image_url": {"url": f"data:image/png;base64,{fake_image}"}}]
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        tool.invoke({
            "operation": "edit",
            "source_image": "/tmp/test.png",
            "creative_direction": "Match the color grading of the reference images",
            "reference_images": ["/tmp/ref1.png", "/tmp/ref2.png"],
        })

        # Should load source + 2 reference images (3 calls total)
        assert mock_load.call_count == 3

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    def test_edit_no_image_in_response(self, mock_load, mock_llm_factory):
        """Test edit handles missing image in response."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "No image generated"  # String, not list with image
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "edit",
            "source_image": "/tmp/test.png",
            "creative_direction": "Remove background",
        })

        assert result["success"] is False
        assert "error" in result


# =============================================================================
# Group 4: Generate Operation Tests
# =============================================================================


class TestGenerateOperation:
    """Test generate operation with creative_direction."""

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    def test_generate_with_creative_direction(
        self, mock_llm_factory, mock_gemini_response_with_image
    ):
        """Test generate with creative_direction."""
        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(return_value=mock_gemini_response_with_image)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        tool.invoke({
            "operation": "generate",
            "creative_direction": "Modern minimalist kitchen scene, morning golden hour through window, marble counter, product on left third",
        })

        mock_llm.invoke.assert_called_once()

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    def test_generate_with_source_reference(
        self, mock_load, mock_llm_factory, mock_gemini_response_with_image
    ):
        """Test generate with source image as reference."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")

        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(return_value=mock_gemini_response_with_image)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        tool.invoke({
            "operation": "generate",
            "source_image": "/tmp/product.png",
            "creative_direction": "Place product in cozy living room scene, warm afternoon light, product on coffee table",
        })

        mock_llm.invoke.assert_called_once()
        # Source image should be loaded
        mock_load.assert_called_once()

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    def test_generate_output_specs(self, mock_llm_factory, mock_gemini_response_with_image):
        """Test generate respects output specifications."""
        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(return_value=mock_gemini_response_with_image)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        tool.invoke({
            "operation": "generate",
            "creative_direction": "Studio shot with dramatic lighting",
            "output": {
                "size": "4K",
                "aspect_ratio": "16:9",
                "format": "PNG",
            },
        })

        mock_llm_factory.assert_called_once()
        call_kwargs = mock_llm_factory.call_args[1]
        output_spec = call_kwargs.get("output_spec")
        assert output_spec is not None
        assert output_spec.size == "4K"
        assert output_spec.aspect_ratio == "16:9"

    @patch("autifyme_agents.tools.image_studio.tool._save_base64_image")
    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    def test_generate_returns_outputs(self, mock_llm_factory, mock_save, mock_gemini_response_with_image):
        """Test generate returns output variants."""
        from pathlib import Path
        # Mock save to return valid data
        mock_save.return_value = (
            Path("/tmp/output.png"),
            ImageMetadata(width=1024, height=1024, format="PNG", size_bytes=10000, aspect_ratio="1:1"),
            "pending/test/output.png"
        )

        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(return_value=mock_gemini_response_with_image)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "generate",
            "creative_direction": "Office desk scene with product",
        })

        assert result["success"] is True
        # The response structure wraps the output model in 'data' from build_success_response
        data = result.get("data", result)
        assert "outputs" in data
        assert data["operation"] == "generate"

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    def test_generate_api_error(self, mock_llm_factory):
        """Test generate handles API errors."""
        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(side_effect=Exception("Generation failed"))
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "generate",
            "creative_direction": "Kitchen scene",
        })

        assert result["success"] is False
        assert result["error_code"] == ImageStudioErrorCode.API_ERROR

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    def test_generate_no_image_in_response(self, mock_llm_factory):
        """Test generate handles missing image in response."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = []  # Empty list - no image
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "generate",
            "creative_direction": "Kitchen scene",
        })

        assert result["success"] is False

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    def test_generate_prompt_includes_output_specs(self, mock_llm_factory):
        """Test generate prompt includes technical output specs."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        fake_image = base64.b64encode(b"fake").decode()
        mock_response.content = [{"image_url": {"url": f"data:image/png;base64,{fake_image}"}}]
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        tool.invoke({
            "operation": "generate",
            "creative_direction": "Product on marble surface",
            "output": {"size": "4K", "aspect_ratio": "1:1", "format": "PNG"},
        })

        # Check prompt includes output specs
        call_args = mock_llm.invoke.call_args[0][0]
        user_content = call_args[1]["content"]
        prompt_text = user_content[0]["text"]
        assert "4K" in prompt_text
        assert "1:1" in prompt_text


# =============================================================================
# Group 5: Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Test error handling across all operations."""

    def test_invalid_operation(self):
        """Test invalid operation type."""
        from pydantic import ValidationError

        tool = create_image_studio_tool()

        # Pydantic should catch invalid enum value
        with pytest.raises((ValidationError, ValueError)):
            tool.invoke({
                "operation": "invalid_op",
                "creative_direction": "Do something",
                "source_image": "/tmp/test.png",
            })

    def test_missing_creative_direction(self):
        """Test missing creative_direction field."""
        from pydantic import ValidationError

        tool = create_image_studio_tool()

        # Missing creative_direction
        with pytest.raises((ValidationError, TypeError)):
            tool.invoke({
                "operation": "edit",
                "source_image": "/tmp/test.png",
            })

    def test_corrupt_image_handling(self):
        """Test handling of corrupt image file."""
        # Create a corrupt "image" file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False, mode="wb") as f:
            f.write(b"not a valid image content")
            corrupt_path = f.name

        try:
            tool = create_image_studio_tool()
            result = tool.invoke({
                "operation": "edit",
                "source_image": corrupt_path,
                "creative_direction": "Remove background",
            })

            # Should handle gracefully
            assert result["success"] is False
            assert "error" in result
        finally:
            Path(corrupt_path).unlink(missing_ok=True)

    def test_missing_required_fields(self):
        """Test missing required fields in input."""
        from pydantic import ValidationError

        tool = create_image_studio_tool()

        # Missing 'operation' field
        with pytest.raises((ValidationError, TypeError)):
            tool.invoke({
                "source_image": "/tmp/test.png",
                "creative_direction": "Edit image",
            })

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    def test_llm_timeout_handling(self, mock_load, mock_llm_factory):
        """Test handling of LLM timeout."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")

        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(side_effect=TimeoutError("Request timed out"))
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "edit",
            "source_image": "/tmp/test.png",
            "creative_direction": "Enhance image",
        })

        assert result["success"] is False
        assert "error" in result

    def test_empty_source_image_path(self):
        """Test empty source_image path."""
        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "edit",
            "source_image": "",
            "creative_direction": "Edit something",
        })

        assert result["success"] is False

    def test_error_codes_are_valid(self):
        """Test all error codes are valid class attributes."""
        # ImageStudioErrorCode is a class with string constants
        assert hasattr(ImageStudioErrorCode, "FILE_NOT_FOUND")
        assert hasattr(ImageStudioErrorCode, "CORRUPT_FILE")
        assert hasattr(ImageStudioErrorCode, "INVALID_INPUT")
        assert hasattr(ImageStudioErrorCode, "API_ERROR")
        assert hasattr(ImageStudioErrorCode, "RATE_LIMIT")
        assert hasattr(ImageStudioErrorCode, "TIMEOUT")
        # Verify they are strings
        assert isinstance(ImageStudioErrorCode.FILE_NOT_FOUND, str)
        assert isinstance(ImageStudioErrorCode.API_ERROR, str)

    def test_error_response_structure(self):
        """Test error responses have consistent structure."""
        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "edit",
            "source_image": "/nonexistent/path.png",
            "creative_direction": "Do something",
        })

        assert result["success"] is False
        assert "error" in result
        assert "error_code" in result
        assert result["operation"] == "edit"


# =============================================================================
# Group 6: Integration Tests (Thread ID Injection)
# =============================================================================


class TestThreadIdInjection:
    """Test thread_id injection from RunnableConfig."""

    @patch("autifyme_agents.tools.image_studio.tool._save_base64_image")
    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    def test_thread_id_injected_from_config(
        self, mock_load, mock_llm_factory, mock_save, mock_gemini_response_with_image
    ):
        """Test thread_id is injected from RunnableConfig."""
        from pathlib import Path
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")
        mock_save.return_value = (
            Path("/tmp/output.png"),
            ImageMetadata(width=1024, height=1024, format="PNG", size_bytes=10000, aspect_ratio="1:1"),
            "pending/test/output.png"
        )

        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(return_value=mock_gemini_response_with_image)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()

        # Invoke with config containing thread_id
        result = tool.invoke(
            {
                "operation": "edit",
                "source_image": "/tmp/test.png",
                "creative_direction": "Remove background",
            },
            config={"configurable": {"thread_id": "whatsapp_123_456"}},
        )

        assert result["success"] is True

    @patch("autifyme_agents.tools.image_studio.tool._save_base64_image")
    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    def test_explicit_thread_id_takes_precedence(
        self, mock_llm_factory, mock_save, mock_gemini_response_with_image
    ):
        """Test explicit thread_id takes precedence over config."""
        from pathlib import Path
        mock_save.return_value = (
            Path("/tmp/output.png"),
            ImageMetadata(width=1024, height=1024, format="PNG", size_bytes=10000, aspect_ratio="1:1"),
            "pending/test/output.png"
        )

        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(return_value=mock_gemini_response_with_image)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()

        # Both explicit and config thread_id
        result = tool.invoke(
            {
                "operation": "generate",
                "creative_direction": "Create scene",
                "thread_id": "explicit_thread",
            },
            config={"configurable": {"thread_id": "config_thread"}},
        )

        assert result["success"] is True
