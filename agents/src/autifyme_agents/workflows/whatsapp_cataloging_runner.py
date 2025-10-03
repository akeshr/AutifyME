"""Workflow runner coordinating WhatsApp cataloging conversations."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional, Tuple

from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.types import Interrupt, Command
from langgraph.errors import GraphRecursionError
from langgraph.checkpoint.base import BaseCheckpointSaver

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.integrations.communication import WhatsAppClient, WhatsAppMediaClient
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from autifyme_agents.schemas.models import CatalogingResult, CompanyProfile
from autifyme_agents.schemas.agent_outputs import CatalogingToolOutput
from autifyme_agents.core.config import settings
from autifyme_agents.workflows.project_manager import create_project_manager

logger = logging.getLogger(__name__)


CATALOGING_PROMPT = "Please share the product details and photo so I can catalog it."  # Minimal triage response


class WhatsAppCatalogingRunner:
    """Coordinates the end-to-end WhatsApp cataloging workflow."""

    def __init__(
        self,
        *,
        storage: StorageInterface | None = None,
        checkpointer: BaseCheckpointSaver | None = None,
        whatsapp_client: WhatsAppClient | None = None,
        media_client: WhatsAppMediaClient | None = None,
        enable_agent: bool = True,
        recursion_limit: int | None = None,
    ) -> None:
        if storage is None:
            raise ValueError("storage adapter must implement StorageInterface and be provided by the entrypoint")
        self.storage = storage
        self.checkpointer = checkpointer
        self.whatsapp_client = whatsapp_client or WhatsAppClient()
        self.media_client = media_client or WhatsAppMediaClient()
        self.enable_agent = enable_agent
        self.recursion_limit = recursion_limit or settings.AGENT_RECURSION_LIMIT
        self.company_profile: CompanyProfile = self.storage.get_company_profile()
        self._last_pm_state: dict[str, Any] | None = None

    def _get_checkpointer(self) -> BaseCheckpointSaver:
        if self.checkpointer:
            return self.checkpointer
        return get_checkpointer()

    def _thread_id(self, sender: str) -> str:
        return f"whatsapp:{sender}"

    def _should_invoke_department(self, text: str | None, has_media: bool) -> bool:
        """Gate to avoid invoking the department on greetings/empty messages."""
        normalized = (text or "").strip().lower()
        if has_media:
            return True
        if not normalized:
            return False
        return normalized not in {"hi", "hello", "hey", "thanks", "thank you"}

    def handle_message(self, sender: str, text: str | None, media_id: str | None) -> None:
        normalized_text = (text or "").strip()
        has_media = media_id is not None

        if not self._should_invoke_department(normalized_text, has_media):
            logger.info(
                "Skipping department invocation for low-intent message",
                extra={"sender": sender, "text": normalized_text, "thread_id": self._thread_id(sender)},
            )
            self._safe_send_text(sender, CATALOGING_PROMPT)
            return

        thread_id = self._thread_id(sender)
        
        # Proactive Check: Only treat as abandonment if user sends a NEW cataloging request
        # (with media) while approval is pending. Text-only messages are treated as conversation
        # continuation (e.g., clarifications, edits) to preserve UX. The reactive recovery layer
        # will handle any unexpected INVALID_CHAT_HISTORY errors that slip through.
        existing_approval = self.storage.get_pending_approval(thread_id)
        if existing_approval and has_media:
            logger.info(
                "User sent NEW product (with media) while approval pending - treating as abandonment",
                extra={"thread_id": thread_id, "abandoned_interrupt_id": existing_approval.get("interrupt_id")},
            )
            # Clear the approval record
            self.storage.delete_pending_approval(thread_id)
            
            # Clear the checkpoint to remove orphaned AIMessage with tool_calls
            try:
                checkpointer_ctx = self._get_checkpointer()
                saver = checkpointer_ctx.__enter__() if hasattr(checkpointer_ctx, "__enter__") else checkpointer_ctx
                saver.delete_thread(thread_id)
                logger.info("Cleared checkpoint for fresh workflow", extra={"thread_id": thread_id})
                if hasattr(checkpointer_ctx, "__exit__"):
                    checkpointer_ctx.__exit__(None, None, None)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to clear checkpoint during abandonment, recovery will handle", exc_info=exc)
        elif existing_approval:
            logger.info(
                "User sent text-only message during approval - treating as conversation continuation",
                extra={"thread_id": thread_id, "pending_interrupt_id": existing_approval.get("interrupt_id")},
            )

        image_path: Path | None = None
        try:
            if media_id:
                image_path = self.media_client.download_media(media_id)
                logger.info(
                    "Media download succeeded",
                    extra={"sender": sender, "media_id": media_id, "path": str(image_path)},
                )

            payload = self._build_project_manager_payload(normalized_text, image_path)

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

            try:
                result, interruption = self._invoke_project_manager(payload, config)
                if interruption is not None:
                    self._handle_interrupt(sender, interruption, thread_id)
                    return
                self._handle_pm_completion(sender, result)
            except ValueError as exc:
                # Reactive Recovery: Safety net for unexpected edge cases (server crashes during
                # interrupt, race conditions, future bugs). This is "defense in depth" - the
                # proactive check handles known scenarios, this catches everything else.
                # Production best practice per AGENTS_DESIGN.md § 6 (Resilience & Safeguards).
                if "INVALID_CHAT_HISTORY" in str(exc) or "do not have a corresponding ToolMessage" in str(exc):
                    logger.warning(
                        "Detected orphaned tool calls in checkpoint - auto-recovery triggered",
                        extra={"thread_id": thread_id, "error": str(exc)[:200]},
                    )
                    # Clear both approval and checkpoint, then retry once
                    self.storage.delete_pending_approval(thread_id)
                    try:
                        checkpointer_ctx = self._get_checkpointer()
                        saver = checkpointer_ctx.__enter__() if hasattr(checkpointer_ctx, "__enter__") else checkpointer_ctx
                        saver.delete_thread(thread_id)
                        logger.info("Auto-recovery: cleared orphaned checkpoint, retrying", extra={"thread_id": thread_id})
                        if hasattr(checkpointer_ctx, "__exit__"):
                            checkpointer_ctx.__exit__(None, None, None)
                    except Exception as clear_exc:  # noqa: BLE001
                        logger.exception("Failed to clear checkpoint during auto-recovery", exc_info=clear_exc)
                        raise exc from clear_exc
                    
                    # Retry with clean state
                    result, interruption = self._invoke_project_manager(payload, config)
                    if interruption is not None:
                        self._handle_interrupt(sender, interruption, thread_id)
                        return
                    self._handle_pm_completion(sender, result)
                else:
                    raise
            except GraphRecursionError as exc:
                logger.exception("Project Manager recursion detected for %s", sender, exc_info=exc)
                self._safe_send_text(
                    sender,
                    "I'm having trouble finishing this task. A specialist will review and follow up.",
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Project Manager invocation failed for %s", sender, exc_info=exc)
                self._safe_send_text(
                    sender,
                    "I hit a processing error. Please try resending the details or wait for support.",
                )
        finally:
            if image_path and image_path.exists():
                image_path.unlink(missing_ok=True)

    def handle_approval(self, sender: str, decision: str) -> None:
        if not self.enable_agent:
            self._safe_send_text(
                sender,
                "Agent approval flow is temporarily disabled while we run diagnostics.",
            )
            return
        action = decision.strip().lower()
        if action not in {"approve", "reject"}:
            self._safe_send_text(sender, "Please reply with 'approve' or 'reject'.")
            return

        thread_id = self._thread_id(sender)
        
        # Retrieve pending approval from persistent storage
        pending_approval = self.storage.get_pending_approval(thread_id)
        
        if pending_approval is None:
            self._safe_send_text(
                sender,
                "No pending approval found for this thread. Please restart the cataloging request.",
            )
            return

        if action == "reject":
            self._safe_send_text(
                sender,
                "Understood. The draft will remain unsaved. Let me know if you'd like updates or a retry.",
            )
            self.storage.delete_pending_approval(thread_id)
            return

        # Handle approve
        interrupt_id = pending_approval.get("interrupt_id")
        tool_call = pending_approval.get("tool_call")
        draft_summary = pending_approval.get("draft_summary")
        ai_message = pending_approval.get("ai_message")
        
        if not interrupt_id or not tool_call:
            logger.warning("Approval resume missing context for %s", sender)
            self._safe_send_text(
                sender,
                "Approval context invalid. Please restart the cataloging request if needed.",
            )
            self.storage.delete_pending_approval(thread_id)
            return

        synthetic_tool_message = ToolMessage(
            content=draft_summary or "Approval granted.",
            tool_call_id=tool_call.get("id"),
            name=tool_call.get("name"),
        )

        command = Command(
            update={"messages": [synthetic_tool_message]},
            resume={
                interrupt_id: {
                    "type": "accept",
                    "args": None,
                }
            },
        )

        config = {
            "configurable": {
                "thread_id": thread_id,
                "company_id": "default",
            },
            "metadata": {
                "langsmith.thread_id": thread_id,
                "workflow": "cataloging",
            },
        }

        # Delete the approval record before resuming
        self.storage.delete_pending_approval(thread_id)

        result, interruption = self._invoke_project_manager(command, config)
        if interruption is not None:
            self._handle_interrupt(sender, interruption, thread_id)
        elif result is not None:
            self._handle_pm_completion(sender, result)
        else:
            logger.warning("No result returned while resuming approval for %s", sender)

    def _invoke_project_manager(
        self,
        payload: dict[str, Any],
        config: dict[str, Any],
    ) -> Tuple[Optional[dict[str, Any]], Optional[Interrupt]]:
        """Invoke Project Manager and handle native LangGraph interrupts.

        With interrupt_before=["tools"], LangGraph will:
        1. Let the agent emit tool calls (AIMessage with tool_calls)
        2. Pause execution and emit an __interrupt__ in the state
        3. Wait for approval/rejection via Command resumption
        4. Resume and execute the tool node (which synthesizes ToolMessage)

        This runner simply streams events and detects __interrupt__ naturally.
        No custom validation error parsing or manual ToolMessage synthesis needed.
        """
        checkpointer_ctx = self._get_checkpointer()
        saver = checkpointer_ctx.__enter__() if hasattr(checkpointer_ctx, "__enter__") else checkpointer_ctx

        project_manager = create_project_manager(
            self.company_profile,
            checkpointer=saver,
            storage=self.storage,
        )

        last_event: Optional[dict[str, Any]] = None
        interrupt_event: Optional[Interrupt] = None

        try:
            stream_config = dict(config)
            stream_config.setdefault("configurable", {})
            stream_config["configurable"].setdefault("remaining_steps", self.recursion_limit)

            # Stream in "values" mode to get full state snapshots.
            stream_input = payload
            if isinstance(payload, Command):
                stream_input = payload
            stream = project_manager.stream(stream_input, config=stream_config, stream_mode="values")
            for event in stream:
                if isinstance(event, dict):
                    last_event = event
                    if (event.get("messages") or []) and isinstance(event.get("messages"), list):
                        self._last_pm_state = event
                    self._log_stream_event_summary(last_event, config)

                    # Check for native LangGraph interrupt signal
                    if "__interrupt__" in event:
                        interrupts = event.get("__interrupt__") or []
                        if interrupts:
                            interrupt_event = interrupts[0]
                            logger.info(
                                "Native LangGraph interrupt detected",
                                extra={
                                    "thread_id": config.get("configurable", {}).get("thread_id"),
                                    "interrupt_count": len(interrupts),
                                    "interrupt_value_type": type(interrupt_event.value).__name__ if hasattr(interrupt_event, "value") else "N/A",
                                    "interrupt_value_keys": list(interrupt_event.value.keys()) if hasattr(interrupt_event, "value") and isinstance(interrupt_event.value, dict) else "N/A",
                                },
                            )
                            # Log the full interrupt structure for debugging
                            logger.debug(f"Full interrupt value: {interrupt_event.value if hasattr(interrupt_event, 'value') else 'N/A'}")
                            break
        finally:
            if hasattr(checkpointer_ctx, "__exit__"):
                checkpointer_ctx.__exit__(None, None, None)

        return last_event, interrupt_event

    def _log_stream_event_summary(self, event: dict[str, Any], config: dict[str, Any]) -> None:
        thread_id = config.get("configurable", {}).get("thread_id")
        messages = event.get("messages") or []
        last_message_type = None
        tool_previews: list[dict[str, Any]] = []
        last_message_preview = None
        
        if messages:
            last_message = messages[-1]
            last_message_type = getattr(last_message, "type", None)
            if not last_message_type and hasattr(last_message, "__class__"):
                last_message_type = last_message.__class__.__name__.replace("Message", "").lower()
            
            if last_message_type == "ai":
                tool_previews = self._summarize_tool_calls(getattr(last_message, "tool_calls", []) or [])
                # For AI messages without tool calls, show a preview of the content
                if not tool_previews:
                    content = getattr(last_message, "content", None)
                    if isinstance(content, str):
                        last_message_preview = content[:100]
            elif last_message_type == "tool":
                tool_previews = [
                    {
                        "id": getattr(last_message, "tool_call_id", None),
                        "name": getattr(last_message, "name", None),
                    }
                ]
                # Show tool response preview
                content = getattr(last_message, "content", None)
                if isinstance(content, str):
                    last_message_preview = content[:100]

        todos = event.get("todos") or []
        todos_preview = todos[-3:] if isinstance(todos, list) else None
        
        # Check if this event has an interrupt signal
        has_interrupt = "__interrupt__" in event

        logger.info(
            f"📊 PM Event #{len(messages)} | Type: {last_message_type or 'none'} | Tools: {len(tool_previews)} | Interrupt: {has_interrupt}",
            extra={
                "thread_id": thread_id,
                "message_count": len(messages),
                "last_message_type": last_message_type,
                "tool_calls": tool_previews,
                "todos_tail": todos_preview,
                "message_preview": last_message_preview,
                "has_interrupt": has_interrupt,
            },
        )

    @staticmethod
    def _summarize_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "id": call.get("id"),
                "name": call.get("name"),
            }
            for call in tool_calls
            if isinstance(call, dict)
        ]

    def _build_project_manager_payload(
        self,
        text: str,
        image_path: Path | None,
    ) -> dict[str, Any]:
        messages: list[HumanMessage] = [HumanMessage(content=text)]
        if image_path:
            messages.append(HumanMessage(content=f"[IMAGE_PATH]{image_path}"))
        return {"messages": messages}

    def _handle_pm_completion(self, sender: str, result: dict[str, Any]) -> None:
        if not result:
            logger.warning("Project Manager returned empty result for %s", sender)
            return

        messages = result.get("messages") or []
        if not messages:
            logger.warning("Project Manager produced no messages for %s", sender)
            return

        ai_message = self._find_last_ai_message(messages)
        structured = self._extract_cataloging_result(messages)
        if structured:
            status = "Success" if structured.success else "Failed"
            product_name = structured.product_name or "Unnamed product"
            summary_lines = [f"Cataloging {status}: {product_name}", structured.message]
            self._safe_send_text(sender, "\n".join(summary_lines))
            return

        summary = self._extract_ai_summary(messages)
        if summary:
            self._safe_send_text(sender, summary)
        else:
            logger.warning("Unable to derive completion summary for %s", sender)

    def _extract_cataloging_result(self, messages: list[dict[str, Any]]) -> CatalogingResult | None:
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
            except ValueError:
                logger.debug("Skipping non-conforming tool content: %s", content)
                continue
            return tool_output.result
        return None

    def _extract_ai_summary(self, messages: list[dict[str, Any]]) -> str | None:
        for message in reversed(messages):
            message_type = getattr(message, "type", None)
            if not message_type and hasattr(message, "__class__"):
                message_type = message.__class__.__name__.replace("Message", "").lower()
            if message_type != "ai":
                continue
            content = getattr(message, "content", None)
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = [
                    part.get("text")
                    for part in content
                    if isinstance(part, dict) and part.get("type") == "text"
                ]
                joined = "\n".join(filter(None, parts))
                return joined or None
        return None

    def _handle_interrupt(self, sender: str, interruption: Interrupt, thread_id: str) -> None:
        """Handle native LangGraph interrupt by extracting tool details and requesting approval.

        With interrupt_before=["tools"], the interrupt.value contains the pending tool calls.
        We inspect them to find save_product and send an approval request to the user.
        
        The interrupt context is persisted to Supabase to survive server restarts,
        honoring the Architecture-First state persistence principle (AGENTS_DESIGN.md § 6.2).
        """
        # The interrupt.value for interrupt_before typically contains a list of tool calls.
        # For deepagents + interrupt_before=["tools"], we expect the last AIMessage's tool_calls
        # to be available in the interrupt payload or in _last_pm_state.
        tool_calls = self._extract_tool_calls_from_interrupt(interruption)
        
        save_product_call = None
        for call in tool_calls:
            if call.get("name") == "save_product":
                save_product_call = call
                break
        
        if not save_product_call:
            logger.warning("Interrupt detected but no save_product tool call found for %s", sender)
            return

        tool_args = save_product_call.get("args", {})
        draft_summary = self._draft_summary_from_tool_args(tool_args)
        if not draft_summary:
            draft_summary = "Cataloging complete. Approve to save the product."

        interrupt_id = interruption.id or save_product_call.get("id") or sender
        
        # Get checkpoint_id from the last PM state for resumption
        checkpoint_id = self._last_pm_state.get("checkpoint_id", "unknown") if self._last_pm_state else "unknown"
        
        # Extract the AIMessage that initiated the tool call
        ai_message_data = None
        if self._last_pm_state:
            ai_msg = self._find_last_ai_message(self._last_pm_state.get("messages", []))
            if ai_msg:
                # Serialize the AIMessage for storage
                ai_message_data = {
                    "type": getattr(ai_msg, "type", "ai"),
                    "content": getattr(ai_msg, "content", ""),
                    "tool_calls": getattr(ai_msg, "tool_calls", []),
                }
        
        # Persist to Supabase for restart resilience
        try:
            self.storage.save_pending_approval(
                thread_id=thread_id,
                interrupt_id=interrupt_id,
                checkpoint_id=checkpoint_id,
                tool_call=save_product_call,
                draft_summary=draft_summary,
                ai_message=ai_message_data,
            )
            logger.info(
                "Persisted pending approval to storage",
                extra={"thread_id": thread_id, "interrupt_id": interrupt_id},
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to persist pending approval", exc_info=exc)
            self._safe_send_text(
                sender,
                "I encountered an issue saving the approval request. Please try again.",
            )
            return

        self._safe_send_text(
            sender,
            f"Approval needed:\n{draft_summary}\nReply 'approve' or 'reject'.",
        )

    def _extract_tool_calls_from_interrupt(self, interruption: Interrupt) -> list[dict[str, Any]]:
        """Extract tool calls from the interrupt payload or the last PM state.
        
        DeepAgents' interrupt_config triggers an interrupt when the PM decides to call
        a configured tool (e.g., save_product). The interrupt.value contains metadata
        about which tool is being called. The actual AIMessage with tool_calls is still
        in the stream state but hasn't been added to the final checkpoint yet.
        """
        payload = interruption.value or {}
        
        # DeepAgents interrupt payload structure: {"tool": "save_product", ...}
        # We need to extract the tool call from the last AIMessage in _last_pm_state
        if not self._last_pm_state:
            logger.debug("No _last_pm_state available to extract tool calls from interrupt")
            return []
        
        messages = self._last_pm_state.get("messages") or []
        # The last message should be an AIMessage with tool_calls
        for message in reversed(messages):
            message_type = getattr(message, "type", None)
            if not message_type and hasattr(message, "__class__"):
                message_type = message.__class__.__name__.replace("Message", "").lower()
            if message_type == "ai":
                tool_calls = getattr(message, "tool_calls", []) or []
                if tool_calls:
                    logger.debug(
                        "Extracted tool calls from last AIMessage",
                        extra={"tool_call_count": len(tool_calls), "tool_names": [tc.get("name") for tc in tool_calls]},
                    )
                    return tool_calls
        
        logger.warning("No AIMessage with tool_calls found in _last_pm_state during interrupt")
        return []

    def _find_last_ai_message(self, messages: list[Any]) -> Any | None:
        for message in reversed(messages):
            message_type = getattr(message, "type", None)
            if not message_type and hasattr(message, "__class__"):
                message_type = message.__class__.__name__.replace("Message", "").lower()
            if message_type == "ai":
                return message
        return None

    def _draft_summary_from_last_state(self) -> str | None:
        if not self._last_pm_state:
            return None
        messages = self._last_pm_state.get("messages") or []
        draft_result = self._extract_cataloging_result(messages)
        if not draft_result:
            return None
        if not draft_result.data or "draft" not in draft_result.data:
            return draft_result.message
        draft_payload = draft_result.data["draft"]
        name = draft_payload.get("name") or "Unnamed product"
        price = draft_payload.get("price")
        sizes = ", ".join(draft_payload.get("sizes") or [])
        description = draft_payload.get("description") or draft_result.message
        lines = [
            f"Product: {name}",
            f"Price: {price}" if price is not None else "Price: n/a",
            f"Sizes: {sizes}" if sizes else "Sizes: n/a",
            f"Description: {description}",
        ]
        return "\n".join(lines)

    def _draft_summary_from_tool_args(self, tool_args: dict[str, Any]) -> str | None:
        """Format a human-readable summary from save_product tool arguments."""
        if not isinstance(tool_args, dict):
            return None
        name = tool_args.get("name") or "Unnamed product"
        price = tool_args.get("price")
        sizes = tool_args.get("sizes")
        if isinstance(sizes, list):
            sizes_text = ", ".join(str(s) for s in sizes if s)
        else:
            sizes_text = None
        description = tool_args.get("description")
        lines = [f"Product: {name}"]
        lines.append(f"Price: {price}" if price is not None else "Price: n/a")
        lines.append(f"Sizes: {sizes_text}" if sizes_text else "Sizes: n/a")
        if description:
            lines.append(f"Description: {description}")
        return "\n".join(lines)

    def _safe_send_text(self, recipient: str, message: str, *, preview_url: bool = False) -> None:
        try:
            self.whatsapp_client.send_text(recipient, message, preview_url=preview_url)
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Failed to send WhatsApp message",
                extra={
                    "recipient": recipient,
                    "preview_url": preview_url,
                    "message_preview": message[:120],
                },
                exc_info=exc,
            )
