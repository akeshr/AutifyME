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
from datetime import datetime
from threading import Lock
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.errors import GraphInterrupt, GraphRecursionError
from langgraph.types import Command

from autifyme_agents.core.config import settings
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from autifyme_agents.schemas.approval import BatchApprovalResponse
from autifyme_agents.schemas.models import CatalogingResult, CompanyProfile
from autifyme_agents.workflows.approval_analyzer import analyze_approval
from autifyme_agents.workflows.channels.protocol import MessagingChannel
from autifyme_agents.workflows.outcome_tracker import IncomingMessage, OutcomeTracker
from autifyme_agents.workflows.project_manager import create_project_manager

logger = logging.getLogger(__name__)

# Constants
MAX_THREAD_LOCKS = 1000  # LRU cache size for thread locks


class WorkflowRunner:
    """Blind executor - forwards messages to PM for intelligent orchestration.

    ## CONTEXT-AWARE APPROVAL ARCHITECTURE:

    Runner responsibilities:
    - Forward messages to PM for orchestration
    - Extract interrupt context from checkpoints
    - Extract conversation history from PM state
    - Use approval analyzer with full conversation history for context-aware decisions
    - Execute Command objects for approval resumption
    - Send interrupts/results to user via channel

    PM handles:
    - Intent detection for new requests
    - Task orchestration and delegation to departments
    - Media download and processing
    - Overall workflow management

    Approval Analyzer handles (with conversation history):
    - Batch approval interpretation using full conversation context
    - Multi-turn approval conversations (resolves "make it 25" from prior clarification)
    - Contextual reference resolution ("the cheaper one", "use same description")
    - Natural language approval patterns
    - Returns structured BatchApprovalResponse

    LangGraph + DeepAgents handle:
    - Checkpoint state management
    - HITL middleware interrupt/resume
    - Message sequence synthesis
    - Tool execution

    ## KEY BENEFITS:
    - Approval analyzer has full conversation context (fixes context-blind issue)
    - Minimal architectural changes (just pass conversation_history parameter)
    - Type-safe communication via BatchApprovalResponse structured outputs
    - Separation of concerns (PM orchestrates, analyzer interprets approvals)
    - Works with existing DeepAgents PM architecture
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
        logger.info("INITIALIZING GENERIC HITL FRAMEWORK (PM-ONLY ARCHITECTURE)")
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

        logger.info("Generic HITL Framework initialized - PM-only architecture")
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

        ✅ SIMPLIFIED: Command resume for deepagents HITL.

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

        workflow_start_time = datetime.now()

        incoming_message = IncomingMessage(
            sender_id=sender,
            sender_name=sender_name,
            text=text,
            media_id=media_id,
            platform=self.channel.__class__.__name__.replace("Channel", "").lower(),
        )
        tracking_id = self.outcome_tracker.track_workflow_start(thread_id, incoming_message)

        # Build raw payload for PM with sender name for personalization
        raw_payload = {
            "platform": incoming_message.platform,
            "sender": sender,
            "sender_name": sender_name,  # For personalized greetings/responses
            "text": text,
            "media_id": media_id,
            "timestamp": incoming_message.received_at.isoformat(),
        }

        try:
            # ✅ ALWAYS invoke PM with message - it handles checkpoint state
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

        ✅ PM-ONLY ARCHITECTURE: PM handles intent detection and Command construction.

        When interrupts exist:
        1. Populate state["pending_interrupts"] from checkpoint
        2. Forward user message to PM
        3. PM analyzes and outputs "COMMAND: {resume: [...]}"
        4. Parse PM's COMMAND output
        5. Build actual Command and resume

        Args:
            thread_id: Conversation thread ID
            raw_payload: Raw platform message dict

        Returns:
            Tuple of (final_result, interrupt_value) - at most one will be non-None
        """
        logger.debug("Invoking Project Manager", extra={"thread_id": thread_id})

        pm = self._create_project_manager()
        config = self._build_config(thread_id)

        # Check for pending HITL interrupts
        pending_interrupts_list = []
        try:
            state_snapshot = pm.get_state(config)

            if state_snapshot and state_snapshot.interrupts:
                # Extract interrupt info for approval analyzer
                # IMPORTANT: interrupt_obj.value can be:
                # - A list of actions (parallel tool calls from same agent)
                # - A single dict (single action)
                # We need N interrupt_info objects for approval analyzer (1 response per action)

                for base_idx, interrupt_obj in enumerate(state_snapshot.interrupts):
                    interrupt_id = interrupt_obj.id if hasattr(interrupt_obj, 'id') else f"interrupt_{base_idx}"
                    interrupt_value = interrupt_obj.value if hasattr(interrupt_obj, 'value') else None

                    # Check if value is a list of actions (parallel tool calls)
                    if isinstance(interrupt_value, list):
                        logger.debug(
                            "Unpacking list-valued interrupt into individual actions",
                            extra={
                                "thread_id": thread_id,
                                "interrupt_id": interrupt_id,
                                "action_count": len(interrupt_value),
                            }
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

                            interrupt_info = {
                                "interrupt_id": f"{interrupt_id}_{action_idx}",
                                "original_interrupt_id": interrupt_id,  # Track original for Command building
                                "tool_name": tool_name,
                                "tool_args": tool_args,
                                "description": description,
                            }
                            pending_interrupts_list.append(interrupt_info)

                    # Single dict value (single action)
                    elif isinstance(interrupt_value, dict):
                        interrupt_info = {
                            "interrupt_id": interrupt_id,
                            "tool_name": interrupt_value.get("tool_name", "unknown"),
                            "tool_args": interrupt_value.get("tool_args", {}),
                            "description": str(interrupt_value)[:100],
                        }
                        pending_interrupts_list.append(interrupt_info)

                    # Fallback for unknown format
                    else:
                        interrupt_info = {
                            "interrupt_id": interrupt_id,
                            "tool_name": "unknown",
                            "tool_args": {},
                            "description": str(interrupt_value)[:100] if interrupt_value else "Pending approval",
                        }
                        pending_interrupts_list.append(interrupt_info)

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

            logger.info(
                "Analyzing approval with conversation history",
                extra={
                    "thread_id": thread_id,
                    "interrupt_count": len(pending_interrupts_list),
                    "user_message": user_message[:50],
                    "has_history": len(conversation_history) > 0,
                }
            )

            try:
                # Invoke approval analyzer with conversation history
                approval_response: BatchApprovalResponse = analyze_approval(
                    pending_interrupts=pending_interrupts_list,
                    user_message=user_message,
                    conversation_history=conversation_history,  # NEW: Full context
                )

                logger.info(
                    "Approval analysis complete",
                    extra={
                        "thread_id": thread_id,
                        "response_count": len(approval_response.responses),
                        "reasoning": approval_response.reasoning,
                    }
                )

            except ValueError as e:
                logger.error(
                    "Approval analysis validation failed",
                    extra={"thread_id": thread_id, "error": str(e)}
                )
                self.channel.send_text(
                    raw_payload.get("sender", ""),
                    "I had trouble processing your response. Please try: 'approve' or 'reject'"
                )
                return None, None

            except Exception as e:
                logger.exception(
                    "Approval analysis failed",
                    extra={"thread_id": thread_id, "error_type": type(e).__name__}
                )
                self.channel.send_text(
                    raw_payload.get("sender", ""),
                    "I encountered an error processing your response. Please try again."
                )
                return None, None

            # Build Command from structured approval response
            command_obj = self._build_command_from_approval(
                approval_response, pending_interrupts_list
            )

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
            interrupt_value = None

            try:
                for event in pm.stream(payload, config=config, stream_mode="values"):
                    last_event = event

                    # Detect interrupt in stream
                    if "__interrupt__" in event:
                        interrupts = event.get("__interrupt__") or []
                        if interrupts:
                            interrupt_value = interrupts[0].value
                            logger.info(
                                "Interrupt detected",
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

    def _build_command_from_approval(
        self,
        approval_response: BatchApprovalResponse,
        pending_interrupts: list[dict],
    ) -> Command:
        """Build LangGraph Command from structured approval response.

        Takes the Pydantic BatchApprovalResponse from approval analyzer and
        constructs a LangGraph Command object for resuming interrupted workflows.

        IMPORTANT: Handles both single and parallel interrupts:
        - Single interrupt: interrupt_id → [response]
        - Parallel (list-valued): original_interrupt_id → [response_0, response_1, ...]

        Args:
            approval_response: Structured approval response from analyzer
            pending_interrupts: List of pending interrupt contexts

        Returns:
            Command object ready for execution

        Example (Parallel):
            approval_response.responses = [
                {"type": "accept", "args": None},
                {"type": "edit", "args": {"price": 45.0}}
            ]
            pending_interrupts = [
                {"interrupt_id": "int_1_0", "original_interrupt_id": "int_1", ...},
                {"interrupt_id": "int_1_1", "original_interrupt_id": "int_1", ...}
            ]
            →
            Command(resume={
                "int_1": [{"type": "accept", "args": None}, {"type": "edit", "args": {"price": 45.0}}]
            })
        """
        # Group responses by original_interrupt_id (for parallel actions)
        # or by interrupt_id (for single actions)
        from collections import defaultdict
        interrupt_responses = defaultdict(list)

        for idx, interrupt_info in enumerate(pending_interrupts):
            # Use original_interrupt_id if available (parallel case), otherwise use interrupt_id
            original_id = interrupt_info.get("original_interrupt_id", interrupt_info["interrupt_id"])
            response = approval_response.responses[idx]

            # Convert Pydantic model to dict
            interrupt_responses[original_id].append(response.model_dump())

        logger.info(
            "Built Command from structured approval",
            extra={
                "total_responses": len(pending_interrupts),
                "interrupt_count": len(interrupt_responses),
                "interrupt_ids": list(interrupt_responses.keys()),
            }
        )

        return Command(resume=dict(interrupt_responses))

    def _handle_interrupt(
        self,
        sender: str,
        thread_id: str,
        interrupt_value: Any,
    ) -> None:
        """Forward interrupt to user via channel.

        ✅ STANDARD APPROACH: Unwrap DeepAgents internal structure before sending to channel.

        DeepAgents wraps tool calls in action_request format:
        [{'action_request': {'action': 'tool_name', 'args': {actual_data}}}]

        Channel should receive clean data (just the args), not framework internals.

        Args:
            sender: Channel-specific sender ID
            thread_id: Conversation thread ID
            interrupt_value: Value from interrupt (may be wrapped by DeepAgents)
        """
        logger.debug("Handling HITL interrupt", extra={"thread_id": thread_id})

        try:
            # Unwrap DeepAgents structure if present (standard pattern from lines 344-366)
            clean_value = interrupt_value

            if isinstance(interrupt_value, list) and len(interrupt_value) > 0:
                # FIXED: Process ALL actions in batch, not just the first one
                for action in interrupt_value:
                    if isinstance(action, dict) and "action_request" in action:
                        # DeepAgents format - extract clean args
                        action_request = action.get("action_request", {})
                        clean_value = action_request.get("args", interrupt_value)
                        logger.debug(
                            "Unwrapped DeepAgents interrupt structure",
                            extra={
                                "thread_id": thread_id,
                                "tool_name": action_request.get("action", "unknown"),
                            }
                        )
                        # Convert to Product and send for approval
                        if isinstance(clean_value, dict):
                            from autifyme_agents.schemas.models import Product
                            draft = Product.model_validate(clean_value)
                            logger.debug(
                                "Converted interrupt args to Product object",
                                extra={"thread_id": thread_id, "product_name": draft.name}
                            )
                            self.channel.send_approval_request(sender, draft)

            # Handle single interrupt case
            elif isinstance(interrupt_value, dict):
                clean_value = interrupt_value
                # Convert dict args to Product object for channel
                if isinstance(clean_value, dict):
                    from autifyme_agents.schemas.models import Product
                    draft = Product.model_validate(clean_value)
                    logger.debug(
                        "Converted single interrupt to Product object",
                        extra={"thread_id": thread_id, "product_name": draft.name}
                    )
                else:
                    draft = clean_value
                self.channel.send_approval_request(sender, draft)

            logger.info(
                "Interrupt(s) forwarded to user - awaiting response",
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
