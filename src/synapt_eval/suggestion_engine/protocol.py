"""SuggestionRule protocol and functional rule decorator."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from synapt_eval.reviewer.types import Verdict
from synapt_eval.suggestion_engine.types import Suggestion
from synapt_eval.types import EvalResult


@runtime_checkable
class SuggestionRule(Protocol):
    """Protocol for suggestion rules.

    Any object with a matching evaluate() signature is a valid rule.
    Supports both class-based rules and functional rules via decorator.
    """

    def evaluate(
        self,
        result: EvalResult,
        verdicts: list[Verdict] | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[Suggestion]: ...


class _FunctionalRule:
    """Wraps a plain function as a SuggestionRule."""

    def __init__(
        self,
        fn: Any,
        name: str | None = None,
        applies_to: str | None = None,
    ) -> None:
        self._fn = fn
        self._name = name or fn.__name__
        self._applies_to = applies_to

    def evaluate(
        self,
        result: EvalResult,
        verdicts: list[Verdict] | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[Suggestion]:
        if self._applies_to and result.category != self._applies_to:
            return []
        return self._fn(result, verdicts, context)


def suggestion_rule(
    name: str | None = None,
    applies_to: str | None = None,
) -> Any:
    """Decorator to create a SuggestionRule from a function.

    Usage:
        @suggestion_rule(name="my_check", applies_to="retrieval")
        def check_something(result, verdicts=None, context=None):
            if result.metrics.p_at_5 < 0.5:
                return [Suggestion(...)]
            return []
    """

    def decorator(fn: Any) -> _FunctionalRule:
        return _FunctionalRule(fn, name=name, applies_to=applies_to)

    return decorator
