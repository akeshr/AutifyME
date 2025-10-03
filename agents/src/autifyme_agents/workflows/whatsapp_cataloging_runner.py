"""Workflow runner coordinating WhatsApp cataloging conversations."""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any, Optional, Tuple

from langchain_core.messages import HumanMessage
from langgraph.types import Interrupt
from langgraph.errors import GraphRecursionError
from langgraph.checkpoint.base import BaseCheckpointSaver

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.integrations.communication import WhatsAppClient, WhatsAppMediaClient
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from autifyme_agents.schemas.models import CatalogingResult, CompanyProfile
from autifyme_agents.schemas.agent_outputs import CatalogingToolOutput
from autifyme_agents.core.config import settings
from autifyme_agents.workflows.project_manager import create_project_manager
from autifyme_agents.tools.registry import get_interrupt_config

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
        self._interrupt_tool_names = set(get_interrupt_config().keys())

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
            self.whatsapp_client.send_text(sender, CATALOGING_PROMPT)
            return

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
                    "thread_id": self._thread_id(sender),
                    "company_id": "default",
                },
                "recursion_limit": self.recursion_limit,
            }

            try:
                result, interruption = self._invoke_project_manager(payload, config)
                if interruption is not None:
                    self._handle_interrupt(sender, interruption)
                    return
                self._handle_pm_completion(sender, result)
            except GraphRecursionError as exc:
                logger.exception("Project Manager recursion detected for %s", sender, exc_info=exc)
                self.whatsapp_client.send_text(
                    sender,
                    "I’m having trouble finishing this task. A specialist will review and follow up.",
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Project Manager invocation failed for %s", sender, exc_info=exc)
                self.whatsapp_client.send_text(
                    sender,
                    "I hit a processing error. Please try resending the details or wait for support.",
                )
        finally:
            if image_path and image_path.exists():
                image_path.unlink(missing_ok=True)

    def handle_approval(self, sender: str, decision: str) -> None:
        if not self.enable_agent:
            self.whatsapp_client.send_text(sender, "Agent approval flow is temporarily disabled while we run diagnostics.")
            return
        action = decision.strip().lower()
        if action not in {"approve", "reject"}:
            self.whatsapp_client.send_text(sender, "Please reply with 'approve' or 'reject'.")
            return

        config = {
            "configurable": {
                "thread_id": self._thread_id(sender),
                "company_id": "default",
            },
            "interrupt": {
                "tool": "save_product",
                "decision": action,
            },
        }

        payload = {"messages": []}
        result, interruption = self._invoke_project_manager(payload, config)
        if interruption is not None:
            self._handle_interrupt(sender, interruption)
        elif result is not None:
            self._handle_pm_completion(sender, result)
        else:
            logger.warning("No result returned while resuming approval for %s", sender)

    def _invoke_project_manager(
        self,
        payload: dict[str, Any],
        config: dict[str, Any],
    ) -> Tuple[Optional[dict[str, Any]], Optional[Interrupt]]:
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

            stream = project_manager.stream(payload, config=stream_config, stream_mode="values")
            while True:
                try:
                    event = next(stream)
                except StopIteration:
                    break
                except ValueError as err:
                    action, interrupt_event = self._handle_tool_validation_error(err)
                    logger.debug(
                        "Tool validation guard tripped",
                    extra={
                        "action": action,
                        "interrupt": bool(interrupt_event),
                        "thread_id": config.get("configurable", {}).get("thread_id"),
                    },
                    )
                    if action == "continue":
                        continue
                    if action == "interrupt":
                        break
                    raise
                if isinstance(event, dict) and "__interrupt__" in event:
                    interrupts = event.get("__interrupt__") or []
                    if interrupts:
                        interrupt_event = interrupts[0]
                    break
                if isinstance(event, dict):
                    last_event = event
                    self._last_pm_state = event
                    self._log_stream_event_summary(last_event, config)

                if interrupt_event is not None:
                    break

                pending_interrupt = self._detect_interrupt_from_event(last_event or {}, config)
                if pending_interrupt is not None:
                    logger.info(
                        "Interrupt inferred from tool call",
                    extra={
                        "tool": pending_interrupt.value.get("tool"),
                        "thread_id": config.get("configurable", {}).get("thread_id"),
                    },
                    )
                    interrupt_event = pending_interrupt
                    break

                if self._should_break_after_event(last_event or {}):
                    logger.debug(
                        "Stream break condition met",
                        extra={
                            "thread_id": config.get("configurable", {}).get("thread_id"),
                            "unmatched_calls": list(self._find_unmatched_tool_calls(last_event or {})),
                        },
                    )
                    break
        finally:
            if hasattr(checkpointer_ctx, "__exit__"):
                checkpointer_ctx.__exit__(None, None, None)

        return last_event, interrupt_event

    def _detect_interrupt_from_event(
        self,
        event: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> Optional[Interrupt]:
        if not event:
            return None
        messages = event.get("messages") or []
        if not messages:
            return None
        # Inspect messages in reverse to catch latest AI tool calls first.
        for message in reversed(messages):
            message_type = getattr(message, "type", None)
            if not message_type and hasattr(message, "__class__"):
                message_type = message.__class__.__name__.replace("Message", "").lower()
            if message_type != "ai":
                continue
            tool_calls = getattr(message, "tool_calls", None) or []
            for call in tool_calls:
                tool_name = call.get("name") if isinstance(call, dict) else None
                if tool_name != "save_product":
                    continue
                logger.info(
                    "save_product tool call detected in stream",
                    extra={
                        "thread_id": (config or {}).get("configurable", {}).get("thread_id"),
                        "tool_call_id": call.get("id"),
                    },
                )
                interrupt_payload = {
                    "tool": tool_name,
                    "args": call.get("args", {}),
                    "message": "Approval required before executing tool.",
                }
                interrupt_id = call.get("id", tool_name)
                return Interrupt(value=interrupt_payload, id=interrupt_id)
        return None

    def _handle_tool_validation_error(
        self,
        error: ValueError,
    ) -> tuple[str, Optional[Interrupt]]:
        message = str(error)
        marker = "Here are the first few of those tool calls:"
        if marker not in message:
            return "raise", None
        start = message.find("[{", message.find(marker))
        end = message.find("}]", start)
        if start == -1 or end == -1:
            return "raise", None
        try:
            tool_calls = ast.literal_eval(message[start : end + 2])
        except (SyntaxError, ValueError):
            return "raise", None
        if not tool_calls:
            return "raise", None

        tool_call = tool_calls[0]
        tool_name = tool_call.get("name")
        if not tool_name:
            return "raise", None

        if tool_name == "write_todos":
            return "continue", None

        if tool_name == "get_company_profile":
            return "continue", None

        if tool_name in self._interrupt_tool_names:
            return "interrupt", Interrupt(
                value={
                    "tool": tool_name,
                    "args": tool_call.get("args", {}) or {},
                    "message": "Approval required before executing tool.",
                },
                id=tool_call.get("id", tool_name),
            )

        return "raise", None

    def _last_message_is_tool_message(self, event: dict[str, Any]) -> bool:
        messages = event.get("messages") or []
        if not messages:
            return False
        last_message = messages[-1]
        return getattr(last_message, "type", None) == "tool"

    def _find_unmatched_tool_calls(self, event: dict[str, Any]) -> set[str]:
        messages = event.get("messages") or []
        requested: set[str] = set()
        responded: set[str] = set()
        for message in messages:
            message_type = getattr(message, "type", None)
            if not message_type and hasattr(message, "__class__"):
                message_type = message.__class__.__name__.replace("Message", "").lower()
            if message_type == "ai":
                for call in getattr(message, "tool_calls", []) or []:
                    call_id = call.get("id")
                    if call_id:
                        requested.add(call_id)
            elif message_type == "tool":
                tool_call_id = getattr(message, "tool_call_id", None)
                if tool_call_id:
                    responded.add(tool_call_id)
        return requested - responded

    def _should_break_after_event(self, event: dict[str, Any]) -> bool:
        if not event:
            return False
        unmatched_calls = self._find_unmatched_tool_calls(event)
        # Ignore DeepAgents planning helpers that resolve immediately.
        unmatched_calls = {
            call_id
            for call_id in unmatched_calls
            if not self._is_planning_tool_response(event, call_id)
        }
        return not unmatched_calls and self._last_message_is_tool_message(event)

    def _is_planning_tool_response(self, event: dict[str, Any], call_id: str) -> bool:
        messages = event.get("messages") or []
        for message in messages:
            message_type = getattr(message, "type", None)
            if not message_type and hasattr(message, "__class__"):
                message_type = message.__class__.__name__.replace("Message", "").lower()
            if message_type != "ai":
                continue
            for call in getattr(message, "tool_calls", []) or []:
                if call.get("id") == call_id and call.get("name") == "write_todos":
                    return True
        return False

    def _log_stream_event_summary(self, event: dict[str, Any], config: dict[str, Any]) -> None:
        if not logger.isEnabledFor(logging.DEBUG):
            return

        thread_id = config.get("configurable", {}).get("thread_id")
        messages = event.get("messages") or []
        last_message_type = None
        tool_previews: list[dict[str, Any]] = []
        if messages:
            last_message = messages[-1]
            last_message_type = getattr(last_message, "type", None)
            if not last_message_type and hasattr(last_message, "__class__"):
                last_message_type = last_message.__class__.__name__.replace("Message", "").lower()
            if last_message_type == "ai":
                tool_previews = self._summarize_tool_calls(getattr(last_message, "tool_calls", []) or [])
            elif last_message_type == "tool":
                tool_previews = [
                    {
                        "id": getattr(last_message, "tool_call_id", None),
                        "name": getattr(last_message, "name", None),
                    }
                ]

        todos = event.get("todos") or []
        todos_preview = todos[-3:] if isinstance(todos, list) else None

        logger.debug(
            "PM stream event",
            extra={
                "thread_id": thread_id,
                "message_count": len(messages),
                "last_message_type": last_message_type,
                "tool_calls": tool_previews,
                "todos_tail": todos_preview,
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

        structured = self._extract_cataloging_result(messages)
        if structured:
            status = "Success" if structured.success else "Failed"
            product_name = structured.product_name or "Unnamed product"
            summary_lines = [f"Cataloging {status}: {product_name}", structured.message]
            self.whatsapp_client.send_text(sender, "\n".join(summary_lines))
            return

        summary = self._extract_ai_summary(messages)
        if summary:
            self.whatsapp_client.send_text(sender, summary)
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

    def _handle_interrupt(self, sender: str, interruption: Interrupt) -> None:
        payload = interruption.value or {}
        tool_name = payload.get("tool")
        if tool_name != "save_product":
            logger.warning("Received unsupported interrupt from tool %s", tool_name)
            return

        draft_summary = self._draft_summary_from_last_state()
        if not draft_summary:
            draft_summary = self._draft_summary_from_payload(payload)
        if not draft_summary:
            logger.warning("No draft available to include in approval message for %s", sender)
            draft_text = "Cataloging complete. Approve to save the product."
        else:
            draft_text = draft_summary

        message = payload.get("message") or draft_text
        self.whatsapp_client.send_text(
            sender,
            f"Approval needed:\n{message}\nReply 'approve' or 'reject'.",
        )

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

    def _draft_summary_from_payload(self, payload: dict[str, Any]) -> str | None:
        tool_args = payload.get("args")
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
