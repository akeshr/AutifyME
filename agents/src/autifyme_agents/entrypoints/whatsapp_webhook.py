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
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
from autifyme_agents.workflows.orchestration.runner import WorkflowRunner
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
_storage_adapter = None
_whatsapp_channel = None

def _get_runner():
    """Lazy initialization of WorkflowRunner for serverless deployment."""
    global _runner, _storage_adapter, _whatsapp_channel

    if _runner is None:
        logger.info("Initializing WorkflowRunner with WhatsApp channel...")
        try:
            # Create storage adapter
            _storage_adapter = SupabaseStorageClient()
            logger.info("Storage adapter initialized successfully")

            # Create channel adapter
            _whatsapp_channel = WhatsAppChannel()
            logger.info("WhatsApp channel adapter created")

            # Create generic workflow runner with WhatsApp channel
            _runner = WorkflowRunner(
                channel=_whatsapp_channel,
                storage=_storage_adapter,
            )
            logger.info("✅ WorkflowRunner initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize WorkflowRunner: {e}", exc_info=True)
            raise

    return _runner

_EVENT_DUMP_DIR = Path("/tmp/whatsapp_events")

# Idempotency tracking: LRU cache of processed message IDs to prevent duplicate processing
# when WhatsApp retries webhooks. In production, this should be persisted in the database
# with a TTL (e.g., 24 hours). For now, we use an in-memory cache with max 10,000 entries.
_MAX_PROCESSED_MESSAGES = 10_000
_processed_messages: OrderedDict[str, bool] = OrderedDict()


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


def _is_duplicate_message(message_id: str) -> bool:
    """Check if we've already processed this message ID (idempotency check).
    
    WhatsApp may retry webhook deliveries, and we need to ensure we don't
    process the same message multiple times. This uses an in-memory LRU cache.
    
    In production, this should be backed by a database table with a TTL
    (e.g., processed_messages table with 24h expiry) to survive server restarts.
    """
    return message_id in _processed_messages


def _mark_message_processed(message_id: str) -> None:
    """Mark a message ID as processed to prevent duplicate processing.
    
    Uses an LRU cache with max 10,000 entries to prevent memory leaks.
    When the cache is full, the oldest entries are automatically evicted.
    """
    if message_id in _processed_messages:
        # Move to end (mark as recently used)
        _processed_messages.move_to_end(message_id)
    else:
        _processed_messages[message_id] = True
        
        # Evict oldest entry if cache is full (LRU)
        if len(_processed_messages) > _MAX_PROCESSED_MESSAGES:
            _processed_messages.popitem(last=False)
            logger.debug(
                "Evicted oldest message from idempotency cache",
                extra={"cache_size": len(_processed_messages)},
            )


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
                    
                    # Check for duplicate processing using message_id
                    # (WhatsApp can retry webhooks, and we might get the same message twice)
                    if _is_duplicate_message(message_id):
                        logger.info(
                            "Skipping duplicate message",
                            extra={"message_id": message_id, "sender": sender, "event_path": str(event_path)},
                        )
                        continue
                    
                    text = message.get("text", {}).get("body")
                    
                    logger.info(
                        "Processing WhatsApp message",
                        extra={
                            "message_id": message_id,
                            "sender": sender,
                            "message_type": msg_type,
                            "has_media": msg_type == "image",
                            "timestamp": timestamp,
                            "event_path": str(event_path),
                        },
                    )

                    if msg_type == "text" and _is_approval_message(text):
                        _get_runner().handle_approval(sender, text)
                        _mark_message_processed(message_id)
                        continue

                    media_id = None
                    if msg_type == "image":
                        media_id = message.get("image", {}).get("id")

                    _get_runner().handle_message(sender, text, media_id)
                    _mark_message_processed(message_id)
        
        return {"status": "processed"}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to handle webhook: %s", exc, extra={"event_path": str(event_path)})
        raise HTTPException(status_code=500, detail="Internal error") from exc
