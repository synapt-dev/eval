"""Retrieval adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RetrievalCandidate:
    """A single retrieval result with ID and score."""

    id: str
    score: float


class RetrievalAdapter(ABC):
    """Interface for customer retrieval systems.

    Customers implement this to connect their retrieval backend
    (Supabase, Pinecone, Weaviate, custom) to the eval runner.
    """

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        k: int = 10,
    ) -> list[RetrievalCandidate]:
        """Retrieve top-K candidates for a query."""

    async def embed(self, text: str) -> list[float]:
        """Optional: embed text for similarity comparison."""
        raise NotImplementedError
