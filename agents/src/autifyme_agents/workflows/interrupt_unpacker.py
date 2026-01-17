"""Interrupt unpacker - normalizes LangGraph interrupts into flat list format."""

from __future__ import annotations

import logging
from typing import Any

from autifyme_agents.schemas.interrupt import InterruptInfo

logger = logging.getLogger(__name__)


class InterruptUnpacker:
    """Unpacks LangGraph interrupts into normalized format for approval processing.

    Handles complex interrupt formats:
    - List-valued interrupts (parallel tool calls from same agent)
    - DeepAgents batch HITL format (dict with action_requests list)
    - Dict-valued interrupts (single action)
    - Unknown formats (defensive fallback)

    Normalizes all formats into flat list of interrupt_info dicts for approval analyzer.
    """

    @staticmethod
    def unpack_interrupts(
        state_snapshot: Any,
        thread_id: str | None = None,
    ) -> list[InterruptInfo]:
        """Unpack LangGraph interrupts into normalized flat list.

        IMPORTANT: interrupt_obj.value can be:
        - A list of actions (parallel tool calls from same agent)
        - A dict with 'action_requests' list (DeepAgents batch HITL format)
        - A single dict (single action)
        - Unknown format (fallback handling)

        We create N InterruptInfo objects for approval analyzer (1 response per action).

        Args:
            state_snapshot: LangGraph StateSnapshot with interrupts
            thread_id: Optional thread ID for logging

        Returns:
            List of normalized InterruptInfo objects with type-safe fields
        """
        pending_interrupts_list: list[InterruptInfo] = []

        if not state_snapshot or not state_snapshot.interrupts:
            return pending_interrupts_list

        for base_idx, interrupt_obj in enumerate(state_snapshot.interrupts):
            interrupt_id = (
                interrupt_obj.id if hasattr(interrupt_obj, "id") else f"interrupt_{base_idx}"
            )
            interrupt_value = interrupt_obj.value if hasattr(interrupt_obj, "value") else None

            logger.info(
                f"[UNPACK] Found interrupt with ID={interrupt_id}, value_type={type(interrupt_value).__name__}"
            )

            # Case 1: List-valued interrupt (parallel tool calls)
            if isinstance(interrupt_value, list):
                logger.debug(
                    "Unpacking list-valued interrupt into individual actions",
                    extra={
                        "thread_id": thread_id or "unknown",
                        "interrupt_id": interrupt_id,
                        "action_count": len(interrupt_value),
                    },
                )

                # Create one interrupt_info per action
                for action_idx, action in enumerate(interrupt_value):
                    # Extract metadata from action
                    if isinstance(action, dict):
                        action_request = action.get("action_request", {})
                        tool_name = action_request.get("action", "unknown")
                        tool_args = action_request.get("args", {})
                        description = action.get("description", f"Action {action_idx + 1}")
                    else:
                        tool_name = "unknown"
                        tool_args = {}
                        description = str(action)[:100]

                    interrupt_info = InterruptInfo(
                        interrupt_id=f"{interrupt_id}_{action_idx}",
                        original_interrupt_id=interrupt_id,
                        tool_name=tool_name,
                        tool_args=tool_args,
                        description=description,
                    )
                    pending_interrupts_list.append(interrupt_info)
                    logger.info(
                        f"[RESUME ORDER] Interrupt {action_idx + 1}: {tool_args.get('name', 'unknown')}"
                    )

            # Case 2a: DeepAgents batch HITL format (action_requests list)
            elif isinstance(interrupt_value, dict) and "action_requests" in interrupt_value:
                action_requests = interrupt_value.get("action_requests", [])

                if isinstance(action_requests, list):
                    logger.debug(
                        "Unpacking DeepAgents batch HITL interrupt into individual actions",
                        extra={
                            "thread_id": thread_id or "unknown",
                            "interrupt_id": interrupt_id,
                            "action_count": len(action_requests),
                        },
                    )

                    # Create one interrupt_info per action_request
                    for action_idx, action_request in enumerate(action_requests):
                        if isinstance(action_request, dict):
                            tool_name = action_request.get("name", "unknown")
                            tool_args = action_request.get("args", {})
                            description = action_request.get(
                                "description", f"Action {action_idx + 1}"
                            )
                        else:
                            tool_name = "unknown"
                            tool_args = {}
                            description = str(action_request)[:200]

                        interrupt_info = InterruptInfo(
                            interrupt_id=f"{interrupt_id}_{action_idx}",
                            original_interrupt_id=interrupt_id,
                            tool_name=tool_name,
                            tool_args=tool_args,
                            description=description,
                        )
                        pending_interrupts_list.append(interrupt_info)
                        logger.info(
                            f"[BATCH HITL] Action {action_idx + 1}: {tool_name} - {tool_args.get('name', 'unknown')}"
                        )
                else:
                    # Fallback if action_requests is not a list
                    logger.warning(
                        "action_requests key found but value is not a list",
                        extra={
                            "thread_id": thread_id or "unknown",
                            "interrupt_id": interrupt_id,
                            "action_requests_type": type(action_requests).__name__,
                        },
                    )
                    interrupt_info = InterruptInfo(
                        interrupt_id=interrupt_id,
                        original_interrupt_id=interrupt_id,
                        tool_name="unknown",
                        tool_args={},
                        description=str(interrupt_value)[:200],
                    )
                    pending_interrupts_list.append(interrupt_info)

            # Case 2: Dict-valued interrupt (single action)
            elif isinstance(interrupt_value, dict):
                interrupt_info = InterruptInfo(
                    interrupt_id=interrupt_id,
                    original_interrupt_id=interrupt_id,
                    tool_name=interrupt_value.get("tool_name", "unknown"),
                    tool_args=interrupt_value.get("tool_args", {}),
                    description=str(interrupt_value)[:100],
                )
                pending_interrupts_list.append(interrupt_info)

            # Case 3: Unknown format (defensive fallback)
            else:
                logger.warning(
                    "Unknown interrupt value format, using fallback",
                    extra={
                        "thread_id": thread_id or "unknown",
                        "interrupt_id": interrupt_id,
                        "value_type": type(interrupt_value).__name__,
                    },
                )
                interrupt_info = InterruptInfo(
                    interrupt_id=interrupt_id,
                    original_interrupt_id=interrupt_id,
                    tool_name="unknown",
                    tool_args={},
                    description=str(interrupt_value)[:100]
                    if interrupt_value
                    else "Pending approval",
                )
                pending_interrupts_list.append(interrupt_info)

        logger.debug(
            "Interrupt unpacking complete",
            extra={
                "thread_id": thread_id or "unknown",
                "total_interrupts": len(pending_interrupts_list),
            },
        )

        return pending_interrupts_list
