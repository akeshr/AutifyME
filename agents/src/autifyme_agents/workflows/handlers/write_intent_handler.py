"""WriteIntent workflow handler - generic HITL approval for database operations."""

from __future__ import annotations

import logging
from typing import Any

from autifyme_agents.core.storage_utils import build_storage_url
from autifyme_agents.core.tool_error_handler import build_agent_error_response
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
            "No AI message with text content found", extra={"message_count": len(messages)}
        )
        return None

    def handle_interrupt(
        self,
        sender: str,
        thread_id: str,
        interrupt_value: Any,
    ) -> dict[str, Any] | None:
        """Send WriteIntent interrupts to user for HITL approval.

        Returns tool-style error dict if validation fails, None on success.
        """
        logger.debug(
            "Handling HITL interrupt",
            extra={
                "thread_id": thread_id,
                "interrupt_type": type(interrupt_value).__name__,
            },
        )

        try:
            # Handle DeepAgents interrupt format with action_requests
            if isinstance(interrupt_value, dict) and "action_requests" in interrupt_value:
                action_requests = interrupt_value.get("action_requests", [])
                logger.info(
                    "Processing DeepAgents interrupt",
                    extra={"thread_id": thread_id, "action_count": len(action_requests)},
                )

                for action_req in action_requests:
                    if action_req.get("name") == "write_data":
                        return self._send_write_intent_approval(sender, action_req.get("args", {}))
                return None

            elif isinstance(interrupt_value, list) and len(interrupt_value) > 0:
                for action in interrupt_value:
                    if isinstance(action, dict) and "action_request" in action:
                        action_request = action.get("action_request", {})
                        if action_request.get("action") == "write_data":
                            return self._send_write_intent_approval(
                                sender, action_request.get("args", {})
                            )
                return None

            return None

        except Exception as exc:
            logger.exception("Failed to process interrupt", exc_info=exc)
            return build_agent_error_response(
                exception=exc,
                context={"thread_id": thread_id},
                fallback_type="HITL_ERROR",
                fallback_action="Interrupt processing failed. Retry write_data call.",
            )

    # Fields that belong to WriteIntent domain model (excludes tool-layer fields like dry_run)
    _WRITE_INTENT_FIELDS = {
        "goal",
        "reasoning",
        "hitl_summary",
        "asset_uploads",
        "operations",
        "impact",
    }

    def _send_write_intent_approval(
        self, sender: str, write_intent_dict: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Send WriteIntent approval with images and summary.

        Returns None on success (HITL sent to user), error dict on validation failure.
        """
        # Filter to WriteIntent fields only
        filtered_dict = {
            k: v for k, v in write_intent_dict.items() if k in self._WRITE_INTENT_FIELDS
        }

        # Validate first - don't send HITL if invalid
        try:
            write_intent = WriteIntent.model_validate(filtered_dict)
        except Exception as e:
            return build_agent_error_response(
                exception=e,
                context={"goal": write_intent_dict.get("goal", "unknown")},
                fallback_type="VALIDATION_ERROR",
                fallback_action="write_data requires: goal, reasoning, hitl_summary, operations, impact. Add missing fields.",
            )

        # Send HITL to user
        logger.info(
            "Sending WriteIntent approval",
            extra={
                "sender": sender,
                "goal": write_intent.goal[:50],
                "asset_count": len(write_intent.asset_uploads),
                "operation_count": len(write_intent.operations),
            },
        )

        # Send each asset image
        images_sent = 0
        for asset in write_intent.asset_uploads:
            try:
                image_source: str | None = None
                if asset.storage_path:
                    image_source = build_storage_url(asset.storage_path, asset.bucket)
                elif asset.temp_path:
                    image_source = asset.temp_path

                if image_source:
                    self.channel.send_image(sender, image_source, caption=asset.caption or None)
                    images_sent += 1
            except Exception as img_err:
                logger.warning(f"Image send failed for {asset.returns}: {img_err}")

        # Send summary text
        summary = write_intent.hitl_summary
        self.channel.send_text(sender, summary)

        logger.info(
            "WriteIntent approval sent", extra={"sender": sender, "images_sent": images_sent}
        )
        return None
