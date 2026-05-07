"""Precision@K metric."""

from __future__ import annotations


def precision_at_k(retrieved: list[str], relevant: list[str], k: int = 5) -> float:
    """Compute precision at K.

    Returns the fraction of the top-K retrieved items that are relevant.
    """
    if k <= 0:
        return 0.0

    top_k = retrieved[:k]
    if not top_k:
        return 0.0

    relevant_set = set(relevant)
    hits = sum(1 for item in top_k if item in relevant_set)
    return hits / len(top_k)
