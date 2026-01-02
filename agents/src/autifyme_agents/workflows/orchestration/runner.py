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
from pathlib import Path
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.errors import GraphInterrupt, GraphRecursionError
from langgraph.types import Command

from autifyme_agents.core.config import settings
from autifyme_agents.core.execution_context import execution_context
from autifyme_agents.core.gemini_retry import BlankResponseError
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.schemas.interrupt import InterruptInfo
from autifyme_agents.schemas.models import CompanyProfile
from autifyme_agents.schemas.pm_output import PMOutput
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

    async def handle_message_batch(
        self,
        sender: str,
        messages: list[dict[str, Any]],
    ) -> None:
        """Process a batch of messages as unified context.

        Used by MessageBatcher for multi-image scenarios where user sends
        multiple images in quick succession. All messages are combined into
        a single PM invocation with full context.

        Args:
            sender: Channel-specific sender ID (phone number)
            messages: List of pending message records from batch buffer
        """
        if not messages:
            logger.warning("handle_message_batch called with empty batch")
            return

        logger.info(
            "Handling message batch",
            extra={
                "sender": sender,
                "batch_size": len(messages),
                "message_types": [m.get("message_type") for m in messages],
            },
        )

        # Build unified payload from batch
        texts = []
        media_ids = []
        sender_name = None

        for msg in messages:
            # Collect text content (message text + captions)
            if msg.get("text_content"):
                texts.append(msg["text_content"])
            if msg.get("caption"):
                texts.append(msg["caption"])

            # Collect media IDs
            if msg.get("media_id"):
                media_ids.append(msg["media_id"])

            # Use first available sender_name
            if sender_name is None and msg.get("sender_name"):
                sender_name = msg["sender_name"]

        # Construct combined text with media reference
        combined_text = " ".join(texts) if texts else ""
        if media_ids:
            media_summary = f"[{len(media_ids)} media attachment(s): {', '.join(media_ids)}]"
            combined_text = f"{combined_text} {media_summary}".strip() if combined_text else media_summary

        # Get thread_id and execute workflow
        thread_id = self.channel.format_thread_id(sender)

        # Use batch-aware execution with media_ids array
        await self._execute_workflow_batch(
            thread_id=thread_id,
            sender=sender,
            combined_text=combined_text,
            media_ids=media_ids,
            sender_name=sender_name,
            message_count=len(messages),
            first_received_at=messages[0].get("received_at"),
        )

    async def _execute_workflow_batch(
        self,
        thread_id: str,
        sender: str,
        combined_text: str,
        media_ids: list[str],
        sender_name: str | None,
        message_count: int,
        first_received_at: str | None,
    ) -> None:
        """Execute workflow for a batched message.

        Similar to _execute_workflow but handles multiple media_ids.

        Args:
            thread_id: Conversation thread ID
            sender: Channel-specific sender ID
            combined_text: Unified text from all messages
            media_ids: List of media attachment IDs
            sender_name: User's display name
            message_count: Number of messages in batch
            first_received_at: Timestamp of first message
        """
        logger.debug(
            "Executing batch workflow",
            extra={
                "thread_id": thread_id,
                "media_count": len(media_ids),
                "message_count": message_count,
            },
        )

        # Prepare structured incoming message (use first media_id for compatibility)
        incoming_message = IncomingMessage(
            sender_id=sender,
            sender_name=sender_name,
            text=combined_text,
            media_id=media_ids[0] if media_ids else None,
            platform=self.channel.__class__.__name__.replace("Channel", "").lower(),
        )

        # Build batch-aware raw payload for PM
        raw_payload = {
            "platform": incoming_message.platform,
            "sender": sender,
            "sender_name": sender_name,
            "text": combined_text,
            "media_id": media_ids[0] if media_ids else None,  # Backward compat
            "media_ids": media_ids,  # NEW: Full array for batch handling
            "message_count": message_count,
            "timestamp": first_received_at or incoming_message.received_at.isoformat(),
        }

        # Set execution context for all tools - thread_id invisible to LLMs
        with execution_context(thread_id=thread_id, company_id="default"):
            try:
                # Execute with automatic outcome tracking via middleware
                result, interrupt_value, tracking_id = await self.tracking_middleware.execute_with_tracking(
                    thread_id=thread_id,
                    incoming_message=incoming_message,
                    pm_invoker=lambda tid: self._invoke_pm(thread_id, raw_payload, run_id=tid),
                )

                # Handle user-facing logic (same as single message flow)
                if interrupt_value:
                    error_response = self.workflow_handler.handle_interrupt(sender, thread_id, interrupt_value)

                    # If validation failed, auto-reject with error so agent can retry
                    if error_response:
                        error_msg = error_response.get("error", str(error_response))
                        logger.warning(
                            "WriteIntent validation failed in batch - auto-rejecting",
                            extra={"thread_id": thread_id, "error_type": error_response.get("error_type")},
                        )
                        auto_reject: Command[Any] = Command(
                            resume={"decisions": [{"type": "reject", "message": error_msg}]}
                        )
                        await self._resume_with_command(thread_id, auto_reject, sender)
                        return

                    # HITL pending - nothing more to do
                    return

                # Workflow completed successfully - cleanup subagent checkpoints
                # Subagents are stateless; their tools:* checkpoints are only needed during HITL
                await self._cleanup_subagent_checkpoints(thread_id)

                if not result:
                    logger.warning(
                        "Batch workflow completed without result",
                        extra={"thread_id": thread_id},
                    )
                    return

                # Extract messages from result
                messages = result.get("messages", [])
                logger.debug(
                    "Batch PM result received",
                    extra={"thread_id": thread_id, "message_count": len(messages)},
                )

                # Check for structured response (PMOutput schema)
                structured_response = result.get("structured_response")
                if structured_response and isinstance(structured_response, PMOutput):
                    # Send images first (if any)
                    if structured_response.images:
                        for img in structured_response.images:
                            try:
                                self.channel.send_image(sender, img.path, img.caption)
                            except Exception as img_err:
                                logger.warning(
                                    "Failed to send image in batch",
                                    extra={"path": img.path, "error": str(img_err)}
                                )

                    # Send text message
                    if structured_response.message:
                        self.channel.send_text(sender, structured_response.message)
                        logger.info(
                            "Batch PM structured response sent",
                            extra={
                                "thread_id": thread_id,
                                "tracking_id": tracking_id,
                                "image_count": len(structured_response.images) if structured_response.images else 0,
                            }
                        )
                else:
                    # Fallback to legacy extract_summary for non-structured responses
                    summary = self.workflow_handler.extract_summary(messages)
                    if summary:
                        self.channel.send_text(sender, summary)
                        logger.info("Batch PM response sent (legacy)", extra={"thread_id": thread_id})
                    else:
                        logger.warning(
                            "No response extracted from batch PM messages",
                            extra={"thread_id": thread_id, "message_count": len(messages)}
                        )

            except Exception:
                logger.error(
                    "Batch workflow execution failed",
                    exc_info=True,
                    extra={"thread_id": thread_id},
                )
                # Send error response to user
                self.channel.send_text(
                    sender,
                    "I encountered an error processing your messages. Please try again.",
                )

    async def _execute_workflow(
        self,
        thread_id: str,
        sender: str,
        text: str | None,
        media_id: str | None,
        sender_name: str | None = None,
    ) -> None:
        """Execute workflow with PM invocation.

        Uses outcome tracking middleware for automatic tracking.
        Blank response handling is delegated to GeminiWithRetry at LLM level.

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

        # Set execution context for all tools - thread_id invisible to LLMs
        with execution_context(thread_id=thread_id, company_id="default"):
            try:
                # Execute with automatic outcome tracking via middleware
                result, interrupt_value, tracking_id = await self.tracking_middleware.execute_with_tracking(
                    thread_id=thread_id,
                    incoming_message=incoming_message,
                    pm_invoker=lambda tid: self._invoke_pm(thread_id, raw_payload, run_id=tid),
                )

                # Handle user-facing logic (middleware handles tracking)
                if interrupt_value:
                    error_response = self.workflow_handler.handle_interrupt(sender, thread_id, interrupt_value)

                    # If validation failed, auto-reject with error so agent can retry
                    if error_response:
                        error_msg = error_response.get("error", str(error_response))
                        logger.warning(
                            "WriteIntent validation failed - auto-rejecting",
                            extra={"thread_id": thread_id, "error_type": error_response.get("error_type")}
                        )
                        auto_reject: Command[Any] = Command(
                            resume={"decisions": [{"type": "reject", "message": error_msg}]}
                        )
                        await self._resume_with_command(thread_id, auto_reject, sender)
                    return

                # Workflow completed successfully - cleanup subagent checkpoints
                # Subagents are stateless; their tools:* checkpoints are only needed during HITL
                await self._cleanup_subagent_checkpoints(thread_id)

                if not result:
                    logger.warning("No result from PM - cannot send response", extra={"thread_id": thread_id})
                    return

                # Extract messages from result
                messages = result.get("messages", [])

                logger.debug(
                    "PM result received",
                    extra={"thread_id": thread_id, "message_count": len(messages)},
                )

                # Check for structured response (PMOutput schema)
                structured_response = result.get("structured_response")
                if structured_response and isinstance(structured_response, PMOutput):
                    # Send images first (if any)
                    if structured_response.images:
                        for img in structured_response.images:
                            try:
                                self.channel.send_image(sender, img.path, img.caption)
                                logger.debug(
                                    "Image sent to user",
                                    extra={"path": img.path, "has_caption": img.caption is not None}
                                )
                            except Exception as img_err:
                                logger.warning(
                                    "Failed to send image",
                                    extra={"path": img.path, "error": str(img_err)}
                                )

                    # Send text message
                    if structured_response.message:
                        self.channel.send_text(sender, structured_response.message)
                        logger.info(
                            "PM structured response sent",
                            extra={
                                "thread_id": thread_id,
                                "tracking_id": tracking_id,
                                "image_count": len(structured_response.images) if structured_response.images else 0,
                                "await_feedback": structured_response.await_feedback,
                            }
                        )

                    # Handle await_feedback (interrupt for user response)
                    if structured_response.await_feedback:
                        logger.info(
                            "PM awaiting user feedback",
                            extra={"thread_id": thread_id}
                        )
                        # Note: Feedback loop is handled by next user message
                        # No explicit interrupt needed - PM state is preserved
                else:
                    # Fallback to legacy extract_summary for non-structured responses
                    summary = self.workflow_handler.extract_summary(messages)
                    if summary:
                        self.channel.send_text(sender, summary)
                        logger.info("PM response sent (legacy)", extra={"thread_id": thread_id, "tracking_id": tracking_id})
                    else:
                        logger.warning(
                            "No response extracted from PM messages",
                            extra={"thread_id": thread_id, "message_count": len(messages)}
                        )

            except BlankResponseError as exc:
                # Gemini returned blank responses even after LLM-level retries
                logger.error(
                    "Gemini blank response after all retries",
                    extra={"thread_id": thread_id, "error": str(exc)},
                )
                self.channel.send_text(
                    sender,
                    "I apologize, but I encountered an error generating a response. Please try again."
                )

            except GraphRecursionError as exc:
                logger.exception("PM recursion limit exceeded", exc_info=exc)
                self.channel.send_error(sender, "recursion")

            except Exception as exc:
                logger.exception("PM invocation failed", exc_info=exc)
                self.channel.send_error(sender, "processing")

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
        media_id = raw_payload.get("media_id")
        media_path: str | None = None

        # Download media if user sent image with their approval response
        if media_id:
            try:
                logger.info(
                    "Downloading media attached to approval response",
                    extra={"thread_id": thread_id, "media_id": media_id}
                )
                # Use channel's download_media_with_bytes + storage upload (same as platform_tools)
                if hasattr(self.channel, 'download_media_with_bytes'):
                    local_path, media_bytes, mime_type = self.channel.download_media_with_bytes(media_id)
                    filename = Path(local_path).name
                    upload_result = await self.storage.upload_to_inbox(
                        file_bytes=media_bytes,
                        thread_id=thread_id,
                        filename=filename,
                        content_type=mime_type,
                    )
                    media_path = upload_result["storage_path"]
                    logger.info(
                        "Media downloaded and stored for approval response",
                        extra={"thread_id": thread_id, "media_path": media_path}
                    )
            except Exception as e:
                logger.warning(
                    "Failed to download media from approval response - continuing without it",
                    extra={"thread_id": thread_id, "media_id": media_id, "error": str(e)}
                )

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
                media_path=media_path,
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

    async def _resume_with_command(
        self,
        thread_id: str,
        command_obj: Command[Any],
        sender: str,
    ) -> None:
        """Resume workflow with a Command (used for auto-reject on validation errors).

        Args:
            thread_id: Conversation thread ID
            command_obj: LangGraph Command to resume with
            sender: Channel sender ID for error messages
        """
        try:
            pm = await self._create_project_manager()
            config = self._build_config(thread_id)

            logger.info(
                "Auto-resuming workflow with command",
                extra={"thread_id": thread_id, "command_type": "auto_reject"}
            )

            # Stream and collect result
            last_event = None
            async for event in pm.astream(command_obj, config=config, stream_mode="values"):
                last_event = event
                # Check for new interrupts (e.g., agent retried and hit HITL again)
                if "__interrupt__" in event:
                    interrupts = event.get("__interrupt__") or []
                    if interrupts:
                        # New interrupt after auto-reject - send to user
                        interrupt_value = interrupts[0].value
                        new_error = self.workflow_handler.handle_interrupt(sender, thread_id, interrupt_value)
                        if new_error:
                            logger.error(
                                "Repeated validation failure after auto-reject",
                                extra={"thread_id": thread_id, "error_type": new_error.get("error_type")}
                            )
                        return

            # Send any response from PM
            if last_event:
                messages = last_event.get("messages", [])
                summary = self.workflow_handler.extract_summary(messages)
                if summary:
                    self.channel.send_text(sender, summary)
                    logger.info(
                        "Auto-reject response sent to user",
                        extra={"thread_id": thread_id, "summary_length": len(summary)}
                    )

        except Exception as e:
            logger.error(
                "Auto-resume failed",
                extra={"thread_id": thread_id, "error": str(e)},
                exc_info=True
            )
            self.channel.send_error(sender, "processing", "I encountered an issue. Please try again.")

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
            # Use `or ""` to handle explicit None values (not just missing keys)
            user_text = raw_payload.get("text") or ""

            # Handle batch scenario (media_ids array) or single message (media_id)
            media_ids = raw_payload.get("media_ids", [])
            media_id = raw_payload.get("media_id")

            # Build natural language message that includes media reference(s) when present
            # PM needs media_id(s) explicitly to call download_media tool
            if media_ids:
                # Batch scenario: multiple media attachments
                media_refs = ", ".join(media_ids)
                if user_text:
                    # Text + media batch: append all media_ids to user message
                    user_text = f"{user_text} [media attachments ({len(media_ids)}): {media_refs}]"
                else:
                    # Media batch only: create descriptive message with all media_ids
                    user_text = f"[{len(media_ids)} media attachment(s): {media_refs}]"
            elif media_id:
                # Single media scenario (backward compat)
                if user_text:
                    # Text + media: append media_id to user message
                    user_text = f"{user_text} [media_id: {media_id}]"
                else:
                    # Media only: create descriptive message with media_id
                    user_text = f"[Media attachment: {media_id}]"

            # Guard: ensure we have actual content to send to PM
            # Empty content causes Gemini to fail with "contents are required"
            if not user_text.strip():
                logger.warning(
                    "Skipping message with no content (empty text, no media)",
                    extra={"thread_id": thread_id},
                )
                return (None, None)

            # Put platform metadata in additional_kwargs (standard LangChain pattern)
            # PM receives clean user text with embedded media_id(s), metadata available if needed
            payload = {
                "messages": [HumanMessage(
                    content=user_text,
                    additional_kwargs={
                        "platform": raw_payload.get("platform"),
                        "sender": raw_payload.get("sender"),
                        "sender_name": raw_payload.get("sender_name"),
                        "media_id": media_id,  # Backward compat
                        "media_ids": media_ids,  # Batch support
                        "message_count": raw_payload.get("message_count"),
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

    async def _cleanup_subagent_checkpoints(self, thread_id: str) -> None:
        """Cleanup subagent checkpoints after successful workflow completion.

        Subagents (specialists) are stateless - their checkpoints (tools:* namespace)
        are only needed during HITL interrupts for resume. Once PM completes without
        interrupt, all subagent checkpoints can be safely deleted.

        Called when interrupt_value is None after PM execution.

        Args:
            thread_id: Conversation thread ID to cleanup checkpoints for
        """
        await self.storage.cleanup_subagent_checkpoints(thread_id)

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

        # Extract visual identity and SKU naming convention
        visual = self.company_profile.visual_identity
        sku_conv = self.company_profile.sku_naming_convention

        company_context = CompanyContext(
            # Core identification
            company_id=self.company_profile.id,
            company_name=self.company_profile.name,
            # Brand guidelines
            brand_voice=self.company_profile.brand_voice,
            target_audience=self.company_profile.target_audience,
            style_preferences=self.company_profile.style_preferences or [],
            industry=self.company_profile.industry,
            # Visual identity (for creative specialist)
            primary_color=visual.primary_color,
            secondary_color=visual.secondary_color,
            accent_color=visual.accent_color,
            font_family=visual.font_family,
            logo_asset_path=visual.logo_asset_path,
            # Catalog defaults
            default_currency=self.company_profile.default_currency,
            currency_symbol=self.company_profile.currency_symbol,
            default_price_list_id=None,  # TODO: Load from company settings
            # SKU naming
            sku_prefix=sku_conv.prefix if sku_conv else None,
            sku_separator=sku_conv.separator if sku_conv else "-",
            sku_uppercase=sku_conv.uppercase if sku_conv else True,
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


