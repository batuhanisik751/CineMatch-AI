"""Lightweight content recommender using pgvector only (no FAISS)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
from pgvector.sqlalchemy import Vector
from sqlalchemy import bindparam, text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from cinematch.services.lightweight_embedding_service import LightweightEmbeddingService

logger = logging.getLogger(__name__)


class LightweightContentRecommender:
    """Find similar movies via pgvector only — no FAISS dependency.

    Drop-in replacement for ``ContentRecommender`` in lightweight mode.
    """

    def __init__(self, embedding_service: LightweightEmbeddingService) -> None:
        self._embedding_service = embedding_service
        # Stubs so accidental attribute access fails gracefully
        self._faiss_index = None
        self._faiss_id_map: list[int] = []
        self._id_to_faiss_idx: dict[int, int] = {}

    # ------------------------------------------------------------------
    # Public interface (matches ContentRecommender)
    # ------------------------------------------------------------------

    async def get_similar_movies(
        self,
        movie_id: int,
        db: AsyncSession,
        top_k: int = 20,
        use_pgvector: bool = True,
    ) -> list[tuple[int, float]]:
        """Return ``(movie_id, similarity)`` pairs via pgvector."""
        return await self._pgvector_search(movie_id, db, top_k)

    async def pgvector_search_by_vector(
        self,
        query_vec: np.ndarray,
        db: AsyncSession,
        top_k: int = 20,
        exclude_ids: set[int] | None = None,
    ) -> list[tuple[int, float]]:
        """Search pgvector with an arbitrary query vector.

        Replaces ``ContentRecommender.faiss_search_by_vector`` for
        lightweight mode.
        """
        exclude = list(exclude_ids) if exclude_ids else []
        vec_list = query_vec.tolist()

        if exclude:
            stmt = text(
                "SELECT id, (embedding <#> :query_vec) * -1 AS similarity "
                "FROM movies "
                "WHERE embedding IS NOT NULL AND id != ALL(:exclude_ids) "
                "ORDER BY embedding <#> :query_vec "
                "LIMIT :top_k"
            ).bindparams(bindparam("query_vec", type_=Vector(384)))
            result = await db.execute(
                stmt,
                {"query_vec": vec_list, "exclude_ids": exclude, "top_k": top_k},
            )
        else:
            stmt = text(
                "SELECT id, (embedding <#> :query_vec) * -1 AS similarity "
                "FROM movies "
                "WHERE embedding IS NOT NULL "
                "ORDER BY embedding <#> :query_vec "
                "LIMIT :top_k"
            ).bindparams(bindparam("query_vec", type_=Vector(384)))
            result = await db.execute(
                stmt,
                {"query_vec": vec_list, "top_k": top_k},
            )

        return [(r[0], float(r[1])) for r in result.fetchall()]

    async def fetch_embeddings(
        self,
        movie_ids: list[int],
        db: AsyncSession,
    ) -> dict[int, np.ndarray]:
        """Batch-fetch movie embeddings from the database.

        Replaces FAISS ``reconstruct()`` calls.
        """
        if not movie_ids:
            return {}
        result = await db.execute(
            text("SELECT id, embedding FROM movies WHERE id = ANY(:ids) AND embedding IS NOT NULL"),
            {"ids": movie_ids},
        )
        return {
            row[0]: np.array(row[1], dtype=np.float32) for row in result.fetchall()
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _pgvector_search(
        self,
        movie_id: int,
        db: AsyncSession,
        top_k: int,
    ) -> list[tuple[int, float]]:
        """Query pgvector using negative inner product operator."""
        result = await db.execute(
            text("SELECT embedding FROM movies WHERE id = :movie_id"),
            {"movie_id": movie_id},
        )
        row = result.first()
        if row is None or row[0] is None:
            return []

        query_embedding = row[0]

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
