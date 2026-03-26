"""Tests for CollabRecommender."""

from __future__ import annotations

import numpy as np


def test_recommend_for_user_returns_ranked_list(collab_recommender):
    results = collab_recommender.recommend_for_user(user_id=1, top_k=3)
    assert len(results) == 3
    # Verify descending order
    scores = [s for _, s in results]
    assert scores == sorted(scores, reverse=True)


def test_recommend_for_user_returns_movie_ids(collab_recommender):
    results = collab_recommender.recommend_for_user(user_id=1, top_k=3)
    movie_ids = [mid for mid, _ in results]
    # Mock returns item indices [0, 2, 4] -> movie_ids [101, 103, 105]
    assert movie_ids == [101, 103, 105]


def test_recommend_for_user_cold_start_returns_empty(collab_recommender):
    results = collab_recommender.recommend_for_user(user_id=999, top_k=5)
    assert results == []


def test_recommend_for_user_respects_top_k(collab_recommender):
    collab_recommender.recommend_for_user(user_id=1, top_k=2)
    collab_recommender._model.recommend.assert_called_once()
    call_kwargs = collab_recommender._model.recommend.call_args
    assert call_kwargs[1]["N"] == 2


def test_score_items_returns_scores_for_known_movies(collab_recommender):
    scores = collab_recommender.score_items(user_id=1, movie_ids=[101, 103])
    assert 101 in scores
    assert 103 in scores
    # Scores should be dot products of user/item factors
    expected_101 = float(
        np.dot(collab_recommender._model.user_factors[0], collab_recommender._model.item_factors[0])
    )
    assert abs(scores[101] - expected_101) < 1e-5


def test_score_items_cold_start_returns_empty_dict(collab_recommender):
    scores = collab_recommender.score_items(user_id=999, movie_ids=[101])
    assert scores == {}


def test_score_items_skips_unknown_movies(collab_recommender):
    scores = collab_recommender.score_items(user_id=1, movie_ids=[101, 999])
    assert 101 in scores
    assert 999 not in scores


def test_is_known_user_true_for_known(collab_recommender):
    assert collab_recommender.is_known_user(1) is True
    assert collab_recommender.is_known_user(2) is True


def test_is_known_user_false_for_unknown(collab_recommender):
    assert collab_recommender.is_known_user(999) is False
