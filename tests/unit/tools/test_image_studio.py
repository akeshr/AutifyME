"""
Comprehensive tests for Image Studio tool.

Tests the Gemini 3 Pro Image integration with labeled images architecture:
- Schema validation (ImageInput, structured specs, outputs)
- Image processing with labeled images
- Error handling and edge cases
- Tool factory

Updated: 2025-12-04 - Labeled images architecture (no operation distinction)
"""

import base64
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from autifyme_agents.tools.image_studio import (
    BackgroundSpec,
    CompositionSpec,
    ExtractionSpec,
    ImageInput,
    ImageMetadata,
    ImageStudioErrorCode,
    ImageStudioInput,
    ImageStudioOutput,
    LightingSpec,
    MaterialTreatmentSpec,
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
# Group 1: Schema Tests (Labeled Images Architecture)
# =============================================================================


class TestImageStudioSchemas:
    """Test Pydantic schemas for Image Studio."""

    def test_image_input_structure(self):
        """Test ImageInput schema."""
        img = ImageInput(path="inbox/thread/photo.jpg", label="product")
        assert img.path == "inbox/thread/photo.jpg"
        assert img.label == "product"

    def test_image_input_various_labels(self):
        """Test ImageInput with various label types."""
        labels = ["product", "style_ref", "mood", "background", "hero", "variant"]
        for label in labels:
            img = ImageInput(path="inbox/test/img.jpg", label=label)
            assert img.label == label

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

    def test_image_studio_input_with_labeled_images(self):
        """Test ImageStudioInput with labeled images."""
        input_spec = ImageStudioInput(
            images=[
                ImageInput(path="inbox/test/product.jpg", label="product"),
                ImageInput(path="inbox/test/style.jpg", label="style_ref"),
            ],
            extraction=ExtractionSpec(
                target_description="Extract [product] from background",
                isolation="complete",
            ),
            background=BackgroundSpec(treatment="pure white"),
        )
        assert len(input_spec.images) == 2
        assert input_spec.images[0].label == "product"
        assert input_spec.extraction.target_description == "Extract [product] from background"

    def test_image_studio_input_with_all_specs(self):
        """Test ImageStudioInput with multiple specs."""
        input_spec = ImageStudioInput(
            images=[ImageInput(path="inbox/test/jar.jpg", label="product")],
            extraction=ExtractionSpec(target_description="Glass jar [product]"),
            background=BackgroundSpec(treatment="solid white", color="#FFFFFF"),
            lighting=LightingSpec(
                type="soft studio",
                direction="45 degrees camera-left",
                shadows="contact shadow",
            ),
            composition=CompositionSpec(product_coverage="80% frame", position="centered"),
            material_treatment=MaterialTreatmentSpec(
                primary_material="clear glass",
                rendering_notes="preserve caustics and refraction",
            ),
            creative_direction="Premium hero shot",
            output=OutputSpec(size="2K", aspect_ratio="1:1"),
        )
        assert input_spec.lighting.type == "soft studio"
        assert input_spec.material_treatment.primary_material == "clear glass"

    def test_image_studio_input_empty_images_for_generation(self):
        """Test ImageStudioInput with no images (pure generation)."""
        input_spec = ImageStudioInput(
            images=[],
            creative_direction="Generate luxury bathroom scene",
        )
        assert len(input_spec.images) == 0

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
            description="Processed image",
            storage_path="pending/test/output.png",
        )
        assert variant.variant == "master"
        assert variant.storage_path == "pending/test/output.png"

    def test_image_studio_output_success(self):
        """Test ImageStudioOutput success structure."""
        output = ImageStudioOutput(
            success=True,
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
            error="Image not found",
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

    def test_tool_has_structured_input(self):
        """Test tool uses structured Pydantic input."""
        tool = create_image_studio_tool()
        assert tool.args_schema is not None

    def test_tool_description_includes_labeled_images(self):
        """Test tool description mentions labeled images."""
        tool = create_image_studio_tool()
        assert "label" in tool.description.lower()

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
# Group 3: Image Processing Tests (Labeled Images)
# =============================================================================


class TestImageProcessing:
    """Test image processing with labeled images architecture."""

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    def test_process_with_labeled_images(
        self, mock_load, mock_llm_factory, mock_gemini_response_with_image
    ):
        """Test processing with labeled images."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")

        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(return_value=mock_gemini_response_with_image)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        tool.invoke({
            "images": [{"path": "/tmp/test.png", "label": "product"}],
            "extraction": {"target_description": "Extract [product]", "isolation": "complete"},
            "background": {"treatment": "pure white"},
        })

        # Should attempt to invoke the LLM
        mock_llm.invoke.assert_called_once()

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    def test_prompt_contains_image_labels(self, mock_load, mock_llm_factory):
        """Test that the prompt sent to LLM contains image labels."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")

        mock_llm = MagicMock()
        mock_response = MagicMock()
        fake_image = base64.b64encode(b"fake").decode()
        mock_response.content = [{"image_url": {"url": f"data:image/png;base64,{fake_image}"}}]
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        tool.invoke({
            "images": [
                {"path": "/tmp/product.png", "label": "hero"},
                {"path": "/tmp/style.png", "label": "mood_ref"},
            ],
            "lighting": {"type": "match [mood_ref] lighting"},
            "creative_direction": "Place [hero] in warm scene",
        })

        # Check the prompt sent to LLM contains labels
        call_args = mock_llm.invoke.call_args[0][0]
        user_content = call_args[1]["content"]
        prompt_text = user_content[0]["text"]
        assert "[hero]" in prompt_text
        assert "[mood_ref]" in prompt_text

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    def test_file_not_found(self, mock_llm_factory):
        """Test with non-existent file - graceful degradation logs warning, continues."""
        # LLM returns no image, so tool fails after image load warning
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "I cannot process without an image."
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "images": [{"path": "/nonexistent/image.png", "label": "product"}],
            "background": {"treatment": "white"},
        })

        # Graceful degradation: image load fails with warning, LLM returns no image
        assert result["success"] is False
        assert result["error_code"] == ImageStudioErrorCode.API_ERROR

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    def test_output_spec_applied(
        self, mock_load, mock_llm_factory, mock_gemini_response_with_image
    ):
        """Test output specifications are applied."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")

        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(return_value=mock_gemini_response_with_image)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        tool.invoke({
            "images": [{"path": "/tmp/test.png", "label": "source"}],
            "creative_direction": "Enhance colors",
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
    def test_multiple_images_loaded(self, mock_load, mock_llm_factory):
        """Test multiple labeled images are loaded."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")

        mock_llm = MagicMock()
        mock_response = MagicMock()
        fake_image = base64.b64encode(b"fake").decode()
        mock_response.content = [{"image_url": {"url": f"data:image/png;base64,{fake_image}"}}]
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        tool.invoke({
            "images": [
                {"path": "/tmp/img1.png", "label": "product"},
                {"path": "/tmp/img2.png", "label": "style_ref"},
                {"path": "/tmp/img3.png", "label": "background"},
            ],
            "creative_direction": "Compose [product] with [style_ref] lighting on [background]",
        })

        # Should load all 3 images
        assert mock_load.call_count == 3

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    def test_no_image_in_response(self, mock_load, mock_llm_factory):
        """Test handles missing image in response."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "No image generated"  # String, not list with image
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "images": [{"path": "/tmp/test.png", "label": "source"}],
            "background": {"treatment": "white"},
        })

        assert result["success"] is False
        assert "error" in result


# =============================================================================
# Group 4: Pure Generation Tests (No Source Images)
# =============================================================================


class TestPureGeneration:
    """Test pure generation (no source images)."""

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    def test_generate_without_images(
        self, mock_llm_factory, mock_gemini_response_with_image
    ):
        """Test generation with no source images."""
        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(return_value=mock_gemini_response_with_image)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        tool.invoke({
            "images": [],
            "creative_direction": "Generate luxury bathroom vanity scene, morning light",
        })

        mock_llm.invoke.assert_called_once()

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    def test_generate_output_specs(self, mock_llm_factory, mock_gemini_response_with_image):
        """Test generation respects output specifications."""
        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(return_value=mock_gemini_response_with_image)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        tool.invoke({
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
        """Test generation returns output variants."""
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
            "creative_direction": "Office desk scene",
        })

        assert result["success"] is True
        data = result.get("data", result)
        assert "outputs" in data

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    def test_generate_api_error(self, mock_llm_factory):
        """Test generation handles API errors."""
        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(side_effect=Exception("Generation failed"))
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "creative_direction": "Kitchen scene",
        })

        assert result["success"] is False
        assert result["error_code"] == ImageStudioErrorCode.API_ERROR


# =============================================================================
# Group 5: Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Test error handling across all operations."""

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    def test_corrupt_image_handling(self, mock_llm_factory):
        """Test handling of corrupt image file - graceful degradation logs warning."""
        # LLM returns no image after corrupt image is skipped
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Unable to generate."
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        # Create a corrupt "image" file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False, mode="wb") as f:
            f.write(b"not a valid image content")
            corrupt_path = f.name

        try:
            tool = create_image_studio_tool()
            result = tool.invoke({
                "images": [{"path": corrupt_path, "label": "source"}],
                "background": {"treatment": "white"},
            })

            # Graceful degradation: corrupt image skipped with warning, LLM returns no image
            assert result["success"] is False
            assert "error" in result
        finally:
            Path(corrupt_path).unlink(missing_ok=True)

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
            "images": [{"path": "/tmp/test.png", "label": "source"}],
            "creative_direction": "Enhance image",
        })

        assert result["success"] is False
        assert "error" in result

    def test_error_codes_are_valid(self):
        """Test all error codes are valid class attributes."""
        assert hasattr(ImageStudioErrorCode, "FILE_NOT_FOUND")
        assert hasattr(ImageStudioErrorCode, "CORRUPT_FILE")
        assert hasattr(ImageStudioErrorCode, "INVALID_INPUT")
        assert hasattr(ImageStudioErrorCode, "API_ERROR")
        assert hasattr(ImageStudioErrorCode, "RATE_LIMIT")
        assert hasattr(ImageStudioErrorCode, "TIMEOUT")
        # Verify they are strings
        assert isinstance(ImageStudioErrorCode.FILE_NOT_FOUND, str)
        assert isinstance(ImageStudioErrorCode.API_ERROR, str)

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    def test_error_response_structure(self, mock_llm_factory):
        """Test error responses have consistent structure."""
        # LLM returns no image to trigger error response
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Cannot process request."
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "images": [{"path": "/nonexistent/path.png", "label": "source"}],
            "creative_direction": "Do something",
        })

        assert result["success"] is False
        assert "error" in result
        assert "error_code" in result


# =============================================================================
# Group 6: Thread ID Injection Tests
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
                "images": [{"path": "/tmp/test.png", "label": "source"}],
                "creative_direction": "Process image",
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
                "creative_direction": "Create scene",
                "thread_id": "explicit_thread",
            },
            config={"configurable": {"thread_id": "config_thread"}},
        )

        assert result["success"] is True
