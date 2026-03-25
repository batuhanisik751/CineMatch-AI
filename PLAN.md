# CineMatch-AI: Complete Implementation Plan

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Tech Stack](#3-tech-stack)
4. [Project Structure](#4-project-structure)
5. [Database Schema](#5-database-schema)
6. [Data Flow](#6-data-flow)
7. [Data Pipeline](#7-data-pipeline)
8. [Embedding System](#8-embedding-system)
9. [Collaborative Filtering](#9-collaborative-filtering)
10. [Hybrid Recommendation Engine](#10-hybrid-recommendation-engine)
11. [API Design](#11-api-design)
12. [Caching & Optimization](#12-caching--optimization)
13. [Evaluation Framework](#13-evaluation-framework)
14. [Optional LLM Integration](#14-optional-llm-integration)
15. [Configuration Management](#15-configuration-management)
16. [Infrastructure (Docker)](#16-infrastructure-docker)
17. [Testing Strategy](#17-testing-strategy)
18. [Step-by-Step Implementation Roadmap](#18-step-by-step-implementation-roadmap)

---

## 1. Project Overview

**Goal**: Build a movie recommendation application that suggests movies to users using a hybrid recommendation system combining:
- **Content-based filtering** -- uses movie metadata (overview, genres, keywords) encoded as vector embeddings to find similar movies
- **Collaborative filtering** -- uses user rating patterns to find users with similar taste and recommend what they liked

**Constraints**:
- No paid APIs or API keys -- the system runs fully locally
- Only free and open-source tools, datasets, and models
- Production-like architecture: clean separation of concerns, scalable design, proper error handling

**Data Sources**:
- **MovieLens ml-25m** (https://grouplens.org/datasets/movielens/25m/) -- 25 million user ratings from 162,000 users on 62,000 movies. Provides `ratings.csv`, `movies.csv`, `links.csv` (which maps MovieLens IDs to TMDb/IMDb IDs).
- **TMDb metadata from Kaggle** ("The Movies Dataset" on Kaggle) -- contains `movies_metadata.csv`, `keywords.csv`, `credits.csv` with rich movie information: overviews, genres, keywords, cast, crew, popularity scores, and more.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT (curl / frontend)                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP
┌──────────────────────────────▼──────────────────────────────────────┐
│                        FastAPI Backend (uvicorn)                      │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                      API Layer (api/v1/)                     │    │
│  │  movies.py │ ratings.py │ recommendations.py │ users.py      │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
│                              │                                       │
│  ┌──────────────────────────▼──────────────────────────────────┐    │
│  │                     Service Layer (services/)                │    │
│  │                                                              │    │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │    │
│  │  │ MovieService │  │RatingService │  │HybridRecommender │   │    │
│  │  └─────────────┘  └──────────────┘  └────────┬─────────┘   │    │
│  │                                               │              │    │
│  │                          ┌────────────────────┼──────────┐  │    │
│  │                          │                    │          │  │    │
│  │               ┌──────────▼───┐  ┌─────────────▼──┐      │  │    │
│  │               │   Content    │  │  Collaborative │      │  │    │
│  │               │ Recommender  │  │  Recommender   │      │  │    │
│  │               └──────┬───┬──┘  └───────┬────────┘      │  │    │
│  │                      │   │             │                │  │    │
│  │           ┌──────────┘   └──────┐      │                │  │    │
│  │           │                     │      │                │  │    │
│  │  ┌────────▼─────┐  ┌───────────▼──┐  ┌▼────────────┐  │  │    │
│  │  │EmbeddingServ.│  │  FAISS Index │  │  ALS Model  │  │  │    │
│  │  │(MiniLM-L6)  │  │  (in-memory) │  │  (implicit) │  │  │    │
│  │  └──────────────┘  └──────────────┘  └─────────────┘  │  │    │
│  └───────────────────────────────────────────────────────────┘    │
│                              │                                       │
│  ┌───────────────────────────▼─────────────────────────────────┐    │
│  │                     Data Layer                               │    │
│  │   ┌──────────────────┐        ┌──────────────┐             │    │
│  │   │   PostgreSQL     │        │    Redis     │             │    │
│  │   │   + pgvector     │        │   (cache)   │             │    │
│  │   │                  │        │              │             │    │
│  │   │  - movies table  │        │  - movie     │             │    │
│  │   │  - users table   │        │    details   │             │    │
│  │   │  - ratings table │        │  - similar   │             │    │
│  │   │  - recs cache    │        │    movies    │             │    │
│  │   │  - vector index  │        │  - user recs │             │    │
│  │   └──────────────────┘        └──────────────┘             │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘

OFFLINE DATA PIPELINE (run once, then periodically):
┌────────────────┐    ┌───────────────┐    ┌──────────────────┐
│  MovieLens     │    │   TMDb        │    │                  │
│  ml-25m        │───►│   Metadata    │───►│  Clean & Join    │
│  (ratings.csv  │    │   (Kaggle)    │    │  (cleaner.py)    │
│   links.csv)   │    │   (metadata,  │    │                  │
│                │    │    keywords,  │    └────────┬─────────┘
│                │    │    credits)   │             │
└────────────────┘    └───────────────┘             │
                                          ┌─────────▼──────────┐
                                          │                    │
                              ┌───────────┤  Processed Data    │
                              │           │  (parquet files)   │
                              │           └────────────────────┘
                              │
               ┌──────────────┼──────────────┬──────────────────┐
               │              │              │                  │
      ┌────────▼─────┐ ┌─────▼──────┐ ┌─────▼──────┐  ┌───────▼──────┐
      │  Embed       │ │ Build      │ │ Train      │  │ Seed         │
      │  (MiniLM)   │ │ FAISS      │ │ ALS Model  │  │ PostgreSQL   │
      │  embedder.py │ │ Index      │ │ collab.py  │  │ seed_db.py   │
      └──────────────┘ └────────────┘ └────────────┘  └──────────────┘
```

**Data flow summary**:
1. Raw datasets are downloaded and placed in `data/raw/`
2. The cleaner joins MovieLens and TMDb data via `links.csv` (which maps `movieId` to `tmdbId`)
3. The embedder generates 384-dimensional vectors for each movie's text
4. FAISS index is built from embeddings for fast in-memory similarity search
5. ALS model is trained on the user-item rating matrix
6. All structured data + embeddings are loaded into PostgreSQL
7. At runtime, the API serves recommendations by combining content similarity (pgvector/FAISS) with collaborative scores (ALS)

---

## 3. Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| **Language** | Python 3.11+ | ML ecosystem, async support, FastAPI compatibility |
| **Web Framework** | FastAPI | Async-native, auto OpenAPI docs, Pydantic integration, high performance |
| **Database** | PostgreSQL 16 | Robust, JSONB support, mature ecosystem |
| **Vector Search (primary)** | pgvector | Keeps vectors in the same DB as structured data, transactional consistency |
| **Vector Search (batch)** | FAISS (faiss-cpu) | Facebook's library for fast in-memory similarity search, used for batch evaluation and offline operations |
| **ORM** | SQLAlchemy 2.0 (async) | Modern async API, Alembic migrations, type-safe queries |
| **DB Driver** | asyncpg | Fastest async PostgreSQL driver for Python |
| **Embeddings** | sentence-transformers/all-MiniLM-L6-v2 | 384-dim embeddings, ~80MB model, fast inference (~1000 sentences/sec on CPU), no GPU required |
| **Collaborative Filtering** | implicit (ALS) | C++ backed Alternating Least Squares, handles millions of ratings efficiently |
| **Caching** | Redis 7 | In-memory key-value store for caching API responses |
| **Migrations** | Alembic | SQLAlchemy-native migration tool, auto-generates diffs |
| **Config** | pydantic-settings | Type-safe configuration from environment variables |
| **Data Processing** | pandas + pyarrow | Efficient DataFrame ops, parquet for intermediate storage |
| **Optional LLM** | Mistral 7B via Ollama | Local LLM for natural language explanations, NOT used for embeddings |

---

## 4. Project Structure

```
CineMatch-AI/
│
├── .gitignore                          # Python + data + env ignores
├── LICENSE
├── README.md
├── PLAN.md                             # This file
├── pyproject.toml                      # Project metadata, all dependencies, scripts, tool config
├── Makefile                            # Convenience commands for common operations
├── docker-compose.yml                  # PostgreSQL (pgvector) + Redis containers
├── alembic.ini                         # Alembic migration configuration
├── .env.example                        # Template for environment variables
│
├── data/                               # *** GITIGNORED *** -- all data lives here
│   ├── raw/                            # Downloaded datasets (MovieLens zip, Kaggle CSVs)
│   │   ├── ml-25m/                     # Extracted MovieLens files
│   │   │   ├── ratings.csv             # 25M ratings (userId, movieId, rating, timestamp)
│   │   │   ├── movies.csv              # Movie titles and genres
│   │   │   └── links.csv               # movieId -> tmdbId, imdbId mapping
│   │   └── tmdb/                       # Kaggle "The Movies Dataset"
│   │       ├── movies_metadata.csv     # ~45K movies with overview, genres, vote_average, etc.
│   │       ├── keywords.csv            # Movie keywords as JSON
│   │       └── credits.csv             # Cast and crew as JSON
│   └── processed/                      # Pipeline output artifacts
│       ├── movies_clean.parquet        # Cleaned, joined movie metadata
│       ├── ratings_clean.parquet       # Cleaned ratings with consistent IDs
│       ├── id_mapping.parquet          # MovieLens ID <-> TMDb ID <-> internal ID mapping
│       ├── embeddings.npy              # Numpy array of shape (N, 384)
│       ├── faiss.index                 # FAISS IndexFlatIP for similarity search
│       ├── faiss_id_map.pkl            # Ordered movie ID list matching FAISS internal indices
│       ├── als_model.pkl               # Trained ALS model (implicit library)
│       ├── als_user_map.pkl            # user_id -> matrix_index mapping
│       ├── als_item_map.pkl            # movie_id -> matrix_index mapping
│       ├── als_user_items.npz          # Sparse user-item matrix (for recommend calls)
│       └── evaluation_report.json      # Metrics comparison output
│
├── scripts/                            # Standalone scripts for pipeline operations
│   ├── download_data.py                # Download MovieLens ml-25m; print Kaggle instructions
│   ├── seed_db.py                      # Load processed data into PostgreSQL
│   └── train_models.py                 # Train ALS model, build FAISS index
│
├── src/
│   └── cinematch/                      # Main Python package
│       ├── __init__.py                 # Package version
│       ├── main.py                     # FastAPI application factory with lifespan events
│       ├── config.py                   # Pydantic Settings class (reads .env)
│       │
│       ├── db/                         # Database layer
│       │   ├── __init__.py
│       │   ├── session.py              # create_async_engine, async_sessionmaker, get_db dependency
│       │   ├── base.py                 # DeclarativeBase with pgvector Vector type registered
│       │   └── migrations/             # Alembic migrations directory
│       │       ├── env.py              # Alembic environment config (async support)
│       │       ├── script.py.mako      # Migration template
│       │       └── versions/           # Auto-generated migration scripts
│       │           └── 001_initial.py  # First migration: pgvector extension + all tables + indexes
│       │
│       ├── models/                     # SQLAlchemy ORM models (one file per table)
│       │   ├── __init__.py             # Re-exports all models for Alembic discovery
│       │   ├── movie.py                # Movie model with VECTOR(384) column
│       │   ├── user.py                 # User model
│       │   ├── rating.py               # Rating model with composite unique constraint
│       │   └── recommendation.py       # RecommendationsCache model
│       │
│       ├── schemas/                    # Pydantic v2 request/response models
│       │   ├── __init__.py
│       │   ├── movie.py                # MovieResponse, MovieDetail, MovieSearchResult
│       │   ├── user.py                 # UserResponse
│       │   ├── rating.py               # RatingCreate, RatingResponse
│       │   └── recommendation.py       # RecommendationResponse, ExplanationResponse
│       │
│       ├── api/                        # API routes
│       │   ├── __init__.py
│       │   ├── deps.py                 # Dependency injection: get_db, get_services
│       │   └── v1/                     # Version 1 API
│       │       ├── __init__.py
│       │       ├── router.py           # Aggregates all v1 sub-routers under /api/v1
│       │       ├── movies.py           # GET /movies/{id}, GET /movies/search, GET /movies/{id}/similar
│       │       ├── users.py            # User-related endpoints
│       │       ├── ratings.py          # POST /users/{id}/ratings, GET /users/{id}/ratings
│       │       └── recommendations.py  # GET /users/{id}/recommendations, GET .../explain/{movie_id}
│       │
│       ├── services/                   # Business logic layer (stateful services loaded at startup)
│       │   ├── __init__.py
│       │   ├── movie_service.py        # CRUD operations for movies (get by ID, search by title)
│       │   ├── rating_service.py       # Add/update ratings, get user ratings
│       │   ├── embedding_service.py    # Holds loaded sentence-transformer, embed text/batch
│       │   ├── content_recommender.py  # Find similar movies via pgvector SQL or FAISS
│       │   ├── collab_recommender.py   # Load ALS model, score users, recommend items
│       │   ├── hybrid_recommender.py   # Combine content + collab scores, handle cold-start
│       │   └── llm_service.py          # (Optional) Mistral 7B for explanations via Ollama
│       │
│       ├── pipeline/                   # Data processing modules (used by scripts/)
│       │   ├── __init__.py
│       │   ├── downloader.py           # Download and extract MovieLens dataset
│       │   ├── cleaner.py              # Parse TMDb CSV quirks, join datasets, output parquet
│       │   ├── embedder.py             # Batch embedding generation with sentence-transformers
│       │   ├── faiss_builder.py        # Build, save, load FAISS IndexFlatIP
│       │   └── collaborative.py        # Build sparse matrix, train ALS, save model artifacts
│       │
│       ├── evaluation/                 # Recommendation quality evaluation
│       │   ├── __init__.py
│       │   ├── metrics.py              # Precision@K, Recall@K, NDCG@K, MAP@K implementations
│       │   ├── splitter.py             # Temporal train/test split on ratings
│       │   └── evaluate.py             # Run full evaluation, compare strategies, output report
│       │
│       └── core/                       # Cross-cutting concerns
│           ├── __init__.py
│           ├── cache.py                # Redis client wrapper, caching decorators
│           ├── logging.py              # Structured logging configuration
│           └── exceptions.py           # Custom exception classes + FastAPI exception handlers
│
└── tests/                              # Test suite
    ├── conftest.py                     # Shared fixtures: test DB, test client, mock services
    ├── test_api/                       # API endpoint tests (integration)
    │   ├── test_movies.py
    │   ├── test_ratings.py
    │   └── test_recommendations.py
    ├── test_services/                  # Service unit tests
    │   ├── test_embedding_service.py
    │   ├── test_content_recommender.py
    │   ├── test_collab_recommender.py
    │   └── test_hybrid_recommender.py
    ├── test_pipeline/                  # Pipeline unit tests
    │   ├── test_cleaner.py
    │   └── test_embedder.py
    └── test_evaluation/                # Evaluation unit tests
        └── test_metrics.py
```

---

## 5. Database Schema

### 5.1 movies

The central table storing all movie information, including the pgvector embedding.

```sql
CREATE TABLE movies (
    id              SERIAL          PRIMARY KEY,
    tmdb_id         INTEGER         UNIQUE NOT NULL,
    imdb_id         VARCHAR(15),                          -- e.g., "tt0133093"
    movielens_id    INTEGER         UNIQUE,               -- MovieLens movieId (nullable for movies not in MovieLens)
    title           VARCHAR(500)    NOT NULL,
    overview        TEXT,                                  -- Movie plot summary (used for embedding)
    genres          JSONB           NOT NULL DEFAULT '[]', -- e.g., ["Action", "Sci-Fi"]
    keywords        JSONB           NOT NULL DEFAULT '[]', -- e.g., ["artificial intelligence", "dystopia"]
    cast_names      JSONB           NOT NULL DEFAULT '[]', -- Top 5 cast members, e.g., ["Keanu Reeves", ...]
    director        VARCHAR(255),
    release_date    DATE,
    vote_average    FLOAT           NOT NULL DEFAULT 0.0,  -- TMDb average vote (0-10)
    vote_count      INTEGER         NOT NULL DEFAULT 0,
    popularity      FLOAT           NOT NULL DEFAULT 0.0,  -- TMDb popularity score
    poster_path     VARCHAR(255),                          -- TMDb poster path (e.g., "/abc123.jpg")
    embedding       VECTOR(384),                           -- all-MiniLM-L6-v2 embedding
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX idx_movies_tmdb_id ON movies (tmdb_id);
CREATE INDEX idx_movies_movielens_id ON movies (movielens_id);
CREATE INDEX idx_movies_imdb_id ON movies (imdb_id);
CREATE INDEX idx_movies_genres ON movies USING GIN (genres);             -- For genre-based filtering
CREATE INDEX idx_movies_title_trgm ON movies USING GIN (title gin_trgm_ops);  -- For fuzzy text search (requires pg_trgm)
-- Vector index (created AFTER data is loaded for optimal performance):
CREATE INDEX idx_movies_embedding ON movies USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### 5.2 users

Stores user identifiers. Each MovieLens user becomes a row.

```sql
CREATE TABLE users (
    id              SERIAL          PRIMARY KEY,
    movielens_id    INTEGER         UNIQUE NOT NULL,      -- Original MovieLens userId
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_movielens_id ON users (movielens_id);
```

### 5.3 ratings

Stores all user-movie ratings. The 25M MovieLens ratings are the primary data source for collaborative filtering.

```sql
CREATE TABLE ratings (
    id              SERIAL          PRIMARY KEY,
    user_id         INTEGER         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    movie_id        INTEGER         NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    rating          FLOAT           NOT NULL CHECK (rating >= 0.5 AND rating <= 5.0),
    timestamp       TIMESTAMPTZ     NOT NULL,

    CONSTRAINT uq_user_movie UNIQUE (user_id, movie_id)
);

CREATE INDEX idx_ratings_user_id ON ratings (user_id);
CREATE INDEX idx_ratings_movie_id ON ratings (movie_id);
CREATE INDEX idx_ratings_timestamp ON ratings (timestamp);  -- For temporal train/test split
```

### 5.4 recommendations_cache

Stores precomputed recommendations for active users, avoiding expensive recomputation at request time.

```sql
CREATE TABLE recommendations_cache (
    id              SERIAL          PRIMARY KEY,
    user_id         INTEGER         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    movie_id        INTEGER         NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    score           FLOAT           NOT NULL,
    strategy        VARCHAR(20)     NOT NULL,               -- 'content', 'collab', or 'hybrid'
    computed_at     TIMESTAMPTZ     NOT NULL DEFAULT now(),

    CONSTRAINT uq_user_movie_strategy UNIQUE (user_id, movie_id, strategy)
);

CREATE INDEX idx_recs_cache_user_strategy ON recommendations_cache (user_id, strategy);
```

### 5.5 Required PostgreSQL Extensions

```sql
CREATE EXTENSION IF NOT EXISTS vector;      -- pgvector for VECTOR type and similarity operators
CREATE EXTENSION IF NOT EXISTS pg_trgm;     -- Trigram index for fuzzy text search on title
```

---

## 6. Data Flow

### 6.1 Offline Pipeline (run once, or periodically to refresh)

```
1. DOWNLOAD
   MovieLens ml-25m.zip  ──extract──►  data/raw/ml-25m/{ratings,movies,links}.csv
   Kaggle TMDb dataset   ──manual───►  data/raw/tmdb/{movies_metadata,keywords,credits}.csv

2. CLEAN & JOIN
   links.csv provides: movieId (MovieLens) ↔ tmdbId (TMDb) ↔ imdbId

   movies_metadata.csv ──parse genres JSON, filter bad rows──►  movies_df
   keywords.csv        ──parse keywords JSON────────────────►  keywords_df
   credits.csv         ──extract top 5 cast + director───────►  credits_df

   movies_df + keywords_df + credits_df  ──join on tmdb_id──►  full_movies_df
   full_movies_df + links.csv            ──join on tmdb_id──►  movies_with_movielens_id

   Output: data/processed/movies_clean.parquet (~45K rows)
           data/processed/ratings_clean.parquet (~25M rows)
           data/processed/id_mapping.parquet

3. EMBED
   For each movie: text = "{title}. {overview} Genres: {genres}. Keywords: {keywords}."
   Encode with all-MiniLM-L6-v2 (batch_size=256, normalize=True)
   Output: data/processed/embeddings.npy (shape: N x 384, float32)

4. BUILD FAISS INDEX
   Load embeddings.npy
   Create IndexFlatIP (inner product = cosine similarity for normalized vectors)
   Output: data/processed/faiss.index + data/processed/faiss_id_map.pkl

5. TRAIN ALS MODEL
   Build sparse CSR matrix: users x items, values = confidence (1 + 40 * rating)
   Train implicit.als.AlternatingLeastSquares(factors=128, iterations=15, regularization=0.01)
   Output: data/processed/als_model.pkl
           data/processed/als_user_map.pkl
           data/processed/als_item_map.pkl
           data/processed/als_user_items.npz

6. SEED DATABASE
   Run Alembic migrations (create tables, extensions, indexes)
   Bulk-insert movies with embeddings (batch of 1000)
   Bulk-insert users (distinct from ratings)
   Bulk-insert ratings (batch of 50,000 via asyncpg COPY)
   Create IVFFlat vector index after data is loaded
```

### 6.2 Runtime Request Flow

```
User request: GET /api/v1/users/42/recommendations?top_k=20&strategy=hybrid

1. CHECK CACHE
   Redis key: "recs:42:hybrid:20"
   If hit: return cached result immediately

2. COLLABORATIVE FILTERING
   Load user_idx from als_user_map[42]
   Call als_model.recommend(user_idx, user_items[user_idx], N=100)
   Returns: [(movie_idx, score), ...] -- top 100 collaborative candidates

3. CONTENT-BASED FILTERING
   Fetch user's top 10 highest-rated movies from PostgreSQL
   For each top-rated movie, query pgvector:
     SELECT id, 1 - (embedding <=> target_embedding) AS similarity
     FROM movies ORDER BY embedding <=> target_embedding LIMIT 30
   Collect union of all content candidates

4. HYBRID SCORING
   For each candidate movie:
     content_score = average cosine similarity to user's top-rated movies
     collab_score  = ALS model score
   Normalize both to [0, 1] range (min-max normalization)
   hybrid_score = alpha * content_score + (1 - alpha) * collab_score

5. RANK & RETURN
   Sort candidates by hybrid_score descending
   Take top 20
   Fetch movie details from PostgreSQL
   Cache result in Redis (TTL: 15 min)
   Return JSON response
```

---

## 7. Data Pipeline (Detailed)

### 7.1 Downloader (`pipeline/downloader.py`)

**MovieLens ml-25m**:
- URL: `https://files.grouplens.org/datasets/movielens/ml-25m.zip` (~250MB)
- Downloads with `urllib.request.urlretrieve` with progress callback
- Extracts to `data/raw/ml-25m/`
- Key files used: `ratings.csv` (25M rows), `links.csv` (62K rows), `movies.csv` (62K rows)

**TMDb metadata from Kaggle**:
- Cannot be auto-downloaded without Kaggle API key
- The script prints clear instructions:
  1. Visit https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset
  2. Download and place `movies_metadata.csv`, `keywords.csv`, `credits.csv` in `data/raw/tmdb/`
  3. Or use Kaggle CLI: `kaggle datasets download -d rounakbanik/the-movies-dataset`
- The script validates that required files exist before proceeding

### 7.2 Cleaner (`pipeline/cleaner.py`)

This is the most complex pipeline step due to known data quality issues in the TMDb dataset.

**Known TMDb CSV issues and how we handle them**:
1. **Bad rows in movies_metadata.csv**: Some rows have a date string in the `id` column instead of an integer (rows at indices ~19730, ~29503, ~35587). **Fix**: `pd.to_numeric(df['id'], errors='coerce').dropna()`.
2. **JSON columns with Python literals**: The `genres` column contains strings like `[{'id': 28, 'name': 'Action'}]` which is Python dict syntax, not valid JSON. **Fix**: Use `ast.literal_eval()` wrapped in try/except, falling back to empty list.
3. **Duplicate tmdb_ids**: Some movies appear multiple times. **Fix**: `drop_duplicates(subset='id', keep='first')`.
4. **Missing overviews**: Movies without an overview cannot be embedded. **Fix**: Drop these rows (they can't participate in content-based filtering).

**Join logic**:
```
links.csv:  movieId (int) | imdbId (str) | tmdbId (int)
                │                              │
                │                              ▼
                │               movies_metadata.csv 'id' column
                │
                ▼
        ratings.csv 'movieId' column
```

The join produces a unified dataset where each movie has:
- An internal sequential ID (for our DB)
- A MovieLens ID (for linking to ratings)
- A TMDb ID (for linking to metadata)
- All metadata fields (overview, genres, keywords, cast, director, etc.)

**Filtering**:
- Drop movies with no overview (can't embed)
- Drop movies with fewer than 5 total ratings (reduces noise)
- Keep users with at least 20 ratings (ensures enough signal for collaborative filtering)

### 7.3 Embedder (`pipeline/embedder.py`)

**Model**: `sentence-transformers/all-MiniLM-L6-v2`
- 384-dimensional embeddings
- ~80MB model size (auto-downloaded from HuggingFace Hub on first use)
- ~1000 sentences/second on CPU, faster on GPU
- Trained on 1B+ sentence pairs, excellent for semantic similarity

**Text construction for each movie**:
```python
text = f"{title}. {overview} Genres: {', '.join(genres)}. Keywords: {', '.join(keywords)}."
```

Example for "The Matrix":
```
The Matrix. A computer hacker learns from mysterious rebels about the true nature of
his reality and his role in the war against its controllers. Genres: Action, Science
Fiction. Keywords: saving the world, artificial intelligence, virtual reality, dystopia.
```

**Batch processing**:
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
embeddings = model.encode(
    texts,
    batch_size=256,
    show_progress_bar=True,
    normalize_embeddings=True  # L2 normalization: cosine sim = dot product
)
np.save('data/processed/embeddings.npy', embeddings)
```

The `normalize_embeddings=True` parameter is crucial: it L2-normalizes each vector so that cosine similarity equals the dot product. This enables:
- pgvector's `<#>` (negative inner product) operator for fast cosine similarity
- FAISS `IndexFlatIP` (inner product) to compute cosine similarity directly

### 7.4 FAISS Builder (`pipeline/faiss_builder.py`)

```python
import faiss
import numpy as np
import pickle

embeddings = np.load('data/processed/embeddings.npy')  # shape: (N, 384)
dimension = embeddings.shape[1]  # 384

# IndexFlatIP = brute-force inner product (exact nearest neighbors)
# For ~45K movies this is fast enough (<5ms per query)
index = faiss.IndexFlatIP(dimension)
index.add(embeddings.astype(np.float32))

faiss.write_index(index, 'data/processed/faiss.index')

# Save the ordered list of movie IDs corresponding to FAISS internal indices
with open('data/processed/faiss_id_map.pkl', 'wb') as f:
    pickle.dump(movie_ids_ordered, f)
```

**Why IndexFlatIP instead of IVF**: With ~45K vectors of 384 dimensions, a flat index search takes <5ms. IVF/HNSW would add complexity (training, nprobe tuning) for negligible speedup at this scale. If scaling to 500K+ movies, switch to `IndexIVFFlat(quantizer, dim, nlist=256, faiss.METRIC_INNER_PRODUCT)`.

### 7.5 Collaborative Filtering Training (`pipeline/collaborative.py`)

```python
import implicit
from scipy.sparse import csr_matrix
import pickle

# Build user-item matrix
# Rows = users, Columns = items (movies), Values = confidence
# Confidence = 1 + alpha * rating (alpha=40 is standard for converting explicit to implicit)
user_indices = [user_map[uid] for uid in ratings['user_id']]
item_indices = [item_map[mid] for mid in ratings['movie_id']]
confidence_values = 1 + 40 * ratings['rating'].values

user_items = csr_matrix(
    (confidence_values, (user_indices, item_indices)),
    shape=(n_users, n_items)
)

# Train ALS
model = implicit.als.AlternatingLeastSquares(
    factors=128,          # Latent factor dimensions
    iterations=15,        # Training iterations
    regularization=0.01,  # L2 regularization
    random_state=42
)
model.fit(user_items)

# Save artifacts
pickle.dump(model, open('data/processed/als_model.pkl', 'wb'))
pickle.dump(user_map, open('data/processed/als_user_map.pkl', 'wb'))
pickle.dump(item_map, open('data/processed/als_item_map.pkl', 'wb'))
scipy.sparse.save_npz('data/processed/als_user_items.npz', user_items)
```

**Why ALS (Alternating Least Squares)**:
- Handles implicit feedback well (we convert explicit ratings to confidence scores)
- The `implicit` library is C++ backed and handles 25M ratings in minutes
- Produces user factors and item factors that can be used for fast scoring
- Well-suited for offline batch training + online serving pattern

---

## 8. Embedding System

### 8.1 Model Choice: all-MiniLM-L6-v2

| Property | Value |
|----------|-------|
| Dimensions | 384 |
| Model size | ~80MB |
| Max sequence length | 256 tokens |
| Speed (CPU) | ~1000 sentences/sec |
| Speed (GPU) | ~5000 sentences/sec |
| Training data | 1B+ sentence pairs |
| License | Apache 2.0 |

This model is specifically designed for semantic similarity tasks and runs efficiently on CPU. It's small enough for local deployment without GPU requirements while still producing high-quality embeddings.

### 8.2 Embedding Service (`services/embedding_service.py`)

Loaded once at application startup via FastAPI's lifespan context manager:

```python
class EmbeddingService:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text string. Returns a normalized 384-dim vector."""
        return self.model.encode(text, normalize_embeddings=True)

    def embed_batch(self, texts: list[str], batch_size: int = 256) -> np.ndarray:
        """Embed multiple texts. Returns (N, 384) normalized array."""
        return self.model.encode(texts, batch_size=batch_size, normalize_embeddings=True)

    def build_movie_text(self, title: str, overview: str, genres: list[str], keywords: list[str]) -> str:
        """Construct the text representation of a movie for embedding."""
        parts = [f"{title}."]
        if overview:
            parts.append(overview)
        if genres:
            parts.append(f"Genres: {', '.join(genres)}.")
        if keywords:
            parts.append(f"Keywords: {', '.join(keywords)}.")
        return " ".join(parts)
```

### 8.3 Content Recommender (`services/content_recommender.py`)

Two search paths depending on use case:

**Path A -- pgvector (single-query, default for API requests)**:
```sql
-- Find top K movies most similar to a given movie
SELECT m.id, m.title, m.genres, m.vote_average,
       1 - (m.embedding <=> :query_embedding) AS similarity
FROM movies m
WHERE m.id != :exclude_movie_id
  AND m.embedding IS NOT NULL
ORDER BY m.embedding <=> :query_embedding
LIMIT :top_k;
```
The `<=>` operator computes cosine distance. We convert to similarity: `1 - distance`.

**Path B -- FAISS (batch queries, evaluation)**:
```python
# query_vec shape: (1, 384) or (N, 384) for batch
distances, indices = self.faiss_index.search(query_vec, top_k)
# Map FAISS internal indices back to movie IDs
movie_ids = [self.id_map[idx] for idx in indices[0]]
```

FAISS is preferred for batch operations (evaluating 1000 users) because it avoids 1000 separate SQL queries.

---

## 9. Collaborative Filtering

### 9.1 Algorithm: Alternating Least Squares (ALS)

ALS factorizes the user-item interaction matrix into two lower-rank matrices:

```
R ≈ U × I^T

Where:
  R = user-item matrix (n_users × n_items)
  U = user factors matrix (n_users × n_factors)  -- each user is a 128-dim vector
  I = item factors matrix (n_items × n_factors)  -- each movie is a 128-dim vector
```

To predict how much user `u` would like item `i`: `score = dot(U[u], I[i])`

### 9.2 Collaborative Recommender (`services/collab_recommender.py`)

```python
class CollabRecommender:
    def __init__(self, model_path: str, user_map_path: str, item_map_path: str, user_items_path: str):
        self.model = pickle.load(open(model_path, 'rb'))
        self.user_map = pickle.load(open(user_map_path, 'rb'))      # user_id -> matrix_idx
        self.item_map = pickle.load(open(item_map_path, 'rb'))      # movie_id -> matrix_idx
        self.reverse_item_map = {v: k for k, v in self.item_map.items()}
        self.user_items = scipy.sparse.load_npz(user_items_path)

    def recommend_for_user(self, user_id: int, top_k: int = 50) -> list[tuple[int, float]]:
        """Get top K recommendations for a user.
        Returns list of (movie_id, score) tuples.
        Returns empty list for cold-start users (not in training data)."""
        user_idx = self.user_map.get(user_id)
        if user_idx is None:
            return []  # Cold start -- hybrid will fall back to content-only

        item_indices, scores = self.model.recommend(
            user_idx,
            self.user_items[user_idx],
            N=top_k,
            filter_already_liked_items=True
        )
        return [(self.reverse_item_map[idx], float(score))
                for idx, score in zip(item_indices, scores)
                if idx in self.reverse_item_map]

    def score_items(self, user_id: int, movie_ids: list[int]) -> dict[int, float]:
        """Score specific items for a user. Used by hybrid combiner."""
        user_idx = self.user_map.get(user_id)
        if user_idx is None:
            return {}
        scores = {}
        for mid in movie_ids:
            item_idx = self.item_map.get(mid)
            if item_idx is not None:
                user_vec = self.model.user_factors[user_idx]
                item_vec = self.model.item_factors[item_idx]
                scores[mid] = float(np.dot(user_vec, item_vec))
        return scores
```

### 9.3 Cold-Start Handling

| Scenario | Behavior |
|----------|----------|
| **New user (no ratings)** | Collaborative score = 0. Hybrid alpha forced to 1.0 (pure content-based). Recommend popular + high-rated movies. |
| **User with < 5 ratings** | Collaborative results may be poor. Alpha shifted toward content: `alpha = max(0.8, base_alpha)` |
| **New movie (no ratings)** | Movie won't appear in collaborative results. Still found via content similarity (embeddings). |
| **New movie (no overview)** | Cannot be embedded. Only appears if manually rated by users. Excluded from content-based. |

---

## 10. Hybrid Recommendation Engine

### 10.1 Algorithm

The hybrid recommender combines content-based and collaborative filtering scores:

```
hybrid_score(user, movie) = alpha * content_score + (1 - alpha) * collab_score
```

Where `alpha` is configurable (default: 0.5), and both scores are normalized to [0, 1].

### 10.2 Detailed Flow (`services/hybrid_recommender.py`)

```python
class HybridRecommender:
    def __init__(self, content: ContentRecommender, collab: CollabRecommender, alpha: float = 0.5):
        self.content = content
        self.collab = collab
        self.alpha = alpha

    async def recommend(self, user_id: int, db: AsyncSession, top_k: int = 20) -> list[RecommendationResult]:
        # Step 1: Get collaborative candidates (cast a wide net: top 100)
        collab_results = self.collab.recommend_for_user(user_id, top_k=100)
        collab_scores = {movie_id: score for movie_id, score in collab_results}

        # Step 2: Get user's top-rated movies for content-based seeding
        user_top_movies = await self._get_user_top_rated(user_id, db, limit=10)

        # Step 3: Find content-similar movies to what user already likes
        content_candidates = {}
        for rated_movie_id, user_rating in user_top_movies:
            similar = await self.content.get_similar_movies(rated_movie_id, db, top_k=30)
            for movie_id, similarity in similar:
                if movie_id not in content_candidates:
                    content_candidates[movie_id] = []
                # Weight similarity by how much the user liked the seed movie
                content_candidates[movie_id].append(similarity * (user_rating / 5.0))

        # Step 4: Aggregate content scores (average weighted similarity)
        content_scores = {
            mid: np.mean(sims) for mid, sims in content_candidates.items()
        }

        # Step 5: Merge candidate pools
        all_candidates = set(collab_scores.keys()) | set(content_scores.keys())

        # Remove movies the user has already rated
        already_rated = {mid for mid, _ in user_top_movies}
        all_candidates -= already_rated

        # Step 6: Normalize scores to [0, 1]
        collab_scores = self._min_max_normalize(collab_scores)
        content_scores = self._min_max_normalize(content_scores)

        # Step 7: Compute hybrid score
        alpha = self.alpha
        if not collab_scores:  # Cold-start user
            alpha = 1.0

        results = []
        for movie_id in all_candidates:
            c_score = content_scores.get(movie_id, 0.0)
            f_score = collab_scores.get(movie_id, 0.0)
            hybrid = alpha * c_score + (1 - alpha) * f_score
            results.append(RecommendationResult(
                movie_id=movie_id,
                score=round(hybrid, 4),
                content_score=round(c_score, 4),
                collab_score=round(f_score, 4)
            ))

        # Step 8: Sort by hybrid score, return top K
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    @staticmethod
    def _min_max_normalize(scores: dict[int, float]) -> dict[int, float]:
        if not scores:
            return scores
        min_s = min(scores.values())
        max_s = max(scores.values())
        if max_s == min_s:
            return {k: 1.0 for k in scores}
        return {k: (v - min_s) / (max_s - min_s) for k, v in scores.items()}
```

### 10.3 Strategy Selection

The API supports three strategies via query parameter:

| Strategy | Behavior |
|----------|----------|
| `hybrid` (default) | Full hybrid: alpha * content + (1-alpha) * collab |
| `content` | Content-only: find movies similar to user's top-rated |
| `collab` | Collaborative-only: pure ALS recommendations |

---

## 11. API Design

### 11.1 Endpoints

#### Health Check
```
GET /health
Response: {"status": "ok", "version": "0.1.0"}
```

#### Get Movie Details
```
GET /api/v1/movies/{movie_id}

Response 200:
{
  "id": 1,
  "tmdb_id": 862,
  "imdb_id": "tt0114709",
  "title": "Toy Story",
  "overview": "Led by Woody, Andy's toys live happily...",
  "genres": ["Animation", "Comedy", "Family"],
  "keywords": ["jealousy", "toy", "boy", "friendship"],
  "cast_names": ["Tom Hanks", "Tim Allen", "Don Rickles", "Jim Varney", "Wallace Shawn"],
  "director": "John Lasseter",
  "release_date": "1995-10-30",
  "vote_average": 7.7,
  "vote_count": 5415,
  "popularity": 21.946943
}

Response 404: {"detail": "Movie not found"}
```

#### Search Movies
```
GET /api/v1/movies/search?q=matrix&limit=10

Response 200:
{
  "results": [
    {"id": 603, "title": "The Matrix", "release_date": "1999-03-30", "vote_average": 8.2, "genres": ["Action", "Science Fiction"]},
    {"id": 604, "title": "The Matrix Reloaded", ...},
    ...
  ],
  "total": 5,
  "query": "matrix"
}
```

#### Get Similar Movies (Content-Based)
```
GET /api/v1/movies/{movie_id}/similar?top_k=10

Response 200:
{
  "movie_id": 603,
  "movie_title": "The Matrix",
  "similar": [
    {"id": 604, "title": "The Matrix Reloaded", "similarity": 0.89, "genres": ["Action", "Science Fiction"]},
    {"id": 605, "title": "The Matrix Revolutions", "similarity": 0.87, ...},
    {"id": 1091, "title": "The Terminator", "similarity": 0.72, ...},
    ...
  ]
}
```

#### Get User Recommendations (Hybrid)
```
GET /api/v1/users/{user_id}/recommendations?top_k=20&strategy=hybrid

Response 200:
{
  "user_id": 42,
  "strategy": "hybrid",
  "recommendations": [
    {
      "movie": {"id": 278, "title": "The Shawshank Redemption", "genres": ["Drama", "Crime"], "vote_average": 8.7},
      "score": 0.923,
      "content_score": 0.87,
      "collab_score": 0.95
    },
    ...
  ]
}

Response 404: {"detail": "User not found"}
```

#### Explain Recommendation (Optional LLM)
```
GET /api/v1/users/{user_id}/recommendations/explain/{movie_id}

Response 200:
{
  "user_id": 42,
  "movie_id": 278,
  "explanation": "Based on your high ratings for 'The Green Mile' and 'Forrest Gump', we recommend 'The Shawshank Redemption' because it shares themes of hope and redemption, features a similar dramatic tone, and is consistently rated highly by users with similar taste profiles.",
  "content_factors": ["Similar genres: Drama", "Shared keywords: prison, hope, friendship"],
  "collab_factors": ["Users who liked 'The Green Mile' (4.5) also rated this 4.8"]
}

Response 503: {"detail": "LLM service not enabled"}
```

#### Add/Update Rating
```
POST /api/v1/users/{user_id}/ratings
Body: {"movie_id": 603, "rating": 4.5}

Response 201:
{
  "user_id": 42,
  "movie_id": 603,
  "rating": 4.5,
  "timestamp": "2026-03-25T12:00:00Z"
}

Response 404: {"detail": "Movie not found"}
Response 422: {"detail": "Rating must be between 0.5 and 5.0"}
```

#### Get User Ratings
```
GET /api/v1/users/{user_id}/ratings?offset=0&limit=20

Response 200:
{
  "user_id": 42,
  "ratings": [
    {"movie_id": 603, "title": "The Matrix", "rating": 5.0, "timestamp": "2025-01-15T..."},
    ...
  ],
  "total": 156,
  "offset": 0,
  "limit": 20
}
```

### 11.2 Error Handling

All errors follow a consistent format:
```json
{
  "detail": "Human-readable error message"
}
```

| Status Code | Usage |
|-------------|-------|
| 200 | Successful GET |
| 201 | Successful POST (resource created) |
| 400 | Bad request (invalid query params) |
| 404 | Resource not found |
| 422 | Validation error (invalid rating value) |
| 500 | Internal server error |
| 503 | Service unavailable (LLM not enabled) |

### 11.3 Pagination

All list endpoints support offset/limit pagination:
- `offset` (default: 0) -- number of items to skip
- `limit` (default: 20, max: 100) -- number of items to return
- Response includes `total` count for UI pagination

---

## 12. Caching & Optimization

### 12.1 Redis Caching Strategy

| Cache Key Pattern | TTL | Invalidation |
|-------------------|-----|-------------|
| `movie:{movie_id}` | 1 hour | Manual (on movie data update) |
| `similar:{movie_id}:{top_k}` | 30 min | Never (content similarity is stable) |
| `recs:{user_id}:{strategy}:{top_k}` | 15 min | On new rating from this user |
| `search:{query_hash}:{limit}` | 10 min | Never (search results stable short-term) |

### 12.2 Cache Implementation (`core/cache.py`)

```python
class CacheService:
    def __init__(self, redis_url: str, default_ttl: int = 3600):
        self.redis = aioredis.from_url(redis_url)
        self.default_ttl = default_ttl

    async def get(self, key: str) -> Optional[str]:
        return await self.redis.get(key)

    async def set(self, key: str, value: str, ttl: Optional[int] = None):
        await self.redis.set(key, value, ex=ttl or self.default_ttl)

    async def delete_pattern(self, pattern: str):
        """Delete all keys matching a pattern (e.g., 'recs:42:*')"""
        async for key in self.redis.scan_iter(match=pattern):
            await self.redis.delete(key)

    async def invalidate_user_recs(self, user_id: int):
        """Called when a user adds a new rating"""
        await self.delete_pattern(f"recs:{user_id}:*")
```

### 12.3 Other Optimizations

| Optimization | Description |
|-------------|-------------|
| **Connection pooling** | SQLAlchemy async engine with `pool_size=20, max_overflow=10` |
| **Precomputed embeddings** | All movie embeddings stored in DB and FAISS at pipeline time -- no runtime embedding for existing movies |
| **Model preloading** | Sentence-transformer and ALS model loaded once at startup via FastAPI lifespan |
| **FAISS in-memory** | FAISS index loaded to RAM at startup for sub-millisecond similarity search |
| **Batch DB inserts** | Seeding uses `asyncpg.copy_records_to_table` for 50K rows/batch (10-50x faster than INSERT) |
| **Normalized embeddings** | Pre-normalized vectors mean cosine similarity = dot product (no runtime normalization) |
| **IVFFlat index** | pgvector approximate nearest neighbor index, created after bulk load for optimal list distribution |
| **Lazy LLM loading** | Mistral 7B only loaded if `llm_enabled=True` (saves ~4GB RAM when not needed) |

---

## 13. Evaluation Framework

### 13.1 Train/Test Split (`evaluation/splitter.py`)

**Method**: Temporal split -- sort all ratings by timestamp, use the first 80% for training and the last 20% for testing.

**Why temporal**: Random splits leak future information (a user's 2023 rating being in the training set while their 2022 rating is in the test set). Temporal splits simulate the real scenario: predict what a user will rate next based on their history.

```python
def temporal_split(ratings_df: pd.DataFrame, train_ratio: float = 0.8):
    ratings_sorted = ratings_df.sort_values('timestamp')
    split_idx = int(len(ratings_sorted) * train_ratio)
    train = ratings_sorted.iloc[:split_idx]
    test = ratings_sorted.iloc[split_idx:]
    return train, test
```

### 13.2 Metrics (`evaluation/metrics.py`)

All metrics are computed per user, then averaged across the test set.

**Precision@K**: Of the K recommended movies, what fraction did the user actually rate highly (>= 4.0)?
```
Precision@K = |recommended_top_K ∩ relevant| / K
```

**Recall@K**: Of all movies the user rated highly, what fraction appeared in the top K recommendations?
```
Recall@K = |recommended_top_K ∩ relevant| / |relevant|
```

**NDCG@K (Normalized Discounted Cumulative Gain)**: Rewards relevant items appearing earlier in the list.
```
DCG@K = Σ(i=1..K) rel(i) / log2(i + 1)
NDCG@K = DCG@K / IDCG@K  (IDCG = perfect ranking)
```

**MAP@K (Mean Average Precision)**: Average of precision values at each position where a relevant item is found.
```
AP@K = (1/min(K, |relevant|)) * Σ(i=1..K) Precision(i) * rel(i)
MAP@K = mean of AP@K across all users
```

### 13.3 Evaluation Runner (`evaluation/evaluate.py`)

```python
def evaluate(train_ratings, test_ratings, n_users=1000, k_values=[5, 10, 20]):
    """
    1. Sample n_users from test set (users who have >= 5 test ratings)
    2. For each user:
       a. Get their test ratings where rating >= 4.0 (relevant items)
       b. Generate recommendations using each strategy (content, collab, hybrid)
       c. Compute Precision@K, Recall@K, NDCG@K, MAP@K for each K
    3. Average across all users
    4. Output comparison table and save to evaluation_report.json
    """
```

**Expected output format**:
```
Strategy    | P@5   | P@10  | P@20  | R@5   | R@10  | R@20  | NDCG@10 | MAP@10
------------|-------|-------|-------|-------|-------|-------|---------|-------
Content     | 0.12  | 0.10  | 0.08  | 0.05  | 0.08  | 0.13  | 0.11    | 0.09
Collab      | 0.18  | 0.15  | 0.12  | 0.07  | 0.12  | 0.19  | 0.16    | 0.14
Hybrid      | 0.21  | 0.17  | 0.14  | 0.08  | 0.14  | 0.22  | 0.19    | 0.16
```

(Numbers are illustrative -- actual values depend on alpha tuning and data quality.)

---

## 14. Optional LLM Integration

### 14.1 Purpose

Mistral 7B is used **exclusively** for:
- Explaining why a movie was recommended (natural language)
- Generating conversational summaries of recommendation results
- Optionally reranking top candidates based on deeper understanding

It is **NOT** used for generating embeddings (that's all-MiniLM-L6-v2's job).

### 14.2 Integration via Ollama

Ollama runs locally and provides an HTTP API at `http://localhost:11434`.

```python
class LLMService:
    def __init__(self, model_name: str = "mistral", base_url: str = "http://localhost:11434"):
        self.model = model_name
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=60.0)

    async def explain_recommendation(
        self, user_rated_movies: list[dict], recommended_movie: dict
    ) -> str:
        prompt = f"""You are a movie recommendation assistant. A user has highly rated these movies:
{self._format_movies(user_rated_movies)}

We are recommending: {recommended_movie['title']} ({recommended_movie['genres']})
Overview: {recommended_movie['overview']}

Explain in 2-3 sentences why this movie is a good recommendation for this user,
based on genre overlap, thematic similarities, and the user's apparent preferences."""

        response = await self.client.post("/api/generate", json={
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 200}
        })
        return response.json()["response"]
```

### 14.3 Setup

```bash
# Install Ollama (macOS)
brew install ollama

# Pull Mistral 7B (~4GB download)
ollama pull mistral

# Set in .env
CINEMATCH_LLM_ENABLED=true
CINEMATCH_LLM_BACKEND=ollama
```

---

## 15. Configuration Management

### 15.1 Settings (`config.py`)

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="CINEMATCH_")

    # Database
    database_url: str = "postgresql+asyncpg://cinematch:cinematch@localhost:5432/cinematch"
    database_url_sync: str = "postgresql://cinematch:cinematch@localhost:5432/cinematch"  # For Alembic
    db_pool_size: int = 20
    db_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 3600

    # Embedding model
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    embedding_batch_size: int = 256

    # FAISS
    faiss_index_path: str = "data/processed/faiss.index"
    faiss_id_map_path: str = "data/processed/faiss_id_map.pkl"

    # Collaborative filtering
    als_model_path: str = "data/processed/als_model.pkl"
    als_user_map_path: str = "data/processed/als_user_map.pkl"
    als_item_map_path: str = "data/processed/als_item_map.pkl"
    als_user_items_path: str = "data/processed/als_user_items.npz"
    als_factors: int = 128
    als_iterations: int = 15
    als_regularization: float = 0.01

    # Hybrid recommender
    hybrid_alpha: float = 0.5  # 0.0 = pure collab, 1.0 = pure content

    # LLM (optional)
    llm_enabled: bool = False
    llm_model_name: str = "mistral"
    llm_base_url: str = "http://localhost:11434"
    llm_backend: str = "ollama"  # "ollama" or "llamacpp"

    # Data paths
    data_raw_dir: str = "data/raw"
    data_processed_dir: str = "data/processed"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
```

### 15.2 `.env.example`

```env
# Database
CINEMATCH_DATABASE_URL=postgresql+asyncpg://cinematch:cinematch@localhost:5432/cinematch
CINEMATCH_DATABASE_URL_SYNC=postgresql://cinematch:cinematch@localhost:5432/cinematch

# Redis
CINEMATCH_REDIS_URL=redis://localhost:6379/0

# Hybrid recommender
CINEMATCH_HYBRID_ALPHA=0.5

# LLM (optional -- set to true if you have Ollama + Mistral installed)
CINEMATCH_LLM_ENABLED=false

# API
CINEMATCH_DEBUG=false
```

---

## 16. Infrastructure (Docker)

### 16.1 docker-compose.yml

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: cinematch-postgres
    environment:
      POSTGRES_USER: cinematch
      POSTGRES_PASSWORD: cinematch
      POSTGRES_DB: cinematch
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U cinematch"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: cinematch-redis
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
  redisdata:
```

The `pgvector/pgvector:pg16` Docker image comes with the pgvector extension pre-installed. No manual compilation needed.

### 16.2 Makefile

```makefile
.PHONY: setup run test download pipeline seed evaluate clean

setup:          ## Install dependencies and run migrations
    pip install -e ".[dev]"
    alembic upgrade head

run:            ## Start the FastAPI development server
    uvicorn cinematch.main:app --reload --host 0.0.0.0 --port 8000

test:           ## Run test suite
    pytest tests/ -v --cov=cinematch

download:       ## Download datasets
    python scripts/download_data.py

pipeline:       ## Run full data pipeline (clean, embed, build FAISS, train ALS)
    python -m cinematch.pipeline.cleaner
    python -m cinematch.pipeline.embedder
    python -m cinematch.pipeline.faiss_builder
    python -m cinematch.pipeline.collaborative

seed:           ## Seed PostgreSQL with processed data
    python scripts/seed_db.py

evaluate:       ## Run evaluation metrics
    python -m cinematch.evaluation.evaluate

clean:          ## Remove processed data and artifacts
    rm -rf data/processed/*

lint:           ## Run linter
    ruff check src/ tests/
    ruff format --check src/ tests/
```

---

## 17. Testing Strategy

### 17.1 Test Categories

| Category | Location | What It Tests | Fixtures |
|----------|----------|---------------|----------|
| **Unit tests** | `tests/test_services/` | Individual service methods with mocked dependencies | Mock DB, mock models |
| **Pipeline tests** | `tests/test_pipeline/` | Data cleaning, embedding generation with small sample data | Sample CSV files |
| **API tests** | `tests/test_api/` | Endpoint behavior, request validation, error handling | TestClient + test DB |
| **Evaluation tests** | `tests/test_evaluation/` | Metric calculations against known expected values | Synthetic data |

### 17.2 Test Fixtures (`conftest.py`)

```python
@pytest.fixture
async def db_session():
    """Create a test database session with rollback after each test."""
    # Uses a separate test database or transaction rollback

@pytest.fixture
def test_client(db_session):
    """FastAPI TestClient with overridden dependencies."""

@pytest.fixture
def sample_embeddings():
    """Small set of pre-computed embeddings for testing similarity search."""

@pytest.fixture
def mock_als_model():
    """Mock ALS model that returns deterministic results."""
```

### 17.3 Key Test Scenarios

- **Content recommender**: Given movie A with known embedding, verify that most similar movies match expected results
- **Collab recommender**: Given a user with known ratings, verify recommendations are sensible
- **Hybrid combiner**: Verify score normalization, alpha weighting, and cold-start fallback
- **API validation**: Invalid movie ID returns 404, invalid rating value returns 422
- **Metrics**: Known relevance sets produce expected Precision/Recall/NDCG values

---

## 18. Step-by-Step Implementation Roadmap

### Phase 1: Foundation (Milestone 1) -- Priority: CRITICAL

**Goal**: Get the project skeleton running with Docker, database, and a health check endpoint.

| Step | Task | Files Created/Modified | Details |
|------|------|----------------------|---------|
| 1.1 | Create `pyproject.toml` | `pyproject.toml` | All dependencies, project metadata, tool config (ruff, pytest) |
| 1.2 | Create `docker-compose.yml` | `docker-compose.yml` | PostgreSQL (pgvector) + Redis containers |
| 1.3 | Create `.env.example` | `.env.example` | Template with all config variables and documentation |
| 1.4 | Create `Makefile` | `Makefile` | Convenience commands: setup, run, test, download, pipeline, seed, evaluate |
| 1.5 | Create config module | `src/cinematch/config.py` | Pydantic Settings class reading from `.env` |
| 1.6 | Create DB base | `src/cinematch/db/base.py` | SQLAlchemy DeclarativeBase with pgvector Vector type |
| 1.7 | Create DB session | `src/cinematch/db/session.py` | Async engine, sessionmaker, `get_db` dependency |
| 1.8 | Create ORM models | `src/cinematch/models/{movie,user,rating,recommendation}.py` | All four tables with proper types, constraints, indexes |
| 1.9 | Configure Alembic | `alembic.ini`, `src/cinematch/db/migrations/env.py` | Async Alembic config pointing to our models |
| 1.10 | Create initial migration | `src/cinematch/db/migrations/versions/001_initial.py` | pgvector + pg_trgm extensions, all tables, all indexes |
| 1.11 | Create FastAPI app | `src/cinematch/main.py` | App factory with lifespan, health check endpoint, CORS |
| 1.12 | Create package inits | `src/cinematch/__init__.py`, etc. | Package initialization files |
| 1.13 | Update `.gitignore` | `.gitignore` | Add `data/`, `.env`, model artifacts |

**Verification**:
```bash
docker compose up -d                    # PostgreSQL + Redis running
cp .env.example .env                    # Create local config
pip install -e ".[dev]"                 # Install dependencies
alembic upgrade head                    # Create tables
uvicorn cinematch.main:app --reload     # Server starts on :8000
curl http://localhost:8000/health       # Returns {"status": "ok"}
```

---

### Phase 2: Data Pipeline (Milestone 2) -- Priority: CRITICAL

**Goal**: Download, clean, join, embed, and prepare all data for the system.

| Step | Task | Files Created/Modified | Details |
|------|------|----------------------|---------|
| 2.1 | Create downloader | `src/cinematch/pipeline/downloader.py` | Download MovieLens ml-25m zip, extract. Print Kaggle TMDb instructions. |
| 2.2 | Create download script | `scripts/download_data.py` | CLI entry point calling downloader module |
| 2.3 | Create cleaner | `src/cinematch/pipeline/cleaner.py` | Parse TMDb CSVs (handle bad rows, Python-literal JSON), join with MovieLens via links.csv, output parquet files |
| 2.4 | Create embedder | `src/cinematch/pipeline/embedder.py` | Load all-MiniLM-L6-v2, construct movie text, batch encode, save embeddings.npy |
| 2.5 | Create FAISS builder | `src/cinematch/pipeline/faiss_builder.py` | Load embeddings, build IndexFlatIP, save index + id_map |
| 2.6 | Create ALS trainer | `src/cinematch/pipeline/collaborative.py` | Build sparse user-item matrix, train implicit ALS, save model + mappings |
| 2.7 | Create seed script | `scripts/seed_db.py` | Bulk-insert movies (with embeddings), users, ratings into PostgreSQL. Build IVFFlat index. |
| 2.8 | Create train script | `scripts/train_models.py` | Orchestrate: clean -> embed -> FAISS -> ALS (convenience wrapper) |

**Verification**:
```bash
make download                           # Downloads MovieLens; prompts for Kaggle TMDb
# (manually place TMDb CSVs in data/raw/tmdb/)
make pipeline                           # Outputs parquet + embeddings + FAISS + ALS
ls data/processed/                      # All artifacts present
make seed                               # ~45K movies + 25M ratings in PostgreSQL
psql -U cinematch -c "SELECT count(*) FROM movies;"  # ~45000
psql -U cinematch -c "SELECT count(*) FROM ratings;"  # ~25000000
```

---

### Phase 3: Recommendation Engines (Milestone 3) -- Priority: CRITICAL

**Goal**: Implement the three recommendation strategies as service classes.

| Step | Task | Files Created/Modified | Details |
|------|------|----------------------|---------|
| 3.1 | Create embedding service | `src/cinematch/services/embedding_service.py` | Load model, embed_text(), embed_batch(), build_movie_text() |
| 3.2 | Create content recommender | `src/cinematch/services/content_recommender.py` | pgvector cosine similarity query, FAISS fallback, get_similar_movies() |
| 3.3 | Create collab recommender | `src/cinematch/services/collab_recommender.py` | Load ALS model, recommend_for_user(), score_items() |
| 3.4 | Create hybrid recommender | `src/cinematch/services/hybrid_recommender.py` | Combine scores, normalize, cold-start handling, recommend() |
| 3.5 | Write service tests | `tests/test_services/test_*.py` | Unit tests for each recommender with mocked data |

**Verification**:
```python
# Quick manual test in Python REPL
from cinematch.services.content_recommender import ContentRecommender
similar = await content_rec.get_similar_movies(movie_id=603, db=session, top_k=5)
# Should return Matrix sequels and similar sci-fi movies
```

---

### Phase 4: API Layer (Milestone 4) -- Priority: CRITICAL

**Goal**: Expose all functionality via FastAPI endpoints.

| Step | Task | Files Created/Modified | Details |
|------|------|----------------------|---------|
| 4.1 | Create Pydantic schemas | `src/cinematch/schemas/{movie,user,rating,recommendation}.py` | Request/response models with validation |
| 4.2 | Create movie service | `src/cinematch/services/movie_service.py` | get_by_id(), search_by_title() with DB queries |
| 4.3 | Create rating service | `src/cinematch/services/rating_service.py` | add_rating(), get_user_ratings() |
| 4.4 | Create API dependencies | `src/cinematch/api/deps.py` | get_db(), get_services() dependency injection |
| 4.5 | Create movie routes | `src/cinematch/api/v1/movies.py` | GET /{id}, GET /search, GET /{id}/similar |
| 4.6 | Create rating routes | `src/cinematch/api/v1/ratings.py` | POST /users/{id}/ratings, GET /users/{id}/ratings |
| 4.7 | Create recommendation routes | `src/cinematch/api/v1/recommendations.py` | GET /users/{id}/recommendations |
| 4.8 | Create user routes | `src/cinematch/api/v1/users.py` | User-related endpoints |
| 4.9 | Create v1 router | `src/cinematch/api/v1/router.py` | Aggregate all sub-routers |
| 4.10 | Wire lifespan | `src/cinematch/main.py` | Load all models/services at startup, attach to app.state |
| 4.11 | Write API tests | `tests/test_api/test_*.py` | Integration tests with TestClient |

**Verification**:
```bash
make run
curl http://localhost:8000/api/v1/movies/search?q=matrix
curl http://localhost:8000/api/v1/movies/1
curl http://localhost:8000/api/v1/movies/1/similar?top_k=5
curl http://localhost:8000/api/v1/users/1/recommendations?top_k=10&strategy=hybrid
curl -X POST http://localhost:8000/api/v1/users/1/ratings -H "Content-Type: application/json" -d '{"movie_id": 1, "rating": 4.5}'
# Visit http://localhost:8000/docs for Swagger UI
```

---

### Phase 5: Caching, Evaluation, Polish (Milestone 5) -- Priority: HIGH

**Goal**: Add caching, implement evaluation metrics, and polish the system.

| Step | Task | Files Created/Modified | Details |
|------|------|----------------------|---------|
| 5.1 | Create cache service | `src/cinematch/core/cache.py` | Redis wrapper, caching decorators, invalidation |
| 5.2 | Add caching to services | `src/cinematch/services/*.py` | Decorate movie_service, content_recommender, hybrid_recommender |
| 5.3 | Create metrics module | `src/cinematch/evaluation/metrics.py` | Precision@K, Recall@K, NDCG@K, MAP@K |
| 5.4 | Create splitter | `src/cinematch/evaluation/splitter.py` | Temporal train/test split |
| 5.5 | Create evaluation runner | `src/cinematch/evaluation/evaluate.py` | Full evaluation pipeline, comparison table, JSON report |
| 5.6 | Create exception handling | `src/cinematch/core/exceptions.py` | Custom exceptions + FastAPI exception handlers |
| 5.7 | Create logging config | `src/cinematch/core/logging.py` | Structured logging with request IDs |
| 5.8 | Write evaluation tests | `tests/test_evaluation/test_metrics.py` | Verify metrics against known expected values |
| 5.9 | Write integration tests | `tests/test_api/*.py` | End-to-end tests with seeded test database |

**Verification**:
```bash
make evaluate                           # Produces evaluation_report.json
cat data/processed/evaluation_report.json
make test                               # All tests pass
# Verify Redis caching: second request to same endpoint is faster
```

---

### Phase 6: LLM Integration (Milestone 6) -- Priority: OPTIONAL

**Goal**: Add natural language explanations via Mistral 7B.

| Step | Task | Files Created/Modified | Details |
|------|------|----------------------|---------|
| 6.1 | Create LLM service | `src/cinematch/services/llm_service.py` | Ollama HTTP client, explain_recommendation() |
| 6.2 | Add explain endpoint | `src/cinematch/api/v1/recommendations.py` | GET /users/{id}/recommendations/explain/{movie_id} |
| 6.3 | Wire LLM to lifespan | `src/cinematch/main.py` | Conditionally load LLM service if enabled |
| 6.4 | Test with Ollama | Manual testing | Verify explanations are coherent and relevant |

**Verification**:
```bash
ollama pull mistral                     # Download Mistral 7B (~4GB)
# Set CINEMATCH_LLM_ENABLED=true in .env
make run
curl http://localhost:8000/api/v1/users/1/recommendations/explain/603
# Should return natural language explanation
```

---

## Summary of Priorities

| Priority | Milestone | What You Get |
|----------|-----------|-------------|
| **P0 - CRITICAL** | 1. Foundation | Running app skeleton with DB |
| **P0 - CRITICAL** | 2. Data Pipeline | All data processed and loaded |
| **P0 - CRITICAL** | 3. Recommendation Engines | Working content + collab + hybrid recommenders |
| **P0 - CRITICAL** | 4. API Layer | Fully functional REST API |
| **P1 - HIGH** | 5. Caching + Evaluation | Production-ready performance + quality metrics |
| **P2 - OPTIONAL** | 6. LLM Integration | Natural language explanations |

After completing Milestones 1-4, you have a fully functional movie recommendation system. Milestone 5 makes it production-grade. Milestone 6 adds a nice-to-have feature.
