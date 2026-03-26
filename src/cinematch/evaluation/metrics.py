"""Recommendation quality metrics: Precision@K, Recall@K, NDCG@K, MAP@K."""

from __future__ import annotations

import math


def precision_at_k(recommended: list[int], relevant: set[int], k: int) -> float:
    """Fraction of top-K recommendations that are relevant."""
    if k <= 0 or not recommended:
        return 0.0
    top_k = recommended[:k]
    hits = sum(1 for r in top_k if r in relevant)
    return hits / k


def recall_at_k(recommended: list[int], relevant: set[int], k: int) -> float:
    """Fraction of relevant items that appear in top-K recommendations."""
    if not relevant or k <= 0 or not recommended:
        return 0.0
    top_k = recommended[:k]
    hits = sum(1 for r in top_k if r in relevant)
    return hits / len(relevant)


def ndcg_at_k(recommended: list[int], relevant: set[int], k: int) -> float:
    """Normalized Discounted Cumulative Gain at K."""
    if k <= 0 or not recommended or not relevant:
        return 0.0

    top_k = recommended[:k]

    # DCG
    dcg = 0.0
    for i, item in enumerate(top_k):
        if item in relevant:
            dcg += 1.0 / math.log2(i + 2)  # i+2 because positions are 1-indexed

    # Ideal DCG (all relevant items at the top)
    n_relevant = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(n_relevant))

    if idcg == 0.0:
        return 0.0
    return dcg / idcg


def map_at_k(recommended: list[int], relevant: set[int], k: int) -> float:
    """Average Precision at K."""
    if not relevant or k <= 0 or not recommended:
        return 0.0

    top_k = recommended[:k]
    hits = 0
    sum_precision = 0.0

    for i, item in enumerate(top_k):
        if item in relevant:
            hits += 1
            sum_precision += hits / (i + 1)

    return sum_precision / min(k, len(relevant))
