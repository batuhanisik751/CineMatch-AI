"""Hybrid recommender combining content-based and collaborative filtering."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

import numpy as np
from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from cinematch.services.collab_recommender import CollabRecommender
    from cinematch.services.content_recommender import ContentRecommender
    from cinematch.services.llm_service import LLMService

logger = logging.getLogger(__name__)

# Articles to strip when comparing franchise base titles
_ARTICLES = re.compile(r"^(the|a|an)\s+", re.IGNORECASE)
# Trailing sequel markers: numbers, roman numerals, colon+subtitle
_SEQUEL_SUFFIX = re.compile(r"\s*[:]\s*.*$|\s+\d+$|\s+(II|III|IV|V|VI|VII|VIII|IX|X)$")


class HybridRecommender:
    """Combine content and collaborative scores with configurable alpha."""

    def __init__(
        self,
        content_recommender: ContentRecommender,
        collab_recommender: CollabRecommender,
        alpha: float = 0.5,
        llm_service: LLMService | None = None,
        sequel_penalty: float = 0.5,
        diversity_lambda: float = 0.7,
        rerank_candidates: int = 50,
        llm_rerank_enabled: bool = True,
    ) -> None:
        self._content = content_recommender
        self._collab = collab_recommender
        self._alpha = alpha
        self._llm = llm_service
        self._sequel_penalty = sequel_penalty
        self._diversity_lambda = diversity_lambda
        self._rerank_candidates = rerank_candidates
        self._llm_rerank_enabled = llm_rerank_enabled

    async def recommend(
        self,
        user_id: int,
        db: AsyncSession,
        top_k: int = 20,
        strategy: str = "hybrid",
    ) -> list[tuple[int, float]]:
        """Main entry point. Strategy: 'hybrid', 'content', or 'collab'."""
        if strategy == "hybrid":
            return await self._hybrid_recommend(user_id, db, top_k)
        if strategy == "content":
            return await self._content_only_recommend(user_id, db, top_k)
        if strategy == "collab":
            return self._collab_only_recommend(user_id, top_k)
        raise ValueError(f"Unknown strategy: {strategy!r}. Use 'hybrid', 'content', or 'collab'.")

    async def _hybrid_recommend(
        self,
        user_id: int,
        db: AsyncSession,
        top_k: int,
    ) -> list[tuple[int, float]]:
        """Full hybrid: alpha * content + (1 - alpha) * collab, with diversity."""
        alpha = self._alpha if self._collab.is_known_user(user_id) else 1.0

        if alpha == 1.0:
            return await self._content_only_recommend(user_id, db, top_k)

        # Step 1: collaborative candidates
        collab_results = self._collab.recommend_for_user(user_id, top_k=200)
        collab_scores: dict[int, float] = dict(collab_results)

        # Step 2: user's top-rated movies (genre-diverse)
        user_top = await self._get_user_top_rated_diverse(user_id, db, limit=10)
        if not user_top:
            return collab_results[:top_k]

        # Step 3: content candidates from user's favorites
        content_raw: dict[int, list[float]] = {}
        for rated_movie_id, user_rating in user_top:
            similar = await self._content.get_similar_movies(rated_movie_id, db, top_k=50)
            weight = user_rating / 10.0
            for mid, similarity in similar:
                content_raw.setdefault(mid, []).append(similarity * weight)

        # Step 4: aggregate content scores
        content_scores: dict[int, float] = {
            mid: float(np.mean(sims)) for mid, sims in content_raw.items()
        }

        # Step 5: merge pools, exclude already-rated
        rated_ids = await self._get_user_rated_movie_ids(user_id, db)
        all_candidates = (set(collab_scores) | set(content_scores)) - rated_ids

        # Step 6: normalize
        collab_norm = self._min_max_normalize(collab_scores)
        content_norm = self._min_max_normalize(content_scores)

        # Step 7: compute hybrid scores
        scored: dict[int, float] = {}
        for mid in all_candidates:
            c_score = content_norm.get(mid, 0.0)
            f_score = collab_norm.get(mid, 0.0)
            scored[mid] = alpha * c_score + (1 - alpha) * f_score

        # Step 8: franchise/sequel penalty
        seed_titles = await self._get_movie_titles([mid for mid, _ in user_top], db)
        seed_bases = {self._base_title(t) for t in seed_titles.values()}
        candidate_titles = await self._get_movie_titles(list(scored.keys()), db)
        for mid, title in candidate_titles.items():
            if mid in scored and self._base_title(title) in seed_bases:
                scored[mid] *= self._sequel_penalty

        # Step 9: sort and over-fetch for re-ranking
        fetch_n = max(top_k, self._rerank_candidates)
        ranked = sorted(scored.items(), key=lambda r: r[1], reverse=True)[:fetch_n]

        # Step 10: LLM re-ranking (with MMR fallback)
        final = await self._rerank(ranked, candidate_titles, seed_titles, user_top, db, top_k)

        return final

    async def _content_only_recommend(
        self,
        user_id: int,
        db: AsyncSession,
        top_k: int,
    ) -> list[tuple[int, float]]:
        """Content-only: recommend based on user's top-rated movies."""
        user_top = await self._get_user_top_rated_diverse(user_id, db, limit=10)
        if not user_top:
            return []

        content_raw: dict[int, list[float]] = {}
        for rated_movie_id, user_rating in user_top:
            similar = await self._content.get_similar_movies(rated_movie_id, db, top_k=50)
            weight = user_rating / 10.0
            for mid, similarity in similar:
                content_raw.setdefault(mid, []).append(similarity * weight)

        content_scores = {mid: float(np.mean(sims)) for mid, sims in content_raw.items()}

        rated_ids = await self._get_user_rated_movie_ids(user_id, db)
        scored: dict[int, float] = {
            mid: score for mid, score in content_scores.items() if mid not in rated_ids
        }

        # Franchise penalty
        seed_titles = await self._get_movie_titles([mid for mid, _ in user_top], db)
        seed_bases = {self._base_title(t) for t in seed_titles.values()}
        candidate_titles = await self._get_movie_titles(list(scored.keys()), db)
        for mid, title in candidate_titles.items():
            if mid in scored and self._base_title(title) in seed_bases:
                scored[mid] *= self._sequel_penalty

        fetch_n = max(top_k, self._rerank_candidates)
        ranked = sorted(scored.items(), key=lambda r: r[1], reverse=True)[:fetch_n]

        final = await self._rerank(ranked, candidate_titles, seed_titles, user_top, db, top_k)
        return final

    def _collab_only_recommend(
        self,
        user_id: int,
        top_k: int,
    ) -> list[tuple[int, float]]:
        """Collab-only: delegate to CollabRecommender."""
        if not self._collab.is_known_user(user_id):
            raise ValueError(
                f"User {user_id} has no collaborative filtering data yet. "
                "Use 'hybrid' or 'content' strategy for cold-start users."
            )
        return self._collab.recommend_for_user(user_id, top_k=top_k)

    # ------------------------------------------------------------------
    # Re-ranking: LLM primary, MMR fallback
    # ------------------------------------------------------------------

    async def _rerank(
        self,
        ranked: list[tuple[int, float]],
        candidate_titles: dict[int, str],
        seed_titles: dict[int, str],
        user_top: list[tuple[int, float]],
        db: AsyncSession,
        top_k: int,
    ) -> list[tuple[int, float]]:
        """Try LLM re-ranking; fall back to MMR on failure."""
        if self._llm_rerank_enabled and self._llm is not None:
            try:
                candidate_genres = await self._get_movie_genres([mid for mid, _ in ranked], db)
                llm_result = await self._llm_rerank(
                    ranked, candidate_titles, candidate_genres, seed_titles, user_top
                )
                if llm_result is not None:
                    return llm_result[:top_k]
            except Exception:
                logger.warning("LLM re-ranking failed, falling back to MMR.", exc_info=True)

        # MMR fallback
        candidate_genres = await self._get_movie_genres([mid for mid, _ in ranked], db)
        return self._mmr_rerank(ranked, candidate_genres, top_k)

    async def _llm_rerank(
        self,
        ranked: list[tuple[int, float]],
        candidate_titles: dict[int, str],
        candidate_genres: dict[int, list[str]],
        seed_titles: dict[int, str],
        user_top: list[tuple[int, float]],
    ) -> list[tuple[int, float]] | None:
        """Ask the LLM to re-rank candidates. Returns None if parsing fails."""
        if self._llm is None:
            return None

        reranked_ids = await self._llm.rerank_candidates(
            candidates=[
                {
                    "id": mid,
                    "title": candidate_titles.get(mid, f"Movie #{mid}"),
                    "genres": candidate_genres.get(mid, []),
                    "score": round(score, 3),
                }
                for mid, score in ranked
            ],
            user_history=[
                {
                    "title": seed_titles.get(mid, f"Movie #{mid}"),
                    "rating": rating,
                }
                for mid, rating in user_top
            ],
        )

        if reranked_ids is None:
            return None

        score_map = dict(ranked)
        result = []
        for mid in reranked_ids:
            if mid in score_map:
                result.append((mid, score_map[mid]))
        return result if result else None

    def _mmr_rerank(
        self,
        ranked: list[tuple[int, float]],
        genres_map: dict[int, list[str]],
        top_k: int,
    ) -> list[tuple[int, float]]:
        """Maximal Marginal Relevance using genre Jaccard similarity."""
        if not ranked:
            return []

        # Normalize scores for MMR
        scores = self._min_max_normalize(dict(ranked))
        selected: list[tuple[int, float]] = []
        remaining = list(ranked)
        lam = self._diversity_lambda

        for _ in range(min(top_k, len(ranked))):
            best_mid, best_score, best_idx = -1, -float("inf"), -1
            for idx, (mid, orig_score) in enumerate(remaining):
                relevance = scores.get(mid, 0.0)
                if selected:
                    max_sim = max(
                        self._jaccard(
                            set(genres_map.get(mid, [])),
                            set(genres_map.get(sel_mid, [])),
                        )
                        for sel_mid, _ in selected
                    )
                else:
                    max_sim = 0.0
                mmr = lam * relevance - (1 - lam) * max_sim
                if mmr > best_score:
                    best_score = mmr
                    best_mid = mid
                    best_idx = idx
            if best_mid == -1:
                break
            selected.append((best_mid, remaining[best_idx][1]))
            remaining.pop(best_idx)

        return selected

    # ------------------------------------------------------------------
    # Mood-based recommendation
    # ------------------------------------------------------------------

    async def mood_recommend(
        self,
        mood_text: str,
        user_id: int,
        db: AsyncSession,
        alpha: float = 0.3,
        top_k: int = 20,
    ) -> tuple[list[tuple[int, float]], bool]:
        """Recommend movies matching a mood, optionally blended with user taste.

        Returns ``(results, is_personalized)`` where *is_personalized* is
        ``False`` for cold-start users (no ratings).
        """
        mood_vec = self._content._embedding_service.embed_text(mood_text)

        user_top = await self._get_user_top_rated_diverse(user_id, db, limit=10)
        if not user_top:
            rated_ids = await self._get_user_rated_movie_ids(user_id, db)
            results = self._content.faiss_search_by_vector(mood_vec, top_k, exclude_ids=rated_ids)
            return results, False

        # Build user taste vector from FAISS-stored embeddings
        weighted_vecs: list[np.ndarray] = []
        total_weight = 0.0
        for movie_id, rating in user_top:
            faiss_idx = self._content._id_to_faiss_idx.get(movie_id)
            if faiss_idx is None:
                continue
            vec = self._content._faiss_index.reconstruct(int(faiss_idx))
            weight = rating / 10.0
            weighted_vecs.append(vec * weight)
            total_weight += weight

        if not weighted_vecs:
            # All rated movies missing from FAISS — fall back to pure mood
            rated_ids = await self._get_user_rated_movie_ids(user_id, db)
            results = self._content.faiss_search_by_vector(mood_vec, top_k, exclude_ids=rated_ids)
            return results, False

        user_taste_vec = np.sum(weighted_vecs, axis=0) / total_weight
        # L2-normalize
        norm = np.linalg.norm(user_taste_vec)
        if norm > 0:
            user_taste_vec = user_taste_vec / norm

        # Blend and re-normalize
        query_vec = alpha * user_taste_vec + (1 - alpha) * mood_vec
        norm = np.linalg.norm(query_vec)
        if norm > 0:
            query_vec = query_vec / norm

        rated_ids = await self._get_user_rated_movie_ids(user_id, db)
        results = self._content.faiss_search_by_vector(query_vec, top_k, exclude_ids=rated_ids)
        return results, True

    # ------------------------------------------------------------------
    # Diverse seed selection
    # ------------------------------------------------------------------

    async def _get_user_top_rated_diverse(
        self,
        user_id: int,
        db: AsyncSession,
        limit: int = 10,
    ) -> list[tuple[int, float]]:
        """Pick top-rated movies ensuring genre diversity among seeds."""
        # Fetch more than needed so we can diversify
        result = await db.execute(
            text(
                "SELECT r.movie_id, r.rating, m.genres FROM ratings r "
                "JOIN movies m ON r.movie_id = m.id "
                "WHERE r.user_id = :user_id "
                "ORDER BY r.rating DESC, r.timestamp DESC "
                "LIMIT :fetch_limit"
            ),
            {"user_id": user_id, "fetch_limit": limit * 3},
        )
        rows = result.fetchall()
        if not rows:
            return []

        # Greedily pick: prefer top-rated, but skip if genre set already covered
        selected: list[tuple[int, float]] = []
        covered_genres: set[str] = set()

        for movie_id, rating, genres in rows:
            if len(selected) >= limit:
                break
            movie_genres = set(genres) if genres else set()
            new_genres = movie_genres - covered_genres
            # Always pick if we haven't filled up and either:
            # - it brings new genres, OR
            # - we've exhausted new genre options (all remaining share genres)
            if new_genres or len(selected) < limit:
                selected.append((movie_id, float(rating)))
                covered_genres.update(movie_genres)

        return selected

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    async def _get_user_top_rated(
        self,
        user_id: int,
        db: AsyncSession,
        limit: int = 10,
    ) -> list[tuple[int, float]]:
        """Fetch user's highest-rated movies as ``(movie_id, rating)``."""
        result = await db.execute(
            text(
                "SELECT movie_id, rating FROM ratings "
                "WHERE user_id = :user_id "
                "ORDER BY rating DESC, timestamp DESC "
                "LIMIT :limit"
            ),
            {"user_id": user_id, "limit": limit},
        )
        return [(r[0], float(r[1])) for r in result.fetchall()]

    async def _get_user_rated_movie_ids(
        self,
        user_id: int,
        db: AsyncSession,
    ) -> set[int]:
        """Get all movie IDs the user has rated."""
        result = await db.execute(
            text("SELECT movie_id FROM ratings WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
        return {r[0] for r in result.fetchall()}

    async def _get_movie_titles(
        self,
        movie_ids: list[int],
        db: AsyncSession,
    ) -> dict[int, str]:
        """Batch fetch movie titles."""
        if not movie_ids:
            return {}
        result = await db.execute(
            text("SELECT id, title FROM movies WHERE id = ANY(:ids)"),
            {"ids": movie_ids},
        )
        return {r[0]: r[1] for r in result.fetchall()}

    async def _get_movie_genres(
        self,
        movie_ids: list[int],
        db: AsyncSession,
    ) -> dict[int, list[str]]:
        """Batch fetch movie genres."""
        if not movie_ids:
            return {}
        result = await db.execute(
            text("SELECT id, genres FROM movies WHERE id = ANY(:ids)"),
            {"ids": movie_ids},
        )
        return {r[0]: (r[1] if r[1] else []) for r in result.fetchall()}

    @staticmethod
    def _base_title(title: str) -> str:
        """Extract franchise base title for sequel detection.

        Examples: 'Cars 2' -> 'cars', 'Star Wars: A New Hope' -> 'star wars'.
        """
        t = _SEQUEL_SUFFIX.sub("", title).strip()
        t = _ARTICLES.sub("", t).strip()
        return t.lower()

    @staticmethod
    def _jaccard(a: set, b: set) -> float:
        """Jaccard similarity between two sets."""
        if not a and not b:
            return 1.0
        union = a | b
        if not union:
            return 0.0
        return len(a & b) / len(union)

    @staticmethod
    def _min_max_normalize(scores: dict[int, float]) -> dict[int, float]:
        """Normalize scores to [0, 1]. Returns 0.5 for all if values are equal."""
        if not scores:
            return scores
        min_s = min(scores.values())
        max_s = max(scores.values())
        if max_s == min_s:
            return {k: 0.5 for k in scores}
        return {k: (v - min_s) / (max_s - min_s) for k, v in scores.items()}
