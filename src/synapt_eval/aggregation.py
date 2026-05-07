"""Metrics aggregation: per-fixture results to per-category statistics."""

from __future__ import annotations

from synapt_eval.types import CategoryMetrics, EvalResult, RetrievalResult


def aggregate_retrieval(
    results: list[RetrievalResult],
    category: str,
) -> EvalResult:
    """Aggregate per-fixture retrieval results into category metrics."""
    if not results:
        return EvalResult(category=category, metrics=CategoryMetrics())

    n = len(results)
    avg_p5 = sum(r.p_at_5 for r in results) / n
    avg_r10 = sum(r.r_at_10 for r in results) / n

    tau_values = [r.tau for r in results if r.tau is not None]
    avg_tau = sum(tau_values) / len(tau_values) if tau_values else None

    return EvalResult(
        category=category,
        metrics=CategoryMetrics(
            p_at_5=avg_p5,
            r_at_10=avg_r10,
            tau=avg_tau,
            n=n,
        ),
    )
