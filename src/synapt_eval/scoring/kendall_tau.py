"""Kendall's Tau rank correlation coefficient."""

from __future__ import annotations


def kendall_tau(ranking_a: list[str], ranking_b: list[str]) -> float | None:
    """Compute Kendall's Tau-b between two rankings.

    Both rankings must contain the same items. Returns None if fewer than
    2 items are shared between the rankings.
    """
    common = [x for x in ranking_a if x in ranking_b]
    n = len(common)
    if n < 2:
        return None

    rank_b = {item: i for i, item in enumerate(ranking_b)}
    ordered = [rank_b[item] for item in common]

    concordant = 0
    discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            if ordered[i] < ordered[j]:
                concordant += 1
            elif ordered[i] > ordered[j]:
                discordant += 1

    pairs = n * (n - 1) / 2
    if pairs == 0:
        return None

    return (concordant - discordant) / pairs
