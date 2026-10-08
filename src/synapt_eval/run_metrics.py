"""Portable measurements for an evaluation run, without implicit pricing."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass
class TokenCount:
    value: int | None = None
    status: Literal["measured", "unavailable"] = "unavailable"


@dataclass
class TokenUsage:
    """Prompt tokens include cache reads and writes; caches are subsets."""

    prompt_tokens: TokenCount = field(default_factory=TokenCount)
    cached_prompt_tokens: TokenCount = field(default_factory=TokenCount)
    cache_write_tokens: TokenCount = field(default_factory=TokenCount)
    completion_tokens: TokenCount = field(default_factory=TokenCount)
    total_tokens: TokenCount = field(default_factory=TokenCount)


@dataclass
class RunCost:
    """Provider-reported cost, an explicit estimate, or an unavailable value."""

    value_usd: float | None = None
    status: Literal["measured", "GUESS", "unavailable"] = "unavailable"
    source: str | None = None
    reason: str | None = None
    rates: dict[str, Any] | None = None


@dataclass
class RunMetrics:
    """Measurements for one declared scope; missing values are never zero."""

    runtime: str | None = None
    runtime_versions: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)
    turns: int | None = None
    tool_calls: int | None = None
    wall_seconds: float | None = None
    box_minutes: float | None = None
    model_cost: RunCost = field(default_factory=RunCost)
    box_cost: RunCost = field(default_factory=RunCost)
    scope: str | None = None
    start: str | None = None
    end: str | None = None
    counting_rule: str | None = None
    usage_basis: str | None = None
    wall_basis: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunMetrics:
        values = dict(data)
        values["usage"] = TokenUsage(**{
            key: TokenCount(**value) for key, value in values.get("usage", {}).items()
        })
        for key in ("model_cost", "box_cost"):
            values[key] = RunCost(**values.get(key, {}))
        return cls(**values)

    @classmethod
    def from_collector(cls, data: dict[str, Any]) -> RunMetrics:
        """Select the normalized measurement fields from a transcript collector."""
        names = cls.__dataclass_fields__
        return cls.from_dict({key: value for key, value in data.items() if key in names})
