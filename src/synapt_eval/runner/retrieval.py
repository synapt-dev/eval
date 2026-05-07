"""Retrieval eval runner: fixtures + adapter + scoring -> results."""

from __future__ import annotations

from typing import Any

from synapt_eval.adapters.retrieval_adapter import RetrievalAdapter
from synapt_eval.aggregation import aggregate_retrieval
from synapt_eval.scoring import kendall_tau, precision_at_k, recall_at_k
from synapt_eval.types import EvalResult, Fixture, PerFixtureResult, RetrievalResult


async def run_retrieval_eval(
    fixtures: list[Fixture[Any]],
    adapter: RetrievalAdapter,
    k_precision: int = 5,
    k_recall: int = 10,
) -> list[RetrievalResult]:
    """Run retrieval eval across all fixtures.

    For each fixture, retrieves candidates via the adapter and computes
    P@K, R@K, and Kendall's Tau against the expected ranking.
    """
    results: list[RetrievalResult] = []

    for fixture in fixtures:
        candidates = await adapter.retrieve(fixture.query, k=k_recall)
        retrieved_ids = [c.id for c in candidates]
        scores = [c.score for c in candidates]

        p5 = precision_at_k(retrieved_ids, fixture.expected, k=k_precision)
        r10 = recall_at_k(retrieved_ids, fixture.expected, k=k_recall)
        tau = kendall_tau(retrieved_ids, fixture.expected)

        results.append(
            RetrievalResult(
                fixture_id=fixture.id,
                retrieved_ids=retrieved_ids,
                scores=scores,
                p_at_5=p5,
                r_at_10=r10,
                tau=tau,
            )
        )

    return results


async def run_retrieval_category(
    fixtures: list[Fixture[Any]],
    adapter: RetrievalAdapter,
    category: str,
    k_precision: int = 5,
    k_recall: int = 10,
) -> EvalResult:
    """Run retrieval eval for a single category and aggregate."""
    per_fixture = await run_retrieval_eval(
        fixtures, adapter, k_precision=k_precision, k_recall=k_recall
    )
    result = aggregate_retrieval(per_fixture, category)

    result.per_fixture = [
        PerFixtureResult(
            fixture_id=r.fixture_id,
            category=category,
            passed=r.p_at_5 > 0,
            score=r.p_at_5,
            details={"r_at_10": r.r_at_10, "tau": r.tau},
        )
        for r in per_fixture
    ]

    return result
