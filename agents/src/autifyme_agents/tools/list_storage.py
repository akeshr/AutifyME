"""List Storage Tool - Discover files in storage folders.

Browse storage folders (inbox, pending, products) to see what files exist.
Complements read_data (database queries) and view_image (see specific images).

Use Cases:
- See what user uploaded in current session (inbox/)
- Check AI-generated images awaiting approval (pending/)
- Browse approved assets (products/)
- Find files by extension or prefix
"""

import logging
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from autifyme_agents.core.execution_context import get_thread_id
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.tool_error_handler import (
    build_agent_error_response,
    build_success_response,
)

logger = logging.getLogger(__name__)


class ListStorageInput(BaseModel):
    """Input schema for list_storage tool."""

    model_config = {"extra": "forbid"}

    folder: str = Field(
        ...,
        description=(
            "Storage folder to list. Common folders:\n"
            "- 'inbox' - User uploads (images sent via WhatsApp)\n"
            "- 'pending' - AI-generated images awaiting approval\n"
            "- 'products' - Approved permanent assets\n"
            "Can also be a custom path like 'approved/families'"
        ),
    )
    limit: int = Field(
        default=20, description="Maximum files to return (default: 20, max: 100)", gt=0, le=100
    )
    offset: int = Field(default=0, description="Skip N files for pagination (default: 0)", ge=0)
    extension_filter: list[str] | None = Field(
        default=None,
        description=(
            "Only include files with these extensions. "
            "Examples: ['jpg', 'png'], ['pdf'], ['.jpeg', '.webp']"
        ),
    )
    prefix_filter: str | None = Field(
        default=None,
        description=(
            "Only include files starting with this prefix. "
            "Example: 'hero_' to find 'hero_shot.png', 'hero_v2.png'"
        ),
    )


def create_list_storage_tool(
    storage: StorageInterface,
) -> StructuredTool:
    """Create list_storage tool for browsing storage folders.

    Enables agents to discover what files exist in storage without
    querying the database. Useful for:
    - Seeing what images user uploaded in session
    - Checking pending images before approval
    - Finding files by pattern

    Args:
        storage: Storage interface for file operations

    Returns:
        StructuredTool configured for storage listing

    Note:
        Thread ID is obtained from execution context (invisible to LLM).
        For session-scoped folders (inbox/pending), context must be set.
    """
    _storage_client = storage

    async def _list_storage_impl(
        folder: str,
        limit: int = 20,
        offset: int = 0,
        extension_filter: list[str] | None = None,
        prefix_filter: str | None = None,
    ) -> dict[str, Any]:
        """
        List files in a storage folder.

        USE WHEN:
        - Discovering what files exist in storage
        - Checking user uploads in current session
        - Finding AI-generated images awaiting approval
        - Browsing approved assets by pattern

        NOT FOR:
        - Database queries (use read_data for assets table)
        - Viewing image content (use view_image)
        - File operations (use image_studio, write_data)

        Args:
            folder: Storage folder ("inbox", "pending", "products", or custom path)
            limit: Max files to return (default 20, max 100)
            offset: Skip N files for pagination
            extension_filter: Only files with these extensions (e.g., ["jpg", "png"])
            prefix_filter: Only files starting with this prefix

        Returns:
            Structured response with file list and pagination info

        Examples:
            # See what user uploaded in this session
            list_storage(folder="inbox")
            # Returns: Files in inbox/{thread_id}/

            # Check pending images (AI-generated awaiting approval)
            list_storage(folder="pending", extension_filter=["png"])
            # Returns: PNG files in pending/{thread_id}/

            # Browse approved products with pagination
            list_storage(folder="products", limit=50, offset=100)
            # Returns: Files 101-150 in products/

            # Find hero shots by prefix
            list_storage(folder="pending", prefix_filter="hero_")
            # Returns: Files starting with "hero_"
        """
        try:
            # Get thread_id from execution context (invisible to LLM)
            current_thread_id = get_thread_id()

            # Validate thread_id for session-scoped folders
            if folder in ("inbox", "pending") and not current_thread_id:
                logger.warning(
                    f"No thread_id available for {folder}/ listing", extra={"folder": folder}
                )
                return build_agent_error_response(
                    exception=ValueError(f"Session context required for {folder}/"),
                    context={"folder": folder},
                    fallback_type="CONTEXT_ERROR",
                    fallback_action=(
                        f"Cannot list {folder}/ without session context. "
                        f"This folder is thread-scoped. "
                        f"Use 'products' folder for non-session files."
                    ),
                )

            logger.info(
                f"Listing storage folder: {folder}",
                extra={
                    "folder": folder,
                    "limit": limit,
                    "offset": offset,
                    "extension_filter": extension_filter,
                    "prefix_filter": prefix_filter,
                },
            )

            result = await _storage_client.list_storage_files(
                folder=folder,
                thread_id=current_thread_id,
                limit=limit,
                offset=offset,
                extension_filter=extension_filter,
                prefix_filter=prefix_filter,
            )

            if not result.get("success"):
                return result

            # Enrich response with user-friendly paths
            files = result.get("files", [])
            for file_info in files:
                # Add user path (without thread_id) for convenience
                storage_path = file_info.get("storage_path", "")
                if "/" in storage_path:
                    parts = storage_path.split("/")
                    if len(parts) >= 3 and parts[0] in ("inbox", "pending"):
                        # inbox/{thread_id}/file.jpg -> inbox/file.jpg
                        file_info["user_path"] = f"{parts[0]}/{parts[-1]}"
                    else:
                        file_info["user_path"] = storage_path

            logger.info(
                f"Listed {len(files)} files from {folder}",
                extra={
                    "folder": folder,
                    "count": len(files),
                    "total": result.get("total", 0),
                    "has_more": result.get("has_more", False),
                },
            )

            return build_success_response(
                {
                    "folder": result.get("folder"),
                    "files": files,
                    "count": result.get("count", len(files)),
                    "total": result.get("total", 0),
                    "has_more": result.get("has_more", False),
                    "pagination": {
                        "limit": limit,
                        "offset": offset,
                        "next_offset": offset + limit if result.get("has_more") else None,
                    },
                }
            )

        except ValueError as e:
            logger.warning(f"Validation error for list_storage: {e}", extra={"folder": folder})
            return build_agent_error_response(
                exception=e,
                context={"folder": folder},
                fallback_type="VALIDATION_ERROR",
                fallback_action=str(e),
            )

        except Exception as e:
            logger.error(
                f"Failed to list storage folder: {folder}", exc_info=True, extra={"folder": folder}
            )
            return build_agent_error_response(
                exception=e,
                context={"folder": folder},
                fallback_type="STORAGE_ERROR",
                fallback_action=(
                    f"Failed to list {folder}/. "
                    f"Check folder name and try again. "
                    f"Common folders: inbox, pending, products."
                ),
            )

    return StructuredTool.from_function(
        func=_list_storage_impl,
        name="list_storage",
        description=(
            "PURPOSE: Discover files in storage folders - see what exists before viewing or using.\n\n"
            "USE WHEN:\n"
            "- Checking what user uploaded in session (inbox/)\n"
            "- Finding AI-generated images awaiting approval (pending/)\n"
            "- Browsing approved assets (products/)\n"
            "- Finding files by extension or prefix pattern\n\n"
            "DON'T USE:\n"
            "- For database queries (use read_data for assets table metadata)\n"
            "- For viewing image content (use view_image with path from list_storage)\n"
            "- For file operations (use image_studio, write_data)\n\n"
            "COMMON FOLDERS:\n"
            "- inbox: User uploads (session-scoped, auto-expanded to inbox/{thread_id}/)\n"
            "- pending: AI-generated awaiting approval (session-scoped)\n"
            "- products: Approved permanent assets (not session-scoped)\n\n"
            "WORKFLOW:\n"
            "1. list_storage(folder='inbox') -> See available files\n"
            "2. view_image(image_path='inbox/photo.jpg') -> View specific file\n"
            "3. read_data(table='assets') -> Query database metadata\n\n"
            "FILTERS:\n"
            "- extension_filter: ['jpg', 'png'] for images only\n"
            "- prefix_filter: 'hero_' for files starting with prefix\n"
            "- limit/offset: Pagination for large folders\n\n"
            "RETURNS: Always structured dict with success flag.\n"
            "- success=True: {folder, files[], count, total, has_more, pagination}\n"
            "  * files[]: [{name, storage_path, user_path, public_url, size_bytes?, content_type?}]\n"
            "- success=False: {error, error_type, Agent Action: ...}"
        ),
        args_schema=ListStorageInput,
        coroutine=_list_storage_impl,
    )
