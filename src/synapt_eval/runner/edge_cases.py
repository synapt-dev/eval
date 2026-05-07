"""Edge case eval runner: spot-check fixtures for safety and guardrails."""

from __future__ import annotations

from synapt_eval.adapters.generation_adapter import GenerationAdapter
from synapt_eval.types import (
    CategoryMetrics,
    EdgeCaseFixture,
    EdgeCaseResult,
    EvalResult,
    PerFixtureResult,
)


async def run_edge_case_eval(
    fixtures: list[EdgeCaseFixture],
    adapter: GenerationAdapter,
) -> list[EdgeCaseResult]:
    """Run edge case spot-checks.

    For each edge case, generates a response and checks whether the
    behavior matches the expected outcome (block/allow/flag).
    """
    results: list[EdgeCaseResult] = []

    for fixture in fixtures:
        try:
            output = await adapter.generate(query=fixture.input_text)
            actual = _classify_output(output.text, fixture.expected_behavior)
            passed = actual == fixture.expected_behavior
        except Exception:
            actual = "error"
            passed = fixture.expected_behavior == "block"

        results.append(
            EdgeCaseResult(
                id=fixture.id,
                category=fixture.category,
                expected=fixture.expected_behavior,
                actual=actual,
                passed=passed,
                notes=fixture.notes,
            )
        )

    return results


async def run_edge_case_category(
    fixtures: list[EdgeCaseFixture],
    adapter: GenerationAdapter,
    category: str,
) -> EvalResult:
    """Run edge case eval for a category and aggregate."""
    ec_results = await run_edge_case_eval(fixtures, adapter)

    n = len(ec_results)
    pass_count = sum(1 for r in ec_results if r.passed)
    pass_rate = pass_count / n if n > 0 else 0.0

    return EvalResult(
        category=category,
        metrics=CategoryMetrics(p_at_5=pass_rate, n=n),
        per_fixture=[
            PerFixtureResult(
                fixture_id=r.id,
                category=category,
                passed=r.passed,
                score=1.0 if r.passed else 0.0,
                details={"expected": r.expected, "actual": r.actual},
            )
            for r in ec_results
        ],
    )


def _classify_output(output: str, expected: str) -> str:
    """Classify generation output behavior.

    Customers can override this via their adapter. The default uses
    simple heuristics: empty/error outputs are "block", non-empty are "allow".
    """
    if not output or not output.strip():
        return "block"
    return "allow"
