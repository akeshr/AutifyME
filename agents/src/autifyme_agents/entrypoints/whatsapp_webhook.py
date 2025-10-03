"""WhatsApp webhook entrypoint."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse

from autifyme_agents.core.config import settings
from autifyme_agents.workflows.whatsapp_cataloging_runner import WhatsAppCatalogingRunner

app = FastAPI()
logger = logging.getLogger(__name__)
runner = WhatsAppCatalogingRunner(enable_agent=True)

_EVENT_DUMP_DIR = Path("tmp/whatsapp_events")


def _persist_event(payload: dict[str, Any]) -> Path:
    _EVENT_DUMP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S%fZ")
    path = _EVENT_DUMP_DIR / f"event_{stamp}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("Persisted WhatsApp event to %s", path)
    return path


def _is_approval_message(text: str | None) -> bool:
    if not text:
        return False
    lowered = text.strip().lower()
    return lowered in {"approve", "reject"}


@app.get("/webhook")
async def verify(request: Request) -> Any:
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    challenge = params.get("hub.challenge")
    token = params.get("hub.verify_token")

    if mode == "subscribe" and challenge and token == settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
        return PlainTextResponse(challenge)

    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def receive(request: Request) -> Any:
    body = await request.json()
    event_path = _persist_event(body)
    logger.info("Incoming WhatsApp payload saved", extra={"event_path": str(event_path)})
    logger.debug("Incoming WhatsApp payload: %s", json.dumps(body))

    try:
        entry = body["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        messages = value.get("messages")

        if not messages:
            return {"status": "ignored"}

        message = messages[0]
        sender = message["from"]
        msg_type = message.get("type")
        text = message.get("text", {}).get("body")

        logger.info(
            "Processing WhatsApp message",
            extra={
                "sender": sender,
                "message_type": msg_type,
                "has_media": msg_type == "image",
                "event_path": str(event_path),
            },
        )

        if msg_type == "text" and _is_approval_message(text):
            runner.handle_approval(sender, text)
            return {"status": "approval_processed"}

        media_id = None
        if msg_type == "image":
            media_id = message["image"]["id"]

        runner.handle_message(sender, text, media_id)
        return {"status": "processed"}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to handle webhook: %s", exc, extra={"event_path": str(event_path)})
        raise HTTPException(status_code=500, detail="Internal error") from exc
