# CineMatch-AI

Hybrid movie recommendation system combining content-based filtering (embeddings) and collaborative filtering (user ratings). Built with FastAPI, PostgreSQL + pgvector, and local ML models. Runs fully locally with no paid APIs.

## Tech Stack

- **Backend:** FastAPI (Python 3.11+)
- **Database:** PostgreSQL 16 + pgvector
- **Vector Search:** pgvector (primary) + FAISS (batch operations)
- **Embeddings:** sentence-transformers/all-MiniLM-L6-v2 (384-dim, local)
- **Collaborative Filtering:** implicit ALS (matrix factorization)
- **Caching:** Redis
- **Optional LLM:** Mistral 7B via Ollama (explanations only)

## Data Sources

- [MovieLens ml-25m](https://grouplens.org/datasets/movielens/25m/) — 25M user ratings
- [TMDb metadata (Kaggle)](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset) — movie overviews, genres, keywords, cast, crew

## Quick Start

```bash
# Start infrastructure
docker compose up -d

# Install dependencies
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Configure environment
cp .env.example .env

# Run database migrations
alembic upgrade head

# Download and process data
python scripts/download_data.py
python scripts/train_models.py
python scripts/seed_db.py

# Start the API server
uvicorn cinematch.main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at http://localhost:8000/docs

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1/movies/{id}` | Movie details |
| GET | `/api/v1/movies/search?q=` | Search movies by title |
| GET | `/api/v1/movies/{id}/similar` | Content-similar movies |
| GET | `/api/v1/users/{id}/recommendations` | Hybrid recommendations |
| POST | `/api/v1/users/{id}/ratings` | Add/update a rating |
| GET | `/api/v1/users/{id}/ratings` | User's ratings |

## How It Works

1. **Content-Based:** Movie overviews, genres, and keywords are encoded into 384-dim vectors using all-MiniLM-L6-v2. Similar movies are found via cosine similarity (pgvector).
2. **Collaborative:** User-item rating matrix is factorized using ALS. Users with similar taste patterns get similar recommendations.
3. **Hybrid:** Both scores are normalized to [0,1] and combined: `hybrid = alpha * content + (1 - alpha) * collab`. Cold-start users fall back to content-only.

## Project Structure

```
src/cinematch/
├── api/v1/          # REST endpoints
├── services/        # Business logic (recommenders, embedding, etc.)
├── models/          # SQLAlchemy ORM models
├── schemas/         # Pydantic request/response schemas
├── pipeline/        # Data processing (cleaner, embedder, FAISS, ALS)
├── evaluation/      # Recommendation quality metrics
├── core/            # Cache, logging, exceptions
├── db/              # Database engine, migrations
├── config.py        # Environment-based configuration
└── main.py          # FastAPI app factory
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
