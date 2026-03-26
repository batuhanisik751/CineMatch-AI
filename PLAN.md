# CineMatch-AI: Improvement Plan

## Problem 1: Show Movie Name Instead of Movie ID in Rating History

**Current state:** The Profile page's Rating History table shows `#movie_id` (e.g., `#123`). The API endpoint `GET /users/{user_id}/ratings` returns `RatingResponse` which only has `movie_id`, not the movie title. The DB query in `RatingService.get_user_ratings()` selects only from the `ratings` table with no join to `movies`.

### Plan

**Backend:**
1. **Add `movie_title` to `RatingResponse` schema** in `src/cinematch/schemas/rating.py` — add an optional `movie_title: str | None = None` field.
2. **Join movies table in `RatingService.get_user_ratings()`** in `src/cinematch/services/rating_service.py` — modify the query to `select(Rating, Movie.title).join(Movie, Rating.movie_id == Movie.id)` so the title comes back in a single query (no N+1).
3. **Populate `movie_title` in the API layer** in `src/cinematch/api/v1/ratings.py` — map the joined result into `RatingResponse` with the title included.

**Frontend:**
4. **Update `RatingResponse` type** in `frontend/src/api/types.ts` — add `movie_title?: string`.
5. **Update Profile table** in `frontend/src/pages/Profile.tsx` — change the "Movie ID" column header to "Movie" and render `r.movie_title` (with fallback to `#movie_id` if null). Make the title a clickable link to `/movies/{movie_id}`.

### Files to modify
- `src/cinematch/schemas/rating.py`
- `src/cinematch/services/rating_service.py`
- `src/cinematch/api/v1/ratings.py`
- `frontend/src/api/types.ts`
- `frontend/src/pages/Profile.tsx`
- `tests/` — update existing rating tests for the new field

---

## Problem 2: Fuzzy/Typo-Tolerant Search ("Casr" -> "Cars")

**Current state:** Search uses `ILIKE '%query%'` (simple substring match) in `MovieService.search_by_title()`. A `pg_trgm` GIN index already exists on `movies.title` but the code never uses trigram similarity functions. So "Casr" returns nothing because it's not a substring of any title.

### Plan

**Backend — hybrid search strategy (exact match + fuzzy fallback):**
1. **Add a fuzzy search method** to `src/cinematch/services/movie_service.py`:
   - First, try the existing `ILIKE` search. If it returns results, use them (fast path for correct spelling).
   - If `ILIKE` returns zero results, fall back to `pg_trgm` similarity search using `similarity(title, query)` with a threshold (e.g., 0.2) and order by similarity score descending.
   - This way, exact matches are prioritized but typos still find results.

2. **Implement the trigram query** using SQLAlchemy:
   ```python
   # Fuzzy fallback query
   stmt = (
       select(Movie, func.similarity(Movie.title, query).label("sim"))
       .where(func.similarity(Movie.title, query) > 0.2)
       .order_by(desc("sim"), Movie.popularity.desc())
       .limit(limit)
   )
   ```
   The `pg_trgm` extension is already enabled and the GIN index `idx_movies_title_trgm` exists, so this requires no migration.

3. **Alternative enhancement — combine both in one query:** Use `ILIKE` results unioned with trigram results, deduplicated, with exact matches ranked higher. This gives the best UX: "Cars" returns Cars immediately, "Casr" returns Cars via fuzzy match.

**Frontend:**
4. No frontend changes needed — the search endpoint contract stays the same.

### Files to modify
- `src/cinematch/services/movie_service.py` — modify `search_by_title()` or add `fuzzy_search()`
- `src/cinematch/api/v1/movies.py` — possibly no change if we modify the existing method
- `tests/` — add tests for fuzzy search behavior

---

## Problem 3: Richer, More Diverse Hybrid Recommendations + LLM-Powered Re-ranking

**Current state:** The hybrid recommender in `hybrid_recommender.py`:
- Gets the user's top 10 rated movies
- For each, fetches 30 similar movies from content recommender (embedding similarity)
- Averages content scores, normalizes, blends with ALS collab scores
- **No diversity mechanism exists** — no genre spreading, no franchise dedup, no penalty for sequels
- **Mistral LLM is optional** and only used for post-hoc explanations, never for the recommendation logic itself

This causes: Rating "Cars" recommends "Cars 2" and "Cars 3" (highest embedding similarity = same franchise). Rating "Star Wars" only gives other Star Wars films. The recommendations feel mechanical and lack the nuanced reasoning an LLM could provide.

### Plan

**A. Make Mistral a requirement (not optional):**
1. **Remove the feature flag** — `CINEMATCH_LLM_ENABLED` defaults to `True` in `src/cinematch/config.py` instead of `False`.
2. **Always initialize LLMService** in `src/cinematch/main.py` — remove the conditional `if settings.llm_enabled` guard. Keep a graceful fallback: if Ollama is unreachable at startup, log a warning but still start the app (LLM re-ranking degrades gracefully to the existing scoring pipeline).
3. **Update `.env.example`** — set `CINEMATCH_LLM_ENABLED=true` and add a comment that Mistral is required.
4. **Update `CLAUDE.md`** — change the "Optional LLM" section to "Required LLM", remove "Optional" wording.

**B. LLM-powered recommendation re-ranking:**
5. **Add an LLM re-ranking step** to the hybrid pipeline in `src/cinematch/services/hybrid_recommender.py`:
   - After the standard hybrid scoring produces a candidate list (e.g., top 50 candidates), pass the top candidates to Mistral for intelligent re-ranking.
   - Build a prompt that gives Mistral: (a) the user's rating history (top-rated movies with genres), (b) the candidate list with titles/genres/overviews, (c) instructions to re-rank based on thematic coherence, variety, and user taste patterns.
   - Parse Mistral's ranked output and use it as the final ordering.
   - **Fallback**: if the LLM call fails (timeout, Ollama down), fall back to the existing score-based ranking. The system must never break due to LLM unavailability.

6. **LLM re-ranking prompt design** — add a new method `_llm_rerank()` to `LLMService`:
   - Input: user's top-rated movies (title + genre + rating), candidate movies (title + genre + overview + score)
   - Prompt instructs Mistral to:
     - Consider genre diversity (don't cluster on one genre)
     - Penalize sequels/franchises (prefer unique films over franchise entries)
     - Match thematic patterns the user enjoys (not just surface-level genre matching)
     - Return a JSON array of movie IDs in recommended order
   - Parse the JSON response, validate movie IDs are from the candidate set
   - Over-fetch candidates (top 50) so Mistral has a broad pool to re-rank down to `top_k` (default 20)

7. **Add `llm_rerank` method to `LLMService`** in `src/cinematch/services/llm_service.py`:
   - Accepts: `candidates: list[dict]` (id, title, genres, overview, score), `user_history: list[dict]` (title, genres, rating)
   - Builds the re-ranking prompt
   - POSTs to Ollama `/api/generate` with `format: "json"` for structured output
   - Parses the response as a JSON list of movie IDs
   - Returns the re-ordered list of movie IDs
   - Timeout: higher than explanations (e.g., 60s) since re-ranking processes more data

**C. Genre diversity re-ranking (MMR-style fallback):**
8. **Add a diversity re-ranker** to `src/cinematch/services/hybrid_recommender.py`:
   - This serves as the non-LLM diversity mechanism AND the fallback when LLM is unavailable.
   - After computing the final blended scores, apply Maximal Marginal Relevance (MMR).
   - For each slot in the final list, pick the movie that maximizes: `lambda * relevance_score - (1 - lambda) * max_similarity_to_already_selected`.
   - Use Jaccard similarity on genre sets as the "similarity to already selected" metric.
   - Use a configurable `diversity_lambda` (e.g., 0.7 = mostly relevance, 0.3 diversity weight).

**D. Franchise/sequel penalty:**
9. **Detect franchise duplicates** — movies sharing the same base title (e.g., "Cars", "Cars 2", "Cars 3").
   - Simple heuristic: if a candidate's title starts with the same base words as a seed movie's title, apply a score penalty (e.g., multiply score by 0.5).
   - Applied BEFORE both LLM re-ranking and MMR, so the LLM also gets pre-penalized scores as a signal.

**E. Broader content candidate pool:**
10. **Increase seed diversity** — currently uses the user's top 10 movies by rating. Modify to pick top-rated movies spanning different genres:
    - Instead of just `ORDER BY rating DESC LIMIT 10`, select the top movie from each genre the user has rated.
    - This prevents all 10 seeds from being the same franchise/genre.

11. **Expand candidate sourcing** for LLM re-ranking:
    - Increase content candidates per seed from 30 to 50.
    - For collab candidates, increase from 100 to 200.
    - Over-fetch top 50 scored candidates, send to LLM, return top `top_k`.

**F. Configuration:**
12. **Add/update config parameters** in `src/cinematch/config.py`:
    - `llm_enabled: bool = True` — now defaults to True
    - `llm_rerank_enabled: bool = True` — separate flag to toggle LLM re-ranking (allows disabling re-ranking while keeping explanations)
    - `llm_rerank_timeout: float = 60.0` — higher timeout for re-ranking
    - `llm_rerank_candidates: int = 50` — how many candidates to send to LLM
    - `hybrid_diversity_lambda: float = 0.7` — MMR diversity tradeoff (used as fallback)
    - `hybrid_sequel_penalty: float = 0.5` — score multiplier for same-franchise movies

### Pipeline flow (updated)

```
User request → Hybrid scoring (content + collab blend)
            → Franchise penalty (score adjustment)
            → Over-fetch top 50 candidates
            → LLM re-rank (Mistral picks best 20 from 50, considering diversity + taste)
            → If LLM fails: MMR diversity re-rank (fallback)
            → Return top_k results
```

### Files to modify
- `src/cinematch/config.py` — new config parameters, `llm_enabled` default to `True`
- `src/cinematch/main.py` — always initialize LLMService (with graceful fallback)
- `src/cinematch/services/llm_service.py` — add `llm_rerank()` method with re-ranking prompt
- `src/cinematch/services/hybrid_recommender.py` — franchise penalty, diverse seeds, LLM re-ranking call, MMR fallback
- `src/cinematch/api/v1/recommendations.py` — pass `llm_service` to hybrid recommender
- `src/cinematch/api/deps.py` — may need to update dependency injection
- `.env.example` — update LLM defaults
- `CLAUDE.md` — update LLM documentation
- `tests/test_services/test_hybrid_recommender.py` — tests for LLM re-ranking, franchise penalty, MMR, diverse seeds
- `tests/test_services/test_llm_service.py` — tests for `llm_rerank()` method

---

## Implementation Order

1. ~~**Problem 1** (Movie Name in Ratings)~~ — DONE
2. ~~**Problem 2** (Fuzzy Search)~~ — DONE
3. **Problem 3** (Richer Recommendations + LLM Re-ranking) — implement in this order:
   a. Make Mistral required (config + startup changes)
   b. Franchise/sequel penalty
   c. Diverse seed selection
   d. MMR diversity re-ranking (fallback)
   e. LLM `llm_rerank()` method
   f. Integrate LLM re-ranking into hybrid pipeline
   g. Tests for all new logic
