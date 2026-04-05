"""Tests for LightweightEmbeddingService (HuggingFace Inference API)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from cinematch.services.lightweight_embedding_service import LightweightEmbeddingService


@pytest.fixture()
def mock_httpx_client():
    """Mock httpx.Client that returns a known 384-dim vector."""
    client = MagicMock()
    vec_384 = list(np.random.RandomState(42).randn(384).astype(float))
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = vec_384
    response.raise_for_status = MagicMock()
    client.post.return_value = response
    return client, vec_384


@pytest.fixture()
def embedding_service_lw(mock_httpx_client):
    """LightweightEmbeddingService with mocked HTTP client."""
    client, _ = mock_httpx_client
    svc = LightweightEmbeddingService(inference_url="https://fake-api.example.com")
    svc._client = client
    return svc


def test_embed_text_returns_normalized_384(embedding_service_lw, mock_httpx_client):
    _, raw_vec = mock_httpx_client
    result = embedding_service_lw.embed_text("test query")
    assert result.shape == (384,)
    assert result.dtype == np.float32
    # Should be L2-normalized
    norm = np.linalg.norm(result)
    assert abs(norm - 1.0) < 1e-5


def test_embed_batch_returns_normalized_array():
    svc = LightweightEmbeddingService(inference_url="https://fake-api.example.com")
    rng = np.random.RandomState(42)
    batch_response = rng.randn(3, 384).tolist()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = batch_response
    mock_resp.raise_for_status = MagicMock()
    svc._client = MagicMock()
    svc._client.post.return_value = mock_resp

    result = svc.embed_batch(["a", "b", "c"])
    assert result.shape == (3, 384)
    assert result.dtype == np.float32
    # Each row should be L2-normalized
    norms = np.linalg.norm(result, axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-5)


def test_embed_text_retries_on_503():
    svc = LightweightEmbeddingService(inference_url="https://fake-api.example.com")

    vec_384 = list(np.random.RandomState(42).randn(384).astype(float))
    resp_503 = MagicMock()
    resp_503.status_code = 503
    resp_ok = MagicMock()
    resp_ok.status_code = 200
    resp_ok.json.return_value = vec_384
    resp_ok.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.post.side_effect = [resp_503, resp_ok]
    svc._client = mock_client

    with patch("cinematch.services.lightweight_embedding_service.time.sleep"):
        result = svc.embed_text("test")
    assert result.shape == (384,)
    assert mock_client.post.call_count == 2


def test_embed_text_raises_after_max_retries():
    svc = LightweightEmbeddingService(inference_url="https://fake-api.example.com")

    resp_503 = MagicMock()
    resp_503.status_code = 503

    mock_client = MagicMock()
    mock_client.post.return_value = resp_503
    svc._client = mock_client

    with patch("cinematch.services.lightweight_embedding_service.time.sleep"):
        with pytest.raises(RuntimeError, match="failed after"):
            svc.embed_text("test")


def test_build_movie_text():
    text = LightweightEmbeddingService.build_movie_text(
        title="The Matrix",
        overview="A hacker discovers reality is a simulation.",
        genres=["Action", "Sci-Fi"],
        keywords=["hacker", "simulation"],
    )
    assert text.startswith("The Matrix.")
    assert "Genres: Action, Sci-Fi." in text
    assert "Keywords: hacker, simulation." in text


def test_warm_up_does_not_raise(embedding_service_lw):
    embedding_service_lw.warm_up()  # Should not raise


def test_close(embedding_service_lw):
    embedding_service_lw.close()
    embedding_service_lw._client.close.assert_called_once()
