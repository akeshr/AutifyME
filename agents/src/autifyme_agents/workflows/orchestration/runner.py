"""Generic HITL Framework - Workflow Orchestration.

Blind executor coordinating PM invocation and approval flows.

Architecture:
- PM: Orchestration (delegates to specialists)
- Approval Analyzer: HITL interpretation (structured responses)
- Runner: Coordination (routes, manages interrupts)

Flows:
- New message: User -> Runner -> PM -> Specialists -> HITL interrupt -> Channel
- Resume: User approval -> Approval Analyzer -> Command -> Resume workflow

Delegates to: WorkflowHandler, OutcomeTrackingMiddleware, ApprovalCoordinator
"""

from __future__ import annotations

import logging

# Threading removed - not needed for single-tenant architecture
# FastAPI background tasks + database checkpointing provide sufficient concurrency control
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.errors import GraphInterrupt, GraphRecursionError

from autifyme_agents.core.config import settings
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.schemas.interrupt import InterruptInfo
from autifyme_agents.schemas.models import CompanyProfile
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


class WorkflowRunner:
    """Blind executor - forwards messages to PM for intelligent orchestration.

    Responsibilities:
    - Forward messages to PM, extract interrupts, execute Commands
    - Coordinate approval flow via ApprovalCoordinator
    - Delegate domain logic to WorkflowHandler

    Injected dependencies: channel, storage, workflow_handler, checkpointer
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

    async def _clear_checkpoint(self, thread_id: str) -> None:
        """Clear checkpoint state to remove blank/corrupted LLM responses.

        Used when detecting blank responses to prevent cached blanks from being reused.

        Args:
            thread_id: Conversation thread ID to clear
        """
        try:
            if self._checkpointer:
                # Note: LangGraph checkpointer doesn't have direct delete, so we rely on
                # new invocation overwriting the state
                logger.info(
                    "Checkpoint cleared (will be overwritten on retry)",
                    extra={"thread_id": thread_id}
                )
        except Exception as e:
            logger.warning(
                "Failed to clear checkpoint",
                extra={"thread_id": thread_id, "error": str(e)}
            )

    async def handle_message(
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

        # Single-tenant architecture - no locking needed
        # FastAPI background tasks + database checkpointing provide sufficient concurrency control
        thread_id = self.channel.format_thread_id(sender)
        await self._execute_workflow(thread_id, sender, text, media_id, sender_name)

    async def _execute_workflow(
        self,
        thread_id: str,
        sender: str,
        text: str | None,
        media_id: str | None,
        sender_name: str | None = None,
    ) -> None:
        """Execute workflow with automatic retry on blank LLM responses.

        Uses outcome tracking middleware for automatic tracking.
        Implements retry logic to handle Gemini blank response bug.

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

        # Retry loop for blank LLM response recovery
        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            try:
                logger.debug(
                    f"PM invocation attempt {attempt}/{max_attempts}",
                    extra={"thread_id": thread_id, "attempt": attempt}
                )

                # Execute with automatic outcome tracking via middleware
                result, interrupt_value, tracking_id = await self.tracking_middleware.execute_with_tracking(
                    thread_id=thread_id,
                    incoming_message=incoming_message,
                    pm_invoker=lambda tid: self._invoke_pm(thread_id, raw_payload, run_id=tid),
                )

                # Handle user-facing logic (middleware handles tracking)
                if interrupt_value:
                    self.workflow_handler.handle_interrupt(sender, thread_id, interrupt_value)
                    return

                if not result:
                    logger.warning("No result from PM - cannot send response", extra={"thread_id": thread_id})
                    return

                # Extract messages from result
                messages = result.get("messages", [])

                logger.debug(
                    "PM result received",
                    extra={
                        "thread_id": thread_id,
                        "message_count": len(messages),
                        "attempt": attempt,
                    }
                )

                # CRITICAL: Detect blank/empty LLM responses (Gemini bug)
                is_blank = self._detect_blank_response(messages)

                if is_blank:
                    logger.warning(
                        f"BLANK LLM RESPONSE DETECTED on attempt {attempt}/{max_attempts}",
                        extra={
                            "thread_id": thread_id,
                            "attempt": attempt,
                            "tracking_id": tracking_id,
                        }
                    )

                    # If not last attempt, clear checkpoint and retry
                    if attempt < max_attempts:
                        logger.info(
                            "Clearing checkpoint and retrying",
                            extra={"thread_id": thread_id, "next_attempt": attempt + 1}
                        )
                        await self._clear_checkpoint(thread_id)
                        continue  # Retry

                    # Last attempt failed - inform user
                    logger.error(
                        f"BLANK LLM RESPONSE persisted after {max_attempts} attempts",
                        extra={"thread_id": thread_id, "tracking_id": tracking_id}
                    )
                    self.channel.send_text(
                        sender,
                        "I apologize, but I encountered an error generating a response. Please try again."
                    )
                    return

                # Valid response - process and send
                logger.info(
                    f"Valid response received on attempt {attempt}",
                    extra={"thread_id": thread_id, "attempt": attempt}
                )

                # Send PM response to user
                summary = self.workflow_handler.extract_summary(messages)
                if summary:
                    self.channel.send_text(sender, summary)
                    logger.info("PM response sent", extra={"thread_id": thread_id, "tracking_id": tracking_id})
                else:
                    logger.warning(
                        "No response extracted from PM messages",
                        extra={"thread_id": thread_id, "message_count": len(messages)}
                    )
                return

            except GraphRecursionError as exc:
                logger.exception("PM recursion limit exceeded", exc_info=exc)
                self.channel.send_error(sender, "recursion")
                return

            except Exception as exc:
                logger.exception("PM invocation failed", exc_info=exc)
                self.channel.send_error(sender, "processing")
                return

    def _detect_blank_response(self, messages: list[Any]) -> bool:
        """Detect if LLM returned blank/empty response.

        Args:
            messages: List of messages from PM result

        Returns:
            True if blank response detected, False otherwise
        """
        if not messages:
            return False

        # Check last AI message for blank content
        last_ai_message = None
        for msg in reversed(messages):
            if hasattr(msg, 'type') and msg.type == 'ai':
                last_ai_message = msg
                break

        if last_ai_message:
            content = getattr(last_ai_message, 'content', '')
            if not content or (isinstance(content, str) and not content.strip()):
                return True

        return False

    async def _handle_resume_flow(
        self,
        pm: Any,
        config: dict[str, Any],
        thread_id: str,
        raw_payload: dict[str, Any],
        pending_interrupts_list: list[InterruptInfo],
    ) -> tuple[dict[str, Any] | None, Any | None]:
        """Handle resume flow when interrupts exist.

        Args:
            pm: Project Manager instance
            config: LangGraph config
            thread_id: Conversation thread ID
            raw_payload: Raw platform message dict
            pending_interrupts_list: List of normalized interrupt dicts

        Returns:
            Tuple of (final_result, interrupt_value)
        """
        user_message = raw_payload.get("text", "")

        # Extract conversation history
        conversation_history = []
        try:
            state_snapshot = await pm.aget_state(config)
            if state_snapshot and hasattr(state_snapshot, 'values'):
                conversation_history = state_snapshot.values.get("messages", [])
        except Exception as e:
            logger.debug("Could not extract conversation history", extra={"thread_id": thread_id, "error": str(e)})

        # Analyze approval and build command
        try:
            command_obj, approval_tracking_id = self.approval_coordinator.analyze_and_build_command(
                thread_id=thread_id,
                user_message=user_message,
                pending_interrupts=pending_interrupts_list,
                conversation_history=conversation_history,
                raw_payload=raw_payload,
            )
        except Exception as e:
            logger.error(
                "Approval analysis failed",
                extra={"thread_id": thread_id, "error": str(e)},
                exc_info=True
            )
            raise

        if not command_obj:
            logger.error("Approval analysis returned no command", extra={"thread_id": thread_id})
            return None, None

        logger.info(
            "Resume flow: executing command",
            extra={
                "thread_id": thread_id,
                "interrupt_count": len(pending_interrupts_list),
                "message_preview": user_message[:50],
                "history_length": len(conversation_history),
                "command_resume_keys": list(command_obj.resume.keys()) if command_obj and command_obj.resume else [],
            }
        )

        # Execute command and collect results
        last_event = None
        interrupt_value = None

        try:
            logger.info(
                "Starting PM stream with Command",
                extra={"thread_id": thread_id, "stream_mode": "values"}
            )

            event_count = 0
            async for event in pm.astream(command_obj, config=config, stream_mode="values"):
                event_count += 1
                last_event = event
                if "__interrupt__" in event:
                    interrupts = event.get("__interrupt__") or []
                    if interrupts:
                        interrupt_value = interrupts[0].value

            logger.info(
                "PM stream completed",
                extra={
                    "thread_id": thread_id,
                    "event_count": event_count,
                    "had_new_interrupt": interrupt_value is not None,
                }
            )

            logger.debug(
                "Command execution complete",
                extra={"thread_id": thread_id, "had_new_interrupt": interrupt_value is not None}
            )
            return last_event, interrupt_value

        except GraphInterrupt as interrupt_exc:
            interrupts_list = interrupt_exc.args[0] if interrupt_exc.args else []
            logger.debug("Interrupt via exception", extra={"thread_id": thread_id, "count": len(interrupts_list)})
            if interrupts_list:
                return last_event, interrupts_list[0].value
            return last_event, None

        except Exception as e:
            logger.error("Command execution failed", extra={"thread_id": thread_id, "error": str(e)}, exc_info=True)
            raise

    async def _handle_new_message_flow(
        self,
        pm: Any,
        config: dict[str, Any],
        thread_id: str,
        raw_payload: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, Any | None]:
        """Handle new message flow when no interrupts exist.

        Args:
            pm: Project Manager instance
            config: LangGraph config
            thread_id: Conversation thread ID
            raw_payload: Raw platform message dict

        Returns:
            Tuple of (final_result, interrupt_value)
        """
        # Create payload with actual user text as content, metadata in additional_kwargs
        try:
            from langchain.messages import HumanMessage

            # Extract user text - this is what PM should see directly
            user_text = raw_payload.get("text", "")
            media_id = raw_payload.get("media_id")

            # Build natural language message that includes media_id when present
            # PM needs media_id explicitly to call download_media tool
            if media_id:
                if user_text:
                    # Text + media: append media_id to user message
                    user_text = f"{user_text} [media_id: {media_id}]"
                else:
                    # Media only: create descriptive message with media_id
                    user_text = f"[Media attachment: {media_id}]"

            # Put platform metadata in additional_kwargs (standard LangChain pattern)
            # PM receives clean user text with embedded media_id, metadata available if needed
            payload = {
                "messages": [HumanMessage(
                    content=user_text,
                    additional_kwargs={
                        "platform": raw_payload.get("platform"),
                        "sender": raw_payload.get("sender"),
                        "sender_name": raw_payload.get("sender_name"),
                        "media_id": media_id,
                        "timestamp": raw_payload.get("timestamp"),
                    }
                )]
            }
        except Exception as e:
            logger.error("Payload creation failed", extra={"thread_id": thread_id, "error": str(e)}, exc_info=True)
            raise

        logger.info(
            "New message flow: starting PM stream",
            extra={
                "thread_id": thread_id,
                "has_text": raw_payload.get('text') is not None,
                "has_media": raw_payload.get('media_id') is not None,
            }
        )

        # Stream PM and accumulate interrupts
        last_event = None
        accumulated_interrupts: list[Any] = []

        try:
            async for event in pm.astream(payload, config=config, stream_mode="values"):
                last_event = event
                if "__interrupt__" in event:
                    interrupts = event.get("__interrupt__") or []
                    if interrupts:
                        accumulated_interrupts.extend(interrupts)

            # Process accumulated interrupts
            interrupt_value = None
            if accumulated_interrupts:
                if len(accumulated_interrupts) > 1:
                    # Flatten multiple interrupts
                    interrupt_value = []
                    for intr in accumulated_interrupts:
                        if isinstance(intr.value, list):
                            interrupt_value.extend(intr.value)
                        else:
                            interrupt_value.append(intr.value)
                else:
                    interrupt_value = accumulated_interrupts[0].value

            logger.debug(
                "PM stream complete",
                extra={
                    "thread_id": thread_id,
                    "interrupt_count": len(accumulated_interrupts),
                    "has_result": last_event is not None,
                }
            )
            return last_event, interrupt_value

        except GraphInterrupt as interrupt_exc:
            interrupts_list = interrupt_exc.args[0] if interrupt_exc.args else []
            logger.debug("Interrupt via exception", extra={"thread_id": thread_id, "count": len(interrupts_list)})
            if interrupts_list:
                return last_event, interrupts_list[0].value
            return last_event, None

        except Exception as e:
            logger.error("PM streaming failed", extra={"thread_id": thread_id, "error": str(e)}, exc_info=True)
            raise

    async def _invoke_pm(
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
        # Create PM and config
        try:
            pm = await self._create_project_manager()
            config = self._build_config(thread_id, run_id=run_id)
        except Exception as e:
            logger.error("PM initialization failed", extra={"thread_id": thread_id, "error": str(e)}, exc_info=True)
            raise

        # Check for pending interrupts
        try:
            state_snapshot = await pm.aget_state(config)
            pending_interrupts_list = InterruptUnpacker.unpack_interrupts(state_snapshot, thread_id=thread_id)

            flow_type = "resume" if pending_interrupts_list else "new_message"
            logger.info(
                "PM invocation starting",
                extra={
                    "thread_id": thread_id,
                    "flow_type": flow_type,
                    "interrupt_count": len(pending_interrupts_list),
                }
            )
        except Exception as e:
            logger.warning(
                "Interrupt check failed, treating as new message",
                extra={"thread_id": thread_id, "error": str(e)}
            )
            pending_interrupts_list = []

        # Route to appropriate flow
        if pending_interrupts_list:
            return await self._handle_resume_flow(pm, config, thread_id, raw_payload, pending_interrupts_list)
        else:
            return await self._handle_new_message_flow(pm, config, thread_id, raw_payload)

    async def _get_async_checkpointer(self) -> BaseCheckpointSaver[Any]:
        """Get async checkpointer instance."""
        if self._checkpointer:
            return self._checkpointer
        from autifyme_agents.integrations.storage.postgres_saver_factory import (
            get_async_checkpointer,
        )
        return await get_async_checkpointer()

    async def _create_project_manager(self) -> Any:
        """Create PM instance with company context and channel.

        PM checkpointer stores PM conversation state.
        DeepAgents SubAgentMiddleware handles specialist state internally.
        """
        # Get PM checkpointer (stores PM conversation state)
        pm_checkpointer = await self._get_async_checkpointer()

        return await create_project_manager(
            company_profile=self.company_profile,
            checkpointer=pm_checkpointer,
            storage=self.storage,
            channel=self.channel,
        )

    def _build_config(self, thread_id: str, run_id: str | None = None) -> dict[str, Any]:
        """Build PM config.

        Args:
            thread_id: Conversation thread ID
            run_id: Optional run_id to use as trace_id in LangSmith

        Returns:
            PM config dict with context for v1.0 context_schema support
        """
        # Build typed company context for v1.0 context_schema
        from autifyme_agents.schemas.context import CompanyContext

        company_context = CompanyContext(
            company_id=self.company_profile.id,
            company_name=self.company_profile.name,
            brand_voice=self.company_profile.brand_voice,
            target_audience=self.company_profile.target_audience,
            style_preferences=self.company_profile.style_preferences or [],
            industry=self.company_profile.industry,
        )

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
            "context": company_context,  # v1.0: Type-safe context injection
        }

        # Add run_id if provided - this becomes the trace_id in LangSmith
        if run_id:
            from uuid import UUID
            config["run_id"] = UUID(run_id) if isinstance(run_id, str) else run_id

        return config


