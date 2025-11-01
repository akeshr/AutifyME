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

import logging

# Threading removed - not needed for single-tenant architecture
# FastAPI background tasks + database checkpointing provide sufficient concurrency control
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.errors import GraphInterrupt, GraphRecursionError

from autifyme_agents.core.config import settings
from autifyme_agents.core.ports import StorageInterface
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

# Constants removed - threading complexity eliminated


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

    async def _execute_workflow(
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
                }
            )

            # Send workflow-specific completion to user
            cataloging_result = self.workflow_handler.extract_result(messages)
            if cataloging_result:
                self.channel.send_completion(sender, cataloging_result)
                logger.info("Workflow completed", extra={"thread_id": thread_id, "tracking_id": tracking_id})
                return

            # Send conversational response
            summary = self.workflow_handler.extract_summary(messages)
            if summary:
                self.channel.send_text(sender, summary)
                logger.info("Conversational response sent", extra={"thread_id": thread_id})
            else:
                logger.warning(
                    "No response extracted from PM messages",
                    extra={
                        "thread_id": thread_id,
                        "message_count": len(messages),
                    }
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
        pending_interrupts_list: list[dict[str, Any]],
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

        Uses separate checkpointers for PM and specialists for context isolation:
        - PM checkpointer: Stores PM conversation with user
        - Specialist checkpointer: Stores only specialist's own work history
        """
        # Get PM checkpointer (stores full conversation)
        pm_checkpointer = await self._get_async_checkpointer()

        # Get separate checkpointer for specialists (context isolation)
        # Specialists should only see their own work, not PM conversation
        specialist_checkpointer = await self._get_async_checkpointer()

        return await create_project_manager(
            company_profile=self.company_profile,
            checkpointer=pm_checkpointer,
            specialist_checkpointer=specialist_checkpointer,
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

