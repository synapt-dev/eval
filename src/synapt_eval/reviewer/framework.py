"""FrameworkReviewer: multi-method triangulation via chained predicates."""

from __future__ import annotations

from typing import Any

from synapt_eval.reviewer.protocol import Predicate, Reviewer
from synapt_eval.reviewer.types import (
    SEVERITY_INFO,
    CheckResult,
    Verdict,
)


class FrameworkReviewer(Reviewer):
    """Chains predicates with severity and composes verdicts.

    Each predicate runs independently. The final verdict fails if any
    predicate fails; the severity is the worst among failures.
    """

    def __init__(self, predicates: list[Predicate]) -> None:
        self._predicates = predicates

    async def review(
        self,
        output: str,
        expected: list[str],
        query: str,
        **kwargs: Any,
    ) -> Verdict:
        checks: list[CheckResult] = [p.check(output, expected, query) for p in self._predicates]

        failed = [c for c in checks if not c.passed]

        if not failed:
            return Verdict(
                passed=True,
                reasoning="All checks passed",
                severity=SEVERITY_INFO,
                checks=checks,
                score=1.0,
            )

        worst = max(failed, key=lambda c: c.severity.weight)
        score = sum(1 for c in checks if c.passed) / len(checks) if checks else 0.0

        return Verdict(
            passed=False,
            reasoning=f"{len(failed)} check(s) failed: {', '.join(c.name for c in failed)}",
            severity=worst.severity,
            checks=checks,
            score=score,
        )
