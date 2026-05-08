"""Tests for Reviewer SDK: framework, chain, and composition."""

import pytest

from synapt_eval.reviewer import (
    CheckResult,
    FrameworkReviewer,
    Predicate,
    Reviewer,
    ReviewerChain,
    Severity,
    Verdict,
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


class CurrentStatePredicate(Predicate):
    def check(self, output: str, expected: list[str], query: str) -> CheckResult:
        current_query = "current" in query.lower()
        history_leak = any(
            token in output.lower() for token in ["used to", "previously", "last week"]
        )
        return CheckResult(
            name="current_state",
            passed=not (current_query and history_leak),
            severity=SEVERITY_ERROR,
            reasoning="Response should stay grounded in current state",
        )


class TemporalAnchorPredicate(Predicate):
    def check(self, output: str, expected: list[str], query: str) -> CheckResult:
        asked_for_today = "today" in query.lower()
        stale_anchor = any(token in output.lower() for token in ["yesterday", "last week"])
        return CheckResult(
            name="temporal_anchor",
            passed=not (asked_for_today and stale_anchor),
            severity=SEVERITY_WARNING,
            reasoning="Temporal reference should match the query anchor",
        )


class ExpectedFacetPredicate(Predicate):
    def check(self, output: str, expected: list[str], query: str) -> CheckResult:
        found = any(e.lower() in output.lower() for e in expected)
        return CheckResult(
            name="expected_facet",
            passed=found,
            severity=SEVERITY_INFO,
            reasoning="Expected facet should be present in the response",
        )


class EmptyCheckReviewer(Reviewer):
    async def review(self, output: str, expected: list[str], query: str, **kwargs) -> Verdict:
        return Verdict(
            passed=True,
            reasoning="No signal",
            severity=SEVERITY_INFO,
            checks=[],
            score=1.0,
        )


class CustomTaggedReviewer(Reviewer):
    def __init__(self, name: str, passed: bool):
        self._name = name
        self._passed = passed

    async def review(self, output: str, expected: list[str], query: str, **kwargs) -> Verdict:
        severity = SEVERITY_INFO if self._passed else SEVERITY_ERROR
        return Verdict(
            passed=self._passed,
            reasoning=f"{self._name} {'passed' if self._passed else 'failed'}",
            severity=severity,
            checks=[
                CheckResult(
                    name=self._name,
                    passed=self._passed,
                    severity=severity,
                    reasoning="custom reviewer seam",
                )
            ],
            score=1.0 if self._passed else 0.0,
        )


TEMPORAL_CASES = [
    ("Current plan status today?", "The current status is green.", ["green"], set()),
    (
        "Current plan status today?",
        "It used to be green last week.",
        ["green"],
        {"current_state", "temporal_anchor"},
    ),
    (
        "What is the current deployment state?",
        "Previously stable, now degraded.",
        ["degraded"],
        {"current_state"},
    ),
    ("What changed today?", "Today the rollout is paused.", ["paused"], set()),
    (
        "What changed today?",
        "Yesterday it was paused and last week it was green.",
        ["paused"],
        {"temporal_anchor"},
    ),
    ("What is the current owner?", "The current owner is Atlas.", ["Atlas"], set()),
    (
        "What is the current owner?",
        "It used to be Apollo.",
        ["Apollo"],
        {"current_state"},
    ),
    ("What changed today?", "Current state is stable with no delta.", ["stable"], set()),
]


class TestReviewerAntagonists:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(("query", "output", "expected", "failed_names"), TEMPORAL_CASES)
    async def test_oss_safe_temporal_like_cases(self, query, output, expected, failed_names):
        reviewer = FrameworkReviewer(
            [
                CurrentStatePredicate(),
                TemporalAnchorPredicate(),
                ExpectedFacetPredicate(),
            ]
        )
        verdict = await reviewer.review(output, expected, query)
        observed = {check.name for check in verdict.checks if not check.passed}
        assert verdict.passed is (len(failed_names) == 0)
        assert observed == failed_names

    @pytest.mark.asyncio
    async def test_custom_reviewer_subclass_composes_cleanly(self):
        chain = ReviewerChain(
            [
                FrameworkReviewer([AlwaysPassPredicate("framework_ok")]),
                CustomTaggedReviewer("plugin_review", passed=False),
            ],
            strategy="strictest",
        )
        verdict = await chain.review("out", ["exp"], "q")
        assert not verdict.passed
        names = {check.name for check in verdict.checks}
        assert names == {"framework_ok", "plugin_review"}

    @pytest.mark.asyncio
    async def test_majority_with_empty_check_reviewer_is_deterministic(self):
        chain = ReviewerChain(
            [
                FrameworkReviewer([AlwaysPassPredicate("method_a")]),
                FrameworkReviewer([AlwaysFailPredicate("method_b")]),
                EmptyCheckReviewer(),
            ],
            strategy="majority",
        )
        verdict = await chain.review("out", ["exp"], "q")
        assert verdict.passed
        assert verdict.score == pytest.approx((1.0 + 0.0 + 1.0) / 3)
        names = {check.name for check in verdict.checks}
        assert names == {"method_a", "method_b"}
