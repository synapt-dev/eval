"""SuggestionEngine: registers rules and evaluates eval results."""

from __future__ import annotations

from typing import Any

from synapt_eval.reviewer.types import Verdict
from synapt_eval.suggestion_engine.protocol import SuggestionRule
from synapt_eval.suggestion_engine.types import Suggestion
from synapt_eval.types import EvalResult


class SuggestionEngine:
    """Registers suggestion rules and evaluates them against eval results.

    Results are ordered by severity weight (highest first).
    """

    def __init__(self) -> None:
        self._rules: list[SuggestionRule] = []

    def register(self, rule: SuggestionRule) -> None:
        """Register a suggestion rule."""
        self._rules.append(rule)

    @property
    def rules(self) -> list[SuggestionRule]:
        return list(self._rules)

    def evaluate(
        self,
        result: EvalResult,
        verdicts: list[Verdict] | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[Suggestion]:
        """Run all registered rules and return suggestions ordered by severity."""
        suggestions: list[Suggestion] = []
        for rule in self._rules:
            suggestions.extend(rule.evaluate(result, verdicts, context))
        suggestions.sort(key=lambda s: s.severity.weight, reverse=True)
        return suggestions

    def evaluate_all(
        self,
        results: list[EvalResult],
        verdicts: list[Verdict] | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[Suggestion]:
        """Run rules across multiple category results."""
        suggestions: list[Suggestion] = []
        for result in results:
            suggestions.extend(self.evaluate(result, verdicts, context))
        suggestions.sort(key=lambda s: s.severity.weight, reverse=True)
        return suggestions

    @classmethod
    def with_defaults(cls) -> SuggestionEngine:
        """Create an engine with all baseline rules registered."""
        from synapt_eval.suggestion_engine.rules import default_rules

        engine = cls()
        for rule in default_rules():
            engine.register(rule)
        return engine
