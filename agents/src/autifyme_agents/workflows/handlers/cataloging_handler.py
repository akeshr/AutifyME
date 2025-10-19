"""Cataloging workflow handler - domain-specific logic extracted from runner."""

from __future__ import annotations

import logging
from typing import Any

from autifyme_agents.schemas.models import CatalogingResult, Product
from autifyme_agents.workflows.channels.protocol import MessagingChannel

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

        Handles two formats:
        1. Initial workflow: Tool message with dict content {tool_name, result}
        2. Resume workflow: Tool message with tool_call_id referencing AI message

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

            # Format 1: Dict content with tool_name and result
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

            # Format 2: String content (resume workflow) - find tool call
            else:
                tool_call_id = getattr(message, "tool_call_id", None)
                if tool_call_id:
                    result = self._find_tool_call_args(messages, tool_call_id, "save_product")
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
            if isinstance(content, str):
                return content

        return None

    def handle_interrupt(
        self,
        sender: str,
        thread_id: str,
        interrupt_value: Any,
    ) -> None:
        """Send cataloging-specific Product interrupts to user.

        Handles batch approval for parallel tool calls.

        Args:
            sender: Channel-specific sender ID
            thread_id: Conversation thread ID
            interrupt_value: Interrupt value (may be list of actions or single dict)
        """
        logger.debug(
            "Handling cataloging interrupt",
            extra={
                "thread_id": thread_id,
                "interrupt_type": type(interrupt_value).__name__,
                "is_list": isinstance(interrupt_value, list),
                "length_if_list": len(interrupt_value) if isinstance(interrupt_value, list) else "N/A",
            }
        )

        try:
            # Collect all products (for batch approval)
            products_to_approve: list[Product] = []

            if isinstance(interrupt_value, list) and len(interrupt_value) > 0:
                # Parallel tool calls - collect ALL products
                logger.info(
                    "Processing batch interrupt",
                    extra={"thread_id": thread_id, "action_count": len(interrupt_value)}
                )

                for idx, action in enumerate(interrupt_value):
                    if isinstance(action, dict) and "action_request" in action:
                        # DeepAgents format - extract clean args
                        action_request = action.get("action_request", {})
                        clean_value = action_request.get("args", {})
                        tool_name = action_request.get("action", "unknown")

                        logger.debug(
                            f"Unwrapping action {idx + 1} of {len(interrupt_value)}",
                            extra={
                                "thread_id": thread_id,
                                "tool_name": tool_name,
                                "product_name": clean_value.get("name", "unknown"),
                            }
                        )

                        # Convert to Product and add to batch
                        if isinstance(clean_value, dict):
                            draft = Product.model_validate(clean_value)
                            products_to_approve.append(draft)

                # Send all products in batch
                if len(products_to_approve) > 0:
                    logger.info(
                        "Sending batch approval request",
                        extra={
                            "thread_id": thread_id,
                            "product_count": len(products_to_approve),
                            "product_names": [p.name for p in products_to_approve],
                        }
                    )

                    if len(products_to_approve) == 1:
                        # Single product - use standard approval request
                        self.channel.send_approval_request(sender, products_to_approve[0])
                    else:
                        # Multiple products - send batch approval
                        self._send_batch_approval(sender, products_to_approve)

            # Handle single interrupt case
            elif isinstance(interrupt_value, dict):
                logger.info(
                    "Processing single interrupt",
                    extra={"thread_id": thread_id}
                )

                # Convert dict args to Product object for channel
                draft = Product.model_validate(interrupt_value)
                logger.debug(
                    "Converted single interrupt to Product",
                    extra={"thread_id": thread_id, "product_name": draft.name}
                )
                self.channel.send_approval_request(sender, draft)

            logger.info(
                "Interrupt(s) forwarded to user - awaiting response",
                extra={
                    "thread_id": thread_id,
                    "product_count": len(products_to_approve) if products_to_approve else 1,
                },
            )

        except Exception as exc:
            logger.exception("Failed to send interrupt to user", exc_info=exc, extra={"thread_id": thread_id})
            self.channel.send_error(sender, "processing", "I encountered an issue requesting your input.")

    # --- Internal Methods ---

    def _find_tool_call_args(
        self,
        messages: list[Any],
        tool_call_id: str,
        tool_name: str,
    ) -> CatalogingResult | None:
        """Find tool call arguments in AI message by tool_call_id.

        Used for resume workflows where tool message has string content.

        Args:
            messages: All messages
            tool_call_id: ID to match
            tool_name: Expected tool name

        Returns:
            CatalogingResult if found
        """
        for message in messages:
            message_type = getattr(message, "type", None)
            if not message_type and hasattr(message, "__class__"):
                message_type = message.__class__.__name__.replace("Message", "").lower()
            if message_type != "ai":
                continue

            # Check for tool_calls
            tool_calls = getattr(message, "tool_calls", None)
            if not tool_calls:
                continue

            for tc in tool_calls:
                tc_id = tc.get("id")

                # Match on ID regardless of name - resume flows use "task" instead of "save_product"
                if tc_id == tool_call_id:
                    args = tc.get("args", {})

                    # Try direct validation
                    try:
                        result = CatalogingResult.model_validate(args)
                        return result
                    except Exception:
                        # Validation failed, continue to next tool call
                        pass

        return None

    def _send_batch_approval(self, sender: str, products: list[Product]) -> None:
        """Send batch approval request with ALL products displayed together.

        Args:
            sender: Channel-specific sender ID
            products: List of Product objects to approve
        """
        # Format batch approval message
        message_parts = [
            f"**Batch Approval Request** ({len(products)} products)",
            "",
            "Please review the following products:",
            "",
        ]

        for idx, product in enumerate(products, 1):
            # Format each product
            product_lines = [
                f"**Product {idx}:**",
                f"  - Name: {product.name}",
                f"  - Description: {product.description}",
                f"  - Price: Rs {product.price}",
            ]

            if product.sizes:
                product_lines.append(f"  - Sizes: {', '.join(product.sizes)}")
            if product.colors:
                product_lines.append(f"  - Colors: {', '.join(product.colors)}")
            if product.image_urls:
                product_lines.append(f"  - Images: {len(product.image_urls)} attached")

            message_parts.extend(product_lines)
            message_parts.append("")  # Blank line between products

        message_parts.extend([
            "---",
            "",
            "**How to respond:**",
            "- To approve all: 'approve' or 'yes'",
            "- To approve some: 'approve 1 and 2' or 'approve product 1'",
            "- To edit: 'edit product 2 price to 45'",
            "- To reject all: 'reject' or 'no'",
        ])

        # Send formatted message
        batch_message = "\n".join(message_parts)
        self.channel.send_text(sender, batch_message)
