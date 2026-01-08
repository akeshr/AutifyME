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
import sys
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

# Cached PM instance for reuse within same process
_pm_cache: dict[str, Any] = {}


def _get_or_create_session(thread_id: str | None) -> tuple[str, dict[str, Any]]:
    """Get existing session or create new one.

    Args:
        thread_id: Existing thread ID to continue, or None for new session

    Returns:
        Tuple of (thread_id, session_dict)

    Note: Session state is in-memory for turn counting only.
          Actual conversation state is in PM's checkpointer (PostgreSQL).
          So passing a thread_id will continue the PM conversation even if
          local session is lost.
    """
    # If thread_id provided, use it (PM checkpointer has the real state)
    if thread_id:
        if thread_id not in _sessions:
            # Recreate local session tracking for existing thread
            _sessions[thread_id] = {
                "turn_count": 0,  # Will increment to 1 on first use
                "messages": [],
            }
        return thread_id, _sessions[thread_id]

    # Create new session with new thread_id
    new_thread_id = f"test_{uuid.uuid4().hex[:12]}"
    _sessions[new_thread_id] = {
        "turn_count": 0,
        "messages": [],
    }
    return new_thread_id, _sessions[new_thread_id]


def _invoke_pm(
    message: str,
    thread_id: str,
    media_paths: list[str] | None = None,
    scenario_id: str | None = None,
) -> tuple[str, bool, list[dict[str, Any]] | None, bool]:
    """Invoke PM and return response details.

    Uses sync checkpointer for Windows stability.

    Args:
        message: User message to send
        thread_id: Conversation thread ID
        media_paths: Optional list of paths to media files
        scenario_id: Optional scenario ID for evaluation tracking

    Returns:
        Tuple of (response_text, is_approval_request, approval_products, workflow_complete)
    """
    # Load environment
    load_dotenv()

    from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
    from autifyme_agents.integrations.storage.storage_factory import get_storage
    from autifyme_agents.workflows.project_manager import create_project_manager

    # Setup
    storage = get_storage()
    company_profile = storage.get_company_profile()
    pm_checkpointer = get_checkpointer()

    # Create PM (async factory requires event loop)
    async def _create_pm():
        return await create_project_manager(
            company_profile=company_profile,
            checkpointer=pm_checkpointer,
            storage=storage,
        )

    # Windows event loop setup
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # type: ignore

    pm = asyncio.run(_create_pm())

    # Build message content with media attachments
    content = message
    if media_paths:
        valid_paths = []
        for media_path in media_paths:
            path = Path(media_path)
            if path.exists():
                valid_paths.append(str(path))
            else:
                logger.warning(f"Media file not found: {media_path}")

        if len(valid_paths) == 1:
            content += f" [media_id: {valid_paths[0]}]"
        elif len(valid_paths) > 1:
            media_ids = ", ".join(valid_paths)
            content += f" [media attachments ({len(valid_paths)}): {media_ids}]"

    # Build config with metadata for LangSmith tracking
    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}

    # Add scenario_id to metadata for evaluation queries
    if scenario_id:
        config["metadata"] = {"scenario_id": scenario_id}

    # Invoke PM (sync with sync checkpointer)
    result = pm.invoke(
        {"messages": [HumanMessage(content=content)]},
        config=config,
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
            "await",
            "proceed",
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
            "has been saved",
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
        time.sleep(2)

        client = Client()

        # Get recent root traces
        runs = list(
            client.list_runs(
                project_name="autifyme-dev",
                limit=5,
                is_root=True,
            )
        )

        # Find the run with matching thread_id in metadata
        for run in runs:
            metadata = run.metadata or {}
            # Check both thread_id and langsmith.thread_id
            if metadata.get("thread_id") == thread_id or metadata.get("langsmith.thread_id") == thread_id:
                trace_id = str(run.trace_id)
                trace_url = f"https://smith.langchain.com/public/{run.id}"
                return trace_id, trace_url

        # If no match by thread_id, return the most recent trace
        if runs:
            run = runs[0]
            trace_id = str(run.trace_id)
            trace_url = f"https://smith.langchain.com/public/{run.id}"
            logger.info(f"Returning most recent trace (thread_id not matched): {trace_id}")
            return trace_id, trace_url

    except Exception as e:
        logger.warning(f"Failed to get trace info: {e}")

    return None, None


def chat_with_pm(
    message: str,
    thread_id: str | None = None,
    media_path: str | None = None,
    media_paths: list[str] | None = None,
    scenario_id: str | None = None,
) -> PMChatResult:
    """Send a message to PM and get structured response.

    This is the primary interface for Claude Code to interact with the PM.
    Each call sends a message and returns the PM's response with metadata
    for evaluation.

    Args:
        message: User message to send to PM
        thread_id: Thread ID from previous call to continue conversation.
                   Pass None to start a new conversation.
        media_path: Optional path to single media file (backward compat)
        media_paths: Optional list of paths to media files (multi-image)
        scenario_id: Optional scenario ID for LangSmith tracking. When provided,
                     this is stored in trace metadata enabling queries like
                     get_scenario_history("PM-01").

    Returns:
        PMChatResult with response details for evaluation

    Examples:
        # Start new conversation with scenario tracking
        >>> result = chat_with_pm(
        ...     "Catalog these sneakers for $79.99",
        ...     scenario_id="PM-01"
        ... )
        >>> print(result.pm_response)

        # Continue conversation (scenario_id auto-inherited from thread)
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
        # Combine media_path and media_paths into single list
        all_media_paths: list[str] | None = None
        if media_paths:
            all_media_paths = list(media_paths)
        if media_path:
            if all_media_paths:
                all_media_paths.insert(0, media_path)
            else:
                all_media_paths = [media_path]

        # Invoke PM
        response_text, is_approval, products, complete = _invoke_pm(
            message, actual_thread_id, all_media_paths, scenario_id
        )

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
            scenario_id=scenario_id,
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
