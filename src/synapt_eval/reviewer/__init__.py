"""Reviewer SDK: verdict-producing interfaces and composition."""

from synapt_eval.reviewer.bridge import JudgingReviewer
from synapt_eval.reviewer.chain import ReviewerChain
from synapt_eval.reviewer.framework import FrameworkReviewer
from synapt_eval.reviewer.protocol import Predicate, Reviewer
from synapt_eval.reviewer.types import (
    SEVERITY_CRITICAL,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    CheckResult,
    Severity,
    Verdict,
)

__all__ = [
    "CheckResult",
    "FrameworkReviewer",
    "JudgingReviewer",
    "Predicate",
    "Reviewer",
    "ReviewerChain",
    "SEVERITY_CRITICAL",
    "SEVERITY_ERROR",
    "SEVERITY_INFO",
    "SEVERITY_WARNING",
    "Severity",
    "Verdict",
]
