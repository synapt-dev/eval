"""Generation suggestion rules."""

from __future__ import annotations

from typing import Any

from synapt_eval.reviewer.types import SEVERITY_ERROR, SEVERITY_WARNING, Verdict
from synapt_eval.suggestion_engine.types import Suggestion
from synapt_eval.types import EvalResult


class LowSuccessRateRule:
    """Flags when generation success rate drops below threshold."""

    categories = {"generation"}

    def __init__(self, threshold: float = 0.8) -> None:
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
                    f"Generation success rate is {result.metrics.p_at_5:.0%}, "
                    f"below threshold {self._threshold:.0%}"
                ),
                rule_name="low_success_rate",
                metric="success_rate",
                category=result.category,
                fix_hint="Check adapter error handling and API connectivity.",
            )
        ]


class HallucinationSignalRule:
    """Flags when judge verdicts indicate hallucinated content.

    Scans verdicts for judge checks with low scores, which may
    indicate the generation fabricated content not grounded in context.
    """

    categories = {"generation"}

    def __init__(self, score_threshold: float = 0.5) -> None:
        self._score_threshold = score_threshold

    def evaluate(
        self,
        result: EvalResult,
        verdicts: list[Verdict] | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[Suggestion]:
        if not verdicts:
            return []

        flagged = [
            v
            for v in verdicts
            if not v.passed and v.score is not None and v.score < self._score_threshold
        ]

        if not flagged:
            return []

        return [
            Suggestion(
                severity=SEVERITY_ERROR,
                message=(
                    f"{len(flagged)} verdict(s) scored below {self._score_threshold:.1f}, "
                    f"possible hallucination or fabricated content"
                ),
                rule_name="hallucination_signal",
                metric="judge_score",
                category=result.category,
                fix_hint=(
                    "Add grounding context to generation prompts; "
                    "consider retrieval-augmented generation or stricter guardrails."
                ),
            )
        ]


class VerdictFailureRule:
    """Creates suggestions from failed verdict checks.

    Generic rule that scans all verdict check results for failures
    and generates per-failure suggestions. Covers domain-specific
    checks (temporal drift, persona inconsistency, etc.) when the
    customer's reviewer chain includes those predicates.
    """

    def evaluate(
        self,
        result: EvalResult,
        verdicts: list[Verdict] | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[Suggestion]:
        if not verdicts:
            return []

        suggestions: list[Suggestion] = []
        for verdict in verdicts:
            for check in verdict.checks:
                if check.passed:
                    continue
                suggestions.append(
                    Suggestion(
                        severity=check.severity,
                        message=f"Check '{check.name}' failed: {check.reasoning}",
                        rule_name="verdict_failure",
                        category=result.category,
                    )
                )

        return suggestions
