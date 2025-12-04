"""Image Studio Tool - Gemini 3 Pro Image integration.

Simplified architecture: Creative Specialist writes natural language briefs.
- edit: Modify existing images (background, extraction, enhancement)
- generate: Create new scenes from product images

Architecture: Single atomic tool with creative_direction as primary input.
"""

from autifyme_agents.tools.image_studio.schemas import (
    ImageMetadata,
    ImageOperation,
    ImageStudioErrorCode,
    ImageStudioInput,
    ImageStudioOutput,
    OutputSpec,
    OutputVariant,
)
from autifyme_agents.tools.image_studio.tool import create_image_studio_tool

__all__ = [
    # Tool factory
    "create_image_studio_tool",
    # Input schemas
    "ImageOperation",
    "OutputSpec",
    "ImageStudioInput",
    # Output schemas
    "ImageMetadata",
    "OutputVariant",
    "ImageStudioOutput",
    # Error codes
    "ImageStudioErrorCode",
]
