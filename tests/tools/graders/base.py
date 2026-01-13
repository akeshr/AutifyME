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
        verdict: PASS | PARTIAL | FAIL
    """

    trace_id: str
    total_graders: int
    passed: int
    failed: int
    overall_score: float
    results: list[GraderResult] = field(default_factory=list)
    verdict: str = ""

    def __post_init__(self):
        """Set verdict based on score if not provided."""
        if not self.verdict:
            if self.overall_score >= 0.85:
                self.verdict = "PASS"
            elif self.overall_score >= 0.55:
                self.verdict = "PARTIAL"
            else:
                self.verdict = "FAIL"

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
            "results": [r.to_dict() for r in self.results],
        }

    def format_summary(self) -> str:
        """Format as human-readable summary."""
        lines = [
            f"## Grader Results: {self.verdict}",
            f"**Score:** {self.overall_score:.2f} ({self.passed}/{self.total_graders} passed)",
            "",
            "| Grader | Result | Severity | Reason |",
            "|--------|--------|----------|--------|",
        ]

        for r in self.results:
            result_icon = "PASS" if r.passed else "FAIL"
            lines.append(f"| {r.name} | {result_icon} | {r.severity} | {r.reason[:50]}{'...' if len(r.reason) > 50 else ''} |")

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
