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

Features: movie discovery with genre/year/sort filters, title search with typo tolerance, semantic "vibe" search by description, mood-based discovery (preset moods + custom vibe input, personalized by blending mood with user taste), hybrid/content/collab recommendations with smart explanation tags ("Because you liked Inception", "Same director as Interstellar — Christopher Nolan", content vs. collab score breakdown bar), "Why This?" deep-dive explanation button (powered by Mistral), **Top Charts** (genre-tab selector showing the highest community-rated movies per genre, ranked by in-system average with numbered badges), rating history with movie names, watchlist/save-for-later with bookmark buttons across all pages, profile analytics dashboard with rating histogram, top directors/actors, and monthly activity timeline.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1/movies/{id}` | Movie details |
| GET | `/api/v1/movies/search?q=&limit=20` | Search movies by title (fuzzy/typo-tolerant) |
| GET | `/api/v1/movies/semantic-search?q=&limit=20` | Semantic "vibe" search by description (e.g., "dark thriller in space") |
| GET | `/api/v1/movies/discover?genre=&sort_by=popularity&year_min=&year_max=&offset=0&limit=20` | Browse movies with filters and pagination |
| GET | `/api/v1/movies/genres` | All genres with movie counts |
| GET | `/api/v1/movies/top?genre=Drama&limit=20` | Top-rated movies for a genre, ranked by community avg rating (min 50 ratings) |
| GET | `/api/v1/movies/{id}/similar?top_k=20` | Content-similar movies |
| GET | `/api/v1/users/{id}` | User details |
| GET | `/api/v1/users/{id}/stats` | User profile analytics (rating histogram, top directors/actors, timeline) |
| GET | `/api/v1/users/{id}/recommendations?top_k=20&strategy=hybrid` | Recommendations with smart explanations (strategy: `hybrid`, `content`, `collab`) |
| POST | `/api/v1/recommendations/mood` | Mood-based discovery (body: `{"mood": "dark gritty thriller", "user_id": 1, "alpha": 0.3, "limit": 20}`) |
| GET | `/api/v1/users/{id}/recommendations/explain/{movie_id}?score=0.9` | LLM explanation for a recommendation |
| POST | `/api/v1/users/{id}/ratings` | Add/update a rating (body: `{"movie_id": 1, "rating": 4.5}`) |
| GET | `/api/v1/users/{id}/ratings?offset=0&limit=20` | User's ratings (paginated) |
| POST | `/api/v1/users/{id}/watchlist` | Add to watchlist (body: `{"movie_id": 1}`) |
| DELETE | `/api/v1/users/{id}/watchlist/{movie_id}` | Remove from watchlist |
| GET | `/api/v1/users/{id}/watchlist?offset=0&limit=20` | User's watchlist (paginated, with movie details) |
| GET | `/api/v1/users/{id}/watchlist/check?movie_ids=1,2,3` | Bulk check which movies are in watchlist |

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
7. **MMR Fallback:** If the LLM is unavailable, Maximal Marginal Relevance (MMR) with genre Jaccard similarity ensures diversity algorithmically.
8. **Smart Explanations:** Every recommendation includes lightweight, always-available explanation metadata — no LLM required. Three levels: (a) seed influence tracking ("Because you liked Inception"), (b) feature-based templates comparing genres, directors, and cast against the user's top-rated movies, and (c) score decomposition showing the content vs. collaborative contribution breakdown.
9. **Fuzzy Search:** Movie search uses ILIKE for exact matches, with automatic pg_trgm fuzzy fallback for typos (e.g., "Casr" finds "Cars").
10. **Semantic "Vibe" Search:** Users can search by mood or description (e.g., "funny movie about time travel"). The query text is embedded using the same sentence-transformer model and matched against movie embeddings via pgvector cosine similarity. No LLM needed — pure vector search.
11. **Mood-Based Discovery:** Users pick a mood preset (e.g., "Feel-Good", "Mind-Bending", "Edge of Your Seat") or type a custom vibe. The mood text is embedded, then blended with the user's taste vector (weighted average of their top-rated movies' embeddings): `query = alpha * taste + (1-alpha) * mood`. The blended vector is L2-normalized and searched via FAISS. Cold-start users get pure mood results. Alpha defaults to 0.3 (mood-weighted with light personalization).
12. **Strategies:** The API supports three modes — `hybrid` (default), `content` (content-only), and `collab` (collaborative-only). Cold-start users (not in ALS training data) get a 400 error on `collab` with guidance to use `hybrid` or `content` instead. The `hybrid` strategy handles cold-start automatically by falling back to content-only.

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
| `top_charts:{genre}:{limit}` | 6 hours | Manual |
| `movie:{id}` | 1 hour | Manual |
| `similar:{id}:{top_k}` | 30 min | Never (content similarity is stable) |
| `recs:{user_id}:{strategy}:{top_k}` | 15 min | On new rating from this user |
| `mood_rec:{user_id}:{mood_hash}:{alpha}:{limit}` | 10 min | On new rating from this user |
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
│       ├── movies.py             # GET /{id}, /search, /semantic-search, /discover, /genres, /{id}/similar
│       ├── ratings.py            # POST/GET /users/{id}/ratings
│       ├── recommendations.py    # GET /users/{id}/recommendations, POST /recommendations/mood
│       ├── users.py              # GET /users/{id}, /users/{id}/stats
│       ├── watchlist.py          # POST/DELETE/GET /users/{id}/watchlist
│       └── router.py             # Aggregated v1 router
├── services/        # Business logic
│   ├── embedding_service.py      # sentence-transformers wrapper
│   ├── content_recommender.py    # pgvector + FAISS similarity search
│   ├── collab_recommender.py     # ALS collaborative filtering
│   ├── hybrid_recommender.py     # Combined scoring + franchise penalty + MMR + LLM re-ranking
│   ├── movie_service.py          # Movie DB queries (get, search, discover, genres, batch)
│   ├── rating_service.py         # Rating DB queries (upsert, list with movie titles)
│   ├── user_stats_service.py     # User profile analytics (genre, rating, director/actor stats)
│   ├── watchlist_service.py      # Watchlist CRUD (add, remove, list, bulk check)
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
