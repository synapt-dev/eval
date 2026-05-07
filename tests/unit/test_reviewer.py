"""Tests for Reviewer SDK: framework, chain, and composition."""

import pytest

from synapt_eval.reviewer import (
    CheckResult,
    FrameworkReviewer,
    Predicate,
    ReviewerChain,
    Severity,
)
from synapt_eval.reviewer.types import (
    SEVERITY_CRITICAL,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
)


class AlwaysPassPredicate(Predicate):
    def __init__(self, name: str = "pass_check"):
        self._name = name

    def check(self, output: str, expected: list[str], query: str) -> CheckResult:
        return CheckResult(
            name=self._name,
            passed=True,
            severity=SEVERITY_INFO,
            reasoning="OK",
        )


class AlwaysFailPredicate(Predicate):
    def __init__(self, name: str = "fail_check", severity: Severity = SEVERITY_ERROR):
        self._name = name
        self._severity = severity

    def check(self, output: str, expected: list[str], query: str) -> CheckResult:
        return CheckResult(
            name=self._name,
            passed=False,
            severity=self._severity,
            reasoning="Failed",
        )


class ContainsExpectedPredicate(Predicate):
    def check(self, output: str, expected: list[str], query: str) -> CheckResult:
        found = any(e in output for e in expected)
        return CheckResult(
            name="contains_expected",
            passed=found,
            severity=SEVERITY_WARNING,
            reasoning=f"{'Found' if found else 'Missing'} expected content",
        )


class TestFrameworkReviewer:
    @pytest.mark.asyncio
    async def test_all_pass(self):
        reviewer = FrameworkReviewer([AlwaysPassPredicate(), AlwaysPassPredicate("p2")])
        verdict = await reviewer.review("output", ["expected"], "query")
        assert verdict.passed
        assert verdict.score == 1.0
        assert len(verdict.checks) == 2

    @pytest.mark.asyncio
    async def test_one_fails(self):
        reviewer = FrameworkReviewer([AlwaysPassPredicate(), AlwaysFailPredicate()])
        verdict = await reviewer.review("output", ["expected"], "query")
        assert not verdict.passed
        assert verdict.score == 0.5
        assert "fail_check" in verdict.reasoning

    @pytest.mark.asyncio
    async def test_all_fail(self):
        reviewer = FrameworkReviewer([AlwaysFailPredicate("f1"), AlwaysFailPredicate("f2")])
        verdict = await reviewer.review("output", ["expected"], "query")
        assert not verdict.passed
        assert verdict.score == 0.0

    @pytest.mark.asyncio
    async def test_severity_propagation(self):
        reviewer = FrameworkReviewer(
            [
                AlwaysFailPredicate("low", SEVERITY_WARNING),
                AlwaysFailPredicate("high", SEVERITY_CRITICAL),
            ]
        )
        verdict = await reviewer.review("output", ["expected"], "query")
        assert verdict.severity == SEVERITY_CRITICAL

    @pytest.mark.asyncio
    async def test_empty_predicates(self):
        reviewer = FrameworkReviewer([])
        verdict = await reviewer.review("output", ["expected"], "query")
        assert verdict.passed
        assert verdict.score == 1.0

    @pytest.mark.asyncio
    async def test_predicate_receives_args(self):
        reviewer = FrameworkReviewer([ContainsExpectedPredicate()])
        v1 = await reviewer.review("hello world", ["hello"], "q")
        assert v1.passed
        v2 = await reviewer.review("hello world", ["goodbye"], "q")
        assert not v2.passed


class TestReviewerChain:
    @pytest.mark.asyncio
    async def test_strictest_all_pass(self):
        chain = ReviewerChain(
            [
                FrameworkReviewer([AlwaysPassPredicate()]),
                FrameworkReviewer([AlwaysPassPredicate()]),
            ],
            strategy="strictest",
        )
        verdict = await chain.review("out", ["exp"], "q")
        assert verdict.passed

    @pytest.mark.asyncio
    async def test_strictest_one_fails(self):
        chain = ReviewerChain(
            [
                FrameworkReviewer([AlwaysPassPredicate()]),
                FrameworkReviewer([AlwaysFailPredicate()]),
            ],
            strategy="strictest",
        )
        verdict = await chain.review("out", ["exp"], "q")
        assert not verdict.passed

    @pytest.mark.asyncio
    async def test_majority_pass(self):
        chain = ReviewerChain(
            [
                FrameworkReviewer([AlwaysPassPredicate()]),
                FrameworkReviewer([AlwaysPassPredicate()]),
                FrameworkReviewer([AlwaysFailPredicate()]),
            ],
            strategy="majority",
        )
        verdict = await chain.review("out", ["exp"], "q")
        assert verdict.passed

    @pytest.mark.asyncio
    async def test_majority_fail(self):
        chain = ReviewerChain(
            [
                FrameworkReviewer([AlwaysFailPredicate()]),
                FrameworkReviewer([AlwaysFailPredicate()]),
                FrameworkReviewer([AlwaysPassPredicate()]),
            ],
            strategy="majority",
        )
        verdict = await chain.review("out", ["exp"], "q")
        assert not verdict.passed

    @pytest.mark.asyncio
    async def test_weighted_pass(self):
        pass_reviewer = FrameworkReviewer([AlwaysPassPredicate()])
        fail_reviewer = FrameworkReviewer([AlwaysFailPredicate("f", SEVERITY_INFO)])
        chain = ReviewerChain([pass_reviewer, fail_reviewer], strategy="weighted")
        verdict = await chain.review("out", ["exp"], "q")
        assert verdict.passed
        assert verdict.score >= 0.5

    @pytest.mark.asyncio
    async def test_weighted_fail(self):
        pass_reviewer = FrameworkReviewer([AlwaysPassPredicate()])
        fail_reviewer = FrameworkReviewer([AlwaysFailPredicate("f", SEVERITY_CRITICAL)])
        chain = ReviewerChain([pass_reviewer, fail_reviewer], strategy="weighted")
        verdict = await chain.review("out", ["exp"], "q")
        assert not verdict.passed

    @pytest.mark.asyncio
    async def test_empty_chain(self):
        chain = ReviewerChain([], strategy="strictest")
        verdict = await chain.review("out", ["exp"], "q")
        assert verdict.passed

    @pytest.mark.asyncio
    async def test_invalid_strategy(self):
        chain = ReviewerChain([FrameworkReviewer([])], strategy="unknown")
        with pytest.raises(ValueError, match="Unknown strategy"):
            await chain.review("out", ["exp"], "q")

    @pytest.mark.asyncio
    async def test_checks_aggregated(self):
        chain = ReviewerChain(
            [
                FrameworkReviewer([AlwaysPassPredicate("a"), AlwaysPassPredicate("b")]),
                FrameworkReviewer([AlwaysPassPredicate("c")]),
            ],
            strategy="strictest",
        )
        verdict = await chain.review("out", ["exp"], "q")
        assert len(verdict.checks) == 3
        names = {c.name for c in verdict.checks}
        assert names == {"a", "b", "c"}


class TestSeverityOrdering:
    def test_weight_ordering(self):
        assert SEVERITY_INFO.weight < SEVERITY_WARNING.weight
        assert SEVERITY_WARNING.weight < SEVERITY_ERROR.weight
        assert SEVERITY_ERROR.weight < SEVERITY_CRITICAL.weight

    def test_frozen(self):
        with pytest.raises(AttributeError):
            SEVERITY_INFO.weight = 99.0  # type: ignore[misc]
