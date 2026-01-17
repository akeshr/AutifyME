"""View Image Tool - Universal image viewing for any agent.

Returns images as multimodal content, enabling LLMs to SEE images directly.
Accepts user-friendly paths (no thread_id) and expands internally.

Path Format:
- LLM provides: "inbox/photo.jpg" or "pending/output.png"
- Internally expanded to: "inbox/{thread_id}/photo.jpg"
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

MAX_DIMENSION = 1024


class ViewImageInput(BaseModel):
    """Input schema for view_image tool."""

    image_path: str = Field(
        description="Image path from download_media or image_studio output. Example: 'inbox/photo.jpg'"
    )


def _load_image_as_data_uri(image_path: str) -> tuple[str, dict[str, Any]]:
    """Load image and convert to data URI.

    Handles user paths, storage paths, URLs, and local files.
    """
    from autifyme_agents.core.storage_utils import build_storage_url, is_storage_path

    # Convert storage path to URL (handles user path expansion internally)
    if is_storage_path(image_path):
        image_path = build_storage_url(image_path)

    # Fetch image
    img: Image.Image
    if image_path.startswith(("http://", "https://")):
        import httpx

        response = httpx.get(image_path, timeout=30)
        response.raise_for_status()
        img = Image.open(io.BytesIO(response.content))
        source_type = "url"
    else:
        img = Image.open(Path(image_path))
        source_type = "local"

    with img:
        original_size = img.size
        original_format = img.format or "JPEG"

        # Resize for efficiency
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
    """View an image - returns multimodal content for agent to see."""
    from autifyme_agents.core.storage_utils import is_storage_path

    # Validate local paths
    is_url = image_path.startswith(("http://", "https://"))
    is_storage = is_storage_path(image_path)
    if not is_url and not is_storage and not Path(image_path).exists():
        return [{"type": "text", "text": f"Error: Image not found at {image_path}"}]

    try:
        data_uri, metadata = _load_image_as_data_uri(image_path)

        return [
            {
                "type": "text",
                "text": f"Image ({metadata['type']}): {metadata['original_size']}, {metadata['format']}",
            },
            {"type": "image_url", "image_url": {"url": data_uri}},
        ]

    except Exception as e:
        logger.exception("Failed to load image: %s", image_path)
        return [{"type": "text", "text": f"Error loading image: {e}"}]


def create_view_image_tool() -> StructuredTool:
    """Create the view_image tool."""
    return StructuredTool.from_function(
        func=_view_image_impl,
        name="view_image",
        description=(
            "PURPOSE: View images directly - this tool gives you EYES. "
            "Returns multimodal content so you SEE images visually.\n\n"
            "USE WHEN:\n"
            "- Analyzing user images (materials, features, colors)\n"
            "- Before write_data (visual verification)\n"
            "- After image_studio (quality check)\n"
            "- Product categorization and material identification\n\n"
            "DON'T USE:\n"
            "- For metadata only\n"
            "- When you already know contents from prior viewing\n\n"
            "INPUT:\n"
            "- storage_path from download_media: 'inbox/photo.jpg'\n"
            "- storage_path from image_studio: 'pending/output.png'\n"
            "- URLs also accepted\n\n"
            "RETURNS: Multimodal content - text metadata + image you can SEE"
        ),
        args_schema=ViewImageInput,
        return_direct=False,
    )
