"""Eval orchestration: run envelope, baseline comparison, 3-loop discipline."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from synapt_eval.types import EvalResult


@dataclass
class RunEnvelope:
    """Envelope wrapping a complete eval run for persistence and trending."""

    run_id: str
    timestamp: str
    results: list[EvalResult]
    config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    baseline_id: str | None = None

    @staticmethod
    def create(
        results: list[EvalResult],
        config: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        baseline_id: str | None = None,
    ) -> RunEnvelope:
        now = datetime.now(timezone.utc)
        run_id = now.strftime("%Y%m%dT%H%M%SZ")
        return RunEnvelope(
            run_id=run_id,
            timestamp=now.isoformat(),
            results=results,
            config=config or {},
            metadata=metadata or {},
            baseline_id=baseline_id,
        )

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, default=str)

    def save(self, output_dir: str | Path) -> Path:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        file_path = path / f"run-{self.run_id}.json"
        file_path.write_text(self.to_json(), encoding="utf-8")
        return file_path


@dataclass
class Delta:
    """Metric delta between current run and baseline."""

    category: str
    metric: str
    current: float
    baseline: float
    delta: float
    regression: bool


def compute_deltas(
    current: list[EvalResult],
    baseline: list[EvalResult],
    regression_threshold: float = 0.0,
) -> list[Delta]:
    """Compare current run against baseline and identify regressions.

    A regression is flagged when the current metric drops below
    baseline - regression_threshold.
    """
    baseline_map: dict[str, EvalResult] = {r.category: r for r in baseline}
    deltas: list[Delta] = []

    for result in current:
        base = baseline_map.get(result.category)
        if base is None:
            continue

        for metric_name in ("p_at_5", "r_at_10"):
            cur_val = getattr(result.metrics, metric_name)
            base_val = getattr(base.metrics, metric_name)
            diff = cur_val - base_val
            is_regression = diff < -regression_threshold

            deltas.append(
                Delta(
                    category=result.category,
                    metric=metric_name,
                    current=cur_val,
                    baseline=base_val,
                    delta=diff,
                    regression=is_regression,
                )
            )

        if result.metrics.tau is not None and base.metrics.tau is not None:
            diff = result.metrics.tau - base.metrics.tau
            deltas.append(
                Delta(
                    category=result.category,
                    metric="tau",
                    current=result.metrics.tau,
                    baseline=base.metrics.tau,
                    delta=diff,
                    regression=diff < -regression_threshold,
                )
            )

    return deltas


def has_regressions(deltas: list[Delta]) -> bool:
    """Check if any deltas indicate a regression."""
    return any(d.regression for d in deltas)


@dataclass
class GateResult:
    """Result of a PR-gate evaluation."""

    passed: bool
    deltas: list[Delta]
    summary: str


def pr_gate(
    current: list[EvalResult],
    baseline: list[EvalResult],
    regression_threshold: float = 0.05,
) -> GateResult:
    """L1 PR-gate: pass/fail based on regression threshold.

    Returns a GateResult with pass/fail status, deltas, and a
    human-readable summary suitable for GitHub Actions output.
    """
    deltas = compute_deltas(current, baseline, regression_threshold)
    regressions = [d for d in deltas if d.regression]
    passed = len(regressions) == 0

    if passed:
        summary = f"PR gate PASSED: {len(deltas)} metrics checked, no regressions."
    else:
        lines = [f"PR gate FAILED: {len(regressions)} regression(s) detected."]
        for r in regressions:
            lines.append(
                f"  {r.category}/{r.metric}: {r.baseline:.3f} -> {r.current:.3f} "
                f"(delta: {r.delta:+.3f}, threshold: {regression_threshold})"
            )
        summary = "\n".join(lines)

    return GateResult(passed=passed, deltas=deltas, summary=summary)


def load_baseline(path: str | Path) -> list[EvalResult] | None:
    """Load a baseline run from a JSON file."""
    file_path = Path(path)
    if not file_path.exists():
        return None

    raw = json.loads(file_path.read_text(encoding="utf-8"))
    results_raw = raw.get("results", [])

    from synapt_eval.types import CategoryMetrics, PerFixtureResult

    results: list[EvalResult] = []
    for r in results_raw:
        metrics_raw = r.get("metrics", {})
        metrics = CategoryMetrics(
            p_at_5=metrics_raw.get("p_at_5", 0.0),
            r_at_10=metrics_raw.get("r_at_10", 0.0),
            tau=metrics_raw.get("tau"),
            n=metrics_raw.get("n", 0),
        )
        per_fixture = [
            PerFixtureResult(
                fixture_id=pf["fixture_id"],
                category=pf["category"],
                passed=pf["passed"],
                score=pf.get("score", 0.0),
                details=pf.get("details", {}),
            )
            for pf in r.get("per_fixture", [])
        ]
        results.append(
            EvalResult(
                category=r["category"],
                metrics=metrics,
                per_fixture=per_fixture,
            )
        )

    return results
