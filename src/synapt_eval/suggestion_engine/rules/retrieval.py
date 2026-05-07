"""Retrieval suggestion rules."""

from __future__ import annotations

from typing import Any

from synapt_eval.reviewer.types import SEVERITY_ERROR, SEVERITY_WARNING, Verdict
from synapt_eval.suggestion_engine.types import Suggestion
from synapt_eval.types import EvalResult


class LowPrecisionRule:
    """Flags when P@5 drops below a configurable threshold."""

    def __init__(self, threshold: float = 0.7) -> None:
        self._threshold = threshold

    def evaluate(
        self,
        result: EvalResult,
        verdicts: list[Verdict] | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[Suggestion]:
        if result.metrics.p_at_5 >= self._threshold:
            return []
        return [
            Suggestion(
                severity=SEVERITY_WARNING,
                message=(
                    f"P@5 is {result.metrics.p_at_5:.2f}, below threshold {self._threshold:.2f}"
                ),
                rule_name="low_precision",
                metric="p_at_5",
                category=result.category,
                fix_hint=(
                    "Review retrieval ranking; "
                    "consider re-embedding or tuning similarity thresholds."
                ),
            )
        ]


class LowRecallRule:
    """Flags when R@10 drops below a configurable threshold."""

    def __init__(self, threshold: float = 0.6) -> None:
        self._threshold = threshold

    def evaluate(
        self,
        result: EvalResult,
        verdicts: list[Verdict] | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[Suggestion]:
        if result.metrics.r_at_10 >= self._threshold:
            return []
        return [
            Suggestion(
                severity=SEVERITY_WARNING,
                message=(
                    f"R@10 is {result.metrics.r_at_10:.2f}, below threshold {self._threshold:.2f}"
                ),
                rule_name="low_recall",
                metric="r_at_10",
                category=result.category,
                fix_hint=(
                    "Relevant items are being missed; "
                    "check chunk boundaries and embedding coverage."
                ),
            )
        ]


class HighNoResultsRule:
    """Flags when too many fixtures return zero retrieval results."""

    def __init__(self, threshold: float = 0.1) -> None:
        self._threshold = threshold

    def evaluate(
        self,
        result: EvalResult,
        verdicts: list[Verdict] | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[Suggestion]:
        if not result.per_fixture:
            return []

        no_result_count = sum(1 for pf in result.per_fixture if pf.score == 0.0)
        rate = no_result_count / len(result.per_fixture)

        if rate <= self._threshold:
            return []

        return [
            Suggestion(
                severity=SEVERITY_ERROR,
                message=(
                    f"{no_result_count}/{len(result.per_fixture)} fixtures "
                    f"({rate:.0%}) returned no results"
                ),
                rule_name="high_no_results",
                metric="no_results_rate",
                category=result.category,
                fix_hint=(
                    "Check that queries match indexed content; verify embeddings are populated."
                ),
            )
        ]
