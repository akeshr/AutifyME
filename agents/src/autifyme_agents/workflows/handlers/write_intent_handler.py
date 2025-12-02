"""WriteIntent workflow handler - generic HITL approval for database operations."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from autifyme_agents.schemas.write_intent import WriteIntent
from autifyme_agents.workflows.channels.protocol import MessagingChannel
from autifyme_agents.workflows.message_utils import extract_text_content

logger = logging.getLogger(__name__)


class WriteIntentHandler:
    """Generic handler for WriteIntent HITL approval flow.

    Handles:
    - Extracting AI response summaries from PM messages
    - Processing WriteIntent interrupts for user approval
    - Sending asset previews and approval summaries via channel

    Works with any workflow type (cataloging, marketing, etc.) that uses
    WriteIntent for database operations.
    """

    def __init__(self, channel: MessagingChannel, supabase_url: str | None = None):
        """Initialize handler.

        Args:
            channel: Messaging channel for sending user notifications
            supabase_url: Optional Supabase project URL for building asset URLs.
                          Falls back to SUPABASE_URL environment variable.
        """
        self.channel = channel
        self._supabase_url = supabase_url or os.getenv("SUPABASE_URL")

    def extract_summary(self, messages: list[Any]) -> str | None:
        """Extract AI summary for conversational responses.

        Args:
            messages: PM output messages

        Returns:
            Summary string if found, None otherwise
        """
        for message in reversed(messages):
            message_type = getattr(message, "type", None)
            if not message_type and hasattr(message, "__class__"):
                message_type = message.__class__.__name__.replace("Message", "").lower()

            if message_type != "ai":
                continue

            content = getattr(message, "content", None)
            text = extract_text_content(content)
            if text:
                return text

        logger.warning(
            "No AI message with text content found",
            extra={"message_count": len(messages)}
        )
        return None

    def handle_interrupt(
        self,
        sender: str,
        thread_id: str,
        interrupt_value: Any,
    ) -> None:
        """Send WriteIntent interrupts to user for HITL approval.

        Args:
            sender: Channel-specific sender ID
            thread_id: Conversation thread ID
            interrupt_value: Interrupt value (WriteIntent dict or action_requests)
        """
        logger.debug(
            "Handling HITL interrupt",
            extra={
                "thread_id": thread_id,
                "interrupt_type": type(interrupt_value).__name__,
            }
        )

        try:
            # Handle DeepAgents interrupt format with action_requests
            if isinstance(interrupt_value, dict) and "action_requests" in interrupt_value:
                action_requests = interrupt_value.get("action_requests", [])
                logger.info(
                    "Processing DeepAgents interrupt",
                    extra={"thread_id": thread_id, "action_count": len(action_requests)}
                )

                for action_req in action_requests:
                    tool_name = action_req.get("name", "unknown")
                    args = action_req.get("args", {})

                    if tool_name == "write_data" and self._is_write_intent(args):
                        self._send_write_intent_approval(sender, args)
                        return

                # No WriteIntent found in action_requests
                logger.warning(
                    "No WriteIntent found in action_requests",
                    extra={"thread_id": thread_id, "tools": [ar.get("name") for ar in action_requests]}
                )

            # Handle legacy list format
            elif isinstance(interrupt_value, list) and len(interrupt_value) > 0:
                for action in interrupt_value:
                    if isinstance(action, dict) and "action_request" in action:
                        action_request = action.get("action_request", {})
                        args = action_request.get("args", {})
                        tool_name = action_request.get("action", "unknown")

                        if tool_name == "write_data" and self._is_write_intent(args):
                            self._send_write_intent_approval(sender, args)
                            return

            # Handle single dict (direct WriteIntent)
            elif isinstance(interrupt_value, dict) and self._is_write_intent(interrupt_value):
                self._send_write_intent_approval(sender, interrupt_value)
                return

            # Unknown format
            logger.warning(
                "Unknown interrupt format",
                extra={"thread_id": thread_id, "type": type(interrupt_value).__name__}
            )

        except Exception as exc:
            logger.exception("Failed to send interrupt to user", exc_info=exc, extra={"thread_id": thread_id})
            self.channel.send_error(sender, "processing", "I encountered an issue requesting your input.")

    def _is_write_intent(self, value: dict[str, Any]) -> bool:
        """Check if dict represents a WriteIntent."""
        return (
            isinstance(value, dict)
            and "goal" in value
            and "reasoning" in value
            and "operations" in value
            and "impact" in value
        )

    def _build_storage_url(self, storage_path: str, bucket: str = "assets") -> str | None:
        """Build full Supabase storage URL from storage_path.

        Args:
            storage_path: Relative path within bucket (e.g., "pending/thread_id/image.png")
            bucket: Storage bucket name (default: "assets")

        Returns:
            Full public URL or None if SUPABASE_URL not configured
        """
        if not self._supabase_url:
            logger.warning("Cannot build storage URL: SUPABASE_URL not configured")
            return None
        # Pattern: https://{project}.supabase.co/storage/v1/object/public/{bucket}/{path}
        base_url = self._supabase_url.rstrip("/")
        return f"{base_url}/storage/v1/object/public/{bucket}/{storage_path}"

    def _send_write_intent_approval(self, sender: str, write_intent_dict: dict[str, Any]) -> None:
        """Send WriteIntent approval with images and summary."""
        try:
            write_intent = WriteIntent.model_validate(write_intent_dict)

            logger.info(
                "Sending WriteIntent approval",
                extra={
                    "sender": sender,
                    "goal": write_intent.goal[:50],
                    "asset_count": len(write_intent.asset_uploads),
                    "operation_count": len(write_intent.operations),
                }
            )

            # Send each asset image with caption
            for asset in write_intent.asset_uploads:
                try:
                    # Determine image source (prefer URL for WhatsApp)
                    image_source: str | None = None

                    # 1. Use storage_url if provided
                    if asset.storage_url:
                        image_source = asset.storage_url
                    # 2. Build URL from storage_path if available
                    elif asset.storage_path:
                        image_source = self._build_storage_url(asset.storage_path, asset.bucket)
                    # 3. Fallback to temp_path (local file)
                    elif asset.temp_path:
                        image_source = asset.temp_path

                    if not image_source:
                        logger.warning("Asset has no image source", extra={"returns": asset.returns})
                        continue

                    # For local paths (temp_path), check existence
                    if (
                        asset.temp_path
                        and image_source == asset.temp_path
                        and not Path(image_source).exists()
                    ):
                        logger.warning("Asset file not found", extra={"temp_path": asset.temp_path})
                        continue

                    logger.info(
                        "Sending asset image for HITL preview",
                        extra={"returns": asset.returns, "source": image_source[:50]}
                    )

                    self.channel.send_image(
                        sender,
                        image_source,
                        caption=asset.caption if asset.caption else None,
                    )
                except Exception as img_err:
                    logger.warning("Failed to send asset image", extra={"error": str(img_err), "returns": asset.returns})

            # Send summary text (required - LLM must generate)
            if not write_intent.hitl_summary:
                logger.error(
                    "WriteIntent missing hitl_summary - LLM prompt violation",
                    extra={"sender": sender, "goal": write_intent.goal[:50]}
                )
                raise ValueError("hitl_summary is required - LLM must generate approval summary")
            self.channel.send_text(sender, write_intent.hitl_summary)

            logger.info(
                "WriteIntent approval sent",
                extra={"sender": sender, "summary_length": len(write_intent.hitl_summary)}
            )

        except Exception as e:
            logger.error("Failed to send WriteIntent approval", extra={"error": str(e)}, exc_info=True)
            fallback_msg = (
                f"*Database Operation Approval*\n\n"
                f"*Goal:* {write_intent_dict.get('goal', 'Unknown')}\n\n"
                f"Reply *approve* to proceed or *reject* to cancel."
            )
            self.channel.send_text(sender, fallback_msg)
