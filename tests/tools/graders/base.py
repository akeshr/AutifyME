"""Base schemas for code graders.

Defines GraderResult and GraderSuiteResult used by all graders.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class GraderCategory(Enum):
    """Category of grader for filtering."""

    PM = "pm"
    ANALYST = "analyst"
    SPECIALIST = "specialist"
    UNIVERSAL = "universal"


@dataclass
class GraderResult:
    """Single grader evaluation result.

    Attributes:
        name: Grader name (e.g., "protocol_load_first")
        passed: Whether the check passed
        score: Score from 0.0 to 1.0
        evidence: What was checked (for debugging)
        reason: Human-readable explanation
        category: Which agent type this grader applies to
        severity: Impact level (HIGH | MEDIUM | LOW)
    """

    name: str
    passed: bool
    score: float
    evidence: dict[str, Any]
    reason: str
    category: GraderCategory = GraderCategory.UNIVERSAL
    severity: str = "MEDIUM"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for serialization."""
        return {
            "name": self.name,
            "passed": self.passed,
            "score": self.score,
            "evidence": self.evidence,
            "reason": self.reason,
            "category": self.category.value,
            "severity": self.severity,
        }


@dataclass
class GraderSuiteResult:
    """Result of running a suite of graders.

    Attributes:
        trace_id: LangSmith trace ID
        total_graders: Number of graders run
        passed: Number that passed
        failed: Number that failed
        overall_score: Weighted average score
        results: Individual grader results
        verdict: PASS | PARTIAL | FAIL (behavioral checks only)
        trace_status: Actual trace outcome (success | error | pending)
        trace_error: Error message if trace failed
        overall_verdict: Combined assessment (PASS | PASS_WITH_ERRORS | PARTIAL | FAIL | ERROR)
    """

    trace_id: str
    total_graders: int
    passed: int
    failed: int
    overall_score: float
    results: list[GraderResult] = field(default_factory=list)
    verdict: str = ""
    trace_status: str = "unknown"
    trace_error: str | None = None
    overall_verdict: str = ""

    def __post_init__(self):
        """Set verdicts based on score and trace status."""
        # Behavioral verdict (graders only)
        if not self.verdict:
            if self.overall_score >= 0.85:
                self.verdict = "PASS"
            elif self.overall_score >= 0.55:
                self.verdict = "PARTIAL"
            else:
                self.verdict = "FAIL"

        # Overall verdict (combines trace status + behavioral checks)
        if not self.overall_verdict:
            if self.trace_status == "error":
                # Trace failed - can't be overall PASS regardless of graders
                if self.verdict == "PASS":
                    self.overall_verdict = "ERROR"  # Graders passed but trace failed
                else:
                    self.overall_verdict = "ERROR"  # Both failed
            elif self.trace_status == "pending":
                self.overall_verdict = "INCOMPLETE"
            else:
                # Trace succeeded - use behavioral verdict
                self.overall_verdict = self.verdict

    def get_failures(self) -> list[GraderResult]:
        """Get list of failed graders."""
        return [r for r in self.results if not r.passed]

    def get_high_severity_failures(self) -> list[GraderResult]:
        """Get list of HIGH severity failures."""
        return [r for r in self.results if not r.passed and r.severity == "HIGH"]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for serialization."""
        return {
            "trace_id": self.trace_id,
            "total_graders": self.total_graders,
            "passed": self.passed,
            "failed": self.failed,
            "overall_score": self.overall_score,
            "verdict": self.verdict,
            "trace_status": self.trace_status,
            "trace_error": self.trace_error,
            "overall_verdict": self.overall_verdict,
            "results": [r.to_dict() for r in self.results],
        }

    def format_summary(self) -> str:
        """Format as human-readable summary."""
        lines = [
            f"## Grader Results: {self.overall_verdict}",
            "",
            "### Status",
            f"- **Trace Status:** {self.trace_status.upper()}",
            f"- **Behavioral Score:** {self.overall_score:.2f} ({self.passed}/{self.total_graders} passed)",
            f"- **Grader Verdict:** {self.verdict}",
        ]

        # Show trace error prominently if present
        if self.trace_error:
            lines.extend([
                "",
                "### Trace Error",
                f"```",
                f"{self.trace_error[:200]}{'...' if len(self.trace_error) > 200 else ''}",
                f"```",
            ])

        lines.extend([
            "",
            "### Behavioral Checks",
            "| Grader | Result | Severity | Reason |",
            "|--------|--------|----------|--------|",
        ])

        for r in self.results:
            result_icon = "PASS" if r.passed else "FAIL"
            reason_preview = r.reason[:50] + "..." if len(r.reason) > 50 else r.reason
            lines.append(f"| {r.name} | {result_icon} | {r.severity} | {reason_preview} |")

        if self.get_failures():
            lines.extend([
                "",
                "### Failed Graders Detail",
            ])
            for r in self.get_failures():
                lines.append(f"\n**{r.name}** ({r.severity})")
                lines.append(f"- Reason: {r.reason}")
                lines.append(f"- Evidence: {r.evidence}")

        return "\n".join(lines)
