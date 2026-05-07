"""synapt-eval: domain-agnostic eval framework for AI applications."""

__version__ = "0.1.0"

from synapt_eval.types import (
    CategoryMetrics,
    EdgeCaseFixture,
    EdgeCaseResult,
    EvalConfig,
    EvalResult,
    Fixture,
    GenerationResult,
    PerFixtureResult,
    RetrievalResult,
)

__all__ = [
    "CategoryMetrics",
    "EdgeCaseFixture",
    "EdgeCaseResult",
    "EvalConfig",
    "EvalResult",
    "Fixture",
    "GenerationResult",
    "PerFixtureResult",
    "RetrievalResult",
]
