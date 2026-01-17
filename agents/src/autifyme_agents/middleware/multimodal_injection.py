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
# - Storage paths: inbox/..., pending/..., products/... (AutifyME storage)
# - Storage URLs: https://....supabase.co/storage/...
# - Plain text: /tmp/file.jpg or C:\path\file.png
# - JSON strings: "path": "/tmp/file.jpg" or "path": "C:\\path\\file.png"
# - With escaped backslashes in JSON: C:\\\\Users\\\\...
IMAGE_PATH_PATTERN = re.compile(
    r"(?:"
    # Storage URLs (Supabase, S3, etc.)
    r'(https?://[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp))'
    r"|"
    # Storage paths: inbox/..., pending/..., products/... (with optional leading slash)
    r'(/?(?:inbox|pending|products)/[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp))'
    r"|"
    # Unix paths: /tmp/..., /var/...
    r'(/(?:tmp|var|home|Users)[/][^\s<>"\'\\]+\.(?:jpg|jpeg|png|gif|webp))'
    r"|"
    # Windows paths with normal slashes: C:/Users/...
    r'([A-Za-z]:/[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp))'
    r"|"
    # Windows paths with single backslash: C:\Users\...
    r'([A-Za-z]:\\[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp))'
    r"|"
    # Windows paths with escaped backslashes in JSON: C:\\Users\\...
    r'([A-Za-z]:\\\\[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp))'
    r")",
    re.IGNORECASE,
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
            extra={"source": image_path, "type": source_type, "size": original_size},
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
    content_blocks.append(
        {
            "type": "text",
            "text": original_content,
        }
    )

    # Add each image
    for path in image_paths:
        result = _load_and_encode_image(path)
        if result is not None:
            data_uri, metadata = result
            content_blocks.append(
                {
                    "type": "image_url",
                    "image_url": {"url": data_uri},
                }
            )
            # Add metadata as text for context
            content_blocks.append(
                {
                    "type": "text",
                    "text": f"[Above image: {metadata['source']} ({metadata['original_size']})]",
                }
            )

    return content_blocks


class MultimodalInjectionMiddleware(AgentMiddleware):
    """Middleware that injects images into specialist messages.

    When a specialist receives a message containing image paths,
    this middleware loads the images and transforms the message
    to multimodal format so the LLM can see them directly.

    This enables specialists to make visual decisions without
    relying on separate tool calls to view images.

    PATH REFERENCE RESOLUTION:
    LLMs can hallucinate/corrupt long paths when typing them out for tool calls.
    To prevent this, specialists can use path references instead of full paths:

    - @0, @1, @2... - Reference by index (order paths appear in delegation)
    - @product, @source, @background... - Reference by label (matched from image metadata)

    The middleware resolves these references to actual paths before tool execution.

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

        # Specialist can then use references in image_studio:
        # {"images": [{"path": "@0", "label": "product"}]}
        # Instead of:
        # {"images": [{"path": "inbox/whatsapp_.../20251209_085136_25217028717961295.jpg", "label": "product"}]}
        ```
    """

    def __init__(self, *, enabled: bool = True) -> None:
        """Initialize the middleware.

        Args:
            enabled: Whether image injection is active. Defaults to True.
        """
        super().__init__()
        self.enabled = enabled
        # Store injected paths for reference resolution in tool calls
        # List of (path, detected_label) tuples in order of appearance
        self._injected_paths: list[tuple[str, str | None]] = []

    def _process_messages(self, messages: list[Any]) -> list[Any]:
        """Process messages to inject images.

        Looks for HumanMessage and ToolMessage with text content containing
        image paths, and transforms them to multimodal content.

        This allows the specialist to:
        1. SEE input images from PM delegation (HumanMessage)
        2. SEE output images from tool results (ToolMessage)

        Also stores extracted paths in self._injected_paths for reference
        resolution when specialist calls image_studio with @0, @1, etc.

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
                        extra={"paths": image_paths},
                    )
                    # Store paths for reference resolution (with None label - to be inferred)
                    for path in image_paths:
                        if not any(p == path for p, _ in self._injected_paths):
                            self._injected_paths.append((path, None))
                    logger.info(
                        "Stored %d path(s) for reference resolution: %s",
                        len(self._injected_paths),
                        [p for p, _ in self._injected_paths],
                    )
                    multimodal_content = _transform_to_multimodal(msg.content, image_paths)
                    # Create new HumanMessage with multimodal content
                    processed.append(
                        HumanMessage(content=cast(list[str | dict[Any, Any]], multimodal_content))
                    )
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
                        extra={"paths": image_paths},
                    )
                    multimodal_content = _transform_to_multimodal(msg.content, image_paths)
                    # Create new ToolMessage with multimodal content
                    # Preserve tool_call_id which is required for ToolMessage
                    processed.append(
                        ToolMessage(
                            content=cast(list[str | dict[Any, Any]], multimodal_content),
                            tool_call_id=msg.tool_call_id,
                            name=msg.name,
                        )
                    )
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
            str(result.content)[:200] if result.content else "None",
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
                    extra={"paths": image_paths},
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
                image_paths[:3] if image_paths else "none",
            )
            if image_paths:
                logger.info(
                    "Extracting %d image(s) from string tool output: %s",
                    len(image_paths),
                    tool_name or "unknown",
                    extra={"paths": image_paths},
                )
                multimodal_content = _transform_to_multimodal(content, image_paths)
                return ToolMessage(
                    content=cast(list[str | dict[Any, Any]], multimodal_content),
                    tool_call_id=result.tool_call_id,
                    name=result.name,
                )
        elif not isinstance(content, list):  # Defensive: handles unexpected content types
            logger.debug(  # type: ignore[unreachable]
                "[MULTIMODAL] Content is neither dict nor str nor list: %s", type(content).__name__
            )

        logger.debug("[MULTIMODAL] No image paths found, returning original result")
        return result

    # =========================================================================
    # Path Reference Resolution
    # =========================================================================

    def _resolve_path_reference(self, path: str) -> str:
        """Resolve a path reference (@0, @1, @product) to actual path.

        Args:
            path: Either a real path or a reference like @0, @1, @product

        Returns:
            Resolved actual path, or original path if not a reference
        """
        if not path.startswith("@"):
            return path

        ref = path[1:]  # Remove @

        # Try numeric index first (@0, @1, etc.)
        if ref.isdigit():
            idx = int(ref)
            if 0 <= idx < len(self._injected_paths):
                resolved = self._injected_paths[idx][0]
                logger.info("Resolved path reference @%d -> %s", idx, resolved)
                return resolved
            else:
                logger.warning(
                    "Path reference @%d out of range (have %d paths)",
                    idx,
                    len(self._injected_paths),
                )
                return path

        # Try label match (@product, @source, @background, etc.)
        # Currently labels are None, but could be populated from image metadata
        for stored_path, label in self._injected_paths:
            if label and label.lower() == ref.lower():
                logger.info("Resolved path reference @%s -> %s", ref, stored_path)
                return stored_path

        # No match - return original (will likely fail, but with clear error)
        logger.warning(
            "Could not resolve path reference @%s (available: %s)",
            ref,
            [f"@{i}" for i in range(len(self._injected_paths))],
        )
        return path

    def _resolve_image_studio_args(self, args: dict[str, Any]) -> dict[str, Any]:
        """Resolve path references in image_studio tool arguments.

        Args:
            args: Tool arguments dict

        Returns:
            Modified args with resolved paths
        """
        if "images" not in args:
            return args

        images = args.get("images", [])
        if not isinstance(images, list):
            return args

        resolved_images = []
        for img in images:
            if isinstance(img, dict) and "path" in img:
                original_path = img["path"]
                resolved_path = self._resolve_path_reference(original_path)
                if resolved_path != original_path:
                    img = {**img, "path": resolved_path}
            resolved_images.append(img)

        return {**args, "images": resolved_images}

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        """Intercept tool call and inject images into the result.

        For image_studio: Resolves path references BEFORE execution.
        For all tools: Injects images into result AFTER execution.

        Args:
            request: The tool call request
            handler: The next handler in the chain

        Returns:
            Tool result with images injected
        """
        # Get tool name for logging
        tool_name = request.tool.name if request.tool else None

        logger.debug("[MULTIMODAL] wrap_tool_call INVOKED for tool: %s", tool_name or "unknown")

        # BEFORE execution: Resolve path references for image_studio
        if tool_name == "image_studio" and self._injected_paths:
            original_args = request.tool_call.get("args", {})
            if isinstance(original_args, dict):
                resolved_args = self._resolve_image_studio_args(original_args)
                if resolved_args != original_args:
                    logger.info("[MULTIMODAL] Resolved path references in image_studio args")
                    # Create new tool_call with resolved args
                    request.tool_call = {**request.tool_call, "args": resolved_args}

        # Execute the tool
        result = handler(request)

        logger.debug(
            "[MULTIMODAL] Tool result type: %s, content type: %s",
            type(result).__name__,
            type(result.content).__name__ if hasattr(result, "content") else "N/A",
        )

        # AFTER execution: Process image_studio output for multimodal injection
        if tool_name == "image_studio":
            processed = self._process_tool_result(result, tool_name)
            logger.debug(
                "[MULTIMODAL] After processing - content type: %s, is_list: %s",
                type(processed.content).__name__ if hasattr(processed, "content") else "N/A",
                isinstance(processed.content, list) if hasattr(processed, "content") else False,
            )
            return processed

        return result

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        """(async) Intercept tool call and inject images into the result.

        For image_studio: Resolves path references BEFORE execution.
        For all tools: Injects images into result AFTER execution.

        Args:
            request: The tool call request
            handler: The next handler in the chain

        Returns:
            Tool result with images injected
        """
        # Get tool name for logging
        tool_name = request.tool.name if request.tool else None

        logger.debug("[MULTIMODAL] awrap_tool_call INVOKED for tool: %s", tool_name or "unknown")

        # BEFORE execution: Resolve path references for image_studio
        if tool_name == "image_studio" and self._injected_paths:
            original_args = request.tool_call.get("args", {})
            if isinstance(original_args, dict):
                resolved_args = self._resolve_image_studio_args(original_args)
                if resolved_args != original_args:
                    logger.info("[MULTIMODAL] Resolved path references in image_studio args")
                    # Create new tool_call with resolved args
                    request.tool_call = {**request.tool_call, "args": resolved_args}

        # Execute the tool
        result = await handler(request)

        logger.debug(
            "[MULTIMODAL] Tool result type: %s, content type: %s",
            type(result).__name__,
            type(result.content).__name__ if hasattr(result, "content") else "N/A",
        )

        # AFTER execution: Process image_studio output for multimodal injection
        if tool_name == "image_studio":
            processed = self._process_tool_result(result, tool_name)
            logger.debug(
                "[MULTIMODAL] After processing - content type: %s, is_list: %s",
                type(processed.content).__name__ if hasattr(processed, "content") else "N/A",
                isinstance(processed.content, list) if hasattr(processed, "content") else False,
            )
            return processed

        return result
