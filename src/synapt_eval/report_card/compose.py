"""Compose a ReportCard from upstream eval phase outputs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from synapt_eval.report_card.types import (
    CategorySection,
    ReportCard,
    ReportCardFooter,
    ReportCardHeader,
    TrendingEntry,
)
from synapt_eval.runner.orchestration import compute_deltas
from synapt_eval.suggestion_engine.types import Suggestion
from synapt_eval.types import EvalResult


def compose_report_card(
    results: list[EvalResult],
    suggestions: list[Suggestion] | None = None,
    baseline: list[EvalResult] | None = None,
    history: list[EvalResult] | None = None,
    run_id: str | None = None,
    timestamp: str | None = None,
    commit: str | None = None,
    config: dict[str, Any] | None = None,
) -> ReportCard:
    """Build a ReportCard from eval results and upstream outputs."""
    suggestions = suggestions or []

    now = datetime.now(timezone.utc)
    run_id = run_id or now.strftime("%Y%m%dT%H%M%SZ")
    timestamp = timestamp or now.isoformat()

    severity_counts = _count_severities(suggestions)
    fixture_count = sum(r.metrics.n for r in results)

    header = ReportCardHeader(
        run_id=run_id,
        timestamp=timestamp,
        fixture_count=fixture_count,
        category_count=len(results),
        severity_counts=severity_counts,
        commit=commit,
        config=config or {},
    )

    suggestion_by_category: dict[str, list[Suggestion]] = {}
    for s in suggestions:
        cat = s.category or "_global"
        suggestion_by_category.setdefault(cat, []).append(s)

    sections = [
        CategorySection(
            category=r.category,
            metrics=r.metrics,
            suggestions=suggestion_by_category.get(r.category, []),
            fixture_count=r.metrics.n,
        )
        for r in results
    ]

    deltas = []
    regression_summary = None
    if baseline:
        deltas = compute_deltas(results, baseline)
        regressions = [d for d in deltas if d.regression]
        if regressions:
            regression_summary = f"{len(regressions)} regression(s) detected"

    has_errors = severity_counts.get("error", 0) > 0
    has_regressions = regression_summary is not None
    passed = not has_errors and not has_regressions

    footer = ReportCardFooter(
        passed=passed,
        total_suggestions=len(suggestions),
        error_count=severity_counts.get("error", 0),
        warning_count=severity_counts.get("warning", 0),
        info_count=severity_counts.get("info", 0),
        regression_summary=regression_summary,
        deltas=deltas,
    )

    trending = _build_trending(history) if history else []

    return ReportCard(
        header=header,
        sections=sections,
        suggestions=suggestions,
        footer=footer,
        trending=trending,
    )


def _count_severities(suggestions: list[Suggestion]) -> dict[str, int]:
    counts: dict[str, int] = {"error": 0, "warning": 0, "info": 0}
    for s in suggestions:
        level = s.severity.level
        if level in counts:
            counts[level] += 1
        elif s.severity.weight >= 0.75:
            counts["error"] += 1
        elif s.severity.weight >= 0.5:
            counts["warning"] += 1
        else:
            counts["info"] += 1
    return counts


def _build_trending(
    history: list[EvalResult],
) -> list[TrendingEntry]:
    entries: list[TrendingEntry] = []
    for r in history:
        metrics: dict[str, float] = {
            "p_at_5": r.metrics.p_at_5,
            "r_at_10": r.metrics.r_at_10,
        }
        if r.metrics.tau is not None:
            metrics["tau"] = r.metrics.tau
        entries.append(
            TrendingEntry(
                run_id="historical",
                category=r.category,
                metrics=metrics,
            )
        )
    return entries
