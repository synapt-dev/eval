"""Suggestion types for the suggestion engine."""

from __future__ import annotations

from dataclasses import dataclass

from synapt_eval.reviewer.types import Severity


@dataclass
class Suggestion:
    """An actionable recommendation from an eval rule."""

    severity: Severity
    message: str
    rule_name: str
    metric: str | None = None
    category: str | None = None
    fix_hint: str | None = None
