"""WriteIntent workflow handler - generic HITL approval for database operations."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from autifyme_agents.core.storage_utils import build_storage_url
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

    def __init__(self, channel: MessagingChannel):
        """Initialize handler.

        Args:
            channel: Messaging channel for sending user notifications
        """
        self.channel = channel

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

    # Fields that belong to WriteIntent domain model (excludes tool-layer fields like dry_run)
    _WRITE_INTENT_FIELDS = {"goal", "reasoning", "hitl_summary", "asset_uploads", "operations", "impact"}

    def _send_write_intent_approval(self, sender: str, write_intent_dict: dict[str, Any]) -> None:
        """Send WriteIntent approval with images and summary."""
        try:
            # Filter to WriteIntent fields only - tool args may contain extra fields
            # (e.g., dry_run, validate_only from WriteDataInput) that WriteIntent rejects
            filtered_dict = {
                k: v for k, v in write_intent_dict.items()
                if k in self._WRITE_INTENT_FIELDS
            }
            write_intent = WriteIntent.model_validate(filtered_dict)

            logger.info(
                "Sending WriteIntent approval",
                extra={
                    "sender": sender,
                    "goal": write_intent.goal[:50],
                    "asset_count": len(write_intent.asset_uploads),
                    "operation_count": len(write_intent.operations),
                }
            )

            # Track image sending results
            images_sent = 0
            image_errors: list[str] = []

            # Send each asset image with caption
            for asset in write_intent.asset_uploads:
                try:
                    # Determine image source
                    image_source: str | None = None

                    # 1. Build URL from storage_path (primary path for Supabase files)
                    if asset.storage_path:
                        try:
                            image_source = build_storage_url(asset.storage_path, asset.bucket)
                        except ValueError as e:
                            error_msg = f"URL build failed for {asset.returns}: {e}"
                            logger.error(error_msg)
                            image_errors.append(error_msg)
                            continue
                    # 2. Fallback to temp_path (local file for external uploads)
                    elif asset.temp_path:
                        image_source = asset.temp_path

                    if not image_source:
                        error_msg = f"No image source for {asset.returns}"
                        logger.error(error_msg)
                        image_errors.append(error_msg)
                        continue

                    # For local paths (temp_path), check existence
                    if asset.temp_path and not Path(image_source).exists():
                        error_msg = f"File not found: {asset.temp_path}"
                        logger.error(error_msg)
                        image_errors.append(error_msg)
                        continue

                    logger.info(
                        "Sending asset image for HITL preview",
                        extra={"returns": asset.returns, "source": image_source[:80]}
                    )

                    self.channel.send_image(
                        sender,
                        image_source,
                        caption=asset.caption if asset.caption else None,
                    )
                    images_sent += 1

                except Exception as img_err:
                    error_msg = f"Send failed for {asset.returns}: {img_err}"
                    logger.error(error_msg, exc_info=True)
                    image_errors.append(error_msg)

            # Log summary
            logger.info(
                "Image sending complete",
                extra={
                    "sender": sender,
                    "total": len(write_intent.asset_uploads),
                    "sent": images_sent,
                    "errors": len(image_errors),
                }
            )

            # Send summary text (required - LLM must generate)
            if not write_intent.hitl_summary:
                logger.error(
                    "WriteIntent missing hitl_summary - LLM prompt violation",
                    extra={"sender": sender, "goal": write_intent.goal[:50]}
                )
                raise ValueError("hitl_summary is required - LLM must generate approval summary")

            # Append error info if images failed
            summary = write_intent.hitl_summary
            if image_errors:
                summary += f"\n\n[{len(image_errors)} image(s) failed to send]"

            self.channel.send_text(sender, summary)

            logger.info(
                "WriteIntent approval sent",
                extra={"sender": sender, "summary_length": len(summary), "images_sent": images_sent}
            )

        except Exception as e:
            logger.error("Failed to send WriteIntent approval", extra={"error": str(e)}, exc_info=True)
            fallback_msg = (
                f"*Database Operation Approval*\n\n"
                f"*Goal:* {write_intent_dict.get('goal', 'Unknown')}\n\n"
                f"Reply *approve* to proceed or *reject* to cancel."
            )
            self.channel.send_text(sender, fallback_msg)
