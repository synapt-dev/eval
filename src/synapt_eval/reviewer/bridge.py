"""JudgingReviewer: bridges JudgeAdapter into the Reviewer protocol."""

from __future__ import annotations

from typing import Any

from synapt_eval.adapters.judge_adapter import JudgeAdapter, JudgeRequest
from synapt_eval.reviewer.protocol import Reviewer
from synapt_eval.reviewer.types import (
    SEVERITY_ERROR,
    SEVERITY_INFO,
    CheckResult,
    Severity,
    Verdict,
)


class JudgingReviewer(Reviewer):
    """Wraps a JudgeAdapter so it can participate in a ReviewerChain.

    This bridge lets LLM judges compose with predicate-based reviewers
    in the same chain, sharing a common Verdict interface.
    """

    def __init__(
        self,
        judge: JudgeAdapter,
        severity: Severity | None = None,
    ) -> None:
        self._judge = judge
        self._severity = severity or SEVERITY_ERROR

    async def review(
        self,
        output: str,
        expected: list[str],
        query: str,
        **kwargs: Any,
    ) -> Verdict:
        request = JudgeRequest(
            query=query,
            expected=expected,
            actual=output,
            rubric=kwargs.get("rubric"),
            context=kwargs.get("context"),
        )
        response = await self._judge.judge(request)

        check = CheckResult(
            name="llm_judge",
            passed=response.passed,
            severity=self._severity,
            reasoning=response.reasoning,
        )

        score = max(0.0, min(1.0, response.score)) if response.score is not None else None

        return Verdict(
            passed=response.passed,
            reasoning=response.reasoning,
            severity=self._severity if not response.passed else SEVERITY_INFO,
            checks=[check],
            score=score,
        )
