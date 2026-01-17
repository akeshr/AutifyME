"""Workflow Outcomes Integration for Evaluation Framework.

Bridges production workflow_outcomes data with evaluation scenarios.
Domain-agnostic - works for any workflow type.

Enables:
- Query production outcomes with flexible filters
- Retrieve media assets from Supabase storage
- Create replay scenarios from production data
- Ground truth comparison (actual vs expected)

Usage:
    from tests.tools.workflow_outcomes import (
        get_outcomes,
        get_outcome_by_trace,
        get_media_for_outcome,
        create_scenario_from_outcome,
    )

    # Query with any filter combination
    outcomes = get_outcomes(
        days=7,
        intent="cataloging",  # or any intent
        success=True,
        with_media=True,
    )

    # Get media from storage
    media = get_media_for_outcome(outcome)
    # media.storage_path, media.public_url, media.local_path
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


@dataclass
class ProductionOutcome:
    """Normalized view of WorkflowOutcome for evaluation.

    Domain-agnostic - works for any workflow type.
    """

    tracking_id: str
    thread_id: str
    trace_id: str | None

    # User input
    message_text: str
    media_id: str | None
    media_type: str | None
    sender_id: str
    platform: str

    # Routing
    intent: str
    department: str
    routing_reasoning: str | None
    routing_confidence: float | None

    # Outcome
    success: bool
    error_type: str | None
    error_message: str | None
    result_data: dict[str, Any] | None

    # Timing
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: float | None

    @property
    def has_media(self) -> bool:
        """Check if outcome has media attachment."""
        return self.media_id is not None

    @property
    def has_trace(self) -> bool:
        """Check if outcome has LangSmith trace linked."""
        return self.trace_id is not None


@dataclass
class MediaAsset:
    """Media asset retrieved from storage."""

    storage_path: str
    public_url: str
    filename: str
    content_type: str | None = None
    size_bytes: int | None = None
    local_path: str | None = None  # Set after download


@dataclass
class ProductionScenario:
    """Scenario created from production outcome for replay."""

    id: str
    name: str
    description: str

    # Input
    message: str

    # Expected (from actual production outcome)
    expected_intent: str
    expected_department: str
    expected_success: bool

    # Source
    source_tracking_id: str
    source_thread_id: str

    # Fields with defaults must come last
    source_trace_id: str | None = None
    media_assets: list[MediaAsset] = field(default_factory=list)
    actual_result: dict[str, Any] | None = None
    tags: list[str] = field(default_factory=list)


def _get_storage():
    """Get storage adapter."""
    load_dotenv()
    from autifyme_agents.integrations.storage.storage_factory import get_storage

    return get_storage()


def _run_async(coro):
    """Run async coroutine synchronously."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, create a new one
            import nest_asyncio

            nest_asyncio.apply()
            return loop.run_until_complete(coro)
        return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(coro)


# =============================================================================
# Query Functions (Domain-Agnostic)
# =============================================================================


def get_outcomes(
    days: int = 7,
    intent: str | None = None,
    department: str | None = None,
    success: bool | None = None,
    with_media: bool | None = None,
    with_trace: bool | None = None,
    limit: int = 100,
) -> list[ProductionOutcome]:
    """Query workflow outcomes with flexible filters.

    Domain-agnostic - use any filter combination.

    Args:
        days: Look back this many days
        intent: Filter by intent (any value)
        department: Filter by department (any value)
        success: Filter by success status
        with_media: If True, only outcomes with media_id
        with_trace: If True, only outcomes with trace_id
        limit: Maximum outcomes to return

    Returns:
        List of ProductionOutcome objects

    Example:
        # All successful outcomes with images
        outcomes = get_outcomes(days=7, success=True, with_media=True)

        # All failed outcomes for investigation
        failures = get_outcomes(days=7, success=False)

        # Specific intent
        cataloging = get_outcomes(days=7, intent="cataloging")
    """
    storage = _get_storage()

    raw_outcomes = storage.get_workflow_outcomes(
        time_window=timedelta(days=days),
        intent=intent,
        department=department,
        success=success,
        limit=limit * 2 if with_media or with_trace else limit,
    )

    outcomes = [
        ProductionOutcome(
            tracking_id=o.tracking_id,
            thread_id=o.thread_id,
            trace_id=o.trace_id,
            message_text=o.message_text or "",
            media_id=o.media_id,
            media_type=o.media_type,
            sender_id=o.sender_id,
            platform=o.platform or "whatsapp",
            intent=o.intent or "unknown",
            department=o.department or "unknown",
            routing_reasoning=o.routing_reasoning,
            routing_confidence=o.routing_confidence,
            success=o.success,
            error_type=o.error_type,
            error_message=o.error_message,
            result_data=o.result_data,
            started_at=o.started_at,
            ended_at=o.ended_at,
            duration_seconds=o.duration_seconds,
        )
        for o in raw_outcomes
    ]

    # Apply post-filters
    if with_media is True:
        outcomes = [o for o in outcomes if o.has_media]
    elif with_media is False:
        outcomes = [o for o in outcomes if not o.has_media]

    if with_trace is True:
        outcomes = [o for o in outcomes if o.has_trace]
    elif with_trace is False:
        outcomes = [o for o in outcomes if not o.has_trace]

    return outcomes[:limit]


def get_outcome_by_trace(trace_id: str) -> ProductionOutcome | None:
    """Get workflow outcome by LangSmith trace ID.

    Args:
        trace_id: LangSmith trace ID

    Returns:
        ProductionOutcome if found, None otherwise
    """
    # Query recent outcomes and filter
    outcomes = get_outcomes(days=30, limit=500)
    for o in outcomes:
        if o.trace_id == trace_id:
            return o
    return None


def get_outcome_by_thread(thread_id: str) -> list[ProductionOutcome]:
    """Get all outcomes for a thread (multi-turn conversations).

    Args:
        thread_id: LangGraph thread ID

    Returns:
        List of outcomes for this thread, ordered by time
    """
    outcomes = get_outcomes(days=30, limit=500)
    thread_outcomes = [o for o in outcomes if o.thread_id == thread_id]
    return sorted(thread_outcomes, key=lambda o: o.started_at)


# =============================================================================
# Media Retrieval
# =============================================================================


def get_media_for_outcome(
    outcome: ProductionOutcome,
    download_to: str | Path | None = None,
) -> list[MediaAsset]:
    """Get media assets for an outcome from Supabase storage.

    Looks up files in inbox/{thread_id}/ folder.

    Args:
        outcome: Outcome to get media for
        download_to: Directory to download files to (optional)

    Returns:
        List of MediaAsset objects with storage paths and URLs

    Example:
        outcome = get_outcomes(with_media=True, limit=1)[0]
        assets = get_media_for_outcome(outcome)
        for asset in assets:
            print(f"Found: {asset.storage_path}")
            print(f"URL: {asset.public_url}")
    """
    if not outcome.has_media:
        return []

    storage = _get_storage()

    # List files in inbox for this thread
    try:
        result = _run_async(
            storage.list_storage_files(
                folder="inbox",
                thread_id=outcome.thread_id,
                extension_filter=["jpg", "jpeg", "png", "webp", "gif"],
            )
        )
    except Exception as e:
        logger.warning(f"Failed to list storage files: {e}")
        return []

    if not result.get("success") or not result.get("files"):
        return []

    assets = []
    for file_info in result["files"]:
        asset = MediaAsset(
            storage_path=file_info["storage_path"],
            public_url=file_info["public_url"],
            filename=file_info["name"],
            content_type=file_info.get("content_type"),
            size_bytes=file_info.get("size_bytes"),
        )

        # Download if requested
        if download_to:
            local_path = _download_asset(asset, download_to)
            asset.local_path = local_path

        assets.append(asset)

    return assets


def _download_asset(asset: MediaAsset, download_dir: str | Path) -> str | None:
    """Download asset to local directory."""
    import httpx

    download_dir = Path(download_dir)
    download_dir.mkdir(parents=True, exist_ok=True)

    local_path = download_dir / asset.filename

    if local_path.exists():
        return str(local_path)

    try:
        response = httpx.get(asset.public_url, timeout=30)
        response.raise_for_status()
        local_path.write_bytes(response.content)
        logger.info(f"Downloaded: {asset.filename} -> {local_path}")
        return str(local_path)
    except Exception as e:
        logger.warning(f"Failed to download {asset.filename}: {e}")
        return None


def download_media_for_outcomes(
    outcomes: list[ProductionOutcome],
    download_dir: str | Path,
) -> dict[str, list[MediaAsset]]:
    """Batch download media for multiple outcomes.

    Args:
        outcomes: List of outcomes to download media for
        download_dir: Directory to save files

    Returns:
        Dict mapping tracking_id -> list of MediaAsset with local paths
    """
    result = {}
    for outcome in outcomes:
        if outcome.has_media:
            assets = get_media_for_outcome(outcome, download_to=download_dir)
            if assets:
                result[outcome.tracking_id] = assets
    return result


# =============================================================================
# Scenario Creation
# =============================================================================


def create_scenario_from_outcome(
    outcome: ProductionOutcome,
    scenario_id: str | None = None,
    download_media_to: str | Path | None = None,
) -> ProductionScenario:
    """Create evaluation scenario from production outcome.

    Uses real production data as input, with actual outcome as ground truth.

    Args:
        outcome: Production outcome to convert
        scenario_id: Custom ID (default: PROD-{tracking_id[:8]})
        download_media_to: Directory to download media (optional)

    Returns:
        ProductionScenario ready for replay

    Example:
        outcome = get_outcomes(with_media=True, limit=1)[0]
        scenario = create_scenario_from_outcome(
            outcome,
            download_media_to="tests/test_assets/production"
        )
        # scenario.message = real user message
        # scenario.media_assets = downloaded files
        # scenario.expected_success = actual outcome
    """
    sid = scenario_id or f"PROD-{outcome.tracking_id[:8]}"

    # Build name from message preview
    msg_preview = outcome.message_text[:40] if outcome.message_text else "(no text)"
    name = f"Production: {msg_preview}..."

    # Get media assets
    media_assets = []
    if outcome.has_media:
        media_assets = get_media_for_outcome(outcome, download_to=download_media_to)

    # Build tags
    tags = ["production", outcome.intent, outcome.department]
    if outcome.has_media:
        tags.append("media")
    if outcome.success:
        tags.append("successful")
    else:
        tags.append("failed")
        if outcome.error_type:
            tags.append(f"error:{outcome.error_type}")

    return ProductionScenario(
        id=sid,
        name=name,
        description=f"Replayed from {outcome.tracking_id} ({outcome.started_at.date()})",
        message=outcome.message_text,
        media_assets=media_assets,
        expected_intent=outcome.intent,
        expected_department=outcome.department,
        expected_success=outcome.success,
        source_tracking_id=outcome.tracking_id,
        source_trace_id=outcome.trace_id,
        source_thread_id=outcome.thread_id,
        actual_result=outcome.result_data,
        tags=tags,
    )


# =============================================================================
# Statistics (Domain-Agnostic)
# =============================================================================


def get_outcome_stats(days: int = 7) -> dict[str, Any]:
    """Get aggregate statistics from workflow outcomes.

    Args:
        days: Look back this many days

    Returns:
        Dict with aggregate statistics
    """
    outcomes = get_outcomes(days=days, limit=500)

    if not outcomes:
        return {"total": 0, "days": days}

    total = len(outcomes)
    successful = sum(1 for o in outcomes if o.success)
    with_media = sum(1 for o in outcomes if o.has_media)
    with_trace = sum(1 for o in outcomes if o.has_trace)

    # Intent distribution
    intent_counts: dict[str, int] = {}
    for o in outcomes:
        intent_counts[o.intent] = intent_counts.get(o.intent, 0) + 1

    # Department distribution
    dept_counts: dict[str, int] = {}
    for o in outcomes:
        dept_counts[o.department] = dept_counts.get(o.department, 0) + 1

    # Error distribution
    error_counts: dict[str, int] = {}
    for o in outcomes:
        if o.error_type:
            error_counts[o.error_type] = error_counts.get(o.error_type, 0) + 1

    # Duration stats
    durations = [o.duration_seconds for o in outcomes if o.duration_seconds]
    avg_duration = sum(durations) / len(durations) if durations else 0

    return {
        "total": total,
        "days": days,
        "successful": successful,
        "failed": total - successful,
        "success_rate": successful / total,
        "with_media": with_media,
        "with_trace": with_trace,
        "avg_duration_seconds": avg_duration,
        "intent_distribution": intent_counts,
        "department_distribution": dept_counts,
        "error_distribution": error_counts,
    }


def list_distinct_values(field: str, days: int = 30) -> list[str]:
    """List distinct values for a field.

    Args:
        field: Field name (intent, department, error_type, platform)
        days: Look back this many days

    Returns:
        Sorted list of distinct values
    """
    outcomes = get_outcomes(days=days, limit=500)

    values = set()
    for o in outcomes:
        value = getattr(o, field, None)
        if value:
            values.add(value)

    return sorted(values)
