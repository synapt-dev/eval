"""ReviewerChain: composes multiple reviewers with conflict resolution."""

from __future__ import annotations

from typing import Any

from synapt_eval.reviewer.protocol import Reviewer
from synapt_eval.reviewer.types import (
    SEVERITY_INFO,
    Verdict,
)


class ReviewerChain(Reviewer):
    """Composes multiple reviewers with configurable conflict resolution.

    Strategies:
    - "strictest": any reviewer failure fails the chain (AND logic)
    - "majority": pass if >50% of reviewers pass
    - "weighted": weighted average of scores using severity weights
    """

    def __init__(
        self,
        reviewers: list[Reviewer],
        strategy: str = "strictest",
    ) -> None:
        self._reviewers = reviewers
        self._strategy = strategy

    async def review(
        self,
        output: str,
        expected: list[str],
        query: str,
        **kwargs: Any,
    ) -> Verdict:
        verdicts: list[Verdict] = []
        for reviewer in self._reviewers:
            verdict = await reviewer.review(output, expected, query, **kwargs)
            verdicts.append(verdict)
        return self._resolve(verdicts)

    def _resolve(self, verdicts: list[Verdict]) -> Verdict:
        if not verdicts:
            return Verdict(
                passed=True,
                reasoning="No reviewers in chain",
                severity=SEVERITY_INFO,
            )

        all_checks = [c for v in verdicts for c in v.checks]
        avg_score = sum(v.score for v in verdicts) / len(verdicts)

        if self._strategy == "strictest":
            return self._resolve_strictest(verdicts, all_checks, avg_score)
        elif self._strategy == "majority":
            return self._resolve_majority(verdicts, all_checks, avg_score)
        elif self._strategy == "weighted":
            return self._resolve_weighted(verdicts, all_checks)
        else:
            raise ValueError(f"Unknown strategy: {self._strategy}")

    def _resolve_strictest(
        self,
        verdicts: list[Verdict],
        all_checks: list,
        avg_score: float,
    ) -> Verdict:
        failed = [v for v in verdicts if not v.passed]
        if not failed:
            return Verdict(
                passed=True,
                reasoning="All reviewers passed",
                severity=SEVERITY_INFO,
                checks=all_checks,
                score=avg_score,
            )
        worst = max(failed, key=lambda v: v.severity.weight)
        reasons = [v.reasoning for v in failed]
        return Verdict(
            passed=False,
            reasoning=f"{len(failed)} reviewer(s) failed: {'; '.join(reasons)}",
            severity=worst.severity,
            checks=all_checks,
            score=avg_score,
        )

    def _resolve_majority(
        self,
        verdicts: list[Verdict],
        all_checks: list,
        avg_score: float,
    ) -> Verdict:
        pass_count = sum(1 for v in verdicts if v.passed)
        passed = pass_count > len(verdicts) / 2
        if passed:
            return Verdict(
                passed=True,
                reasoning=f"Majority passed ({pass_count}/{len(verdicts)})",
                severity=SEVERITY_INFO,
                checks=all_checks,
                score=avg_score,
            )
        failed = [v for v in verdicts if not v.passed]
        worst = max(failed, key=lambda v: v.severity.weight)
        return Verdict(
            passed=False,
            reasoning=f"Majority failed ({len(failed)}/{len(verdicts)})",
            severity=worst.severity,
            checks=all_checks,
            score=avg_score,
        )

    def _resolve_weighted(
        self,
        verdicts: list[Verdict],
        all_checks: list,
    ) -> Verdict:
        total_weight = sum(v.severity.weight for v in verdicts)
        if total_weight == 0:
            return Verdict(
                passed=True,
                reasoning="No weighted signal",
                severity=SEVERITY_INFO,
                checks=all_checks,
                score=1.0,
            )
        weighted_score = sum(v.score * v.severity.weight for v in verdicts) / total_weight
        passed = weighted_score >= 0.5
        worst_failing = [v for v in verdicts if not v.passed]
        severity = (
            max(worst_failing, key=lambda v: v.severity.weight).severity
            if worst_failing
            else SEVERITY_INFO
        )
        return Verdict(
            passed=passed,
            reasoning=f"Weighted score: {weighted_score:.2f}",
            severity=severity,
            checks=all_checks,
            score=weighted_score,
        )
