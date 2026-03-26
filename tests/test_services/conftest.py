"""Shared fixtures for service tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import faiss
import numpy as np
import pytest
import scipy.sparse as sp

from cinematch.services.collab_recommender import CollabRecommender
from cinematch.services.content_recommender import ContentRecommender
from cinematch.services.embedding_service import EmbeddingService
from cinematch.services.hybrid_recommender import HybridRecommender

EMBEDDING_DIM = 384
SAMPLE_MOVIE_IDS = [101, 102, 103, 104, 105]


def _make_normalized_vectors(n: int, dim: int = EMBEDDING_DIM, seed: int = 42) -> np.ndarray:
    """Generate deterministic L2-normalized vectors."""
    rng = np.random.RandomState(seed)
    vecs = rng.randn(n, dim).astype(np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / norms


@pytest.fixture()
def mock_embedding_model():
    """Mock SentenceTransformer returning deterministic vectors."""
    model = MagicMock()
    vecs = _make_normalized_vectors(10)

    def _encode(text_or_texts, **kwargs):
        if isinstance(text_or_texts, str):
            return vecs[0]
        return vecs[: len(text_or_texts)]

    model.encode = MagicMock(side_effect=_encode)
    return model


@pytest.fixture()
def embedding_service(mock_embedding_model, monkeypatch):
    """EmbeddingService with mocked model (no real model download)."""
    monkeypatch.setattr(
        "cinematch.services.embedding_service.SentenceTransformer",
        lambda *a, **kw: mock_embedding_model,
    )
    svc = EmbeddingService(model_name="mock-model")
    return svc


@pytest.fixture()
def sample_embeddings():
    """5 known L2-normalized embeddings matching SAMPLE_MOVIE_IDS."""
    return _make_normalized_vectors(len(SAMPLE_MOVIE_IDS))


@pytest.fixture()
def sample_faiss_index(sample_embeddings):
    """Real FAISS IndexFlatIP with 5 vectors."""
    index = faiss.IndexFlatIP(EMBEDDING_DIM)
    index.add(sample_embeddings)
    return index


@pytest.fixture()
def sample_faiss_id_map():
    return list(SAMPLE_MOVIE_IDS)


@pytest.fixture()
def content_recommender(embedding_service, sample_faiss_index, sample_faiss_id_map):
    return ContentRecommender(embedding_service, sample_faiss_index, sample_faiss_id_map)


@pytest.fixture()
def mock_als_model():
    """Mock implicit ALS model with known outputs."""
    model = MagicMock()
    # recommend returns (item_indices, scores)
    model.recommend.return_value = (
        np.array([0, 2, 4]),
        np.array([0.9, 0.7, 0.5]),
    )
    # factor matrices for score_items dot product
    rng = np.random.RandomState(42)
    model.user_factors = rng.randn(3, 128).astype(np.float32)
    model.item_factors = rng.randn(5, 128).astype(np.float32)
    return model


@pytest.fixture()
def sample_user_map():
    return {1: 0, 2: 1, 3: 2}


@pytest.fixture()
def sample_item_map():
    return {101: 0, 102: 1, 103: 2, 104: 3, 105: 4}


@pytest.fixture()
def sample_user_items():
    """Sparse user-item matrix (3 users x 5 items)."""
    data = np.array([41.0, 201.0, 121.0, 81.0], dtype=np.float32)
    row = np.array([0, 0, 1, 2])
    col = np.array([0, 2, 4, 1])
    return sp.csr_matrix((data, (row, col)), shape=(3, 5))


@pytest.fixture()
def collab_recommender(mock_als_model, sample_user_map, sample_item_map, sample_user_items):
    return CollabRecommender(mock_als_model, sample_user_map, sample_item_map, sample_user_items)


@pytest.fixture()
def mock_db_session():
    """AsyncMock of AsyncSession with configurable execute results."""
    session = AsyncMock()
    return session


@pytest.fixture()
def hybrid_recommender(content_recommender, collab_recommender):
    return HybridRecommender(content_recommender, collab_recommender, alpha=0.5)
