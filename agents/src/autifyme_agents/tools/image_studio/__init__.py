"""Image Studio Tool - Gemini 3 Pro Image integration.

Unified tool for product image operations:
- edit: Background removal, enhancement, extraction, cleanup
- generate: Lifestyle shots, scene placement

Architecture: Single atomic tool with structured Pydantic schema.
"""

from autifyme_agents.tools.image_studio.schemas import (
    BackgroundSpec,
    EnhancementSpec,
    ExtractionSpec,
    FocusRegionSpec,
    FramingSpec,
    ImageMetadata,
    ImageOperation,
    ImageStudioErrorCode,
    ImageStudioInput,
    ImageStudioOutput,
    LightingSpec,
    OutputSpec,
    OutputVariant,
    ProductPlacement,
    SceneSpec,
)
from autifyme_agents.tools.image_studio.tool import create_image_studio_tool

__all__ = [
    # Tool factory
    "create_image_studio_tool",
    # Input schemas
    "ImageOperation",
    "BackgroundSpec",
    "LightingSpec",
    "FramingSpec",
    "EnhancementSpec",
    "SceneSpec",
    "ProductPlacement",
    "ExtractionSpec",
    "FocusRegionSpec",
    "OutputSpec",
    "ImageStudioInput",
    # Output schemas
    "ImageMetadata",
    "OutputVariant",
    "ImageStudioOutput",
    # Error codes
    "ImageStudioErrorCode",
]
