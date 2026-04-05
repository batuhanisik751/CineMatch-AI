# CineMatch-AI

A hybrid movie recommendation engine that combines content-based filtering, collaborative filtering, and optional LLM re-ranking to deliver personalized movie discovery. Built with FastAPI, PostgreSQL + pgvector, and local ML models. Runs locally or deployed with free-tier cloud services.

> **29K movies | 162K users | 24.7M ratings | 384-dim embeddings | 85+ API endpoints**

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Features](#features)
- [How It Works](#how-it-works)
- [Getting Started](#getting-started)
- [Running the App](#running-the-app)
- [Data Pipeline](#data-pipeline)
- [API Overview](#api-overview)
- [Frontend Pages](#frontend-pages)
- [Project Structure](#project-structure)
- [Evaluation](#evaluation)
- [License](#license)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **API** | FastAPI (Python 3.11+), Pydantic v2 |
| **Database** | PostgreSQL 16 + pgvector + pg_trgm |
| **ORM** | SQLAlchemy 2.0 (async) + asyncpg + Alembic |
| **Vector Search** | pgvector (primary) + FAISS (batch operations) |
| **Embeddings** | sentence-transformers / all-MiniLM-L6-v2 (384-dim) |
| **Collaborative Filtering** | implicit ALS (matrix factorization) |
| **Caching** | Redis 7 |
| **LLM** | Ollama (local) or Groq (cloud, free tier) — optional |
| **Frontend** | React 18 + TypeScript + Vite + Tailwind CSS + Recharts |
| **Rate Limiting** | slowapi (Redis-backed, per-endpoint tiers) |
| **Reverse Proxy** | Caddy 2 (automatic HTTPS / Let's Encrypt) |
| **Infrastructure** | Docker Compose (PostgreSQL + Redis), production compose with Caddy |

### Data Sources

- [MovieLens ml-25m](https://grouplens.org/datasets/movielens/25m/) -- 25M ratings from 162K users across 62K movies
- [TMDb Metadata (Kaggle)](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset) -- overviews, genres, keywords, cast, crew

---

## Features

### Recommendations

| Feature | Description |
|---------|-------------|
| **Hybrid Engine** | Blends content similarity + collaborative filtering with configurable alpha |
| **Diversity Controls** | Safe / Balanced / Adventurous modes via MMR re-ranking |
| **LLM Re-ranking** | LLM re-ranks top 50 candidates for thematic diversity (falls back to MMR) |
| **"More Like This"** | Seed any movie to get personalized similar recommendations |
| **Mood Discovery** | 9 preset moods + custom vibe input, blended with user taste |
| **Watchlist Recs** | Recommendations based on your saved-for-later movies |
| **Predicted Match %** | Netflix-style match badge on every movie card |
| **"Why This?"** | LLM-powered natural language explanations for recommendations |
| **Smart Explanations** | Always-on lightweight tags ("Because you liked X", score breakdowns) |
| **Cold-Start Handling** | New users automatically get content-only recommendations |

### Discovery

| Feature | Description |
|---------|-------------|
| **Title Search** | Fuzzy, typo-tolerant search with pg_trgm fallback |
| **Autocomplete** | Real-time suggestions as you type (Redis-cached) |
| **Semantic Search** | Search by vibe or description ("dark thriller in space") |
| **Advanced Filters** | Genre, decade, rating, director, keyword, cast, language, runtime |
| **Trending** | Movies with recent popularity spikes |
| **Hidden Gems** | High quality, low attention films |
| **Top Charts** | Genre-specific highest-rated movies |
| **Decade Explorer** | Browse film history by era |
| **Seasonal** | Movies themed to the current season |
| **Controversial** | Polarizing community favorites |
| **Keyword Explorer** | Tag cloud of crowd-sourced keywords (time travel, heist, dystopia...) |
| **Thematic Collections** | Auto-generated collections (genre+decade combos, director filmographies, yearly rankings) |

### People

| Feature | Description |
|---------|-------------|
| **Director Spotlight** | Search directors, view filmographies with your ratings overlaid |
| **Actor Explorer** | Browse actors, select multiple to find movies they share |
| **Cast Combo Search** | Find movies where 2-5 specific actors appear together |
| **Director & Actor Gaps** | Unseen films from your favorite creators |
| **Complete the Collection** | Unrated movies by directors/actors you've rated 3+ films for |

### Personalization & Analytics

| Feature | Description |
|---------|-------------|
| **Taste Profile** | Natural language summary of your movie personality |
| **Taste Evolution** | Stacked area chart of genre preferences over time |
| **Rating Comparison** | Your ratings vs. community averages with agreement % |
| **Director & Actor Affinity** | Ranked by enthusiasm (avg rating x engagement) |
| **Surprise Me** | Random picks outside your comfort zone |
| **Blind Spots** | Iconic movies you haven't seen yet |
| **Rewatch Suggestions** | Highly-rated movies worth revisiting |
| **Film Diary** | GitHub-style calendar heatmap of daily rating activity |
| **User Stats Dashboard** | Rating histogram, top directors/actors, monthly timeline |

### Gamification

| Feature | Description |
|---------|-------------|
| **12 Achievement Badges** | First Rating, Century Club, Genre Explorer, Director Devotee, Night Owl, and more |
| **Weekly Challenges** | 3 rotating challenges (genre, decade, director) every Monday |
| **Movie Bingo** | Monthly 5x5 card with row/column/diagonal completion |
| **Rating Streaks** | Consecutive-day tracking with milestone badges (10 to 1000) |

### User Management

| Feature | Description |
|---------|-------------|
| **Watchlist** | Save movies for later with bookmark buttons across all pages |
| **"Not Interested"** | Dismiss movies from all recommendation surfaces |
| **Custom Lists** | Named, ordered, public/private movie collections |
| **Import / Export** | Bring ratings from Letterboxd or IMDb via CSV |
| **Onboarding** | Rate 10-20 popular movies to bootstrap your taste profile |
| **Platform Stats** | Community-wide statistics dashboard |

### Security

| Feature | Description |
|---------|-------------|
| **JWT Authentication** | Register/login with email + password, bcrypt hashing, Bearer token auth |
| **HTTPS** | Caddy reverse proxy with automatic TLS / Let's Encrypt |
| **Rate Limiting** | Redis-backed per-endpoint limits (100/min global, 5/min auth, 10/min recommendations, 30/min search, 3/min CSV import) |
| **Credential Protection** | SecretStr for all sensitive config, no insecure defaults, Redis password auth |
| **Input Validation** | 200-ID cap on bulk endpoints, max_length on search queries, SHA-256 hashed cache keys, frontend auto-batching |
| **Security Headers** | X-Content-Type-Options, X-Frame-Options, HSTS, Content-Security-Policy, Referrer-Policy, Permissions-Policy on every response |
| **CORS Lockdown** | Configurable allowed origins, methods (`GET/POST/PATCH/PUT/DELETE/OPTIONS`), and headers (`Content-Type`, `Authorization`) — no wildcards in production |
| **Error Response Hardening** | Generic error messages in all API responses — no internal IDs, service names, stack traces, or Python exceptions leak to clients. Catch-all handler for unhandled errors. Full details logged server-side only |
| **Audit Logging** | Structured JSON audit trail for security events (login success/failure, registration, CSV import/export, authorization failures, rate limit hits). Dual-write to database + file. Per-user audit log viewer in the frontend |
| **Database Connection Security** | SSL/TLS support for PostgreSQL connections (5 modes: disable, prefer, require, verify-ca, verify-full), statement timeout to prevent slow-query DoS, connection pool hardening (recycle + pre-ping), limited-privilege database user for production, DB security dashboard in the frontend |
| **pgvector Query Safety** | All vector similarity queries use typed `bindparam(type_=Vector(384))` bindings instead of `str()` cast — prevents type confusion and ensures pgvector's native type adapter handles serialization. Verified via the DB security dashboard |
| **Pickle Deserialization Safety** | SHA-256 checksum verification for all pickle artifacts (FAISS ID map, ALS model, user/item maps). Checksums generated at training time, verified at startup — mismatch aborts launch. Frontend integrity dashboard at Profile > Pickle Safety |
| **Container Security** | Non-root containers (USER 1000), read-only root filesystems with tmpfs, `no-new-privileges` flag, capability dropping (`cap_drop: ALL` with targeted `cap_add`), multi-stage Docker builds, expanded `.dockerignore`, HEALTHCHECK directive. Frontend container security dashboard at Profile > Container Security |
| **Dependency Vulnerability Scanning** | On-demand scanning via pip-audit (PyPI vulnerability database), bandit (Python static security analysis), and safety. Backend endpoint runs tools as subprocesses with timeout handling and graceful degradation. Frontend dashboard at Profile > Dep Scan. GitHub Actions CI workflow runs pip-audit and bandit on every PR |

### Content Analysis (Per Movie)

| Feature | Description |
|---------|-------------|
| **Movie DNA** | Genre composition bar, keyword themes, decade, vibe tags |
| **Community Sentiment** | Rating histogram, avg/median, polarization score |
| **Popularity Timeline** | Area chart of rating activity over time |
| **Six Degrees** | Shared cast, directors, genres between any two movies |
| **Shortest Path** | BFS path-finding between movies through shared people |
| **Side-by-Side Compare** | Pick two movies and compare everything |

---

## How It Works

```
User rates movies
       |
       v
+------+------+                    +-----------------+
| Collaborative |                    |  Content-Based  |
|  Filtering    |                    |   Filtering     |
|  (ALS)        |                    |  (Embeddings)   |
+------+--------+                    +--------+--------+
       |                                      |
       +------ Hybrid Scoring ----------------+
               alpha * content + (1-alpha) * collab
                          |
                  Franchise Penalty
                          |
                  MMR Diversity Re-ranking
                          |
                  LLM Re-ranking (optional)
                          |
                     Top 20 Results
                  with explanations
```

1. **Content-Based:** Movie text (overview + genres + keywords) is encoded into 384-dim vectors. Similar movies are found via cosine similarity using pgvector and FAISS.
2. **Collaborative:** The user-item rating matrix is factorized with ALS. Users with similar taste patterns get similar recommendations.
3. **Hybrid Scoring:** Both scores are normalized and combined: `alpha * content + (1-alpha) * collab` (default 0.5). Cold-start users automatically fall back to content-only.
4. **Franchise Penalty:** Sequels and franchise entries are detected and downranked to prevent clustering.
5. **MMR Diversity:** Maximal Marginal Relevance ensures results span different genres, not just the most similar.
6. **LLM Re-ranking:** An LLM (Ollama locally or Groq cloud) optionally re-ranks the top 50 candidates for deeper thematic diversity and taste matching.

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker + Docker Compose
- Ollama (optional, for local LLM) or a free Groq API key (for cloud LLM)

### Installation

```bash
# 1. Clone and set up Python environment
git clone https://github.com/your-username/CineMatch-AI.git
cd CineMatch-AI
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pip install psycopg2-binary

# 2. Start infrastructure
docker compose up -d

# 3. Configure environment
cp .env.example .env
# Edit the REQUIRED section at the bottom of .env:
#   - Set POSTGRES_PASSWORD and REDIS_PASSWORD
#   - Update CINEMATCH_DATABASE_URL and CINEMATCH_REDIS_URL to match
#   - Generate CINEMATCH_SECRET_KEY: python -c "import secrets; print(secrets.token_urlsafe(64))"

# 4. Run database migrations
alembic upgrade head

# 5. Download datasets
python scripts/download_data.py
# TMDb: download manually from Kaggle and place in data/raw/tmdb/
# Or: pip install kaggle && kaggle datasets download -d rounakbanik/the-movies-dataset -p data/raw/tmdb/ --unzip

# 6. Run data pipeline (~10 min)
PYTHONPATH=src python scripts/train_models.py

# 7. Seed database (~15 min)
PYTHONPATH=src python scripts/seed_db.py

# 8. Install frontend
cd frontend && npm install && cd ..
```

### Optional: LLM Setup

**Option A: Groq (cloud, recommended for deployment)**

1. Sign up at [console.groq.com](https://console.groq.com) (free, no credit card)
2. Create an API key
3. Set in `.env`:
```env
CINEMATCH_LLM_BACKEND=groq
CINEMATCH_LLM_MODEL_NAME=llama-3.1-8b-instant
CINEMATCH_LLM_BASE_URL=https://api.groq.com
CINEMATCH_LLM_API_KEY=gsk_your_key_here
```

**Option B: Ollama (local)**

```bash
brew install ollama
ollama serve          # keep running in a separate terminal
ollama pull mistral
```

Set `CINEMATCH_LLM_ENABLED=true` in `.env`. If neither backend is reachable, the app still works -- recommendations use algorithmic MMR diversity instead.

---

## Running the App

Open 3 terminals:

**Terminal 1 -- Backend API**
```bash
source .venv/bin/activate
PYTHONPATH=src uvicorn cinematch.main:app --reload --host 0.0.0.0 --port 8000
```
API docs at http://localhost:8000/docs (requires `CINEMATCH_DEBUG=true`)

**Terminal 2 -- Frontend**
```bash
cd frontend && npm run dev
```
Opens at http://localhost:3000

**Terminal 3 -- Ollama (optional, only if using local LLM)**
```bash
ollama serve
```

Docker services run in the background (`docker compose up -d`). If using Groq, no third terminal is needed.

### Production Deployment

The production stack runs everything in Docker behind a Caddy reverse proxy with automatic HTTPS.

```bash
# 1. Build frontend and Docker images
make prod-build

# 2. Configure production environment
cp .env.example .env
# Edit .env: set strong POSTGRES_PASSWORD, REDIS_PASSWORD, CINEMATCH_SECRET_KEY,
# CINEMATCH_DOMAIN, and update CINEMATCH_DATABASE_URL / CINEMATCH_REDIS_URL to match

# 3. Start production stack
make prod-up
# App available at https://localhost (self-signed cert)
# or https://your-domain.com (auto Let's Encrypt cert)

# 4. View logs
make prod-logs

# 5. Stop
make prod-down
```

In production, only Caddy is exposed on ports 80/443. PostgreSQL, Redis, and the app are on an internal Docker network with no host port exposure. PostgreSQL runs with SSL enabled (self-signed cert) and a limited-privilege `cinematch_app` user (DML-only, no DDL or superuser). All containers run with `no-new-privileges`, `cap_drop: ALL` (with targeted `cap_add` where needed), and read-only root filesystems (tmpfs for `/tmp`). The app container runs as non-root (UID 1000).

---

## Data Pipeline

```
MovieLens ml-25m ---+
                    +---> Clean & Join ---> Embed ---> FAISS Index ---> Seed DB
TMDb Metadata ------+                                     |
                                                     Train ALS
```

| Step | Command | Output |
|------|---------|--------|
| Download | `python scripts/download_data.py` | `data/raw/ml-25m/`, `data/raw/tmdb/` |
| Clean & Join | `pipeline/cleaner.py` | `movies_clean.parquet`, `ratings_clean.parquet` |
| Embed | `pipeline/embedder.py` | `embeddings.npy` (29K x 384) |
| Build FAISS | `pipeline/faiss_builder.py` | `faiss.index`, `faiss_id_map.pkl`, `faiss_id_map.pkl.sha256` |
| Train ALS | `pipeline/collaborative.py` | `als_model.pkl`, mappings, sparse matrix, `.sha256` checksums |
| Seed DB | `python scripts/seed_db.py` | PostgreSQL tables + IVFFlat vector index |
| Evaluate | `python -m cinematch.evaluation.evaluate` | `evaluation_report.json` |

Run the full pipeline: `PYTHONPATH=src python scripts/train_models.py`

---

## API Overview

The REST API is organized into 10 endpoint groups with 85+ routes. Full interactive docs at `/docs` (requires `CINEMATCH_DEBUG=true`; disabled in production).

### Movies (`/api/v1/movies`)
Search, browse, filter, and analyze movies. Includes title search, autocomplete, semantic search, discover with filters, trending, hidden gems, top charts, decades, directors, actors, cast combos, keywords, advanced multi-criteria search, thematic collections, movie DNA, rating stats, popularity timeline, connections, path finding, and side-by-side comparison.

### Recommendations (`/api/v1/users/{id}/recommendations`)
Hybrid, content-only, or collaborative recommendations. Mood-based discovery. "More Like This" from any seed movie. LLM-powered explanations.

### Ratings (`/api/v1/users/{id}/ratings`)
Add/update ratings, view history, bulk check, import from Letterboxd/IMDb CSV, export as CSV.

### Predictions (`/api/v1/users/{id}/predicted-rating`)
Predicted match percentage for single or batch (up to 100) movies.

### Watchlist (`/api/v1/users/{id}/watchlist`)
Add, remove, list, bulk check. Watchlist-based recommendations.

### Dismissals (`/api/v1/users/{id}/dismissals`)
"Not Interested" feedback. Dismissed movies are filtered from all recommendation surfaces.

### Lists (`/api/v1/users/{id}/lists`)
Full CRUD for custom movie collections. Add/remove/reorder items. Browse popular public lists.

### Users (`/api/v1/users/{id}`)
Profile stats, film diary, personalized feed, surprise mode, completions, director/actor gaps, rewatch suggestions, taste profile, affinities, rating comparison, streaks, achievements, challenges, blind spots.

### Challenges (`/api/v1/challenges`)
Weekly rotating challenges (genre, decade, director).

### Platform (`/api/v1`)
Onboarding movies/status, global platform statistics, health check.

---

## Frontend Pages

### Main Sections

| Page | Description |
|------|-------------|
| **Home** | Personalized feed with mood carousel, trending, hidden gems, surprise me, rewatch suggestions |
| **Onboarding** | New user flow -- rate popular movies to bootstrap taste |

### Search

| Page | Description |
|------|-------------|
| **Search** | Unified search with title, semantic vibe, and advanced filter modes |

### Discover

| Page | Description |
|------|-------------|
| **Browse** | Multi-criteria filtering (genre, year, language, runtime, sort) |
| **Trending** | Movies with recent popularity spikes |
| **Top Charts** | Genre-tab selector for highest-rated movies |
| **Hidden Gems** | High quality, low attention films |
| **Seasonal** | Season and month themed movies |
| **Controversial** | Polarizing community favorites |
| **Decades** | Explore film history by era with genre filtering |

### Explore

| Page | Description |
|------|-------------|
| **Actors** | Search actors, view filmographies, multi-select for cast combos |

### For You

| Page | Description |
|------|-------------|
| **Recommendations** | Hybrid/content/collab with diversity controls |
| **Blind Spots** | Popular movies you haven't seen |
| **Rewatch** | Movies worth revisiting |

### Library

| Page | Description |
|------|-------------|
| **Watchlist** | Saved movies with bookmark management |
| **Lists** | Custom named collections (CRUD, public/private) |
| **Collections** | Auto-generated thematic collections |

### Profile & Activity

| Page | Description |
|------|-------------|
| **Overview** | Stats, taste profile, achievements, streaks, rating comparison |
| **Taste Evolution** | Genre preference changes over time (stacked area chart) |
| **Platform Stats** | Community-wide statistics dashboard |
| **Audit Log** | Personal security activity trail with action/status filters |
| **DB Security** | Database connection security dashboard (SSL status, statement timeout, pool stats, connection info, pgvector query safety) |
| **Pickle Safety** | ML artifact integrity dashboard — SHA-256 checksum verification status for all pickle files |
| **Container Security** | Docker container runtime security posture — non-root check, read-only filesystem, capabilities, no-new-privileges, multi-stage build verification |
| **Dep Scan** | Dependency vulnerability scanning — pip-audit CVEs, bandit static analysis findings, safety check, overall status with severity badges |
| **Achievements** | 12 badge collection with progress bars |
| **Challenges** | Weekly rating challenges with progress tracking |
| **Bingo** | Monthly 5x5 movie bingo card |
| **Diary** | GitHub-style calendar heatmap of daily activity |

### Detail Pages

| Page | Description |
|------|-------------|
| **Movie Detail** | Full movie info, DNA, sentiment, timeline, similar, connections |
| **Compare** | Side-by-side movie comparison |
| **More Like This** | Seed-based personalized recommendations |
| **Watchlist Recs** | Recommendations from your watchlist |
| **List Detail** | View and manage a single list |
| **Popular Lists** | Browse public community lists |

---

## Project Structure

```
src/cinematch/
  api/v1/             REST endpoints (movies, ratings, recommendations, users,
                      watchlist, dismissals, lists, predictions, challenges, stats)
  services/           Business logic (25 services -- recommendation engines,
                      discovery, analytics, gamification, import/export)
  models/             SQLAlchemy ORM (movies, users, ratings, watchlist,
                      dismissals, user_lists, user_list_items)
  schemas/            Pydantic v2 request/response validation
  pipeline/           Offline data processing (cleaner, embedder, FAISS, ALS)
  evaluation/         Recommendation quality metrics (Precision, Recall, NDCG, MAP)
  core/               Cache, exceptions, logging, rate limiting, security headers middleware
  db/                 Database engine, sessions, Alembic migrations
  config.py           Environment-based settings (CINEMATCH_ prefix)
  main.py             FastAPI app factory with lifespan

frontend/src/
  pages/              React pages (home, discover, search, for-you, library,
                      profile, activity, explore, movie detail, compare)
  components/         Reusable UI (MovieCard, MoodCarousel, StarRating,
                      AutocompleteSearch, MovieDNA, modals)

scripts/              download_data.py, train_models.py, seed_db.py
docker/               Production Docker config (PostgreSQL SSL init, limited-privilege user)
tests/                pytest suite mirroring src/ structure
```

---

## Evaluation

```bash
python -m cinematch.evaluation.evaluate
```

Uses a temporal 80/20 train/test split and computes:
- **Precision@K** -- fraction of recommended items that are relevant
- **Recall@K** -- fraction of relevant items that are recommended
- **NDCG@K** -- ranking quality with position-weighted relevance
- **MAP@K** -- mean average precision across users

Results are saved to `data/processed/evaluation_report.json`.

---

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
make prod-build # Build frontend + production Docker images
make prod-up    # Start production stack (HTTPS via Caddy)
make prod-down  # Stop production stack
make prod-logs  # Tail production logs
```

---

## License

MIT
