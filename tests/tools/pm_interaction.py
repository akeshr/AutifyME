"""PM Interaction Tool for Claude Code Testing.

This tool provides a clean interface for Claude Code to interact with the PM
and evaluate its behavior in real-time. It's designed for:
1. Sending messages to PM and receiving structured responses
2. Detecting approval requests (HITL interrupts)
3. Continuing conversations across multiple turns
4. Retrieving trace information for deep analysis

Architecture:
- Uses direct PM invocation (not WorkflowRunner) for simplicity
- Maintains session state for multi-turn conversations
- Returns structured PMChatResult for programmatic evaluation

Usage by Claude Code:
    # Start a new conversation
    result = chat_with_pm("Catalog these sneakers for $79.99", media_path="sneaker.jpg")

    # Evaluate the response...
    # Continue the conversation
    result = chat_with_pm("Approved", thread_id=result.thread_id)

    # Analyze trace if needed
    overview = get_trace_overview(result.trace_id)
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain.messages import HumanMessage
from langsmith import Client

from .models import PMChatResult

logger = logging.getLogger(__name__)

# Session storage (in-memory for testing)
_sessions: dict[str, dict[str, Any]] = {}


def _get_or_create_session(thread_id: str | None) -> tuple[str, dict[str, Any]]:
    """Get existing session or create new one.

    Args:
        thread_id: Existing thread ID to continue, or None for new session

    Returns:
        Tuple of (thread_id, session_dict)
    """
    if thread_id and thread_id in _sessions:
        return thread_id, _sessions[thread_id]

    # Create new session
    new_thread_id = f"test_{uuid.uuid4().hex[:12]}"
    _sessions[new_thread_id] = {
        "turn_count": 0,
        "messages": [],
        "pm_instance": None,
    }
    return new_thread_id, _sessions[new_thread_id]


async def _invoke_pm_async(
    message: str,
    thread_id: str,
    media_path: str | None = None,
) -> tuple[str, bool, list[dict[str, Any]] | None, bool]:
    """Invoke PM asynchronously and return response details.

    Args:
        message: User message to send
        thread_id: Conversation thread ID
        media_path: Optional path to media file

    Returns:
        Tuple of (response_text, is_approval_request, approval_products, workflow_complete)
    """
    # Load environment and imports inside function to avoid import issues
    load_dotenv()

    from autifyme_agents.core.ports import StorageInterface
    from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
    from autifyme_agents.integrations.storage.storage_factory import get_storage
    from autifyme_agents.workflows.project_manager import create_project_manager

    # Setup
    storage: StorageInterface = get_storage()
    company_profile = storage.get_company_profile()
    pm_checkpointer = get_checkpointer()

    # Create PM
    pm = await create_project_manager(
        company_profile=company_profile,
        checkpointer=pm_checkpointer,
        storage=storage,
    )

    # Build message content
    content = message
    if media_path:
        path = Path(media_path)
        if path.exists():
            content += f" [media_id: {path}]"
        else:
            logger.warning(f"Media file not found: {media_path}")

    # Invoke PM
    result = pm.invoke(
        {"messages": [HumanMessage(content=content)]},
        config={"configurable": {"thread_id": thread_id}},
    )

    # Extract response
    messages = result.get("messages", [])
    response_text = ""
    is_approval_request = False
    approval_products = None
    workflow_complete = False

    if messages:
        last_message = messages[-1]
        response_text = getattr(last_message, "content", str(last_message))

        # Detect approval request patterns
        approval_indicators = [
            "approve",
            "confirm",
            "review",
            "look good",
            "ready to save",
            "batch approval",
        ]
        is_approval_request = any(
            indicator in response_text.lower() for indicator in approval_indicators
        )

        # Detect workflow completion
        completion_indicators = [
            "successfully saved",
            "completed",
            "done",
            "created",
            "added to catalog",
        ]
        workflow_complete = any(
            indicator in response_text.lower() for indicator in completion_indicators
        )

        # Check for structured response with products
        structured_response = result.get("structured_response")
        if structured_response and hasattr(structured_response, "await_feedback"):
            is_approval_request = structured_response.await_feedback

    return response_text, is_approval_request, approval_products, workflow_complete


def _get_trace_info(thread_id: str) -> tuple[str | None, str | None]:
    """Get trace ID and URL from LangSmith for a thread.

    Args:
        thread_id: Thread ID to look up

    Returns:
        Tuple of (trace_id, trace_url) or (None, None) if not found
    """
    try:
        # Brief delay for trace to be available
        time.sleep(1)

        client = Client()
        runs = list(
            client.list_runs(
                project_name="autifyme-dev",
                filter=f'has(metadata, "thread_id") and eq(metadata["thread_id"], "{thread_id}")',
                limit=1,
            )
        )

        if runs:
            trace_id = str(runs[0].trace_id)
            session_id = runs[0].session_id
            trace_url = f"https://smith.langchain.com/public/{session_id}/r/{trace_id}"
            return trace_id, trace_url

    except Exception as e:
        logger.warning(f"Failed to get trace info: {e}")

    return None, None


def chat_with_pm(
    message: str,
    thread_id: str | None = None,
    media_path: str | None = None,
) -> PMChatResult:
    """Send a message to PM and get structured response.

    This is the primary interface for Claude Code to interact with the PM.
    Each call sends a message and returns the PM's response with metadata
    for evaluation.

    Args:
        message: User message to send to PM
        thread_id: Thread ID from previous call to continue conversation.
                   Pass None to start a new conversation.
        media_path: Optional path to media file (image, video, etc.)

    Returns:
        PMChatResult with response details for evaluation

    Examples:
        # Start new conversation
        >>> result = chat_with_pm("Catalog these sneakers for $79.99")
        >>> print(result.pm_response)

        # Continue conversation
        >>> result = chat_with_pm("Approved", thread_id=result.thread_id)

        # With media
        >>> result = chat_with_pm("Catalog this", media_path="product.jpg")
    """
    start_time = time.time()

    # Get or create session
    actual_thread_id, session = _get_or_create_session(thread_id)
    session["turn_count"] += 1
    turn = session["turn_count"]

    logger.info(
        f"chat_with_pm: turn={turn}, thread={actual_thread_id}, message={message[:50]}..."
    )

    try:
        # Run async PM invocation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response_text, is_approval, products, complete = loop.run_until_complete(
                _invoke_pm_async(message, actual_thread_id, media_path)
            )
        finally:
            loop.close()

        # Calculate timing
        elapsed_ms = int((time.time() - start_time) * 1000)

        # Get trace info (optional, may fail)
        trace_id, trace_url = _get_trace_info(actual_thread_id)

        return PMChatResult(
            thread_id=actual_thread_id,
            pm_response=response_text,
            is_approval_request=is_approval,
            approval_products=products,
            conversation_turn=turn,
            response_time_ms=elapsed_ms,
            trace_id=trace_id,
            trace_url=trace_url,
            workflow_complete=complete,
            error=None,
        )

    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.exception(f"chat_with_pm failed: {e}")

        return PMChatResult(
            thread_id=actual_thread_id,
            pm_response="",
            is_approval_request=False,
            approval_products=None,
            conversation_turn=turn,
            response_time_ms=elapsed_ms,
            trace_id=None,
            trace_url=None,
            workflow_complete=False,
            error=str(e),
        )


def clear_session(thread_id: str) -> None:
    """Clear a session from memory.

    Args:
        thread_id: Thread ID to clear
    """
    if thread_id in _sessions:
        del _sessions[thread_id]
        logger.info(f"Session cleared: {thread_id}")


def clear_all_sessions() -> None:
    """Clear all sessions from memory."""
    _sessions.clear()
    logger.info("All sessions cleared")
