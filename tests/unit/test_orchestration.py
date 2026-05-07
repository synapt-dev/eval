"""Tests for orchestration: run envelope, deltas, PR gate."""

import json
from pathlib import Path

from synapt_eval.runner.orchestration import (
    RunEnvelope,
    compute_deltas,
    has_regressions,
    load_baseline,
    pr_gate,
)
from synapt_eval.types import CategoryMetrics, EvalResult


def _make_result(category: str, p5: float, r10: float, tau: float | None = None) -> EvalResult:
    return EvalResult(
        category=category,
        metrics=CategoryMetrics(p_at_5=p5, r_at_10=r10, tau=tau, n=10),
    )


class TestRunEnvelope:
    def test_create(self):
        results = [_make_result("retrieval", 0.8, 0.6)]
        envelope = RunEnvelope.create(results)
        assert envelope.run_id
        assert envelope.timestamp
        assert len(envelope.results) == 1

    def test_to_json(self):
        results = [_make_result("retrieval", 0.8, 0.6)]
        envelope = RunEnvelope.create(results)
        raw = json.loads(envelope.to_json())
        assert raw["results"][0]["category"] == "retrieval"

    def test_save_and_load(self, tmp_path: Path):
        results = [_make_result("retrieval", 0.8, 0.6, 0.5)]
        envelope = RunEnvelope.create(results)
        saved = envelope.save(tmp_path)
        assert saved.exists()

        loaded = load_baseline(saved)
        assert loaded is not None
        assert len(loaded) == 1
        assert loaded[0].category == "retrieval"
        assert loaded[0].metrics.p_at_5 == 0.8


class TestDeltas:
    def test_no_regression(self):
        current = [_make_result("r", 0.85, 0.65)]
        baseline = [_make_result("r", 0.80, 0.60)]
        deltas = compute_deltas(current, baseline)
        assert not has_regressions(deltas)
        assert all(d.delta >= 0 for d in deltas)

    def test_regression_detected(self):
        current = [_make_result("r", 0.70, 0.50)]
        baseline = [_make_result("r", 0.80, 0.60)]
        deltas = compute_deltas(current, baseline, regression_threshold=0.0)
        assert has_regressions(deltas)

    def test_threshold_tolerance(self):
        current = [_make_result("r", 0.78, 0.58)]
        baseline = [_make_result("r", 0.80, 0.60)]
        deltas = compute_deltas(current, baseline, regression_threshold=0.05)
        assert not has_regressions(deltas)

    def test_missing_baseline_category(self):
        current = [_make_result("new_cat", 0.9, 0.8)]
        baseline = [_make_result("old_cat", 0.8, 0.7)]
        deltas = compute_deltas(current, baseline)
        assert len(deltas) == 0

    def test_tau_delta(self):
        current = [_make_result("r", 0.8, 0.6, 0.7)]
        baseline = [_make_result("r", 0.8, 0.6, 0.5)]
        deltas = compute_deltas(current, baseline)
        tau_deltas = [d for d in deltas if d.metric == "tau"]
        assert len(tau_deltas) == 1
        assert tau_deltas[0].delta > 0


class TestPrGate:
    def test_pass(self):
        current = [_make_result("r", 0.85, 0.65)]
        baseline = [_make_result("r", 0.80, 0.60)]
        result = pr_gate(current, baseline)
        assert result.passed
        assert "PASSED" in result.summary

    def test_fail(self):
        current = [_make_result("r", 0.60, 0.40)]
        baseline = [_make_result("r", 0.80, 0.60)]
        result = pr_gate(current, baseline, regression_threshold=0.05)
        assert not result.passed
        assert "FAILED" in result.summary

    def test_no_baseline(self):
        result = load_baseline("/nonexistent/path")
        assert result is None
