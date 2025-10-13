"""Test Synthesizer - Auto-generate tests from production usage patterns.

This module implements Phase 1.3 of the Agentic Evolution roadmap. Tests stay
current with real user behavior automatically by analyzing production logs and
synthesizing test scenarios.

**Architecture**:
- Analyzes workflow_outcomes to identify unique patterns
- Clusters similar messages to avoid redundant tests
- Prioritizes edge cases (low frequency, high complexity)
- Generates pytest code from failure cases

**Test Generation Strategy**:
1. Extract representative samples from production
2. Identify edge cases not in existing test suite
3. Generate scenarios for simulate.py
4. Auto-generate pytest regression tests from failures

**Benefits**:
- Coverage evolves with real user behavior
- Edge cases become regression tests automatically
- Reduces manual test maintenance burden
- Ensures tests reflect actual usage patterns
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

from pydantic import BaseModel, Field

from autifyme_agents.core.ports import StorageInterface


logger = logging.getLogger(__name__)


class UsagePattern(BaseModel):
    """Represents a unique usage pattern extracted from production."""

    pattern_id: str = Field(description="Unique identifier")
    message_text: str | None = Field(description="Representative message text")
    media_type: str | None = Field(description="Media type if present")
    intent: str = Field(description="Classified intent")
    department: str = Field(description="Department that handled it")
    occurrence_count: int = Field(description="Times this pattern occurred")
    last_seen: datetime = Field(description="Most recent occurrence")
    avg_duration_seconds: float = Field(description="Average handling time")
    success_rate: float = Field(description="Success rate (0-1)")
    is_edge_case: bool = Field(
        default=False, description="Low frequency or high complexity"
    )


class TestScenario(BaseModel):
    """Test scenario ready for simulate.py."""

    name: str = Field(description="Descriptive scenario name")
    text: str | None = Field(description="User message text")
    media_path: str | None = Field(description="Path to media file if needed")
    expected_intent: str = Field(description="Expected intent classification")
    expected_department: str = Field(description="Expected department routing")
    origin: str = Field(default="synthesized", description="Source of scenario")
    frequency: int = Field(description="Production occurrence count")
    last_seen: datetime = Field(description="Last seen in production")


class FailureCase(BaseModel):
    """Production failure case for regression test generation."""

    failure_id: str = Field(description="Unique identifier")
    message_text: str | None = Field(description="Message that caused failure")
    media_path: str | None = Field(description="Media path if involved")
    error_type: str = Field(description="Error class name")
    error_message: str = Field(description="Error details")
    thread_id: str = Field(description="LangGraph thread ID for debugging")
    occurred_at: datetime = Field(description="When failure occurred")
    resolution_strategy: str | None = Field(
        description="How it was resolved (if applicable)"
    )


class TestSynthesizer:
    """Generates test scenarios from production usage patterns.

    **Design Principles**:
    - Representative: Samples cover diverse user behaviors
    - Edge-case focused: Prioritizes uncommon patterns
    - Non-redundant: Clusters similar messages
    - Actionable: Generates executable test code

    **Usage**:
        synthesizer = TestSynthesizer(storage)

        # Daily: Extract new patterns from production
        patterns = synthesizer.analyze_production_logs(timedelta(days=7))

        # Generate test scenarios
        scenarios = [synthesizer.synthesize_test_scenario(p) for p in patterns]

        # Auto-generate regression tests from failures
        failures = synthesizer.get_recent_failures(timedelta(days=1))
        for failure in failures:
            test_file = synthesizer.generate_regression_test(failure)
    """

    def __init__(
        self,
        storage: StorageInterface,
        *,
        edge_case_threshold: int = 3,
        similarity_threshold: float = 0.8,
    ):
        """Initialize test synthesizer.

        Args:
            storage: Storage adapter for production logs
            edge_case_threshold: Max occurrences to consider edge case
            similarity_threshold: Cosine similarity for clustering (Phase 2)
        """
        self.storage = storage
        self.edge_case_threshold = edge_case_threshold
        self.similarity_threshold = similarity_threshold

    def analyze_production_logs(
        self,
        time_window: timedelta,
        max_patterns: int = 20,
    ) -> list[UsagePattern]:
        """Extract unique patterns from production logs.

        Args:
            time_window: How far back to analyze
            max_patterns: Maximum patterns to return

        Returns:
            List of unique usage patterns, prioritized by value
        """
        # TODO: Implement when workflow_outcomes table exists
        # Query outcomes within time window
        # Cluster by message similarity (Phase 2: use embeddings)
        # Extract representative sample from each cluster
        # Prioritize edge cases (low frequency, high complexity)

        logger.info(
            "Analyzing production logs",
            extra={
                "time_window_days": time_window.days,
                "max_patterns": max_patterns,
                "note": "Full implementation pending workflow_outcomes table",
            },
        )

        # Phase 1.3: Return placeholder patterns
        # Phase 2: Real clustering and analysis with vector embeddings
        return []

    def synthesize_test_scenario(self, pattern: UsagePattern) -> TestScenario:
        """Create test scenario from usage pattern.

        Args:
            pattern: Production usage pattern

        Returns:
            Test scenario ready for simulate.py
        """
        # Determine scenario name
        edge_marker = "[EDGE CASE] " if pattern.is_edge_case else ""
        name = (
            f"{edge_marker}Production Pattern: {pattern.intent} "
            f"({pattern.occurrence_count}x)"
        )

        scenario = TestScenario(
            name=name,
            text=pattern.message_text,
            media_path=None,  # TODO: Map media_type to test files
            expected_intent=pattern.intent,
            expected_department=pattern.department,
            origin="synthesized",
            frequency=pattern.occurrence_count,
            last_seen=pattern.last_seen,
        )

        logger.debug(
            "Synthesized test scenario",
            extra={
                "pattern_id": pattern.pattern_id,
                "scenario_name": name,
                "is_edge_case": pattern.is_edge_case,
            },
        )

        return scenario

    def get_recent_failures(
        self,
        time_window: timedelta,
        limit: int = 10,
    ) -> list[FailureCase]:
        """Retrieve recent production failures for regression test generation.

        Args:
            time_window: How far back to look
            limit: Maximum failures to return

        Returns:
            List of failure cases ordered by recency
        """
        # TODO: Implement when workflow_outcomes table exists
        # Query failed workflows within time window
        # Order by occurred_at DESC
        # Extract failure details

        logger.info(
            "Retrieving recent failures",
            extra={
                "time_window_hours": time_window.total_seconds() / 3600,
                "limit": limit,
                "note": "Full implementation pending workflow_outcomes table",
            },
        )

        return []

    def generate_regression_test(
        self,
        failure: FailureCase,
        output_dir: Path | None = None,
    ) -> Path:
        """Auto-generate pytest test from failure case.

        Args:
            failure: Production failure case
            output_dir: Directory for generated test (default: tests/regression/)

        Returns:
            Path to generated test file
        """
        if output_dir is None:
            output_dir = Path(__file__).parent.parent.parent / "tests" / "regression"

        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate safe test function name
        test_func_name = (
            f"test_regression_{failure.failure_id.replace('-', '_')[:16]}"
        )
        test_file_name = f"{test_func_name}.py"
        test_file_path = output_dir / test_file_name

        # Generate pytest code
        test_code = self._generate_pytest_code(failure, test_func_name)

        # Write to file
        test_file_path.write_text(test_code, encoding="utf-8")

        logger.info(
            "Generated regression test",
            extra={
                "failure_id": failure.failure_id,
                "test_file": str(test_file_path),
                "error_type": failure.error_type,
            },
        )

        return test_file_path

    def generate_scenarios_file(
        self,
        patterns: list[UsagePattern],
        output_path: Path | None = None,
    ) -> Path:
        """Generate Python file with scenario definitions for simulate.py.

        Args:
            patterns: Usage patterns to convert to scenarios
            output_path: Output file path (default: cli/synthesized_scenarios.py)

        Returns:
            Path to generated scenarios file
        """
        if output_path is None:
            output_path = (
                Path(__file__).parent.parent
                / "cli"
                / "synthesized_scenarios.py"
            )

        # Generate scenarios dictionary
        scenarios_code = self._generate_scenarios_code(patterns)

        # Write to file
        output_path.write_text(scenarios_code, encoding="utf-8")

        logger.info(
            "Generated scenarios file",
            extra={
                "output_path": str(output_path),
                "scenario_count": len(patterns),
            },
        )

        return output_path

    # --- Internal Methods ---

    def _generate_pytest_code(
        self,
        failure: FailureCase,
        test_func_name: str,
    ) -> str:
        """Generate pytest test code from failure case.

        Args:
            failure: Failure case
            test_func_name: Name for test function

        Returns:
            Python test code
        """
        # Escape strings for Python code
        message_text = (failure.message_text or "").replace('"', '\\"')
        # Variables for template
        sender = "regression_test"

        return f'''"""Auto-generated regression test from production failure.

Failure ID: {failure.failure_id}
Error Type: {failure.error_type}
Occurred At: {failure.occurred_at.isoformat()}
Thread ID: {failure.thread_id}

This test ensures the failure is resolved and doesn't reoccur.
"""

import pytest

from autifyme_agents.workflows.orchestration.runner_v2 import WorkflowRunner
from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
from autifyme_agents.integrations.storage.postgres_saver_factory import get_checkpointer
from autifyme_agents.workflows.channels.protocol import MessagingChannel


class MockChannel(MessagingChannel):
    """Mock channel for testing."""

    def __init__(self):
        self.messages = []

    def format_thread_id(self, sender: str) -> str:
        return f"test:{sender}"

    def send_text(self, recipient: str, message: str, **kwargs) -> dict:
        self.messages.append({{"type": "text", "message": message}})
        return {{"status": "sent"}}

    def send_approval_request(self, recipient: str, draft: dict) -> dict:
        # Auto-approve for regression test
        return {{"status": "approved", "draft": draft}}

    def send_completion(self, recipient: str, result: dict) -> dict:
        self.messages.append({{"type": "completion", "result": result}})
        return {{"status": "sent"}}

    def send_error(self, recipient: str, error_type: str, custom_message: str | None = None) -> dict:
        self.messages.append({{"type": "error", "error_type": error_type}})
        return {{"status": "sent"}}

    def download_media(self, media_id: str):
        return None


def {test_func_name}():
    """Regression test for {failure.error_type}.

    Original message: {message_text}
    Expected: Should not raise {failure.error_type}
    """
    # Setup
    storage = SupabaseStorageClient()
    channel = MockChannel()
    checkpointer = get_checkpointer()

    runner = WorkflowRunner(
        channel=channel,
        storage=storage,
        checkpointer=checkpointer,
    )

    # Execute workflow with original failure message
    # This should NOT raise {failure.error_type}
    runner.handle_message(
        sender="regression_test",
        text="{message_text}",
        media_id={"'" + failure.media_path + "'" if failure.media_path else "None"},
    )

    # Verify workflow completed without error
    error_messages = [m for m in channel.messages if m.get("type") == "error"]
    assert len(error_messages) == 0, (
        f"Workflow failed with error (original: {failure.error_type})"
    )


if __name__ == "__main__":
    # Run this test standalone
    {test_func_name}()
    print("✅ Regression test passed!")
'''

    def _generate_scenarios_code(self, patterns: list[UsagePattern]) -> str:
        """Generate Python code for scenarios dictionary.

        Args:
            patterns: Usage patterns

        Returns:
            Python code defining scenarios
        """
        scenarios_dict = {}

        for i, pattern in enumerate(patterns):
            scenario_id = f"synthesized_{pattern.pattern_id[:8]}"
            scenarios_dict[scenario_id] = {
                "name": (
                    f"{'[EDGE] ' if pattern.is_edge_case else ''}"
                    f"{pattern.intent} ({pattern.occurrence_count}x)"
                ),
                "text": pattern.message_text,
                "media": None,  # TODO: Map media types
                "frequency": pattern.occurrence_count,
                "last_seen": pattern.last_seen.isoformat(),
            }

        # Format as Python code
        code = '''"""Auto-generated test scenarios from production usage patterns.

Generated: {timestamp}
Source: Production logs analysis
Pattern Count: {count}

These scenarios represent real user behavior patterns extracted from
production logs. They are automatically synthesized to keep test coverage
current with actual usage.
"""

from datetime import datetime


SYNTHESIZED_SCENARIOS = {{
{scenarios}
}}


def get_synthesized_scenarios():
    """Get synthesized scenarios dictionary."""
    return SYNTHESIZED_SCENARIOS
'''.format(
            timestamp=datetime.now().isoformat(),
            count=len(patterns),
            scenarios=self._format_scenarios_dict(scenarios_dict),
        )

        return code

    @staticmethod
    def _format_scenarios_dict(scenarios: dict[str, dict]) -> str:
        """Format scenarios dictionary as pretty-printed Python code.

        Args:
            scenarios: Scenarios dictionary

        Returns:
            Formatted Python dictionary code
        """
        lines = []
        for scenario_id, scenario_data in scenarios.items():
            lines.append(f'    "{scenario_id}": {{')
            for key, value in scenario_data.items():
                if isinstance(value, str):
                    lines.append(f'        "{key}": "{value}",')
                elif value is None:
                    lines.append(f'        "{key}": None,')
                else:
                    lines.append(f'        "{key}": {value},')
            lines.append("    },")

        return "\n".join(lines)
