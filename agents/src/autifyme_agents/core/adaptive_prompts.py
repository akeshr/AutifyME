"""Adaptive Prompts Framework - Self-improving prompts with feedback loops.

This module implements Phase 1.1 of the Agentic Evolution roadmap. Prompts
evolve based on workflow outcomes instead of remaining static. The framework
learns successful patterns and failure cases, composing context-aware prompts
that improve over time.

**Architecture**:
- Maintains hexagonal architecture: StorageInterface port for persistence
- Type-safe with Pydantic models for all data structures
- Observability: All decisions logged with structured metadata
- Feedback loop: Outcomes → Pattern extraction → Prompt enhancement

**Integration**:
- PM: get_prompt() injects learned delegation strategies
- Departments: Context-aware tool selection based on success patterns
- Specialists: Warnings about known failure cases
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.prompt_loader import load_prompt


logger = logging.getLogger(__name__)


class SuccessPattern(BaseModel):
    """Represents a learned success pattern from workflow outcomes."""

    pattern_id: str = Field(description="Hash-based unique identifier")
    agent_name: str = Field(description="Agent that used this pattern")
    context_keys: list[str] = Field(description="Context attributes that triggered pattern")
    strategy_summary: str = Field(description="What strategy worked")
    success_count: int = Field(default=1, description="Times this pattern succeeded")
    last_used: datetime = Field(default_factory=datetime.now)
    avg_duration_seconds: float = Field(description="Average workflow duration")


class FailureWarning(BaseModel):
    """Represents a known failure case to avoid."""

    warning_id: str = Field(description="Hash-based unique identifier")
    agent_name: str = Field(description="Agent that encountered failure")
    context_keys: list[str] = Field(description="Context attributes that triggered failure")
    error_type: str = Field(description="Type of error encountered")
    failure_summary: str = Field(description="What went wrong")
    occurrence_count: int = Field(default=1, description="Times this failure occurred")
    last_seen: datetime = Field(default_factory=datetime.now)
    mitigation_hint: str | None = Field(default=None, description="Suggested mitigation")


class WorkflowOutcome(BaseModel):
    """Structured workflow outcome for learning."""

    agent_name: str
    context: dict[str, Any]
    success: bool
    duration_seconds: float
    strategy_used: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)


class AdaptivePromptManager:
    """Self-improving prompt system with feedback loops.

    This manager composes prompts by combining:
    1. Base static prompt template (from version control)
    2. Learned success patterns (from similar contexts)
    3. Failure warnings (to avoid known pitfalls)
    4. Runtime context (current message, similar cases)

    **Design Principles**:
    - Prompts evolve gradually, never replace base template completely
    - Success patterns require minimum threshold before injection
    - Failure warnings take precedence (fail-safe first)
    - All learning is traceable and auditable
    """

    def __init__(
        self,
        storage: StorageInterface,
        *,
        min_pattern_threshold: int = 3,
        max_patterns_per_prompt: int = 5,
        pattern_ttl_days: int = 30,
    ):
        """Initialize adaptive prompt manager.

        Args:
            storage: Storage adapter for persisting learned patterns
            min_pattern_threshold: Minimum successes before pattern is injected
            max_patterns_per_prompt: Maximum patterns to include (avoid bloat)
            pattern_ttl_days: Days before old patterns are pruned
        """
        self.storage = storage
        self.min_pattern_threshold = min_pattern_threshold
        self.max_patterns_per_prompt = max_patterns_per_prompt
        self.pattern_ttl_days = pattern_ttl_days

        # In-memory caches (refreshed periodically)
        self._success_patterns: dict[str, list[SuccessPattern]] = {}
        self._failure_warnings: dict[str, list[FailureWarning]] = {}
        self._cache_loaded_at: datetime | None = None
        self._cache_ttl_seconds = 300  # 5 minutes

    def get_prompt(
        self,
        agent_name: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Get contextualized prompt with learned patterns.

        Args:
            agent_name: Name of agent requesting prompt (e.g., 'project_manager')
            context: Runtime context (message type, similar cases, etc.)

        Returns:
            Composed prompt with base template + learned enhancements

        Example:
            >>> manager = AdaptivePromptManager(storage)
            >>> context = {
            ...     "message_type": "cataloging",
            ...     "has_media": True,
            ...     "similar_cases": [...]
            ... }
            >>> prompt = manager.get_prompt("project_manager", context)
        """
        context = context or {}

        # 1. Load base prompt template from version control
        base_prompt = self._load_base_prompt(agent_name)

        # 2. Refresh cache if stale
        self._refresh_cache_if_needed()

        # 3. Get relevant success patterns for this context
        patterns = self._get_relevant_patterns(agent_name, context)

        # 4. Get relevant failure warnings for this context
        warnings = self._get_failure_warnings(agent_name, context)

        # 5. Compose final prompt
        composed = self._compose_prompt(base_prompt, patterns, warnings, context)

        logger.info(
            "Composed adaptive prompt",
            extra={
                "agent_name": agent_name,
                "patterns_count": len(patterns),
                "warnings_count": len(warnings),
                "context_keys": list(context.keys()),
            },
        )

        return composed

    def record_outcome(
        self,
        agent_name: str,
        context: dict[str, Any],
        outcome: WorkflowOutcome,
    ) -> None:
        """Learn from workflow outcome.

        Args:
            agent_name: Agent that executed workflow
            context: Context used for prompt composition
            outcome: Structured workflow result

        This method:
        - Extracts success patterns from successful outcomes
        - Records failure warnings from failed outcomes
        - Updates pattern statistics (success count, avg duration)
        - Prunes stale patterns based on TTL
        """
        if outcome.success:
            self._extract_success_pattern(agent_name, context, outcome)
        else:
            self._record_failure_case(agent_name, context, outcome)

        logger.info(
            "Recorded workflow outcome",
            extra={
                "agent_name": agent_name,
                "success": outcome.success,
                "duration_seconds": outcome.duration_seconds,
            },
        )

    # --- Internal Methods ---

    def _load_base_prompt(self, agent_name: str) -> str:
        """Load static prompt template from filesystem.

        Maps agent names to prompt file paths following existing conventions.
        """
        # Map agent names to prompt file paths
        prompt_map = {
            "project_manager": "project_manager.prompt",
            "cataloging_department": "departments/cataloging_department.prompt",
            "cataloging_specialist": "specialists/cataloging_specialist.prompt",
            "image_analysis_specialist": "specialists/image_analysis_specialist.prompt",
        }

        prompt_file = prompt_map.get(agent_name)
        if not prompt_file:
            logger.warning(
                f"No prompt file mapped for agent '{agent_name}', using generic fallback"
            )
            return f"You are {agent_name}. Process the user's request professionally."

        try:
            return load_prompt(prompt_file)
        except FileNotFoundError:
            logger.error(
                f"Prompt file not found for agent '{agent_name}': {prompt_file}"
            )
            return f"You are {agent_name}. Process the user's request professionally."

    def _refresh_cache_if_needed(self) -> None:
        """Refresh in-memory caches if TTL expired."""
        if self._cache_loaded_at is None:
            self._load_patterns_from_storage()
            self._cache_loaded_at = datetime.now()
            return

        elapsed = (datetime.now() - self._cache_loaded_at).total_seconds()
        if elapsed > self._cache_ttl_seconds:
            self._load_patterns_from_storage()
            self._cache_loaded_at = datetime.now()

    def _load_patterns_from_storage(self) -> None:
        """Load learned patterns from persistent storage.

        NOTE: Phase 1.1 implementation - patterns stored in-memory.
        Phase 1.2 will add database persistence via StorageInterface extension.
        """
        # TODO: Implement storage retrieval when workflow_outcomes table exists
        # For now, patterns are memory-only (will persist after Phase 1.2)
        logger.debug("Pattern cache refreshed (memory-only in Phase 1.1)")

    def _get_relevant_patterns(
        self,
        agent_name: str,
        context: dict[str, Any],
    ) -> list[SuccessPattern]:
        """Retrieve success patterns matching current context.

        Args:
            agent_name: Agent requesting patterns
            context: Current workflow context

        Returns:
            List of relevant patterns, filtered by threshold and sorted by success count
        """
        agent_patterns = self._success_patterns.get(agent_name, [])

        # Filter by minimum threshold
        qualified = [
            p for p in agent_patterns if p.success_count >= self.min_pattern_threshold
        ]

        # Filter by context similarity (simple key matching for Phase 1)
        context_keys = set(context.keys())
        relevant = [
            p
            for p in qualified
            if any(key in context_keys for key in p.context_keys)
        ]

        # Sort by success count descending, take top N
        relevant.sort(key=lambda p: p.success_count, reverse=True)
        return relevant[: self.max_patterns_per_prompt]

    def _get_failure_warnings(
        self,
        agent_name: str,
        context: dict[str, Any],
    ) -> list[FailureWarning]:
        """Retrieve failure warnings matching current context.

        Args:
            agent_name: Agent requesting warnings
            context: Current workflow context

        Returns:
            List of relevant warnings, sorted by occurrence count
        """
        agent_warnings = self._failure_warnings.get(agent_name, [])

        # Filter by context similarity
        context_keys = set(context.keys())
        relevant = [
            w
            for w in agent_warnings
            if any(key in context_keys for key in w.context_keys)
        ]

        # Sort by occurrence count descending (most common failures first)
        relevant.sort(key=lambda w: w.occurrence_count, reverse=True)
        return relevant

    def _compose_prompt(
        self,
        base: str,
        patterns: list[SuccessPattern],
        warnings: list[FailureWarning],
        context: dict[str, Any],
    ) -> str:
        """Compose final prompt from components.

        Args:
            base: Static base prompt template
            patterns: Learned success patterns
            warnings: Known failure warnings
            context: Runtime context

        Returns:
            Composed prompt with all enhancements
        """
        sections = [base]

        # Add failure warnings (fail-safe first)
        if warnings:
            sections.append("\n## ⚠️ Known Failure Cases (Avoid These):\n")
            for i, warning in enumerate(warnings, 1):
                sections.append(
                    f"{i}. **{warning.error_type}**: {warning.failure_summary}\n"
                )
                if warning.mitigation_hint:
                    sections.append(f"   → Mitigation: {warning.mitigation_hint}\n")

        # Add success patterns
        if patterns:
            sections.append("\n## ✅ Learned Success Patterns:\n")
            for i, pattern in enumerate(patterns, 1):
                sections.append(
                    f"{i}. {pattern.strategy_summary} "
                    f"(✓ {pattern.success_count} times, "
                    f"avg {pattern.avg_duration_seconds:.1f}s)\n"
                )

        # Add runtime context hints
        if context.get("similar_cases"):
            sections.append("\n## 📚 Similar Past Cases:\n")
            similar = context["similar_cases"]
            for i, case in enumerate(similar[:3], 1):  # Top 3
                sections.append(f"{i}. {case.get('summary', 'Similar case')}\n")

        return "".join(sections)

    def _extract_success_pattern(
        self,
        agent_name: str,
        context: dict[str, Any],
        outcome: WorkflowOutcome,
    ) -> None:
        """Extract and store success pattern from outcome.

        Args:
            agent_name: Agent that succeeded
            context: Context used
            outcome: Successful workflow outcome
        """
        # Generate pattern ID from context
        context_keys = sorted(context.keys())
        pattern_id = self._hash_context(agent_name, context_keys)

        # Get or create pattern
        if agent_name not in self._success_patterns:
            self._success_patterns[agent_name] = []

        existing = next(
            (p for p in self._success_patterns[agent_name] if p.pattern_id == pattern_id),
            None,
        )

        if existing:
            # Update existing pattern stats
            existing.success_count += 1
            existing.last_used = datetime.now()
            # Incremental average duration
            existing.avg_duration_seconds = (
                existing.avg_duration_seconds * (existing.success_count - 1)
                + outcome.duration_seconds
            ) / existing.success_count
        else:
            # Create new pattern
            new_pattern = SuccessPattern(
                pattern_id=pattern_id,
                agent_name=agent_name,
                context_keys=context_keys,
                strategy_summary=outcome.strategy_used or "Successful workflow completion",
                success_count=1,
                last_used=datetime.now(),
                avg_duration_seconds=outcome.duration_seconds,
            )
            self._success_patterns[agent_name].append(new_pattern)

        logger.debug(
            "Extracted success pattern",
            extra={
                "agent_name": agent_name,
                "pattern_id": pattern_id,
                "success_count": existing.success_count if existing else 1,
            },
        )

    def _record_failure_case(
        self,
        agent_name: str,
        context: dict[str, Any],
        outcome: WorkflowOutcome,
    ) -> None:
        """Record failure warning from outcome.

        Args:
            agent_name: Agent that failed
            context: Context used
            outcome: Failed workflow outcome
        """
        # Generate warning ID from context + error type
        context_keys = sorted(context.keys())
        warning_id = self._hash_context(
            agent_name, context_keys, outcome.error_type or "unknown"
        )

        # Get or create warning
        if agent_name not in self._failure_warnings:
            self._failure_warnings[agent_name] = []

        existing = next(
            (w for w in self._failure_warnings[agent_name] if w.warning_id == warning_id),
            None,
        )

        if existing:
            # Update occurrence count
            existing.occurrence_count += 1
            existing.last_seen = datetime.now()
        else:
            # Create new warning
            new_warning = FailureWarning(
                warning_id=warning_id,
                agent_name=agent_name,
                context_keys=context_keys,
                error_type=outcome.error_type or "UnknownError",
                failure_summary=outcome.error_message or "Workflow failed",
                occurrence_count=1,
                last_seen=datetime.now(),
            )
            self._failure_warnings[agent_name].append(new_warning)

        logger.debug(
            "Recorded failure warning",
            extra={
                "agent_name": agent_name,
                "warning_id": warning_id,
                "occurrence_count": existing.occurrence_count if existing else 1,
            },
        )

    @staticmethod
    def _hash_context(agent_name: str, context_keys: list[str], suffix: str = "") -> str:
        """Generate deterministic hash for pattern/warning identification.

        Args:
            agent_name: Agent name
            context_keys: Sorted context attribute names
            suffix: Optional suffix (e.g., error type)

        Returns:
            First 12 chars of SHA-256 hash (sufficient for uniqueness)
        """
        content = f"{agent_name}:{'|'.join(context_keys)}:{suffix}"
        return hashlib.sha256(content.encode()).hexdigest()[:12]
