"""Lightweight hybrid recommender — pgvector + cached collab (no FAISS/ALS)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from cinematch.services.hybrid_recommender import (
    HybridRecommender,
    PredictedMatchResult,
    RecommendationResult,
    ScoreBreakdown,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from cinematch.services.lightweight_collab_recommender import LightweightCollabRecommender
    from cinematch.services.lightweight_content_recommender import LightweightContentRecommender
    from cinematch.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class LightweightHybridRecommender(HybridRecommender):
    """Hybrid recommender for lightweight mode.

    Overrides methods that use FAISS ``reconstruct()`` /
    ``faiss_search_by_vector()`` or synchronous collab calls, replacing
    them with pgvector queries and async cache lookups.
    """

    def __init__(
        self,
        content_recommender: LightweightContentRecommender,
        collab_recommender: LightweightCollabRecommender,
        alpha: float = 0.5,
        llm_service: LLMService | None = None,
        sequel_penalty: float = 0.5,
        diversity_lambda: float = 0.7,
        rerank_candidates: int = 50,
        llm_rerank_enabled: bool = True,
    ) -> None:
        super().__init__(
            content_recommender=content_recommender,  # type: ignore[arg-type]
            collab_recommender=collab_recommender,  # type: ignore[arg-type]
            alpha=alpha,
            llm_service=llm_service,
            sequel_penalty=sequel_penalty,
            diversity_lambda=diversity_lambda,
            rerank_candidates=rerank_candidates,
            llm_rerank_enabled=llm_rerank_enabled,
        )

    # ------------------------------------------------------------------
    # Helper: fetch embeddings from DB (replaces FAISS reconstruct)
    # ------------------------------------------------------------------

    async def _fetch_embeddings(
        self,
        movie_ids: list[int],
        db: AsyncSession,
    ) -> dict[int, np.ndarray]:
        """Batch-fetch movie embeddings from the movies table."""
        return await self._content.fetch_embeddings(movie_ids, db)

    # ------------------------------------------------------------------
    # Override: _hybrid_recommend (sync collab calls → async)
    # ------------------------------------------------------------------

    async def _hybrid_recommend(
        self,
        user_id: int,
        db: AsyncSession,
        top_k: int,
        diversity_lambda: float | None = None,
    ) -> list[RecommendationResult]:
        """Full hybrid with async collab lookups."""
        alpha = self._alpha if await self._collab.is_known_user(user_id, db) else 1.0

        if alpha == 1.0:
            return await self._content_only_recommend(
                user_id, db, top_k, diversity_lambda=diversity_lambda
            )

        # Step 1: collaborative candidates from cache
        collab_results = await self._collab.recommend_for_user(user_id, db, top_k=200)
        collab_scores: dict[int, float] = dict(collab_results)

        # Step 2: user's top-rated movies (genre-diverse)
        user_top = await self._get_user_top_rated_diverse(user_id, db, limit=10)
        if not user_top:
            return [
                RecommendationResult(
                    movie_id=mid,
                    score=score,
                    score_breakdown=ScoreBreakdown(
                        content_score=0.0, collab_score=score, alpha=0.0
                    ),
                )
                for mid, score in collab_results[:top_k]
            ]

        # Step 3: content candidates from user's favorites (with seed tracking)
        content_scores, best_seed = await self._score_content_candidates(user_top, db)

        # Step 4: merge pools, exclude already-rated and dismissed
        rated_ids = await self._get_excluded_movie_ids(user_id, db)
        all_candidates = (set(collab_scores) | set(content_scores)) - rated_ids

        # Step 5: normalize
        collab_norm = self._min_max_normalize(collab_scores)
        content_norm = self._min_max_normalize(content_scores)

        # Step 6: compute hybrid scores + breakdowns
        scored: dict[int, float] = {}
        breakdowns: dict[int, ScoreBreakdown] = {}
        for mid in all_candidates:
            c_score = content_norm.get(mid, 0.0)
            f_score = collab_norm.get(mid, 0.0)
            scored[mid] = alpha * c_score + (1 - alpha) * f_score
            breakdowns[mid] = ScoreBreakdown(
                content_score=round(c_score, 4),
                collab_score=round(f_score, 4),
                alpha=alpha,
            )

        # Step 7: franchise/sequel penalty
        seed_titles = await self._get_movie_titles([mid for mid, _ in user_top], db)
        seed_bases = {self._base_title(t) for t in seed_titles.values()}
        candidate_titles = await self._get_movie_titles(list(scored.keys()), db)
        for mid, title in candidate_titles.items():
            if mid in scored and self._base_title(title) in seed_bases:
                scored[mid] *= self._sequel_penalty

        # Step 8: sort and over-fetch for re-ranking
        fetch_n = max(top_k, self._rerank_candidates)
        ranked = sorted(scored.items(), key=lambda r: r[1], reverse=True)[:fetch_n]

        # Step 9: LLM re-ranking (with MMR fallback)
        final = await self._rerank(
            ranked, candidate_titles, seed_titles, user_top, db, top_k,
            diversity_lambda=diversity_lambda,
        )

        # Step 10: generate feature explanations for final results
        final_ids = [mid for mid, _ in final]
        feature_explanations = await self._generate_feature_explanations(
            final_ids, user_top, best_seed, seed_titles, db,
        )

        return self._build_results(final, best_seed, seed_titles, breakdowns, feature_explanations)

    # ------------------------------------------------------------------
    # Override: _collab_only_recommend (sync → async)
    # ------------------------------------------------------------------

    async def _collab_only_recommend(
        self,
        user_id: int,
        db: AsyncSession,
        top_k: int = 50,
    ) -> list[RecommendationResult]:
        """Collab-only using precomputed cache (async)."""
        if not await self._collab.is_known_user(user_id, db):
            raise ValueError(
                f"User {user_id} has no collaborative filtering data yet. "
                "Use 'hybrid' or 'content' strategy for cold-start users."
            )
        results = await self._collab.recommend_for_user(user_id, db, top_k=top_k)
        return [
            RecommendationResult(
                movie_id=mid,
                score=score,
                score_breakdown=ScoreBreakdown(
                    content_score=0.0, collab_score=score, alpha=0.0
                ),
            )
            for mid, score in results
        ]

    # ------------------------------------------------------------------
    # Override: recommend dispatch (collab strategy now needs db)
    # ------------------------------------------------------------------

    async def recommend(
        self,
        user_id: int,
        db: AsyncSession,
        top_k: int = 20,
        strategy: str = "hybrid",
        diversity_lambda: float | None = None,
    ) -> list[RecommendationResult]:
        """Main entry point — dispatches to the right strategy."""
        if strategy == "hybrid":
            return await self._hybrid_recommend(
                user_id, db, top_k, diversity_lambda=diversity_lambda,
            )
        if strategy == "content":
            return await self._content_only_recommend(
                user_id, db, top_k, diversity_lambda=diversity_lambda,
            )
        if strategy == "collab":
            return await self._collab_only_recommend(user_id, db, top_k)
        raise ValueError(f"Unknown strategy: {strategy!r}. Use 'hybrid', 'content', or 'collab'.")

    # ------------------------------------------------------------------
    # Override: from_seed_recommend (sync collab calls → async)
    # ------------------------------------------------------------------

    async def from_seed_recommend(
        self,
        seed_movie_id: int,
        user_id: int,
        db: AsyncSession,
        top_k: int = 20,
    ) -> list[RecommendationResult]:
        """Seed-based recommendation with async collab lookups."""
        similar = await self._content.get_similar_movies(seed_movie_id, db, top_k=100)
        if not similar:
            return []
        content_scores: dict[int, float] = dict(similar)

        alpha = self._alpha
        collab_scores: dict[int, float] = {}
        if await self._collab.is_known_user(user_id, db):
            collab_scores = await self._collab.score_items(
                user_id, list(content_scores.keys()), db
            )
        else:
            alpha = 1.0

        rated_ids = await self._get_excluded_movie_ids(user_id, db)
        excluded = rated_ids | {seed_movie_id}
        candidates = set(content_scores) - excluded
        if not candidates:
            return []

        content_norm = self._min_max_normalize(
            {mid: content_scores[mid] for mid in candidates}
        )
        collab_norm = self._min_max_normalize(
            {mid: collab_scores[mid] for mid in candidates if mid in collab_scores}
        )

        scored: dict[int, float] = {}
        breakdowns: dict[int, ScoreBreakdown] = {}
        for mid in candidates:
            c = content_norm.get(mid, 0.0)
            f = collab_norm.get(mid, 0.0)
            scored[mid] = alpha * c + (1 - alpha) * f
            breakdowns[mid] = ScoreBreakdown(
                content_score=round(c, 4), collab_score=round(f, 4), alpha=alpha,
            )

        best_seed: dict[int, tuple[int, float, float]] = {
            mid: (seed_movie_id, content_scores[mid], 10.0) for mid in candidates
        }

        seed_titles = await self._get_movie_titles([seed_movie_id], db)
        seed_bases = {self._base_title(t) for t in seed_titles.values()}
        candidate_titles = await self._get_movie_titles(list(scored.keys()), db)
        for mid, title in candidate_titles.items():
            if mid in scored and self._base_title(title) in seed_bases:
                scored[mid] *= self._sequel_penalty

        fetch_n = max(top_k, self._rerank_candidates)
        ranked = sorted(scored.items(), key=lambda r: r[1], reverse=True)[:fetch_n]

        genres_map = await self._get_movie_genres([mid for mid, _ in ranked], db)
        final = self._mmr_rerank(ranked, genres_map, top_k)

        user_top: list[tuple[int, float]] = [(seed_movie_id, 10.0)]
        final_ids = [mid for mid, _ in final]
        feature_explanations = await self._generate_feature_explanations(
            final_ids, user_top, best_seed, seed_titles, db,
        )

        return self._build_results(final, best_seed, seed_titles, breakdowns, feature_explanations)

    # ------------------------------------------------------------------
    # Override: mood_recommend (FAISS → pgvector)
    # ------------------------------------------------------------------

    async def mood_recommend(
        self,
        mood_text: str,
        user_id: int,
        db: AsyncSession,
        alpha: float = 0.3,
        top_k: int = 20,
    ) -> tuple[list[tuple[int, float]], bool]:
        """Mood-based recommendation using pgvector instead of FAISS."""
        mood_vec = self._content._embedding_service.embed_text(mood_text)

        user_top = await self._get_user_top_rated_diverse(user_id, db, limit=10)
        if not user_top:
            excluded_ids = await self._get_excluded_movie_ids(user_id, db)
            results = await self._content.pgvector_search_by_vector(
                mood_vec, db, top_k, exclude_ids=excluded_ids
            )
            return results, False

        # Build user taste vector from DB-stored embeddings
        movie_ids = [mid for mid, _ in user_top]
        embeddings = await self._fetch_embeddings(movie_ids, db)

        weighted_vecs: list[np.ndarray] = []
        total_weight = 0.0
        for movie_id, rating in user_top:
            vec = embeddings.get(movie_id)
            if vec is None:
                continue
            weight = rating / 10.0
            weighted_vecs.append(vec * weight)
            total_weight += weight

        if not weighted_vecs:
            excluded_ids = await self._get_excluded_movie_ids(user_id, db)
            results = await self._content.pgvector_search_by_vector(
                mood_vec, db, top_k, exclude_ids=excluded_ids
            )
            return results, False

        user_taste_vec = np.sum(weighted_vecs, axis=0) / total_weight
        norm = np.linalg.norm(user_taste_vec)
        if norm > 0:
            user_taste_vec = user_taste_vec / norm

        query_vec = alpha * user_taste_vec + (1 - alpha) * mood_vec
        norm = np.linalg.norm(query_vec)
        if norm > 0:
            query_vec = query_vec / norm

        excluded_ids = await self._get_excluded_movie_ids(user_id, db)
        results = await self._content.pgvector_search_by_vector(
            query_vec, db, top_k, exclude_ids=excluded_ids
        )
        return results, True

    # ------------------------------------------------------------------
    # Override: watchlist_recommend (FAISS → pgvector)
    # ------------------------------------------------------------------

    async def watchlist_recommend(
        self,
        watchlist_movie_ids: list[int],
        user_id: int,
        db: AsyncSession,
        top_k: int = 10,
    ) -> list[tuple[int, float]]:
        """Watchlist-based recommendation using pgvector instead of FAISS."""
        if not watchlist_movie_ids:
            return []

        embeddings = await self._fetch_embeddings(watchlist_movie_ids, db)
        vecs = list(embeddings.values())
        if not vecs:
            return []

        mean_vec = np.mean(vecs, axis=0)
        norm = np.linalg.norm(mean_vec)
        if norm > 0:
            mean_vec = mean_vec / norm

        excluded = await self._get_excluded_movie_ids(user_id, db)
        excluded = excluded | set(watchlist_movie_ids)

        return await self._content.pgvector_search_by_vector(
            mean_vec, db, top_k, exclude_ids=excluded
        )

    # ------------------------------------------------------------------
    # Override: predict_match (FAISS + sync collab → pgvector + async)
    # ------------------------------------------------------------------

    async def predict_match(
        self,
        user_id: int,
        movie_ids: list[int],
        db: AsyncSession,
    ) -> list[PredictedMatchResult]:
        """Predicted match with pgvector embeddings and async collab."""
        user_top = await self._get_user_top_rated_diverse(user_id, db, limit=10)
        if not user_top:
            return []

        # Content: taste centroid similarity
        taste_vec = await self._compute_taste_centroid_async(user_top, db)
        content_scores: dict[int, float] = {}
        if taste_vec is not None:
            movie_embeddings = await self._fetch_embeddings(movie_ids, db)
            for mid in movie_ids:
                movie_vec = movie_embeddings.get(mid)
                if movie_vec is None:
                    content_scores[mid] = 0.0
                    continue
                sim = float(np.dot(taste_vec, movie_vec))
                content_scores[mid] = (sim + 1.0) / 2.0

        # Collaborative: sigmoid-normalized scores from cache
        is_known = await self._collab.is_known_user(user_id, db)
        alpha = self._alpha if is_known else 1.0
        collab_scores: dict[int, float] = {}
        if is_known:
            raw_collab = await self._collab.score_items(user_id, movie_ids, db)
            for mid, score in raw_collab.items():
                collab_scores[mid] = 1.0 / (1.0 + np.exp(-score))

        # Blend and scale to percentage
        results: list[PredictedMatchResult] = []
        for mid in movie_ids:
            c = content_scores.get(mid, 0.0)
            f = collab_scores.get(mid, 0.0)
            hybrid = alpha * c + (1.0 - alpha) * f
            pct = max(0, min(100, round(hybrid * 100)))
            results.append(
                PredictedMatchResult(
                    movie_id=mid,
                    match_percent=pct,
                    content_score=round(c, 4),
                    collab_score=round(f, 4),
                    alpha=alpha,
                )
            )
        return results

    # ------------------------------------------------------------------
    # Override: _compute_taste_centroid (FAISS → DB)
    # ------------------------------------------------------------------

    async def _compute_taste_centroid_async(
        self,
        user_top: list[tuple[int, float]],
        db: AsyncSession,
    ) -> np.ndarray | None:
        """Build weighted average embedding from DB instead of FAISS."""
        movie_ids = [mid for mid, _ in user_top]
        embeddings = await self._fetch_embeddings(movie_ids, db)

        weighted_vecs: list[np.ndarray] = []
        total_weight = 0.0
        for movie_id, rating in user_top:
            vec = embeddings.get(movie_id)
            if vec is None:
                continue
            weight = rating / 10.0
            weighted_vecs.append(vec * weight)
            total_weight += weight

        if not weighted_vecs:
            return None

        centroid = np.sum(weighted_vecs, axis=0) / total_weight
        norm = np.linalg.norm(centroid)
        if norm > 0:
            centroid = centroid / norm
        return centroid
