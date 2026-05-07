"""Core types for the eval framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class EvalConfig:
    """Configuration for an eval run."""

    fixtures_path: str
    output_path: str
    categories: list[str]
    embedding_model: str | None = None
    generation_model: str | None = None
    api_endpoints: dict[str, str] = field(default_factory=dict)


@dataclass
class Fixture(Generic[T]):
    """A single eval fixture with optional domain-specific content."""

    id: str
    category: str
    query: str
    expected: list[str]
    user_history: list[T] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CategoryMetrics:
    """Aggregate metrics for a single eval category."""

    p_at_5: float = 0.0
    r_at_10: float = 0.0
    tau: float | None = None
    n: int = 0


@dataclass
class PerFixtureResult:
    """Result for a single fixture evaluation."""

    fixture_id: str
    category: str
    passed: bool
    score: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """Result of a retrieval evaluation for one fixture."""

    fixture_id: str
    retrieved_ids: list[str]
    scores: list[float]
    p_at_5: float = 0.0
    r_at_10: float = 0.0
    tau: float | None = None


@dataclass
class GenerationResult:
    """Result of a generation evaluation for one fixture."""

    fixture_id: str
    query: str
    output: str
    latency_ms: float = 0.0
    status: str = "ok"


@dataclass
class EdgeCaseFixture:
    """An edge case test fixture."""

    id: str
    category: str
    input_text: str
    expected_behavior: str  # "block" | "allow" | "flag"
    notes: str = ""


@dataclass
class EdgeCaseResult:
    """Result of an edge case evaluation."""

    id: str
    category: str
    expected: str
    actual: str
    passed: bool
    notes: str = ""


@dataclass
class EvalResult:
    """Complete result for one eval category."""

    category: str
    metrics: CategoryMetrics
    per_fixture: list[PerFixtureResult] = field(default_factory=list)
