"""JSON report card renderer (forward-compat schema for Pro dashboard)."""

from __future__ import annotations

import json
from typing import Any

from synapt_eval.report_card.types import ReportCard

SCHEMA_VERSION = "1.0"


def generate_json(report_card: ReportCard) -> dict[str, Any]:
    """Render a ReportCard as a JSON-serializable dict.

    The schema is versioned from line 1. Pro tier dashboard consumes
    this structure directly; changes must be backward-compatible.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": report_card.header.run_id,
        "timestamp": report_card.header.timestamp,
        "commit": report_card.header.commit,
        "passed": report_card.footer.passed,
        "summary": {
            "fixture_count": report_card.header.fixture_count,
            "category_count": report_card.header.category_count,
            "error_count": report_card.footer.error_count,
            "warning_count": report_card.footer.warning_count,
            "info_count": report_card.footer.info_count,
            "total_suggestions": report_card.footer.total_suggestions,
        },
        "sections": [
            {
                "category": section.category,
                "metrics": {
                    "p_at_5": section.metrics.p_at_5,
                    "r_at_10": section.metrics.r_at_10,
                    "tau": section.metrics.tau,
                    "n": section.metrics.n,
                },
                "fixture_count": section.fixture_count,
                "suggestions": [_serialize_suggestion(s) for s in section.suggestions],
            }
            for section in report_card.sections
        ],
        "suggestions": [_serialize_suggestion(s) for s in report_card.suggestions],
        "regression": {
            "has_regression": report_card.footer.regression_summary is not None,
            "summary": report_card.footer.regression_summary,
            "deltas": [
                {
                    "category": d.category,
                    "metric": d.metric,
                    "baseline": d.baseline,
                    "current": d.current,
                    "delta": d.delta,
                    "regression": d.regression,
                }
                for d in report_card.footer.deltas
            ],
        },
        "trending": [
            {
                "run_id": e.run_id,
                "category": e.category,
                "metrics": e.metrics,
            }
            for e in report_card.trending
        ]
        if report_card.trending
        else None,
        "config": report_card.header.config,
    }


def generate_json_string(report_card: ReportCard) -> str:
    """Render a ReportCard as a formatted JSON string."""
    data = generate_json(report_card)
    return json.dumps(data, indent=2, default=str)


def _serialize_suggestion(s: Any) -> dict[str, Any]:
    return {
        "severity": s.severity.level,
        "severity_weight": s.severity.weight,
        "message": s.message,
        "rule_name": s.rule_name,
        "metric": s.metric,
        "category": s.category,
        "fix_hint": s.fix_hint,
    }
