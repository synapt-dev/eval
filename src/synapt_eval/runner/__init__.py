"""Eval runners: retrieval, generation, edge cases, orchestration."""

from synapt_eval.runner.eval_runner import EvalRunner, run_eval_sync
from synapt_eval.runner.orchestration import (
    Delta,
    GateResult,
    RunEnvelope,
    compute_deltas,
    has_regressions,
    load_baseline,
    pr_gate,
)

__all__ = [
    "Delta",
    "EvalRunner",
    "GateResult",
    "RunEnvelope",
    "compute_deltas",
    "has_regressions",
    "load_baseline",
    "pr_gate",
    "run_eval_sync",
]
