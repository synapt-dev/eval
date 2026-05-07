"""Append-only JSON history store for eval trending."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from synapt_eval.report_card.json_output import generate_json
from synapt_eval.report_card.types import ReportCard


class TrendingStore:
    """Append-only JSON file store for eval run history.

    Each run writes one JSON file using the ReportCard schema v1.0.
    Files are named run-{run_id}.json to match RunEnvelope convention.
    """

    def __init__(self, path: str | Path = ".synapt-eval/history") -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def save(self, report_card: ReportCard) -> Path:
        """Save a report card to the history store."""
        self._path.mkdir(parents=True, exist_ok=True)
        data = generate_json(report_card)
        run_id = data.get("run_id", "unknown")
        filename = f"run-{run_id}.json"
        file_path = self._path / filename
        file_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return file_path

    def load_history(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Load recent runs from the history store, newest first."""
        if not self._path.exists():
            return []

        files = sorted(self._path.glob("run-*.json"), reverse=True)
        if limit is not None:
            files = files[:limit]

        history: list[dict[str, Any]] = []
        for f in files:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                history.append(data)
            except (json.JSONDecodeError, OSError):
                continue

        return history

    def list_runs(self) -> list[str]:
        """List all run IDs in the store."""
        if not self._path.exists():
            return []
        files = sorted(self._path.glob("run-*.json"), reverse=True)
        return [f.stem.removeprefix("run-") for f in files]


def compute_trending_deltas(
    history: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compute metric deltas between consecutive runs.

    Returns a list of delta records with run_id, category, metric,
    previous value, current value, and delta direction.
    """
    if len(history) < 2:
        return []

    deltas: list[dict[str, Any]] = []
    current = history[0]
    previous = history[1]

    current_sections = {s["category"]: s for s in current.get("sections", [])}
    previous_sections = {s["category"]: s for s in previous.get("sections", [])}

    for category, cur_section in current_sections.items():
        prev_section = previous_sections.get(category)
        if prev_section is None:
            continue

        cur_metrics = cur_section.get("metrics", {})
        prev_metrics = prev_section.get("metrics", {})

        for metric in ("p_at_5", "r_at_10", "tau"):
            cur_val = cur_metrics.get(metric)
            prev_val = prev_metrics.get(metric)
            if cur_val is None or prev_val is None:
                continue

            diff = cur_val - prev_val
            if diff > 0.001:
                direction = "up"
            elif diff < -0.001:
                direction = "down"
            else:
                direction = "flat"

            deltas.append(
                {
                    "run_id": current.get("run_id", "unknown"),
                    "category": category,
                    "metric": metric,
                    "current": cur_val,
                    "previous": prev_val,
                    "delta": diff,
                    "direction": direction,
                }
            )

    return deltas
