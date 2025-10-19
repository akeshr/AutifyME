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
        checkpointer: BaseCheckpointSaver[Any] | None = None,
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
        logger.info("INITIALIZING GENERIC HITL FRAMEWORK (APPROVAL_ANALYZER ARCHITECTURE)")
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

            # Extract and link trace_id for observability correlation
            # Trace ID is stored in LangSmith run metadata after PM execution
            try:
                from langsmith import Client
                ls_client = Client()
                # Query latest run for this thread (most recent trace)
                runs_iter = ls_client.list_runs(
                    filter=f'eq(metadata_key, "langsmith.thread_id") and eq(metadata_value, "{thread_id}")',
                    limit=1
                )
                runs = list(runs_iter)
                if runs:
                    trace_id = str(runs[0].trace_id)
                    self.outcome_tracker.set_trace_id(thread_id, trace_id)
                    logger.debug(
                        "Linked trace_id to workflow outcome",
                        extra={"thread_id": thread_id, "trace_id": trace_id}
                    )
            except Exception as e:
                logger.warning(
                    "Failed to extract trace_id (non-blocking)",
                    extra={"thread_id": thread_id, "error": str(e)}
                )

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
                            logger.info(f"[RESUME ORDER] Interrupt {action_idx + 1}: {tool_args.get('name', 'unknown')}")

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
            accumulated_interrupts = []  # ✅ Accumulate ALL interrupts across stream events

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

    def _build_command_from_approval(
        self,
        approval_response: BatchApprovalResponse,
        pending_interrupts: list[dict[str, Any]],
    ) -> Command[Any]:
        """Build LangGraph Command from structured approval response.

        Takes the Pydantic BatchApprovalResponse from approval analyzer and
        constructs a LangGraph Command object for resuming interrupted workflows.

        IMPORTANT: Uses original_interrupt_id (WITHOUT suffix) to match checkpoint format.
        Each interrupt gets its own entry in Command.resume with its response.

        Args:
            approval_response: Structured approval response from analyzer
            pending_interrupts: List of pending interrupt contexts

        Returns:
            Command object ready for execution

        Example (Parallel Interrupts):
            approval_response.responses = [
                {"type": "accept"},
                {"type": "edit", "args": {"price": 120.0}},
                {"type": "response", "args": "Not required"}
            ]
            pending_interrupts = [
                {"interrupt_id": "abc123_0", ...},  # Blue bottle
                {"interrupt_id": "abc123_1", ...},  # Pink bottle
                {"interrupt_id": "abc123_2", ...}   # Green bottle
            ]
            →
            Command(resume={
                "abc123_0": [{"type": "accept"}],
                "abc123_1": [{"type": "edit", "args": {...}}],
                "abc123_2": [{"type": "response", "args": "Not required"}]
            })
        """
        # Build Command.resume mapping each interrupt_id to its response
        from collections import defaultdict
        interrupt_responses = defaultdict(list)

        for idx, interrupt_info in enumerate(pending_interrupts):
            # Use original_interrupt_id (WITHOUT suffix) to match checkpoint format
            # Checkpoint stores base IDs: "abc123", "def456", etc. (no suffix)
            # Suffix is only used internally for unpacking list-valued interrupts
            interrupt_id_for_command = interrupt_info.get("original_interrupt_id", interrupt_info["interrupt_id"])

            response = approval_response.responses[idx]
            tool_name = interrupt_info.get("tool_name", "unknown")
            tool_args = interrupt_info.get("tool_args", {})

            # Format response based on type for HITL middleware compatibility
            if response.type == "edit":
                # HITL middleware expects: {"type": "edit", "args": {"action": "tool_name", "args": {...}}}
                # The "args" field should be an ActionRequest with action and args
                merged_args = {**tool_args, **response.args} if isinstance(response.args, dict) else tool_args
                hitl_response = {
                    "type": "edit",
                    "args": {
                        "action": tool_name,
                        "args": merged_args
                    }
                }
                logger.debug(
                    f"Built edit response for {interrupt_id_for_command}",
                    extra={
                        "tool_name": tool_name,
                        "edited_fields": list(response.args.keys()) if isinstance(response.args, dict) else [],
                    }
                )
            elif response.type == "accept":
                # Accept - HITL middleware expects {"type": "accept"}
                hitl_response = {"type": "accept"}
            elif response.type == "response":
                # Reject/clarification - HITL middleware expects {"type": "response", "args": "message"}
                hitl_response = {
                    "type": "response",
                    "args": response.args
                }
            else:
                # Unknown type - log warning and treat as accept
                logger.warning(
                    f"Unknown response type: {response.type}",
                    extra={"interrupt_id": interrupt_id_for_command}
                )
                hitl_response = {"type": "accept"}

            interrupt_responses[interrupt_id_for_command].append(hitl_response)

        logger.info(
            "Built Command from structured approval",
            extra={
                "total_responses": len(pending_interrupts),
                "interrupt_count": len(interrupt_responses),
                "interrupt_ids": list(interrupt_responses.keys()),
                "edit_count": sum(1 for resp in approval_response.responses if resp.type == "edit"),
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

        ✅ BATCH APPROVAL SUPPORT: Send ALL products in one batch to channel.

        DeepAgents wraps tool calls in action_request format:
        [{'action_request': {'action': 'tool_name', 'args': {actual_data}}}]

        For parallel tool calls (multiple products), we collect all Products
        and send them together for batch approval.

        Args:
            sender: Channel-specific sender ID
            thread_id: Conversation thread ID
            interrupt_value: Value from interrupt (may be wrapped by DeepAgents)
        """
        logger.debug(
            "Handling HITL interrupt",
            extra={
                "thread_id": thread_id,
                "interrupt_type": type(interrupt_value).__name__,
                "is_list": isinstance(interrupt_value, list),
                "length_if_list": len(interrupt_value) if isinstance(interrupt_value, list) else "N/A",
            }
        )

        try:
            from autifyme_agents.schemas.models import Product

            # Collect all products (for batch approval)
            products_to_approve: list[Product] = []

            if isinstance(interrupt_value, list) and len(interrupt_value) > 0:
                # Parallel tool calls - collect ALL products
                logger.info(
                    "Processing batch interrupt",
                    extra={"thread_id": thread_id, "action_count": len(interrupt_value)}
                )

                for idx, action in enumerate(interrupt_value):
                    if isinstance(action, dict) and "action_request" in action:
                        # DeepAgents format - extract clean args
                        action_request = action.get("action_request", {})
                        clean_value = action_request.get("args", {})
                        tool_name = action_request.get("action", "unknown")

                        logger.debug(
                            f"Unwrapping action {idx + 1} of {len(interrupt_value)}",
                            extra={
                                "thread_id": thread_id,
                                "tool_name": tool_name,
                                "product_name": clean_value.get("name", "unknown"),
                            }
                        )

                        # Convert to Product and add to batch
                        if isinstance(clean_value, dict):
                            draft = Product.model_validate(clean_value)
                            products_to_approve.append(draft)
                            logger.info(f"[DISPLAY ORDER] Product {idx + 1}: {draft.name}")

                # Send all products in batch
                if len(products_to_approve) > 0:
                    logger.info(
                        "Sending batch approval request",
                        extra={
                            "thread_id": thread_id,
                            "product_count": len(products_to_approve),
                            "product_names": [p.name for p in products_to_approve],
                        }
                    )

                    # Send batch approval - show ALL products at once
                    if len(products_to_approve) == 1:
                        # Single product - use standard approval request
                        self.channel.send_approval_request(sender, products_to_approve[0])
                    else:
                        # Multiple products - format as batch and send all together
                        self._send_batch_approval(sender, products_to_approve)

            # Handle single interrupt case
            elif isinstance(interrupt_value, dict):
                logger.info(
                    "Processing single interrupt",
                    extra={"thread_id": thread_id}
                )

                # Convert dict args to Product object for channel
                draft = Product.model_validate(interrupt_value)
                logger.debug(
                    "Converted single interrupt to Product",
                    extra={"thread_id": thread_id, "product_name": draft.name}
                )
                self.channel.send_approval_request(sender, draft)

            logger.info(
                "Interrupt(s) forwarded to user - awaiting response",
                extra={
                    "thread_id": thread_id,
                    "product_count": len(products_to_approve) if products_to_approve else 1,
                },
            )

        except Exception as exc:
            logger.exception("Failed to send interrupt to user", exc_info=exc, extra={"thread_id": thread_id})
            self.channel.send_error(sender, "processing", "I encountered an issue requesting your input.")

    def _send_batch_approval(self, sender: str, products: list[Any]) -> None:
        """Send batch approval request with ALL products displayed together.

        Args:
            sender: Channel-specific sender ID
            products: List of Product objects to approve

        Notes:
            This method formats multiple products into a single approval message
            so users can see and approve all products at once for batch workflows.
        """
        from autifyme_agents.schemas.models import Product

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

    def _extract_cataloging_result(self, messages: list[Any]) -> CatalogingResult | None:
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

    def _extract_ai_summary(self, messages: list[Any]) -> str | None:
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
