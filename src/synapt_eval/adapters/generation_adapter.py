"""Generation adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class GenerationOutput:
    """Output from a generation call."""

    text: str
    latency_ms: float
    metadata: dict[str, Any] | None = None


class GenerationAdapter(ABC):
    """Interface for customer generation systems.

    Customers implement this to connect their generation pipeline
    (Anthropic, OpenAI, custom) to the eval runner.
    """

    @abstractmethod
    async def generate(
        self,
        query: str,
        context: list[Any] | None = None,
    ) -> GenerationOutput:
        """Generate a response for the given query and context."""
