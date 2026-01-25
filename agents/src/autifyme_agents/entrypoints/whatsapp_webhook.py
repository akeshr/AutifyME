"""WhatsApp webhook entrypoint with comprehensive logging."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from autifyme_agents.core.config import configure_deepagents, settings
from autifyme_agents.core.logging_config import get_logger, setup_logging
from autifyme_agents.core.message_batcher import MessageBatcher
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.integrations.storage.storage_factory import get_storage
from autifyme_agents.workflows.channels.whatsapp.adapter import WhatsAppChannel
from autifyme_agents.workflows.handlers.write_intent_handler import WriteIntentHandler
from autifyme_agents.workflows.orchestration.runner import WorkflowRunner

# Initialize logging for serverless environment
try:
    setup_logging(level="DEBUG", enable_file_logging=False)
except Exception as e:
    # Fallback to basic logging if setup fails
    import logging

    logging.basicConfig(level=logging.INFO)
    logging.warning(f"Failed to setup structured logging: {e}")
logger = get_logger(__name__)

# Configure DeepAgents before any agents are created
configure_deepagents()

app = FastAPI()

# Webhook will be initialized lazily on first request
logger.info("AutifyME WhatsApp webhook serverless function loaded")


# ============================================================================
# Startup & Shutdown Events
# ============================================================================


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize services and recover orphaned batches on startup.

    Handles messages that were queued but never processed due to
    server crash or restart before debounce timer fired.
    """
    global _message_batcher

    logger.info("WhatsApp webhook starting up")

    try:
        # Initialize dependencies (forward references resolved at runtime)
        storage = get_storage_dependency()
        channel = get_channel_dependency()
        workflow_handler = WriteIntentHandler(channel=channel)

        # Initialize batcher singleton
        if _message_batcher is None:
            logger.info("Initializing MessageBatcher singleton on startup")
            _message_batcher = MessageBatcher(storage=storage)

        # Create runner for recovery
        runner = WorkflowRunner(
            channel=channel,
            storage=storage,
            workflow_handler=workflow_handler,
        )

        # Recover any orphaned batches from previous server instance
        recovered = await _message_batcher.recover_orphaned_batches(runner)
        if recovered > 0:
            logger.info(
                "Recovered orphaned messages on startup",
                extra={"recovered_count": recovered},
            )
    except Exception:
        # Non-fatal: recovery failure shouldn't prevent startup
        logger.exception("Orphaned batch recovery failed on startup")

    logger.info("WhatsApp webhook startup complete")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Gracefully shutdown services.

    Background tasks may still be running - they'll either complete or
    leave messages in DB for orphan recovery on next startup.
    """
    logger.info("WhatsApp webhook shutdown complete")


# ============================================================================
# FastAPI Dependencies (Dependency Injection)
# ============================================================================
# These functions provide singleton instances for serverless deployment.
# FastAPI automatically manages dependency lifecycle and injection.


@lru_cache(maxsize=1)
def get_storage_dependency() -> StorageInterface:
    """Get singleton storage adapter for dependency injection.

    Returns:
        StorageInterface implementation (singleton via lru_cache)
    """
    logger.info("Initializing storage adapter")
    storage = get_storage()
    logger.info("Storage adapter initialized successfully")
    return storage


@lru_cache(maxsize=1)
def get_channel_dependency() -> WhatsAppChannel:
    """Get singleton WhatsApp channel for dependency injection.

    Returns:
        WhatsAppChannel instance (singleton via lru_cache)
    """
    logger.info("Creating WhatsApp channel adapter")
    channel = WhatsAppChannel()
    logger.info("WhatsApp channel adapter created")
    return channel


def get_workflow_handler(
    channel: WhatsAppChannel = Depends(get_channel_dependency),  # noqa: B008
) -> WriteIntentHandler:
    """Get workflow handler with injected channel.

    Args:
        channel: WhatsApp channel (injected by FastAPI)

    Returns:
        WriteIntentHandler instance
    """
    return WriteIntentHandler(channel=channel)


def get_runner(
    storage: StorageInterface = Depends(get_storage_dependency),  # noqa: B008
    channel: WhatsAppChannel = Depends(get_channel_dependency),  # noqa: B008
    workflow_handler: WriteIntentHandler = Depends(get_workflow_handler),  # noqa: B008
) -> WorkflowRunner:
    """Get workflow runner with all dependencies injected.

    Args:
        storage: Storage adapter (injected by FastAPI)
        channel: WhatsApp channel (injected by FastAPI)
        workflow_handler: WriteIntent workflow handler (injected by FastAPI)

    Returns:
        WorkflowRunner instance with all dependencies
    """
    logger.debug("Creating WorkflowRunner with injected dependencies")
    return WorkflowRunner(
        channel=channel,
        storage=storage,
        workflow_handler=workflow_handler,
    )


# Global batcher instance (singleton for timer management)
_message_batcher: MessageBatcher | None = None


def get_batcher_dependency(
    storage: StorageInterface = Depends(get_storage_dependency),  # noqa: B008
) -> MessageBatcher:
    """Get singleton MessageBatcher for Smart Skip debouncing.

    Uses module-level singleton to preserve in-memory timer state
    across requests (essential for debounce functionality).

    Args:
        storage: Storage adapter (injected by FastAPI)

    Returns:
        MessageBatcher singleton instance
    """
    global _message_batcher
    if _message_batcher is None:
        logger.info("Initializing MessageBatcher singleton")
        _message_batcher = MessageBatcher(storage=storage)
    return _message_batcher


@app.get("/")
def read_root() -> dict[str, str]:
    """Root endpoint to confirm the service is running."""
    return {"status": "ok", "service": "AutifyME WhatsApp Webhook"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> RedirectResponse:
    """Redirects to the static vercel.svg in the public directory."""
    return RedirectResponse("/vercel.svg", status_code=307)


_EVENT_DUMP_DIR = Path("/tmp/whatsapp_events")


def _persist_event(payload: dict[str, Any]) -> Path:
    _EVENT_DUMP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S%fZ")
    path = _EVENT_DUMP_DIR / f"event_{stamp}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("Persisted WhatsApp event to %s", path)
    return path


async def _process_message_async(
    runner: WorkflowRunner,
    sender: str,
    text: str | None,
    media_id: str | None,
    sender_name: str | None,
    message_id: str,
    event_path: Path,
) -> None:
    """Process workflow message asynchronously in background.

    This function runs in a FastAPI background task to decouple webhook
    acknowledgment (200 OK) from workflow processing. This ensures WhatsApp
    receives a response within their timeout window (~5 seconds) even when
    workflows take longer (e.g., image analysis, 8+ products).

    Phase 1 Typing Indicator:
    - Sends typing indicator once at start (25s duration or until message sent)
    - Provides immediate feedback that bot is processing
    - No auto-refresh in Phase 1 (future: Phase 2 for workflows >25s)

    Args:
        runner: Workflow runner instance
        sender: WhatsApp sender phone number
        text: Message text (optional)
        media_id: Media attachment ID (optional)
        sender_name: User's display name (optional)
        message_id: WhatsApp message ID (for logging)
        event_path: Path to persisted event JSON (for logging)
    """
    try:
        logger.info(
            "Background workflow processing started",
            extra={
                "message_id": message_id,
                "sender": sender,
                "has_media": media_id is not None,
                "has_text": text is not None,
            },
        )

        # Send typing indicator (Phase 1: single call, lasts 25s or until message sent)
        # WhatsApp API: marks message as read + shows "typing..." for 25s
        try:
            # Cast to WhatsAppChannel to access WhatsApp-specific client methods
            whatsapp_channel = cast(WhatsAppChannel, runner.channel)
            whatsapp_channel.client.send_typing_indicator(message_id)
            logger.debug(
                "Typing indicator sent (message marked as read)",
                extra={"message_id": message_id, "sender": sender},
            )
        except Exception as typing_exc:
            # Non-critical: continue processing even if typing indicator fails
            logger.warning(
                "Failed to send typing indicator (continuing with workflow)",
                exc_info=typing_exc,
                extra={"message_id": message_id, "sender": sender},
            )

        # Process workflow (may take >5 seconds for complex catalogs)
        # Typing indicator automatically stops when workflow sends response message
        await runner.handle_message(sender, text, media_id, sender_name=sender_name)

        logger.info(
            "Background workflow processing completed",
            extra={"message_id": message_id, "sender": sender},
        )

    except GeneratorExit:
        # GeneratorExit occurs when workflow streaming times out
        logger.warning(
            "Workflow streaming timed out (GeneratorExit) in background task",
            extra={"message_id": message_id, "sender": sender, "event_path": str(event_path)},
        )

    except Exception as workflow_exc:
        logger.exception(
            "Background workflow execution failed",
            exc_info=workflow_exc,
            extra={
                "message_id": message_id,
                "sender": sender,
                "error_type": type(workflow_exc).__name__,
                "event_path": str(event_path),
            },
        )
        # Don't raise - background task failures are logged but don't affect webhook response


async def _process_batch_after_delay(
    batcher: MessageBatcher,
    sender: str,
    runner: WorkflowRunner,
) -> None:
    """Wait for debounce window, then process batch.

    Each queued message starts this as a background task. The task:
    1. Waits the debounce window (3 seconds)
    2. Checks if messages are still pending for this sender
    3. If yes, atomically fetches and processes them

    Multiple concurrent tasks are safe - atomic fetch_and_clear ensures
    only one task actually processes the batch.
    """
    try:
        processed = await batcher.process_after_delay(sender, runner)
        if processed:
            logger.info(
                "Background batch processing completed",
                extra={"sender": sender},
            )
    except Exception as batch_exc:
        logger.error(
            "Background batch processing failed",
            exc_info=batch_exc,
            extra={"sender": sender, "error_type": type(batch_exc).__name__},
        )
        # Don't raise - background task failures are logged but don't affect webhook response


# REMOVED: _is_approval_message() helper
# Runner uses native LangGraph patterns - ALL messages go through handle_message()
# Runner automatically detects pending interrupts via pm.get_state() and invokes approval_analyzer


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
async def receive(
    request: Request,
    background_tasks: BackgroundTasks,
    runner: WorkflowRunner = Depends(get_runner),  # noqa: B008
    storage: StorageInterface = Depends(get_storage_dependency),  # noqa: B008
    batcher: MessageBatcher = Depends(get_batcher_dependency),  # noqa: B008
) -> Any:
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

                # Extract sender profile information for personalization
                # WhatsApp sends contacts array with profile name
                contacts = value.get("contacts", [])
                sender_name = None
                if contacts and len(contacts) > 0:
                    profile = contacts[0].get("profile", {})
                    sender_name = profile.get("name")
                    logger.debug(
                        "Extracted sender profile name",
                        extra={"sender_name": sender_name, "event_path": str(event_path)},
                    )
                else:
                    logger.warning(
                        "No contacts array in WhatsApp payload - personalization unavailable",
                        extra={"value_keys": list(value.keys()), "event_path": str(event_path)},
                    )

                # Process each message (usually just one, but iterate for safety)
                for message in messages:
                    message_id = message.get("id")
                    sender = message.get("from")
                    msg_type = message.get("type")
                    timestamp = message.get("timestamp")

                    # Generate trace ID for this message's journey through the system
                    trace_id = f"trace_{uuid.uuid4().hex[:8]}"

                    # Log raw message payload for debugging
                    logger.info(
                        f"TRACE[{trace_id}] RAW_PAYLOAD: WhatsApp message received",
                        extra={
                            "trace_id": trace_id,
                            "raw_message": message,
                            "message_id": message_id,
                            "sender": sender,
                            "msg_type": msg_type,
                            "timestamp": timestamp,
                            "message_keys": list(message.keys()),
                            "event_path": str(event_path),
                        },
                    )

                    # Skip if essential fields are missing
                    if not message_id or not sender:
                        logger.warning(
                            f"TRACE[{trace_id}] SKIP: Missing id or sender",
                            extra={
                                "trace_id": trace_id,
                                "whatsapp_message": message,
                                "event_path": str(event_path),
                            },
                        )
                        continue

                    # Validate message type is supported
                    # WhatsApp sends "unsupported" for message types not enabled on the account
                    # (stickers, locations, contacts, reactions, etc.)
                    supported_message_types = {
                        "text",
                        "image",
                        "video",
                        "document",
                        "audio",
                        "voice",
                    }
                    if msg_type not in supported_message_types:
                        logger.warning(
                            f"TRACE[{trace_id}] SKIP: Unsupported message type '{msg_type}'",
                            extra={
                                "trace_id": trace_id,
                                "msg_type": msg_type,
                                "supported_types": list(supported_message_types),
                                "raw_message": message,
                                "message_id": message_id,
                                "sender": sender,
                                "event_path": str(event_path),
                            },
                        )
                        continue

                    # Check for duplicate processing using message_id (DB-backed idempotency)
                    # WhatsApp can retry webhooks, and we need to ensure we don't
                    # process the same message multiple times. Uses database to survive restarts.
                    # Storage adapter handles atomic check-and-mark via port (no concrete adapter leakage)
                    thread_id = runner.channel.format_thread_id(sender)
                    logger.info(
                        f"TRACE[{trace_id}] IDEMPOTENCY_CHECK: Checking duplicate for message_id",
                        extra={
                            "trace_id": trace_id,
                            "message_id": message_id,
                            "thread_id": thread_id,
                            "sender": sender,
                        },
                    )
                    if storage.check_and_mark_message_processed(
                        message_id=message_id,
                        sender_id=sender,
                        thread_id=thread_id,
                        received_at=datetime.fromtimestamp(int(timestamp)),
                    ):
                        logger.info(
                            f"TRACE[{trace_id}] SKIP: Duplicate message (already processed)",
                            extra={
                                "trace_id": trace_id,
                                "message_id": message_id,
                                "sender": sender,
                                "event_path": str(event_path),
                            },
                        )
                        continue
                    logger.info(
                        f"TRACE[{trace_id}] IDEMPOTENCY_CHECK: New message, marked as processing",
                        extra={"trace_id": trace_id, "message_id": message_id},
                    )

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

                    # Skip empty text messages (reactions, read receipts, etc.)
                    # These have msg_type="text" but no actual body content
                    if msg_type == "text" and not (text and text.strip()):
                        logger.debug(
                            "Skipping empty text message",
                            extra={"message_id": message_id, "sender": sender},
                        )
                        continue

                    logger.info(
                        "Processing WhatsApp message",
                        extra={
                            "message_id": message_id,
                            "sender": sender,
                            "sender_name": sender_name,
                            "message_type": msg_type,
                            "has_media": media_id is not None,
                            "has_text": text is not None,
                            "has_caption": media_id is not None and text is not None,
                            "timestamp": timestamp,
                            "event_path": str(event_path),
                        },
                    )

                    # ✅ SMART SKIP BATCHING: Debounce media or burst messages
                    # For multi-image scenarios, users send multiple images in quick succession.
                    # Smart Skip logic:
                    # - Media messages always debounce (common multi-image scenario)
                    # - Text messages debounce only if recent activity or pending messages
                    # - Single text with no activity processes immediately (zero latency)
                    #
                    # Flow:
                    # 1. Duplicate check (above) prevents multiple tasks for same message
                    # 2. Smart Skip decides: debounce or immediate processing
                    # 3. If debounce: queue to DB, start timer (3s), batch process
                    # 4. If immediate: add to background tasks (existing behavior)
                    # 5. Return 200 OK immediately (within milliseconds)

                    received_at = datetime.fromtimestamp(int(timestamp))

                    # Check if message should be debounced
                    logger.info(
                        f"TRACE[{trace_id}] DEBOUNCE_CHECK: Evaluating batch vs immediate",
                        extra={
                            "trace_id": trace_id,
                            "message_id": message_id,
                            "msg_type": msg_type,
                            "sender": sender,
                        },
                    )
                    should_batch = await batcher.should_debounce(sender, msg_type or "text")
                    debounce_reason = (
                        "media"
                        if msg_type in ("image", "video", "document", "audio", "voice")
                        else "recent_activity_or_pending"
                    )

                    logger.info(
                        f"TRACE[{trace_id}] DEBOUNCE_DECISION: {'BATCH' if should_batch else 'IMMEDIATE'}",
                        extra={
                            "trace_id": trace_id,
                            "message_id": message_id,
                            "should_batch": should_batch,
                            "debounce_reason": debounce_reason
                            if should_batch
                            else "no_recent_activity",
                            "msg_type": msg_type,
                            "sender": sender,
                        },
                    )

                    if should_batch:
                        # Queue for batch processing
                        # IMPORTANT: For media messages, caption goes in 'caption' field only
                        # For text messages, text goes in 'text_content' field only
                        # This prevents duplication in batch processing
                        await batcher.queue_message(
                            message_id=message_id,
                            sender_id=sender,
                            thread_id=thread_id,
                            message_type=msg_type or "text",
                            text_content=text if not media_id else None,  # Text-only messages
                            media_id=media_id,
                            caption=text if media_id else None,  # Media captions only
                            sender_name=sender_name,
                            received_at=received_at,
                            runner=runner,
                        )
                        logger.info(
                            f"TRACE[{trace_id}] QUEUED: Message added to pending_messages DB",
                            extra={
                                "trace_id": trace_id,
                                "message_id": message_id,
                                "sender": sender,
                                "message_type": msg_type,
                                "thread_id": thread_id,
                            },
                        )

                        # Each message starts a delayed processing task
                        # Task waits debounce window (3s), then processes if messages still pending
                        # Multiple concurrent tasks are safe - atomic fetch_and_clear ensures only one processes
                        logger.info(
                            f"TRACE[{trace_id}] BATCH_TASK_STARTED: Background task for delayed processing",
                            extra={
                                "trace_id": trace_id,
                                "message_id": message_id,
                                "sender": sender,
                            },
                        )
                        background_tasks.add_task(
                            _process_batch_after_delay,
                            batcher=batcher,
                            sender=sender,
                            runner=runner,
                        )
                    else:
                        # Process immediately (text-only, no recent activity)
                        logger.info(
                            f"TRACE[{trace_id}] IMMEDIATE_TASK_STARTED: Background task for workflow",
                            extra={
                                "trace_id": trace_id,
                                "message_id": message_id,
                                "sender": sender,
                            },
                        )
                        background_tasks.add_task(
                            _process_message_async,
                            runner=runner,
                            sender=sender,
                            text=text,
                            media_id=media_id,
                            sender_name=sender_name,
                            message_id=message_id,
                            event_path=event_path,
                        )

        return {"status": "processed"}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to handle webhook: %s", exc, extra={"event_path": str(event_path)})
        raise HTTPException(status_code=500, detail="Internal error") from exc
