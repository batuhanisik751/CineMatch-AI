"""Embedding service wrapping sentence-transformers for runtime use."""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """Load a sentence-transformers model and provide embedding methods."""

    def __init__(self, model_name: str, batch_size: int = 256) -> None:
        self._model = SentenceTransformer(model_name)
        self._batch_size = batch_size

    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text string. Returns L2-normalized (384,) float32 vector."""
        return self._model.encode(text, normalize_embeddings=True)

    def embed_batch(self, texts: list[str], batch_size: int | None = None) -> np.ndarray:
        """Embed multiple texts. Returns L2-normalized (N, 384) float32 array."""
        return self._model.encode(
            texts,
            batch_size=batch_size or self._batch_size,
            normalize_embeddings=True,
        )

    @staticmethod
    def build_movie_text(
        title: str,
        overview: str | None = None,
        genres: list[str] | None = None,
        keywords: list[str] | None = None,
    ) -> str:
        """Build text representation for embedding.

        Must produce identical output to ``pipeline/embedder.py:build_movie_text``
        for the same inputs.
        """
        parts: list[str] = [f"{title}."]
        if overview:
            parts.append(overview)
        if genres:
            parts.append(f"Genres: {', '.join(genres)}.")
        if keywords:
            parts.append(f"Keywords: {', '.join(keywords)}.")
        return " ".join(parts)
