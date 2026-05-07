"""Report card data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from synapt_eval.runner.orchestration import Delta
from synapt_eval.suggestion_engine.types import Suggestion
from synapt_eval.types import CategoryMetrics


@dataclass
class ReportCardHeader:
    """Run metadata displayed at the top of the report."""

    run_id: str
    timestamp: str
    fixture_count: int
    category_count: int
    severity_counts: dict[str, int] = field(default_factory=dict)
    commit: str | None = None
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class CategorySection:
    """Per-category metrics and suggestions."""

    category: str
    metrics: CategoryMetrics
    suggestions: list[Suggestion] = field(default_factory=list)
    fixture_count: int = 0


@dataclass
class ReportCardFooter:
    """Overall result and regression summary."""

    passed: bool
    total_suggestions: int
    error_count: int
    warning_count: int
    info_count: int
    regression_summary: str | None = None
    deltas: list[Delta] = field(default_factory=list)


@dataclass
class TrendingEntry:
    """Historical metric snapshot for trending display."""

    run_id: str
    category: str
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class ReportCard:
    """Complete report card ready for rendering."""

    header: ReportCardHeader
    sections: list[CategorySection]
    suggestions: list[Suggestion]
    footer: ReportCardFooter
    trending: list[TrendingEntry] = field(default_factory=list)
