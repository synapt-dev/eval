"""Reviewer verdict types: severity, check results, and verdicts."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Severity:
    """Severity level for a check result or verdict."""

    level: str
    weight: float = 1.0


SEVERITY_INFO = Severity("info", 0.25)
SEVERITY_WARNING = Severity("warning", 0.5)
SEVERITY_ERROR = Severity("error", 0.75)
SEVERITY_CRITICAL = Severity("critical", 1.0)


@dataclass
class CheckResult:
    """Result of a single predicate check."""

    name: str
    passed: bool
    severity: Severity
    reasoning: str = ""


@dataclass
class Verdict:
    """Composed verdict from one or more checks."""

    passed: bool
    reasoning: str
    severity: Severity
    checks: list[CheckResult] = field(default_factory=list)
    score: float = 1.0
