"""Multimodal Injection Middleware - Transforms text messages to include images.

Intercepts messages containing image paths and injects actual image data
as multimodal content. Works for both:

1. **Input images** (HumanMessage from PM delegation)
   - PM sends: "Process /tmp/photo.jpg"
   - Specialist SEES the actual image

2. **Output images** (ToolMessage from tool results)
   - image_studio returns: {"output_images": ["/tmp/result.png"]}
   - Specialist SEES the generated/edited image

This allows the specialist's LLM to SEE images directly (~258-1000 tokens)
instead of receiving just text paths (which would be useless).

Architecture:
- Intercepts ModelRequest.messages before each model call
- Extracts image paths from HumanMessage and ToolMessage content
- Loads and encodes images as base64 data URIs
- Transforms message content to multimodal format
- Specialist LLM receives [text + image] content blocks
"""

from __future__ import annotations

import base64
import io
import logging
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
)
from langchain_core.messages import HumanMessage, ToolMessage
from PIL import Image

logger = logging.getLogger(__name__)

# Match common image paths in various contexts:
# - Plain text: /tmp/file.jpg or C:\path\file.png
# - JSON strings: "path": "/tmp/file.jpg" or "path": "C:\\path\\file.png"
# - With escaped backslashes in JSON: C:\\\\Users\\\\...
IMAGE_PATH_PATTERN = re.compile(
    r'(?:'
    # Unix paths: /tmp/..., /var/...
    r'(/(?:tmp|var|home|Users)[/][^\s<>"\'\\]+\.(?:jpg|jpeg|png|gif|webp))'
    r'|'
    # Windows paths with normal slashes: C:/Users/...
    r'([A-Za-z]:/[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp))'
    r'|'
    # Windows paths with single backslash: C:\Users\...
    r'([A-Za-z]:\\[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp))'
    r'|'
    # Windows paths with escaped backslashes in JSON: C:\\Users\\...
    r'([A-Za-z]:\\\\[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp))'
    r')',
    re.IGNORECASE
)

MAX_IMAGE_DIMENSION = 1024  # Larger for specialist (more detail than view_image)


def _load_and_encode_image(image_path: str) -> tuple[str, dict[str, Any]] | None:
    """Load image from path and encode as base64 data URI.

    Args:
        image_path: Path to image file

    Returns:
        Tuple of (data_uri, metadata) or None if loading fails
    """
    try:
        path = Path(image_path)
        if not path.exists():
            logger.warning("Image not found: %s", image_path)
            return None

        with Image.open(path) as img:
            original_size = img.size
            original_format = img.format or "JPEG"

            # Resize for efficient token usage while preserving detail
            width, height = img.size
            if max(width, height) > MAX_IMAGE_DIMENSION:
                if width > height:
                    new_width = MAX_IMAGE_DIMENSION
                    new_height = int(height * (MAX_IMAGE_DIMENSION / width))
                else:
                    new_height = MAX_IMAGE_DIMENSION
                    new_width = int(width * (MAX_IMAGE_DIMENSION / height))
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Convert to RGB if needed (handle RGBA, palette modes)
            if img.mode in ("RGBA", "LA", "P"):
                rgb_img = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "RGBA":
                    rgb_img.paste(img, mask=img.split()[-1])
                else:
                    rgb_img.paste(img)
                img = rgb_img

            # Encode to base64
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
            data_uri = f"data:image/jpeg;base64,{encoded}"

        metadata = {
            "path": str(path),
            "original_size": f"{original_size[0]}x{original_size[1]}",
            "format": original_format,
        }

        logger.info(
            "Image loaded for multimodal injection",
            extra={"path": image_path, "size": original_size}
        )

        return data_uri, metadata

    except Exception:
        logger.exception("Failed to load image for injection: %s", image_path)
        return None


def _extract_image_paths(text: str) -> list[str]:
    """Extract image file paths from text.

    Handles paths in various formats:
    - Plain text paths
    - JSON-embedded paths with escaped backslashes
    - Windows and Unix paths

    Args:
        text: Text that may contain image paths

    Returns:
        List of unique image paths found (normalized for filesystem access)
    """
    matches = IMAGE_PATH_PATTERN.findall(text)
    # findall returns tuples when pattern has multiple groups
    # Extract the non-empty match from each tuple
    seen: set[str] = set()
    unique_paths: list[str] = []
    for match in matches:
        # match is a tuple of capture groups, one will be non-empty
        if isinstance(match, tuple):
            path = next((m for m in match if m), None)
        else:
            path = match

        if not path:
            continue

        # Normalize escaped backslashes from JSON (\\\\  -> \\ and \\ -> \)
        normalized = path.replace("\\\\", "\\").strip()

        if normalized not in seen:
            seen.add(normalized)
            unique_paths.append(normalized)

    return unique_paths


def _transform_to_multimodal(
    original_content: str,
    image_paths: list[str],
) -> list[dict[str, Any]]:
    """Transform text content into multimodal content blocks with images.

    Args:
        original_content: Original text content
        image_paths: List of image paths to inject

    Returns:
        List of content blocks (text + images)
    """
    content_blocks: list[dict[str, Any]] = []

    # Add original text (minus redundant path mentions if desired)
    content_blocks.append({
        "type": "text",
        "text": original_content,
    })

    # Add each image
    for path in image_paths:
        result = _load_and_encode_image(path)
        if result is not None:
            data_uri, metadata = result
            content_blocks.append({
                "type": "image_url",
                "image_url": {"url": data_uri},
            })
            # Add metadata as text for context
            content_blocks.append({
                "type": "text",
                "text": f"[Above image: {metadata['path']} ({metadata['original_size']})]",
            })

    return content_blocks


class MultimodalInjectionMiddleware(AgentMiddleware):
    """Middleware that injects images into specialist messages.

    When a specialist receives a message containing image paths,
    this middleware loads the images and transforms the message
    to multimodal format so the LLM can see them directly.

    This enables specialists to make visual decisions without
    relying on separate tool calls to view images.

    Example:
        ```python
        from autifyme_agents.middleware.multimodal_injection import (
            MultimodalInjectionMiddleware,
        )

        # Add to specialist middleware
        spec = {
            "name": "creative_specialist",
            "middleware": [MultimodalInjectionMiddleware()],
            ...
        }
        ```
    """

    def __init__(self, *, enabled: bool = True) -> None:
        """Initialize the middleware.

        Args:
            enabled: Whether image injection is active. Defaults to True.
        """
        super().__init__()
        self.enabled = enabled

    def _process_messages(self, messages: list[Any]) -> list[Any]:
        """Process messages to inject images.

        Looks for HumanMessage and ToolMessage with text content containing
        image paths, and transforms them to multimodal content.

        This allows the specialist to:
        1. SEE input images from PM delegation (HumanMessage)
        2. SEE output images from tool results (ToolMessage)

        Args:
            messages: List of messages

        Returns:
            Modified messages with images injected
        """
        if not self.enabled:
            return messages

        processed: list[Any] = []
        for msg in messages:
            if isinstance(msg, HumanMessage) and isinstance(msg.content, str):
                image_paths = _extract_image_paths(msg.content)
                if image_paths:
                    logger.info(
                        "Injecting %d image(s) into HumanMessage",
                        len(image_paths),
                        extra={"paths": image_paths}
                    )
                    multimodal_content = _transform_to_multimodal(
                        msg.content, image_paths
                    )
                    # Create new HumanMessage with multimodal content
                    processed.append(HumanMessage(content=multimodal_content))
                else:
                    processed.append(msg)
            elif isinstance(msg, ToolMessage) and isinstance(msg.content, str):
                # Also inject images from tool responses (e.g., image_studio output)
                image_paths = _extract_image_paths(msg.content)
                if image_paths:
                    logger.info(
                        "Injecting %d image(s) into ToolMessage from %s",
                        len(image_paths),
                        msg.name or "unknown tool",
                        extra={"paths": image_paths}
                    )
                    multimodal_content = _transform_to_multimodal(
                        msg.content, image_paths
                    )
                    # Create new ToolMessage with multimodal content
                    # Preserve tool_call_id which is required for ToolMessage
                    processed.append(ToolMessage(
                        content=multimodal_content,
                        tool_call_id=msg.tool_call_id,
                        name=msg.name,
                    ))
                else:
                    processed.append(msg)
            else:
                processed.append(msg)

        return processed

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Intercept model call and inject images into messages.

        Args:
            request: The model request
            handler: The next handler in the chain

        Returns:
            Model response
        """
        # Process messages to inject images
        request.messages = self._process_messages(request.messages)
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """(async) Intercept model call and inject images into messages.

        Args:
            request: The model request
            handler: The next handler in the chain

        Returns:
            Model response
        """
        # Process messages to inject images
        request.messages = self._process_messages(request.messages)
        return await handler(request)
