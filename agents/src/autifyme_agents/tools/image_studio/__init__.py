"""Image Studio Tool - Gemini 3 Pro Image (Nano Banana Pro) integration.

Unified tool for product image operations:
- analyze: Extract visual attributes
- edit: Background removal, enhancement, cleanup
- generate: Lifestyle shots, scene placement

Architecture: Single atomic tool with structured Pydantic schema.
One powerful LLM = One powerful tool.
"""

from autifyme_agents.tools.image_studio.schemas import (
    AnalysisAttributes,
    AnalysisResult,
    BackgroundSpec,
    EnhancementSpec,
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
    "AnalysisAttributes",
    "OutputSpec",
    "ImageStudioInput",
    # Output schemas
    "ImageMetadata",
    "AnalysisResult",
    "OutputVariant",
    "ImageStudioOutput",
    # Error codes
    "ImageStudioErrorCode",
]
