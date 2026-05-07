"""Markdown report card renderer."""

from __future__ import annotations

from synapt_eval.report_card.types import (
    CategorySection,
    ReportCard,
    ReportCardFooter,
    ReportCardHeader,
    TrendingEntry,
)
from synapt_eval.suggestion_engine.types import Suggestion


def generate_markdown(report_card: ReportCard) -> str:
    """Render a ReportCard as a markdown string."""
    parts: list[str] = []

    parts.append(_render_header(report_card.header))

    for section in report_card.sections:
        parts.append(_render_section(section))

    if report_card.trending:
        parts.append(_render_trending(report_card.trending))

    if report_card.suggestions:
        parts.append(_render_suggestions(report_card.suggestions))

    parts.append(_render_footer(report_card.footer))

    return "\n".join(parts)


def _render_header(header: ReportCardHeader) -> str:
    lines = ["# Eval Report Card", ""]

    lines.append(f"**Run ID**: {header.run_id}  ")
    lines.append(f"**Timestamp**: {header.timestamp}  ")
    if header.commit:
        lines.append(f"**Commit**: {header.commit}  ")
    lines.append(
        f"**Fixtures**: {header.fixture_count} across {header.category_count} categories  "
    )

    severity_parts = []
    for level in ("error", "warning", "info"):
        count = header.severity_counts.get(level, 0)
        if count > 0:
            severity_parts.append(f"{count} {level.upper()}")
    if severity_parts:
        lines.append(f"**Severity**: {' / '.join(severity_parts)}")

    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _render_section(section: CategorySection) -> str:
    lines = [f"## {section.category}", ""]

    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| P@5 | {section.metrics.p_at_5:.3f} |")
    lines.append(f"| R@10 | {section.metrics.r_at_10:.3f} |")
    if section.metrics.tau is not None:
        lines.append(f"| Tau | {section.metrics.tau:.3f} |")
    lines.append(f"| N | {section.metrics.n} |")
    lines.append("")

    if section.suggestions:
        lines.append("### Suggestions")
        lines.append("")
        for s in section.suggestions:
            level = s.severity.level.upper()
            lines.append(f"- [{level}] **{s.rule_name}**: {s.message}")
            if s.fix_hint:
                lines.append(f"  - *Fix*: {s.fix_hint}")
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _render_trending(entries: list[TrendingEntry]) -> str:
    if not entries:
        return ""

    categories = sorted({e.category for e in entries})
    lines = ["## Trending", ""]

    for category in categories:
        cat_entries = [e for e in entries if e.category == category]
        if not cat_entries:
            continue

        lines.append(f"### {category}")
        lines.append("")

        metric_names = sorted({k for e in cat_entries for k in e.metrics})
        header_cols = ["Run"] + [m.upper() for m in metric_names]
        lines.append("| " + " | ".join(header_cols) + " |")
        lines.append("| " + " | ".join("---" for _ in header_cols) + " |")

        for entry in cat_entries:
            row = [entry.run_id]
            for m in metric_names:
                val = entry.metrics.get(m)
                row.append(f"{val:.3f}" if val is not None else "-")
            lines.append("| " + " | ".join(row) + " |")

        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _render_suggestions(suggestions: list[Suggestion]) -> str:
    lines = ["## Suggestions Summary", ""]
    lines.append("| # | Severity | Rule | Category | Message |")
    lines.append("|---|----------|------|----------|---------|")

    for i, s in enumerate(suggestions, 1):
        level = s.severity.level.upper()
        category = s.category or "-"
        lines.append(f"| {i} | {level} | {s.rule_name} | {category} | {s.message} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _render_footer(footer: ReportCardFooter) -> str:
    lines = ["## Result", ""]

    status = "PASSED" if footer.passed else "FAILED"
    parts = []
    if footer.regression_summary:
        parts.append(footer.regression_summary)
    if footer.total_suggestions > 0:
        parts.append(f"{footer.total_suggestions} suggestion(s) for improvement")
    else:
        parts.append("No suggestions")

    detail = ". ".join(parts) + "." if parts else ""
    lines.append(f"**{status}** -- {detail}")

    if footer.deltas:
        lines.append("")
        lines.append("### Regression Deltas")
        lines.append("")
        lines.append("| Category | Metric | Baseline | Current | Delta |")
        lines.append("|----------|--------|----------|---------|-------|")
        for d in footer.deltas:
            flag = " [REGRESSION]" if d.regression else ""
            lines.append(
                f"| {d.category} | {d.metric} | "
                f"{d.baseline:.3f} | {d.current:.3f} | "
                f"{d.delta:+.3f}{flag} |"
            )
        lines.append("")

    lines.append("")
    return "\n".join(lines)
