"""Test history tracking for autonomous testing framework.

Provides persistent storage and retrieval of test execution history.
Stores results in JSON file for simple persistence without external dependencies.
"""

import json
from datetime import datetime
from pathlib import Path

from .models import ExecutionHistory, ExecutionRecord, ExecutionResult

# History file location (in tests/tools directory)
HISTORY_FILE = Path(__file__).parent / ".test_history.json"


def _load_history() -> list[dict]:
    """Load test history from file.

    Returns:
        List of test execution dictionaries (empty if file doesn't exist)
    """
    if not HISTORY_FILE.exists():
        return []

    try:
        with HISTORY_FILE.open(encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        # Corrupted file - start fresh
        return []


def _save_history(history: list[dict]) -> None:
    """Save test history to file.

    Args:
        history: List of test execution dictionaries
    """
    with HISTORY_FILE.open("w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, default=str)


def record_test_execution(result: ExecutionResult, scenario_id: str) -> None:
    """Record a test execution in history.

    Args:
        result: Execution result from execute_scenario()
        scenario_id: Scenario identifier that was executed
    """
    # Load existing history
    history = _load_history()

    # Create new test execution record
    execution = {
        "timestamp": datetime.now().isoformat(),
        "scenario_id": scenario_id,
        "thread_id": result.thread_id,
        "trace_url": result.trace_url,
        "success": result.success,
        "products_created": result.products_created,
        "execution_time_seconds": result.execution_time_seconds,
        "errors_summary": "; ".join(result.errors) if result.errors else "",
    }

    # Add to history (newest first)
    history.insert(0, execution)

    # Keep only last 100 executions to avoid unbounded growth
    history = history[:100]

    # Save updated history
    _save_history(history)


def list_recent_tests(limit: int = 10) -> ExecutionHistory:
    """Get recent test execution history.

    Retrieves the N most recent test executions for progress tracking
    and debugging. Useful for identifying trends, frequent failures,
    and execution time changes.

    Args:
        limit: Maximum number of test executions to return (default: 10)

    Returns:
        ExecutionHistory with list of recent test executions (newest first)

    Example:
        >>> history = list_recent_tests(limit=5)
        >>> for test in history.tests:
        ...     status = "PASS" if test.success else "FAIL"
        ...     print(f"[{status}] {test.scenario_id} - {test.execution_time_seconds}s")
        ...     if not test.success:
        ...         print(f"  Errors: {test.errors_summary}")
    """
    # Load history
    history_data = _load_history()

    # Convert to Pydantic models
    tests = []
    for data in history_data[:limit]:
        try:
            execution = ExecutionRecord(
                timestamp=datetime.fromisoformat(data["timestamp"]),
                scenario_id=data["scenario_id"],
                thread_id=data["thread_id"],
                trace_url=data["trace_url"],
                success=data["success"],
                products_created=data["products_created"],
                execution_time_seconds=data["execution_time_seconds"],
                errors_summary=data.get("errors_summary", ""),
            )
            tests.append(execution)
        except (KeyError, ValueError):
            # Skip malformed records
            continue

    return ExecutionHistory(tests=tests)


def clear_test_history() -> None:
    """Clear all test history.

    Use this to reset history when starting a new testing session
    or when history becomes too large/irrelevant.
    """
    if HISTORY_FILE.exists():
        HISTORY_FILE.unlink()
