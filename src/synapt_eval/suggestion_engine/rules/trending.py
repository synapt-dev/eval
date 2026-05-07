"""Trending suggestion rules: multi-run pattern detection."""

from __future__ import annotations

from typing import Any

from synapt_eval.reviewer.types import SEVERITY_ERROR, SEVERITY_WARNING, Verdict
from synapt_eval.suggestion_engine.types import Suggestion
from synapt_eval.types import EvalResult


class MonotonicDegradationRule:
    """Detects 3+ consecutive runs where a key metric gets worse.

    Consumes run history from context["history"] (list of EvalResult,
    oldest first). Current result is included as the latest data point.
    """

    def __init__(
        self,
        metric: str = "p_at_5",
        consecutive: int = 3,
    ) -> None:
        self._metric = metric
        self._consecutive = consecutive

    def evaluate(
        self,
        result: EvalResult,
        verdicts: list[Verdict] | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[Suggestion]:
        if not context or "history" not in context:
            return []

        history: list[EvalResult] = context["history"]
        same_category = [r for r in history if r.category == result.category]
        same_category.append(result)

        if len(same_category) < self._consecutive:
            return []

        values = [getattr(r.metrics, self._metric, None) for r in same_category]
        values = [v for v in values if v is not None]

        if len(values) < self._consecutive:
            return []

        tail = values[-self._consecutive :]
        monotonic_down = all(tail[i] > tail[i + 1] for i in range(len(tail) - 1))

        if not monotonic_down:
            return []

        return [
            Suggestion(
                severity=SEVERITY_ERROR,
                message=(
                    f"{self._metric} has degraded for {self._consecutive} consecutive runs "
                    f"in category '{result.category}': "
                    f"{' -> '.join(f'{v:.3f}' for v in tail)}"
                ),
                rule_name="monotonic_degradation",
                metric=self._metric,
                category=result.category,
                fix_hint=(
                    "Investigate recent changes; this metric is trending consistently downward."
                ),
            )
        ]


class StableLowRule:
    """Detects metrics stuck below threshold across multiple runs.

    Flags when a metric stays below the threshold for N or more
    consecutive runs without improvement, suggesting systemic issues.
    """

    def __init__(
        self,
        metric: str = "p_at_5",
        threshold: float = 0.7,
        min_runs: int = 3,
    ) -> None:
        self._metric = metric
        self._threshold = threshold
        self._min_runs = min_runs

    def evaluate(
        self,
        result: EvalResult,
        verdicts: list[Verdict] | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[Suggestion]:
        if not context or "history" not in context:
            return []

        history: list[EvalResult] = context["history"]
        same_category = [r for r in history if r.category == result.category]
        same_category.append(result)

        if len(same_category) < self._min_runs:
            return []

        values = [getattr(r.metrics, self._metric, None) for r in same_category]
        values = [v for v in values if v is not None]

        if len(values) < self._min_runs:
            return []

        tail = values[-self._min_runs :]
        all_below = all(v < self._threshold for v in tail)

        if not all_below:
            return []

        avg = sum(tail) / len(tail)
        return [
            Suggestion(
                severity=SEVERITY_WARNING,
                message=(
                    f"{self._metric} has been below {self._threshold:.2f} for "
                    f"{self._min_runs} consecutive runs in category '{result.category}' "
                    f"(avg: {avg:.3f})"
                ),
                rule_name="stable_low",
                metric=self._metric,
                category=result.category,
                fix_hint=(
                    "This metric is consistently underperforming; "
                    "consider architectural changes rather than incremental tuning."
                ),
            )
        ]
