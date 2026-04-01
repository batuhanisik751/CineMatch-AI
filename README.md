# CineMatch-AI

Hybrid movie recommendation system combining content-based filtering (embeddings) and collaborative filtering (user ratings). Built with FastAPI, PostgreSQL + pgvector, and local ML models. Runs fully locally with no paid APIs.

## Tech Stack

- **Backend:** FastAPI (Python 3.11+)
- **Database:** PostgreSQL 16 + pgvector
- **Vector Search:** pgvector (primary) + FAISS (batch operations)
- **Embeddings:** sentence-transformers/all-MiniLM-L6-v2 (384-dim, local)
- **Collaborative Filtering:** implicit ALS (matrix factorization)
- **Caching:** Redis
- **LLM:** Mistral 7B via Ollama (recommendation re-ranking + explanations)

## Data Sources

- [MovieLens ml-25m](https://grouplens.org/datasets/movielens/25m/) — 25M user ratings from 162K users on 62K movies
- [TMDb metadata (Kaggle)](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset) — movie overviews, genres, keywords, cast, crew

After processing: ~29K movies, ~162K users, ~24.7M ratings with 384-dim embeddings.

## Running the App (3 Terminals)

Open 3 terminal windows and keep them all running:

**Terminal 1 — Backend**
```bash
source .venv/bin/activate
PYTHONPATH=src uvicorn cinematch.main:app --reload --reload-dir src --host 0.0.0.0 --port 8000
```

**Terminal 2 — Frontend**
```bash
cd frontend
npm run dev
```
Opens at http://localhost:3000

**Terminal 3 — Ollama (LLM, optional)**
```bash
ollama serve
```
Required for "Why This?" explanations and LLM re-ranking. Skip this if you don't need those features — recommendations still work without it.

Docker runs in the background (`docker compose up -d`) and does not need its own terminal.

---

## Quick Start

```bash
# 1. Start infrastructure
docker compose up -d

# 2. Install Ollama + Mistral (required for LLM re-ranking)
brew install ollama
ollama serve          # keep running in a separate terminal
ollama pull mistral

# 3. Install dependencies
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pip install psycopg2-binary   # needed for seed script

# 4. Configure environment
cp .env.example .env
# Add your KAGGLE_API_TOKEN to .env if using Kaggle CLI

# 5. Run database migrations
alembic upgrade head

# 6. Download datasets
python scripts/download_data.py
# For TMDb: either use Kaggle CLI or download manually from Kaggle
# pip install kaggle && kaggle datasets download -d rounakbanik/the-movies-dataset -p data/raw/tmdb/ --unzip

# 7. Run data pipeline (clean, embed, build FAISS, train ALS — ~10 min)
PYTHONPATH=src python scripts/train_models.py

# 8. Seed database (~15 min for 24.7M ratings)
PYTHONPATH=src python scripts/seed_db.py

# 9. Start the API server
uvicorn cinematch.main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at http://localhost:8000/docs

### Frontend (separate terminal)

```bash
cd frontend
npm install
npm run dev
```

Opens at http://localhost:3000 — connects to the backend API automatically.

Features: movie discovery with genre/year/sort filters, title search with typo tolerance, semantic "vibe" search by description, mood-based discovery (9 preset moods + custom vibe input, personalized by blending mood with user taste, dedicated Moods page with multi-select carousels), hybrid/content/collab recommendations with smart explanation tags ("Because you liked Inception", "Same director as Interstellar — Christopher Nolan", content vs. collab score breakdown bar), "Why This?" deep-dive explanation button (powered by Mistral), **Top Charts** (genre-tab selector showing the highest community-rated movies per genre, ranked by in-system average with numbered badges), **Decade Explorer** (browse film history by era — clickable decade grid with movie counts and avg ratings, drill into any decade for top-rated movies with genre filtering and ranked badges), **Director Spotlight** (search or browse popular directors, view full filmography sorted chronologically with your personal ratings overlaid, director stats including total films, average rating, genres, and your average score), **Actor Filmography** (search or browse popular actors, view their complete filmography with your personal ratings overlaid — same two-level drill-down pattern, backed by GIN-indexed JSONB containment queries on cast_names), rating history with movie names, watchlist/save-for-later with bookmark buttons across all pages, profile analytics dashboard with rating histogram, **Genre Affinity Radar Chart** (spider chart of top 8 genres by percentage, powered by Recharts RadarChart), top directors/actors, and monthly activity timeline, **Surprise Me** (serendipity mode — one-click random recommendations from genres outside the user's typical taste profile, with shuffle-again capability), **Keyword Explorer** (interactive tag cloud of crowd-sourced keyword tags like "time travel", "heist", "dystopia" — click any tag to browse matching movies sorted by popularity, with stats showing total movies, average rating, and top genres; includes keyword search with debounced filtering), **Advanced Search** (multi-criteria discovery combining genre, decade, rating range, director, keyword, and cast filters in a single query — all filters are URL-driven for bookmarkable queries, with debounced text inputs, removable active filter chips, and pagination), **Complete the Collection** (identifies directors and actors where you've rated 3+ films, shows unrated movies by those creators with completion progress bars — drives completionism for invested fans), **Personalized Home Feed** (replaces static home carousels with dynamically named sections tailored to user taste — "Because you rated X highly", "Trending with users like you", "Hidden gems in {genre}", "Something different", "New to you in the {decade}s" — cold-start users see generic trending/top-rated/hidden-gems sections), **More Like This** (pick any movie as a seed and get personalized recommendations branching from it — blends content similarity with collaborative filtering, filters already-rated movies, applies franchise penalty and MMR diversity reranking, with full score breakdowns and feature explanations), **Recommendation Diversity Controls** (user-facing toggle to adjust how adventurous vs. safe recommendations are — Safe/Balanced/Adventurous maps to MMR lambda values 0.9/0.7/0.4, controlling the relevance-diversity tradeoff in re-ranking), **"Not Interested" / Negative Feedback** (dismiss movies you don't want to see — dismissed movies are filtered from all recommendation, feed, and mood-based results; "Not Interested" button appears on every movie card across all pages; Profile page shows a collapsible list of dismissed movies with undo capability; cache is invalidated on dismiss/undismiss), **Watch History Awareness** (movies you've already rated show a "Rated X/10" badge across all discovery and recommendation pages; all discovery endpoints — trending, hidden gems, top charts, search, discover — accept optional `user_id` + `exclude_rated=true` params to server-side filter already-seen movies from results while preserving the global Redis cache), **Film Diary** (GitHub-style calendar heatmap at `/diary` showing daily rating activity for the year — color-coded cells from 0 to 4+ ratings per day, year navigation, click any day to expand and see which movies were rated with their scores; backed by `GET /api/v1/users/{id}/diary?year=` endpoint with daily GROUP BY aggregation and Redis caching), **You vs. Community** (rating comparison section on the Profile page showing how your ratings stack up against community averages — displays your avg vs community avg, agreement percentage, top 5 most overrated movies where you scored higher than the crowd, and top 5 most underrated movies where you scored lower; backed by `GET /api/v1/users/{id}/rating-comparison` endpoint with Redis caching), **Rating Streaks & Milestones** (gamification section on the Profile page tracking consecutive-day rating streaks with fire/trophy icons and milestone badges at 10/25/50/100/250/500/1000 ratings — reached milestones glow gold, unreached stay muted; includes yesterday grace period so streaks don't break before the day is over), **Taste Evolution Timeline** (dedicated `/taste-evolution` page showing how your genre preferences have shifted over time — stacked area chart of genre distribution per period with month/quarter/year granularity toggle, backed by `GET /api/v1/users/{id}/taste-evolution?granularity=quarter` endpoint that joins ratings with movies, unnests JSONB genres, and computes percentage distribution per time period; linked from Profile page and sidebar), **Platform Stats** (dedicated `/platform-stats` dashboard showing platform-wide statistics — total movies, total users, total ratings, average rating, ratings this week, most rated movie, highest rated movie with minimum 50-rating threshold, and most active user; backed by `GET /api/v1/stats/global` with 1-hour Redis caching), **Custom User Lists** (named, ordered movie collections — full CRUD with public/private toggle, add-to-list from any MovieCard, browse popular public lists at `/lists/popular`; backed by `user_lists` and `user_list_items` tables with cascade deletes and position-based ordering), **Movie Rating Comparison** (per-movie community rating histogram on the Movie Detail page — shows avg rating, median, total ratings, and a Recharts bar chart of the 1-10 rating distribution with the user's own rating bar highlighted in gold; answers "am I the outlier here?"; backed by `GET /api/v1/movies/{id}/rating-stats?user_id=` with 1-hour Redis caching for movie-level stats and separate uncached user rating lookup; auto-refreshes after rating submission), **Watchlist Recommendations** ("If these are on your list, you'll also want these" — computes the mean embedding of all watchlist movies, runs FAISS nearest-neighbor search, filters out rated/dismissed/watchlisted movies, returns recommendations with "Based on your watchlist" explanations; dedicated `/watchlist/recommendations` page with "Why This?" LLM explanations; cache invalidated on watchlist add/remove, ratings, and dismissals).

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1/movies/{id}` | Movie details |
| GET | `/api/v1/movies/search?q=&limit=20&user_id=&exclude_rated=false` | Search movies by title (fuzzy/typo-tolerant); pass `user_id` + `exclude_rated=true` to hide already-rated movies |
| GET | `/api/v1/movies/semantic-search?q=&limit=20` | Semantic "vibe" search by description (e.g., "dark thriller in space") |
| GET | `/api/v1/movies/discover?genre=&sort_by=popularity&year_min=&year_max=&offset=0&limit=20&user_id=&exclude_rated=false` | Browse movies with filters and pagination; pass `user_id` + `exclude_rated=true` to hide already-rated movies |
| GET | `/api/v1/movies/genres` | All genres with movie counts |
| GET | `/api/v1/movies/trending?limit=20&user_id=&exclude_rated=false` | Trending movies; pass `user_id` + `exclude_rated=true` to hide already-rated movies |
| GET | `/api/v1/movies/hidden-gems?limit=20&user_id=&exclude_rated=false` | Hidden gems; pass `user_id` + `exclude_rated=true` to hide already-rated movies |
| GET | `/api/v1/movies/top?genre=Drama&limit=20&user_id=&exclude_rated=false` | Top-rated movies for a genre, ranked by community avg rating (min 50 ratings); pass `user_id` + `exclude_rated=true` to hide already-rated movies |
| GET | `/api/v1/movies/decades` | Available decades with movie counts and avg ratings |
| GET | `/api/v1/movies/decades/{decade}?genre=&offset=0&limit=20` | Top-rated movies for a decade (e.g., `/decades/1990`) |
| GET | `/api/v1/movies/directors/search?q=nolan&limit=20` | Search directors by name |
| GET | `/api/v1/movies/directors/popular?limit=30` | Popular directors (3+ films, sorted by popularity) |
| GET | `/api/v1/movies/directors/filmography?name=Christopher+Nolan&user_id=1` | Director filmography with user rating overlay |
| GET | `/api/v1/movies/actors/search?q=hanks&limit=20` | Search actors by name |
| GET | `/api/v1/movies/actors/popular?limit=30` | Popular actors (3+ films, sorted by popularity) |
| GET | `/api/v1/movies/actors/filmography?name=Tom+Hanks&user_id=1` | Actor filmography with user rating overlay |
| GET | `/api/v1/movies/keywords/popular?limit=50` | Popular keyword tags with movie counts |
| GET | `/api/v1/movies/keywords/search?q=time&limit=20` | Search keywords by partial match |
| GET | `/api/v1/movies/keywords/movies?keyword=time+travel&offset=0&limit=20` | Movies by keyword with stats (total, avg rating, top genres) |
| GET | `/api/v1/movies/advanced-search?genre=Sci-Fi&decade=2010s&min_rating=7&director=Villeneuve&keyword=dystopia&cast=Gosling&sort_by=popularity&offset=0&limit=20` | Multi-criteria discovery combining genre, decade, rating range, director, keyword, and cast filters |
| GET | `/api/v1/movies/thematic-collections?collection_type=genre_decade` | Browse auto-generated thematic collections (types: `genre_decade`, `director`, `year`; omit param for all) |
| GET | `/api/v1/movies/thematic-collections/{collection_id}?limit=20` | Ranked movies within a specific collection (e.g., `genre_decade:Sci-Fi:2010`, `director:Christopher Nolan`, `year:2023`) |
| GET | `/api/v1/movies/{id}/similar?top_k=20` | Content-similar movies |
| GET | `/api/v1/movies/{id}/rating-stats?user_id=42` | Per-movie rating distribution (avg, median, histogram 1-10, user's rating highlighted) |
| GET | `/api/v1/users/{id}` | User details |
| GET | `/api/v1/users/{id}/stats` | User profile analytics (rating histogram, top directors/actors, timeline) |
| GET | `/api/v1/users/{id}/affinities?limit=15` | Director & actor affinity rankings weighted by enthusiasm (avg_rating × log(count+1)), with rated films list |
| GET | `/api/v1/users/{id}/surprise?limit=5` | Serendipity mode — random well-rated movies outside user's top genres |
| GET | `/api/v1/users/{id}/completions?limit=10` | "Complete the Collection" — unrated films by directors/actors the user has rated 3+ films for |
| GET | `/api/v1/users/{id}/feed?sections=5` | Personalized home feed — dynamic named sections tailored to user taste (cold-start users get generic sections) |
| GET | `/api/v1/users/{id}/taste-profile` | Natural-language taste profile — template-based insights (top genre, critic style, director affinity, decade preference) with optional LLM-enhanced summary |
| GET | `/api/v1/users/{id}/affinities?limit=15` | Director & actor affinity rankings — weighted score (avg_rating × log(count+1)), with rated films per person |
| GET | `/api/v1/users/{id}/rating-comparison` | You vs. community — user avg, community avg, agreement %, most overrated and most underrated movies |
| GET | `/api/v1/users/{id}/streaks` | Rating streaks & milestones — current streak, longest streak, total ratings, milestone badges (10/25/50/100/250/500/1000) |
| GET | `/api/v1/users/{id}/achievements` | Achievement badges — 12 badges computed on-the-fly from rating history (milestones, genre exploration, streaks, timestamps, director completionism) |
| GET | `/api/v1/challenges/current` | This week's active challenges — 3 deterministic challenges (genre, decade, director) rotated weekly via date hash, no manual curation |
| GET | `/api/v1/users/{id}/challenges/progress` | User's progress on the current week's challenges — qualifying ratings counted per challenge with completion status |
| GET | `/api/v1/users/{id}/bingo?seed=YYYY-MM` | Monthly Movie Bingo card — 5x5 grid of movie categories (genre, decade, director, keyword, rating filters), cells marked from all-time ratings, detects completed rows/cols/diagonals |
| GET | `/api/v1/users/{id}/recommendations?top_k=20&strategy=hybrid&diversity=medium` | Recommendations with smart explanations (strategy: `hybrid`/`content`/`collab`, diversity: `low`/`medium`/`high`) |
| GET | `/api/v1/users/{id}/recommendations/from-seed/{movie_id}?limit=20` | "More Like This" — personalized recommendations branching from a seed movie |
| POST | `/api/v1/recommendations/mood` | Mood-based discovery (body: `{"mood": "dark gritty thriller", "user_id": 1, "alpha": 0.3, "limit": 20}`) |
| GET | `/api/v1/users/{id}/recommendations/explain/{movie_id}?score=0.9` | LLM explanation for a recommendation |
| POST | `/api/v1/users/{id}/ratings` | Add/update a rating (body: `{"movie_id": 1, "rating": 4.5}`) |
| GET | `/api/v1/users/{id}/ratings?offset=0&limit=20` | User's ratings (paginated) |
| GET | `/api/v1/users/{id}/ratings/check?movie_ids=1,2,3` | Bulk check which movies the user has rated (returns `{movie_id: rating}` map) |
| POST | `/api/v1/users/{id}/watchlist` | Add to watchlist (body: `{"movie_id": 1}`) |
| DELETE | `/api/v1/users/{id}/watchlist/{movie_id}` | Remove from watchlist |
| GET | `/api/v1/users/{id}/watchlist?offset=0&limit=20` | User's watchlist (paginated, with movie details) |
| GET | `/api/v1/users/{id}/watchlist/recommendations?limit=10` | Recommend movies similar to the user's watchlist (mean embedding + FAISS search) |
| GET | `/api/v1/users/{id}/watchlist/check?movie_ids=1,2,3` | Bulk check which movies are in watchlist |
| POST | `/api/v1/users/{id}/dismissals` | Dismiss a movie — "Not Interested" (body: `{"movie_id": 1}`) |
| DELETE | `/api/v1/users/{id}/dismissals/{movie_id}` | Undo a dismissal |
| GET | `/api/v1/users/{id}/dismissals?offset=0&limit=20` | User's dismissed movies (paginated, with movie details) |
| GET | `/api/v1/users/{id}/dismissals/check?movie_ids=1,2,3` | Bulk check which movies are dismissed |
| POST | `/api/v1/users/{id}/lists` | Create a new user list (body: `{"name": "...", "description": "...", "is_public": false}`) |
| GET | `/api/v1/users/{id}/lists` | Get all lists for a user |
| GET | `/api/v1/lists/{id}?offset=0&limit=20` | Get a single list with paginated items and movie details |
| PATCH | `/api/v1/users/{id}/lists/{list_id}` | Update list metadata (name, description, is_public) |
| DELETE | `/api/v1/users/{id}/lists/{list_id}` | Delete a list and all its items |
| POST | `/api/v1/users/{id}/lists/{list_id}/items` | Add a movie to a list (body: `{"movie_id": 1}`) |
| DELETE | `/api/v1/users/{id}/lists/{list_id}/items/{movie_id}` | Remove a movie from a list |
| PUT | `/api/v1/users/{id}/lists/{list_id}/items/reorder` | Reorder list items (body: `{"movie_ids": [3,1,2]}`) |
| GET | `/api/v1/lists/popular?offset=0&limit=20` | Browse popular public lists sorted by item count |
| GET | `/api/v1/stats/global` | Platform-wide statistics (total movies/users/ratings, avg rating, most rated movie, highest rated movie, most active user, ratings this week) |

## LLM Integration (Mistral via Ollama)

Mistral 7B is used for two features:

- **Recommendation re-ranking:** After hybrid scoring produces candidates, Mistral re-ranks them for thematic diversity and deeper taste matching. Falls back to algorithmic MMR re-ranking if Ollama is unavailable.
- **Explanations:** The `/explain` endpoint generates natural language explanations for why a movie was recommended.

```bash
# Install and start Ollama (required)
brew install ollama
ollama serve
ollama pull mistral
```

If Ollama is not running, the app still works — recommendations use the algorithmic MMR diversity fallback instead of LLM re-ranking.

## How It Works

1. **Content-Based:** Movie overviews, genres, and keywords are encoded into 384-dim vectors using all-MiniLM-L6-v2. Similar movies are found via cosine similarity (pgvector with FAISS fallback).
2. **Collaborative:** User-item rating matrix is factorized using ALS. Users with similar taste patterns get similar recommendations.
3. **Hybrid Scoring:** Both scores are min-max normalized to [0,1] and combined: `hybrid = alpha * content + (1 - alpha) * collab` (default alpha=0.5). Cold-start users (not in ALS training data) automatically fall back to content-only (alpha=1.0).
4. **Franchise Penalty:** Sequels and franchise entries (e.g., "Cars 2", "Star Wars: Episode V") are detected and penalized to avoid clustering on one series.
5. **Diverse Seed Selection:** User's top-rated movies are picked to span different genres, not just the N highest ratings.
6. **LLM Re-ranking:** Top 50 candidates are sent to Mistral, which re-ranks for thematic variety, sequel avoidance, and deeper taste matching. Returns the best 20.
7. **MMR Fallback:** If the LLM is unavailable, Maximal Marginal Relevance (MMR) with genre Jaccard similarity ensures diversity algorithmically. Users can tune the diversity level via a `diversity` parameter (`low`=safe/relevance-heavy, `medium`=balanced, `high`=adventurous/diversity-heavy).
8. **Smart Explanations:** Every recommendation includes lightweight, always-available explanation metadata — no LLM required. Three levels: (a) seed influence tracking ("Because you liked Inception"), (b) feature-based templates comparing genres, directors, and cast against the user's top-rated movies, and (c) score decomposition showing the content vs. collaborative contribution breakdown.
9. **Fuzzy Search:** Movie search uses ILIKE for exact matches, with automatic pg_trgm fuzzy fallback for typos (e.g., "Casr" finds "Cars").
10. **Semantic "Vibe" Search:** Users can search by mood or description (e.g., "funny movie about time travel"). The query text is embedded using the same sentence-transformer model and matched against movie embeddings via pgvector cosine similarity. No LLM needed — pure vector search.
11. **Mood-Based Discovery:** Users pick a mood preset (e.g., "Feel-Good", "Mind-Bending", "Edge of Your Seat", "Tearjerker", "Nostalgic") or type a custom vibe. The mood text is embedded, then blended with the user's taste vector (weighted average of their top-rated movies' embeddings): `query = alpha * taste + (1-alpha) * mood`. The blended vector is L2-normalized and searched via FAISS. Cold-start users get pure mood results. Alpha defaults to 0.3 (mood-weighted with light personalization). A dedicated **Moods page** (`/moods`) lets users select multiple moods simultaneously, displaying themed carousel rows for each — plus custom vibe input with dismiss controls per carousel.
12. **Serendipity / Surprise Me:** Computes the user's top 2 genres from their rating history, then randomly selects well-rated movies (vote_average > 7) from genres outside that comfort zone, excluding already-rated movies. Cold-start users with no ratings get any well-rated movie as a surprise.
13. **Complete the Collection:** Finds directors and actors where the user has rated 3+ films, queries for their unrated movies, and groups them by creator — sorted by the user's average rating per creator so the most-loved creators appear first.
14. **"More Like This" from Seed:** Users pick any movie as a seed. The system finds the top 100 content-similar movies, scores them with ALS collab data (if the user has ratings), blends via `alpha * content + (1-alpha) * collab`, filters out already-rated movies and the seed itself, applies franchise/sequel penalty, and diversifies with MMR. Cold-start users get pure content-based results. Every result includes "Because you liked {seed}" influence tracking and feature explanations.
15. **Strategies:** The API supports three modes — `hybrid` (default), `content` (content-only), and `collab` (collaborative-only). Cold-start users (not in ALS training data) get a 400 error on `collab` with guidance to use `hybrid` or `content` instead. The `hybrid` strategy handles cold-start automatically by falling back to content-only.
16. **"Not Interested" Dismissals:** Users can dismiss movies from any page via the `visibility_off` button on movie cards. Dismissed movies are stored in a `dismissals` table and filtered from all recommendation paths — hybrid, content-only, from-seed, mood-based, and home feed sections. Cache is invalidated on dismiss/undismiss. The Profile page shows a collapsible "Not Interested" section with undo capability.
17. **Diversity Controls:** Users can adjust the diversity-relevance tradeoff via a `diversity` query parameter: `low` (lambda=0.9, safe/similar picks), `medium` (lambda=0.7, balanced default), or `high` (lambda=0.4, adventurous/genre-spanning). Applies to `hybrid` and `content` strategies which use MMR re-ranking; `collab` strategy returns raw ALS scores without re-ranking.
18. **Taste Profile Summary:** Generates a natural-language personality snapshot of the user's taste from their rating history — "You're a Thriller enthusiast (35% of your ratings)", "You're a generous critic (avg 7.2 vs site avg 6.5)", "You have a special appreciation for Nolan's work", "Your sweet spot is 2000s cinema". Backed by four template-driven insights (top genre, critic style, director affinity, decade preference) computed from the same stats used by the analytics dashboard. If Ollama is running, the service optionally asks Mistral to synthesize a 2-3 sentence cohesive personality summary. Cached per-user (10 min) and invalidated on new ratings. Displayed as a card on the Profile page above the analytics charts.
19. **Rating Streaks & Milestones:** Tracks consecutive-day rating streaks and celebrates milestone badges. The Profile page shows a "Current Streak" counter (with fire icon) and "Longest Streak" record (with trophy icon), plus a row of milestone badges (10, 25, 50, 100, 250, 500, 1000 ratings) — reached milestones glow in gold, unreached ones stay muted. Streaks include a "yesterday grace" so users don't lose their streak before the day is over. Backed by `GET /api/v1/users/{id}/streaks` with window-function SQL for consecutive-date grouping and Redis caching (5 min TTL).
20. **Movie Rating Comparison:** On each movie's detail page, a "Community Ratings" card shows the full rating distribution (1-10 histogram), average, median, and total ratings. When a user is logged in, their own rating bar is highlighted in gold so they can instantly see whether they're an outlier. Movie-level stats are cached for 1 hour; the user's individual rating is fetched separately (uncached) so the cache is not per-user. The histogram auto-refreshes after the user submits a new rating.
21. **Custom User Lists:** Named, ordered movie collections that users can create, edit, and share. Full CRUD for lists and items — create public or private lists, add/remove movies, reorder with up/down controls, search and add movies from within a list. "Add to List" button on every MovieCard across all pages via a reusable modal. Browse popular public lists at `/lists/popular`. Backed by `user_lists` and `user_list_items` tables with cascade deletes and compound indexes.
22. **Watchlist Recommendations:** "If these are on your list, you'll also want these" — computes the mean embedding of all watchlist movies, runs FAISS nearest-neighbor search with the mean vector, filters out already-rated, dismissed, and watchlisted movies, and returns recommendations with "Based on your watchlist" explanations. Dedicated `/watchlist/recommendations` page accessible via a button on the Watchlist page. Cache is invalidated on watchlist add/remove, new ratings, and dismissals.
24. **Curated Thematic Collections:** Auto-generated browsable collections like "Best Sci-Fi of the 2010s", "Christopher Nolan: A Filmography", and "Highest Rated 2023". Three collection types — genre+decade combos, director filmographies, and per-year rankings — computed on-demand from existing movie and rating data with 6-hour Redis caching. A dedicated `/curated` page presents a two-level drill-down: browse a grid of collection cards (with 2x2 poster previews, movie counts, and type filter tabs), then drill into any collection for ranked movies with numbered badges, avg ratings, and rating counts. No new database tables — pure SQL aggregation over existing `movies` and `ratings`.
25. **Achievement Badges:** 12 gamification badges computed on-the-fly from user rating history — First Rating, Century Club (100), Marathon Runner (500), Genre Explorer (10+ genres), Decade Hopper (5+ decades), Director Devotee (5+ films by one director), The Critic (avg < 5.0), Easy to Please (avg > 8.0), Weekend Warrior (5+ in one weekend), Night Owl (10+ midnight-5am ratings), Streak Master (7-day streak), and Completionist (all films by a director with 5+ in DB). Computed via 5 batched SQL queries, cached 1 hour in Redis, invalidated on new ratings. Dedicated `/achievements` page with progress bars for locked badges and a compact unlocked-badges section on the Profile page.
27. **Weekly Rating Challenges:** Three time-bound challenges rotate every Monday — one genre challenge ("Rate 5 Horror movies"), one decade challenge ("Explore the 1960s"), and one director challenge ("Director deep-dive: Kubrick") — all selected deterministically via a SHA-256 date hash so every user sees the same challenges each week with no manual curation. Progress is tracked by querying the user's ratings within the ISO week window against genre (JSONB containment), decade (EXTRACT), and director (exact match) criteria. Challenges and progress are cached in Redis (24h and 2min TTL respectively). Dedicated `/challenges` page with a 3-column card grid, color-coded progress bars (green for complete, amber for in-progress), and a completion counter in the header.
26. **Watch History Awareness:** Every MovieCard across all pages shows a "Rated X/10" badge (in tertiary-container colors, distinct from the match-percent badge) when the user has already rated that movie — powered by a shared `useRated` hook that batch-fetches ratings via `GET /users/{id}/ratings/check`. All five discovery endpoints (trending, hidden gems, top charts, search, discover) accept optional `user_id` + `exclude_rated=true` params; filtering is applied post-cache in Python so the global Redis cache is preserved and only per-user results are trimmed.

## Data Pipeline

```
MovieLens ml-25m ──┐
                   ├──► Clean & Join ──► Embeddings ──► Seed DB + FAISS + ALS
TMDb Metadata ─────┘
```

| Step | Script | Output |
|------|--------|--------|
| Download | `scripts/download_data.py` | `data/raw/ml-25m/`, `data/raw/tmdb/` |
| Clean & join | `pipeline/cleaner.py` | `movies_clean.parquet`, `ratings_clean.parquet` |
| Embed | `pipeline/embedder.py` | `embeddings.npy` (29K x 384) |
| FAISS index | `pipeline/faiss_builder.py` | `faiss.index`, `faiss_id_map.pkl` |
| Train ALS | `pipeline/collaborative.py` | `als_model.pkl`, mappings, sparse matrix |
| Seed DB | `scripts/seed_db.py` | PostgreSQL tables + IVFFlat vector index (re-run after pipeline) |
| Evaluate | `python -m cinematch.evaluation.evaluate` | `evaluation_report.json` |

## Caching

Redis caches API responses with automatic invalidation:

| Cache Key Pattern | TTL | Invalidation |
|---|---|---|
| `decades` | 6 hours | Manual |
| `decade_movies:{decade}:{genre}:{offset}:{limit}` | 6 hours | Manual |
| `popular_directors:{limit}` | 6 hours | Manual |
| `director_filmography:{name}` | 6 hours | Manual (not cached when user_id provided) |
| `popular_actors:{limit}` | 6 hours | Manual |
| `actor_filmography:{name}` | 6 hours | Manual (not cached when user_id provided) |
| `popular_keywords:{limit}` | 6 hours | Manual |
| `keyword_movies:{keyword}:{offset}:{limit}` | 6 hours | Manual |
| `adv_search:{filters}:{sort}:{offset}:{limit}` | 1 hour | Manual |
| `thematic_list:{type}` | 6 hours | Manual |
| `thematic_detail:{collection_id}:{limit}` | 6 hours | Manual |
| `top_charts:{genre}:{limit}` | 6 hours | Manual |
| `movie:{id}` | 1 hour | Manual |
| `similar:{id}:{top_k}` | 30 min | Never (content similarity is stable) |
| `movie_rating_stats:{id}` | 1 hour | Manual (user rating fetched separately, not cached) |
| `recs:{user_id}:{strategy}:{top_k}` | 15 min | On new rating or dismissal from this user |
| `from_seed:{user_id}:{movie_id}:{limit}` | 10 min | On new rating or dismissal from this user |
| `mood_rec:{user_id}:{mood_hash}:{alpha}:{limit}` | 10 min | On new rating or dismissal from this user |
| `feed:{user_id}:{sections}` | 10 min | On new rating or dismissal from this user |
| `taste_profile:{user_id}` | 10 min | On new rating or dismissal from this user |
| `watchlist_recs:{user_id}:{limit}` | 10 min | On watchlist add/remove, new rating, or dismissal |
| `streaks:{user_id}` | 5 min | On new rating from this user |
| `achievements:{user_id}` | 1 hour | On new rating from this user |
| `challenges:current:{week}` | 24 hours | Never (deterministic per week) |
| `challenges:progress:{user_id}` | 2 min | On new rating from this user |
| `global_stats` | 1 hour | Manual |
| `search:{query_hash}:{limit}` | 10 min | Never |

Redis is optional — the app runs without it, just without caching.

## Evaluation

Run `python -m cinematch.evaluation.evaluate` to measure recommendation quality. Uses temporal train/test split (80/20) and computes Precision@K, Recall@K, NDCG@K, and MAP@K for content and collaborative strategies. Results are saved to `data/processed/evaluation_report.json`.

## Project Structure

```
src/cinematch/
├── api/
│   ├── deps.py                   # Dependency injection (get_db, services)
│   └── v1/                       # REST endpoints
│       ├── movies.py             # GET /{id}, /search, /semantic-search, /discover, /genres, /decades, /directors, /actors, /keywords, /advanced-search, /thematic-collections, /{id}/similar, /{id}/rating-stats
│       ├── ratings.py            # POST/GET /users/{id}/ratings
│       ├── recommendations.py    # GET /users/{id}/recommendations, /from-seed/{movie_id}, POST /recommendations/mood
│       ├── users.py              # GET /users/{id}, /users/{id}/stats, /users/{id}/surprise, /users/{id}/completions, /users/{id}/feed, /users/{id}/taste-profile, /users/{id}/rating-comparison, /users/{id}/streaks, /users/{id}/taste-evolution, /users/{id}/affinities, /users/{id}/achievements, /users/{id}/challenges/progress
│       ├── challenges.py         # GET /challenges/current (weekly rotating challenges)
│       ├── watchlist.py          # POST/DELETE/GET /users/{id}/watchlist, GET /users/{id}/watchlist/recommendations
│       ├── dismissals.py         # POST/DELETE/GET /users/{id}/dismissals ("Not Interested")
│       ├── lists.py              # CRUD /users/{id}/lists, /lists/{id}, /lists/popular (custom movie collections)
│       ├── stats.py              # GET /stats/global (platform-wide statistics)
│       └── router.py             # Aggregated v1 router
├── services/        # Business logic
│   ├── embedding_service.py      # sentence-transformers wrapper
│   ├── content_recommender.py    # pgvector + FAISS similarity search
│   ├── collab_recommender.py     # ALS collaborative filtering
│   ├── hybrid_recommender.py     # Combined scoring + franchise penalty + MMR + LLM re-ranking
│   ├── movie_service.py          # Movie DB queries (get, search, discover, genres, batch)
│   ├── rating_service.py         # Rating DB queries (upsert, list with movie titles, bulk check, rated-ID set)
│   ├── feed_service.py           # Personalized home feed orchestrator (5 named sections)
│   ├── user_stats_service.py     # User profile analytics (genre, rating, director/actor stats)
│   ├── taste_profile_service.py  # Natural-language taste profile generation (template-based + optional LLM)
│   ├── streak_service.py         # Rating streaks & milestones (consecutive-day tracking)
│   ├── achievement_service.py    # Achievement badges (12 badges computed from rating history)
│   ├── challenge_service.py      # Weekly rating challenges (deterministic rotation + progress tracking)
│   ├── bingo_service.py          # Monthly Movie Bingo (deterministic 5x5 card from seed, progress from ratings)
│   ├── global_stats_service.py   # Platform-wide aggregate statistics
│   ├── watchlist_service.py      # Watchlist CRUD (add, remove, list, bulk check)
│   ├── dismissal_service.py     # Dismissal CRUD ("Not Interested" feedback)
│   ├── user_list_service.py      # Custom user lists CRUD (create, edit, delete, add/remove/reorder items)
│   ├── thematic_collection_service.py  # Auto-generated curated collections (genre+decade, director, year)
│   └── llm_service.py            # Ollama LLM client for re-ranking + explanations
├── models/          # SQLAlchemy ORM models
├── schemas/         # Pydantic request/response schemas
├── pipeline/        # Data processing (cleaner, embedder, FAISS, ALS)
├── evaluation/      # Recommendation quality metrics
│   ├── metrics.py             # Precision@K, Recall@K, NDCG@K, MAP@K
│   ├── splitter.py            # Temporal train/test split
│   └── evaluate.py            # Full evaluation runner + JSON report
├── core/            # Infrastructure
│   ├── cache.py               # Redis cache service + invalidation
│   ├── exceptions.py          # Custom exceptions + FastAPI handlers
│   └── logging.py             # Structured logging config
├── db/              # Database engine, migrations
├── config.py        # Environment-based configuration
└── main.py          # FastAPI app factory + service loading
```

## Make Commands

```bash
make setup      # Install deps + run migrations
make run        # Start dev server
make test       # Run tests with coverage
make download   # Download datasets
make pipeline   # Run data pipeline
make seed       # Load data into PostgreSQL
make evaluate   # Run evaluation metrics
make lint       # Lint with ruff
make format     # Format with ruff
```

## License

MIT
