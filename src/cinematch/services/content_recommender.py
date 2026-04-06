"""Content-based recommender using pgvector and FAISS."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import faiss
import numpy as np
from pgvector.sqlalchemy import Vector
from sqlalchemy import bindparam, text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from cinematch.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class ContentRecommender:
    """Find similar movies via vector similarity (pgvector or FAISS)."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        faiss_index: faiss.Index,
        faiss_id_map: list[int],
    ) -> None:
        self._embedding_service = embedding_service
        self._faiss_index = faiss_index
        self._faiss_id_map = faiss_id_map
        self._id_to_faiss_idx: dict[int, int] = {mid: idx for idx, mid in enumerate(faiss_id_map)}

    async def get_similar_movies(
        self,
        movie_id: int,
        db: AsyncSession,
        top_k: int = 20,
        use_pgvector: bool = True,
    ) -> list[tuple[int, float]]:
        """Return ``(movie_id, similarity)`` pairs for the most similar movies."""
        if use_pgvector:
            try:
                results = await self._pgvector_search(movie_id, db, top_k)
                if results:
                    return results
            except Exception:
                logger.warning(
                    "pgvector search failed for movie %s, falling back to FAISS",
                    movie_id,
                    exc_info=True,
                )
        return self._faiss_search(movie_id, top_k)

    async def _pgvector_search(
        self,
        movie_id: int,
        db: AsyncSession,
        top_k: int,
    ) -> list[tuple[int, float]]:
        """Query pgvector using negative inner product operator."""
        # Fetch the query movie's embedding
        result = await db.execute(
            text("SELECT embedding FROM movies WHERE id = :movie_id"),
            {"movie_id": movie_id},
        )
        row = result.first()
        if row is None or row[0] is None:
            return []

        raw_embedding = row[0]
        # asyncpg returns pgvector values as strings via text() queries;
        # parse to a list so the Vector bindparam adapter can serialize it.
        query_embedding = (
            json.loads(raw_embedding) if isinstance(raw_embedding, str) else raw_embedding
        )

        # Find similar movies using <#> (negative inner product)
        stmt = text(
            "SELECT id, (embedding <#> :query_embedding) * -1 AS similarity "
            "FROM movies "
            "WHERE id != :movie_id AND embedding IS NOT NULL "
            "ORDER BY embedding <#> :query_embedding "
            "LIMIT :top_k"
        ).bindparams(bindparam("query_embedding", type_=Vector(384)))
        result = await db.execute(
            stmt,
            {
                "query_embedding": query_embedding,
                "movie_id": movie_id,
                "top_k": top_k,
            },
        )
        return [(r[0], float(r[1])) for r in result.fetchall()]

    def _faiss_search(
        self,
        movie_id: int,
        top_k: int,
    ) -> list[tuple[int, float]]:
        """Search FAISS index for similar movies."""
        faiss_idx = self._id_to_faiss_idx.get(movie_id)
        if faiss_idx is None:
            return []

        query_vec = self._faiss_index.reconstruct(faiss_idx).reshape(1, -1)
        distances, indices = self._faiss_index.search(query_vec.astype(np.float32), top_k + 1)

        results: list[tuple[int, float]] = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            mid = self._faiss_id_map[idx]
            if mid == movie_id:
                continue
            results.append((mid, float(dist)))

        return results[:top_k]

    def faiss_search_by_vector(
        self,
        query_vec: np.ndarray,
        top_k: int = 20,
        exclude_ids: set[int] | None = None,
    ) -> list[tuple[int, float]]:
        """Search FAISS index with an arbitrary query vector."""
        exclude = exclude_ids or set()
        fetch_k = top_k + len(exclude)
        vec = query_vec.reshape(1, -1).astype(np.float32)
        distances, indices = self._faiss_index.search(vec, fetch_k)

        results: list[tuple[int, float]] = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            mid = self._faiss_id_map[idx]
            if mid in exclude:
                continue
            results.append((mid, float(dist)))
            if len(results) >= top_k:
                break

        return results
