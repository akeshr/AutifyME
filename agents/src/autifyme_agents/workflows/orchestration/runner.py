"""Generic workflow orchestration runner.

Channel-agnostic workflow coordination for all messaging platforms.

Design Principle: Strategy Pattern - channel behavior injected via MessagingChannel.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from threading import Lock
from typing import Any, Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.errors import GraphRecursionError
from langgraph.types import Interrupt
from langchain_core.messages import HumanMessage

try:
    from openai import BadRequestError
except Exception:  # pragma: no cover - optional dependency
    BadRequestError = None  # type: ignore

from autifyme_agents.core.config import settings
from autifyme_agents.core.logging_config import get_logger
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from autifyme_agents.schemas.models import CompanyProfile, CatalogingResult
from autifyme_agents.workflows.channels.protocol import MessagingChannel
from autifyme_agents.workflows.orchestration.interrupt_coordinator import InterruptCoordinator
from autifyme_agents.workflows.orchestration.state_manager import StateManager
from autifyme_agents.workflows.orchestration.recovery_strategy import RecoveryStrategy
from autifyme_agents.workflows.project_manager import create_project_manager

logger = get_logger(__name__)

# Constants
CATALOGING_PROMPT = "Please share the product details and photo so I can catalog it."
MAX_THREAD_LOCKS = 1000  # LRU cache size for thread locks


class WorkflowRunner:
    """Generic, channel-agnostic workflow orchestration.

    Responsibilities:
    - Accept user messages and coordinate processing
    - Invoke Project Manager
    - Stream events and detect interrupts
    - Delegate to specialized coordinators
    - Thread-safe handling of concurrent requests

    NOT responsible for:
    - Channel-specific logic (delegates to MessagingChannel)
    - Media handling (delegates to MessagingChannel)
    - Message formatting (delegates to MessagingChannel)
    - Interrupt logic (delegates to InterruptCoordinator)
    - State persistence (delegates to StateManager)
    - Recovery logic (delegates to RecoveryStrategy)

    Design Note: This is the orchestration layer - clean business logic
    with no channel-specific code. All channel operations go through
    self.channel (Strategy Pattern).
    """

    def __init__(
        self,
        *,
        channel: MessagingChannel,
        storage: StorageInterface,
        interrupt_coordinator: InterruptCoordinator | None = None,
        state_manager: StateManager | None = None,
        recovery_strategy: RecoveryStrategy | None = None,
        checkpointer: BaseCheckpointSaver | None = None,
        recursion_limit: int | None = None,
    ):
        """Initialize workflow runner with dependency injection.

        Args:
            channel: Messaging channel adapter (WhatsApp, SMS, etc.)
            storage: Storage adapter for company profile and products
            interrupt_coordinator: HITL interrupt handler (creates default if None)
            state_manager: Approval state manager (creates default if None)
            recovery_strategy: Error recovery logic (creates default if None)
            checkpointer: LangGraph checkpointer (creates default if None)
            recursion_limit: Max PM recursion depth
        """
        logger.info("=" * 80)
        logger.info("INITIALIZING WORKFLOW RUNNER")
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
            extra={
                "company_name": self.company_profile.name,
                "target_audience": self.company_profile.target_audience[:50]
                if self.company_profile.target_audience
                else "N/A",
            },
        )

        # Initialize coordinators (allow injection for testing)
        self.state = state_manager or StateManager(storage)
        self.recovery = recovery_strategy or RecoveryStrategy(
            state_manager=self.state,
            checkpointer_factory=lambda: self._get_checkpointer(),
        )
        self.interrupt_coord = interrupt_coordinator or InterruptCoordinator(
            state_manager=self.state,
        )

        # Checkpointer management
        self._checkpointer = checkpointer

        # Thread safety: LRU lock manager per sender
        self._thread_locks: OrderedDict[str, Lock] = OrderedDict()
        self._locks_mutex = Lock()

        # PM state tracking
        self._last_pm_state: dict[str, Any] | None = None

        logger.info("WorkflowRunner initialization complete")
        logger.info("=" * 80)

    def handle_message(
        self,
        sender: str,
        text: str | None,
        media_id: str | None,
    ) -> None:
        """Process incoming message from any channel.

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

        # Gate check - skip low-intent messages
        if not self._should_process(text, media_id):
            logger.info(
                "Skipping low-intent message",
                extra={"sender": sender, "text": text},
            )
            self.channel.send_text(sender, CATALOGING_PROMPT)
            return

        # Thread safety - serialize per sender
        thread_id = self.channel.format_thread_id(sender)
        lock = self._get_lock(sender)

        with lock:
            self._execute_workflow(thread_id, sender, text, media_id)

    def handle_approval(
        self,
        sender: str,
        decision: Literal["approve", "reject"],
    ) -> None:
        """Process approval/rejection from user.

        Args:
            sender: Channel-specific sender ID
            decision: User's decision
        """
        logger.info(
            "Handling approval decision",
            extra={"sender": sender, "decision": decision},
        )

        thread_id = self.channel.format_thread_id(sender)
        lock = self._get_lock(sender)

        with lock:
            try:
                result = self.interrupt_coord.resume_workflow(
                    thread_id=thread_id,
                    decision=decision,
                    pm_factory=lambda: self._create_project_manager(),
                )

                if result:
                    self.channel.send_completion(sender, result)
                else:
                    # Rejection - send friendly message
                    self.channel.send_text(
                        sender,
                        "Understood. The draft will remain unsaved. Let me know if you'd like updates or a retry.",
                    )

                # Cleanup media if it was stored
                approval = self.state.get_pending_approval(thread_id)
                if approval and approval.get("image_path"):
                    self._cleanup_media(Path(approval["image_path"]))

            except Exception as exc:
                logger.exception("Failed to handle approval", exc_info=exc)
                self.channel.send_error(sender, "processing")

    def _execute_workflow(
        self,
        thread_id: str,
        sender: str,
        text: str | None,
        media_id: str | None,
    ) -> None:
        """Core workflow execution (clean business logic).

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

        # Check for abandonment (new request while approval pending)
        if self.recovery.should_clear_state(thread_id, bool(media_id)):
            logger.info("Abandonment detected - clearing orphaned state", extra={"thread_id": thread_id})
            self.recovery.clear_orphaned_state(thread_id)

        # Download media if present
        media_path = None
        if media_id:
            try:
                media_path = self.channel.download_media(media_id)
            except Exception as exc:
                logger.exception("Media download failed", exc_info=exc, extra={"thread_id": thread_id})
                self.channel.send_error(sender, "media_download")
                return

        # Invoke PM
        try:
            result, interrupt = self._invoke_pm(thread_id, text, media_path)

            if interrupt:
                self._handle_interrupt(sender, thread_id, interrupt, media_path)
            elif result:
                self._handle_completion(sender, result)

        except ValueError as exc:
            # Reactive recovery for orphaned state
            if "INVALID_CHAT_HISTORY" in str(exc) or "do not have a corresponding ToolMessage" in str(exc):
                logger.warning(
                    "Detected orphaned tool calls - auto-recovery triggered",
                    extra={"thread_id": thread_id, "error": str(exc)[:200]},
                )
                self.recovery.auto_recover(thread_id)

                # Retry once
                result, interrupt = self._invoke_pm(thread_id, text, media_path)
                if interrupt:
                    self._handle_interrupt(sender, thread_id, interrupt, media_path)
                elif result:
                    self._handle_completion(sender, result)
            else:
                raise

        except GraphRecursionError as exc:
            logger.exception("PM recursion limit exceeded", exc_info=exc, extra={"thread_id": thread_id})
            self.channel.send_error(sender, "recursion")

        except Exception as exc:
            if BadRequestError and isinstance(exc, BadRequestError):
                error_text = str(exc)
                logger.error(
                    "PM invocation failed due to tool-call mismatch",
                    extra={
                        "thread_id": thread_id,
                        "error": error_text,
                        "has_tool_call_violation": "tool_call" in error_text,
                    },
                )
                self.channel.send_error(
                    sender,
                    "processing",
                    "I hit a coordination error while prepping your request. Please resend the details so I can try again.",
                )
            else:
                logger.exception("PM invocation failed", exc_info=exc, extra={"thread_id": thread_id})
                self.channel.send_error(sender, "processing")

        finally:
            # Cleanup media unless approval pending
            if media_path and not self.state.has_pending_approval(thread_id):
                self._cleanup_media(media_path)

    def _invoke_pm(
        self,
        thread_id: str,
        text: str | None,
        media_path: Path | None,
    ) -> tuple[dict[str, Any] | None, Interrupt | None]:
        """Invoke PM and detect interrupts.

        Args:
            thread_id: Conversation thread ID
            text: Message text (optional)
            media_path: Downloaded media file path (optional)

        Returns:
            Tuple of (final_result, interrupt) - exactly one will be non-None
        """
        logger.debug("Invoking Project Manager", extra={"thread_id": thread_id})

        pm = self._create_project_manager()

        payload = self._build_payload(text, media_path)
        config = self._build_config(thread_id)

        last_event = None
        interrupt = None

        for event in pm.stream(payload, config=config, stream_mode="values"):
            last_event = event

            # Track PM state for interrupt handling
            if isinstance(event, dict) and event.get("messages"):
                self._last_pm_state = event

            # Detect native LangGraph interrupt
            if "__interrupt__" in event:
                interrupts = event.get("__interrupt__") or []
                if interrupts:
                    interrupt = interrupts[0]
                    logger.info(
                        "Native LangGraph interrupt detected",
                        extra={
                            "thread_id": thread_id,
                            "interrupt_count": len(interrupts),
                        },
                    )
                    break

        return last_event, interrupt

    def _handle_interrupt(
        self,
        sender: str,
        thread_id: str,
        interrupt: Interrupt,
        media_path: Path | None,
    ) -> None:
        """Delegate interrupt handling to coordinator.

        Args:
            sender: Channel-specific sender ID
            thread_id: Conversation thread ID
            interrupt: LangGraph interrupt object
            media_path: Optional media file to preserve
        """
        logger.debug("Handling interrupt", extra={"thread_id": thread_id})

        try:
            approval_request = self.interrupt_coord.process_interrupt(
                interrupt=interrupt,
                thread_id=thread_id,
                pm_state=self._last_pm_state,
                media_path=media_path,
            )

            # Send approval request via channel
            self.channel.send_approval_request(sender, approval_request.draft)

        except Exception as exc:
            logger.exception("Failed to handle interrupt", exc_info=exc, extra={"thread_id": thread_id})

            # Critical: clear checkpoint to prevent stuck state
            try:
                self.recovery.clear_orphaned_state(thread_id)
            except Exception as clear_exc:
                logger.exception("Failed to clear checkpoint after interrupt error", exc_info=clear_exc)

            self.channel.send_error(
                sender,
                "processing",
                "I encountered an unexpected issue. Please try resending your product details.",
            )

    def _handle_completion(self, sender: str, result: dict[str, Any]) -> None:
        """Handle PM completion without interrupt.

        Args:
            sender: Channel-specific sender ID
            result: Final PM result
        """
        logger.debug("Handling workflow completion", extra={"sender": sender})

        if not result:
            logger.warning("PM returned empty result", extra={"sender": sender})
            return

        messages = result.get("messages") or []
        if not messages:
            logger.warning("PM produced no messages", extra={"sender": sender})
            return

        # Try to extract structured result
        cataloging_result = self._extract_cataloging_result(messages)
        if cataloging_result:
            self.channel.send_completion(sender, cataloging_result)
            return

        # Fallback: extract AI summary
        summary = self._extract_ai_summary(messages)
        if summary:
            self.channel.send_text(sender, summary)
        else:
            logger.warning("Unable to derive completion summary", extra={"sender": sender})

    def _should_process(self, text: str | None, has_media: bool) -> bool:
        """Gate to avoid invoking PM on greetings/empty messages.

        Args:
            text: Message text (optional)
            has_media: Whether message includes media

        Returns:
            True if should process, False if should skip
        """
        if has_media:
            return True

        normalized = (text or "").strip().lower()
        if not normalized:
            return False

        # Skip common greetings
        return normalized not in {"hi", "hello", "hey", "thanks", "thank you"}

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
        """Create PM instance with company context."""
        return create_project_manager(
            company_profile=self.company_profile,
            checkpointer=self._get_checkpointer(),
            storage=self.storage,
        )

    def _build_payload(self, text: str | None, media_path: Path | None) -> dict[str, Any]:
        """Build PM payload from message.

        Args:
            text: Message text (optional)
            media_path: Downloaded media file path (optional)

        Returns:
            PM input payload
        """
        messages = []

        if media_path and media_path.exists():
            if text and text.strip():
                content = f"{text}\n\n[An image was provided - analyze it using the image_analysis_specialist tool with path: {media_path}]"
            else:
                content = f"[An image was provided - analyze it using the image_analysis_specialist tool with path: {media_path}]"
            messages.append(HumanMessage(content=content))
        elif text and text.strip():
            messages.append(HumanMessage(content=text))
        else:
            messages.append(HumanMessage(content="Please provide product details."))

        return {"messages": messages}

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
        from autifyme_agents.schemas.agent_outputs import CatalogingToolOutput

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

    def _cleanup_media(self, media_path: Path) -> None:
        """Cleanup temporary media file.

        Args:
            media_path: Path to media file
        """
        try:
            if media_path.exists():
                media_path.unlink(missing_ok=True)
                logger.debug("Cleaned up temp media", extra={"path": str(media_path)})
        except Exception as exc:
            logger.warning("Failed to clean up temp media", extra={"path": str(media_path)}, exc_info=exc)
