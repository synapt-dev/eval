"""Generation eval runner: fixtures + adapter -> results."""

from __future__ import annotations

from typing import Any

from synapt_eval.adapters.generation_adapter import GenerationAdapter
from synapt_eval.types import (
    CategoryMetrics,
    EvalResult,
    Fixture,
    GenerationResult,
    PerFixtureResult,
)


async def run_generation_eval(
    fixtures: list[Fixture[Any]],
    adapter: GenerationAdapter,
) -> list[GenerationResult]:
    """Run generation eval across all fixtures.

    For each fixture, generates a response via the adapter and captures
    output text, latency, and status.
    """
    results: list[GenerationResult] = []

    for fixture in fixtures:
        try:
            output = await adapter.generate(
                query=fixture.query,
                context=fixture.user_history,
            )
            results.append(
                GenerationResult(
                    fixture_id=fixture.id,
                    query=fixture.query,
                    output=output.text,
                    latency_ms=output.latency_ms,
                    status="ok",
                )
            )
        except Exception as exc:
            results.append(
                GenerationResult(
                    fixture_id=fixture.id,
                    query=fixture.query,
                    output="",
                    latency_ms=0.0,
                    status=f"error: {exc}",
                )
            )

    return results


async def run_generation_category(
    fixtures: list[Fixture[Any]],
    adapter: GenerationAdapter,
    category: str,
) -> EvalResult:
    """Run generation eval for a single category and aggregate."""
    gen_results = await run_generation_eval(fixtures, adapter)

    ok_count = sum(1 for r in gen_results if r.status == "ok")
    n = len(gen_results)
    success_rate = ok_count / n if n > 0 else 0.0
    return EvalResult(
        category=category,
        metrics=CategoryMetrics(p_at_5=success_rate, n=n),
        per_fixture=[
            PerFixtureResult(
                fixture_id=r.fixture_id,
                category=category,
                passed=r.status == "ok",
                score=1.0 if r.status == "ok" else 0.0,
                details={"latency_ms": r.latency_ms, "status": r.status},
            )
            for r in gen_results
        ],
    )
