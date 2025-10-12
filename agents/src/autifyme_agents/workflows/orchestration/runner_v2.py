"""Generic HITL Framework - Simplified Checkpoint-Based Architecture.

Runner is a BLIND EXECUTOR - forwards messages to PM, which handles checkpoint state naturally.

## CRITICAL FIX: Subgraph Interrupt Handling

**Problem**: Manual Command construction caused message sequence errors with OpenAI API.
**Solution**: Let LangGraph's checkpoint flow handle resumption automatically.

## How It Works Now

1. User sends message → Runner forwards to PM
2. PM processes with checkpoint context (sees pending interrupts automatically)
3. If interrupt occurs → Runner sends to user via channel
4. User responds → Runner forwards to PM (NO Command construction)
5. PM sees checkpoint state and resumes naturally
6. LangGraph handles message sequence synthesis correctly

**Benefits**:
- No manual Command construction
- No checkpoint namespace handling needed
- No message sequence validation errors
- Truly generic for ANY workflow
"""

from __future__ import annotations

import json
import logging
from collections import OrderedDict
from datetime import datetime
from threading import Lock
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.errors import GraphRecursionError, GraphInterrupt

from autifyme_agents.core.config import settings
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from autifyme_agents.schemas.models import CompanyProfile, CatalogingResult
from autifyme_agents.workflows.channels.protocol import MessagingChannel
from autifyme_agents.workflows.project_manager import create_project_manager
from autifyme_agents.workflows.outcome_tracker import OutcomeTracker, IncomingMessage

logger = logging.getLogger(__name__)

# Constants
MAX_THREAD_LOCKS = 1000  # LRU cache size for thread locks


class WorkflowRunner:
    """Blind executor - forwards messages and lets PM + checkpoints handle state.

    ## SIMPLIFIED ARCHITECTURE (Post-Fix):
    
    Runner responsibilities:
    - Forward raw messages to PM
    - Detect interrupts from stream
    - Send interrupts to user via channel
    - Forward user responses back to PM
    
    PM + LangGraph handles:
    - Checkpoint state management
    - Interrupt resumption logic
    - Message sequence synthesis
    - Command construction (if needed)
    
    ## NO MORE:
    - Manual Command construction
    - Interrupt ID extraction
    - Checkpoint namespace handling
    - Resume value creation
    
    PM sees checkpoint context and handles everything naturally.
    """

    def __init__(
        self,
        *,
        channel: MessagingChannel,
        storage: StorageInterface,
        checkpointer: BaseCheckpointSaver | None = None,
        recursion_limit: int | None = None,
    ):
        """Initialize workflow runner.

        Args:
            channel: Messaging channel adapter (WhatsApp, Telegram, etc.)
            storage: Storage adapter for company profile and products
            checkpointer: LangGraph checkpointer (creates default if None)
            recursion_limit: Max PM recursion depth
        """
        logger.info("=" * 80)
        logger.info("INITIALIZING GENERIC HITL FRAMEWORK (Simplified Checkpoint Flow)")
        logger.info("=" * 80)

        self.channel = channel
        self.storage = storage
        self.recursion_limit = recursion_limit or settings.AGENT_RECURSION_LIMIT

        logger.debug(
            "Runner configuration",
            extra={
                "channel": channel.__class__.__name__,
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

        logger.info("Generic HITL Framework initialized - simplified architecture")
        logger.info("=" * 80)

    def handle_message(
        self,
        sender: str,
        text: str | None,
        media_id: str | None,
    ) -> None:
        """Process incoming message by forwarding to PM.

        Args:
            sender: Channel-specific sender ID (e.g., phone number)
            text: Message text (optional)
            media_id: Media attachment ID (optional, channel-specific)
        """
        logger.info(
            "Handling incoming message",
            extra={
                "sender": sender,
                "has_text": text is not None,
                "has_media": media_id is not None,
            },
        )

        # Thread safety - serialize per sender
        thread_id = self.channel.format_thread_id(sender)
        lock = self._get_lock(sender)

        with lock:
            self._execute_workflow(thread_id, sender, text, media_id)

    def _execute_workflow(
        self,
        thread_id: str,
        sender: str,
        text: str | None,
        media_id: str | None,
    ) -> None:
        """Execute workflow: forward message to PM, handle any interrupts.

        ✅ SIMPLIFIED: No Command construction, PM handles checkpoint state.

        Args:
            thread_id: Conversation thread ID
            sender: Channel-specific sender ID
            text: Message text (optional)
            media_id: Media attachment ID (optional)
        """
        logger.debug(
            "Executing workflow",
            extra={"thread_id": thread_id, "has_text": text is not None, "has_media": media_id is not None},
        )

        workflow_start_time = datetime.now()

        incoming_message = IncomingMessage(
            sender_id=sender,
            text=text,
            media_id=media_id,
            platform=self.channel.__class__.__name__.replace("Channel", "").lower(),
        )
        tracking_id = self.outcome_tracker.track_workflow_start(thread_id, incoming_message)

        # Build raw payload for PM
        raw_payload = {
            "platform": incoming_message.platform,
            "sender": sender,
            "text": text,
            "media_id": media_id,
            "timestamp": incoming_message.received_at.isoformat(),
        }

        try:
            # ✅ ALWAYS invoke PM with new message - it handles checkpoint state
            result, interrupt_value = self._invoke_pm(thread_id, raw_payload)

            if interrupt_value:
                # Department is requesting HITL - forward to user
                self._handle_interrupt(sender, thread_id, interrupt_value)
                duration = (datetime.now() - workflow_start_time).total_seconds()
                self.outcome_tracker.track_workflow_end(
                    thread_id=thread_id,
                    success=True,
                    result={"status": "pending_hitl", "tracking_id": tracking_id},
                )
                return

            if not result:
                logger.warning("PM returned no result", extra={"thread_id": thread_id})
                return

            # Check for workflow completion
            cataloging_result = self._extract_cataloging_result(result.get("messages", []))
            if cataloging_result:
                self.channel.send_completion(sender, cataloging_result)
                duration = (datetime.now() - workflow_start_time).total_seconds()
                logger.info(
                    "Workflow completed successfully",
                    extra={"thread_id": thread_id, "duration_seconds": duration},
                )
                self.outcome_tracker.track_workflow_end(
                    thread_id=thread_id,
                    success=True,
                    result=cataloging_result.model_dump(),
                )
                return

            # Fallback: send AI summary if available
            summary = self._extract_ai_summary(result.get("messages", []))
            if summary:
                self.channel.send_text(sender, summary)
            else:
                logger.warning("No result or summary from PM", extra={"thread_id": thread_id})

        except GraphRecursionError as exc:
            logger.exception("PM recursion limit exceeded", exc_info=exc, extra={"thread_id": thread_id})
            self.channel.send_error(sender, "recursion")
            self.outcome_tracker.track_workflow_end(
                thread_id=thread_id,
                success=False,
                error=exc,
                resolution_strategy="user_notified",
            )

        except Exception as exc:
            logger.exception("PM invocation failed", exc_info=exc, extra={"thread_id": thread_id})
            self.channel.send_error(sender, "processing")
            self.outcome_tracker.track_workflow_end(
                thread_id=thread_id,
                success=False,
                error=exc,
                resolution_strategy="user_notified",
            )

    def _invoke_pm(
        self,
        thread_id: str,
        raw_payload: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, Any | None]:
        """Invoke PM with raw message payload.

        ✅ SIMPLIFIED: No Command support needed - PM handles checkpoint state.

        Args:
            thread_id: Conversation thread ID
            raw_payload: Raw platform message dict

        Returns:
            Tuple of (final_result, interrupt_value) - at most one will be non-None
        """
        logger.debug("Invoking Project Manager", extra={"thread_id": thread_id})

        pm = self._create_project_manager()
        config = self._build_config(thread_id)

        # Build message payload
        from langchain.messages import HumanMessage
        payload = {"messages": [HumanMessage(content=json.dumps(raw_payload))]}

        last_event = None
        interrupt_value = None

        try:
            for event in pm.stream(payload, config=config, stream_mode="values"):
                last_event = event

                # Detect interrupt in stream (from subgraph or PM)
                if "__interrupt__" in event:
                    interrupts = event.get("__interrupt__") or []
                    if interrupts:
                        interrupt_value = interrupts[0].value
                        logger.info(
                            "Interrupt detected",
                            extra={
                                "thread_id": thread_id,
                                "interrupt_count": len(interrupts),
                                "has_checkpoint_ns": hasattr(interrupts[0], 'checkpoint_ns'),
                            },
                        )

            logger.debug(
                "PM stream completed",
                extra={
                    "thread_id": thread_id,
                    "had_interrupt": interrupt_value is not None,
                },
            )

            return last_event, interrupt_value

        except GraphInterrupt as interrupt_exc:
            # Alternative interrupt detection via exception
            logger.info(
                "Interrupt detected via exception",
                extra={
                    "thread_id": thread_id,
                    "interrupt_count": len(interrupt_exc.interrupts),
                },
            )
            if interrupt_exc.interrupts:
                return last_event, interrupt_exc.interrupts[0].value
            return last_event, None

        except Exception as e:
            logger.exception(
                "PM streaming error",
                extra={"thread_id": thread_id, "error_type": type(e).__name__},
            )
            raise

    def _handle_interrupt(
        self,
        sender: str,
        thread_id: str,
        interrupt_value: Any,
    ) -> None:
        """Forward interrupt to user via channel.

        ✅ SIMPLIFIED: Just send to user - PM handles resumption when they respond.

        Args:
            sender: Channel-specific sender ID
            thread_id: Conversation thread ID
            interrupt_value: Value from interrupt (Product draft, form, etc.)
        """
        logger.debug("Handling HITL interrupt", extra={"thread_id": thread_id})

        try:
            self.channel.send_hitl_request(sender, interrupt_value)
            logger.info(
                "Interrupt forwarded to user - awaiting response",
                extra={
                    "thread_id": thread_id,
                    "interrupt_type": type(interrupt_value).__name__,
                },
            )

        except Exception as exc:
            logger.exception("Failed to send interrupt to user", exc_info=exc, extra={"thread_id": thread_id})
            self.channel.send_error(sender, "processing", "I encountered an issue requesting your input.")

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

    def _get_checkpointer(self) -> BaseCheckpointSaver:
        """Get checkpointer instance."""
        if self._checkpointer:
            return self._checkpointer
        return get_checkpointer()

    def _create_project_manager(self):
        """Create PM instance with company context and channel."""
        return create_project_manager(
            company_profile=self.company_profile,
            checkpointer=self._get_checkpointer(),
            storage=self.storage,
            channel=self.channel,
        )

    def _build_config(self, thread_id: str) -> dict[str, Any]:
        """Build PM config.

        Args:
            thread_id: Conversation thread ID

        Returns:
            PM config dict
        """
        return {
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

    def _extract_cataloging_result(self, messages: list) -> CatalogingResult | None:
        """Extract CatalogingResult from messages.

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
            if not isinstance(content, dict):
                continue
            if content.get("tool_name") != "save_product":
                continue

            try:
                from autifyme_agents.schemas.agent_outputs import CatalogingToolOutput

                tool_output = CatalogingToolOutput.model_validate(content)
                return tool_output.result
            except ValueError:
                continue

        return None

    def _extract_ai_summary(self, messages: list) -> str | None:
        """Extract AI summary from messages.

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