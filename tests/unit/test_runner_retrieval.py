"""Tests for retrieval eval runner."""

import pytest

from synapt_eval.adapters.retrieval_adapter import RetrievalAdapter, RetrievalCandidate
from synapt_eval.runner.retrieval import run_retrieval_category, run_retrieval_eval
from synapt_eval.types import Fixture


class MockRetrievalAdapter(RetrievalAdapter):
    def __init__(self, results: dict[str, list[RetrievalCandidate]]):
        self._results = results

    async def retrieve(self, query: str, k: int = 10) -> list[RetrievalCandidate]:
        return self._results.get(query, [])


@pytest.mark.asyncio
async def test_retrieval_eval_basic():
    fixtures = [
        Fixture(id="f1", category="test", query="q1", expected=["a", "b", "c"]),
    ]
    adapter = MockRetrievalAdapter(
        {
            "q1": [
                RetrievalCandidate(id="a", score=0.9),
                RetrievalCandidate(id="b", score=0.8),
                RetrievalCandidate(id="x", score=0.7),
            ],
        }
    )

    results = await run_retrieval_eval(fixtures, adapter)
    assert len(results) == 1
    assert results[0].fixture_id == "f1"
    assert results[0].p_at_5 > 0
    assert results[0].r_at_10 > 0


@pytest.mark.asyncio
async def test_retrieval_eval_empty_results():
    fixtures = [
        Fixture(id="f1", category="test", query="q1", expected=["a"]),
    ]
    adapter = MockRetrievalAdapter({"q1": []})

    results = await run_retrieval_eval(fixtures, adapter)
    assert len(results) == 1
    assert results[0].p_at_5 == 0.0
    assert results[0].r_at_10 == 0.0


@pytest.mark.asyncio
async def test_retrieval_category():
    fixtures = [
        Fixture(id="f1", category="test", query="q1", expected=["a", "b"]),
        Fixture(id="f2", category="test", query="q2", expected=["c"]),
    ]
    adapter = MockRetrievalAdapter(
        {
            "q1": [RetrievalCandidate(id="a", score=0.9)],
            "q2": [RetrievalCandidate(id="c", score=0.8)],
        }
    )

    result = await run_retrieval_category(fixtures, adapter, "test")
    assert result.category == "test"
    assert result.metrics.n == 2
    assert len(result.per_fixture) == 2
