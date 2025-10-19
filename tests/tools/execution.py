"""Execution tool for autonomous testing framework.

Provides execute_scenario() to run workflow tests programmatically.
"""
import time
import uuid
from pathlib import Path
from typing import Optional

from langsmith import Client
from dotenv import load_dotenv

# Ensure .env is loaded
load_dotenv()

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from autifyme_agents.integrations.storage.storage_factory import get_storage
from autifyme_agents.workflows.channels.protocol import MessagingChannel
from autifyme_agents.workflows.orchestration.runner_v2 import WorkflowRunner

from .models import ExecutionResult


class _SilentConsoleChannel(MessagingChannel):
    """Console channel for programmatic execution - minimal output."""

    def __init__(self, hitl_mode: str = "auto_approve"):
        self.hitl_mode = hitl_mode
        self.messages_sent = []
        self.approval_count = 0  # Track product count for mixed mode

    def format_thread_id(self, sender: str) -> str:
        return f"console:{sender}"

    def send_text(self, recipient: str, message: str, *, metadata: dict | None = None) -> dict:
        self.messages_sent.append({"type": "text", "message": message})

        # Detect batch approval messages and track product count (for mixed mode)
        if "**Batch Approval Request**" in message:
            import re
            match = re.search(r'\((\d+) products?\)', message)
            if match:
                self.approval_count = int(match.group(1))

        return {"status": "sent"}

    def send_approval_request(self, recipient: str, interrupt_value) -> dict:
        """Auto-handle HITL based on mode."""
        self.approval_count += 1  # Increment for single approval requests

        if self.hitl_mode == "auto_approve":
            return {"status": "approved", "value": interrupt_value}
        elif self.hitl_mode == "auto_reject":
            return {"status": "rejected"}
        elif self.hitl_mode == "mixed":
            # Mixed mode signals to send batch response later
            return {"status": "pending_batch"}
        else:
            # Default to approve for programmatic execution
            return {"status": "approved", "value": interrupt_value}

    def send_completion(self, recipient: str, result) -> dict:
        self.messages_sent.append({"type": "completion", "result": result})
        return {"status": "sent"}

    def send_error(self, recipient: str, error_type: str, custom_message: str | None = None) -> dict:
        self.messages_sent.append({"type": "error", "error_type": error_type})
        return {"status": "sent"}

    def download_media(self, media_id: str) -> Path:
        return Path(media_id)


def execute_scenario(
    scenario_id: str,
    hitl_mode: str = "auto_approve",
    media_path: Optional[str] = None,
) -> ExecutionResult:
    """Execute test scenario programmatically.

    This is the primary execution tool for autonomous testing. It runs a complete
    workflow (Runner → PM → Departments → Specialists → Tools) and returns
    structured execution results including trace information.

    Args:
        scenario_id: Scenario identifier or custom prompt text
        hitl_mode: HITL behavior - "auto_approve" (default) | "auto_reject" | "mixed"
                  mixed mode: For 3+ products, approves 1, rejects 2, edits 3 price to 50
        media_path: Optional path to media file (image/video/audio/document)

    Returns:
        ExecutionResult with success status, trace info, products created, timing

    Example:
        >>> result = execute_scenario("cataloging_with_image", "auto_approve")
        >>> if not result.success:
        ...     print(f"Failed: {result.errors}")
        ...     # Analyze trace
        ...     overview = get_trace_overview(result.trace_id)
    """
    start_time = time.time()

    # Setup components
    storage: StorageInterface = get_storage()
    channel = _SilentConsoleChannel(hitl_mode=hitl_mode)
    checkpointer = get_checkpointer()

    runner = WorkflowRunner(
        channel=channel,
        storage=storage,
        checkpointer=checkpointer,
    )

    # Generate unique sender to avoid checkpoint conflicts
    unique_sender = f"test_{uuid.uuid4().hex[:8]}"
    thread_id = channel.format_thread_id(unique_sender)

    errors = []
    success = False
    trace_id = None
    trace_url = None

    try:
        # Execute initial message
        runner.handle_message(
            sender=unique_sender,
            text=scenario_id,
            media_id=media_path if media_path else None,
        )

        # Auto-respond to HITL if in auto mode
        if hitl_mode in ["auto_approve", "auto_reject", "mixed"]:
            time.sleep(0.1)  # Brief pause

            # Determine follow-up text based on mode
            if hitl_mode == "auto_approve":
                follow_up = "approve"
            elif hitl_mode == "auto_reject":
                follow_up = "reject"
            elif hitl_mode == "mixed":
                # Mixed approval based on product count (same as simulate.py)
                product_count = channel.approval_count
                if product_count == 1:
                    follow_up = "approve"
                elif product_count == 2:
                    follow_up = "approve 1, reject 2"
                elif product_count >= 3:
                    # Approve 1, Reject 2, Edit 3 price to 50
                    follow_up = "approve 1, reject 2, edit 3 price to 50"
                else:
                    follow_up = "approve"

            runner.handle_message(
                sender=unique_sender,
                text=follow_up,
                media_id=None,
            )

        # Query LangSmith for trace by thread_id AFTER workflow completes
        # (get_current_run_tree() doesn't work outside traced context)
        # Wait for trace to be uploaded to LangSmith (async process)
        time.sleep(3.0)

        try:
            client = Client()
            # Query recent root runs
            runs = list(client.list_runs(
                project_name="autifyme-dev",
                is_root=True,
                limit=20
            ))

            # Find run matching our thread_id
            for run in runs:
                if run.extra:
                    metadata = run.extra.get("metadata", {})
                    langsmith_thread_id = metadata.get("langsmith.thread_id")
                    if langsmith_thread_id == thread_id:
                        trace_id = str(run.trace_id)
                        # Build LangSmith trace URL
                        # Format: https://smith.langchain.com/public/SESSION_ID/r/TRACE_ID
                        trace_url = f"https://smith.langchain.com/public/{run.session_id}/r/{trace_id}"
                        break

            if not trace_id:
                # Debug: list thread IDs we found
                found_threads = [
                    run.extra.get("metadata", {}).get("langsmith.thread_id")
                    for run in runs
                    if run.extra and run.extra.get("metadata")
                ]
                errors.append(f"Trace not found for thread {thread_id}. Found threads: {found_threads[:5]}")
        except Exception as e:
            # If trace capture fails, continue but note the error
            errors.append(f"Failed to capture trace: {str(e)}")

        success = True

    except Exception as e:
        errors.append(f"{type(e).__name__}: {str(e)}")

    execution_time = time.time() - start_time

    # Query database for products created
    products_created = 0
    try:
        # Use storage interface to query products for this thread
        # This is a simplified approach - in real implementation, we'd query by thread_id
        # For now, just check if any completion message was sent
        completion_msgs = [m for m in channel.messages_sent if m.get("type") == "completion"]
        products_created = len(completion_msgs)
    except Exception as e:
        errors.append(f"Failed to count products: {str(e)}")

    return ExecutionResult(
        success=success,
        thread_id=thread_id,
        trace_url=trace_url or "https://smith.langchain.com",
        trace_id=trace_id or "unknown",
        products_created=products_created,
        execution_time_seconds=round(execution_time, 2),
        errors=errors,
    )
