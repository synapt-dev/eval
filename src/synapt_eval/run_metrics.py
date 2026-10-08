"""Portable measurements for an evaluation run, without implicit pricing."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass
class TokenCount:
    value: int | None = None
    status: Literal["measured", "unavailable"] = "unavailable"

    def __post_init__(self) -> None:
        if self.status not in ("measured", "unavailable"):
            raise ValueError("token status must be measured or unavailable")
        if (self.value is None) != (self.status == "unavailable"):
            raise ValueError("unavailable token counts must be null; measured counts need a value")
        _nonnegative("token count", self.value, integer=True)


@dataclass
class TokenUsage:
    """Prompt tokens include cache reads and writes; caches are subsets."""

    prompt_tokens: TokenCount = field(default_factory=TokenCount)
    cached_prompt_tokens: TokenCount = field(default_factory=TokenCount)
    cache_write_tokens: TokenCount = field(default_factory=TokenCount)
    completion_tokens: TokenCount = field(default_factory=TokenCount)
    total_tokens: TokenCount = field(default_factory=TokenCount)

    def __post_init__(self) -> None:
        prompt, read, write, output, total = (
            count.value
            for count in (
                self.prompt_tokens,
                self.cached_prompt_tokens,
                self.cache_write_tokens,
                self.completion_tokens,
                self.total_tokens,
            )
        )
        if prompt is not None:
            if any(value is not None and value > prompt for value in (read, write)):
                raise ValueError("cache tokens cannot exceed prompt tokens")
            if read is not None and write is not None and read + write > prompt:
                raise ValueError("cache subsets cannot exceed prompt tokens")
        if prompt is not None and output is not None and total is not None:
            if total != prompt + output:
                raise ValueError("total tokens must equal prompt plus completion tokens")


@dataclass
class RunCost:
    """Provider-reported cost, an explicit estimate, or an unavailable value."""

    value_usd: float | None = None
    status: Literal["measured", "GUESS", "unavailable"] = "unavailable"
    source: str | None = None
    reason: str | None = None
    rates: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.status not in ("measured", "GUESS", "unavailable"):
            raise ValueError("cost status must be measured, GUESS or unavailable")
        if (self.value_usd is None) != (self.status == "unavailable"):
            raise ValueError(
                "unavailable cost must be null; measured or guessed cost needs a value"
            )
        _nonnegative("cost", self.value_usd)
        if self.value_usd is not None and not (self.source or (self.rates or {}).get("source")):
            raise ValueError("a reported or guessed cost needs its source")


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

    def __post_init__(self) -> None:
        for name in ("turns", "tool_calls"):
            _nonnegative(name, getattr(self, name), integer=True)
        for name in ("wall_seconds", "box_minutes"):
            _nonnegative(name, getattr(self, name))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunMetrics:
        values = dict(data)
        values["usage"] = TokenUsage(
            **{key: TokenCount(**value) for key, value in values.get("usage", {}).items()}
        )
        for key in ("model_cost", "box_cost"):
            values[key] = RunCost(**values.get(key, {}))
        return cls(**values)

    @classmethod
    def from_collector(cls, data: dict[str, Any]) -> RunMetrics:
        """Select the normalized measurement fields from a transcript collector."""
        names = cls.__dataclass_fields__
        return cls.from_dict({key: value for key, value in data.items() if key in names})


def _nonnegative(name: str, value: int | float | None, *, integer: bool = False) -> None:
    if value is None:
        return
    kinds = (int,) if integer else (int, float)
    if (
        isinstance(value, bool)
        or not isinstance(value, kinds)
        or (isinstance(value, float) and not math.isfinite(value))
        or value < 0
    ):
        raise ValueError(
            f"{name} must be a finite nonnegative {'integer' if integer else 'number'}"
        )
