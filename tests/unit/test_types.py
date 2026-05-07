"""Tests for core types."""

from synapt_eval.types import CategoryMetrics, EvalConfig, EvalResult, Fixture


def test_fixture_generic_content():
    fixture = Fixture(
        id="f1",
        category="retrieval",
        query="test query",
        expected=["a", "b"],
        user_history=[{"text": "hello", "date": "2026-01-01"}],
    )
    assert fixture.id == "f1"
    assert fixture.user_history is not None
    assert len(fixture.user_history) == 1


def test_fixture_without_history():
    fixture = Fixture(
        id="f2",
        category="generation",
        query="test",
        expected=["x"],
    )
    assert fixture.user_history is None


def test_eval_config_defaults():
    config = EvalConfig(
        fixtures_path="fixtures/",
        output_path="output/",
        categories=["retrieval", "generation"],
    )
    assert config.embedding_model is None
    assert config.api_endpoints == {}


def test_eval_result_construction():
    result = EvalResult(
        category="retrieval",
        metrics=CategoryMetrics(p_at_5=0.8, r_at_10=0.6, tau=0.5, n=10),
    )
    assert result.metrics.p_at_5 == 0.8
    assert result.per_fixture == []
