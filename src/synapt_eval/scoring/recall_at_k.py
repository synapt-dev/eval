"""Recall@K metric."""

from __future__ import annotations


def recall_at_k(retrieved: list[str], relevant: list[str], k: int = 10) -> float:
    """Compute recall at K.

    Returns the fraction of relevant items found in the top-K retrieved items.
    """
    if not relevant or k <= 0:
        return 0.0

    top_k = retrieved[:k]
    relevant_set = set(relevant)
    hits = sum(1 for item in top_k if item in relevant_set)
    return hits / len(relevant_set)
