"""Code graders for evaluation framework.

Fast, deterministic checks that run in milliseconds and cost nothing.
Use these before model-based evaluation.

Usage:
    from tests.tools.graders import run_code_graders, GraderResult

    result = run_code_graders(trace_id)
    if result.verdict == "PASS":
        print("All code graders passed")
    else:
        for r in result.results:
            if not r.passed:
                print(f"FAILED: {r.name} - {r.reason}")
"""

from .base import GraderCategory, GraderResult, GraderSuiteResult
from .orchestrator import (
    run_analyst_graders,
    run_code_graders,
    run_pm_graders,
    run_specialist_graders,
)

__all__ = [
    "GraderResult",
    "GraderSuiteResult",
    "GraderCategory",
    "run_code_graders",
    "run_pm_graders",
    "run_specialist_graders",
    "run_analyst_graders",
]
