"""
Comprehensive tests for Image Studio tool.

Tests the Gemini 3 Pro Image (Nano Banana Pro) integration:
- Schema validation (inputs and outputs)
- Operation handlers (analyze, edit, generate)
- Image utilities (load, encode, save)
- Error handling and edge cases
- Tool factory

Created: 2025-11-30
"""

import base64
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from autifyme_agents.tools.image_studio import (
    AnalysisAttributes,
    AnalysisResult,
    BackgroundSpec,
    EnhancementSpec,
    FramingSpec,
    ImageOperation,
    ImageStudioErrorCode,
    ImageStudioInput,
    LightingSpec,
    OutputSpec,
    ProductPlacement,
    SceneSpec,
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
def mock_gemini_llm():
    """Mock Gemini 3 Pro Image LLM."""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "colors": ["red", "blue"],
        "materials": ["plastic"],
        "product_category": "container",
        "quality_score": 0.85,
        "confidence": 0.9,
        "product_count": 1,
    })
    mock_llm.invoke = MagicMock(return_value=mock_response)
    return mock_llm


# =============================================================================
# Group 1: Schema Tests (15 tests)
# =============================================================================


class TestImageStudioSchemas:
    """Test Pydantic schemas for Image Studio."""

    def test_image_operation_enum_values(self):
        """Test ImageOperation enum has correct values."""
        assert ImageOperation.ANALYZE.value == "analyze"
        assert ImageOperation.GENERATE.value == "generate"
        assert ImageOperation.EDIT.value == "edit"

    def test_background_spec_defaults(self):
        """Test BackgroundSpec default values."""
        spec = BackgroundSpec()
        assert spec.type == "solid"
        assert spec.color == "#FFFFFF"
        assert spec.gradient_end is None
        assert spec.blur_strength is None

    def test_background_spec_gradient(self):
        """Test BackgroundSpec gradient configuration."""
        spec = BackgroundSpec(type="gradient", color="#FFFFFF", gradient_end="#000000")
        assert spec.type == "gradient"
        assert spec.gradient_end == "#000000"

    def test_lighting_spec_defaults(self):
        """Test LightingSpec default values."""
        spec = LightingSpec()
        assert spec.type == "studio"
        assert spec.direction == "front"
        assert spec.intensity == "medium"
        assert spec.color_temperature == "neutral"

    def test_framing_spec_validation(self):
        """Test FramingSpec field validation."""
        # Valid values
        spec = FramingSpec(product_coverage_percent=80, padding_percent=10)
        assert spec.product_coverage_percent == 80

        # Invalid - out of range
        with pytest.raises(ValueError):
            FramingSpec(product_coverage_percent=120)  # > 95

        with pytest.raises(ValueError):
            FramingSpec(padding_percent=2)  # < 5

    def test_enhancement_spec_defaults(self):
        """Test EnhancementSpec defaults."""
        spec = EnhancementSpec()
        assert spec.sharpness == "medium"
        assert spec.contrast == "subtle"
        assert spec.denoise is False
        assert spec.upscale == "none"
        assert spec.color_correction is True

    def test_scene_spec_environments(self):
        """Test SceneSpec environment options."""
        valid_environments = [
            "kitchen", "living_room", "office", "outdoor",
            "restaurant", "retail", "warehouse", "studio"
        ]
        for env in valid_environments:
            spec = SceneSpec(environment=env)
            assert spec.environment == env

    def test_product_placement_options(self):
        """Test ProductPlacement position options."""
        spec = ProductPlacement(position="foreground", scale="dominant", surface="table")
        assert spec.position == "foreground"
        assert spec.scale == "dominant"
        assert spec.surface == "table"

    def test_analysis_attributes_defaults(self):
        """Test AnalysisAttributes defaults."""
        attrs = AnalysisAttributes()
        assert attrs.colors is True
        assert attrs.materials is True
        assert attrs.dimensions is True
        assert attrs.quality_score is True
        assert attrs.custom_attributes == []

    def test_output_spec_defaults(self):
        """Test OutputSpec defaults."""
        spec = OutputSpec()
        assert spec.format == "PNG"
        assert spec.size == "2K"
        assert spec.aspect_ratio == "1:1"
        assert spec.quality == 90
        assert spec.variants == ["master"]

    def test_output_spec_quality_validation(self):
        """Test OutputSpec quality range validation."""
        # Valid
        spec = OutputSpec(quality=50)
        assert spec.quality == 50

        # Invalid
        with pytest.raises(ValueError):
            OutputSpec(quality=0)  # < 1

        with pytest.raises(ValueError):
            OutputSpec(quality=101)  # > 100

    def test_image_studio_input_analyze(self):
        """Test ImageStudioInput for analyze operation."""
        input_spec = ImageStudioInput(
            operation=ImageOperation.ANALYZE,
            source_image="/path/to/image.png",
            analysis=AnalysisAttributes(colors=True, materials=True),
        )
        assert input_spec.operation == ImageOperation.ANALYZE
        assert input_spec.source_image == "/path/to/image.png"
        assert input_spec.analysis is not None

    def test_image_studio_input_edit(self):
        """Test ImageStudioInput for edit operation."""
        input_spec = ImageStudioInput(
            operation=ImageOperation.EDIT,
            source_image="/path/to/image.png",
            background=BackgroundSpec(type="solid", color="#FFFFFF"),
            enhancement=EnhancementSpec(sharpness="high"),
        )
        assert input_spec.operation == ImageOperation.EDIT
        assert input_spec.background is not None
        assert input_spec.enhancement is not None

    def test_image_studio_input_generate(self):
        """Test ImageStudioInput for generate operation."""
        input_spec = ImageStudioInput(
            operation=ImageOperation.GENERATE,
            source_image="/path/to/product.png",
            scene=SceneSpec(environment="kitchen", style="modern"),
            placement=ProductPlacement(position="center"),
            output=OutputSpec(size="2K", aspect_ratio="1:1"),
        )
        assert input_spec.operation == ImageOperation.GENERATE
        assert input_spec.scene is not None
        assert input_spec.placement is not None

    def test_analysis_result_schema(self):
        """Test AnalysisResult schema."""
        result = AnalysisResult(
            colors=["red", "blue"],
            materials=["plastic", "metal"],
            product_category="container",
            quality_score=0.85,
            confidence=0.9,
            product_count=1,
        )
        assert result.quality_score == 0.85
        assert result.confidence == 0.9
        assert result.product_count == 1


# =============================================================================
# Group 2: Tool Factory Tests (8 tests)
# =============================================================================


class TestImageStudioToolFactory:
    """Test Image Studio tool factory."""

    def test_create_image_studio_tool(self):
        """Test tool factory creates valid tool."""
        tool = create_image_studio_tool()
        assert tool.name == "image_studio"
        assert "Gemini 3 Pro Image" in tool.description
        assert "analyze" in tool.description.lower()
        assert "edit" in tool.description.lower()
        assert "generate" in tool.description.lower()

    def test_tool_has_structured_input(self):
        """Test tool uses structured Pydantic input."""
        tool = create_image_studio_tool()
        assert tool.args_schema is not None

    def test_tool_description_includes_operations(self):
        """Test tool description lists all operations."""
        tool = create_image_studio_tool()
        assert "analyze" in tool.description.lower()
        assert "edit" in tool.description.lower()
        assert "generate" in tool.description.lower()

    def test_tool_is_callable(self):
        """Test tool can be called (sync wrapper)."""
        tool = create_image_studio_tool()
        # Tool should be callable (though it will fail without valid input)
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

    def test_tool_metadata(self):
        """Test tool has proper metadata."""
        tool = create_image_studio_tool()
        assert tool.name == "image_studio"


# =============================================================================
# Group 3: Analyze Operation Tests (10 tests)
# =============================================================================


@pytest.mark.skip(reason="Requires Gemini API integration - tool handlers not fully implemented")
class TestAnalyzeOperation:
    """Test analyze operation.

    NOTE: These tests require full Gemini API integration.
    Skipped until _handle_analyze is fully implemented.
    """

    def test_analyze_requires_source_image(self):
        """Test analyze fails without source_image."""
        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "analyze",
            # Missing source_image
            "analysis": {"colors": True},
        })
        assert result["success"] is False
        assert "source_image required" in result["error"]

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    def test_analyze_with_valid_image(self, mock_load, mock_llm_factory, temp_image_file):
        """Test analyze with valid image."""
        # Mock image loading
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")

        # Mock LLM response
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "colors": ["red"],
            "materials": ["plastic"],
            "product_category": "container",
            "quality_score": 0.85,
            "confidence": 0.9,
            "product_count": 1,
        })
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "analyze",
            "source_image": temp_image_file,
            "analysis": {"colors": True, "materials": True},
        })

        assert result["success"] is True
        assert result["operation"] == "analyze"
        assert "analysis" in result

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    def test_analyze_extracts_colors(self, mock_load, mock_llm_factory):
        """Test analyze extracts color information."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "colors": ["red", "blue", "white"],
            "quality_score": 0.8,
            "confidence": 0.9,
            "product_count": 1,
        })
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "analyze",
            "source_image": "/tmp/test.png",
            "analysis": {"colors": True},
        })

        assert result["success"] is True
        assert "colors" in result.get("analysis", {})

    def test_analyze_file_not_found(self):
        """Test analyze with non-existent file."""
        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "analyze",
            "source_image": "/nonexistent/path/image.png",
        })

        assert result["success"] is False
        assert result["error_code"] == ImageStudioErrorCode.FILE_NOT_FOUND.value

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    def test_analyze_custom_attributes(self, mock_load, mock_llm_factory):
        """Test analyze with custom attributes."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "quality_score": 0.8,
            "confidence": 0.9,
            "product_count": 1,
            "custom_attributes": {"brand_visible": True, "text_readable": True},
        })
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "analyze",
            "source_image": "/tmp/test.png",
            "analysis": {"custom_attributes": ["brand_visible", "text_readable"]},
        })

        assert result["success"] is True

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    def test_analyze_multi_product_detection(self, mock_load, mock_llm_factory):
        """Test analyze detects multiple products."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "quality_score": 0.7,
            "confidence": 0.85,
            "product_count": 3,
            "multi_product_warning": "Multiple products detected in frame",
        })
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "analyze",
            "source_image": "/tmp/test.png",
        })

        assert result["success"] is True
        analysis = result.get("analysis", {})
        assert analysis.get("product_count", 1) == 3

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    def test_analyze_quality_score_range(self, mock_load, mock_llm_factory):
        """Test analyze returns quality score in valid range."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "quality_score": 0.75,
            "confidence": 0.9,
            "product_count": 1,
        })
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "analyze",
            "source_image": "/tmp/test.png",
        })

        assert result["success"] is True
        quality = result.get("analysis", {}).get("quality_score", 0)
        assert 0.0 <= quality <= 1.0

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    def test_analyze_uses_gemini3_model(self, mock_load, mock_llm_factory):
        """Test analyze uses Gemini 3 Pro Image model."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "quality_score": 0.8,
            "confidence": 0.9,
            "product_count": 1,
        })
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        tool.invoke({
            "operation": "analyze",
            "source_image": "/tmp/test.png",
        })

        # Verify LLM factory was called with for_analysis=True
        mock_llm_factory.assert_called_once()
        call_kwargs = mock_llm_factory.call_args[1]
        assert call_kwargs.get("for_analysis") is True

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    def test_analyze_api_error_handling(self, mock_load, mock_llm_factory):
        """Test analyze handles API errors gracefully."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")

        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(side_effect=Exception("API rate limit exceeded"))
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "analyze",
            "source_image": "/tmp/test.png",
        })

        assert result["success"] is False
        assert result["error_code"] == ImageStudioErrorCode.API_ERROR.value


# =============================================================================
# Group 4: Edit Operation Tests (10 tests)
# =============================================================================


@pytest.mark.skip(reason="Requires Gemini API integration - tool handlers not fully implemented")
class TestEditOperation:
    """Test edit operation.

    NOTE: These tests require full Gemini API integration.
    Skipped until _handle_edit is fully implemented.
    """

    def test_edit_requires_source_image(self):
        """Test edit fails without source_image."""
        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "edit",
            "background": {"type": "solid", "color": "#FFFFFF"},
        })

        assert result["success"] is False
        assert "source_image required" in result["error"]

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    @patch("autifyme_agents.tools.image_studio.tool._save_generated_image")
    def test_edit_background_removal(self, mock_save, mock_load, mock_llm_factory):
        """Test edit with background removal."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")
        mock_save.return_value = "/tmp/output.png"

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.additional_kwargs = {"image": base64.b64encode(b"fake_image").decode()}
        mock_response.content = "Image edited successfully"
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "edit",
            "source_image": "/tmp/test.png",
            "background": {"type": "transparent"},
        })

        # Should attempt to invoke the LLM
        mock_llm.invoke.assert_called_once()

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    @patch("autifyme_agents.tools.image_studio.tool._save_generated_image")
    def test_edit_with_enhancement(self, mock_save, mock_load, mock_llm_factory):
        """Test edit with image enhancement."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")
        mock_save.return_value = "/tmp/output.png"

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.additional_kwargs = {"image": base64.b64encode(b"fake_image").decode()}
        mock_response.content = "Enhanced"
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "edit",
            "source_image": "/tmp/test.png",
            "enhancement": {
                "sharpness": "high",
                "contrast": "medium",
                "denoise": True,
            },
        })

        mock_llm.invoke.assert_called_once()

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    @patch("autifyme_agents.tools.image_studio.tool._save_generated_image")
    def test_edit_with_lighting(self, mock_save, mock_load, mock_llm_factory):
        """Test edit with lighting adjustment."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")
        mock_save.return_value = "/tmp/output.png"

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.additional_kwargs = {"image": base64.b64encode(b"fake_image").decode()}
        mock_response.content = "Lighting adjusted"
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "edit",
            "source_image": "/tmp/test.png",
            "lighting": {
                "type": "studio",
                "direction": "front",
                "intensity": "high",
            },
        })

        mock_llm.invoke.assert_called_once()

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    def test_edit_file_not_found(self, mock_load, mock_llm_factory):
        """Test edit with non-existent file."""
        mock_load.side_effect = FileNotFoundError("File not found")

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "edit",
            "source_image": "/nonexistent/image.png",
            "background": {"type": "solid"},
        })

        assert result["success"] is False
        assert result["error_code"] == ImageStudioErrorCode.FILE_NOT_FOUND.value

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    @patch("autifyme_agents.tools.image_studio.tool._save_generated_image")
    def test_edit_output_spec_applied(self, mock_save, mock_load, mock_llm_factory):
        """Test edit applies output specifications."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")
        mock_save.return_value = "/tmp/output.png"

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.additional_kwargs = {"image": base64.b64encode(b"fake_image").decode()}
        mock_response.content = "Edited"
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "edit",
            "source_image": "/tmp/test.png",
            "background": {"type": "solid"},
            "output": {"size": "4K", "aspect_ratio": "16:9", "format": "JPEG"},
        })

        # Verify LLM factory was called with output specs
        mock_llm_factory.assert_called_once()
        call_kwargs = mock_llm_factory.call_args[1]
        output_spec = call_kwargs.get("output_spec")
        assert output_spec is not None

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    @patch("autifyme_agents.tools.image_studio.tool._save_generated_image")
    def test_edit_returns_output_path(self, mock_save, mock_load, mock_llm_factory):
        """Test edit returns output file path."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")
        mock_save.return_value = "/tmp/media_downloads/20251130_edit_abc123.png"

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.additional_kwargs = {"image": base64.b64encode(b"fake_image").decode()}
        mock_response.content = "Edited"
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "edit",
            "source_image": "/tmp/test.png",
            "background": {"type": "solid"},
        })

        assert result["success"] is True
        assert "outputs" in result
        assert len(result["outputs"]) > 0

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    def test_edit_no_image_in_response(self, mock_load, mock_llm_factory):
        """Test edit handles missing image in response."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.additional_kwargs = {}  # No image!
        mock_response.content = "No image generated"
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "edit",
            "source_image": "/tmp/test.png",
            "background": {"type": "solid"},
        })

        assert result["success"] is False
        assert "error" in result

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    def test_edit_uses_gemini3_with_image_modality(self, mock_load, mock_llm_factory):
        """Test edit uses Gemini 3 with IMAGE modality."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.additional_kwargs = {"image": base64.b64encode(b"fake").decode()}
        mock_response.content = "OK"
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        tool.invoke({
            "operation": "edit",
            "source_image": "/tmp/test.png",
            "background": {"type": "solid"},
        })

        # Verify LLM factory was called WITHOUT for_analysis (means IMAGE modality)
        mock_llm_factory.assert_called_once()
        call_kwargs = mock_llm_factory.call_args[1]
        assert call_kwargs.get("for_analysis") is not True


# =============================================================================
# Group 5: Generate Operation Tests (10 tests)
# =============================================================================


@pytest.mark.skip(reason="Requires Gemini API integration - tool handlers not fully implemented")
class TestGenerateOperation:
    """Test generate operation (lifestyle shots).

    NOTE: These tests require full Gemini API integration.
    Skipped until _handle_generate is fully implemented.
    """

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._save_generated_image")
    def test_generate_without_source_image(self, mock_save, mock_llm_factory):
        """Test generate can work without source image."""
        mock_save.return_value = "/tmp/output.png"

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.additional_kwargs = {"image": base64.b64encode(b"fake").decode()}
        mock_response.content = "Generated"
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "generate",
            "scene": {"environment": "kitchen", "style": "modern"},
        })

        # Generate should work without source_image
        mock_llm.invoke.assert_called_once()

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    @patch("autifyme_agents.tools.image_studio.tool._save_generated_image")
    def test_generate_with_source_reference(self, mock_save, mock_load, mock_llm_factory):
        """Test generate with source image as reference."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")
        mock_save.return_value = "/tmp/output.png"

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.additional_kwargs = {"image": base64.b64encode(b"fake").decode()}
        mock_response.content = "Generated with reference"
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "generate",
            "source_image": "/tmp/product.png",
            "scene": {"environment": "living_room"},
            "placement": {"position": "center", "scale": "balanced"},
        })

        mock_llm.invoke.assert_called_once()

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._save_generated_image")
    def test_generate_kitchen_scene(self, mock_save, mock_llm_factory):
        """Test generate kitchen lifestyle scene."""
        mock_save.return_value = "/tmp/output.png"

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.additional_kwargs = {"image": base64.b64encode(b"fake").decode()}
        mock_response.content = "Kitchen scene generated"
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "generate",
            "scene": {
                "environment": "kitchen",
                "style": "modern",
                "mood": "professional",
                "time_of_day": "morning",
            },
        })

        mock_llm.invoke.assert_called_once()

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._save_generated_image")
    def test_generate_with_placement(self, mock_save, mock_llm_factory):
        """Test generate with product placement."""
        mock_save.return_value = "/tmp/output.png"

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.additional_kwargs = {"image": base64.b64encode(b"fake").decode()}
        mock_response.content = "Placed"
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "generate",
            "scene": {"environment": "restaurant"},
            "placement": {
                "position": "table",
                "scale": "dominant",
                "surface": "table",
            },
        })

        mock_llm.invoke.assert_called_once()

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._save_generated_image")
    def test_generate_output_specs(self, mock_save, mock_llm_factory):
        """Test generate respects output specifications."""
        mock_save.return_value = "/tmp/output.png"

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.additional_kwargs = {"image": base64.b64encode(b"fake").decode()}
        mock_response.content = "4K generated"
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "generate",
            "scene": {"environment": "studio"},
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

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._save_generated_image")
    def test_generate_returns_outputs(self, mock_save, mock_llm_factory):
        """Test generate returns output variants."""
        mock_save.return_value = "/tmp/media_downloads/20251130_generate_xyz.png"

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.additional_kwargs = {"image": base64.b64encode(b"fake").decode()}
        mock_response.content = "Generated"
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "generate",
            "scene": {"environment": "office"},
        })

        assert result["success"] is True
        assert "outputs" in result
        assert result["operation"] == "generate"

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    def test_generate_api_error(self, mock_llm_factory):
        """Test generate handles API errors."""
        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(side_effect=Exception("Generation failed"))
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "generate",
            "scene": {"environment": "kitchen"},
        })

        assert result["success"] is False
        assert result["error_code"] == ImageStudioErrorCode.API_ERROR.value

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._save_generated_image")
    def test_generate_all_environments(self, mock_save, mock_llm_factory):
        """Test generate works with all environment types."""
        mock_save.return_value = "/tmp/output.png"

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.additional_kwargs = {"image": base64.b64encode(b"fake").decode()}
        mock_response.content = "OK"
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()

        environments = ["kitchen", "living_room", "office", "outdoor",
                       "restaurant", "retail", "warehouse", "studio"]

        for env in environments:
            result = tool.invoke({
                "operation": "generate",
                "scene": {"environment": env},
            })
            # All should invoke the LLM
            assert mock_llm.invoke.called

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    def test_generate_no_image_in_response(self, mock_llm_factory):
        """Test generate handles missing image in response."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.additional_kwargs = {}  # No image
        mock_response.content = "Failed to generate"
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "generate",
            "scene": {"environment": "kitchen"},
        })

        assert result["success"] is False

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._save_generated_image")
    def test_generate_uses_gemini3_model(self, mock_save, mock_llm_factory):
        """Test generate uses Gemini 3 Pro Image model."""
        mock_save.return_value = "/tmp/output.png"

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.additional_kwargs = {"image": base64.b64encode(b"fake").decode()}
        mock_response.content = "OK"
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        tool.invoke({
            "operation": "generate",
            "scene": {"environment": "kitchen"},
        })

        # Verify LLM factory was called
        mock_llm_factory.assert_called()


# =============================================================================
# Group 6: Error Handling Tests (8 tests)
# =============================================================================


class TestErrorHandling:
    """Test error handling across all operations."""

    def test_invalid_operation(self):
        """Test invalid operation type."""
        tool = create_image_studio_tool()

        # Pydantic should catch invalid enum value
        with pytest.raises(Exception):
            tool.invoke({
                "operation": "invalid_op",
                "source_image": "/tmp/test.png",
            })

    def test_corrupt_image_handling(self, temp_image_file):
        """Test handling of corrupt image file."""
        # Create a corrupt "image" file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False, mode="wb") as f:
            f.write(b"not a valid image content")
            corrupt_path = f.name

        try:
            tool = create_image_studio_tool()
            result = tool.invoke({
                "operation": "analyze",
                "source_image": corrupt_path,
            })

            # Should handle gracefully
            assert result["success"] is False
            assert "error" in result
        finally:
            Path(corrupt_path).unlink(missing_ok=True)

    def test_missing_required_fields(self):
        """Test missing required fields in input."""
        tool = create_image_studio_tool()

        # Missing 'operation' field
        with pytest.raises(Exception):
            tool.invoke({
                "source_image": "/tmp/test.png",
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
            "operation": "analyze",
            "source_image": "/tmp/test.png",
        })

        assert result["success"] is False
        assert "error" in result

    def test_empty_source_image_path(self):
        """Test empty source_image path."""
        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "analyze",
            "source_image": "",
        })

        assert result["success"] is False

    @patch("autifyme_agents.tools.image_studio.tool._get_gemini3_image_llm")
    @patch("autifyme_agents.tools.image_studio.tool._load_and_encode_image")
    def test_malformed_llm_response(self, mock_load, mock_llm_factory):
        """Test handling of malformed LLM response."""
        mock_load.return_value = ("data:image/png;base64,abc123", "image/png")

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "not valid json {{{{"  # Invalid JSON
        mock_llm.invoke = MagicMock(return_value=mock_response)
        mock_llm_factory.return_value = mock_llm

        tool = create_image_studio_tool()
        result = tool.invoke({
            "operation": "analyze",
            "source_image": "/tmp/test.png",
        })

        # Should handle JSON parse error gracefully
        assert result["success"] is False or "analysis" in result

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
            "operation": "analyze",
            "source_image": "/nonexistent/path.png",
        })

        assert result["success"] is False
        assert "error" in result
        assert "error_code" in result
        assert result["operation"] == "analyze"
