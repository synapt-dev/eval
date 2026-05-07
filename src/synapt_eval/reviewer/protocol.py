"""Reviewer and Predicate abstract base classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from synapt_eval.reviewer.types import CheckResult, Verdict


class Reviewer(ABC):
    """Abstract verdict-producing interface.

    Implementations examine eval output and produce a Verdict
    with pass/fail, reasoning, severity, and constituent checks.
    """

    @abstractmethod
    async def review(
        self,
        output: str,
        expected: list[str],
        query: str,
        **kwargs: Any,
    ) -> Verdict:
        """Review an output against expected values."""


class Predicate(ABC):
    """A single check that a FrameworkReviewer applies."""

    @abstractmethod
    def check(
        self,
        output: str,
        expected: list[str],
        query: str,
    ) -> CheckResult:
        """Run this predicate and return a check result."""
