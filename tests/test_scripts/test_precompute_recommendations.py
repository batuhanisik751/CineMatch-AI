"""Tests for the precompute_recommendations script."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import scipy.sparse as sp

# Ensure scripts/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from precompute_recommendations import (  # noqa: I001
    compute_user_recommendations,
    get_eligible_user_ids,
    get_valid_movie_ids,
    load_als_artifacts,
    precompute_recommendations,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture()
def mock_als_model():
    """Mock implicit ALS model returning deterministic recommendations."""
    model = MagicMock()
    model.recommend.return_value = (
        np.array([0, 2, 4, 1, 3]),
        np.array([0.95, 0.85, 0.75, 0.65, 0.55]),
    )
    return model


@pytest.fixture()
def sample_user_map():
    return {1: 0, 2: 1, 3: 2}


@pytest.fixture()
def sample_item_map():
    return {101: 0, 102: 1, 103: 2, 104: 3, 105: 4}


@pytest.fixture()
def reverse_item_map(sample_item_map):
    return {v: k for k, v in sample_item_map.items()}


@pytest.fixture()
def sample_user_items():
    """Sparse user-item matrix (3 users x 5 items)."""
    data = np.array([41.0, 201.0, 121.0, 81.0], dtype=np.float32)
    row = np.array([0, 0, 1, 2])
    col = np.array([0, 2, 4, 1])
    return sp.csr_matrix((data, (row, col)), shape=(3, 5))


@pytest.fixture()
def valid_movie_ids():
    return {101, 102, 103, 104, 105}


# ------------------------------------------------------------------
# compute_user_recommendations
# ------------------------------------------------------------------


def test_compute_returns_ranked_results(
    mock_als_model, sample_user_items, reverse_item_map, valid_movie_ids
):
    results = compute_user_recommendations(
        mock_als_model,
        user_idx=0,
        user_items_row=sample_user_items[0],
        reverse_item_map=reverse_item_map,
        valid_movie_ids=valid_movie_ids,
        top_k=5,
    )
    assert len(results) == 5
    # Check movie IDs are correctly mapped from item indices
    assert results[0] == (101, 0.95)  # index 0 -> movie 101
    assert results[1] == (103, 0.85)  # index 2 -> movie 103
    assert results[2] == (105, 0.75)  # index 4 -> movie 105
    assert results[3] == (102, 0.65)  # index 1 -> movie 102
    assert results[4] == (104, 0.55)  # index 3 -> movie 104


def test_compute_filters_invalid_movie_ids(mock_als_model, sample_user_items, reverse_item_map):
    # Only movies 101 and 103 are valid
    limited_valid = {101, 103}
    results = compute_user_recommendations(
        mock_als_model,
        user_idx=0,
        user_items_row=sample_user_items[0],
        reverse_item_map=reverse_item_map,
        valid_movie_ids=limited_valid,
        top_k=5,
    )
    assert len(results) == 2
    assert results[0] == (101, 0.95)
    assert results[1] == (103, 0.85)


def test_compute_handles_empty_recommendations(
    sample_user_items, reverse_item_map, valid_movie_ids
):
    model = MagicMock()
    model.recommend.return_value = (np.array([]), np.array([]))
    results = compute_user_recommendations(
        model,
        user_idx=0,
        user_items_row=sample_user_items[0],
        reverse_item_map=reverse_item_map,
        valid_movie_ids=valid_movie_ids,
        top_k=5,
    )
    assert results == []


# ------------------------------------------------------------------
# get_eligible_user_ids
# ------------------------------------------------------------------


def test_eligible_users_intersection(sample_user_map):
    session = MagicMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(1,), (2,), (3,), (4,), (5,)]
    session.execute.return_value = mock_result

    eligible = get_eligible_user_ids(session, sample_user_map)
    # user_map has keys {1, 2, 3}; DB has {1, 2, 3, 4, 5}
    assert eligible == [1, 2, 3]


def test_eligible_users_no_overlap(sample_user_map):
    session = MagicMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(10,), (20,)]
    session.execute.return_value = mock_result

    eligible = get_eligible_user_ids(session, sample_user_map)
    assert eligible == []


# ------------------------------------------------------------------
# get_valid_movie_ids
# ------------------------------------------------------------------


def test_get_valid_movie_ids():
    session = MagicMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(101,), (102,), (103,)]
    session.execute.return_value = mock_result

    result = get_valid_movie_ids(session)
    assert result == {101, 102, 103}


# ------------------------------------------------------------------
# load_als_artifacts
# ------------------------------------------------------------------


@patch("precompute_recommendations.sp.load_npz")
@patch("precompute_recommendations.pickle.load")
@patch("builtins.open", new_callable=MagicMock)
@patch("precompute_recommendations.verify_and_log")
def test_load_artifacts_raises_on_checksum_mismatch(mock_verify, mock_open, mock_pickle, mock_npz):
    mock_verify.return_value = "mismatch"
    settings = MagicMock()
    settings.als_model_path = "/fake/als_model.pkl"
    settings.als_user_map_path = "/fake/als_user_map.pkl"
    settings.als_item_map_path = "/fake/als_item_map.pkl"

    with pytest.raises(RuntimeError, match="Checksum FAILED"):
        load_als_artifacts(settings)


@patch("precompute_recommendations.sp.load_npz")
@patch("precompute_recommendations.pickle.load")
@patch("builtins.open", new_callable=MagicMock)
@patch("precompute_recommendations.verify_and_log")
def test_load_artifacts_raises_on_missing_file(mock_verify, mock_open, mock_pickle, mock_npz):
    mock_verify.return_value = "missing_artifact"
    settings = MagicMock()
    settings.als_model_path = "/fake/als_model.pkl"
    settings.als_user_map_path = "/fake/als_user_map.pkl"
    settings.als_item_map_path = "/fake/als_item_map.pkl"

    with pytest.raises(FileNotFoundError, match="Artifact not found"):
        load_als_artifacts(settings)


@patch("precompute_recommendations.Path")
@patch("precompute_recommendations.sp.load_npz")
@patch("precompute_recommendations.pickle.load")
@patch("builtins.open", new_callable=MagicMock)
@patch("precompute_recommendations.verify_and_log")
def test_load_artifacts_succeeds_on_verified(
    mock_verify, mock_open, mock_pickle, mock_npz, mock_path_cls
):
    mock_verify.return_value = "verified"
    mock_pickle.side_effect = ["model", {"1": 0}, {"101": 0}]
    mock_npz.return_value = sp.csr_matrix((1, 1))

    mock_path_instance = MagicMock()
    mock_path_instance.exists.return_value = True
    mock_path_cls.return_value = mock_path_instance

    settings = MagicMock()
    settings.als_model_path = "/fake/als_model.pkl"
    settings.als_user_map_path = "/fake/als_user_map.pkl"
    settings.als_item_map_path = "/fake/als_item_map.pkl"
    settings.als_user_items_path = "/fake/als_user_items.npz"

    model, user_map, item_map, user_items = load_als_artifacts(settings)
    assert model == "model"
    assert user_map == {"1": 0}
    assert item_map == {"101": 0}


# ------------------------------------------------------------------
# precompute_recommendations (full flow)
# ------------------------------------------------------------------


@patch("precompute_recommendations.load_als_artifacts")
@patch("precompute_recommendations.create_engine")
@patch("precompute_recommendations.get_settings")
def test_precompute_full_flow(mock_settings, mock_engine, mock_load):
    settings = MagicMock()
    settings.database_url_sync.get_secret_value.return_value = "postgresql://test"
    mock_settings.return_value = settings

    # Set up ALS artifacts
    model = MagicMock()
    model.recommend.return_value = (
        np.array([0, 1]),
        np.array([0.9, 0.8]),
    )
    user_map = {1: 0, 2: 1}
    item_map = {101: 0, 102: 1}
    user_items = sp.csr_matrix(
        (np.array([1.0, 1.0]), (np.array([0, 1]), np.array([0, 1]))),
        shape=(2, 2),
    )
    mock_load.return_value = (model, user_map, item_map, user_items)

    # Mock the Session context manager
    mock_session = MagicMock()
    mock_session_ctx = MagicMock()
    mock_session_ctx.__enter__ = MagicMock(return_value=mock_session)
    mock_session_ctx.__exit__ = MagicMock(return_value=False)

    # DB queries: eligible users, then valid movies
    user_result = MagicMock()
    user_result.fetchall.return_value = [(1,), (2,)]
    movie_result = MagicMock()
    movie_result.fetchall.return_value = [(101,), (102,)]
    mock_session.execute.side_effect = [user_result, movie_result] + [
        MagicMock()
    ] * 10  # DELETE + INSERT calls

    with patch("precompute_recommendations.Session", return_value=mock_session_ctx):
        precompute_recommendations(batch_size=500, top_k=2)

    # Verify model.recommend was called for each user
    assert model.recommend.call_count == 2

    # Verify session.commit was called (at least once for the batch)
    assert mock_session.commit.called

    # Verify DELETE and INSERT were executed
    execute_calls = mock_session.execute.call_args_list
    # First two are SELECT queries, then DELETE, then INSERT
    assert len(execute_calls) >= 4


@patch("precompute_recommendations.load_als_artifacts")
@patch("precompute_recommendations.create_engine")
@patch("precompute_recommendations.get_settings")
def test_precompute_skips_users_not_in_map(mock_settings, mock_engine, mock_load):
    settings = MagicMock()
    settings.database_url_sync.get_secret_value.return_value = "postgresql://test"
    mock_settings.return_value = settings

    model = MagicMock()
    model.recommend.return_value = (np.array([0]), np.array([0.9]))
    # user_map only has user 1
    user_map = {1: 0}
    item_map = {101: 0}
    user_items = sp.csr_matrix(
        (np.array([1.0]), (np.array([0]), np.array([0]))),
        shape=(1, 1),
    )
    mock_load.return_value = (model, user_map, item_map, user_items)

    mock_session = MagicMock()
    mock_session_ctx = MagicMock()
    mock_session_ctx.__enter__ = MagicMock(return_value=mock_session)
    mock_session_ctx.__exit__ = MagicMock(return_value=False)

    # DB has users 1, 2, 3 — but only user 1 is in user_map
    user_result = MagicMock()
    user_result.fetchall.return_value = [(1,), (2,), (3,)]
    movie_result = MagicMock()
    movie_result.fetchall.return_value = [(101,)]
    mock_session.execute.side_effect = [user_result, movie_result] + [MagicMock()] * 10

    with patch("precompute_recommendations.Session", return_value=mock_session_ctx):
        precompute_recommendations(batch_size=500, top_k=1)

    # Only user 1 should have recommendations computed
    assert model.recommend.call_count == 1


@patch("precompute_recommendations.load_als_artifacts")
@patch("precompute_recommendations.create_engine")
@patch("precompute_recommendations.get_settings")
def test_precompute_handles_empty_user_list(mock_settings, mock_engine, mock_load):
    settings = MagicMock()
    settings.database_url_sync.get_secret_value.return_value = "postgresql://test"
    mock_settings.return_value = settings

    model = MagicMock()
    user_map = {1: 0}
    item_map = {101: 0}
    user_items = sp.csr_matrix((1, 1))
    mock_load.return_value = (model, user_map, item_map, user_items)

    mock_session = MagicMock()
    mock_session_ctx = MagicMock()
    mock_session_ctx.__enter__ = MagicMock(return_value=mock_session)
    mock_session_ctx.__exit__ = MagicMock(return_value=False)

    # DB has no users that match
    user_result = MagicMock()
    user_result.fetchall.return_value = [(999,)]
    movie_result = MagicMock()
    movie_result.fetchall.return_value = [(101,)]
    mock_session.execute.side_effect = [user_result, movie_result]

    with patch("precompute_recommendations.Session", return_value=mock_session_ctx):
        precompute_recommendations(batch_size=500)

    # No recommendations computed, no commits for data
    model.recommend.assert_not_called()
