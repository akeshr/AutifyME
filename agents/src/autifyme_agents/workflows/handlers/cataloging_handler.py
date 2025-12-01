"""Cataloging workflow handler - domain-specific logic extracted from runner."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from autifyme_agents.schemas.models import CatalogingResult
from autifyme_agents.schemas.write_intent import WriteIntent
from autifyme_agents.workflows.channels.protocol import MessagingChannel
from autifyme_agents.workflows.message_utils import extract_text_content

logger = logging.getLogger(__name__)


class CatalogingWorkflowHandler:
    """Handles cataloging-specific result extraction and interrupt handling.

    Extracted from WorkflowRunner to achieve separation of concerns.
    Generic runner delegates cataloging domain logic to this handler.
    """

    def __init__(self, channel: MessagingChannel):
        """Initialize cataloging handler.

        Args:
            channel: Messaging channel for sending user notifications
        """
        self.channel = channel

    def extract_result(self, messages: list[Any]) -> CatalogingResult | None:
        """Extract CatalogingResult from PM messages.

        Args:
            messages: PM output messages

        Returns:
            CatalogingResult if found, None otherwise
        """
        for message in messages:
            message_type = getattr(message, "type", None)
            if not message_type and hasattr(message, "__class__"):
                message_type = message.__class__.__name__.replace("Message", "").lower()
            if message_type != "tool":
                continue

            content = getattr(message, "content", None)

            if isinstance(content, dict):
                tool_name = content.get("tool_name")
                if tool_name != "save_product":
                    continue

                try:
                    from autifyme_agents.schemas.agent_outputs import CatalogingToolOutput

                    tool_output = CatalogingToolOutput.model_validate(content)
                    return tool_output.result
                except ValueError:
                    continue
            else:
                tool_call_id = getattr(message, "tool_call_id", None)
                if tool_call_id:
                    result = self._find_tool_call_args(messages, tool_call_id)
                    if result:
                        return result

        return None

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
            "Handling cataloging interrupt",
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

    def _find_tool_call_args(
        self,
        messages: list[Any],
        tool_call_id: str,
    ) -> CatalogingResult | None:
        """Find tool call arguments in AI message by tool_call_id."""
        for message in messages:
            message_type = getattr(message, "type", None)
            if not message_type and hasattr(message, "__class__"):
                message_type = message.__class__.__name__.replace("Message", "").lower()
            if message_type != "ai":
                continue

            tool_calls = getattr(message, "tool_calls", None)
            if not tool_calls:
                continue

            for tc in tool_calls:
                if tc.get("id") == tool_call_id:
                    args = tc.get("args", {})
                    try:
                        return CatalogingResult.model_validate(args)
                    except Exception:
                        continue

        return None

    def _is_write_intent(self, value: dict[str, Any]) -> bool:
        """Check if dict represents a WriteIntent."""
        return (
            isinstance(value, dict)
            and "goal" in value
            and "reasoning" in value
            and "operations" in value
            and "impact" in value
        )

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
                    if not Path(asset.temp_path).exists():
                        logger.warning("Asset file not found", extra={"temp_path": asset.temp_path})
                        continue

                    self.channel.send_image(
                        sender,
                        asset.temp_path,
                        caption=asset.caption if asset.caption else None,
                    )
                except Exception as img_err:
                    logger.warning("Failed to send asset image", extra={"error": str(img_err)})

            # Send summary text
            summary = write_intent.hitl_summary or write_intent.generate_hitl_summary()
            self.channel.send_text(sender, summary)

            logger.info(
                "WriteIntent approval sent",
                extra={"sender": sender, "summary_length": len(summary)}
            )

        except Exception as e:
            logger.error("Failed to send WriteIntent approval", extra={"error": str(e)}, exc_info=True)
            fallback_msg = (
                f"*Database Operation Approval*\n\n"
                f"*Goal:* {write_intent_dict.get('goal', 'Unknown')}\n\n"
                f"Reply *approve* to proceed or *reject* to cancel."
            )
            self.channel.send_text(sender, fallback_msg)
