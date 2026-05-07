"""Tests for suggestion engine: rules, engine, and registration."""

from typing import Any

from synapt_eval.reviewer.types import (
    SEVERITY_CRITICAL,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    CheckResult,
    Verdict,
)
from synapt_eval.suggestion_engine import (
    Suggestion,
    SuggestionEngine,
    SuggestionRule,
    suggestion_rule,
)
from synapt_eval.suggestion_engine.rules import (
    CategoryImbalanceRule,
    HallucinationSignalRule,
    HighNoResultsRule,
    LowPrecisionRule,
    LowRecallRule,
    LowSuccessRateRule,
    MonotonicDegradationRule,
    RegressionRule,
    StableLowRule,
    VerdictFailureRule,
)
from synapt_eval.types import CategoryMetrics, EvalResult, PerFixtureResult


def _result(
    category: str = "test",
    p5: float = 0.8,
    r10: float = 0.7,
    n: int = 10,
    per_fixture: list[PerFixtureResult] | None = None,
) -> EvalResult:
    return EvalResult(
        category=category,
        metrics=CategoryMetrics(p_at_5=p5, r_at_10=r10, n=n),
        per_fixture=per_fixture or [],
    )


def _per_fixture(fixture_id: str, score: float) -> PerFixtureResult:
    return PerFixtureResult(
        fixture_id=fixture_id,
        category="test",
        passed=score > 0,
        score=score,
    )


# ── Retrieval rules ──


class TestLowPrecisionRule:
    def test_below_threshold(self):
        suggestions = LowPrecisionRule(threshold=0.7).evaluate(_result(p5=0.5))
        assert len(suggestions) == 1
        assert suggestions[0].rule_name == "low_precision"
        assert suggestions[0].metric == "p_at_5"
        assert suggestions[0].fix_hint is not None

    def test_at_threshold(self):
        suggestions = LowPrecisionRule(threshold=0.7).evaluate(_result(p5=0.7))
        assert len(suggestions) == 0

    def test_above_threshold(self):
        suggestions = LowPrecisionRule(threshold=0.7).evaluate(_result(p5=0.9))
        assert len(suggestions) == 0

    def test_custom_threshold(self):
        suggestions = LowPrecisionRule(threshold=0.9).evaluate(_result(p5=0.85))
        assert len(suggestions) == 1


class TestLowRecallRule:
    def test_below_threshold(self):
        suggestions = LowRecallRule(threshold=0.6).evaluate(_result(r10=0.4))
        assert len(suggestions) == 1
        assert suggestions[0].rule_name == "low_recall"

    def test_at_threshold(self):
        suggestions = LowRecallRule(threshold=0.6).evaluate(_result(r10=0.6))
        assert len(suggestions) == 0


class TestHighNoResultsRule:
    def test_high_rate(self):
        fixtures = [_per_fixture(f"f{i}", 0.0) for i in range(3)]
        fixtures.extend([_per_fixture(f"f{i}", 0.8) for i in range(3, 10)])
        result = _result(per_fixture=fixtures)
        suggestions = HighNoResultsRule(threshold=0.1).evaluate(result)
        assert len(suggestions) == 1
        assert suggestions[0].rule_name == "high_no_results"

    def test_low_rate(self):
        fixtures = [_per_fixture("f0", 0.0)]
        fixtures.extend([_per_fixture(f"f{i}", 0.8) for i in range(1, 20)])
        result = _result(per_fixture=fixtures)
        suggestions = HighNoResultsRule(threshold=0.1).evaluate(result)
        assert len(suggestions) == 0

    def test_no_fixtures(self):
        suggestions = HighNoResultsRule().evaluate(_result())
        assert len(suggestions) == 0


# ── Generation rules ──


class TestLowSuccessRateRule:
    def test_below_threshold(self):
        suggestions = LowSuccessRateRule(threshold=0.8).evaluate(_result(p5=0.5))
        assert len(suggestions) == 1
        assert suggestions[0].rule_name == "low_success_rate"

    def test_above_threshold(self):
        suggestions = LowSuccessRateRule(threshold=0.8).evaluate(_result(p5=0.9))
        assert len(suggestions) == 0


class TestHallucinationSignalRule:
    def test_low_score_verdict(self):
        verdicts = [
            Verdict(passed=False, reasoning="fabricated", severity=SEVERITY_ERROR, score=0.2),
        ]
        suggestions = HallucinationSignalRule().evaluate(_result(), verdicts=verdicts)
        assert len(suggestions) == 1
        assert suggestions[0].rule_name == "hallucination_signal"

    def test_passing_verdicts(self):
        verdicts = [
            Verdict(passed=True, reasoning="good", severity=SEVERITY_INFO, score=0.9),
        ]
        suggestions = HallucinationSignalRule().evaluate(_result(), verdicts=verdicts)
        assert len(suggestions) == 0

    def test_no_verdicts(self):
        suggestions = HallucinationSignalRule().evaluate(_result())
        assert len(suggestions) == 0

    def test_custom_threshold(self):
        verdicts = [
            Verdict(passed=False, reasoning="weak", severity=SEVERITY_WARNING, score=0.4),
        ]
        suggestions = HallucinationSignalRule(score_threshold=0.3).evaluate(
            _result(), verdicts=verdicts
        )
        assert len(suggestions) == 0


class TestVerdictFailureRule:
    def test_failed_checks(self):
        verdicts = [
            Verdict(
                passed=False,
                reasoning="issues",
                severity=SEVERITY_ERROR,
                checks=[
                    CheckResult(
                        name="temporal",
                        passed=False,
                        severity=SEVERITY_WARNING,
                        reasoning="stale",
                    ),
                    CheckResult(name="relevance", passed=True, severity=SEVERITY_INFO),
                ],
            ),
        ]
        suggestions = VerdictFailureRule().evaluate(_result(), verdicts=verdicts)
        assert len(suggestions) == 1
        assert "temporal" in suggestions[0].message

    def test_all_passing(self):
        verdicts = [
            Verdict(
                passed=True,
                reasoning="ok",
                severity=SEVERITY_INFO,
                checks=[
                    CheckResult(name="check1", passed=True, severity=SEVERITY_INFO),
                ],
            ),
        ]
        suggestions = VerdictFailureRule().evaluate(_result(), verdicts=verdicts)
        assert len(suggestions) == 0

    def test_no_verdicts(self):
        suggestions = VerdictFailureRule().evaluate(_result())
        assert len(suggestions) == 0


# ── Cross-cutting rules ──


class TestRegressionRule:
    def test_regression_detected(self):
        result = _result(p5=0.65, r10=0.45)
        baseline = [_result(p5=0.80, r10=0.60)]
        suggestions = RegressionRule(regression_threshold=0.05).evaluate(
            result, context={"baseline": baseline}
        )
        assert len(suggestions) == 2
        assert all(s.rule_name == "regression" for s in suggestions)

    def test_no_regression(self):
        result = _result(p5=0.85, r10=0.70)
        baseline = [_result(p5=0.80, r10=0.65)]
        suggestions = RegressionRule().evaluate(result, context={"baseline": baseline})
        assert len(suggestions) == 0

    def test_no_baseline(self):
        suggestions = RegressionRule().evaluate(_result())
        assert len(suggestions) == 0


class TestCategoryImbalanceRule:
    def test_imbalanced(self):
        all_results = [
            _result("cat_a", n=100),
            _result("cat_b", n=10),
        ]
        suggestions = CategoryImbalanceRule(imbalance_ratio=3.0).evaluate(
            _result(), context={"all_results": all_results}
        )
        assert len(suggestions) == 1
        assert suggestions[0].rule_name == "category_imbalance"

    def test_balanced(self):
        all_results = [
            _result("cat_a", n=50),
            _result("cat_b", n=40),
        ]
        suggestions = CategoryImbalanceRule().evaluate(
            _result(), context={"all_results": all_results}
        )
        assert len(suggestions) == 0

    def test_no_context(self):
        suggestions = CategoryImbalanceRule().evaluate(_result())
        assert len(suggestions) == 0

    def test_single_category(self):
        suggestions = CategoryImbalanceRule().evaluate(
            _result(), context={"all_results": [_result()]}
        )
        assert len(suggestions) == 0


# ── Trending rules ──


class TestMonotonicDegradationRule:
    def test_degrading_trend(self):
        history = [
            _result("r", p5=0.80),
            _result("r", p5=0.75),
        ]
        current = _result("r", p5=0.70)
        suggestions = MonotonicDegradationRule(metric="p_at_5", consecutive=3).evaluate(
            current, context={"history": history}
        )
        assert len(suggestions) == 1
        assert suggestions[0].rule_name == "monotonic_degradation"

    def test_improving_trend(self):
        history = [
            _result("r", p5=0.70),
            _result("r", p5=0.75),
        ]
        current = _result("r", p5=0.80)
        suggestions = MonotonicDegradationRule(metric="p_at_5", consecutive=3).evaluate(
            current, context={"history": history}
        )
        assert len(suggestions) == 0

    def test_not_enough_history(self):
        history = [_result("r", p5=0.80)]
        current = _result("r", p5=0.70)
        suggestions = MonotonicDegradationRule(consecutive=3).evaluate(
            current, context={"history": history}
        )
        assert len(suggestions) == 0

    def test_no_history(self):
        suggestions = MonotonicDegradationRule().evaluate(_result())
        assert len(suggestions) == 0

    def test_different_categories_filtered(self):
        history = [
            _result("other", p5=0.80),
            _result("other", p5=0.75),
        ]
        current = _result("r", p5=0.70)
        suggestions = MonotonicDegradationRule(consecutive=3).evaluate(
            current, context={"history": history}
        )
        assert len(suggestions) == 0


class TestStableLowRule:
    def test_consistently_low(self):
        history = [
            _result("r", p5=0.50),
            _result("r", p5=0.55),
        ]
        current = _result("r", p5=0.52)
        suggestions = StableLowRule(metric="p_at_5", threshold=0.7, min_runs=3).evaluate(
            current, context={"history": history}
        )
        assert len(suggestions) == 1
        assert suggestions[0].rule_name == "stable_low"

    def test_improving_above_threshold(self):
        history = [
            _result("r", p5=0.50),
            _result("r", p5=0.60),
        ]
        current = _result("r", p5=0.75)
        suggestions = StableLowRule(threshold=0.7, min_runs=3).evaluate(
            current, context={"history": history}
        )
        assert len(suggestions) == 0

    def test_not_enough_runs(self):
        history = [_result("r", p5=0.50)]
        current = _result("r", p5=0.55)
        suggestions = StableLowRule(min_runs=3).evaluate(current, context={"history": history})
        assert len(suggestions) == 0


# ── Engine tests ──


class TestSuggestionEngine:
    def test_register_and_evaluate(self):
        engine = SuggestionEngine()
        engine.register(LowPrecisionRule(threshold=0.7))
        suggestions = engine.evaluate(_result(category="retrieval", p5=0.5))
        assert len(suggestions) == 1

    def test_category_scoping_skips_wrong_category(self):
        engine = SuggestionEngine()
        engine.register(LowPrecisionRule(threshold=0.7))
        suggestions = engine.evaluate(_result(category="generation", p5=0.5))
        assert len(suggestions) == 0

    def test_ordered_by_severity(self):
        engine = SuggestionEngine()
        engine.register(LowPrecisionRule(threshold=0.9))
        engine.register(HighNoResultsRule(threshold=0.0))
        result = _result(
            category="retrieval",
            p5=0.5,
            per_fixture=[_per_fixture("f1", 0.0), _per_fixture("f2", 0.8)],
        )
        suggestions = engine.evaluate(result)
        assert len(suggestions) == 2
        assert suggestions[0].severity.weight >= suggestions[1].severity.weight

    def test_with_defaults(self):
        engine = SuggestionEngine.with_defaults()
        assert len(engine.rules) == 10

    def test_evaluate_all(self):
        engine = SuggestionEngine()
        engine.register(LowPrecisionRule(threshold=0.7))
        results = [_result("retrieval", p5=0.5), _result("retrieval", p5=0.9)]
        suggestions = engine.evaluate_all(results)
        assert len(suggestions) == 1
        assert suggestions[0].category == "retrieval"

    def test_empty_engine(self):
        engine = SuggestionEngine()
        suggestions = engine.evaluate(_result())
        assert len(suggestions) == 0


# ── Decorator / registration tests ──


class TestSuggestionRuleDecorator:
    def test_functional_rule(self):
        @suggestion_rule(name="custom_check")
        def check_custom(
            result: EvalResult,
            verdicts: list[Verdict] | None = None,
            context: dict[str, Any] | None = None,
        ) -> list[Suggestion]:
            if result.metrics.p_at_5 < 0.5:
                return [
                    Suggestion(
                        severity=SEVERITY_CRITICAL,
                        message="Very low precision",
                        rule_name="custom_check",
                    )
                ]
            return []

        suggestions = check_custom.evaluate(_result(p5=0.3))
        assert len(suggestions) == 1
        assert suggestions[0].rule_name == "custom_check"

    def test_applies_to_filter(self):
        @suggestion_rule(applies_to="retrieval")
        def retrieval_only(result, verdicts=None, context=None):
            return [
                Suggestion(
                    severity=SEVERITY_INFO,
                    message="matched",
                    rule_name="retrieval_only",
                )
            ]

        assert len(retrieval_only.evaluate(_result(category="retrieval"))) == 1
        assert len(retrieval_only.evaluate(_result(category="generation"))) == 0

    def test_protocol_conformance(self):
        @suggestion_rule()
        def my_rule(result, verdicts=None, context=None):
            return []

        assert isinstance(my_rule, SuggestionRule)

    def test_register_functional_rule(self):
        @suggestion_rule(name="pro_pack_rule")
        def pro_rule(result, verdicts=None, context=None):
            if result.metrics.n > 100:
                return [
                    Suggestion(
                        severity=SEVERITY_WARNING,
                        message="Large fixture set",
                        rule_name="pro_pack_rule",
                    )
                ]
            return []

        engine = SuggestionEngine()
        engine.register(pro_rule)
        suggestions = engine.evaluate(_result(n=200))
        assert len(suggestions) == 1

    def test_class_based_custom_rule(self):
        class CustomRule:
            def evaluate(self, result, verdicts=None, context=None):
                return [
                    Suggestion(
                        severity=SEVERITY_INFO,
                        message="custom",
                        rule_name="custom",
                    )
                ]

        engine = SuggestionEngine()
        engine.register(CustomRule())
        assert len(engine.evaluate(_result())) == 1


# ── Integration test ──


class TestIntegration:
    def test_full_pipeline(self):
        engine = SuggestionEngine.with_defaults()

        result = _result(
            category="retrieval",
            p5=0.5,
            r10=0.4,
            n=10,
            per_fixture=[
                _per_fixture("f1", 0.0),
                _per_fixture("f2", 0.0),
                _per_fixture("f3", 0.0),
                _per_fixture("f4", 0.8),
                _per_fixture("f5", 0.7),
            ],
        )

        verdicts = [
            Verdict(
                passed=False,
                reasoning="fabricated content",
                severity=SEVERITY_ERROR,
                checks=[
                    CheckResult(
                        name="grounding",
                        passed=False,
                        severity=SEVERITY_ERROR,
                        reasoning="content not in context",
                    ),
                ],
                score=0.2,
            ),
        ]

        baseline = [_result(category="retrieval", p5=0.8, r10=0.7)]

        suggestions = engine.evaluate(
            result,
            verdicts=verdicts,
            context={"baseline": baseline},
        )

        assert len(suggestions) > 0
        rule_names = {s.rule_name for s in suggestions}
        assert "low_precision" in rule_names
        assert "low_recall" in rule_names
        assert "high_no_results" in rule_names
        assert "hallucination_signal" not in rule_names
        assert "verdict_failure" in rule_names
        assert "regression" in rule_names
        assert suggestions[0].severity.weight >= suggestions[-1].severity.weight
