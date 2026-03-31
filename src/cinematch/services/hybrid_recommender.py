"""Hybrid recommender combining content-based and collaborative filtering."""

from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from cinematch.services.collab_recommender import CollabRecommender
    from cinematch.services.content_recommender import ContentRecommender
    from cinematch.services.llm_service import LLMService

logger = logging.getLogger(__name__)


@dataclass
class SeedInfluence:
    """Which seed movie contributed most to a candidate's content score."""

    movie_id: int
    title: str
    your_rating: float


@dataclass
class ScoreBreakdown:
    """Decomposition of the hybrid score."""

    content_score: float
    collab_score: float
    alpha: float


@dataclass
class RecommendationResult:
    """Rich recommendation result with explanation metadata."""

    movie_id: int
    score: float
    because_you_liked: SeedInfluence | None = None
    feature_explanations: list[str] = field(default_factory=list)
    score_breakdown: ScoreBreakdown | None = None


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
    ) -> list[RecommendationResult]:
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
    ) -> list[RecommendationResult]:
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
            return [
                RecommendationResult(
                    movie_id=mid,
                    score=score,
                    score_breakdown=ScoreBreakdown(
                        content_score=0.0,
                        collab_score=score,
                        alpha=0.0,
                    ),
                )
                for mid, score in collab_results[:top_k]
            ]

        # Step 3: content candidates from user's favorites (with seed tracking)
        content_scores, best_seed = await self._score_content_candidates(user_top, db)

        # Step 4: merge pools, exclude already-rated
        rated_ids = await self._get_user_rated_movie_ids(user_id, db)
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
        final = await self._rerank(ranked, candidate_titles, seed_titles, user_top, db, top_k)

        # Step 10: generate feature explanations for final results
        final_ids = [mid for mid, _ in final]
        feature_explanations = await self._generate_feature_explanations(
            final_ids,
            user_top,
            best_seed,
            seed_titles,
            db,
        )

        # Assemble rich results
        return self._build_results(final, best_seed, seed_titles, breakdowns, feature_explanations)

    async def _content_only_recommend(
        self,
        user_id: int,
        db: AsyncSession,
        top_k: int,
    ) -> list[RecommendationResult]:
        """Content-only: recommend based on user's top-rated movies."""
        user_top = await self._get_user_top_rated_diverse(user_id, db, limit=10)
        if not user_top:
            return []

        content_scores, best_seed = await self._score_content_candidates(user_top, db)

        rated_ids = await self._get_user_rated_movie_ids(user_id, db)
        scored: dict[int, float] = {
            mid: score for mid, score in content_scores.items() if mid not in rated_ids
        }

        # Build breakdowns (content-only: alpha=1.0, collab=0.0)
        content_norm = self._min_max_normalize(scored)
        breakdowns: dict[int, ScoreBreakdown] = {
            mid: ScoreBreakdown(
                content_score=round(content_norm.get(mid, 0.0), 4),
                collab_score=0.0,
                alpha=1.0,
            )
            for mid in scored
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

        # Generate feature explanations for final results
        final_ids = [mid for mid, _ in final]
        feature_explanations = await self._generate_feature_explanations(
            final_ids,
            user_top,
            best_seed,
            seed_titles,
            db,
        )

        return self._build_results(final, best_seed, seed_titles, breakdowns, feature_explanations)

    def _collab_only_recommend(
        self,
        user_id: int,
        top_k: int,
    ) -> list[RecommendationResult]:
        """Collab-only: delegate to CollabRecommender."""
        if not self._collab.is_known_user(user_id):
            raise ValueError(
                f"User {user_id} has no collaborative filtering data yet. "
                "Use 'hybrid' or 'content' strategy for cold-start users."
            )
        return [
            RecommendationResult(
                movie_id=mid,
                score=score,
                score_breakdown=ScoreBreakdown(
                    content_score=0.0,
                    collab_score=score,
                    alpha=0.0,
                ),
            )
            for mid, score in self._collab.recommend_for_user(user_id, top_k=top_k)
        ]

    # ------------------------------------------------------------------
    # Content scoring with seed tracking
    # ------------------------------------------------------------------

    async def _score_content_candidates(
        self,
        user_top: list[tuple[int, float]],
        db: AsyncSession,
    ) -> tuple[dict[int, float], dict[int, tuple[int, float, float]]]:
        """Score candidates from seed movies.

        Returns ``(content_scores, best_seed)`` where *best_seed* maps each
        candidate movie_id to ``(seed_id, weighted_similarity, seed_rating)``.
        """
        content_raw: dict[int, list[float]] = {}
        best_seed: dict[int, tuple[int, float, float]] = {}
        for rated_movie_id, user_rating in user_top:
            similar = await self._content.get_similar_movies(rated_movie_id, db, top_k=50)
            weight = user_rating / 10.0
            for mid, similarity in similar:
                weighted = similarity * weight
                content_raw.setdefault(mid, []).append(weighted)
                if mid not in best_seed or weighted > best_seed[mid][1]:
                    best_seed[mid] = (rated_movie_id, weighted, user_rating)

        content_scores: dict[int, float] = {
            mid: float(np.mean(sims)) for mid, sims in content_raw.items()
        }
        return content_scores, best_seed

    # ------------------------------------------------------------------
    # Result assembly
    # ------------------------------------------------------------------

    @staticmethod
    def _build_results(
        final: list[tuple[int, float]],
        best_seed: dict[int, tuple[int, float, float]],
        seed_titles: dict[int, str],
        breakdowns: dict[int, ScoreBreakdown],
        feature_explanations: dict[int, list[str]],
    ) -> list[RecommendationResult]:
        """Wrap reranked tuples into rich ``RecommendationResult`` objects."""
        results: list[RecommendationResult] = []
        for mid, score in final:
            seed = best_seed.get(mid)
            influence = None
            if seed is not None:
                seed_id, _, seed_rating = seed
                influence = SeedInfluence(
                    movie_id=seed_id,
                    title=seed_titles.get(seed_id, f"Movie #{seed_id}"),
                    your_rating=seed_rating,
                )
            results.append(
                RecommendationResult(
                    movie_id=mid,
                    score=score,
                    because_you_liked=influence,
                    feature_explanations=feature_explanations.get(mid, []),
                    score_breakdown=breakdowns.get(mid),
                )
            )
        return results

    # ------------------------------------------------------------------
    # Feature-based explanations (Level 2)
    # ------------------------------------------------------------------

    async def _generate_feature_explanations(
        self,
        final_ids: list[int],
        user_top: list[tuple[int, float]],
        best_seed: dict[int, tuple[int, float, float]],
        seed_titles: dict[int, str],
        db: AsyncSession,
    ) -> dict[int, list[str]]:
        """Generate template-based explanation strings for final recommendations."""
        if not final_ids:
            return {}

        seed_ids = [mid for mid, _ in user_top]
        all_ids = list(set(final_ids) | set(seed_ids))
        metadata = await self._get_movie_metadata(all_ids, db)

        # Build user preference profile from seeds
        genre_counts: Counter[str] = Counter()
        director_to_seed: dict[str, str] = {}  # director -> seed title
        actor_counts: Counter[str] = Counter()

        for seed_id, rating in user_top:
            meta = metadata.get(seed_id)
            if meta is None:
                continue
            for g in meta["genres"]:
                genre_counts[g] += 1
            if meta["director"]:
                director_to_seed.setdefault(
                    meta["director"], seed_titles.get(seed_id, f"Movie #{seed_id}")
                )
            if rating >= 8.0:
                for actor in meta["cast_names"]:
                    actor_counts[actor] += 1

        top_genres = {g for g, c in genre_counts.items() if c >= 2}
        top_actors = {a for a, c in actor_counts.items() if c >= 2}

        explanations: dict[int, list[str]] = {}
        for mid in final_ids:
            meta = metadata.get(mid)
            if meta is None:
                continue
            tags: list[str] = []

            # Director match
            if meta["director"] and meta["director"] in director_to_seed and len(tags) < 2:
                seed_title = director_to_seed[meta["director"]]
                tags.append(f"Same director as {seed_title} \u2014 {meta['director']}")

            # Genre overlap
            if top_genres and len(tags) < 2:
                overlap = [g for g in meta["genres"] if g in top_genres]
                if len(overlap) >= 2:
                    tags.append(f"Matches your love of {overlap[0]} and {overlap[1]}")
                elif len(overlap) == 1:
                    tags.append(f"Matches your love of {overlap[0]}")

            # Cast match
            if top_actors and len(tags) < 2:
                for actor in meta["cast_names"]:
                    if actor in top_actors:
                        count = actor_counts[actor]
                        tags.append(
                            f"Stars {actor}, who appears in {count} of your top-rated films"
                        )
                        break

            if tags:
                explanations[mid] = tags

        return explanations

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
    # Seed-based recommendation ("More Like This")
    # ------------------------------------------------------------------

    async def from_seed_recommend(
        self,
        seed_movie_id: int,
        user_id: int,
        db: AsyncSession,
        top_k: int = 20,
    ) -> list[RecommendationResult]:
        """Recommend movies similar to a seed, optionally personalized.

        Uses the seed movie as the sole content anchor.  If the user has
        collaborative-filtering data the content scores are blended with
        ALS item scores; otherwise pure content similarity is returned.
        """
        # 1 — content candidates from the seed
        similar = await self._content.get_similar_movies(seed_movie_id, db, top_k=100)
        if not similar:
            return []
        content_scores: dict[int, float] = dict(similar)

        # 2 — collaborative scoring (if available)
        alpha = self._alpha
        collab_scores: dict[int, float] = {}
        if self._collab.is_known_user(user_id):
            collab_scores = self._collab.score_items(user_id, list(content_scores.keys()))
        else:
            alpha = 1.0

        # 3 — filter already-rated movies and the seed itself
        rated_ids = await self._get_user_rated_movie_ids(user_id, db)
        excluded = rated_ids | {seed_movie_id}
        candidates = set(content_scores) - excluded

        if not candidates:
            return []

        # 4 — normalize
        content_norm = self._min_max_normalize(
            {mid: content_scores[mid] for mid in candidates},
        )
        collab_norm = self._min_max_normalize(
            {mid: collab_scores[mid] for mid in candidates if mid in collab_scores},
        )

        # 5 — hybrid score + breakdowns
        scored: dict[int, float] = {}
        breakdowns: dict[int, ScoreBreakdown] = {}
        for mid in candidates:
            c = content_norm.get(mid, 0.0)
            f = collab_norm.get(mid, 0.0)
            scored[mid] = alpha * c + (1 - alpha) * f
            breakdowns[mid] = ScoreBreakdown(
                content_score=round(c, 4),
                collab_score=round(f, 4),
                alpha=alpha,
            )

        # 6 — best-seed map (single seed for all candidates)
        best_seed: dict[int, tuple[int, float, float]] = {
            mid: (seed_movie_id, content_scores[mid], 10.0) for mid in candidates
        }

        # 7 — franchise / sequel penalty
        seed_titles = await self._get_movie_titles([seed_movie_id], db)
        seed_bases = {self._base_title(t) for t in seed_titles.values()}
        candidate_titles = await self._get_movie_titles(list(scored.keys()), db)
        for mid, title in candidate_titles.items():
            if mid in scored and self._base_title(title) in seed_bases:
                scored[mid] *= self._sequel_penalty

        # 8 — sort & over-fetch for MMR
        fetch_n = max(top_k, self._rerank_candidates)
        ranked = sorted(scored.items(), key=lambda r: r[1], reverse=True)[:fetch_n]

        # 9 — MMR diversity re-rank (skip LLM — single-seed context)
        genres_map = await self._get_movie_genres([mid for mid, _ in ranked], db)
        final = self._mmr_rerank(ranked, genres_map, top_k)

        # 10 — feature explanations
        user_top: list[tuple[int, float]] = [(seed_movie_id, 10.0)]
        final_ids = [mid for mid, _ in final]
        feature_explanations = await self._generate_feature_explanations(
            final_ids,
            user_top,
            best_seed,
            seed_titles,
            db,
        )

        return self._build_results(final, best_seed, seed_titles, breakdowns, feature_explanations)

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

    async def _get_movie_metadata(
        self,
        movie_ids: list[int],
        db: AsyncSession,
    ) -> dict[int, dict]:
        """Batch fetch genres, director, cast_names for movies."""
        if not movie_ids:
            return {}
        result = await db.execute(
            text("SELECT id, genres, director, cast_names FROM movies WHERE id = ANY(:ids)"),
            {"ids": movie_ids},
        )
        return {
            r[0]: {
                "genres": r[1] or [],
                "director": r[2],
                "cast_names": r[3] or [],
            }
            for r in result.fetchall()
        }

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
