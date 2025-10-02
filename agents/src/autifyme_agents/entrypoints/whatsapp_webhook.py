"""WhatsApp webhook entrypoint."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import FastAPI, Request, HTTPException

from autifyme_agents.core.config import settings
from autifyme_agents.workflows.whatsapp_cataloging_runner import WhatsAppCatalogingRunner

app = FastAPI()
logger = logging.getLogger(__name__)
runner = WhatsAppCatalogingRunner()


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
        return int(challenge)

    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def receive(request: Request) -> Any:
    body = await request.json()
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

        if msg_type == "text" and _is_approval_message(text):
            runner.handle_approval(sender, text)
            return {"status": "approval_processed"}

        media_id = None
        if msg_type == "image":
            media_id = message["image"]["id"]

        runner.handle_message(sender, text, media_id)
        return {"status": "processed"}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to handle webhook: %s", exc)
        raise HTTPException(status_code=500, detail="Internal error") from exc
