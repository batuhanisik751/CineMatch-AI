"""Tests for evaluation metrics against known expected values."""

from __future__ import annotations

import math

import pytest

from cinematch.evaluation.metrics import map_at_k, ndcg_at_k, precision_at_k, recall_at_k

# --- Precision@K ---


def test_precision_at_k_all_relevant():
    recommended = [1, 2, 3, 4, 5]
    relevant = {1, 2, 3, 4, 5}
    assert precision_at_k(recommended, relevant, 5) == pytest.approx(1.0)


def test_precision_at_k_none_relevant():
    recommended = [10, 20, 30]
    relevant = {1, 2, 3}
    assert precision_at_k(recommended, relevant, 3) == pytest.approx(0.0)


def test_precision_at_k_partial():
    recommended = [1, 10, 2, 20, 3]
    relevant = {1, 2, 3}
    # 3 hits in top 5
    assert precision_at_k(recommended, relevant, 5) == pytest.approx(3 / 5)


def test_precision_at_k_smaller_k():
    recommended = [1, 10, 2, 20, 3]
    relevant = {1, 2, 3}
    # 1 hit in top 2
    assert precision_at_k(recommended, relevant, 2) == pytest.approx(1 / 2)


def test_precision_at_k_empty_recommended():
    assert precision_at_k([], {1, 2}, 5) == 0.0


# --- Recall@K ---


def test_recall_at_k_all_found():
    recommended = [1, 2, 3, 10, 20]
    relevant = {1, 2, 3}
    assert recall_at_k(recommended, relevant, 5) == pytest.approx(1.0)


def test_recall_at_k_partial():
    recommended = [1, 10, 20]
    relevant = {1, 2, 3, 4}
    # 1 of 4 found
    assert recall_at_k(recommended, relevant, 3) == pytest.approx(1 / 4)


def test_recall_at_k_empty_relevant():
    assert recall_at_k([1, 2, 3], set(), 3) == 0.0


def test_recall_at_k_empty_recommended():
    assert recall_at_k([], {1, 2}, 5) == 0.0


# --- NDCG@K ---


def test_ndcg_at_k_perfect_order():
    """All relevant items at the top → NDCG = 1.0."""
    recommended = [1, 2, 3, 10, 20]
    relevant = {1, 2, 3}
    assert ndcg_at_k(recommended, relevant, 5) == pytest.approx(1.0)


def test_ndcg_at_k_reversed():
    """Relevant items at the bottom → NDCG < 1.0."""
    recommended = [10, 20, 1, 2, 3]
    relevant = {1, 2, 3}
    # DCG = 1/log2(4) + 1/log2(5) + 1/log2(6)
    # IDCG = 1/log2(2) + 1/log2(3) + 1/log2(4)
    dcg = 1 / math.log2(4) + 1 / math.log2(5) + 1 / math.log2(6)
    idcg = 1 / math.log2(2) + 1 / math.log2(3) + 1 / math.log2(4)
    assert ndcg_at_k(recommended, relevant, 5) == pytest.approx(dcg / idcg)


def test_ndcg_at_k_no_relevant():
    assert ndcg_at_k([1, 2, 3], set(), 3) == 0.0


def test_ndcg_at_k_single_hit():
    recommended = [10, 1, 20]
    relevant = {1}
    # DCG = 1/log2(3), IDCG = 1/log2(2)
    assert ndcg_at_k(recommended, relevant, 3) == pytest.approx(
        (1 / math.log2(3)) / (1 / math.log2(2))
    )


# --- MAP@K ---


def test_map_at_k_perfect():
    recommended = [1, 2, 3]
    relevant = {1, 2, 3}
    # AP = (1/1 + 2/2 + 3/3) / 3 = 1.0
    assert map_at_k(recommended, relevant, 3) == pytest.approx(1.0)


def test_map_at_k_standard():
    recommended = [1, 10, 2, 20, 3]
    relevant = {1, 2, 3}
    # Hits at positions 1, 3, 5
    # AP = (1/1 + 2/3 + 3/5) / 3
    expected = (1 / 1 + 2 / 3 + 3 / 5) / 3
    assert map_at_k(recommended, relevant, 5) == pytest.approx(expected)


def test_map_at_k_empty_relevant():
    assert map_at_k([1, 2, 3], set(), 3) == 0.0


def test_map_at_k_empty_recommended():
    assert map_at_k([], {1, 2}, 5) == 0.0


def test_map_at_k_no_hits():
    assert map_at_k([10, 20, 30], {1, 2, 3}, 3) == pytest.approx(0.0)
