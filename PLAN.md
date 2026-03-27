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

## Implementation Order (Completed)

1. ~~**Problem 1** (Movie Name in Ratings)~~ — DONE
2. ~~**Problem 2** (Fuzzy Search)~~ — DONE
3. ~~**Problem 3** (Richer Recommendations + LLM Re-ranking)~~ — DONE

---
---

# Phase 2: Additional Features

Below are feature options explored after completing the initial improvements. They are organized by category and ranked by impact vs. effort within each category.

---

## Option A: "Why This?" — LLM Explanations in the UI

**Impact: High | Effort: Low**

The backend already has `GET /users/{id}/recommendations/explain/{movie_id}` but the frontend never calls it. This is the lowest-effort, highest-impact feature to add.

### What to build
1. **Add an "Explain" button** on each recommendation card in the Recommendations page.
2. **Create an API client function** `getExplanation(userId, movieId, score)` in `frontend/src/api/recommendations.ts`.
3. **Add `RecommendationExplanation` type** to `frontend/src/api/types.ts`.
4. **Show the explanation in a modal or expandable panel** below the card when clicked. Display the LLM-generated text explaining why this movie matches the user's taste.
5. **Loading state** — show a spinner while waiting (Mistral takes a few seconds).

### Files to modify
- `frontend/src/api/recommendations.ts` — add `getExplanation()`
- `frontend/src/api/types.ts` — add `RecommendationExplanation` interface
- `frontend/src/pages/Recommendations.tsx` — add explain button + modal/panel per card

### Why it matters
Users currently see a list of movies with a match percentage but no reasoning. The explanation feature makes recommendations feel intelligent rather than random, and builds trust in the system.

---

## Option B: Semantic "Vibe" Search

**Impact: High | Effort: Medium**

Let users search by description/mood instead of just title. Example: "funny movie about time travel" or "dark thriller set in space".

### What to build

**Backend:**
1. **New endpoint** `GET /api/v1/movies/semantic-search?q=funny movie about time travel&limit=20`
2. **New service method** in `MovieService` — calls `EmbeddingService.embed_text(query)` to get a 384-dim vector, then queries pgvector with `<#>` operator to find movies with the most similar embeddings.
3. The `EmbeddingService.embed_text()` method already exists but is never used at runtime — this feature activates it.

**Frontend:**
4. **Add a toggle** on the search page or Home page: "Search by title" vs. "Search by vibe/description".
5. **Reuse the existing search results grid** — same `MovieCard` layout, just different data source.

### Files to modify
- `src/cinematch/services/movie_service.py` — add `semantic_search()` method
- `src/cinematch/api/v1/movies.py` — add `/semantic-search` endpoint
- `src/cinematch/schemas/movie.py` — possibly new response schema with similarity score
- `frontend/src/api/movies.ts` — add `semanticSearch()` client
- `frontend/src/pages/Search.tsx` or `frontend/src/pages/Home.tsx` — UI toggle

### Why it matters
This is a differentiating feature. Most movie apps only support title search. Semantic search lets users find movies by mood, theme, or plot description — exactly what embeddings were built for but are currently only used for "similar movies".

---

## Option C: Movie Discovery & Browsing

**Impact: High | Effort: Medium**

The app currently has no way to browse movies without already knowing a title. There's no "Popular", "Top Rated", "By Genre", or "New Releases" browsing.

### What to build

**Backend:**
1. **New endpoint** `GET /api/v1/movies?genre=Action&sort=popularity&year_min=2000&limit=20&offset=0` — general movie listing with filters and pagination.
2. **New endpoint** `GET /api/v1/genres` — returns all unique genres with movie counts.
3. Use existing JSONB GIN index on `movies.genres` for efficient genre filtering.

**Frontend:**
4. **New "Discover" page** or enhance the Home page with:
   - Genre chips/pills for filtering (Action, Comedy, Drama, Sci-Fi, etc.)
   - Sort dropdown (Popular, Top Rated, Newest, A-Z)
   - Year range slider
   - Infinite scroll or pagination
5. **Update Home page** — replace the static placeholder section with real data: "Popular Now", "Top Rated", "Recently Added" carousels.

### Files to modify
- `src/cinematch/services/movie_service.py` — add `list_movies()`, `get_genres()`
- `src/cinematch/api/v1/movies.py` — add browse/list and genres endpoints
- `src/cinematch/schemas/movie.py` — add filter/list schemas
- `frontend/src/pages/Home.tsx` — data-driven sections
- New `frontend/src/pages/Discover.tsx` — browse page
- `frontend/src/App.tsx` — add route

### Why it matters
New users can't get recommendations without rating movies first, and they can't find movies to rate without search. Browsing solves the cold-start UX problem.

---

## Option D: Watchlist / Save for Later

**Impact: Medium | Effort: Medium**

A standard feature for movie apps — let users bookmark movies they want to watch.

### What to build

**Backend:**
1. **New model** `Watchlist` — `user_id`, `movie_id`, `added_at`, unique constraint on (user_id, movie_id).
2. **New migration** for the `watchlist` table.
3. **New endpoints:**
   - `POST /api/v1/users/{id}/watchlist` — add movie to watchlist (body: `{"movie_id": 123}`)
   - `DELETE /api/v1/users/{id}/watchlist/{movie_id}` — remove from watchlist
   - `GET /api/v1/users/{id}/watchlist?offset=0&limit=20` — paginated watchlist with movie details
4. **New service** `WatchlistService` — CRUD operations.

**Frontend:**
5. **Bookmark icon** on `MovieCard` and `MovieDetail` — toggleable, shows filled/outlined state.
6. **Watchlist section** on the Profile page or a new Watchlist page.
7. **"Add to Watchlist" from recommendations** — quick-save without leaving the page.

### Files to modify
- New `src/cinematch/models/watchlist.py`
- New migration
- New `src/cinematch/services/watchlist_service.py`
- New `src/cinematch/api/v1/watchlist.py`
- New `src/cinematch/schemas/watchlist.py`
- `frontend/src/components/MovieCard.tsx` — bookmark button
- `frontend/src/pages/MovieDetail.tsx` — bookmark button
- New `frontend/src/pages/Watchlist.tsx` or update Profile

### Why it matters
Ratings are a commitment ("I've seen this and I rate it X/5"). Watchlisting is low-friction ("I want to see this"). It captures intent data that could later improve recommendations.

---

## Option E: Score Transparency — Show Content vs. Collab Breakdown

**Impact: Medium | Effort: Low**

The `RecommendationItem` schema already has `content_score` and `collab_score` fields but they're always `null`. Populate them and show users why each movie was recommended.

### What to build

**Backend:**
1. **Pass individual scores through** from `HybridRecommender` — return `(movie_id, hybrid_score, content_score, collab_score)` tuples instead of `(movie_id, score)`.
2. **Update the recommendation API endpoint** to populate `content_score` and `collab_score` on `RecommendationItem`.

**Frontend:**
3. **Score breakdown bar** on each recommendation card — a visual showing the content (blue) vs. collab (green) contribution. Example: "72% taste match, 28% similar users".
4. **Tooltip or label** explaining what each signal means.

### Files to modify
- `src/cinematch/services/hybrid_recommender.py` — return richer tuples
- `src/cinematch/api/v1/recommendations.py` — populate schema fields
- `frontend/src/pages/Recommendations.tsx` — score breakdown visualization

### Why it matters
Transparency builds trust. Users can understand "this was recommended because it's similar to movies you liked" (content) vs. "users like you also enjoyed this" (collab).

---

## Option F: Search Bar in Navigation + Search Page Input

**Impact: Medium | Effort: Low**

Currently there's no way to search from the Search page itself — users must go back to Home. The TopNav has no search input.

### What to build
1. **Add a search input** to `TopNav.tsx` — compact, expands on focus, submits to `/search?q=...`.
2. **Add a search input** at the top of the `Search.tsx` page — pre-filled with the current query, allows refining.
3. **Add pagination** to the search results — the backend already returns `total` but there's no offset param on the endpoint. Add `offset` to the API and paginate in the frontend.

### Files to modify
- `src/cinematch/api/v1/movies.py` — add `offset` query param to search endpoint
- `frontend/src/components/TopNav.tsx` — add search input
- `frontend/src/pages/Search.tsx` — add search input + pagination

### Why it matters
Basic usability. Users currently have no way to refine a search or start a new search without navigating away.

---

## Option G: Richer Embeddings — Include Cast & Director

**Impact: Medium | Effort: Low-Medium**

`cast_names` and `director` are cleaned and stored in the DB but excluded from the embedding text. Including them would capture "people who like Christopher Nolan films" patterns.

### What to build
1. **Update `build_movie_text()`** in both `src/cinematch/pipeline/embedder.py` and `src/cinematch/services/embedding_service.py` to include cast and director:
   ```python
   if director:
       parts.append(f"Director: {director}.")
   if cast_names:
       parts.append(f"Cast: {', '.join(cast_names[:5])}.")
   ```
2. **Re-run the pipeline** — `python scripts/train_models.py` to regenerate embeddings, FAISS index, and re-seed the DB.
3. **No API or frontend changes needed** — the downstream similar-movies and recommendations automatically benefit.

### Files to modify
- `src/cinematch/pipeline/embedder.py` — update `build_movie_text()`
- `src/cinematch/services/embedding_service.py` — update `build_movie_text()`

### Why it matters
Two users who both love "Quentin Tarantino" or "Leonardo DiCaprio" should get recommendations reflecting that. Currently the system is blind to who made or starred in a movie.

---

## Option H: User Profile Analytics Dashboard

**Impact: Medium | Effort: Medium**

The Profile page is minimal. A richer analytics view would make the app feel more personal.

### What to build
1. **Genre distribution chart** — pie or bar chart showing what genres the user rates most.
2. **Rating distribution histogram** — how many 1-star, 2-star, etc. ratings.
3. **Average rating fix** — the current average is computed from the current page only (bug), not all ratings. Compute on the backend instead.
4. **Favorite directors/actors** — derived from rated movies.
5. **Rating timeline** — when the user was most active.

**Backend:**
- New endpoint `GET /api/v1/users/{id}/stats` returning aggregated statistics.

**Frontend:**
- Chart library (e.g., recharts, chart.js) for visualizations.
- Updated Profile page with analytics sections.

### Files to modify
- New `src/cinematch/api/v1/users.py` endpoint or new file
- New `src/cinematch/services/user_stats_service.py`
- `frontend/src/pages/Profile.tsx` — add charts/analytics
- `frontend/package.json` — add chart library

### Why it matters
Makes the app feel personalized and sticky. Users enjoy seeing their own data reflected back.

---

## Option I: Hybrid Strategy Evaluation + Diversity Metrics

**Impact: High (for quality) | Effort: Medium**

The most important recommendation path (hybrid + MMR + LLM reranking) is the one that's never evaluated. The diversity mechanisms have no metrics proving they work.

### What to build
1. **Add "hybrid" to evaluated strategies** in `src/cinematch/evaluation/evaluate.py`.
2. **Add diversity metrics:**
   - **Intra-List Diversity (ILD)** — average pairwise genre dissimilarity within a recommendation list.
   - **Coverage** — fraction of the catalog that appears in at least one user's recommendations.
   - **Novelty** — inverse popularity of recommended items (recommending obscure good movies > obvious popular ones).
3. **Add cold-start evaluation** — separate metrics for users with <5 ratings.
4. **Generate a comparison report** — hybrid vs. content vs. collab across all metrics.

### Files to modify
- `src/cinematch/evaluation/metrics.py` — add ILD, coverage, novelty functions
- `src/cinematch/evaluation/evaluate.py` — add hybrid strategy, new metrics, cold-start split
- Possibly new `src/cinematch/evaluation/diversity.py`

### Why it matters
Without measurement, you can't know if the MMR reranking and LLM reranking are actually improving recommendations or just adding latency.

---

## Recommended Implementation Order

Pick based on your priorities:

**Quick wins (1-2 hours each):**
1. **Option A** — "Why This?" explanations (backend exists, just wire up the frontend)
2. **Option F** — Search bar in nav + search page refinement
3. **Option E** — Score transparency (schema fields already exist)

**Medium features (half day each):**
4. **Option G** — Richer embeddings with cast/director (requires pipeline re-run)
5. **Option B** — Semantic "vibe" search
6. **Option C** — Movie discovery/browsing
7. **Option H** — User profile analytics

**Larger features (1+ day each):**
8. **Option D** — Watchlist
9. **Option I** — Evaluation improvements
