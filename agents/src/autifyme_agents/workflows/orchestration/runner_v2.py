"""Generic HITL Framework - Structured Output Architecture.

Runner is a BLIND EXECUTOR that coordinates between PM and approval analyzer.

## STRUCTURED OUTPUT ARCHITECTURE (2025-10-14)

**Key Principle**: Use Pydantic structured outputs everywhere. No text parsing.

**Components**:
- **PM**: Orchestration (delegates tasks to departments)
- **Approval Analyzer**: HITL interpretation (structured BatchApprovalResponse)
- **Runner**: Coordination (routes based on state, manages interrupts)

## How It Works

### 1. New Request Flow
```
User message → Runner → PM → Departments → HITL interrupt → Channel
```
1. User sends message
2. Runner forwards raw payload to PM
3. PM detects intent, extracts data, downloads media
4. PM delegates to departments via task() tool
5. If department needs approval → interrupt occurs
6. Runner sends approval request to user via channel

### 2. Resume Flow (Structured Batch Approval)
```
User approval → Runner → Approval Analyzer → BatchApprovalResponse → Command → Resume
```
1. User responds (e.g., "approve both", "edit price to 45")
2. Runner detects pending interrupts in checkpoint
3. **Runner invokes approval analyzer** (not PM!)
4. **Approval analyzer returns BatchApprovalResponse** (Pydantic model)
5. Runner builds Command from structured response
6. Runner executes Command
7. HITL middleware receives N responses for N interrupts
8. Workflow resumes
9. ✅ **NO TEXT PARSING - TYPE SAFE!**

**Benefits**:
- ✅ Type safety with Pydantic throughout
- ✅ No brittle text parsing
- ✅ Clear separation: PM = orchestration, Analyzer = HITL interpretation
- ✅ Batch approval works correctly (N responses for N interrupts)
- ✅ Production-grade architecture
- ✅ Easy to test and validate
"""

from __future__ import annotations

import json
import logging
from collections import OrderedDict
from threading import Lock
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.errors import GraphInterrupt, GraphRecursionError

from autifyme_agents.core.config import settings
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from autifyme_agents.schemas.models import CatalogingResult, CompanyProfile
from autifyme_agents.workflows.channels.protocol import MessagingChannel
from autifyme_agents.workflows.handlers.approval_coordinator import ApprovalCoordinator
from autifyme_agents.workflows.handlers.protocol import WorkflowHandler
from autifyme_agents.workflows.interrupt_unpacker import InterruptUnpacker
from autifyme_agents.workflows.middleware.outcome_tracking_middleware import (
    OutcomeTrackingMiddleware,
)
from autifyme_agents.workflows.outcome_tracker import IncomingMessage, OutcomeTracker
from autifyme_agents.workflows.project_manager import create_project_manager

logger = logging.getLogger(__name__)

# Constants
MAX_THREAD_LOCKS = 1000  # LRU cache size for thread locks


class WorkflowRunner:
    """Blind executor - forwards messages to PM for intelligent orchestration.

    ## STRUCTURED OUTPUT ARCHITECTURE:

    Runner responsibilities:
    - Forward ALL messages to PM (blind infrastructure)
    - Extract interrupt context from checkpoints
    - Invoke approval_analyzer for HITL decisions
    - Build Commands from structured responses
    - Execute Commands for workflow resumption
    - Send interrupts/results to user via channel

    PM handles:
    - Intent detection for new requests
    - Task orchestration and delegation to departments
    - Media download and processing
    - Overall workflow management

    Approval Analyzer handles:
    - HITL interpretation (structured BatchApprovalResponse)
    - Batch approval decisions with conversation context
    - Type-safe approval/reject/edit responses

    LangGraph + DeepAgents handle:
    - Checkpoint state management
    - HITL middleware interrupt/resume
    - Message sequence synthesis
    - Tool execution

    ## KEY BENEFITS:
    - Type-safe with Pydantic throughout
    - Clear separation of concerns
    - PM = orchestration, Analyzer = HITL interpretation
    - Batch approval works correctly
    - Production-ready architecture
    """

    def __init__(
        self,
        *,
        channel: MessagingChannel,
        storage: StorageInterface,
        workflow_handler: WorkflowHandler,
        checkpointer: BaseCheckpointSaver[Any] | None = None,
        recursion_limit: int | None = None,
    ):
        """Initialize workflow runner.

        Args:
            channel: Messaging channel adapter (WhatsApp, Telegram, etc.)
            storage: Storage adapter for company profile and products
            workflow_handler: Workflow-specific handler for domain logic
            checkpointer: LangGraph checkpointer (creates default if None)
            recursion_limit: Max PM recursion depth
        """
        logger.info("=" * 80)
        logger.info("INITIALIZING GENERIC HITL FRAMEWORK (APPROVAL_ANALYZER ARCHITECTURE)")
        logger.info("=" * 80)

        self.channel = channel
        self.storage = storage
        self.workflow_handler = workflow_handler
        self.recursion_limit = recursion_limit or settings.AGENT_RECURSION_LIMIT

        logger.debug(
            "Runner configuration",
            extra={
                "channel": channel.__class__.__name__,
                "workflow_handler": workflow_handler.__class__.__name__,
                "recursion_limit": self.recursion_limit,
                "has_custom_checkpointer": checkpointer is not None,
            },
        )

        # Load company context once (single-tenant)
        logger.info("Loading company profile from storage...")
        self.company_profile: CompanyProfile = storage.get_company_profile()
        logger.info(
            "Company profile loaded",
            extra={"company_name": self.company_profile.name},
        )

        # Checkpointer management
        self._checkpointer = checkpointer

        # Thread safety: LRU lock manager per sender
        self._thread_locks: OrderedDict[str, Lock] = OrderedDict()
        self._locks_mutex = Lock()

        # Phase 1: Outcome tracking for agentic learning
        self.outcome_tracker = OutcomeTracker(storage)
        logger.info("OutcomeTracker initialized")

        # Outcome tracking middleware (wraps PM invocation with automatic tracking)
        self.tracking_middleware = OutcomeTrackingMiddleware(
            outcome_tracker=self.outcome_tracker,
            workflow_handler=self.workflow_handler,
        )
        logger.info("Outcome tracking middleware initialized")

        # Approval coordinator (handles approval analyzer invocation with tracking)
        self.approval_coordinator = ApprovalCoordinator(
            outcome_tracker=self.outcome_tracker,
            channel=self.channel,
        )
        logger.info("Approval coordinator initialized")

        logger.info("Generic HITL Framework initialized - approval_analyzer architecture")
        logger.info("=" * 80)

    def handle_message(
        self,
        sender: str,
        text: str | None,
        media_id: str | None,
        sender_name: str | None = None,
    ) -> None:
        """Process incoming message by forwarding to PM.

        Args:
            sender: Channel-specific sender ID (e.g., phone number)
            text: Message text (optional)
            media_id: Media attachment ID (optional, channel-specific)
            sender_name: User's display name for personalization (optional)
        """
        logger.info(
            "Handling incoming message",
            extra={
                "sender": sender,
                "sender_name": sender_name,
                "has_text": text is not None,
                "has_media": media_id is not None,
            },
        )

        # Thread safety - serialize per sender
        thread_id = self.channel.format_thread_id(sender)
        lock = self._get_lock(sender)

        with lock:
            self._execute_workflow(thread_id, sender, text, media_id, sender_name)

    def _execute_workflow(
        self,
        thread_id: str,
        sender: str,
        text: str | None,
        media_id: str | None,
        sender_name: str | None = None,
    ) -> None:
        """Execute workflow: forward message to PM, handle any interrupts.

        Uses outcome tracking middleware for automatic tracking.

        Args:
            thread_id: Conversation thread ID
            sender: Channel-specific sender ID
            text: Message text (optional)
            media_id: Media attachment ID (optional)
            sender_name: User's display name for personalization (optional)
        """
        logger.debug(
            "Executing workflow",
            extra={"thread_id": thread_id, "has_text": text is not None, "has_media": media_id is not None},
        )

        # Prepare structured incoming message
        incoming_message = IncomingMessage(
            sender_id=sender,
            sender_name=sender_name,
            text=text,
            media_id=media_id,
            platform=self.channel.__class__.__name__.replace("Channel", "").lower(),
        )

        # Build raw payload for PM
        raw_payload = {
            "platform": incoming_message.platform,
            "sender": sender,
            "sender_name": sender_name,
            "text": text,
            "media_id": media_id,
            "timestamp": incoming_message.received_at.isoformat(),
        }

        try:
            # Execute with automatic outcome tracking via middleware
            result, interrupt_value, tracking_id = self.tracking_middleware.execute_with_tracking(
                thread_id=thread_id,
                incoming_message=incoming_message,
                pm_invoker=lambda tid: self._invoke_pm(thread_id, raw_payload, run_id=tid),
            )

            # Handle user-facing logic (middleware handles tracking)
            if interrupt_value:
                self.workflow_handler.handle_interrupt(sender, thread_id, interrupt_value)
                return

            if not result:
                return

            # Send workflow-specific completion to user
            cataloging_result = self.workflow_handler.extract_result(result.get("messages", []))
            if cataloging_result:
                self.channel.send_completion(sender, cataloging_result)
                logger.info("Workflow completed", extra={"thread_id": thread_id, "tracking_id": tracking_id})
                return

            # Send conversational response
            summary = self.workflow_handler.extract_summary(result.get("messages", []))
            if summary:
                self.channel.send_text(sender, summary)

        except GraphRecursionError as exc:
            logger.exception("PM recursion limit exceeded", exc_info=exc)
            self.channel.send_error(sender, "recursion")

        except Exception as exc:
            logger.exception("PM invocation failed", exc_info=exc)
            self.channel.send_error(sender, "processing")

    def _invoke_pm(
        self,
        thread_id: str,
        raw_payload: dict[str, Any],
        run_id: str | None = None,
    ) -> tuple[dict[str, Any] | None, Any | None]:
        """Invoke PM with raw message payload.

        ✅ APPROVAL_ANALYZER ARCHITECTURE:
        - PM handles orchestration and intent detection
        - approval_analyzer handles HITL decisions (structured BatchApprovalResponse)
        - Runner coordinates between them

        When interrupts exist:
        1. Extract interrupt context from checkpoint
        2. Invoke approval_analyzer with user message + conversation history
        3. Get structured BatchApprovalResponse
        4. Build Command from structured response
        5. Resume workflow with Command

        Args:
            thread_id: Conversation thread ID
            raw_payload: Raw platform message dict

        Returns:
            Tuple of (final_result, interrupt_value) - at most one will be non-None
        """
        logger.debug("Invoking Project Manager", extra={"thread_id": thread_id})

        pm: Any = self._create_project_manager()
        config = self._build_config(thread_id, run_id=run_id)

        # Check for pending HITL interrupts
        try:
            state_snapshot = pm.get_state(config)

            # Unpack interrupts into normalized format for approval processing
            pending_interrupts_list = InterruptUnpacker.unpack_interrupts(
                state_snapshot, thread_id=thread_id
            )

            if pending_interrupts_list:
                logger.info(
                    "Found pending HITL interrupts",
                    extra={
                        "thread_id": thread_id,
                        "interrupt_count": len(pending_interrupts_list),
                    }
                )
            else:
                logger.debug(
                    "No pending interrupts found",
                    extra={"thread_id": thread_id}
                )
        except Exception as e:
            logger.warning(
                "Failed to check for pending interrupts - treating as new message",
                extra={"thread_id": thread_id, "error": str(e)}
            )

        # Build payload based on checkpoint state
        if pending_interrupts_list:
            # === APPROVAL ANALYZER WITH CONVERSATION HISTORY ===
            # Extract conversation history from PM state for context-aware approval analysis

            user_message = raw_payload.get("text", "")

            # Extract conversation history from PM state
            conversation_history = []
            try:
                state_snapshot = pm.get_state(config)
                if state_snapshot and hasattr(state_snapshot, 'values'):
                    conversation_history = state_snapshot.values.get("messages", [])
                    logger.debug(
                        "Extracted conversation history",
                        extra={
                            "thread_id": thread_id,
                            "history_length": len(conversation_history)
                        }
                    )
            except Exception as e:
                logger.warning(
                    "Could not extract conversation history",
                    extra={"thread_id": thread_id, "error": str(e)}
                )

            # Invoke approval coordinator (handles tracking, error handling, and Command building)
            command_obj, approval_tracking_id = self.approval_coordinator.analyze_and_build_command(
                thread_id=thread_id,
                user_message=user_message,
                pending_interrupts=pending_interrupts_list,
                conversation_history=conversation_history,
                raw_payload=raw_payload,
            )

            if not command_obj:
                # Error already tracked and user notified by coordinator
                return None, None

            # Execute Command to resume workflow
            logger.info(
                "Executing Command to resume workflow",
                extra={"thread_id": thread_id}
            )

            last_event = None
            interrupt_value = None

            try:
                for event in pm.stream(command_obj, config=config, stream_mode="values"):
                    last_event = event

                    # Check for new interrupts (nested workflows)
                    if "__interrupt__" in event:
                        interrupts = event.get("__interrupt__") or []
                        if interrupts:
                            interrupt_value = interrupts[0].value
                            logger.info(
                                "Nested interrupt during resume",
                                extra={"thread_id": thread_id}
                            )

                logger.info(
                    "Command execution complete",
                    extra={
                        "thread_id": thread_id,
                        "had_new_interrupt": interrupt_value is not None,
                    }
                )

                return last_event, interrupt_value

            except GraphInterrupt as interrupt_exc:
                interrupts_list = interrupt_exc.args[0] if interrupt_exc.args else []
                logger.info(
                    "Interrupt detected via exception during resume",
                    extra={
                        "thread_id": thread_id,
                        "interrupt_count": len(interrupts_list),
                    },
                )
                if interrupts_list:
                    return last_event, interrupts_list[0].value
                return last_event, None

            except Exception as e:
                logger.exception(
                    "Command execution error",
                    extra={"thread_id": thread_id, "error_type": type(e).__name__},
                )
                raise

        else:
            # No pending interrupt - normal message flow
            from langchain.messages import HumanMessage
            payload = {"messages": [HumanMessage(content=json.dumps(raw_payload))]}

            logger.debug(
                "Adding new message (no pending interrupt)",
                extra={
                    "thread_id": thread_id,
                    "has_text": raw_payload.get("text") is not None,
                    "has_media": raw_payload.get("media_id") is not None,
                }
            )

            last_event = None
            accumulated_interrupts: list[Any] = []  # ✅ Accumulate ALL interrupts across stream events

            try:
                for event in pm.stream(payload, config=config, stream_mode="values"):
                    last_event = event

                    # Detect interrupt in stream
                    if "__interrupt__" in event:
                        interrupts = event.get("__interrupt__") or []
                        if interrupts:
                            # ✅ ACCUMULATE interrupts from this event
                            # When PM makes 2 parallel task() calls, we get 2 SEPARATE stream events,
                            # each with 1 interrupt. We need to collect all of them.
                            accumulated_interrupts.extend(interrupts)
                            logger.info(
                                "Interrupt event detected",
                                extra={
                                    "thread_id": thread_id,
                                    "event_interrupt_count": len(interrupts),
                                    "total_accumulated": len(accumulated_interrupts),
                                },
                            )

                logger.debug(
                    "PM stream completed",
                    extra={
                        "thread_id": thread_id,
                        "accumulated_interrupt_count": len(accumulated_interrupts),
                    },
                )

                # ✅ Process accumulated interrupts after stream completes
                interrupt_value = None
                if accumulated_interrupts:
                    if len(accumulated_interrupts) > 1:
                        # Multiple interrupts - flatten all values
                        interrupt_value = []
                        for intr in accumulated_interrupts:
                            if isinstance(intr.value, list):
                                interrupt_value.extend(intr.value)
                            else:
                                interrupt_value.append(intr.value)

                        logger.info(
                            "Multiple parallel interrupts collected",
                            extra={
                                "thread_id": thread_id,
                                "interrupt_count": len(accumulated_interrupts),
                                "flattened_count": len(interrupt_value),
                            },
                        )
                    else:
                        # Single interrupt - use value directly
                        interrupt_value = accumulated_interrupts[0].value
                        logger.info(
                            "Single interrupt collected",
                            extra={
                                "thread_id": thread_id,
                            },
                        )

                return last_event, interrupt_value

            except GraphInterrupt as interrupt_exc:
                interrupts_list = interrupt_exc.args[0] if interrupt_exc.args else []
                logger.info(
                    "Interrupt detected via exception",
                    extra={
                        "thread_id": thread_id,
                        "interrupt_count": len(interrupts_list),
                    },
                )
                if interrupts_list:
                    return last_event, interrupts_list[0].value
                return last_event, None

            except Exception as e:
                logger.exception(
                    "PM streaming error",
                    extra={"thread_id": thread_id, "error_type": type(e).__name__},
                )
                raise

    def _send_batch_approval(self, sender: str, products: list[Any]) -> None:
        """Send batch approval request with ALL products displayed together.

        Args:
            sender: Channel-specific sender ID
            products: List of Product objects to approve

        Notes:
            This method formats multiple products into a single approval message
            so users can see and approve all products at once for batch workflows.
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

    def _get_lock(self, sender: str) -> Lock:
        """Get or create thread lock with LRU eviction.

        Args:
            sender: Channel-specific sender ID

        Returns:
            Thread lock for this sender
        """
        # Fast path: lock already exists
        if sender in self._thread_locks:
            with self._locks_mutex:
                self._thread_locks.move_to_end(sender)
            return self._thread_locks[sender]

        # Slow path: create lock with LRU eviction
        with self._locks_mutex:
            # Double-check
            if sender in self._thread_locks:
                self._thread_locks.move_to_end(sender)
                return self._thread_locks[sender]

            # Evict oldest if at capacity
            if len(self._thread_locks) >= MAX_THREAD_LOCKS:
                oldest_sender, _ = self._thread_locks.popitem(last=False)
                logger.debug(
                    "Evicted LRU thread lock",
                    extra={"evicted_sender": oldest_sender, "cache_size": len(self._thread_locks)},
                )

            # Create new lock
            self._thread_locks[sender] = Lock()
            return self._thread_locks[sender]

    def _get_checkpointer(self) -> BaseCheckpointSaver[Any]:
        """Get checkpointer instance."""
        if self._checkpointer:
            return self._checkpointer
        return get_checkpointer()

    def _create_project_manager(self) -> Any:
        """Create PM instance with company context and channel."""
        return create_project_manager(
            company_profile=self.company_profile,
            checkpointer=self._get_checkpointer(),
            storage=self.storage,
            channel=self.channel,
        )

    def _build_config(self, thread_id: str, run_id: str | None = None) -> dict[str, Any]:
        """Build PM config.

        Args:
            thread_id: Conversation thread ID
            run_id: Optional run_id to use as trace_id in LangSmith

        Returns:
            PM config dict
        """
        config = {
            "configurable": {
                "thread_id": thread_id,
                "company_id": "default",
            },
            "recursion_limit": self.recursion_limit,
            "metadata": {
                "langsmith.thread_id": thread_id,
                "workflow": "cataloging",
            },
        }

        # Add run_id if provided - this becomes the trace_id in LangSmith
        if run_id:
            from uuid import UUID
            config["run_id"] = UUID(run_id) if isinstance(run_id, str) else run_id

        return config

    def _find_tool_call_args(self, messages: list[Any], tool_call_id: str, tool_name: str) -> CatalogingResult | None:
        """Find tool call arguments in AI message by tool_call_id.

        Used for resume workflows where tool message has string content.

        Args:
            messages: All messages
            tool_call_id: ID to match
            tool_name: Expected tool name

        Returns:
            CatalogingResult if found
        """
        from autifyme_agents.schemas.models import CatalogingResult

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

