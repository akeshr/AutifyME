"""Image Studio Tool - Gemini 3 Pro Image integration.

Intelligence-First architecture:
- Labeled images: Each image has a label referenced in instructions
- Structured specs: Guide completeness, accept any string value
- Model reasons about what to do from specs and labels
"""

from autifyme_agents.tools.image_studio.schemas import (
    BackgroundSpec,
    CompositionSpec,
    CustomSpec,
    EnhancementSpec,
    ExtractionSpec,
    FocusSpec,
    ImageInput,
    ImageMetadata,
    ImageStudioErrorCode,
    ImageStudioInput,
    ImageStudioOutput,
    LightingSpec,
    MaterialTreatmentSpec,
    OutputSpec,
    OutputVariant,
    ProductPlacementSpec,
    SceneSpec,
)
from autifyme_agents.tools.image_studio.tool import create_image_studio_tool

__all__ = [
    # Tool factory
    "create_image_studio_tool",
    # Input schemas - Images
    "ImageInput",
    "ImageStudioInput",
    # Input schemas - Structured specs
    "BackgroundSpec",
    "LightingSpec",
    "CompositionSpec",
    "EnhancementSpec",
    "SceneSpec",
    "ProductPlacementSpec",
    "ExtractionSpec",
    "FocusSpec",
    "MaterialTreatmentSpec",
    "CustomSpec",
    # Output configuration
    "OutputSpec",
    # Output schemas
    "ImageMetadata",
    "OutputVariant",
    "ImageStudioOutput",
    # Error codes
    "ImageStudioErrorCode",
]
