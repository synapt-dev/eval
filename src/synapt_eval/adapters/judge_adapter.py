"""Judge adapter interface for LLM-as-judge evaluation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class JudgeRequest:
    """Structured request to an LLM judge."""

    query: str
    expected: list[str]
    actual: str
    rubric: str | None = None
    context: dict[str, Any] | None = None


@dataclass
class JudgeResponse:
    """Parsed verdict from an LLM judge."""

    passed: bool
    score: float
    reasoning: str
    raw: dict[str, Any] = field(default_factory=dict)


class JudgeAdapter(ABC):
    """Interface for LLM-as-judge providers.

    Customers implement this to connect their preferred LLM provider
    (OpenAI, Anthropic, custom) to the eval reviewer pipeline.
    """

    @abstractmethod
    async def judge(self, request: JudgeRequest) -> JudgeResponse:
        """Judge an output against expected values using an LLM."""
