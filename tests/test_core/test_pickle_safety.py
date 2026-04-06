"""Tests for pickle artifact checksum verification."""

from __future__ import annotations

import pickle
from unittest.mock import patch

import pytest

from cinematch.core.pickle_safety import (
    compute_sha256,
    get_all_artifact_statuses,
    read_expected_checksum,
    save_checksum,
    verify_checksum,
)


@pytest.fixture()
def sample_artifact(tmp_path):
    """Create a sample pickle artifact."""
    path = tmp_path / "test_artifact.pkl"
    with open(path, "wb") as f:
        pickle.dump({"key": "value", "list": [1, 2, 3]}, f)
    return path


def test_compute_sha256_consistent(sample_artifact):
    hash1 = compute_sha256(sample_artifact)
    hash2 = compute_sha256(sample_artifact)
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex digest length


def test_save_checksum_creates_sidecar(sample_artifact):
    sidecar = save_checksum(sample_artifact)
    assert sidecar.exists()
    assert sidecar.name == "test_artifact.pkl.sha256"


def test_save_checksum_shasum_format(sample_artifact):
    save_checksum(sample_artifact)
    sidecar = sample_artifact.with_suffix(".pkl.sha256")
    content = sidecar.read_text()
    parts = content.strip().split("  ")
    assert len(parts) == 2
    assert len(parts[0]) == 64  # hex digest
    assert parts[1] == "test_artifact.pkl"  # filename only


def test_read_expected_checksum_exists(sample_artifact):
    save_checksum(sample_artifact)
    expected = read_expected_checksum(sample_artifact)
    assert expected is not None
    assert len(expected) == 64


def test_read_expected_checksum_missing(sample_artifact):
    result = read_expected_checksum(sample_artifact)
    assert result is None


def test_verify_checksum_verified(sample_artifact):
    save_checksum(sample_artifact)
    assert verify_checksum(sample_artifact) == "verified"


def test_verify_checksum_mismatch(sample_artifact):
    save_checksum(sample_artifact)
    # Modify the artifact after checksum was saved
    with open(sample_artifact, "wb") as f:
        pickle.dump({"tampered": True}, f)
    assert verify_checksum(sample_artifact) == "mismatch"


def test_verify_checksum_missing_checksum(sample_artifact):
    # No sidecar file exists
    assert verify_checksum(sample_artifact) == "missing_checksum"


def test_verify_checksum_missing_artifact(tmp_path):
    nonexistent = tmp_path / "does_not_exist.pkl"
    assert verify_checksum(nonexistent) == "missing_artifact"


def test_get_all_artifact_statuses_returns_four_items(tmp_path):
    """Mock settings to point at temp files and verify 4 entries returned."""
    # Create fake artifacts
    for name in [
        "faiss_id_map.pkl",
        "als_model.pkl",
        "als_user_map.pkl",
        "als_item_map.pkl",
    ]:
        path = tmp_path / name
        with open(path, "wb") as f:
            pickle.dump({"fake": name}, f)

    mock_settings = type(
        "Settings",
        (),
        {
            "faiss_id_map_path": str(tmp_path / "faiss_id_map.pkl"),
            "als_model_path": str(tmp_path / "als_model.pkl"),
            "als_user_map_path": str(tmp_path / "als_user_map.pkl"),
            "als_item_map_path": str(tmp_path / "als_item_map.pkl"),
        },
    )()

    with patch("cinematch.core.pickle_safety.get_settings", return_value=mock_settings):
        results = get_all_artifact_statuses()

    assert len(results) == 4
    for r in results:
        assert "file_name" in r
        assert "status" in r
        assert r["status"] == "missing_checksum"  # no sidecars created
        assert r["file_size_bytes"] is not None
        assert r["actual_hash"] is not None
