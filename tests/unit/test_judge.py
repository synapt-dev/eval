"""Tests for judge adapter, parsing, and JudgingReviewer bridge."""

import pytest

from synapt_eval.adapters.judge_adapter import JudgeAdapter, JudgeRequest, JudgeResponse
from synapt_eval.judges.parsing import parse_judge_json
from synapt_eval.reviewer.bridge import JudgingReviewer
from synapt_eval.reviewer.chain import ReviewerChain
from synapt_eval.reviewer.framework import FrameworkReviewer
from synapt_eval.reviewer.types import SEVERITY_ERROR, SEVERITY_INFO, SEVERITY_WARNING, CheckResult


class MockJudge(JudgeAdapter):
    def __init__(self, response: JudgeResponse):
        self._response = response

    async def judge(self, request: JudgeRequest) -> JudgeResponse:
        return self._response


class FailingJudge(JudgeAdapter):
    async def judge(self, request: JudgeRequest) -> JudgeResponse:
        raise RuntimeError("judge unavailable")


class AlwaysPassPredicate:
    def check(self, output: str, expected: list[str], query: str) -> CheckResult:
        return CheckResult(name="pass", passed=True, severity=SEVERITY_INFO)


class TestJudgeTypes:
    def test_request_creation(self):
        req = JudgeRequest(query="q", expected=["a"], actual="b")
        assert req.query == "q"
        assert req.rubric is None
        assert req.context is None

    def test_request_with_rubric(self):
        req = JudgeRequest(query="q", expected=["a"], actual="b", rubric="accuracy")
        assert req.rubric == "accuracy"

    def test_response_defaults(self):
        resp = JudgeResponse(passed=True, score=0.9, reasoning="good")
        assert resp.raw == {}


class TestParseJudgeJson:
    def test_valid_json(self):
        resp = parse_judge_json('{"passed": true, "score": 0.85, "reasoning": "correct"}')
        assert resp.passed is True
        assert resp.score == 0.85
        assert resp.reasoning == "correct"

    def test_markdown_fences(self):
        resp = parse_judge_json('```json\n{"passed": true, "score": 0.9, "reasoning": "ok"}\n```')
        assert resp.passed is True
        assert resp.score == 0.9

    def test_malformed_json(self):
        resp = parse_judge_json("this is not json")
        assert resp.passed is False
        assert resp.score == 0.0
        assert "Failed to parse" in resp.reasoning

    def test_missing_fields(self):
        resp = parse_judge_json('{"score": 0.5}')
        assert resp.passed is False
        assert resp.score == 0.5

    def test_string_passed_field(self):
        resp = parse_judge_json('{"passed": "yes", "score": 0.8, "reasoning": "ok"}')
        assert resp.passed is True

    def test_string_false_field(self):
        resp = parse_judge_json('{"passed": "no", "score": 0.2, "reasoning": "bad"}')
        assert resp.passed is False

    def test_score_clamped(self):
        resp = parse_judge_json('{"passed": true, "score": 1.5, "reasoning": "over"}')
        assert resp.score == 1.0

    def test_negative_score_clamped(self):
        resp = parse_judge_json('{"passed": false, "score": -0.5, "reasoning": "under"}')
        assert resp.score == 0.0

    def test_explanation_fallback(self):
        resp = parse_judge_json('{"passed": true, "score": 1.0, "explanation": "alt key"}')
        assert resp.reasoning == "alt key"

    def test_not_a_dict(self):
        resp = parse_judge_json("[1, 2, 3]")
        assert resp.passed is False
        assert "not a JSON object" in resp.reasoning

    def test_missing_score_defaults(self):
        resp = parse_judge_json('{"passed": true, "reasoning": "ok"}')
        assert resp.passed is True
        assert resp.score == 1.0

    def test_failed_missing_score_defaults_zero(self):
        resp = parse_judge_json('{"passed": false, "reasoning": "bad"}')
        assert resp.passed is False
        assert resp.score == 0.0

    def test_empty_string(self):
        resp = parse_judge_json("")
        assert resp.passed is False


class TestJudgingReviewer:
    @pytest.mark.asyncio
    async def test_pass_through(self):
        judge = MockJudge(JudgeResponse(passed=True, score=0.9, reasoning="correct"))
        reviewer = JudgingReviewer(judge)
        verdict = await reviewer.review("answer", ["expected"], "query")
        assert verdict.passed
        assert verdict.score == 0.9
        assert len(verdict.checks) == 1
        assert verdict.checks[0].name == "llm_judge"

    @pytest.mark.asyncio
    async def test_fail_through(self):
        judge = MockJudge(JudgeResponse(passed=False, score=0.2, reasoning="wrong"))
        reviewer = JudgingReviewer(judge)
        verdict = await reviewer.review("answer", ["expected"], "query")
        assert not verdict.passed
        assert verdict.severity == SEVERITY_ERROR

    @pytest.mark.asyncio
    async def test_custom_severity(self):
        judge = MockJudge(JudgeResponse(passed=False, score=0.0, reasoning="bad"))
        reviewer = JudgingReviewer(judge, severity=SEVERITY_WARNING)
        verdict = await reviewer.review("answer", ["expected"], "query")
        assert verdict.severity == SEVERITY_WARNING

    @pytest.mark.asyncio
    async def test_pass_verdict_info_severity(self):
        judge = MockJudge(JudgeResponse(passed=True, score=1.0, reasoning="good"))
        reviewer = JudgingReviewer(judge, severity=SEVERITY_ERROR)
        verdict = await reviewer.review("answer", ["expected"], "query")
        assert verdict.severity == SEVERITY_INFO

    @pytest.mark.asyncio
    async def test_kwargs_forwarded(self):
        class CapturingJudge(JudgeAdapter):
            def __init__(self):
                self.last_request: JudgeRequest | None = None

            async def judge(self, request: JudgeRequest) -> JudgeResponse:
                self.last_request = request
                return JudgeResponse(passed=True, score=1.0, reasoning="ok")

        judge = CapturingJudge()
        reviewer = JudgingReviewer(judge)
        await reviewer.review("out", ["exp"], "q", rubric="accuracy", context={"k": "v"})
        assert judge.last_request is not None
        assert judge.last_request.rubric == "accuracy"
        assert judge.last_request.context == {"k": "v"}

    @pytest.mark.asyncio
    async def test_refusal_reasoning_preserved(self):
        judge = MockJudge(
            JudgeResponse(
                passed=False,
                score=0.0,
                reasoning="I cannot verify this from the provided context.",
            )
        )
        reviewer = JudgingReviewer(judge)
        verdict = await reviewer.review("answer", ["expected"], "query")
        assert not verdict.passed
        assert "cannot verify" in verdict.reasoning
        assert verdict.checks[0].reasoning == verdict.reasoning

    @pytest.mark.asyncio
    async def test_high_score_clamped_at_bridge(self):
        judge = MockJudge(JudgeResponse(passed=True, score=1.5, reasoning="overconfident"))
        reviewer = JudgingReviewer(judge)
        verdict = await reviewer.review("answer", ["expected"], "query")
        assert verdict.score == 1.0

    @pytest.mark.asyncio
    async def test_negative_score_clamped_at_bridge(self):
        judge = MockJudge(JudgeResponse(passed=False, score=-0.25, reasoning="undershot"))
        reviewer = JudgingReviewer(judge)
        verdict = await reviewer.review("answer", ["expected"], "query")
        assert verdict.score == 0.0


class TestJudgeInChain:
    @pytest.mark.asyncio
    async def test_judge_plus_predicate_chain(self):
        judge = MockJudge(JudgeResponse(passed=True, score=0.9, reasoning="good"))
        chain = ReviewerChain(
            [
                JudgingReviewer(judge),
                FrameworkReviewer([AlwaysPassPredicate()]),
            ],
            strategy="strictest",
        )
        verdict = await chain.review("answer", ["expected"], "query")
        assert verdict.passed
        assert len(verdict.checks) == 2

    @pytest.mark.asyncio
    async def test_judge_fails_chain(self):
        judge = MockJudge(JudgeResponse(passed=False, score=0.1, reasoning="bad"))
        chain = ReviewerChain(
            [
                JudgingReviewer(judge),
                FrameworkReviewer([AlwaysPassPredicate()]),
            ],
            strategy="strictest",
        )
        verdict = await chain.review("answer", ["expected"], "query")
        assert not verdict.passed

    @pytest.mark.asyncio
    async def test_ensemble_via_chain(self):
        """Multi-judge ensemble = multiple JudgingReviewers in a majority chain."""
        j1 = MockJudge(JudgeResponse(passed=True, score=0.9, reasoning="good"))
        j2 = MockJudge(JudgeResponse(passed=True, score=0.8, reasoning="ok"))
        j3 = MockJudge(JudgeResponse(passed=False, score=0.3, reasoning="bad"))
        chain = ReviewerChain(
            [JudgingReviewer(j1), JudgingReviewer(j2), JudgingReviewer(j3)],
            strategy="majority",
        )
        verdict = await chain.review("answer", ["expected"], "query")
        assert verdict.passed
