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

## Problem 3: Richer, More Diverse Hybrid Recommendations

**Current state:** The hybrid recommender in `hybrid_recommender.py`:
- Gets the user's top 10 rated movies
- For each, fetches 30 similar movies from content recommender (embedding similarity)
- Averages content scores, normalizes, blends with ALS collab scores
- **No diversity mechanism exists** — no genre spreading, no franchise dedup, no penalty for sequels

This causes: Rating "Cars" recommends "Cars 2" and "Cars 3" (highest embedding similarity = same franchise). Rating "Star Wars" only gives other Star Wars films.

### Plan

**A. Genre diversity re-ranking (MMR-style):**
1. **Add a diversity re-ranker** to `src/cinematch/services/hybrid_recommender.py`:
   - After computing the final blended scores, apply Maximal Marginal Relevance (MMR) or a greedy genre-coverage algorithm.
   - For each slot in the final list, pick the movie that maximizes: `lambda * relevance_score - (1 - lambda) * max_similarity_to_already_selected`.
   - This ensures the top-K results span multiple genres instead of clustering on one franchise.
   - Use a configurable `diversity_lambda` (e.g., 0.7 = mostly relevance, 0.3 diversity weight).

2. **Implementation approach:**
   - After scoring all candidates, load their genre data (already in the `movies` table).
   - Use Jaccard similarity on genre sets as the "similarity to already selected" metric.
   - Greedily select top_k movies that balance relevance and genre diversity.

**B. Franchise/sequel penalty:**
3. **Detect franchise duplicates** — movies sharing the same base title (e.g., "Cars", "Cars 2", "Cars 3") or belonging to the same collection.
   - Simple heuristic: if a candidate's title starts with the same base words as a seed movie's title, apply a score penalty (e.g., multiply score by 0.5).
   - More robust: use the `belongs_to_collection` field from TMDb metadata if available in the DB.

**C. Broader content candidate pool:**
4. **Increase seed diversity** — currently uses the user's top 10 movies by rating. Modify to pick top-rated movies that also span different genres:
   - Instead of just `ORDER BY rating DESC LIMIT 10`, select top movies ensuring genre variety (e.g., pick the top movie from each genre the user has rated).
   - This prevents all 10 seeds from being the same franchise/genre.

5. **Expand candidate sourcing** — consider adding more candidates:
   - Increase content candidates per seed from 30 to 50 (broader net).
   - For collab candidates, increase from 100 to 200.

**D. Configuration:**
6. **Add config parameters** to `src/cinematch/config.py`:
   - `hybrid_diversity_lambda: float = 0.7` — diversity vs relevance tradeoff
   - `hybrid_sequel_penalty: float = 0.5` — score multiplier for same-franchise movies

### Files to modify
- `src/cinematch/services/hybrid_recommender.py` — MMR re-ranking, sequel penalty, diverse seed selection
- `src/cinematch/config.py` — new config parameters
- `src/cinematch/models/movie.py` — may need to check if `genres` field is easily queryable
- `tests/test_services/test_hybrid_recommender.py` — tests for diversity and franchise penalty

---

## Implementation Order

1. **Problem 1** (Movie Name in Ratings) — simplest, self-contained backend+frontend change
2. **Problem 2** (Fuzzy Search) — backend-only, leverages existing pg_trgm infrastructure
3. **Problem 3** (Richer Recommendations) — most complex, requires careful tuning and testing
