"""Suggestion engine: rule-based actionable recommendations from eval results."""

from synapt_eval.suggestion_engine.engine import SuggestionEngine
from synapt_eval.suggestion_engine.protocol import SuggestionRule, suggestion_rule
from synapt_eval.suggestion_engine.types import Suggestion

__all__ = [
    "Suggestion",
    "SuggestionEngine",
    "SuggestionRule",
    "suggestion_rule",
]
