"""Cross-cutting suggestion rules."""

from __future__ import annotations

from typing import Any

from synapt_eval.reviewer.types import SEVERITY_ERROR, SEVERITY_WARNING, Verdict
from synapt_eval.runner.orchestration import compute_deltas
from synapt_eval.suggestion_engine.types import Suggestion
from synapt_eval.types import EvalResult


class RegressionRule:
    """Flags metric regressions compared to a baseline.

    Consumes baseline results from context["baseline"]. If no
    baseline is provided, the rule produces no suggestions.
    """

    def __init__(self, regression_threshold: float = 0.05) -> None:
        self._threshold = regression_threshold

    def evaluate(
        self,
        result: EvalResult,
        verdicts: list[Verdict] | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[Suggestion]:
        if not context or "baseline" not in context:
            return []

        baseline: list[EvalResult] = context["baseline"]
        deltas = compute_deltas([result], baseline, self._threshold)
        regressions = [d for d in deltas if d.regression]

        if not regressions:
            return []

        suggestions: list[Suggestion] = []
        for d in regressions:
            suggestions.append(
                Suggestion(
                    severity=SEVERITY_ERROR,
                    message=(
                        f"{d.metric} regressed: {d.baseline:.3f} -> {d.current:.3f} "
                        f"(delta: {d.delta:+.3f})"
                    ),
                    rule_name="regression",
                    metric=d.metric,
                    category=d.category,
                    fix_hint=(
                        "Compare recent changes against the baseline run to identify the cause."
                    ),
                )
            )
        return suggestions


class CategoryImbalanceRule:
    """Flags when fixture coverage is uneven across categories.

    Operates across multiple results via context["all_results"].
    If the ratio between smallest and largest category exceeds the
    imbalance threshold, a suggestion is generated.
    """

    def __init__(self, imbalance_ratio: float = 3.0) -> None:
        self._ratio = imbalance_ratio

    def evaluate(
        self,
        result: EvalResult,
        verdicts: list[Verdict] | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[Suggestion]:
        if not context or "all_results" not in context:
            return []

        all_results: list[EvalResult] = context["all_results"]
        counts = [r.metrics.n for r in all_results if r.metrics.n > 0]

        if len(counts) < 2:
            return []

        max_n = max(counts)
        min_n = min(counts)

        if min_n == 0 or max_n / min_n <= self._ratio:
            return []

        return [
            Suggestion(
                severity=SEVERITY_WARNING,
                message=(
                    f"Category fixture counts are imbalanced: "
                    f"smallest={min_n}, largest={max_n} (ratio {max_n / min_n:.1f}x)"
                ),
                rule_name="category_imbalance",
                metric="fixture_count",
                fix_hint=(
                    "Add more fixtures to underrepresented categories for balanced evaluation."
                ),
            )
        ]
