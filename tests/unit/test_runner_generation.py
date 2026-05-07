"""Tests for generation eval runner."""

from typing import Any

import pytest

from synapt_eval.adapters.generation_adapter import GenerationAdapter, GenerationOutput
from synapt_eval.runner.generation import run_generation_category, run_generation_eval
from synapt_eval.types import Fixture


class MockGenerationAdapter(GenerationAdapter):
    def __init__(self, responses: dict[str, str], latency: float = 100.0):
        self._responses = responses
        self._latency = latency

    async def generate(self, query: str, context: list[Any] | None = None) -> GenerationOutput:
        text = self._responses.get(query, "default response")
        return GenerationOutput(text=text, latency_ms=self._latency)


class FailingAdapter(GenerationAdapter):
    async def generate(self, query: str, context: list[Any] | None = None) -> GenerationOutput:
        raise RuntimeError("generation failed")


@pytest.mark.asyncio
async def test_generation_eval_basic():
    fixtures = [
        Fixture(id="f1", category="test", query="q1", expected=["a"]),
    ]
    adapter = MockGenerationAdapter({"q1": "generated answer"})

    results = await run_generation_eval(fixtures, adapter)
    assert len(results) == 1
    assert results[0].status == "ok"
    assert results[0].output == "generated answer"
    assert results[0].latency_ms == 100.0


@pytest.mark.asyncio
async def test_generation_eval_error_handling():
    fixtures = [
        Fixture(id="f1", category="test", query="q1", expected=["a"]),
    ]
    adapter = FailingAdapter()

    results = await run_generation_eval(fixtures, adapter)
    assert len(results) == 1
    assert results[0].status.startswith("error:")
    assert results[0].output == ""


@pytest.mark.asyncio
async def test_generation_category():
    fixtures = [
        Fixture(id="f1", category="test", query="q1", expected=["a"]),
        Fixture(id="f2", category="test", query="q2", expected=["b"]),
    ]
    adapter = MockGenerationAdapter({"q1": "ans1", "q2": "ans2"})

    result = await run_generation_category(fixtures, adapter, "test")
    assert result.category == "test"
    assert result.metrics.n == 2
    assert result.metrics.p_at_5 == 1.0  # success rate
    assert len(result.per_fixture) == 2


@pytest.mark.asyncio
async def test_generation_category_partial_failure():
    fixtures = [
        Fixture(id="f1", category="test", query="q1", expected=["a"]),
    ]
    adapter = FailingAdapter()

    result = await run_generation_category(fixtures, adapter, "test")
    assert result.metrics.p_at_5 == 0.0  # 0% success
    assert not result.per_fixture[0].passed
