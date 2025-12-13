"""View Image Tool - Universal image viewing for any agent.

Global utility that returns images as multimodal content, enabling
any agent's LLM to SEE images directly without middleware.

Architecture:
- Accepts storage_path (inbox/, pending/) or local paths
- Converts storage_path to URL internally for fetching
- Returns multimodal content blocks (text + image_url)
- No middleware required - tool owns its output format
- Any agent with this tool can view and analyze images
- Resizes images for efficient token usage (512px max dimension)

Use Cases:
- View images from inbox/ (download_media output)
- Verify output from image_studio (pending/)
- Quality checks before write_data
- Inspect any image by storage_path or local path
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
            "Image source - storage_path from download_media/image_studio. "
            "Example: 'inbox/thread_id/photo.jpg' or 'pending/thread_id/edit.png'"
        )
    )


def _load_image_as_data_uri(image_path: str) -> tuple[str, dict[str, Any]]:
    """Load image from storage_path/URL/local path and convert to data URI.

    Args:
        image_path: storage_path, URL, or local file path

    Returns:
        Tuple of (data_uri, metadata)
    """
    # Import here to avoid circular dependency
    from autifyme_agents.core.storage_utils import build_storage_url, is_storage_path

    # Convert storage_path to URL if needed
    if is_storage_path(image_path):
        image_path = build_storage_url(image_path)

    # Handle URLs
    img: Image.Image
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
        image_path: storage_path (inbox/..., pending/...) or local file path

    Returns content blocks that include the actual image for the agent's LLM.
    """
    # Import here to avoid circular dependency
    from autifyme_agents.core.storage_utils import is_storage_path

    # Check existence for local paths only (storage paths and URLs validated during fetch)
    is_url = image_path.startswith(("http://", "https://"))
    is_storage = is_storage_path(image_path)
    if not is_url and not is_storage and not Path(image_path).exists():
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
    """
    return StructuredTool.from_function(
        func=_view_image_impl,
        name="view_image",
        description=(
            "PURPOSE: View images directly in your context - this tool gives you EYES. Returns multimodal content so you SEE images like viewing a photo. The image appears visually in your LLM context for analysis.\n\n"
            "USE WHEN:\n"
            "- Analyzing user-provided images: What product? What materials? What features?\n"
            "- Before write_data: Visual verification ensures accurate catalog entries (materials, colors, dimensions)\n"
            "- After image_studio: Quality check before using generated images\n"
            "- Duplicate detection: Visual comparison when names/SKUs ambiguous\n"
            "- Material identification: See textures, finishes, transparency for accurate descriptions\n"
            "- Product categorization: Visual features determine product_type, family\n"
            "- Comparing variants: Side-by-side analysis to identify differences\n\n"
            "DON'T USE:\n"
            "- For metadata only (file size, dimensions)\n"
            "- When you already know what's in the image from prior viewing\n"
            "- Batch processing (call once per image)\n\n"
            "CRITICAL:\n"
            "- Accepts storage_path (inbox/, pending/) or local paths or URLs\n"
            "- Auto-converts storage_path to URL internally for fetching\n"
            "- Resizes to 512px max dimension for efficient tokens (faithful representation)\n"
            "- download_media outputs to 'inbox/', image_studio outputs to 'pending/'\n"
            "- Use proactively - when user mentions image, view it immediately\n"
            "- Visual trumps assumptions - when uncertain, look at the image\n\n"
            "EXAMPLES:\n"
            "# Analyzing user upload for cataloging\n"
            "view_image(image_path='inbox/thread_789/product_photo.jpg')\n"
            "Returns: You SEE the product - identify 500ml PET jar, honeycomb texture, blue lid, clear body\n\n"
            "# Verifying image_studio output quality\n"
            "view_image(image_path='pending/thread_789/background_removed.png')\n"
            "Returns: You SEE edited image - confirm background clean, product centered, quality acceptable\n\n"
            "ALSO CONSIDER:\n"
            "- image_studio: After viewing, need processing (extract, background, enhance)? Use image_studio\n"
            "- write_data: After visual verification, ready to catalog? Use write_data\n\n"
            "RETURNS: Multimodal content - text metadata (source type, size, format) + image block (you SEE it visually)"
        ),
        args_schema=ViewImageInput,
        return_direct=False,
    )
