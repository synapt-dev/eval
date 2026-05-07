"""Tests for metrics aggregation."""

from synapt_eval.aggregation import aggregate_retrieval
from synapt_eval.types import RetrievalResult


def test_aggregate_empty():
    result = aggregate_retrieval([], "test")
    assert result.metrics.n == 0
    assert result.metrics.p_at_5 == 0.0


def test_aggregate_single():
    results = [
        RetrievalResult(
            fixture_id="f1",
            retrieved_ids=["a", "b"],
            scores=[0.9, 0.8],
            p_at_5=0.6,
            r_at_10=0.5,
            tau=0.7,
        )
    ]
    agg = aggregate_retrieval(results, "retrieval")
    assert agg.metrics.n == 1
    assert agg.metrics.p_at_5 == 0.6
    assert agg.metrics.r_at_10 == 0.5
    assert agg.metrics.tau == 0.7


def test_aggregate_averages():
    results = [
        RetrievalResult(
            fixture_id="f1",
            retrieved_ids=[],
            scores=[],
            p_at_5=0.8,
            r_at_10=0.6,
            tau=0.5,
        ),
        RetrievalResult(
            fixture_id="f2",
            retrieved_ids=[],
            scores=[],
            p_at_5=0.4,
            r_at_10=0.2,
            tau=0.3,
        ),
    ]
    agg = aggregate_retrieval(results, "retrieval")
    assert agg.metrics.n == 2
    assert abs(agg.metrics.p_at_5 - 0.6) < 1e-9
    assert abs(agg.metrics.r_at_10 - 0.4) < 1e-9
    assert agg.metrics.tau is not None and abs(agg.metrics.tau - 0.4) < 1e-9


def test_aggregate_with_none_tau():
    results = [
        RetrievalResult(
            fixture_id="f1",
            retrieved_ids=[],
            scores=[],
            p_at_5=1.0,
            r_at_10=1.0,
            tau=None,
        ),
    ]
    agg = aggregate_retrieval(results, "retrieval")
    assert agg.metrics.tau is None
