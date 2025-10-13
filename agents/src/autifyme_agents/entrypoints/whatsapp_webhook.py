"""WhatsApp webhook entrypoint with comprehensive logging."""

from __future__ import annotations

import json
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse, RedirectResponse

from autifyme_agents.core.config import settings
from autifyme_agents.core.logging_config import setup_logging, get_logger
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.integrations.storage.storage_factory import get_storage
from autifyme_agents.integrations.storage.idempotency import IdempotencyChecker
from autifyme_agents.workflows.orchestration.runner_v2 import WorkflowRunner
from autifyme_agents.workflows.channels.whatsapp.adapter import WhatsAppChannel

# Initialize logging for serverless environment
try:
    setup_logging(level="INFO", enable_file_logging=False)
except Exception as e:
    # Fallback to basic logging if setup fails
    import logging
    logging.basicConfig(level=logging.INFO)
    logging.warning(f"Failed to setup structured logging: {e}")
logger = get_logger(__name__)

app = FastAPI()

# Webhook will be initialized lazily on first request
logger.info("AutifyME WhatsApp webhook serverless function loaded")


@app.get("/")
def read_root():
    """Root endpoint to confirm the service is running."""
    return {"status": "ok", "service": "AutifyME WhatsApp Webhook"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Redirects to the static vercel.svg in the public directory."""
    return RedirectResponse("/vercel.svg", status_code=307)


# Lazy initialization for serverless deployment
_runner = None
_storage: StorageInterface | None = None
_whatsapp_channel = None
_idempotency_checker = None

def _get_runner():
    """Lazy initialization of WorkflowRunner for serverless deployment."""
    global _runner, _storage, _whatsapp_channel, _idempotency_checker

    if _runner is None:
        logger.info("Initializing WorkflowRunner with WhatsApp channel...")
        try:
            # Get storage adapter via factory (hexagonal architecture - depend on port)
            _storage = get_storage()
            logger.info("Storage adapter initialized successfully")

            # Create idempotency checker (DB-backed)
            _idempotency_checker = IdempotencyChecker(_storage)
            logger.info("Idempotency checker initialized")

            # Create channel adapter
            _whatsapp_channel = WhatsAppChannel()
            logger.info("WhatsApp channel adapter created")

            # Create generic workflow runner with WhatsApp channel
            _runner = WorkflowRunner(
                channel=_whatsapp_channel,
                storage=_storage,
            )
            logger.info("✅ WorkflowRunner initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize WorkflowRunner: {e}", exc_info=True)
            raise

    return _runner

_EVENT_DUMP_DIR = Path("/tmp/whatsapp_events")


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


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for load balancers and monitoring."""
    return {"status": "healthy", "service": "autifyme-webhook"}


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
    logger.debug(
        "Incoming WhatsApp payload keys",
        extra={
            "entry_count": len(body.get("entry", [])),
            "top_level_keys": list(body.keys()),
        },
    )

    try:
        # WhatsApp can send multiple entries in one payload
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                # WhatsApp sends different event types:
                # - "messages": incoming messages from users (PROCESS THESE)
                # - "statuses": delivery/read receipts for outbound messages (IGNORE)
                # - Other metadata events (IGNORE)
                
                # Only process if this is a message event (not status update)
                messages = value.get("messages")
                if not messages:
                    # This is likely a status update or other event type
                    statuses = value.get("statuses")
                    if statuses:
                        logger.debug(
                            "Ignoring status update event",
                            extra={"status_count": len(statuses), "event_path": str(event_path)},
                        )
                    else:
                        logger.debug(
                            "Ignoring non-message event",
                            extra={"value_keys": list(value.keys()), "event_path": str(event_path)},
                        )
                    continue

                # Process each message (usually just one, but iterate for safety)
                for message in messages:
                    message_id = message.get("id")
                    sender = message.get("from")
                    msg_type = message.get("type")
                    timestamp = message.get("timestamp")
                    
                    # Skip if essential fields are missing
                    if not message_id or not sender:
                        logger.warning(
                            "Skipping message with missing id or sender",
                            extra={"message": message, "event_path": str(event_path)},
                        )
                        continue

                    # Check for duplicate processing using message_id (DB-backed idempotency)
                    # WhatsApp can retry webhooks, and we need to ensure we don't
                    # process the same message multiple times. Uses database to survive restarts.
                    thread_id = _whatsapp_channel.format_thread_id(sender) if _whatsapp_channel else f"whatsapp:{sender}"
                    if _idempotency_checker and _idempotency_checker.is_processed_and_mark(
                        message_id=message_id,
                        sender_id=sender,
                        thread_id=thread_id,
                        received_at=datetime.fromtimestamp(int(timestamp)),
                    ):
                        logger.info(
                            "Skipping duplicate message (DB idempotency)",
                            extra={"message_id": message_id, "sender": sender, "event_path": str(event_path)},
                        )
                        continue

                    # Extract text and media based on message type
                    # WhatsApp API structure varies by type:
                    # - text: {"text": {"body": "..."}}
                    # - image: {"image": {"id": "...", "caption": "..."}}
                    # - video: {"video": {"id": "...", "caption": "..."}}
                    # - document: {"document": {"id": "...", "caption": "...", "filename": "..."}}
                    # - audio/voice: {"audio|voice": {"id": "..."}} (no caption)
                    text = None
                    media_id = None

                    if msg_type == "text":
                        text = message.get("text", {}).get("body")
                    elif msg_type == "image":
                        media_obj = message.get("image", {})
                        media_id = media_obj.get("id")
                        text = media_obj.get("caption")  # Extract caption
                    elif msg_type == "video":
                        media_obj = message.get("video", {})
                        media_id = media_obj.get("id")
                        text = media_obj.get("caption")  # Extract caption
                    elif msg_type == "document":
                        media_obj = message.get("document", {})
                        media_id = media_obj.get("id")
                        text = media_obj.get("caption")  # Extract caption
                    elif msg_type in ("audio", "voice"):
                        media_obj = message.get(msg_type, {})
                        media_id = media_obj.get("id")
                        # Audio/voice don't have captions

                    logger.info(
                        "Processing WhatsApp message",
                        extra={
                            "message_id": message_id,
                            "sender": sender,
                            "message_type": msg_type,
                            "has_media": media_id is not None,
                            "has_text": text is not None,
                            "has_caption": media_id is not None and text is not None,
                            "timestamp": timestamp,
                            "event_path": str(event_path),
                        },
                    )

                    # Handle approval messages (text only)
                    if msg_type == "text" and _is_approval_message(text):
                        try:
                            _get_runner().handle_approval(sender, text)
                        except GeneratorExit:
                            # GeneratorExit during approval resumption
                            # Message already marked as processed above for idempotency
                            logger.warning(
                                "Approval workflow streaming timed out (GeneratorExit)",
                                extra={
                                    "message_id": message_id,
                                    "sender": sender,
                                    "event_path": str(event_path)
                                },
                            )
                            continue
                        except Exception as approval_exc:
                            # Message already marked as processed above for idempotency
                            logger.exception(
                                "Approval processing failed",
                                extra={
                                    "message_id": message_id,
                                    "sender": sender,
                                    "event_path": str(event_path),
                                    "error_type": type(approval_exc).__name__
                                },
                            )
                        continue

                    try:
                        _get_runner().handle_message(sender, text, media_id)
                    except GeneratorExit:
                        # GeneratorExit occurs when workflow streaming times out
                        # Message already marked as processed above for idempotency
                        # This prevents WhatsApp retries from creating duplicate threads
                        logger.warning(
                            "Workflow streaming timed out (GeneratorExit)",
                            extra={
                                "message_id": message_id,
                                "sender": sender,
                                "event_path": str(event_path)
                            },
                        )
                        continue
                    except Exception as workflow_exc:
                        # Message already marked as processed above for idempotency
                        logger.exception(
                            "Workflow execution failed",
                            extra={
                                "message_id": message_id,
                                "sender": sender,
                                "event_path": str(event_path),
                                "error_type": type(workflow_exc).__name__
                            },
                        )
                        # Continue processing other messages in the payload
                        continue

        return {"status": "processed"}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to handle webhook: %s", exc, extra={"event_path": str(event_path)})
        raise HTTPException(status_code=500, detail="Internal error") from exc
