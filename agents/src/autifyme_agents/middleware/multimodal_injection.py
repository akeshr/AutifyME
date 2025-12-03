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
from typing import Any, cast

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
# - Storage URLs: https://....supabase.co/storage/...
IMAGE_PATH_PATTERN = re.compile(
    r'(?:'
    # Storage URLs (Supabase, S3, etc.)
    r'(https?://[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp))'
    r'|'
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

MAX_IMAGE_DIMENSION = 1024  # Larger for specialist (higher detail for image_studio)


def _load_and_encode_image(image_path: str) -> tuple[str, dict[str, Any]] | None:
    """Load image from storage_path/URL/local path and encode as base64 data URI.

    Args:
        image_path: storage_path, URL, or local file path

    Returns:
        Tuple of (data_uri, metadata) or None if loading fails
    """
    try:
        # Import here to avoid circular dependency
        from autifyme_agents.core.storage_utils import build_storage_url, is_storage_path

        # Convert storage_path to URL if needed
        if is_storage_path(image_path):
            try:
                image_path = build_storage_url(image_path)
            except ValueError:
                logger.warning("Cannot build URL for storage_path: %s", image_path)
                return None

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
            if not path.exists():
                logger.warning("Image not found: %s", image_path)
                return None
            img = Image.open(path)
            source_type = "local"

        with img:
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
            "source": image_path,
            "type": source_type,
            "original_size": f"{original_size[0]}x{original_size[1]}",
            "format": original_format,
        }

        logger.info(
            "Image loaded for multimodal injection",
            extra={"source": image_path, "type": source_type, "size": original_size}
        )

        return data_uri, metadata

    except Exception:
        logger.exception("Failed to load image for injection: %s", image_path)
        return None


def _extract_image_paths(text: str) -> list[str]:
    """Extract image file paths and URLs from text.

    Handles paths in various formats:
    - Storage URLs (https://...supabase.co/...)
    - Plain text paths
    - JSON-embedded paths with escaped backslashes
    - Windows and Unix paths

    Args:
        text: Text that may contain image paths or URLs

    Returns:
        List of unique image paths/URLs found
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

        # URLs don't need normalization, only local paths
        if path.startswith(("http://", "https://")):
            normalized = path.strip()
        else:
            # Normalize escaped backslashes from JSON (\\\\  -> \\ and \\ -> \)
            normalized = path.replace("\\\\", "\\").strip()

        if normalized not in seen:
            seen.add(normalized)
            unique_paths.append(normalized)

    return unique_paths


def _extract_paths_from_dict(data: dict[str, Any]) -> list[str]:
    """Extract image paths from structured tool output (dict).

    Recursively searches for 'storage_path' key in the tool output.
    Handles:
    - image_studio output: {"outputs": [{"storage_path": "pending/..."}]}
    - download_media output: {"storage_path": "inbox/..."}

    Args:
        data: Structured tool output dictionary

    Returns:
        List of storage_paths found
    """
    paths: list[str] = []

    def _recurse(obj: Any) -> None:
        if isinstance(obj, dict):
            # Check for 'storage_path' key (primary - Supabase bucket path)
            if "storage_path" in obj:
                path_val = obj["storage_path"]
                if isinstance(path_val, str) and path_val:
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
                "text": f"[Above image: {metadata['source']} ({metadata['original_size']})]",
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
                    processed.append(HumanMessage(
                        content=cast(list[str | dict[Any, Any]], multimodal_content)
                    ))
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
                        content=cast(list[str | dict[Any, Any]], multimodal_content),
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
        result: ToolMessage | Command[Any],
        tool_name: str | None,
    ) -> ToolMessage | Command[Any]:
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
            logger.debug("[MULTIMODAL] _process_tool_result: DISABLED, skipping")
            return result

        # Only process ToolMessage (not Command)
        if not isinstance(result, ToolMessage):
            logger.debug("[MULTIMODAL] _process_tool_result: Not a ToolMessage, skipping")
            return result

        logger.debug(
            "[MULTIMODAL] _process_tool_result: content type=%s, content preview=%s",
            type(result.content).__name__,
            str(result.content)[:200] if result.content else "None"
        )

        # Skip if already multimodal (list with image_url blocks)
        if isinstance(result.content, list):
            has_image = any(
                isinstance(block, dict) and block.get("type") == "image_url"
                for block in result.content
            )
            if has_image:
                logger.debug("[MULTIMODAL] Content already multimodal, skipping")
                return result

        image_paths: list[str] = []

        # Try structured extraction first (more reliable)
        # Note: ToolMessage.content is typed as str | list but may be dict at runtime
        content = result.content
        if isinstance(content, dict):  # type: ignore[unreachable]
            image_paths = _extract_paths_from_dict(content)  # type: ignore[unreachable]
            if image_paths:
                logger.info(
                    "Extracting %d image(s) from structured tool output: %s",
                    len(image_paths),
                    tool_name or "unknown",
                    extra={"paths": image_paths}
                )
                # Convert dict to JSON string for multimodal transformation
                text_content = json.dumps(content, indent=2)
                multimodal_content = _transform_to_multimodal(text_content, image_paths)
                return ToolMessage(
                    content=cast(list[str | dict[Any, Any]], multimodal_content),
                    tool_call_id=result.tool_call_id,
                    name=result.name,
                )

        # Fallback to string extraction
        if isinstance(content, str):
            image_paths = _extract_image_paths(content)
            logger.debug(
                "[MULTIMODAL] String extraction found %d path(s): %s",
                len(image_paths),
                image_paths[:3] if image_paths else "none"
            )
            if image_paths:
                logger.info(
                    "Extracting %d image(s) from string tool output: %s",
                    len(image_paths),
                    tool_name or "unknown",
                    extra={"paths": image_paths}
                )
                multimodal_content = _transform_to_multimodal(content, image_paths)
                return ToolMessage(
                    content=cast(list[str | dict[Any, Any]], multimodal_content),
                    tool_call_id=result.tool_call_id,
                    name=result.name,
                )
        elif not isinstance(content, list):  # Defensive: handles unexpected content types
            logger.debug(  # type: ignore[unreachable]
                "[MULTIMODAL] Content is neither dict nor str nor list: %s",
                type(content).__name__
            )

        logger.debug("[MULTIMODAL] No image paths found, returning original result")
        return result

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        """Intercept tool call and inject images into the result.

        This runs IMMEDIATELY after tool execution, allowing us to work
        with structured data before any serialization happens.

        Args:
            request: The tool call request
            handler: The next handler in the chain

        Returns:
            Tool result with images injected
        """
        # Get tool name for logging
        tool_name = request.tool.name if request.tool else None

        logger.debug(
            "[MULTIMODAL] wrap_tool_call INVOKED for tool: %s",
            tool_name or "unknown"
        )

        # Execute the tool
        result = handler(request)

        logger.debug(
            "[MULTIMODAL] Tool result type: %s, content type: %s",
            type(result).__name__,
            type(result.content).__name__ if hasattr(result, "content") else "N/A"
        )

        # Only process image_studio tool (view_image handles its own multimodal output)
        if tool_name == "image_studio":
            processed = self._process_tool_result(result, tool_name)
            logger.debug(
                "[MULTIMODAL] After processing - content type: %s, is_list: %s",
                type(processed.content).__name__ if hasattr(processed, "content") else "N/A",
                isinstance(processed.content, list) if hasattr(processed, "content") else False
            )
            return processed

        return result

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        """(async) Intercept tool call and inject images into the result.

        Args:
            request: The tool call request
            handler: The next handler in the chain

        Returns:
            Tool result with images injected
        """
        # Get tool name for logging
        tool_name = request.tool.name if request.tool else None

        logger.debug(
            "[MULTIMODAL] awrap_tool_call INVOKED for tool: %s",
            tool_name or "unknown"
        )

        # Execute the tool
        result = await handler(request)

        logger.debug(
            "[MULTIMODAL] Tool result type: %s, content type: %s",
            type(result).__name__,
            type(result.content).__name__ if hasattr(result, "content") else "N/A"
        )

        # Only process image_studio tool (view_image handles its own multimodal output)
        if tool_name == "image_studio":
            processed = self._process_tool_result(result, tool_name)
            logger.debug(
                "[MULTIMODAL] After processing - content type: %s, is_list: %s",
                type(processed.content).__name__ if hasattr(processed, "content") else "N/A",
                isinstance(processed.content, list) if hasattr(processed, "content") else False
            )
            return processed

        return result
