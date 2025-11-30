"""View Image Tool - Allows agents to see images before processing.

Enables multimodal reasoning: agent sees the image and decides what operations to perform.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

from langchain_core.tools import StructuredTool
from PIL import Image
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

MAX_DIMENSION = 1024  # Resize for efficient token usage


class ViewImageInput(BaseModel):
    """Input schema for view_image tool."""

    image_path: str = Field(description="Path to image file to view")
    question: str | None = Field(
        default=None,
        description="Optional question about the image (e.g., 'How many products?', 'What colors?')"
    )


def _view_image_impl(image_path: str, question: str | None = None) -> dict[str, Any]:
    """View an image and return it for multimodal reasoning.

    Returns the image as a data URI that the agent can see directly.
    """
    path = Path(image_path)

    if not path.exists():
        return {
            "success": False,
            "error": f"Image not found: {image_path}",
            "guidance": "Check the path and try again. Use download tool first if needed."
        }

    try:
        with Image.open(path) as img:
            # Get original info
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
            import io
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
            data_uri = f"data:image/jpeg;base64,{encoded}"

        return {
            "success": True,
            "image": data_uri,
            "metadata": {
                "path": str(path),
                "original_size": f"{original_size[0]}x{original_size[1]}",
                "format": original_format,
            },
            "instruction": (
                f"You can now see this image. {question or 'Analyze it and decide what operations are needed.'}"
            )
        }

    except Exception as e:
        logger.exception("Failed to load image: %s", image_path)
        return {
            "success": False,
            "error": f"Failed to load image: {e}",
            "guidance": "Image may be corrupt or unsupported format."
        }


def create_view_image_tool() -> StructuredTool:
    """Create the view_image tool.

    Allows agents to SEE images before deciding what operations to perform.
    Use this FIRST before calling image_studio to make informed decisions.
    """
    return StructuredTool.from_function(
        func=_view_image_impl,
        name="view_image",
        description="""View an image to understand its contents before processing.

USE THIS FIRST before calling image_studio. You will SEE the actual image
and can make informed decisions about:
- How many products are in the image
- What type of products they are
- Whether background removal is needed
- What enhancements would help
- Whether extraction is needed for group photos

Returns the image for you to view directly in your context.

Example workflow:
1. view_image("/tmp/uploaded.jpg") -> You see the image
2. Based on what you see: "3 jars in a row, cluttered background"
3. Call image_studio with specific, informed parameters""",
        args_schema=ViewImageInput,
        return_direct=False,
    )
