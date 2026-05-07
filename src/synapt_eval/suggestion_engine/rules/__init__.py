"""Baseline suggestion rules for common AI eval failure modes."""

from synapt_eval.suggestion_engine.rules.cross_cutting import (
    CategoryImbalanceRule,
    RegressionRule,
)
from synapt_eval.suggestion_engine.rules.generation import (
    HallucinationSignalRule,
    LowSuccessRateRule,
    VerdictFailureRule,
)
from synapt_eval.suggestion_engine.rules.retrieval import (
    HighNoResultsRule,
    LowPrecisionRule,
    LowRecallRule,
)
from synapt_eval.suggestion_engine.rules.trending import (
    MonotonicDegradationRule,
    StableLowRule,
)


def default_rules() -> list:
    """Return all baseline rules with default thresholds."""
    return [
        LowPrecisionRule(),
        LowRecallRule(),
        HighNoResultsRule(),
        LowSuccessRateRule(),
        HallucinationSignalRule(),
        VerdictFailureRule(),
        RegressionRule(),
        CategoryImbalanceRule(),
        MonotonicDegradationRule(),
        StableLowRule(),
    ]


__all__ = [
    "CategoryImbalanceRule",
    "HallucinationSignalRule",
    "HighNoResultsRule",
    "LowPrecisionRule",
    "LowRecallRule",
    "LowSuccessRateRule",
    "MonotonicDegradationRule",
    "RegressionRule",
    "StableLowRule",
    "VerdictFailureRule",
    "default_rules",
]
