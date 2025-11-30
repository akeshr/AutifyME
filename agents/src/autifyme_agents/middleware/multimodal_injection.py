"""Multimodal Injection Middleware - Transforms text messages to include images.

Intercepts messages containing image paths and injects actual image data
as multimodal content. Uses TWO interception points for reliability:

1. **wrap_tool_call** - Intercepts tool output IMMEDIATELY after execution
   - Parses structured tool response (dict) to extract image paths
   - Injects images into ToolMessage before any serialization
   - More reliable than regex parsing of JSON strings

2. **wrap_model_call** - Intercepts before LLM sees messages (fallback + input)
   - Handles input images from PM delegation (HumanMessage)
   - Falls back for any ToolMessage paths missed by wrap_tool_call

Scenarios covered:
- PM sends image path to specialist -> wrap_model_call injects into HumanMessage
- Tool returns image path -> wrap_tool_call injects into ToolMessage
- Tool output as string -> wrap_model_call regex fallback

Architecture:
- wrap_tool_call: Intercepts structured tool results, extracts paths from dict
- wrap_model_call: Scans all messages, transforms to multimodal content
- Specialist LLM receives [text + image] content blocks
"""

from __future__ import annotations

import base64
import io
import json
import logging
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
    ToolCallRequest,
)
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.types import Command
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
        path = next((m for m in match if m), None) if isinstance(match, tuple) else match

        if not path:
            continue

        # Normalize escaped backslashes from JSON (\\\\  -> \\ and \\ -> \)
        normalized = path.replace("\\\\", "\\").strip()

        if normalized not in seen:
            seen.add(normalized)
            unique_paths.append(normalized)

    return unique_paths


def _extract_paths_from_dict(data: dict[str, Any]) -> list[str]:
    """Extract image paths from structured tool output (dict).

    Recursively searches for 'path' keys in the tool output structure.
    Handles image_studio output format: {"outputs": [{"path": "..."}]}

    Args:
        data: Structured tool output dictionary

    Returns:
        List of image paths found
    """
    paths: list[str] = []

    def _recurse(obj: Any) -> None:
        if isinstance(obj, dict):
            # Check for 'path' key that looks like an image path
            if "path" in obj:
                path_val = obj["path"]
                if isinstance(path_val, str) and any(
                    path_val.lower().endswith(ext)
                    for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp")
                ):
                    paths.append(path_val)
            # Recurse into all values
            for value in obj.values():
                _recurse(value)
        elif isinstance(obj, list):
            for item in obj:
                _recurse(item)

    _recurse(data)
    return paths


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

    # =========================================================================
    # Tool-level interception (more reliable for tool outputs)
    # =========================================================================

    def _process_tool_result(
        self,
        result: ToolMessage | Command,
        tool_name: str | None,
    ) -> ToolMessage | Command:
        """Process tool result to inject images.

        Called immediately after tool execution, before any serialization.
        This is more reliable than parsing JSON strings in wrap_model_call.

        Args:
            result: Tool execution result
            tool_name: Name of the tool that was called

        Returns:
            Modified result with images injected if applicable
        """
        if not self.enabled:
            return result

        # Only process ToolMessage (not Command)
        if not isinstance(result, ToolMessage):
            return result

        image_paths: list[str] = []

        # Try structured extraction first (more reliable)
        if isinstance(result.content, dict):
            image_paths = _extract_paths_from_dict(result.content)
            if image_paths:
                logger.info(
                    "Extracting %d image(s) from structured tool output: %s",
                    len(image_paths),
                    tool_name or "unknown",
                    extra={"paths": image_paths}
                )
                # Convert dict to JSON string for multimodal transformation
                text_content = json.dumps(result.content, indent=2)
                multimodal_content = _transform_to_multimodal(text_content, image_paths)
                return ToolMessage(
                    content=multimodal_content,
                    tool_call_id=result.tool_call_id,
                    name=result.name,
                )

        # Fallback to string extraction
        elif isinstance(result.content, str):
            image_paths = _extract_image_paths(result.content)
            if image_paths:
                logger.info(
                    "Extracting %d image(s) from string tool output: %s",
                    len(image_paths),
                    tool_name or "unknown",
                    extra={"paths": image_paths}
                )
                multimodal_content = _transform_to_multimodal(
                    result.content, image_paths
                )
                return ToolMessage(
                    content=multimodal_content,
                    tool_call_id=result.tool_call_id,
                    name=result.name,
                )

        return result

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        """Intercept tool call and inject images into the result.

        This runs IMMEDIATELY after tool execution, allowing us to work
        with structured data before any serialization happens.

        Args:
            request: The tool call request
            handler: The next handler in the chain

        Returns:
            Tool result with images injected
        """
        # Execute the tool
        result = handler(request)

        # Get tool name for logging
        tool_name = request.tool.name if request.tool else None

        # Only process image-producing tools
        if tool_name in ("image_studio", "view_image"):
            return self._process_tool_result(result, tool_name)

        return result

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        """(async) Intercept tool call and inject images into the result.

        Args:
            request: The tool call request
            handler: The next handler in the chain

        Returns:
            Tool result with images injected
        """
        # Execute the tool
        result = await handler(request)

        # Get tool name for logging
        tool_name = request.tool.name if request.tool else None

        # Only process image-producing tools
        if tool_name in ("image_studio", "view_image"):
            return self._process_tool_result(result, tool_name)

        return result
