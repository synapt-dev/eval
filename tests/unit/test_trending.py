"""Tests for trending store, delta computation, and CLI viewer."""

import json
from pathlib import Path

from synapt_eval.cli import main
from synapt_eval.cli.trending import _format_markdown, _format_text
from synapt_eval.report_card import compose_report_card
from synapt_eval.trending.store import TrendingStore, compute_trending_deltas
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


def _card(
    run_id: str = "run1",
    category: str = "retrieval",
    p5: float = 0.8,
    r10: float = 0.7,
):
    return compose_report_card(
        [_result(category, p5, r10)],
        run_id=run_id,
    )


# -- TrendingStore tests --


class TestTrendingStore:
    def test_save_and_load(self, tmp_path: Path):
        store = TrendingStore(tmp_path / "history")
        card = _card(run_id="test-001")
        saved = store.save(card)
        assert saved.exists()
        assert "test-001" in saved.name

        history = store.load_history()
        assert len(history) == 1
        assert history[0]["run_id"] == "test-001"

    def test_multiple_saves_ordered(self, tmp_path: Path):
        store = TrendingStore(tmp_path / "history")
        store.save(_card(run_id="aaa"))
        store.save(_card(run_id="bbb"))
        store.save(_card(run_id="ccc"))

        history = store.load_history()
        assert len(history) == 3
        assert history[0]["run_id"] == "ccc"

    def test_load_with_limit(self, tmp_path: Path):
        store = TrendingStore(tmp_path / "history")
        for i in range(5):
            store.save(_card(run_id=f"run-{i:03d}"))

        history = store.load_history(limit=2)
        assert len(history) == 2

    def test_load_empty_dir(self, tmp_path: Path):
        store = TrendingStore(tmp_path / "nonexistent")
        history = store.load_history()
        assert history == []

    def test_list_runs(self, tmp_path: Path):
        store = TrendingStore(tmp_path / "history")
        store.save(_card(run_id="alpha"))
        store.save(_card(run_id="beta"))

        runs = store.list_runs()
        assert len(runs) == 2
        assert "alpha" in runs
        assert "beta" in runs

    def test_schema_version_preserved(self, tmp_path: Path):
        store = TrendingStore(tmp_path / "history")
        store.save(_card())
        history = store.load_history()
        assert history[0]["schema_version"] == "1.0"

    def test_corrupted_file_skipped(self, tmp_path: Path):
        store = TrendingStore(tmp_path / "history")
        store.save(_card(run_id="good"))

        bad_file = tmp_path / "history" / "run-bad.json"
        bad_file.write_text("not json", encoding="utf-8")

        history = store.load_history()
        assert len(history) == 1
        assert history[0]["run_id"] == "good"


# -- Delta computation tests --


class TestComputeTrendingDeltas:
    def test_improvement(self, tmp_path: Path):
        history = [
            _make_json(run_id="current", p5=0.85, r10=0.72),
            _make_json(run_id="previous", p5=0.80, r10=0.70),
        ]
        deltas = compute_trending_deltas(history)
        p5_delta = _find_delta(deltas, "p_at_5")
        assert p5_delta is not None
        assert p5_delta["direction"] == "up"
        assert p5_delta["delta"] > 0

    def test_regression(self, tmp_path: Path):
        history = [
            _make_json(run_id="current", p5=0.70, r10=0.55),
            _make_json(run_id="previous", p5=0.80, r10=0.70),
        ]
        deltas = compute_trending_deltas(history)
        p5_delta = _find_delta(deltas, "p_at_5")
        assert p5_delta is not None
        assert p5_delta["direction"] == "down"

    def test_flat(self):
        history = [
            _make_json(run_id="a", p5=0.80, r10=0.70),
            _make_json(run_id="b", p5=0.80, r10=0.70),
        ]
        deltas = compute_trending_deltas(history)
        assert all(d["direction"] == "flat" for d in deltas)

    def test_single_run(self):
        history = [_make_json(run_id="only")]
        assert compute_trending_deltas(history) == []

    def test_empty_history(self):
        assert compute_trending_deltas([]) == []


# -- CLI format tests --


class TestFormatText:
    def test_basic_output(self):
        history = [_make_json(run_id="run1", p5=0.85)]
        output = _format_text(history, use_arrows=True)
        assert "run1" in output
        assert "p_at_5=0.850" in output

    def test_arrows_on_latest(self):
        history = [
            _make_json(run_id="new", p5=0.85),
            _make_json(run_id="old", p5=0.80),
        ]
        output = _format_text(history, use_arrows=True)
        assert "^" in output

    def test_words_when_piped(self):
        history = [
            _make_json(run_id="new", p5=0.85),
            _make_json(run_id="old", p5=0.80),
        ]
        output = _format_text(history, use_arrows=False)
        assert "(up)" in output

    def test_pass_fail_status(self):
        history = [_make_json(run_id="r1", passed=True)]
        output = _format_text(history)
        assert "PASS" in output


class TestFormatMarkdown:
    def test_basic_structure(self):
        history = [_make_json(run_id="run1", p5=0.85, r10=0.72)]
        md = _format_markdown(history)
        assert "# Eval Trending" in md
        assert "| run1 |" in md
        assert "0.850" in md

    def test_multiple_categories(self):
        history = [
            {
                "run_id": "r1",
                "passed": True,
                "sections": [
                    {
                        "category": "retrieval",
                        "metrics": {"p_at_5": 0.8, "r_at_10": 0.7},
                    },
                    {
                        "category": "generation",
                        "metrics": {"p_at_5": 0.9, "r_at_10": 0.85},
                    },
                ],
            }
        ]
        md = _format_markdown(history)
        assert "## generation" in md
        assert "## retrieval" in md


# -- CLI integration tests --


class TestCLI:
    def test_no_args(self, capsys):
        code = main([])
        assert code == 0
        captured = capsys.readouterr()
        assert "synapt-eval" in captured.out

    def test_trending_no_history(self, tmp_path: Path, capsys):
        code = main(["trending", "--path", str(tmp_path / "empty")])
        assert code == 1
        captured = capsys.readouterr()
        assert "No eval history" in captured.err

    def test_trending_text(self, tmp_path: Path, capsys):
        store = TrendingStore(tmp_path / "hist")
        store.save(_card(run_id="cli-test", p5=0.85))

        code = main(
            [
                "trending",
                "--path",
                str(tmp_path / "hist"),
                "--format",
                "text",
            ]
        )
        assert code == 0
        captured = capsys.readouterr()
        assert "cli-test" in captured.out

    def test_trending_json(self, tmp_path: Path, capsys):
        store = TrendingStore(tmp_path / "hist")
        store.save(_card(run_id="json-test"))

        code = main(
            [
                "trending",
                "--path",
                str(tmp_path / "hist"),
                "--format",
                "json",
            ]
        )
        assert code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert data[0]["run_id"] == "json-test"

    def test_trending_markdown(self, tmp_path: Path, capsys):
        store = TrendingStore(tmp_path / "hist")
        store.save(_card(run_id="md-test", p5=0.75))

        code = main(
            [
                "trending",
                "--path",
                str(tmp_path / "hist"),
                "--format",
                "markdown",
            ]
        )
        assert code == 0
        captured = capsys.readouterr()
        assert "# Eval Trending" in captured.out
        assert "md-test" in captured.out

    def test_trending_limit(self, tmp_path: Path, capsys):
        store = TrendingStore(tmp_path / "hist")
        for i in range(5):
            store.save(_card(run_id=f"limit-{i:03d}"))

        code = main(
            [
                "trending",
                "--path",
                str(tmp_path / "hist"),
                "--limit",
                "2",
                "--format",
                "json",
            ]
        )
        assert code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert len(data) == 2


# -- Integration test --


class TestTrendingIntegration:
    def test_full_pipeline(self, tmp_path: Path):
        store = TrendingStore(tmp_path / "history")

        for run_id, p5 in [("run-1", 0.80), ("run-2", 0.78), ("run-3", 0.75)]:
            card = _card(run_id=run_id, p5=p5, r10=0.65)
            store.save(card)

        history = store.load_history()
        assert len(history) == 3
        assert history[0]["run_id"] == "run-3"

        deltas = compute_trending_deltas(history)
        p5_delta = _find_delta(deltas, "p_at_5")
        assert p5_delta is not None
        assert p5_delta["direction"] == "down"

        text = _format_text(history, use_arrows=True)
        assert "run-3" in text
        assert "run-1" in text


# -- Helpers --


def _make_json(
    run_id: str = "test",
    p5: float = 0.8,
    r10: float = 0.7,
    passed: bool = True,
) -> dict:
    return {
        "run_id": run_id,
        "passed": passed,
        "sections": [
            {
                "category": "retrieval",
                "metrics": {"p_at_5": p5, "r_at_10": r10},
            }
        ],
    }


def _find_delta(deltas: list[dict], metric: str) -> dict | None:
    for d in deltas:
        if d["metric"] == metric:
            return d
    return None
