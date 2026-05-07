"""Tests for report card: compose, markdown, and JSON rendering."""

import json

from synapt_eval.report_card import (
    compose_report_card,
    generate_json,
    generate_json_string,
    generate_markdown,
)
from synapt_eval.reviewer.types import SEVERITY_ERROR, SEVERITY_INFO, SEVERITY_WARNING
from synapt_eval.suggestion_engine.types import Suggestion
from synapt_eval.types import CategoryMetrics, EvalResult


def _result(
    category: str = "retrieval",
    p5: float = 0.8,
    r10: float = 0.7,
    tau: float | None = None,
    n: int = 10,
) -> EvalResult:
    return EvalResult(
        category=category,
        metrics=CategoryMetrics(p_at_5=p5, r_at_10=r10, tau=tau, n=n),
    )


def _suggestion(
    rule: str = "test_rule",
    message: str = "test message",
    severity_level: str = "warning",
    category: str | None = "retrieval",
) -> Suggestion:
    severity_map = {
        "error": SEVERITY_ERROR,
        "warning": SEVERITY_WARNING,
        "info": SEVERITY_INFO,
    }
    return Suggestion(
        severity=severity_map[severity_level],
        message=message,
        rule_name=rule,
        metric="p_at_5",
        category=category,
        fix_hint="Try improving this.",
    )


# -- Compose tests --


class TestComposeReportCard:
    def test_basic_compose(self):
        results = [_result("retrieval", 0.8, 0.7, n=10)]
        card = compose_report_card(results)
        assert card.header.fixture_count == 10
        assert card.header.category_count == 1
        assert card.footer.passed is True
        assert len(card.sections) == 1

    def test_with_suggestions(self):
        results = [_result()]
        suggestions = [_suggestion(severity_level="warning")]
        card = compose_report_card(results, suggestions=suggestions)
        assert card.footer.total_suggestions == 1
        assert card.footer.warning_count == 1
        assert len(card.sections[0].suggestions) == 1

    def test_with_error_suggestions_fails(self):
        results = [_result()]
        suggestions = [_suggestion(severity_level="error")]
        card = compose_report_card(results, suggestions=suggestions)
        assert not card.footer.passed

    def test_with_baseline_no_regression(self):
        results = [_result("r", 0.85, 0.70)]
        baseline = [_result("r", 0.80, 0.65)]
        card = compose_report_card(results, baseline=baseline)
        assert card.footer.passed is True
        assert card.footer.regression_summary is None
        assert len(card.footer.deltas) > 0

    def test_with_baseline_regression(self):
        results = [_result("r", 0.60, 0.40)]
        baseline = [_result("r", 0.80, 0.70)]
        card = compose_report_card(results, baseline=baseline)
        assert not card.footer.passed
        assert card.footer.regression_summary is not None

    def test_with_history(self):
        results = [_result("r")]
        history = [_result("r", 0.75, 0.65), _result("r", 0.78, 0.68)]
        card = compose_report_card(results, history=history)
        assert len(card.trending) == 2

    def test_custom_metadata(self):
        card = compose_report_card(
            [_result()],
            run_id="test-run-001",
            timestamp="2026-05-07T20:00:00Z",
            commit="abc123",
            config={"model": "gpt-4o"},
        )
        assert card.header.run_id == "test-run-001"
        assert card.header.commit == "abc123"
        assert card.header.config["model"] == "gpt-4o"

    def test_multiple_categories(self):
        results = [
            _result("retrieval", n=20),
            _result("generation", n=30),
        ]
        card = compose_report_card(results)
        assert card.header.fixture_count == 50
        assert card.header.category_count == 2
        assert len(card.sections) == 2

    def test_global_suggestions(self):
        results = [_result()]
        suggestions = [_suggestion(category=None, rule="global_rule")]
        card = compose_report_card(results, suggestions=suggestions)
        assert len(card.sections[0].suggestions) == 0
        assert len(card.suggestions) == 1

    def test_severity_counts(self):
        suggestions = [
            _suggestion(severity_level="error"),
            _suggestion(severity_level="error"),
            _suggestion(severity_level="warning"),
            _suggestion(severity_level="info"),
        ]
        card = compose_report_card([_result()], suggestions=suggestions)
        assert card.header.severity_counts["error"] == 2
        assert card.header.severity_counts["warning"] == 1
        assert card.header.severity_counts["info"] == 1


# -- Markdown tests --


class TestGenerateMarkdown:
    def test_header_present(self):
        card = compose_report_card(
            [_result()],
            run_id="RUN-001",
            commit="abc123",
        )
        md = generate_markdown(card)
        assert "# Eval Report Card" in md
        assert "RUN-001" in md
        assert "abc123" in md

    def test_category_metrics_table(self):
        card = compose_report_card([_result("retrieval", 0.85, 0.72, 0.5)])
        md = generate_markdown(card)
        assert "## retrieval" in md
        assert "| P@5 | 0.850 |" in md
        assert "| R@10 | 0.720 |" in md
        assert "| Tau | 0.500 |" in md

    def test_no_tau_when_none(self):
        card = compose_report_card([_result("retrieval", tau=None)])
        md = generate_markdown(card)
        assert "Tau" not in md

    def test_suggestions_inline(self):
        suggestions = [
            _suggestion(
                rule="low_precision",
                message="P@5 is 0.50",
                severity_level="warning",
            )
        ]
        card = compose_report_card([_result()], suggestions=suggestions)
        md = generate_markdown(card)
        assert "[WARNING]" in md
        assert "low_precision" in md
        assert "P@5 is 0.50" in md
        assert "Try improving this." in md

    def test_suggestions_summary_table(self):
        suggestions = [
            _suggestion(rule="rule_a", severity_level="error"),
            _suggestion(rule="rule_b", severity_level="warning"),
        ]
        card = compose_report_card([_result()], suggestions=suggestions)
        md = generate_markdown(card)
        assert "## Suggestions Summary" in md
        assert "rule_a" in md
        assert "rule_b" in md

    def test_footer_passed(self):
        card = compose_report_card([_result()])
        md = generate_markdown(card)
        assert "**PASSED**" in md

    def test_footer_failed(self):
        suggestions = [_suggestion(severity_level="error")]
        card = compose_report_card([_result()], suggestions=suggestions)
        md = generate_markdown(card)
        assert "**FAILED**" in md

    def test_regression_deltas_table(self):
        results = [_result("r", 0.60, 0.40)]
        baseline = [_result("r", 0.80, 0.70)]
        card = compose_report_card(results, baseline=baseline)
        md = generate_markdown(card)
        assert "### Regression Deltas" in md
        assert "[REGRESSION]" in md

    def test_trending_section(self):
        results = [_result("r")]
        history = [
            _result("r", 0.75, 0.65),
            _result("r", 0.78, 0.68),
        ]
        card = compose_report_card(results, history=history)
        md = generate_markdown(card)
        assert "## Trending" in md
        assert "P_AT_5" in md

    def test_no_trending_when_empty(self):
        card = compose_report_card([_result()])
        md = generate_markdown(card)
        assert "## Trending" not in md

    def test_severity_header(self):
        suggestions = [
            _suggestion(severity_level="error"),
            _suggestion(severity_level="warning"),
        ]
        card = compose_report_card([_result()], suggestions=suggestions)
        md = generate_markdown(card)
        assert "1 ERROR" in md
        assert "1 WARNING" in md


# -- JSON tests --


class TestGenerateJson:
    def test_schema_version(self):
        card = compose_report_card([_result()])
        data = generate_json(card)
        assert data["schema_version"] == "1.0"

    def test_basic_structure(self):
        card = compose_report_card([_result()], run_id="R1", commit="abc")
        data = generate_json(card)
        assert data["run_id"] == "R1"
        assert data["commit"] == "abc"
        assert data["passed"] is True
        assert "summary" in data
        assert "sections" in data
        assert "suggestions" in data
        assert "regression" in data

    def test_summary_counts(self):
        suggestions = [
            _suggestion(severity_level="error"),
            _suggestion(severity_level="warning"),
        ]
        card = compose_report_card([_result()], suggestions=suggestions)
        data = generate_json(card)
        assert data["summary"]["error_count"] == 1
        assert data["summary"]["warning_count"] == 1
        assert data["summary"]["total_suggestions"] == 2

    def test_section_metrics(self):
        card = compose_report_card([_result("retrieval", 0.85, 0.72, 0.5, 20)])
        data = generate_json(card)
        section = data["sections"][0]
        assert section["category"] == "retrieval"
        assert section["metrics"]["p_at_5"] == 0.85
        assert section["metrics"]["r_at_10"] == 0.72
        assert section["metrics"]["tau"] == 0.5
        assert section["fixture_count"] == 20

    def test_suggestions_serialized(self):
        suggestions = [_suggestion(rule="my_rule")]
        card = compose_report_card([_result()], suggestions=suggestions)
        data = generate_json(card)
        assert len(data["suggestions"]) == 1
        s = data["suggestions"][0]
        assert s["rule_name"] == "my_rule"
        assert s["severity"] == "warning"
        assert "severity_weight" in s
        assert s["fix_hint"] == "Try improving this."

    def test_regression_data(self):
        results = [_result("r", 0.60, 0.40)]
        baseline = [_result("r", 0.80, 0.70)]
        card = compose_report_card(results, baseline=baseline)
        data = generate_json(card)
        assert data["regression"]["has_regression"] is True
        assert len(data["regression"]["deltas"]) > 0

    def test_no_regression(self):
        card = compose_report_card([_result()])
        data = generate_json(card)
        assert data["regression"]["has_regression"] is False
        assert data["regression"]["deltas"] == []

    def test_trending_null_when_empty(self):
        card = compose_report_card([_result()])
        data = generate_json(card)
        assert data["trending"] is None

    def test_trending_populated(self):
        history = [_result("r", 0.75, 0.65)]
        card = compose_report_card([_result()], history=history)
        data = generate_json(card)
        assert data["trending"] is not None
        assert len(data["trending"]) == 1
        assert "metrics" in data["trending"][0]

    def test_json_string_valid(self):
        card = compose_report_card([_result()])
        json_str = generate_json_string(card)
        parsed = json.loads(json_str)
        assert parsed["schema_version"] == "1.0"

    def test_config_preserved(self):
        card = compose_report_card([_result()], config={"model": "gpt-4o"})
        data = generate_json(card)
        assert data["config"]["model"] == "gpt-4o"


# -- Integration test --


class TestReportCardIntegration:
    def test_full_pipeline(self):
        results = [
            _result("retrieval", 0.75, 0.60, 0.45, 20),
            _result("generation", 0.90, 0.80, n=15),
        ]
        suggestions = [
            _suggestion("low_precision", "P@5 low", "warning", "retrieval"),
            _suggestion("regression", "p_at_5 regressed", "error", "retrieval"),
        ]
        baseline = [
            _result("retrieval", 0.85, 0.70),
            _result("generation", 0.88, 0.78),
        ]
        history = [
            _result("retrieval", 0.82, 0.68),
            _result("retrieval", 0.80, 0.66),
        ]

        card = compose_report_card(
            results,
            suggestions=suggestions,
            baseline=baseline,
            history=history,
            run_id="integration-test",
            commit="def456",
        )

        md = generate_markdown(card)
        assert "# Eval Report Card" in md
        assert "integration-test" in md
        assert "def456" in md
        assert "## retrieval" in md
        assert "## generation" in md
        assert "## Suggestions Summary" in md
        assert "**FAILED**" in md

        data = generate_json(card)
        assert data["schema_version"] == "1.0"
        assert data["run_id"] == "integration-test"
        assert not data["passed"]
        assert len(data["sections"]) == 2
        assert data["summary"]["fixture_count"] == 35
        assert data["regression"]["has_regression"] is True
        assert data["trending"] is not None
