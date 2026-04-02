# CineMatch-AI — Comprehensive Feature Plan

## Overview

A prioritized catalog of features that CineMatch-AI can implement using **only existing data sources** (MovieLens ml-32m ratings/tags, TMDb metadata, sentence-transformer embeddings, FAISS index, ALS collaborative filtering model). No paid APIs, no new external data sources required.

**Data inventory summary:**
- 29K movies with: title, overview, genres (JSONB), keywords (JSONB), cast_names (top 5, JSONB), director, release_date, vote_average, vote_count, popularity, poster_path, 384-dim embedding
- 162K users with 24.7M ratings (1-10 scale, timestamped)
- Watchlist table (user_id, movie_id, added_at)
- ALS model: 128-dim user factors (162K) + item factors (29K)
- FAISS IndexFlatIP: 29K movie embeddings for fast similarity search
- Existing services: hybrid/content/collab recommender, mood search, semantic search, LLM explanations

**Columns available in raw TMDb CSV but NOT yet imported:** `runtime`, `budget`, `revenue`, `spoken_languages`, `production_companies`, `production_countries`, `tagline`, `status`
**Columns recently imported:** `original_language`

---

## Category 1: Discovery & Exploration

### 1.1 Trending Now ✅
**Scope:** Single user
**One-line:** Surface the most-rated movies in the last N days as a trending feed.
- **Data backing:** `ratings.timestamp` — count ratings grouped by movie within a time window
- **Complexity:** Low
- **Value:** Solves cold-start UX for new users; creates a sense of community activity
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/movies/trending?window=7&limit=20`
  - SQL: `SELECT movie_id, COUNT(*) FROM ratings WHERE timestamp > NOW() - INTERVAL '{window} days' GROUP BY movie_id ORDER BY COUNT(*) DESC`
  - Cache in Redis (1h TTL)
  - Add `trending()` method to `MovieService`

### 1.2 Hidden Gems ✅
**Scope:** Single user
**One-line:** Discover high-quality movies that most users haven't found yet.
- **Data backing:** `movies.vote_average`, `movies.vote_count`, ratings count per movie
- **Complexity:** Low
- **Value:** Differentiates from mainstream recommendation; promotes long-tail discovery
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/movies/hidden-gems?min_rating=7.5&max_votes=100&limit=20`
  - Filter: vote_average >= threshold AND vote_count <= cap AND system_rating_count >= 10
  - Optional genre filter parameter
  - Cache in Redis (6h TTL)

### 1.3 Top Charts by Genre ✅
**Scope:** Single user
**One-line:** Pre-computed "Best of" lists for each genre ranked by in-system average rating.
- **Data backing:** `movies.genres` (JSONB with GIN index), `ratings.rating`, `ratings.movie_id`
- **Complexity:** Low
- **Value:** Familiar UI pattern (IMDb Top 250 style); great for browsing by taste
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/movies/top?genre=Thriller&limit=20`
  - SQL: JOIN movies + ratings, filter by genre containment, compute AVG(rating), require min 50 ratings
  - Cache per genre in Redis (6h TTL)
  - New "Charts" page in frontend with genre tabs

### 1.4 Decade Explorer ✅
**Scope:** Single user
**One-line:** Browse and discover movies organized by decade with per-decade stats.
- **Data backing:** `movies.release_date` — extract decade; `ratings` for per-decade top films
- **Complexity:** Low
- **Value:** Time-based exploration appeals to cinephiles exploring film history
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/movies/decades` — returns available decades + movie counts
  - Endpoint: `GET /api/v1/movies/discover?year_min=1990&year_max=1999&sort_by=rating` (already exists, just needs frontend)
  - Frontend: visual decade timeline with clickable periods

### 1.5 Director Spotlight ✅
**Scope:** Single user
**One-line:** Browse a director's complete filmography with the user's ratings overlaid.
- **Data backing:** `movies.director`, `ratings` (user's ratings for those films)
- **Complexity:** Low
- **Value:** Makes existing metadata interactive; appeals to auteur fans
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/movies/by-creator?name=Christopher+Nolan&role=director`
  - Query: filter movies WHERE director ILIKE query, sorted by release_date
  - If user_id provided, join with ratings to show user's scores
  - Frontend: filmography page with rated/unrated indicators, avg rating for this director

### 1.6 Actor Filmography ✅
**Scope:** Single user
**One-line:** Browse all movies featuring a specific actor with personal ratings overlaid.
- **Data backing:** `movies.cast_names` (JSONB array, top 5 per movie)
- **Complexity:** Low
- **Value:** Enables "I liked this actor, what else have they done?" discovery flow
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/movies/by-creator?name=Tom+Hanks&role=actor`
  - Query: filter movies WHERE cast_names @> '["Tom Hanks"]' (GIN-indexed JSONB containment)
  - Same filmography page pattern as Director Spotlight

### 1.7 "Movies Like This" Enhanced ✅
**Scope:** Single user
**One-line:** Augment existing similar movies with collaborative "users who liked this also liked."
- **Data backing:** `ratings` table — co-occurrence analysis of high-rated movies
- **Complexity:** Low-Medium
- **Value:** Adds a behavioral signal alongside content similarity; more diverse suggestions
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/movies/{id}/also-liked?min_rating=8&limit=10`
  - SQL: find users who rated movie X >= 8, then find their other movies rated >= 8, rank by frequency
  - Exclude the source movie, return with co-occurrence count
  - Display as second row on movie detail page: "Users who loved this also loved..."

### 1.8 Serendipity Mode / "Surprise Me" ✅
**Scope:** Single user
**One-line:** One-click random recommendation from outside the user's typical taste profile.
- **Data backing:** User's genre distribution (from stats), all movies, random selection with anti-genre filter
- **Complexity:** Low
- **Value:** Breaks filter bubbles; adds playfulness to the UX
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/users/{id}/surprise?limit=5`
  - Compute user's top 2 genres from stats, then randomly select well-rated movies (vote_average > 7) from OTHER genres
  - Optional: use ALS item factors to find movies far from user's preference vector (high negative dot product)
  - Frontend: "Surprise Me" button on home page

### 1.9 Keyword/Tag Cloud Explorer ✅
**Scope:** Single user
**One-line:** Browse movies by their crowd-sourced keyword tags with visual tag cloud.
- **Data backing:** `movies.keywords` (JSONB array, aggregated from MovieLens tags — 100K+ unique tags)
- **Complexity:** Low-Medium
- **Value:** Enables fine-grained thematic discovery beyond broad genres ("time travel", "heist", "dystopia")
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/movies/tags/popular?limit=50` — most frequent tags across movies
  - Endpoint: `GET /api/v1/movies/by-tag?tag=time+travel&limit=20`
  - Query: filter movies WHERE keywords @> '["time travel"]'
  - Frontend: interactive tag cloud on explore page, click to filter

### 1.10 Multi-Criteria Discovery ✅
**Scope:** Single user
**One-line:** Advanced filter combining genre + decade + rating range + director + keyword in one query.
- **Data backing:** All movie columns: genres, release_date, vote_average, director, keywords, cast_names
- **Complexity:** Medium
- **Value:** Power-user feature for precise discovery; replaces multiple separate searches
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/movies/advanced-search?genre=Sci-Fi&decade=2010s&min_rating=7&director=Villeneuve&keyword=dystopia`
  - Build dynamic SQLAlchemy query with chained filters
  - Reuse existing discover endpoint pattern with extended parameters

### 1.11 "Complete the Collection" Suggestions ✅
**Scope:** Single user
**One-line:** For users who've rated most films by a director/in a franchise, suggest the ones they're missing.
- **Data backing:** `movies.director`, `movies.cast_names`, `movies.keywords` (franchise tags), `ratings`
- **Complexity:** Medium
- **Value:** Drives completionism; increases engagement for invested users
- **Implementation sketch:**
  - Service method: find directors/actors where user has rated >= 3 films, return unrated films by same creator
  - Endpoint: `GET /api/v1/users/{id}/completions?limit=10`
  - Prioritize directors with highest user avg rating and most films in DB

---

## Category 2: Personalization & Recommendations

### 2.1 Mood Presets ✅
**Scope:** Single user
**One-line:** Curated mood buttons that map to semantic search queries for instant vibe-based discovery.
- **Data backing:** Existing semantic search (embeddings + FAISS), predefined mood-to-query mapping
- **Complexity:** Low
- **Value:** Zero backend work; makes the app feel interactive and approachable instantly
- **Implementation sketch:**
  - Frontend-only: mood buttons ("Feel-Good", "Mind-Bending", "Dark & Gritty", "Epic Adventure", "Cozy Night In", "Edge of Your Seat", "Tearjerker", "Nostalgic")
  - Each maps to a crafted search phrase sent to existing `POST /api/v1/recommendations/mood`
  - Display results as themed carousel rows

### 2.2 Personalized Home Feed ✅
**Scope:** Single user
**One-line:** Replace static home carousels with dynamically named rows tailored to the user's taste.
- **Data backing:** User's top-rated movies, genre distribution, ALS recommendations, trending data
- **Complexity:** Medium
- **Value:** Transforms home page from generic to personal; the Netflix-style "made for you" effect
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/users/{id}/feed?sections=5`
  - Service generates named sections:
    - "Because you rated {Movie} highly" — content-based from top seed
    - "Trending with users like you" — ALS recommendations filtered to recent popular
    - "Hidden gems in {top genre}" — hidden gems + genre filter
    - "Something different" — serendipity pick from outside usual genres
    - "New to you in {decade}" — unrated popular movies from user's favorite decade
  - Each section calls existing services internally

### 2.3 "More Like This" from Any Seed ✅
**Scope:** Single user
**One-line:** Let users pick any movie as a seed and get personalized recommendations branching from it.
- **Data backing:** Movie embeddings (pgvector/FAISS), ALS item factors, user's rating history
- **Complexity:** Medium
- **Value:** Gives users direct control over recommendation direction; "I want more of THIS specifically"
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/users/{id}/recommendations/from-seed/{movie_id}?limit=20`
  - Content candidates: similar movies via embedding (existing similar movies endpoint)
  - If user has ratings: blend with ALS collab scores (alpha weighting)
  - Filter out already-rated movies
  - Return with explanation: "Similar to {seed} and matches your taste"

### 2.4 Recommendation Diversity Controls ✅
**Scope:** Single user
**One-line:** Let users adjust how adventurous vs. safe their recommendations are.
- **Data backing:** Existing hybrid recommender alpha parameter, MMR diversity_lambda
- **Complexity:** Low-Medium
- **Value:** Gives users agency over recommendation behavior; reduces "same old same old" complaints
- **Implementation sketch:**
  - Add query params to existing recommendations endpoint: `diversity=low|medium|high`
  - Map to MMR lambda values: low=0.9 (relevance-heavy), medium=0.7 (default), high=0.4 (diversity-heavy)
  - Frontend: slider or toggle on recommendations page

### 2.5 "Not Interested" / Negative Feedback ✅
**Scope:** Single user
**One-line:** Let users dismiss recommendations they're not interested in, improving future suggestions.
- **Data backing:** New `dismissals` table (user_id, movie_id, dismissed_at)
- **Complexity:** Medium
- **Value:** Critical feedback loop; prevents showing the same unwanted recommendations repeatedly
- **Implementation sketch:**
  - New model: `Dismissal(user_id, movie_id, dismissed_at)`
  - Endpoint: `POST /api/v1/users/{id}/dismiss` with `{movie_id}`
  - Filter dismissed movies from all recommendation queries
  - Invalidate recommendation cache on dismiss (same as rating)
  - Migration: single new table

### 2.6 Watch History Awareness ✅
**Scope:** Single user
**One-line:** Automatically exclude rated movies from recommendations and highlight unrated ones.
- **Data backing:** `ratings` table (user_id, movie_id)
- **Complexity:** Low
- **Value:** Prevents frustrating "I already saw that" recommendations
- **Implementation sketch:**
  - Already partially implemented (hybrid recommender filters rated movies)
  - Extend to all discovery endpoints: trending, hidden gems, genre charts
  - Add `exclude_rated=true` param to discover/search endpoints
  - Frontend: badge on already-rated movies showing user's rating

### 2.7 Taste Profile Summary ✅
**Scope:** Single user
**One-line:** A natural-language summary of the user's movie taste generated from their rating patterns.
- **Data backing:** User stats (genre distribution, top directors, top actors, avg rating, rating count)
- **Complexity:** Medium
- **Value:** Engaging self-reflection feature; "You're a thriller-loving cinephile who gravitates toward Nolan and Fincher"
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/users/{id}/taste-profile`
  - Template-based generation (no LLM needed):
    - Top genre + percentage → "You're a {genre} enthusiast ({pct}% of your ratings)"
    - Avg rating vs global → "You're a {generous/tough} critic (avg {x} vs site avg {y})"
    - Top director affinity → "You have a special appreciation for {director}'s work"
    - Decade preference → "Your sweet spot is {decade}s cinema"
  - Optional: if LLM enabled, pass stats to Ollama for a more natural summary

### 2.8 Genre Affinity Radar Chart ✅
**Scope:** Single user
**One-line:** Visual radar/spider chart showing how much a user leans into each genre.
- **Data backing:** Existing `UserStatsService.genre_distribution` — already computes genre percentages
- **Complexity:** Low
- **Value:** Visually striking profile element; shareable and self-reflective
- **Implementation sketch:**
  - Data already available via `GET /api/v1/users/{id}/stats` → `genre_distribution`
  - Frontend-only: Recharts RadarChart component on profile page
  - Normalize top 8-10 genres to radar axes

---

## Category 3: Analytics & Stats

### 3.1 Film Diary / Rating Calendar ✅
**Scope:** Single user
**One-line:** Calendar heatmap (GitHub-style) showing daily rating activity over time.
- **Data backing:** `ratings.timestamp` — every rating has a precise timestamp
- **Complexity:** Low
- **Value:** Visual record of movie-watching journey; encourages consistent engagement
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/users/{id}/diary?year=2025`
  - SQL: GROUP BY DATE(timestamp), return [{date, count, movies: [{id, title, rating}]}]
  - Frontend: calendar heatmap component (like GitHub contributions)
  - Click a day to expand and see movies rated that day

### 3.2 CineMatch Wrapped (Year in Review)
**Scope:** Single user
**One-line:** Spotify Wrapped-style annual summary of a user's movie year.
- **Data backing:** `ratings` (timestamped), `movies` (genres, director, cast, release_date), ALS user factors
- **Complexity:** Medium
- **Value:** Highly shareable; creates annual engagement spike; showcases data richness
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/users/{id}/year-in-review?year=2025`
  - Stats computed:
    - Total films rated, avg rating, favorite genre (mode), favorite director/actor
    - Most-rated decade, highest-rated movie, lowest-rated movie
    - Longest rating streak (consecutive days), busiest month
    - Rating personality: "The Cinephile" / "The Blockbuster Fan" / "The Critic" / "The Explorer" (rule-based from genre diversity + avg rating + volume)
    - "Movie Soulmate" — nearest user by ALS factor cosine similarity
  - Cache in Redis (24h TTL)
  - Frontend: scrollable visual summary with large stat cards

### 3.3 Rating Distribution Insights ✅
**Scope:** Single user
**One-line:** Show how a user's ratings compare to the community's ratings for the same movies.
- **Data backing:** `ratings` — user's ratings vs. AVG(rating) for same movies
- **Complexity:** Low
- **Value:** "Am I too generous?" self-awareness; adds social comparison element
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/users/{id}/rating-comparison`
  - For user's rated movies, compute: user_avg vs community_avg, agreement percentage, biggest disagreements
  - Return: {user_avg, community_avg, agreement_pct, most_overrated: [...], most_underrated: [...]}
  - "Most overrated" = movies where user rated much higher than community avg
  - "Most underrated" = movies where user rated much lower

### 3.4 Taste Evolution Timeline ✅
**Scope:** Single user
**One-line:** Track how a user's genre preferences have shifted over time.
- **Data backing:** `ratings.timestamp`, `movies.genres` — slice genre distribution by time period
- **Complexity:** Medium
- **Value:** Fascinating self-reflection; "I used to love horror but now I'm all about dramas"
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/users/{id}/taste-evolution?granularity=quarter`
  - Group ratings by quarter/year, compute genre distribution per period
  - Return: [{period: "2024-Q1", genres: {Action: 40%, Drama: 30%, ...}}, ...]
  - Frontend: stacked area chart or alluvial diagram showing genre flow over time

### 3.5 Director/Actor Affinity Ranking ✅
**Scope:** Single user
**One-line:** Ranked list of directors and actors by how much the user loves their work (weighted avg rating).
- **Data backing:** `movies.director`, `movies.cast_names`, `ratings.rating`
- **Complexity:** Low
- **Value:** "Your favorite filmmaker" insights; drives filmography exploration
- **Implementation sketch:**
  - Partially exists in `UserStatsService` (top_directors, top_actors by count)
  - Enhance: compute weighted_score = avg_rating * log(count) to balance frequency with enthusiasm
  - Add to stats response or new endpoint: `GET /api/v1/users/{id}/affinities`
  - Return: [{name, role, avg_rating, count, films_rated: [...]}]

### 3.6 Controversial Movies ✅
**Scope:** Single user
**One-line:** Movies with the highest rating variance across all users — love-it-or-hate-it films.
- **Data backing:** `ratings.rating` — compute STDDEV per movie
- **Complexity:** Low
- **Value:** Fascinating discovery angle; "divisive films" are inherently interesting conversation starters
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/movies/controversial?min_ratings=100&limit=20`
  - SQL: SELECT movie_id, AVG(rating), STDDEV(rating) FROM ratings GROUP BY movie_id HAVING COUNT(*) >= 100 ORDER BY STDDEV(rating) DESC
  - Return with avg + stddev + rating histogram per movie
  - Frontend: bar showing the polarized distribution

### 3.7 Rating Streak & Milestones ✅
**Scope:** Single user
**One-line:** Track consecutive-day rating streaks and celebrate milestones (100th rating, etc.).
- **Data backing:** `ratings.timestamp` — compute consecutive dates with at least one rating
- **Complexity:** Low
- **Value:** Gamification that encourages daily engagement without being pushy
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/users/{id}/streaks`
  - Compute: current_streak, longest_streak, total_ratings, milestones_reached
  - Milestones: 10, 25, 50, 100, 250, 500, 1000 ratings
  - Frontend: streak counter on profile, milestone badges

### 3.8 Global Platform Stats ✅
**Scope:** Single user
**One-line:** Public dashboard showing platform-wide statistics and interesting facts.
- **Data backing:** All tables — aggregate counts, averages, distributions
- **Complexity:** Low
- **Value:** Creates sense of community; interesting landing page content
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/stats/global`
  - Stats: total_movies, total_users, total_ratings, avg_rating, most_rated_movie, highest_rated_movie, most_active_user, ratings_this_week
  - Heavy Redis caching (1h TTL)
  - Display on home page footer or dedicated stats page

---

## Category 4: Social & Comparison

### 4.1 Taste Compatibility Score
**Scope:** Multiple user
**One-line:** Compare movie taste between two users using their ALS latent vectors.
- **Data backing:** ALS user factors (128-dim vectors for 162K users), genre distributions from ratings
- **Complexity:** Medium
- **Value:** Social hook; creates "compare with a friend" engagement loop
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/users/{id}/compatibility/{other_id}`
  - Cosine similarity of ALS user_factors → percentage score
  - Genre overlap: compare genre distributions, highlight agreements and differences
  - Shared movies: JOIN ratings for both users, show movies both rated and rating differences
  - Return: {compatibility_pct, genre_overlap: [...], shared_movies: [...], biggest_disagreements: [...]}

### 4.2 "Movie Soulmate" Finder
**Scope:** Multiple user
**One-line:** Find the user in the system with the most similar taste to you.
- **Data backing:** ALS user factors (128-dim, 162K users)
- **Complexity:** Medium
- **Value:** Curiosity-driven engagement; "who's my movie twin?"
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/users/{id}/soulmate`
  - Compute cosine similarity between target user's ALS vector and all other users
  - Return top match with compatibility score + shared highly-rated movies
  - Cache result in Redis (24h TTL, expensive computation)
  - Optimization: use numpy batch dot product, or pre-build a user-factor FAISS index

### 4.3 Shared Watchlist / "Watch Together"
**Scope:** Multiple user
**One-line:** Find movies on both users' watchlists or recommend movies both would enjoy.
- **Data backing:** `watchlist` table, ALS user factors, movie embeddings
- **Complexity:** Medium
- **Value:** Practical social utility; solves "what should we watch tonight?" for couples/friends
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/users/{id}/watch-together/{other_id}?limit=10`
  - Step 1: Intersection of both watchlists
  - Step 2: If not enough, find movies where BOTH users' ALS predicted scores are high
  - Step 3: Sort by minimum of the two predicted scores (both must like it)
  - Filter out movies either user has already rated

### 4.4 Rating Comparison for a Movie ✅
**Scope:** Single user
**One-line:** See how your rating of a specific movie compares to the community distribution.
- **Data backing:** `ratings` for the specific movie — all user ratings
- **Complexity:** Low
- **Value:** Contextualizes individual ratings; "am I the outlier here?"
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/movies/{id}/rating-stats?user_id=42`
  - Return: {avg_rating, median_rating, total_ratings, distribution: {1: n, 2: n, ...}, user_rating: 8}
  - Frontend: histogram with user's rating highlighted

### 4.5 "Recommend to a Friend"
**Scope:** Multiple user
**One-line:** Given a friend's user_id, suggest movies they'd love that you've already rated highly.
- **Data backing:** User's high ratings, friend's ALS predicted scores, friend's existing ratings (to exclude)
- **Complexity:** Medium
- **Value:** Creates intentional social sharing; makes recommendations feel personal
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/users/{id}/recommend-to/{friend_id}?limit=10`
  - Take user's movies rated >= 8, filter out friend's already-rated
  - Rank remaining by friend's ALS predicted score
  - Return with: "You rated this {rating}/10 and {friend} would probably love it"

---

## Category 5: Lists & Curation

### 5.1 Custom User Lists ✅
**Scope:** Single user
**One-line:** Named, ordered movie collections users can create, edit, and share.
- **Data backing:** New tables; movie data from existing `movies` table
- **Complexity:** Medium
- **Value:** Core engagement feature (Letterboxd's most-used feature); drives return visits
- **Implementation sketch:**
  - New models: `UserList(id, user_id, name, description, is_public, created_at, updated_at)`, `UserListItem(id, list_id, movie_id, position, added_at)`
  - Endpoints: full CRUD `/api/v1/lists/` + `/api/v1/lists/{id}/items/`
  - Public lists browsable at `/api/v1/lists/popular` (ranked by item count or follower count)
  - Migration: 2 new tables with compound indexes

### 5.2 Auto-Generated Thematic Collections ✅
**Scope:** Single user
**One-line:** System-generated lists like "Best Sci-Fi of the 2010s" or "Christopher Nolan: Complete Works."
- **Data backing:** `movies.genres`, `movies.release_date`, `movies.director`, `ratings` for ranking
- **Complexity:** Low-Medium
- **Value:** Curated content without manual effort; fills the "browse" need for casual users
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/collections?type=genre_decade` or `type=director`
  - Generate on-demand: top-rated movies per genre-decade combo, director filmography ranked by rating
  - Templates: "Best {Genre} of the {Decade}", "{Director}: A Filmography", "Highest Rated {Year}"
  - Cache generated collections in Redis (6h TTL)

### 5.3 "Movies You Haven't Seen by Directors You Love" ✅
**Scope:** Single user
**One-line:** Auto-curated list of unwatched films from the user's favorite directors.
- **Data backing:** `movies.director`, `ratings` (to find favorite directors and already-seen films)
- **Complexity:** Low
- **Value:** Highly targeted discovery that feels personally relevant
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/users/{id}/director-gaps?limit=20`
  - Find user's top 5 directors by avg rating (min 3 films rated)
  - For each director, find movies in DB that user hasn't rated
  - Sort by vote_average descending
  - Same pattern works for actors: `GET /api/v1/users/{id}/actor-gaps`

### 5.4 Watchlist Recommendations ✅
**Scope:** Single user
**One-line:** Recommend movies similar to what's on the user's watchlist.
- **Data backing:** `watchlist` (user's saved movies), movie embeddings, FAISS
- **Complexity:** Low-Medium
- **Value:** "If these are on your list, you'll also want these" — natural extension of intent
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/users/{id}/watchlist/recommendations?limit=10`
  - Compute mean embedding of watchlist movies
  - FAISS nearest neighbor search with mean vector
  - Filter out already-rated and already-on-watchlist movies
  - Return with explanation: "Based on your watchlist"

---

## Category 6: Gamification & Engagement

### 6.1 Achievement Badges ✅
**Scope:** Single user
**One-line:** Unlock badges for rating milestones, genre exploration, and special patterns.
- **Data backing:** `ratings` (counts, timestamps, genres via JOIN), `movies.genres`, `movies.director`
- **Complexity:** Medium
- **Value:** Proven engagement driver; encourages exploration and return visits
- **Implementation sketch:**
  - Badge definitions (computed on-the-fly, not stored):
    - **First Rating** — rate your first movie
    - **Century Club** — 100 ratings
    - **Marathon Runner** — 500 ratings
    - **Genre Explorer** — rate movies in 10+ different genres
    - **Decade Hopper** — rate movies from 5+ different decades
    - **Director Devotee** — rate 5+ movies by the same director
    - **The Critic** — avg rating below 5.0 with 50+ ratings
    - **Easy to Please** — avg rating above 8.0 with 50+ ratings
    - **Weekend Warrior** — rate 5+ movies in a single weekend
    - **Night Owl** — 10+ ratings submitted between midnight and 5am
    - **Streak Master** — 7-day rating streak
    - **Completionist** — rate every movie by a director (min 5 in DB)
  - Endpoint: `GET /api/v1/users/{id}/achievements`
  - Compute from ratings data at query time, cache in Redis (1h TTL)
  - No new tables needed — pure computation

### 6.2 Rating Challenges ✅
**Scope:** Single user
**One-line:** Periodic challenges like "Rate 5 horror movies this week" to encourage exploration.
- **Data backing:** `movies.genres`, `movies.release_date`, `movies.director`, `ratings`
- **Complexity:** Medium
- **Value:** Creates time-bound engagement; drives users to explore outside comfort zone
- **Implementation sketch:**
  - Predefined challenge templates: "Rate 5 {random genre} movies", "Explore the {random decade}s", "Director deep-dive: {director}"
  - Endpoint: `GET /api/v1/challenges/current` — returns active challenges
  - Endpoint: `GET /api/v1/users/{id}/challenges/progress` — checks user's ratings against challenge criteria
  - Challenges rotate weekly (deterministic from date hash, no manual curation)

### 6.3 "Movie Bingo" Card ✅
**Scope:** Single user
**One-line:** Personalized bingo card of movie categories to complete (e.g., "A movie from before 1970").
- **Data backing:** `movies.genres`, `movies.release_date`, `movies.director`, `movies.keywords`, `movies.vote_average`
- **Complexity:** Medium
- **Value:** Fun, visual gamification; shareable progress creates social buzz
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/users/{id}/bingo?seed=2025-03`
  - Generate 5x5 grid of categories from templates:
    - "A {genre} movie", "A movie from the {decade}s", "A movie directed by {director}", "A movie rated below 6 on TMDb", "A movie with '{keyword}' theme", "A movie longer than 2.5 hours" (requires runtime field)
  - Check user's ratings to mark completed cells
  - Deterministic seed ensures same card for the month

---

## Category 7: Enhanced Movie Detail

### 7.1 "Why This Score?" Decomposition ✅
**Scope:** Single user
**One-line:** For any recommended movie, show exactly how the content and collaborative scores were computed.
- **Data backing:** Already computed internally in `HybridRecommender._hybrid_recommend()` — content_score, collab_score, alpha
- **Complexity:** Low
- **Value:** Transparency builds trust in recommendations; shows ML depth
- **Implementation sketch:**
  - Already partially implemented (score_breakdown in RecommendationItem schema)
  - Ensure all three fields (content_score, collab_score, alpha) are populated
  - Frontend: small stacked bar or pie showing content vs. collab contribution
  - "78% taste match + 22% popular with similar users"

### 7.2 Enhanced "Because You Liked" Explanations ✅
**Scope:** Single user
**One-line:** Rich explanation tags on every recommendation showing genre/director/actor overlap.
- **Data backing:** `movies.genres`, `movies.director`, `movies.cast_names`, user's rating history
- **Complexity:** Low
- **Value:** Makes recommendations feel intelligent rather than random
- **Implementation sketch:**
  - Already partially implemented (feature_explanations, because_you_liked fields)
  - Enhance feature explanation templates:
    - "Same director as {Movie} — {Director}"
    - "Matches your love of {Genre1} and {Genre2}"
    - "Stars {Actor}, who appears in {N} movies you rated 8+"
    - "From the {Decade}s, your favorite era"
  - Compare recommended movie's metadata with user's top-rated movies' metadata
  - Pure server-side string generation, no LLM needed

### 7.3 Movie Connections / "Six Degrees" ✅
**Scope:** Single user
**One-line:** Show how two movies are connected through shared cast, directors, genres, or keywords.
- **Data backing:** `movies.director`, `movies.cast_names`, `movies.genres`, `movies.keywords`
- **Complexity:** Medium
- **Value:** Fun exploration tool; reveals non-obvious connections between films
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/movies/{id1}/connection/{id2}`
  - Find all shared attributes: common actors, same director, shared genres, shared keywords
  - Return: {connections: [{type: "actor", value: "DiCaprio", details: "appears in both"}, ...]}
  - Extension: find shortest path between two movies through shared people (BFS on actor/director graph)

### 7.4 Movie "DNA" Breakdown ✅
**Scope:** Single user
**One-line:** Visual breakdown of what makes a movie unique — its genre mix, keyword themes, era, and tone.
- **Data backing:** `movies.genres`, `movies.keywords`, `movies.release_date`, `movies.vote_average`, embedding vector
- **Complexity:** Low-Medium
- **Value:** Deeper movie understanding; explains why recommendations match
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/movies/{id}/dna`
  - Return: {genres with weights, top keywords, decade, mood_tags (derived from embedding neighbors)}
  - Mood inference: find 5 nearest neighbors by embedding, extract common keywords not in this movie → these are the "vibe" tags
  - Frontend: visual "DNA strip" or tag cloud showing movie's character

### 7.5 Community Sentiment for a Movie ✅
**Scope:** Single user
**One-line:** Show rating distribution, average, and how polarizing a movie is across all users.
- **Data backing:** `ratings` for the specific movie — all ratings from all users
- **Complexity:** Low
- **Value:** Social proof and context for individual movies; "is this universally loved or divisive?"
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/movies/{id}/community`
  - Return: {total_ratings, avg_rating, median, stddev, distribution: {1: n, ..., 10: n}, polarization_score}
  - polarization_score = stddev / max_possible_stddev (0 = consensus, 1 = maximally divisive)
  - Frontend: histogram chart on movie detail page

### 7.6 Movie Popularity Timeline ✅
**Scope:** Single user
**One-line:** Show when a movie gets rated most — spikes around releases, award seasons, trending moments.
- **Data backing:** `ratings.timestamp` for a specific movie — group by month/week
- **Complexity:** Low
- **Value:** Interesting temporal context; shows cultural moments around a film
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/movies/{id}/activity?granularity=month`
  - SQL: SELECT DATE_TRUNC('month', timestamp), COUNT(*) FROM ratings WHERE movie_id=X GROUP BY 1
  - Return: [{period, count}] timeline
  - Frontend: sparkline or small line chart on movie detail page

---

## Category 8: Search & Navigation

### 8.1 Autocomplete Search ✅
**Scope:** Single user
**One-line:** Real-time search suggestions as the user types, with fuzzy matching.
- **Data backing:** `movies.title` with existing pg_trgm index for fuzzy matching
- **Complexity:** Low
- **Value:** Essential UX improvement; reduces search friction
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/movies/autocomplete?q=inc&limit=5`
  - Use existing ILIKE + pg_trgm similarity, but optimized for speed (return only id + title + year)
  - Debounce on frontend (300ms)
  - Cache popular prefixes in Redis

### 8.2 Natural Language Search ✅
**Scope:** Single user
**One-line:** Search by description like "a heist movie set in space with a twist ending."
- **Data backing:** Already implemented as semantic search via embeddings + FAISS
- **Complexity:** Low (mostly frontend polish)
- **Value:** The most intuitive search possible; leverages existing embedding infrastructure
- **Implementation sketch:**
  - Existing endpoint: `GET /api/v1/movies/semantic-search?q=...`
  - Frontend enhancement: prominent search bar with "Describe what you're looking for..." placeholder
  - Add example queries as clickable suggestions below the search bar

### 8.3 Filter by Language (Pipeline Enhancement) ✅
**Scope:** Single user
**One-line:** Filter movies by original language (English, French, Korean, Japanese, etc.).
- **Data backing:** `original_language` available in raw TMDb CSV but NOT currently imported
- **Complexity:** Low-Medium (requires pipeline change + migration)
- **Value:** Essential for international cinema fans; enables "Korean cinema" or "French New Wave" exploration
- **Implementation sketch:**
  - Pipeline: add `original_language` to cleaner.py output columns
  - Migration: add `original_language VARCHAR(10)` to movies table
  - Seed: populate from movies_clean.parquet
  - Endpoint: add `language` param to existing `/api/v1/movies/discover`

### 8.4 Filter by Runtime (Pipeline Enhancement) ✅
**Scope:** Single user
**One-line:** Filter movies by length — "quick watch" (<90min) vs "epic" (>180min).
- **Data backing:** `runtime` available in raw TMDb CSV but NOT currently imported
- **Complexity:** Low-Medium (requires pipeline change + migration)
- **Value:** Practical filter for "I only have 90 minutes" use case
- **Implementation sketch:**
  - Pipeline: add `runtime` (integer, minutes) to cleaner.py
  - Migration: add `runtime INTEGER` to movies table
  - Endpoint: add `min_runtime`, `max_runtime` params to discover
  - Preset buttons: "Quick Watch (<90min)", "Standard (90-150min)", "Epic (>150min)"

### 8.5 Search by Cast Combination ✅
**Scope:** Single user
**One-line:** Find movies where two specific actors both appear.
- **Data backing:** `movies.cast_names` (JSONB array)
- **Complexity:** Low
- **Value:** "Movies with both DiCaprio and Tom Hardy" — common user intent
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/movies/by-cast?actors=Leonardo+DiCaprio,Tom+Hardy`
  - SQL: WHERE cast_names @> '["Leonardo DiCaprio"]' AND cast_names @> '["Tom Hardy"]'
  - GIN index on cast_names makes this efficient

---

## Category 9: Onboarding & Utility

### 9.1 Quick Rate Onboarding ✅
**Scope:** Single user
**One-line:** New user flow where they rate 10-20 popular, genre-diverse movies to bootstrap their taste profile.
- **Data backing:** `movies.vote_count` + `movies.genres` to select popular, diverse films; `ratings` to capture input
- **Complexity:** Medium
- **Value:** Solves cold-start problem immediately; Taste.io's core onboarding pattern — users who complete it get 10x better recommendations
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/onboarding/movies?count=20`
  - Select 20 movies: highest vote_count, one per genre, ensuring broad recognition
  - Frontend: swipe-style or grid rate flow — "Rate movies you've seen, skip ones you haven't"
  - After completion, trigger recommendation cache build for the user
  - Store ratings via existing `POST /api/v1/users/{id}/ratings`

### 9.2 Rewatch Recommender ✅
**Scope:** Single user
**One-line:** Suggest movies the user rated highly long ago that are worth revisiting.
- **Data backing:** `ratings.rating` + `ratings.timestamp` — find high ratings with old timestamps
- **Complexity:** Low
- **Value:** Unique angle most platforms miss; nostalgia-driven engagement
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/users/{id}/rewatch?limit=10`
  - Query: SELECT movies rated >= 8 WHERE timestamp < NOW() - INTERVAL '2 years', ORDER BY rating DESC, timestamp ASC
  - Optional: boost movies with high community rewatch signal (high rating count + high avg = "classic" indicator)
  - Frontend: "Revisit your favorites" section on profile or home

### 9.3 Blind Spot Detector ✅
**Scope:** Single user
**One-line:** Popular, highly-regarded movies the user has never rated — their cinematic blind spots.
- **Data backing:** `movies.vote_count`, `movies.vote_average`, `ratings` (to find unrated)
- **Complexity:** Low
- **Value:** "You've never seen Pulp Fiction?!" — drives completionism and conversation
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/users/{id}/blind-spots?limit=20`
  - Query: top movies by (vote_count * vote_average) that the user has NOT rated
  - Optional genre filter: "Blind spots in Horror"
  - Frontend: checklist-style display with "Have you seen this?" prompts

### 9.4 Compare Two Movies Side-by-Side
**Scope:** Single user
**One-line:** Visual comparison of any two movies across all metadata dimensions.
- **Data backing:** All movie columns (genres, director, cast, votes, release_date, keywords, embedding similarity)
- **Complexity:** Low
- **Value:** Satisfies "which should I watch?" decision-making; fun exploration tool
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/movies/compare?ids=42,108`
  - Return both movies' full metadata + computed comparisons:
    - Shared genres, actors, keywords
    - Embedding cosine similarity score
    - Community avg rating comparison
    - If user_id provided: predicted preference via ALS scores
  - Frontend: side-by-side card layout with highlighted overlaps

### 9.5 Import/Export Ratings (CSV)
**Scope:** Single user
**One-line:** Import ratings from Letterboxd/IMDb CSV exports; export CineMatch ratings as CSV.
- **Data backing:** `movies.imdb_id`, `movies.tmdb_id` for mapping; `ratings` table for storage
- **Complexity:** Medium
- **Value:** Removes adoption barrier; users with existing Letterboxd/IMDb history can migrate instantly
- **Implementation sketch:**
  - Endpoint: `POST /api/v1/users/{id}/ratings/import` (multipart CSV upload)
  - Parse Letterboxd CSV format (tmdb_id + rating) or IMDb CSV (imdb_id + rating)
  - Map external IDs to internal movie_id via `movies.imdb_id` / `movies.tmdb_id`
  - Endpoint: `GET /api/v1/users/{id}/ratings/export` — download CSV
  - Rescale ratings to 1-10 if source uses different scale (Letterboxd 0.5-5.0, IMDb 1-10)

### 9.6 Tastemaker Score
**Scope:** Single user
**One-line:** Identify users whose high ratings predict what others will later enjoy — community taste leaders.
- **Data backing:** `ratings.rating` + `ratings.timestamp` — find early raters of later-popular films
- **Complexity:** Medium
- **Value:** Gamification + social proof; encourages thoughtful early rating behavior
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/users/{id}/tastemaker-score`
  - For each movie the user rated >= 8 early (within first 10% of ratings chronologically): check if the community later converged to a high avg
  - Score = fraction of early-high-rated movies that became community favorites
  - Leaderboard: `GET /api/v1/leaderboard/tastemakers?limit=20`
  - Cache heavily (computation is expensive, recalculate weekly)

### 9.7 Predicted Match Percentage
**Scope:** Single user
**One-line:** Show a "94% match" score on every movie card based on the user's taste profile.
- **Data backing:** ALS model (collab score) + embedding similarity (content score) — hybrid prediction
- **Complexity:** Low-Medium
- **Value:** Netflix's most iconic UX element; gives users instant confidence about any movie
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/users/{id}/predicted-rating/{movie_id}`
  - Compute: hybrid score from existing recommender (content + collab), normalize to 0-100%
  - Batch version: `POST /api/v1/users/{id}/predicted-ratings` with body `{movie_ids: [...]}`
  - Display as percentage badge on every movie card throughout the app
  - Cache per user-movie pair in Redis (15min TTL, invalidate on new rating)

### 9.8 Seasonal / Contextual Recommendations
**Scope:** Single user
**One-line:** Time-aware recommendations — horror in October, holiday films in December, summer blockbusters in June.
- **Data backing:** `movies.keywords`, `movies.genres`, `movies.release_date`, current date
- **Complexity:** Low
- **Value:** Timely, relevant discovery that feels aware and thoughtful
- **Implementation sketch:**
  - Endpoint: `GET /api/v1/movies/seasonal?limit=20`
  - Month-to-keyword/genre mapping:
    - October → keywords containing "horror", "halloween", "scary" + genre "Horror"
    - December → keywords "christmas", "holiday", "winter" + genre "Family"
    - Summer (Jun-Aug) → genre "Action", "Adventure" + high popularity
    - February → genre "Romance" + keywords "love", "relationship"
  - Combine with user personalization if user_id provided (filter to predicted-high-rating)
  - Frontend: seasonal banner/carousel on home page

---

## Category 10: Data Enrichment (From Existing Raw Data)

These features require importing additional columns from the TMDb CSV that we already download but don't currently use. No new external data sources needed.

### 10.1 Import Runtime Field
**Scope:** Single user
**One-line:** Add movie runtime (minutes) from TMDb CSV to enable duration-based features.
- **Data backing:** `runtime` column in `TMDB_all_movies.csv`
- **Complexity:** Low
- **Value:** Unlocks: runtime filter, "estimated watch time" in Wrapped, movie duration display, "quick watch" discovery
- **Implementation:** Add to cleaner.py column selection, migration for movies table, seed update

### 10.2 Import Original Language
**Scope:** Single user
**One-line:** Add original_language from TMDb CSV to enable language-based filtering and stats.
- **Data backing:** `original_language` column in `TMDB_all_movies.csv`
- **Complexity:** Low
- **Value:** Unlocks: language filter, "international cinema" discovery, language diversity stats
- **Implementation:** Same pattern as runtime — cleaner.py + migration + seed

### 10.3 Import Tagline
**Scope:** Single user
**One-line:** Add movie taglines from TMDb CSV for richer movie cards and search.
- **Data backing:** `tagline` column in `TMDB_all_movies.csv`
- **Complexity:** Low
- **Value:** Richer movie cards; taglines are great for quick context ("In space, no one can hear you scream")
- **Implementation:** Same pattern — cleaner.py + migration + seed

### 10.4 Import Revenue/Budget (for ROI Analysis)
**One-line:** Add budget and revenue to enable box office insights and "sleeper hit" discovery.
- **Data backing:** `budget`, `revenue` columns in `TMDB_all_movies.csv`
- **Complexity:** Low
- **Value:** Unlocks: "sleeper hits" (high rating, low budget), ROI sorting, "most expensive movies" lists
- **Implementation:** Same pattern — only include movies where budget > 0 (many are 0/null)

---

## Implementation Priority Matrix

### Tier 1: Quick Wins (Low effort, high impact — do first)
| # | Feature | Effort | Category |
|---|---------|--------|----------|
| 1 | 2.1 Mood Presets | Low | Personalization |
| 2 | 1.1 Trending Now | Low | Discovery |
| 3 | 7.1 Score Decomposition | Low | Movie Detail |
| 4 | 7.2 Enhanced Explanations | Low | Movie Detail |
| 5 | 1.5 Director Spotlight | Low | Discovery |
| 6 | 1.6 Actor Filmography | Low | Discovery |
| 7 | 3.1 Film Diary | Low | Analytics |
| 8 | 1.2 Hidden Gems | Low | Discovery |
| 9 | 1.3 Top Charts by Genre | Low | Discovery |
| 10 | 3.7 Rating Streaks & Milestones | Low | Analytics |
| 11 | 7.5 Community Sentiment ✅ | Low | Movie Detail |
| 12 | 8.1 Autocomplete Search ✅ | Low | Search |
| 13 | 3.8 Global Platform Stats | Low | Analytics |
| 14 | 2.8 Genre Affinity Radar | Low | Personalization |
| 15 | 9.3 Blind Spot Detector ✅ | Low | Onboarding |
| 16 | 9.4 Compare Two Movies | Low | Onboarding |
| 17 | 9.8 Seasonal Recommendations | Low | Onboarding |

### Tier 2: Medium Effort, High Value
| # | Feature | Effort | Category |
|---|---------|--------|----------|
| 18 | 1.7 "Also Liked" Collaborative | Low-Med | Discovery |
| 19 | 1.8 Serendipity / Surprise Me | Low | Discovery |
| 20 | 1.9 Keyword Tag Cloud | Low-Med | Discovery |
| 21 | 5.3 Director/Actor Gaps | Low | Lists |
| 22 | 5.4 Watchlist Recommendations | Low-Med | Lists |
| 23 | 3.3 Rating Distribution Insights | Low | Analytics |
| 24 | 3.5 Director/Actor Affinity | Low | Analytics |
| 25 | 3.6 Controversial Movies | Low | Analytics |
| 26 | 7.6 Movie Popularity Timeline | Low | Movie Detail |
| 27 | 4.4 Rating Comparison | Low | Social |
| 28 | 2.4 Diversity Controls | Low-Med | Personalization |
| 29 | 8.5 Search by Cast Combo | Low | Search |
| 30 | 9.2 Rewatch Recommender ✅ | Low | Onboarding |
| 31 | 9.7 Predicted Match Percentage | Low-Med | Onboarding |

### Tier 3: Bigger Builds, Strong Differentiators
| # | Feature | Effort | Category |
|---|---------|--------|----------|
| 32 | 10.1-10.4 Data Enrichment (runtime, lang, tagline, budget) | Low-Med | Pipeline |
| 33 | 8.3 Language Filter | Low-Med | Search |
| 34 | 8.4 Runtime Filter ✅ | Low-Med | Search |
| 35 | 2.2 Personalized Home Feed | Medium | Personalization |
| 36 | 2.3 "More Like This" from Seed | Medium | Personalization |
| 37 | 2.5 "Not Interested" Dismissals | Medium | Personalization |
| 38 | 2.7 Taste Profile Summary | Medium | Personalization |
| 39 | 3.2 CineMatch Wrapped | Medium | Analytics |
| 40 | 3.4 Taste Evolution Timeline | Medium | Analytics |
| 41 | 4.1 Taste Compatibility | Medium | Social |
| 42 | 4.2 Movie Soulmate Finder | Medium | Social |
| 43 | 4.3 Shared Watchlist / Watch Together | Medium | Social |
| 44 | 4.5 Recommend to a Friend | Medium | Social |
| 45 | 5.1 Custom User Lists | Medium | Lists |
| 46 | 5.2 Auto-Generated Collections | Low-Med | Lists |
| 47 | 6.1 Achievement Badges ✅ | Medium | Gamification |
| 48 | 6.2 Rating Challenges | Medium | Gamification |
| 49 | 6.3 Movie Bingo ✅ | Medium | Gamification |
| 50 | 7.3 Movie Connections / Six Degrees ✅ | Medium | Movie Detail |
| 51 | 7.4 Movie DNA Breakdown ✅ | Low-Med | Movie Detail |
| 52 | 1.10 Multi-Criteria Discovery | Medium | Discovery |
| 53 | 1.11 Complete the Collection | Medium | Discovery |
| 54 | 9.1 Quick Rate Onboarding ✅ | Medium | Onboarding |
| 55 | 9.5 Import/Export Ratings | Medium | Onboarding |
| 56 | 9.6 Tastemaker Score | Medium | Onboarding |

---

## Data Dependency Summary

| Data Source | Already Imported | Features It Powers |
|-------------|-----------------|-------------------|
| movies.title | Yes | Search, autocomplete, explanations |
| movies.overview | Yes | Embeddings, semantic search, mood discovery |
| movies.genres (JSONB) | Yes | Genre charts, filters, radar, challenges, bingo, explanations |
| movies.keywords (JSONB) | Yes | Tag cloud, keyword search, movie DNA, bingo |
| movies.cast_names (JSONB) | Yes | Actor filmography, cast search, explanations, connections |
| movies.director | Yes | Director spotlight, filmography gaps, explanations, connections |
| movies.release_date | Yes | Decade explorer, timeline, year filters, wrapped |
| movies.vote_average | Yes | Hidden gems, top charts, community sentiment |
| movies.vote_count | Yes | Hidden gems filtering, popularity signals |
| movies.popularity | Yes | Trending supplement, sorting |
| movies.poster_path | Yes | All movie display cards |
| movies.embedding (384d) | Yes | Similar movies, semantic search, mood, watchlist recs, movie DNA |
| ratings.rating | Yes | All stats, charts, achievements, compatibility, trending |
| ratings.timestamp | Yes | Diary, streaks, wrapped, taste evolution, popularity timeline |
| watchlist.movie_id | Yes | Watchlist recs, watch together |
| ALS user_factors (128d) | Yes | Compatibility, soulmate, collab recs, surprise me |
| ALS item_factors (128d) | Yes | Collab recs, movie similarity (behavioral), predicted match % |
| movies.imdb_id | Yes | Rating import/export (IMDb CSV mapping) |
| movies.tmdb_id | Yes | Rating import/export (Letterboxd CSV mapping) |
| TMDb runtime | **No** (in raw CSV) | Runtime filter, watch time stats, bingo, wrapped |
| TMDb original_language | **Yes** (imported) | Language filter, international discovery |
| TMDb tagline | **No** (in raw CSV) | Richer movie cards, search enhancement |
| TMDb budget/revenue | **No** (in raw CSV) | Sleeper hits, ROI lists, box office insights |
