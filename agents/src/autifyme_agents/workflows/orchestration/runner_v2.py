"""Generic HITL Framework - Truly Agentic Architecture.

Runner is a BLIND EXECUTOR with ZERO workflow knowledge.

## Core Principles

**1. Runner Has NO Knowledge Of:**
- What interrupts mean (approval, form, budget, etc.)
- What user responses mean ("go ahead", "change X", etc.)
- Workflow-specific logic
- How to interpret intent

**2. Specialist Has FULL Intelligence:**
- Sees full conversation context + pending interrupts
- Interprets ANY user phrasing
- Constructs exact Commands for resumption
- Decides intent freely (not limited to predefined literals)

**3. Generic HITL Works For:**
- Product approvals ✅
- Budget approvals ✅
- Multi-step wizards ✅
- File upload confirmations ✅
- Payment verifications ✅
- ANY future workflow ✅

## Architecture

```
User: "go ahead"
→ Runner: Forward raw message to PM
→ PM: Call MessageIntentSpecialist tool
→ Specialist: Analyze context + construct Command
→ Specialist: Return {intent: "resume_workflow", command: {interrupt_id, resume_value}}
→ Runner: Blindly execute Command(resume={interrupt_id: resume_value})
→ PM: Resume from interrupt
```

**No hardcoded patterns. No workflow assumptions. Fully generic.**
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
    """Blind executor - forwards messages and executes Commands from specialist.

    ## Runner Responsibilities (Blind Executor):
    - Accept raw platform messages
    - Forward to PM with thread management
    - Detect interrupts from PM stream
    - Forward interrupts to user via channel
    - Execute Commands specialist constructs
    - Relay final results

    ## Runner Has ZERO Knowledge Of:
    - What interrupts mean (approval, form, budget, wizard, etc.)
    - What user responses mean ("go ahead", "change price", "reject")
    - How to construct Commands (specialist does this)
    - Workflow-specific logic
    - Intent classification

    ## Delegated to MessageIntentSpecialist:
    - Message interpretation with full conversation context
    - Interrupt detection from history
    - Command construction for resumption
    - Intent classification (not limited to literals)
    - Media downloading via platform tools
    - Clarification composition

    ## Design Philosophy:
    Generic HITL framework that works for ANY workflow without Runner changes.
    Specialist has full intelligence. Runner blindly executes.
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
        logger.info("INITIALIZING GENERIC HITL FRAMEWORK (Blind Executor)")
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

        logger.info("Generic HITL Framework initialized - Runner is blind executor")
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
        """Execute workflow: interpret message, handle interrupts, resume if needed.

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

        raw_payload = {
            "platform": incoming_message.platform,
            "sender": sender,
            "text": text,
            "media_id": media_id,
            "timestamp": incoming_message.received_at.isoformat(),
        }

        try:
            result, interrupt_value = self._invoke_pm(thread_id, raw_payload)

            if interrupt_value:
                self._handle_interrupt(sender, thread_id, interrupt_value)
                duration = (datetime.now() - workflow_start_time).total_seconds()
                self.outcome_tracker.track_workflow_end(
                    thread_id=thread_id,
                    success=True,
                    result={"status": "pending_hitl", "tracking_id": tracking_id},
                )
                return

            if not result:
                return

            interpretation = self._extract_interpretation(result.get("messages", []))
            if interpretation:
                self._handle_interpretation(sender, thread_id, interpretation)
                return

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

            summary = self._extract_ai_summary(result.get("messages", []))
            if summary:
                self.channel.send_text(sender, summary)

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
        raw_payload: dict[str, Any] | None = None,
        command: Any | None = None,
    ) -> tuple[dict[str, Any] | None, Any | None]:
        """Invoke PM and detect interrupts.

        Args:
            thread_id: Conversation thread ID
            raw_payload: Raw platform message dict (for new messages)
            command: LangGraph Command (for resuming interrupts)

        Returns:
            Tuple of (final_result, interrupt_value) - at most one will be non-None
        """
        logger.debug("Invoking Project Manager", extra={"thread_id": thread_id})

        pm = self._create_project_manager()
        config = self._build_config(thread_id)

        # Build payload
        from langchain.messages import HumanMessage
        if command:
            # Resuming with Command
            payload = command
        elif raw_payload:
            # New message
            payload = {"messages": [HumanMessage(content=json.dumps(raw_payload))]}
        else:
            raise ValueError("Either raw_payload or command must be provided")

        last_event = None
        interrupt_value = None

        try:
            for event in pm.stream(payload, config=config, stream_mode="values"):
                last_event = event

                # Detect interrupt in stream (legacy pattern)
                if "__interrupt__" in event:
                    interrupts = event.get("__interrupt__") or []
                    if interrupts:
                        interrupt_value = interrupts[0].value
                        logger.info(
                            "Interrupt detected from department (in stream)",
                            extra={
                                "thread_id": thread_id,
                                "interrupt_count": len(interrupts),
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
            logger.info(
                "Interrupt detected from department (via exception)",
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
        logger.debug("Handling HITL interrupt", extra={"thread_id": thread_id})

        try:
            self.channel.send_hitl_request(sender, interrupt_value)
            logger.info(
                "Interrupt forwarded to user",
                extra={
                    "thread_id": thread_id,
                    "interrupt_type": type(interrupt_value).__name__,
                },
            )

        except Exception as exc:
            logger.exception("Failed to handle interrupt", exc_info=exc, extra={"thread_id": thread_id})
            self.channel.send_error(sender, "processing", "I encountered an issue requesting your input.")


    def _extract_interpretation(self, messages: list) -> dict[str, Any] | None:
        """Extract MessageInterpretation from PM's tool call result.

        Args:
            messages: PM output messages

        Returns:
            Interpretation dict if found, None otherwise
        """
        for message in messages:
            message_type = getattr(message, "type", None)
            if not message_type and hasattr(message, "__class__"):
                message_type = message.__class__.__name__.replace("Message", "").lower()

            if message_type == "tool":
                content = getattr(message, "content", None)
                if isinstance(content, dict) and content.get("tool_name") == "interpret_incoming_message":
                    result = content.get("result")
                    if isinstance(result, dict):
                        return result

        return None

    def _handle_workflow_resumption(
        self,
        sender: str,
        thread_id: str,
        interpretation: dict[str, Any],
    ) -> None:
        """Handle generic workflow resumption - execute Command specialist constructed.

        Fully generic - no workflow-specific logic. Specialist has already:
        - Analyzed interrupt context
        - Interpreted user's response
        - Constructed appropriate resume_value

        Runner just blindly executes the Command.

        Args:
            sender: Channel-specific sender ID
            thread_id: Conversation thread ID
            interpretation: MessageInterpretation with command field
        """
        logger.debug("Handling workflow resumption", extra={"thread_id": thread_id})

        try:
            command_spec = interpretation.get("command")
            if not command_spec:
                logger.error(
                    "resume_workflow intent without command spec",
                    extra={"thread_id": thread_id},
                )
                self.channel.send_error(sender, "processing", "I couldn't determine how to proceed.")
                return

            interrupt_id = command_spec.get("interrupt_id")
            resume_value = command_spec.get("resume_value")
            if not interrupt_id or not resume_value:
                logger.error(
                    "Invalid command spec from specialist",
                    extra={"thread_id": thread_id, "command_spec": command_spec},
                )
                self.channel.send_error(sender, "processing", "I couldn't determine how to proceed.")
                return

            from langgraph.types import Command

            command = Command(resume={interrupt_id: resume_value})
            logger.info(
                "Resuming workflow with specialist-constructed Command",
                extra={
                    "thread_id": thread_id,
                    "interrupt_id": interrupt_id,
                    "resume_type": resume_value.get("type", "unknown"),
                },
            )

            result, interrupt_value = self._invoke_pm(thread_id, command=command)
            if interrupt_value:
                logger.warning(
                    "Secondary interrupt during resumption",
                    extra={"thread_id": thread_id},
                )
                self.channel.send_error(sender, "processing", "Workflow needs attention before it can continue.")
                return

            if not result:
                logger.warning("No final event after resumption", extra={"thread_id": thread_id})
                self.channel.send_error(sender, "processing", "Workflow resumed but failed to complete.")
                return

            cataloging_result = self._extract_cataloging_result(result.get("messages", []))
            if cataloging_result:
                self.channel.send_completion(sender, cataloging_result)
                logger.info("Workflow resumed and completed", extra={"thread_id": thread_id})
                return

            summary = self._extract_ai_summary(result.get("messages", []))
            if summary:
                self.channel.send_text(sender, summary)
                return

            logger.warning("No result or response after resumption", extra={"thread_id": thread_id})
            self.channel.send_error(sender, "processing", "Workflow resumed but no result returned.")

        except Exception as exc:
            logger.exception("Failed to handle workflow resumption", exc_info=exc, extra={"thread_id": thread_id})
            self.channel.send_error(sender, "processing", "An error occurred while resuming the workflow.")

    def _handle_interpretation(
        self,
        sender: str,
        thread_id: str,
        interpretation: dict[str, Any],
    ) -> None:
        """Handle generic interpretation - execute Command specialist constructed.

        Fully generic - no workflow-specific logic. Specialist has already:
        - Analyzed interrupt context
        - Interpreted user's response
        - Constructed appropriate resume_value

        Runner just blindly executes the Command.

        Args:
            sender: Channel-specific sender ID
            thread_id: Conversation thread ID
            interpretation: MessageInterpretation with command field
        """
        logger.debug("Handling interpretation", extra={"thread_id": thread_id})

        try:
            command_spec = interpretation.get("command")
            if not command_spec:
                logger.error(
                    "interpret_incoming_message intent without command spec",
                    extra={"thread_id": thread_id},
                )
                self.channel.send_error(sender, "processing", "I couldn't determine how to proceed.")
                return

            interrupt_id = command_spec.get("interrupt_id")
            resume_value = command_spec.get("resume_value")
            if not interrupt_id or not resume_value:
                logger.error(
                    "Invalid command spec from specialist",
                    extra={"thread_id": thread_id, "command_spec": command_spec},
                )
                self.channel.send_error(sender, "processing", "I couldn't determine how to proceed.")
                return

            from langgraph.types import Command

            command = Command(resume={interrupt_id: resume_value})
            logger.info(
                "Resuming workflow with specialist-constructed Command",
                extra={
                    "thread_id": thread_id,
                    "interrupt_id": interrupt_id,
                    "resume_type": resume_value.get("type", "unknown"),
                },
            )

            result, interrupt_value = self._invoke_pm(thread_id, command=command)
            if interrupt_value:
                logger.warning(
                    "Secondary interrupt during resumption",
                    extra={"thread_id": thread_id},
                )
                self.channel.send_error(sender, "processing", "Workflow needs attention before it can continue.")
                return

            if not result:
                logger.warning("No final event after resumption", extra={"thread_id": thread_id})
                self.channel.send_error(sender, "processing", "Workflow resumed but failed to complete.")
                return

            cataloging_result = self._extract_cataloging_result(result.get("messages", []))
            if cataloging_result:
                self.channel.send_completion(sender, cataloging_result)
                logger.info("Workflow resumed and completed", extra={"thread_id": thread_id})
                return

            summary = self._extract_ai_summary(result.get("messages", []))
            if summary:
                self.channel.send_text(sender, summary)
                return

            logger.warning("No result or response after resumption", extra={"thread_id": thread_id})
            self.channel.send_error(sender, "processing", "Workflow resumed but no result returned.")

        except Exception as exc:
            logger.exception("Failed to handle interpretation", exc_info=exc, extra={"thread_id": thread_id})
            self.channel.send_error(sender, "processing", "An error occurred while resuming the workflow.")

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
            channel=self.channel,  # ✅ NEW: Pass channel for MessageIntentTool
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
            except ValueError:
                continue
            return tool_output.result

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
