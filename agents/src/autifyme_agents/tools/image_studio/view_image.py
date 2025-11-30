"""View Image Tool - Allows agents to see images before processing.

Returns image as multimodal content so the agent's LLM can see it directly.
"""

from __future__ import annotations

import base64
import io
import logging
from pathlib import Path
from typing import Any

from langchain_core.tools import StructuredTool
from PIL import Image
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

MAX_DIMENSION = 512  # Smaller size for efficient token usage


class ViewImageInput(BaseModel):
    """Input schema for view_image tool."""

    image_path: str = Field(description="Path to image file to view")


def _load_image_as_data_uri(image_path: str) -> tuple[str, dict[str, Any]]:
    """Load image and convert to data URI.

    Returns:
        Tuple of (data_uri, metadata)
    """
    path = Path(image_path)

    with Image.open(path) as img:
        original_size = img.size
        original_format = img.format or "JPEG"

        # Resize for efficient context usage
        width, height = img.size
        if max(width, height) > MAX_DIMENSION:
            if width > height:
                new_width = MAX_DIMENSION
                new_height = int(height * (MAX_DIMENSION / width))
            else:
                new_height = MAX_DIMENSION
                new_width = int(width * (MAX_DIMENSION / height))
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Convert to RGB if needed
        if img.mode in ("RGBA", "LA", "P"):
            rgb_img = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA":
                rgb_img.paste(img, mask=img.split()[-1])
            else:
                rgb_img.paste(img)
            img = rgb_img

        # Encode to base64
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=80)
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
        data_uri = f"data:image/jpeg;base64,{encoded}"

    metadata = {
        "path": str(path),
        "original_size": f"{original_size[0]}x{original_size[1]}",
        "format": original_format,
    }

    return data_uri, metadata


def _view_image_impl(image_path: str) -> list[dict[str, Any]]:
    """View an image - returns multimodal content for agent to see.

    Returns content blocks that include the actual image for the agent's LLM.
    """
    path = Path(image_path)

    if not path.exists():
        return [{"type": "text", "text": f"Error: Image not found at {image_path}"}]

    try:
        data_uri, metadata = _load_image_as_data_uri(image_path)

        # Return multimodal content blocks
        # The agent's LLM will see both the text and the image
        return [
            {
                "type": "text",
                "text": f"Image loaded from {metadata['path']} ({metadata['original_size']}). I can now see this image:"
            },
            {
                "type": "image_url",
                "image_url": {"url": data_uri}
            },
            {
                "type": "text",
                "text": "Based on what I see in this image, I will decide what processing is needed."
            }
        ]

    except Exception as e:
        logger.exception("Failed to load image: %s", image_path)
        return [{"type": "text", "text": f"Error loading image: {e}"}]


def create_view_image_tool() -> StructuredTool:
    """Create the view_image tool.

    Returns multimodal content so the agent can SEE the image directly.
    """
    return StructuredTool.from_function(
        func=_view_image_impl,
        name="view_image",
        description="""View an image file. Returns the actual image so you can SEE it.

Use this to look at an image before deciding what operations to perform.
After calling this, you will see the image and can make informed decisions about:
- How many products are in the image
- Product types, colors, sizes
- Background quality
- What processing is needed

Example: view_image("/tmp/product.jpg") -> You see the actual image""",
        args_schema=ViewImageInput,
        return_direct=False,
    )
