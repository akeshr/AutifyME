"""Workflow Evaluation Framework.

Scripts that provide context and data for intelligent agents to evaluate
and improve agentic workflows. The agent provides intelligence; these
scripts provide structured data access.

Core Scripts:
- get_evaluation_context: Complete context for evaluating a single trace
- get_batch_analysis: Pattern detection across multiple traces
- compare_traces: Side-by-side trace comparison
- verify_improvement: Closed-loop improvement verification
"""

from .context import get_evaluation_context
from .batch import get_batch_analysis
from .compare import compare_traces
from .verify import verify_improvement

__all__ = [
    "get_evaluation_context",
    "get_batch_analysis",
    "compare_traces",
    "verify_improvement",
]
