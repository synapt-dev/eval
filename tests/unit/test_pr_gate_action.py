"""Tests for PR-gate GitHub Actions adapter."""

import json
import os
from pathlib import Path
from unittest.mock import patch

from synapt_eval.actions.pr_gate import (
    COMMENT_MARKER,
    ActionInputs,
    build_comment_body,
    determine_passed,
    load_results,
    parse_inputs,
    run_action,
    set_output,
)
from synapt_eval.runner.orchestration import GateResult


def _results_json(
    p5: float = 0.8,
    r10: float = 0.7,
    category: str = "retrieval",
) -> dict:
    return {
        "results": [
            {
                "category": category,
                "metrics": {"p_at_5": p5, "r_at_10": r10, "n": 10},
                "per_fixture": [],
            }
        ]
    }


def _write_results(path: Path, data: dict | list) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# -- Input parsing tests --


class TestParseInputs:
    def test_required_results_path(self):
        env = {"INPUT_RESULTS_PATH": "results.json"}
        with patch.dict(os.environ, env, clear=True):
            inputs = parse_inputs()
            assert inputs.results_path == "results.json"

    def test_hyphenated_env_var(self):
        env = {"INPUT_RESULTS-PATH": "results.json"}
        with patch.dict(os.environ, env, clear=True):
            inputs = parse_inputs()
            assert inputs.results_path == "results.json"

    def test_missing_results_path_exits(self):
        with patch.dict(os.environ, {}, clear=True):
            try:
                parse_inputs()
                assert False, "Should have exited"
            except SystemExit as e:
                assert e.code == 1

    def test_defaults(self):
        env = {"INPUT_RESULTS_PATH": "r.json"}
        with patch.dict(os.environ, env, clear=True):
            inputs = parse_inputs()
            assert inputs.threshold == 0.05
            assert inputs.fail_on == "error"
            assert inputs.comment is True
            assert inputs.baseline_path is None
            assert inputs.trending_path is None

    def test_custom_threshold(self):
        env = {"INPUT_RESULTS_PATH": "r.json", "INPUT_THRESHOLD": "0.10"}
        with patch.dict(os.environ, env, clear=True):
            inputs = parse_inputs()
            assert inputs.threshold == 0.10

    def test_invalid_threshold_exits(self):
        env = {"INPUT_RESULTS_PATH": "r.json", "INPUT_THRESHOLD": "abc"}
        with patch.dict(os.environ, env, clear=True):
            try:
                parse_inputs()
                assert False, "Should have exited"
            except SystemExit:
                pass

    def test_fail_on_warning(self):
        env = {"INPUT_RESULTS_PATH": "r.json", "INPUT_FAIL_ON": "warning"}
        with patch.dict(os.environ, env, clear=True):
            inputs = parse_inputs()
            assert inputs.fail_on == "warning"

    def test_fail_on_none(self):
        env = {"INPUT_RESULTS_PATH": "r.json", "INPUT_FAIL_ON": "none"}
        with patch.dict(os.environ, env, clear=True):
            inputs = parse_inputs()
            assert inputs.fail_on == "none"

    def test_invalid_fail_on_exits(self):
        env = {"INPUT_RESULTS_PATH": "r.json", "INPUT_FAIL_ON": "critical"}
        with patch.dict(os.environ, env, clear=True):
            try:
                parse_inputs()
                assert False, "Should have exited"
            except SystemExit:
                pass

    def test_comment_false(self):
        env = {"INPUT_RESULTS_PATH": "r.json", "INPUT_COMMENT": "false"}
        with patch.dict(os.environ, env, clear=True):
            inputs = parse_inputs()
            assert inputs.comment is False

    def test_baseline_path(self):
        env = {
            "INPUT_RESULTS_PATH": "r.json",
            "INPUT_BASELINE_PATH": "baseline.json",
        }
        with patch.dict(os.environ, env, clear=True):
            inputs = parse_inputs()
            assert inputs.baseline_path == "baseline.json"

    def test_trending_path(self):
        env = {
            "INPUT_RESULTS_PATH": "r.json",
            "INPUT_TRENDING_PATH": ".eval/history",
        }
        with patch.dict(os.environ, env, clear=True):
            inputs = parse_inputs()
            assert inputs.trending_path == ".eval/history"


# -- Results loading tests --


class TestLoadResults:
    def test_load_dict_format(self, tmp_path: Path):
        path = _write_results(tmp_path / "r.json", _results_json())
        results = load_results(str(path))
        assert len(results) == 1
        assert results[0].category == "retrieval"
        assert results[0].metrics.p_at_5 == 0.8

    def test_load_list_format(self, tmp_path: Path):
        data = _results_json()["results"]
        path = _write_results(tmp_path / "r.json", data)
        results = load_results(str(path))
        assert len(results) == 1
        assert results[0].metrics.r_at_10 == 0.7

    def test_missing_file_exits(self, tmp_path: Path):
        try:
            load_results(str(tmp_path / "nonexistent.json"))
            assert False, "Should have exited"
        except SystemExit:
            pass

    def test_tau_preserved(self, tmp_path: Path):
        data = _results_json()
        data["results"][0]["metrics"]["tau"] = 0.65
        path = _write_results(tmp_path / "r.json", data)
        results = load_results(str(path))
        assert results[0].metrics.tau == 0.65

    def test_per_fixture_loaded(self, tmp_path: Path):
        data = _results_json()
        data["results"][0]["per_fixture"] = [
            {
                "fixture_id": "f1",
                "category": "retrieval",
                "passed": True,
                "score": 0.9,
            }
        ]
        path = _write_results(tmp_path / "r.json", data)
        results = load_results(str(path))
        assert len(results[0].per_fixture) == 1
        assert results[0].per_fixture[0].fixture_id == "f1"

    def test_multiple_categories(self, tmp_path: Path):
        data = {
            "results": [
                {
                    "category": "retrieval",
                    "metrics": {"p_at_5": 0.8, "r_at_10": 0.7, "n": 10},
                    "per_fixture": [],
                },
                {
                    "category": "generation",
                    "metrics": {"p_at_5": 0.9, "r_at_10": 0.85, "n": 5},
                    "per_fixture": [],
                },
            ]
        }
        path = _write_results(tmp_path / "r.json", data)
        results = load_results(str(path))
        assert len(results) == 2
        assert results[1].category == "generation"


# -- Gate decision tests --


class TestDeterminePassed:
    def _gate(self, passed: bool = True) -> GateResult:
        return GateResult(passed=passed, deltas=[], summary="test")

    def _report(self, errors: int = 0, warnings: int = 0) -> dict:
        return {
            "summary": {
                "error_count": errors,
                "warning_count": warnings,
            }
        }

    def test_regression_always_fails(self):
        assert not determine_passed(self._gate(passed=False), self._report(), "none")

    def test_no_issues_passes(self):
        assert determine_passed(self._gate(), self._report(), "error")

    def test_errors_fail_on_error(self):
        assert not determine_passed(self._gate(), self._report(errors=1), "error")

    def test_warnings_pass_on_error(self):
        assert determine_passed(self._gate(), self._report(warnings=3), "error")

    def test_warnings_fail_on_warning(self):
        assert not determine_passed(self._gate(), self._report(warnings=1), "warning")

    def test_errors_fail_on_warning(self):
        assert not determine_passed(self._gate(), self._report(errors=1), "warning")

    def test_fail_on_none_ignores_all(self):
        assert determine_passed(self._gate(), self._report(errors=5, warnings=10), "none")

    def test_fail_on_none_still_catches_regression(self):
        assert not determine_passed(self._gate(passed=False), self._report(), "none")


# -- Comment body tests --


class TestBuildCommentBody:
    def test_marker_present(self):
        body = build_comment_body("# Report")
        assert COMMENT_MARKER in body
        assert body.startswith(COMMENT_MARKER)

    def test_markdown_preserved(self):
        md = "# Eval Report Card\n\n**Run ID**: test-001"
        body = build_comment_body(md)
        assert md in body


# -- Output writing tests --


class TestSetOutput:
    def test_simple_value(self, tmp_path: Path):
        output_file = tmp_path / "output.txt"
        env = {"GITHUB_OUTPUT": str(output_file)}
        with patch.dict(os.environ, env):
            set_output("passed", "true")

        content = output_file.read_text(encoding="utf-8")
        assert "passed=true" in content

    def test_multiline_value(self, tmp_path: Path):
        output_file = tmp_path / "output.txt"
        env = {"GITHUB_OUTPUT": str(output_file)}
        with patch.dict(os.environ, env):
            set_output("report-markdown", "line1\nline2\nline3")

        content = output_file.read_text(encoding="utf-8")
        assert "report-markdown<<" in content
        assert "line1\nline2\nline3" in content

    def test_no_output_file(self):
        env: dict[str, str] = {}
        with patch.dict(os.environ, env, clear=True):
            set_output("key", "val")


# -- Integration tests --


class TestRunAction:
    def test_pass_no_baseline(self, tmp_path: Path):
        results_path = _write_results(tmp_path / "results.json", _results_json(p5=0.85, r10=0.75))
        output_file = tmp_path / "output.txt"

        inputs = ActionInputs(
            results_path=str(results_path),
            baseline_path=None,
            threshold=0.05,
            fail_on="error",
            comment=False,
            trending_path=None,
        )

        env = {
            "GITHUB_OUTPUT": str(output_file),
            "RUNNER_TEMP": str(tmp_path),
        }
        with patch.dict(os.environ, env, clear=False):
            code = run_action(inputs)

        assert code == 0
        content = output_file.read_text(encoding="utf-8")
        assert "passed=true" in content

    def test_fail_on_regression(self, tmp_path: Path):
        results_path = _write_results(tmp_path / "current.json", _results_json(p5=0.60, r10=0.50))
        baseline_path = _write_results(tmp_path / "baseline.json", _results_json(p5=0.85, r10=0.75))
        output_file = tmp_path / "output.txt"

        inputs = ActionInputs(
            results_path=str(results_path),
            baseline_path=str(baseline_path),
            threshold=0.05,
            fail_on="error",
            comment=False,
            trending_path=None,
        )

        env = {
            "GITHUB_OUTPUT": str(output_file),
            "RUNNER_TEMP": str(tmp_path),
        }
        with patch.dict(os.environ, env, clear=False):
            code = run_action(inputs)

        assert code == 1
        content = output_file.read_text(encoding="utf-8")
        assert "passed=false" in content

    def test_report_json_written(self, tmp_path: Path):
        results_path = _write_results(tmp_path / "results.json", _results_json())

        inputs = ActionInputs(
            results_path=str(results_path),
            baseline_path=None,
            threshold=0.05,
            fail_on="error",
            comment=False,
            trending_path=None,
        )

        env = {
            "GITHUB_OUTPUT": str(tmp_path / "out.txt"),
            "RUNNER_TEMP": str(tmp_path),
        }
        with patch.dict(os.environ, env, clear=False):
            run_action(inputs)

        report_path = tmp_path / "synapt-eval-report.json"
        assert report_path.exists()
        data = json.loads(report_path.read_text(encoding="utf-8"))
        assert data["schema_version"] == "1.0"
        assert data["passed"] is True

    def test_trending_saved(self, tmp_path: Path):
        results_path = _write_results(tmp_path / "results.json", _results_json())
        trending_dir = tmp_path / "history"

        inputs = ActionInputs(
            results_path=str(results_path),
            baseline_path=None,
            threshold=0.05,
            fail_on="error",
            comment=False,
            trending_path=str(trending_dir),
        )

        env = {
            "GITHUB_OUTPUT": str(tmp_path / "out.txt"),
            "RUNNER_TEMP": str(tmp_path),
        }
        with patch.dict(os.environ, env, clear=False):
            run_action(inputs)

        assert trending_dir.exists()
        files = list(trending_dir.glob("*.json"))
        assert len(files) == 1

    def test_markdown_in_output(self, tmp_path: Path):
        results_path = _write_results(tmp_path / "results.json", _results_json())
        output_file = tmp_path / "output.txt"

        inputs = ActionInputs(
            results_path=str(results_path),
            baseline_path=None,
            threshold=0.05,
            fail_on="error",
            comment=False,
            trending_path=None,
        )

        env = {
            "GITHUB_OUTPUT": str(output_file),
            "RUNNER_TEMP": str(tmp_path),
        }
        with patch.dict(os.environ, env, clear=False):
            run_action(inputs)

        content = output_file.read_text(encoding="utf-8")
        assert "report-markdown<<" in content
        assert "Eval Report Card" in content

    def test_no_baseline_no_regression(self, tmp_path: Path):
        results_path = _write_results(tmp_path / "results.json", _results_json(p5=0.3, r10=0.2))

        inputs = ActionInputs(
            results_path=str(results_path),
            baseline_path=None,
            threshold=0.05,
            fail_on="error",
            comment=False,
            trending_path=None,
        )

        env = {
            "GITHUB_OUTPUT": str(tmp_path / "out.txt"),
            "RUNNER_TEMP": str(tmp_path),
        }
        with patch.dict(os.environ, env, clear=False):
            code = run_action(inputs)

        assert code == 0

    def test_commit_sha_in_report(self, tmp_path: Path):
        results_path = _write_results(tmp_path / "results.json", _results_json())

        inputs = ActionInputs(
            results_path=str(results_path),
            baseline_path=None,
            threshold=0.05,
            fail_on="error",
            comment=False,
            trending_path=None,
        )

        env = {
            "GITHUB_OUTPUT": str(tmp_path / "out.txt"),
            "RUNNER_TEMP": str(tmp_path),
            "GITHUB_SHA": "abc123def456",
        }
        with patch.dict(os.environ, env, clear=False):
            run_action(inputs)

        report_path = tmp_path / "synapt-eval-report.json"
        data = json.loads(report_path.read_text(encoding="utf-8"))
        assert data["commit"] == "abc123def456"
