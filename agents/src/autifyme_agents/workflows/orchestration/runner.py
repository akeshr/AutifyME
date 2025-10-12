"""Generic workflow orchestration runner.

Channel-agnostic workflow coordination for all messaging platforms.

Design: Uses native LangGraph interrupt handling - no custom coordinators needed.
Framework handles all checkpoint persistence, interrupt state, and recovery.
"""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.errors import GraphRecursionError
from langgraph.types import Command
from langchain.messages import HumanMessage

try:
    from openai import BadRequestError
except Exception:  # pragma: no cover - optional dependency
    BadRequestError = None  # type: ignore

from autifyme_agents.core.config import settings
from autifyme_agents.core.logging_config import get_logger
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from autifyme_agents.schemas.models import CompanyProfile, CatalogingResult, Product
from autifyme_agents.workflows.channels.protocol import MessagingChannel
from autifyme_agents.workflows.project_manager import create_project_manager
from autifyme_agents.workflows.outcome_tracker import OutcomeTracker, IncomingMessage

logger = get_logger(__name__)

# Constants
CATALOGING_PROMPT = "Please share the product details and photo so I can catalog it."
MAX_THREAD_LOCKS = 1000  # LRU cache size for thread locks


class WorkflowRunner:
    """Generic, channel-agnostic workflow orchestration with native LangGraph HITL.

    Responsibilities:
    - Accept user messages and coordinate processing
    - Invoke Project Manager
    - Stream events and detect interrupts (native LangGraph)
    - Send approval requests to user
    - Resume workflows after approval
    - Thread-safe handling of concurrent requests

    NOT responsible for:
    - Channel-specific logic (delegates to MessagingChannel)
    - Media handling (delegates to MessagingChannel)
    - Message formatting (delegates to MessagingChannel)
    - Interrupt state persistence (LangGraph checkpointer handles this)
    - Recovery logic (framework checkpoint consistency)

    Design Note: Massively simplified from original - removed 700+ lines of custom
    interrupt coordination. Framework handles all state management via checkpoints.
    """

    def __init__(
        self,
        *,
        channel: MessagingChannel,
        storage: StorageInterface,
        checkpointer: BaseCheckpointSaver | None = None,
        recursion_limit: int | None = None,
    ):
        """Initialize workflow runner with dependency injection.

        Args:
            channel: Messaging channel adapter (WhatsApp, SMS, etc.)
            storage: Storage adapter for company profile and products
            checkpointer: LangGraph checkpointer (creates default if None)
            recursion_limit: Max PM recursion depth
        """
        logger.info("=" * 80)
        logger.info("INITIALIZING WORKFLOW RUNNER (Native LangGraph HITL)")
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

        # Checkpointer management
        self._checkpointer = checkpointer

        # Thread safety: LRU lock manager per sender
        self._thread_locks: OrderedDict[str, Lock] = OrderedDict()
        self._locks_mutex = Lock()

        # In-memory pending approvals (ephemeral - survives during runtime only)
        # For persistence across restarts, extract from checkpoint on demand
        self._pending_approvals: dict[str, dict[str, Any]] = {}

        # Phase 1: Outcome tracking for agentic learning
        self.outcome_tracker = OutcomeTracker(storage)
        logger.info("OutcomeTracker initialized for agentic learning")

        logger.info("WorkflowRunner initialization complete (simplified architecture)")
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
        if not self._should_process(text, media_id is not None):
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
                # Get pending approval from memory
                pending = self._pending_approvals.get(thread_id)
                if not pending:
                    logger.warning(
                        "No pending approval found in memory",
                        extra={"thread_id": thread_id}
                    )
                    self.channel.send_text(
                        sender,
                        "No pending approval found. Please resend your product details."
                    )
                    return

                if decision == "reject":
                    logger.info("User rejected approval", extra={"thread_id": thread_id})
                    del self._pending_approvals[thread_id]
                    self.channel.send_text(
                        sender,
                        "Understood. The draft will remain unsaved. Let me know if you'd like updates or a retry.",
                    )
                    return

                # Get current checkpoint state to extract interrupt_id
                config = {"configurable": {"thread_id": thread_id}}
                checkpointer = self._get_checkpointer()
                state = checkpointer.get_tuple(config)

                if not state:
                    logger.error("No checkpoint found for thread", extra={"thread_id": thread_id})
                    self.channel.send_error(sender, "processing")
                    return

                # Extract interrupt info from checkpoint
                state_values = state.checkpoint.get("channel_values", {})
                interrupts = state_values.get("__interrupt__", [])

                if not interrupts:
                    logger.warning("No interrupts in checkpoint state", extra={"thread_id": thread_id})
                    self.channel.send_error(sender, "processing")
                    return

                interrupt_id = interrupts[0].id

                # Build Command to resume with accept payload
                # HumanInTheLoopMiddleware expects: {interrupt_id: {"type": "accept"}}
                command = Command(resume={interrupt_id: {"type": "accept"}})

                logger.debug(
                    "Resuming workflow with approval",
                    extra={"thread_id": thread_id, "interrupt_id": interrupt_id}
                )

                # Resume PM from checkpoint
                pm = self._create_project_manager()
                last_event = None

                try:
                    # Fully consume stream to avoid GeneratorExit
                    for event in pm.stream(command, config=config, stream_mode="values"):
                        last_event = event

                        # Check for nested interrupts
                        if "__interrupt__" in event:
                            logger.warning(
                                "Nested interrupt during resumption",
                                extra={"thread_id": thread_id}
                            )
                            # This shouldn't happen with save_product, but handle gracefully
                            self.channel.send_error(sender, "processing")
                            return

                except GeneratorExit:
                    logger.warning(
                        "GeneratorExit during approval resumption",
                        extra={"thread_id": thread_id}
                    )
                    # Try to extract result from what we got
                    if last_event:
                        result = self._extract_cataloging_result(last_event.get("messages", []))
                        if result:
                            self.channel.send_completion(sender, result)
                    del self._pending_approvals[thread_id]
                    return

                except BaseException as e:
                    logger.exception(
                        "Unexpected error during approval resumption",
                        extra={"thread_id": thread_id, "error_type": type(e).__name__}
                    )
                    self.channel.send_error(sender, "processing")
                    del self._pending_approvals[thread_id]
                    return

                # Extract result from final event
                if last_event:
                    result = self._extract_cataloging_result(last_event.get("messages", []))
                    if result:
                        logger.info(
                            "Workflow resumed successfully",
                            extra={"thread_id": thread_id, "has_result": result is not None}
                        )
                        self.channel.send_completion(sender, result)
                    else:
                        logger.warning("No result after resumption", extra={"thread_id": thread_id})
                        self.channel.send_error(sender, "processing")
                else:
                    logger.warning("No final event after resumption", extra={"thread_id": thread_id})
                    self.channel.send_error(sender, "processing")

                # Cleanup
                del self._pending_approvals[thread_id]

            except Exception as exc:
                logger.exception("Failed to handle approval", exc_info=exc)
                # Cleanup on error
                if thread_id in self._pending_approvals:
                    del self._pending_approvals[thread_id]
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

        # Phase 1: Track workflow start
        incoming_message = IncomingMessage(
            sender_id=sender,
            text=text,
            media_id=media_id,
            platform=self.channel.__class__.__name__.replace("Channel", "").lower(),
        )
        tracking_id = self.outcome_tracker.track_workflow_start(thread_id, incoming_message)
        workflow_start_time = datetime.now()

        # Abandonment detection: new media = fresh start (delete old checkpoint)
        if media_id and thread_id in self._pending_approvals:
            logger.info(
                "Abandonment detected - user sent new media while approval pending",
                extra={"thread_id": thread_id}
            )
            # Clear old workflow state
            del self._pending_approvals[thread_id]
            try:
                checkpointer = self._get_checkpointer()
                checkpointer.delete_thread(thread_id)
                logger.info("Cleared old checkpoint for fresh start", extra={"thread_id": thread_id})
            except Exception as e:
                logger.warning("Failed to clear checkpoint", exc_info=e, extra={"thread_id": thread_id})

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
            result, interrupt_value = self._invoke_pm(thread_id, text, media_path)

            if interrupt_value:
                # HITL approval required
                self._handle_interrupt(sender, thread_id, interrupt_value, media_path)
                # Track as pending approval (workflow continues after user input)
                duration = (datetime.now() - workflow_start_time).total_seconds()
                self.outcome_tracker.track_workflow_end(
                    thread_id=thread_id,
                    success=True,
                    result={"status": "pending_approval", "tracking_id": tracking_id},
                )
            elif result:
                # Direct completion without interrupt
                self._handle_completion(sender, result)
                duration = (datetime.now() - workflow_start_time).total_seconds()
                logger.info(
                    "Workflow completed successfully",
                    extra={
                        "thread_id": thread_id,
                        "duration_seconds": duration,
                        "sender": sender,
                    },
                )
                self.outcome_tracker.track_workflow_end(
                    thread_id=thread_id,
                    success=True,
                    result=result,
                )

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
            if isinstance(exc, BadRequestError):
                error_text = str(exc)
                logger.error(
                    "PM invocation failed due to tool-call mismatch",
                    extra={
                        "thread_id": thread_id,
                        "error": error_text,
                        "has_tool_call_violation": "tool_call" in error_text,
                    },
                )
                print("\n=== OpenAI BadRequestError Details ===")
                print(f"Error type: {type(exc).__name__}")
                print(f"Error message: {error_text}")
                if hasattr(exc, 'response'):
                    print(f"Response body: {exc.response.text if hasattr(exc.response, 'text') else 'N/A'}")
                print("======================================\n")
                self.channel.send_error(
                    sender,
                    "processing",
                    "I hit a coordination error while prepping your request. Please resend the details so I can try again.",
                )
            else:
                logger.exception("PM invocation failed", exc_info=exc, extra={"thread_id": thread_id})
                self.channel.send_error(sender, "processing")

            self.outcome_tracker.track_workflow_end(
                thread_id=thread_id,
                success=False,
                error=exc,
                resolution_strategy="user_notified",
            )

        finally:
            # Media persists in media_downloads/ for debugging/auditing
            pass

    def _invoke_pm(
        self,
        thread_id: str,
        text: str | None,
        media_path: Path | None,
    ) -> tuple[dict[str, Any] | None, Any | None]:
        """Invoke PM and detect interrupts using native LangGraph patterns.

        Args:
            thread_id: Conversation thread ID
            text: Message text (optional)
            media_path: Downloaded media file path (optional)

        Returns:
            Tuple of (final_result, interrupt_value) - exactly one will be non-None
        """
        logger.debug("Invoking Project Manager", extra={"thread_id": thread_id})

        pm = self._create_project_manager()
        payload = self._build_payload(text, media_path)
        config = self._build_config(thread_id)

        last_event = None
        interrupt_value = None

        try:
            # Fully consume the stream to avoid GeneratorExit
            for event in pm.stream(payload, config=config, stream_mode="values"):
                last_event = event

                # Detect native LangGraph interrupt
                if "__interrupt__" in event:
                    interrupts = event.get("__interrupt__") or []
                    if interrupts:
                        # Extract interrupt value from first interrupt
                        interrupt_value = interrupts[0].value
                        logger.info(
                            "Native LangGraph interrupt detected",
                            extra={
                                "thread_id": thread_id,
                                "interrupt_count": len(interrupts),
                            },
                        )
                        # Continue consuming to avoid GeneratorExit

            logger.debug(
                "PM stream fully consumed",
                extra={
                    "thread_id": thread_id,
                    "had_interrupt": interrupt_value is not None,
                },
            )

        except GeneratorExit:
            # GeneratorExit in serverless - workflow continues via checkpoint
            logger.warning(
                "GeneratorExit during workflow streaming",
                extra={"thread_id": thread_id},
            )
            return last_event, interrupt_value

        except BaseException as e:
            logger.exception(
                "Unexpected BaseException during workflow streaming",
                extra={"thread_id": thread_id, "error_type": type(e).__name__},
            )
            raise

        return last_event, interrupt_value

    def _handle_interrupt(
        self,
        sender: str,
        thread_id: str,
        interrupt_value: Any,
        media_path: Path | None,
    ) -> None:
        """Handle HITL interrupt - extract draft and send approval request.

        Args:
            sender: Channel-specific sender ID
            thread_id: Conversation thread ID
            interrupt_value: Value from LangGraph interrupt (emitted by HumanInTheLoopMiddleware)
            media_path: Optional media file to preserve
        """
        logger.debug("Handling interrupt", extra={"thread_id": thread_id})

        try:
            # Extract draft from interrupt value
            # HumanInTheLoopMiddleware format: list of dicts with "action_request"
            draft = self._parse_interrupt_draft(interrupt_value)

            if not draft:
                logger.error("Failed to parse draft from interrupt", extra={"thread_id": thread_id})
                self.channel.send_error(
                    sender,
                    "processing",
                    "I encountered an issue preparing your product for approval. Please try again."
                )
                return

            # Store in memory for approval handling
            self._pending_approvals[thread_id] = {
                "draft": draft,
                "media_path": str(media_path) if media_path else None,
                "timestamp": datetime.now(),
            }

            logger.info(
                "Pending approval stored",
                extra={"thread_id": thread_id, "product_name": draft.name}
            )

            # Send approval request via channel
            self.channel.send_approval_request(sender, draft)

        except Exception as exc:
            logger.exception("Failed to handle interrupt", exc_info=exc, extra={"thread_id": thread_id})
            self.channel.send_error(
                sender,
                "processing",
                "I encountered an unexpected issue. Please try resending your product details.",
            )

    def _parse_interrupt_draft(self, interrupt_value: Any) -> Product | None:
        """Parse Product draft from interrupt value.

        Args:
            interrupt_value: Value from interrupt (format varies by middleware)

        Returns:
            Product instance if parsed successfully, None otherwise
        """
        try:
            # HumanInTheLoopMiddleware format: list of action requests
            if isinstance(interrupt_value, list):
                for item in interrupt_value:
                    if isinstance(item, dict) and "action_request" in item:
                        action_request = item["action_request"]
                        if action_request.get("action") == "save_product":
                            args = action_request.get("args", {})
                            return Product(
                                name=args.get("name", "Unnamed Product"),
                                description=args.get("description"),
                                price=args.get("price"),
                                sizes=args.get("sizes"),
                                colors=args.get("colors"),
                                image_urls=args.get("image_urls"),
                            )

            # Fallback: try direct tool call format
            if isinstance(interrupt_value, dict):
                args = interrupt_value.get("args", {})
                if args:
                    return Product(
                        name=args.get("name", "Unnamed Product"),
                        description=args.get("description"),
                        price=args.get("price"),
                        sizes=args.get("sizes"),
                        colors=args.get("colors"),
                        image_urls=args.get("image_urls"),
                    )

            logger.warning(
                "Unknown interrupt value format",
                extra={"interrupt_type": type(interrupt_value).__name__}
            )
            return None

        except Exception as e:
            logger.exception("Failed to parse interrupt draft", exc_info=e)
            return None

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
        """Build semantic PM payload using IncomingMessage schema.

        Args:
            text: Message text (optional)
            media_path: Downloaded media file path (optional)

        Returns:
            PM input payload with semantic message description
        """
        from autifyme_agents.schemas.messages import IncomingMessage, MediaReference

        # Build MediaReference if media present
        media_refs = []
        if media_path and media_path.exists():
            media_ref = MediaReference(
                media_id=media_path.name,
                media_type="image",
                mime_type="image/jpeg",
                platform="whatsapp",
                download_strategy="none",
                local_path=media_path,
                platform_url=None,
                size_bytes=None,
                caption=None,
                filename=media_path.name,
                expires_at=None,
            )
            media_refs.append(media_ref)

        # Create canonical IncomingMessage
        incoming_msg = IncomingMessage(
            text=text,
            media=media_refs,
            platform=self.channel.__class__.__name__.replace("Channel", "").lower(),
            sender_id="placeholder",
            thread_id="placeholder",
            timestamp=datetime.now(),
            reply_to_message_id=None,
            forwarded_from=None,
            conversation_history=None,
        )

        # Use canonical to_semantic_description() method
        content = incoming_msg.to_semantic_description()

        messages = [HumanMessage(content=content)]
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
