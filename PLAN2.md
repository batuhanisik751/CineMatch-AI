# CineMatch-AI — Feature Enrichment Plan

## Overview

This plan covers high-impact features to make CineMatch-AI richer and more engaging. Every feature is implementable with the existing tech stack (FastAPI, React, PostgreSQL + pgvector, Redis, sentence-transformers, FAISS, implicit ALS) — no paid APIs or new infrastructure required.

Features are organized into 6 categories, ordered by impact-to-effort ratio within each.

---

## 1. CineMatch Wrapped — Year in Review

**Inspired by:** Spotify Wrapped, Letterboxd Year in Review

**What it is:** A personalized stats summary page showing a user's movie-watching year at a glance. Highly shareable and the kind of feature that keeps users coming back.

**Stats to compute (all from existing `ratings` + `movies` tables):**
- Total films rated that year
- Total estimated watch hours (sum of movie runtimes — requires adding `runtime` to the movie model, already available in `TMDB_all_movies.csv`)
- Favorite genre (mode of genres across rated films)
- Favorite director and actor (most frequently appearing in highly-rated films)
- Average rating given vs. global site average ("Are you a generous or harsh critic?")
- Longest rating streak (consecutive days with at least one rating)
- Most-rated decade (1980s? 2000s?)
- First and last film rated that year
- "Movie soulmate" — the user with the most similar rating vector (cosine similarity from ALS user factors, already loaded at startup)
- "Movie personality" archetype badge: e.g., "The Cinephile" (diverse genres, high avg), "The Blockbuster Fan" (action-heavy, high volume), "The Critic" (low avg rating), "The Explorer" (many foreign/indie films)

**Backend implementation:**
- New endpoint: `GET /api/v1/users/{user_id}/year-in-review?year=2025`
- New service: `YearInReviewService` — pure SQL aggregation queries on `ratings` joined with `movies`
- Movie soulmate: compute cosine similarity between the target user's ALS factor vector and all other users' vectors, return the closest match
- Schema migration: add `runtime` column to `movies` table (integer, minutes), populated from `TMDB_all_movies.csv` which already has this field
- Cache results in Redis with a 24-hour TTL (stats don't change frequently)

**Frontend implementation:**
- New page: `/year-in-review` — a visually rich scrollable summary with large stat numbers, genre pie chart (reuse Recharts from Profile), and the personality badge
- Shareable: use `html2canvas` to render the summary as a downloadable image — no backend needed for the share step

**Files affected:**
- New: `src/cinematch/services/year_in_review_service.py`, `src/cinematch/api/v1/year_in_review.py`, `src/cinematch/schemas/year_in_review.py`
- Migration: add `runtime` column to `movies` model
- Pipeline: extract `runtime` from `TMDB_all_movies.csv` in `cleaner.py`
- Frontend: new page + route

**Effort:** Medium

---

## 2. Mood-Based Discovery

**Inspired by:** Netflix mood rows, Taste.io, vibe-based apps

**What it is:** Let users pick a mood or vibe and get recommendations tailored to that feeling, not just genre. "I want something tense and unpredictable" returns different results than filtering by "Thriller."

**How it works (leveraging existing infrastructure):**

The app already has semantic vibe search via sentence-transformers embeddings + FAISS. This feature wraps that capability in a more intuitive UX.

**Option A — Mood Presets (lowest effort):**
- Add curated mood buttons to the home page: "Feel-Good", "Mind-Bending", "Dark & Gritty", "Lighthearted", "Epic Adventure", "Cozy Night In", "Edge of Your Seat"
- Each mood maps to a predefined search phrase passed to the existing `POST /api/v1/movies/semantic-search` endpoint
- Example mapping: `"Feel-Good" → "heartwarming uplifting comedy with a happy ending"`
- Zero backend changes — purely a frontend enhancement with a static mood-to-query mapping

**Option B — Mood Blending with User Taste (medium effort):**
- New endpoint: `POST /api/v1/recommendations/mood`
- Accept a mood string (free text or enum) + `user_id`
- Compute a mood embedding via `EmbeddingService.embed_text(mood_string)`
- Compute a user taste vector as the weighted average of their top-rated movies' embeddings (weight = rating)
- Blend: `query_vec = alpha * user_taste_vec + (1 - alpha) * mood_vec`
- Search FAISS with the blended vector — results are personalized to the user's taste AND the requested mood
- The FAISS `IndexFlatIP` already supports arbitrary query vectors, so no index changes needed

**Frontend implementation:**
- Mood pill buttons on the Home page hero section (Option A)
- A dedicated "Mood Discovery" section with a text input for custom vibes + preset buttons
- Results displayed as a horizontal carousel row titled "For your [mood] mood"

**Files affected:**
- Option A: frontend only (`Home.tsx`)
- Option B: new endpoint in `api/v1/recommendations.py`, new method in `HybridRecommender` or a standalone mood service
- Both: new frontend component for mood selector

**Effort:** Low (Option A) / Medium (Option B)

---

## 3. Smart Recommendation Explanations

**Inspired by:** Netflix "Because you watched X", Spotify "Made for you" playlists

**What it is:** Every recommendation card shows a human-readable reason why it was suggested. Instead of a generic list, users see context like "Because you rated Inception 9/10" or "You love Christopher Nolan's films."

**Three levels of explanation (all achievable without new ML):**

**Level 1 — "Because You Liked X" (influence trail):**
- In `HybridRecommender._hybrid_recommend()`, the content scoring loop already iterates over the user's rated movies and accumulates similarity scores. Track which seed movie contributed the highest similarity to each candidate.
- Return as `because_you_liked: {movie_id, title, your_rating}` in the response.
- One-line change to the existing accumulation loop + a new field in `RecommendationResponse` schema.

**Level 2 — Feature-Based Explanations:**
- After generating the ranked list, compare each result's `genres`, `director`, and `cast_names` against the user's top-rated movies.
- Generate template strings server-side:
  - "Same director as [Movie] — Christopher Nolan"
  - "Matches your love of Sci-Fi and Thriller"
  - "Stars Tom Hanks, who appears in 4 movies you rated 8+"
- Data is already in `movies.director`, `movies.cast_names`, `movies.genres` (all JSONB). User stats for top directors/actors are already computed in `UserStatsService`.

**Level 3 — Score Decomposition:**
- Expose the content score, collab score, and final alpha in the API response as `score_breakdown: {content: float, collab: float, alpha: float}`
- These values are already computed internally in `_hybrid_recommend()` — just return them
- Frontend can show a small bar: "78% taste match, 22% trending with similar users"

**Frontend implementation:**
- Each `MovieCard` in the recommendations list shows a small explanation tag below the title
- Clicking the tag expands to show the full breakdown (score decomposition, seed movie link)
- The existing "Why This?" LLM modal stays as the deep-dive option

**Files affected:**
- `src/cinematch/services/hybrid_recommender.py` — track seed influence + return scores
- `src/cinematch/schemas/recommendation.py` — add explanation fields
- Frontend: update recommendation card component

**Effort:** Low (Level 1) / Low-Medium (Level 2+3)

---

## 4. User Lists & Film Diary

**Inspired by:** Letterboxd lists, IMDb watchlists, Trakt collections

**What it is:** Let users create named, ordered movie lists beyond the single watchlist. Plus a chronological film diary showing every movie they've rated, displayed as a calendar/timeline.

### 4a. Custom Lists

- Users can create lists like "My Top 10 Sci-Fi", "Best of 2024", "Movies to Watch with Friends"
- Lists are ordered (drag-to-reorder), public or private, with optional descriptions
- A "Popular Lists" section on the home page surfaces community-created lists as a discovery mechanism

**Backend implementation:**
- New models: `UserList` (id, user_id, name, description, is_public, created_at) and `UserListItem` (id, list_id, movie_id, position)
- New endpoints: full CRUD for lists + items (`/api/v1/lists/`)
- New service: `ListService` with create/update/delete/reorder/get operations
- Index: compound index on `(list_id, position)` for ordered retrieval

**Frontend implementation:**
- New page: `/lists` — shows user's lists + a "Create List" button
- New page: `/lists/:id` — shows list contents with reorder drag handles
- "Add to List" button on every MovieCard (dropdown to select which list)
- Public lists browsable at `/lists/popular`

### 4b. Film Diary

- The `ratings` table already has `timestamp` (when the rating was created). Expose this as a visual diary.
- Calendar heatmap view (like GitHub contribution graph) showing rating activity per day
- Clicking a day shows the movies rated that day with their ratings

**Backend implementation:**
- New endpoint: `GET /api/v1/users/{user_id}/diary?year=2025` — returns ratings grouped by date
- Reuses existing `RatingService` with a date-grouped query

**Frontend implementation:**
- Calendar heatmap component on the Profile page (Recharts or a lightweight heatmap library)
- Click-to-expand day view

**Files affected:**
- New models + migration for lists
- New service, API routes, schemas for lists
- New diary endpoint in users API
- Frontend: 2 new pages + calendar component

**Effort:** Medium (lists) / Low (diary)

---

## 5. Trending & Community Discovery

**Inspired by:** IMDb "Most Popular", Letterboxd "Popular This Week", Netflix trending rows

**What it is:** Surface what's popular across the community right now. Solves the cold-start problem for new users who have no ratings yet — they always have something to browse.

### 5a. Trending This Week

- Count ratings created in the last 7 days, grouped by movie, ranked by frequency
- One SQL query: `SELECT movie_id, COUNT(*) as cnt FROM ratings WHERE timestamp > NOW() - INTERVAL '7 days' GROUP BY movie_id ORDER BY cnt DESC LIMIT 20`
- Cache in Redis with a 1-hour TTL

**Backend implementation:**
- New endpoint: `GET /api/v1/movies/trending?window=7` (window in days, default 7)
- Add method to `MovieService`

### 5b. Hidden Gems

- Movies with high average ratings but low total vote count — quality films that most users haven't discovered yet
- Query: high `vote_average` (>7.5) + low `vote_count` (<100) + at least 10 ratings in the system
- Surfaces diverse, non-obvious recommendations that complement the ML-driven suggestions

### 5c. Top Charts by Genre

- Pre-computed "Top 10 Thrillers", "Top 10 Comedies", etc.
- Ranked by average user rating within the system (not TMDb vote_average)
- Cached in Redis with a 6-hour TTL
- Displayed as browsable tabs on a new "Charts" section of the home page

### 5d. Personalized Home Feed

- Currently the home page shows the same "Popular Now" and "Top Rated" carousels for everyone
- Replace with named recommendation rows:
  - "Because you rated [Movie X] highly" — content-based from top-rated movie
  - "Trending with users like you" — collab-filtered trending
  - "Hidden gems in [your top genre]" — filtered hidden gems
  - "Something different" — one serendipity pick from outside the user's usual genres
- Each row calls the existing recommendation/search endpoints with different parameters

**Files affected:**
- `src/cinematch/services/movie_service.py` — new trending/hidden gems methods
- `src/cinematch/api/v1/movies.py` — new endpoints
- Frontend: new carousel rows on Home page with dynamic titles

**Effort:** Low (5a, 5b, 5c) / Medium (5d)

---

## 6. Taste Comparison & Social Features

**Inspired by:** Letterboxd "Films in Common", Spotify Blend, compatibility scores

### 6a. Taste Compatibility Score

- Compare two users' movie taste using their ALS latent factor vectors (already loaded at startup)
- Compute cosine similarity between user factor vectors → output a percentage: "You and User #42 are a 78% taste match"
- Show which genres they agree/disagree on most
- Show movies they've both rated and how their ratings compare

**Backend implementation:**
- New endpoint: `GET /api/v1/users/{user_id}/compatibility/{other_user_id}`
- Accesses `app.state.collab_recommender._model.user_factors` for the factor vectors
- Computes genre overlap from both users' rating histories

### 6b. "Users Who Liked This Also Liked"

- On the Movie Detail page, show movies that are highly co-rated by users who rated the current movie highly (>= 8)
- Query: find users who rated movie X >= 8, then find their other highest-rated movies, ranked by frequency
- This is a simple SQL query, no ML needed — it's behavioral co-occurrence
- Complements the existing "Similar Movies" section (which uses embedding similarity) with a collaborative signal

### 6c. Director & Actor Filmography Pages

- Clicking a director or actor name (on MovieDetail or Profile stats) opens a filmography view
- Shows all their movies in the database, sorted by release date
- Marks which ones the user has rated and their ratings
- Shows the user's average rating for that person's films

**Backend implementation:**
- New endpoint: `GET /api/v1/movies/by-creator?name=Christopher+Nolan&role=director`
- Uses existing `movies.director` and `movies.cast_names` JSONB columns with GIN index queries

**Frontend implementation:**
- Make director/actor names clickable links throughout the app
- New filmography page or modal with a filtered movie grid

**Files affected:**
- New endpoints in movies API
- New compatibility endpoint in users API
- Frontend: filmography page, compatibility page/modal, clickable creator names

**Effort:** Low (6b, 6c) / Medium (6a)

---

## Implementation Priority

Recommended order based on impact-to-effort ratio:

| # | Feature | Effort | Why Prioritize |
|---|---------|--------|---------------|
| 1 | Mood Presets (2, Option A) | Low | Zero backend work, instantly makes the app feel more interactive |
| 2 | Trending This Week (5a) | Low | One SQL query + Redis cache, solves cold-start UX |
| 3 | Explanation Tags (3, Level 1) | Low | One-line backend change, makes recommendations feel intelligent |
| 4 | Director/Actor Filmography (6c) | Low | Makes existing data clickable and explorable |
| 5 | Film Diary (4b) | Low | Existing data, just needs a calendar view |
| 6 | Hidden Gems + Genre Charts (5b, 5c) | Low | Simple queries, high discovery value |
| 7 | "Users Who Liked Also Liked" (6b) | Low | Pure SQL, adds collaborative discovery to movie pages |
| 8 | Full Explanation System (3, all levels) | Medium | Differentiator for the app — shows ML depth |
| 9 | Mood Blending (2, Option B) | Medium | Personalized mood discovery is a standout feature |
| 10 | CineMatch Wrapped (1) | Medium | High shareability, but more files to create |
| 11 | Custom Lists (4a) | Medium | New models + migration, but essential for engagement |
| 12 | Personalized Home Feed (5d) | Medium | Transforms the home page from static to dynamic |
| 13 | Taste Compatibility (6a) | Medium | Social hook, but needs a way for users to find each other |
