"""View Image Tool - Universal image viewing for any agent.

Global utility that returns images as multimodal content, enabling
any agent's LLM to SEE images directly without middleware.

Architecture:
- Accepts both local paths AND storage_url (Supabase public URLs)
- Returns multimodal content blocks (text + image_url)
- No middleware required - tool owns its output format
- Any agent with this tool can view and analyze images
- Resizes images for efficient token usage (512px max dimension)

Use Cases:
- View images from inbox/ (download_media storage_url)
- Verify output from image_studio (pending/ storage_url)
- Quality checks before write_data
- Inspect any image by URL or local path
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

MAX_DIMENSION = 512  # Optimized for efficient token usage


class ViewImageInput(BaseModel):
    """Input schema for view_image tool."""

    image_path: str = Field(
        description=(
            "Image source - accepts storage_url (from image_studio/download_media) "
            "or local path. Example: 'https://...supabase.co/.../image.png' or '/tmp/preview.jpg'"
        )
    )


def _load_image_as_data_uri(image_path: str) -> tuple[str, dict[str, Any]]:
    """Load image from URL or local path and convert to data URI.

    Args:
        image_path: storage_url (https://...) or local file path

    Returns:
        Tuple of (data_uri, metadata)
    """
    # Handle URLs (storage_url from image_studio/download_media)
    img: Image.Image  # Type hint: resize/convert returns Image.Image, not ImageFile
    if image_path.startswith(("http://", "https://")):
        import httpx

        response = httpx.get(image_path, timeout=30)
        response.raise_for_status()
        img = Image.open(io.BytesIO(response.content))
        source_type = "url"
    else:
        path = Path(image_path)
        img = Image.open(path)
        source_type = "local"

    with img:
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
        "source": image_path,
        "type": source_type,
        "original_size": f"{original_size[0]}x{original_size[1]}",
        "format": original_format,
    }

    return data_uri, metadata


def _view_image_impl(image_path: str) -> list[dict[str, Any]]:
    """View an image - returns multimodal content for agent to see.

    Args:
        image_path: storage_url (https://...) or local file path

    Returns content blocks that include the actual image for the agent's LLM.
    """
    # Check existence for local paths (URLs validated during fetch)
    is_url = image_path.startswith(("http://", "https://"))
    if not is_url and not Path(image_path).exists():
        return [{"type": "text", "text": f"Error: Image not found at {image_path}"}]

    try:
        data_uri, metadata = _load_image_as_data_uri(image_path)

        # Return multimodal content blocks
        # The agent's LLM will see both the text and the image
        return [
            {
                "type": "text",
                "text": f"Image ({metadata['type']}): {metadata['original_size']}, {metadata['format']}"
            },
            {
                "type": "image_url",
                "image_url": {"url": data_uri}
            },
        ]

    except Exception as e:
        logger.exception("Failed to load image: %s", image_path)
        return [{"type": "text", "text": f"Error loading image: {e}"}]


def create_view_image_tool() -> StructuredTool:
    """Create the view_image tool.

    Returns multimodal content so any agent can SEE images directly.
    No middleware required - the tool handles image injection itself.
    """
    return StructuredTool.from_function(
        func=_view_image_impl,
        name="view_image",
        description=(
            "View an image from storage_url or local path. Returns the actual image so you can SEE it.\n\n"
            "Use this to:\n"
            "- Diagnose source images from inbox/ (download_media storage_url)\n"
            "- Verify outputs from image_studio (pending/ storage_url)\n"
            "- Quality check before write_data\n"
            "- Analyze content, colors, composition, product count\n\n"
            "After calling, you see the image directly in your context.\n\n"
            "Example: view_image('https://...supabase.co/.../image.png')"
        ),
        args_schema=ViewImageInput,
        return_direct=False,
    )
