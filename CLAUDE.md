# CineMatch-AI

## Commands
- `docker compose up -d` — start local services (PostgreSQL + pgvector, Redis)
- `docker compose down` — stop local services
- `pip install -e ".[dev]"` — install all dependencies (including dev/test)
- `PYTHONPATH=src uvicorn cinematch.main:app --reload --host 0.0.0.0 --port 8000` — backend dev server
- `pytest tests/ -v` — run all tests
- `pytest tests/path/to/test.py -k test_name` — run single test
- `pytest tests/path/to/test.py -v` — run test file with verbose output
- `pytest tests/ --cov=cinematch` — run tests with coverage report
- `ruff check src/ tests/` — lint all code
- `ruff format src/ tests/` — format all code
- `alembic upgrade head` — run database migrations
- `alembic revision --autogenerate -m "description"` — create new migration
- `python scripts/download_data.py` — download datasets (MovieLens ml-25m + TMDb instructions)
- `python scripts/train_models.py` — run full pipeline (clean, embed, build FAISS, train ALS)
- `python scripts/seed_db.py` — load processed data into PostgreSQL
- `PYTHONPATH=src python scripts/precompute_recommendations.py` — precompute collaborative recommendations into `recommendations_cache`
- `python -m cinematch.evaluation.evaluate` — run evaluation metrics

## Environment Setup
- **Python:** 3.11+ — use a virtual env (`python -m venv .venv && source .venv/bin/activate`)
- **Dependencies:** `pip install -e ".[dev]"`
- **Database:** `docker compose up -d` then `alembic upgrade head`
- **Environment variables:** Copy `.env.example` to `.env` — defaults work out of the box with Docker
- **Data:** Run `python scripts/download_data.py` then manually place TMDb CSVs from Kaggle in `data/raw/tmdb/`
- **Pipeline:** Run `python scripts/train_models.py` then `python scripts/seed_db.py`
- **Optional LLM:** Install Ollama (`brew install ollama`), run `ollama pull mistral`, set `CINEMATCH_LLM_ENABLED=true` in `.env`

## Tech Stack
Python (FastAPI) | PostgreSQL + pgvector | Redis | SQLAlchemy 2.0 (async) + asyncpg + Alembic | sentence-transformers (all-MiniLM-L6-v2) | FAISS | implicit (ALS) | Pydantic v2 | Docker

## Architecture
- `src/cinematch/api/v1/` — REST endpoints (movies, ratings, recommendations, users)
- `src/cinematch/services/` — business logic (embedding, content recommender, collab recommender, hybrid recommender, movie service, rating service, LLM service)
- `src/cinematch/models/` — SQLAlchemy ORM models (movies, users, ratings, recommendations_cache)
- `src/cinematch/schemas/` — Pydantic v2 schemas for request/response validation
- `src/cinematch/core/` — cross-cutting concerns (cache, logging, exceptions)
- `src/cinematch/pipeline/` — offline data processing (downloader, cleaner, embedder, FAISS builder, collaborative filtering trainer)
- `src/cinematch/evaluation/` — recommendation quality metrics (Precision@K, Recall@K, NDCG@K, MAP@K)
- `src/cinematch/db/` — database engine, session management, Alembic migrations
- `src/cinematch/config.py` — Pydantic Settings (all config from environment variables with CINEMATCH_ prefix)
- `src/cinematch/main.py` — FastAPI app factory with lifespan (loads models at startup)
- `scripts/` — standalone scripts for download, seed, and training
- `data/raw/` — downloaded datasets (gitignored)
- `data/processed/` — pipeline output: parquet files, embeddings.npy, FAISS index, ALS model (gitignored)
- `tests/` — pytest tests mirroring `src/cinematch/` structure

## Code Style
- Python with type hints everywhere — use `from __future__ import annotations` when needed
- Ruff for both linting and formatting
- Pydantic v2 for all API input/output validation
- Async/await for all database operations (asyncpg + SQLAlchemy async)
- Consistent error format: `{"detail": "Human-readable message"}` with proper HTTP status codes
- Structured logging with request context
- Use dependency injection via FastAPI's `Depends()` — services live on `app.state`, accessed via `api/deps.py`

## Testing Conventions
- **Framework:** pytest with pytest-asyncio for async tests
- **Structure:** test files mirror source structure in `tests/` (e.g., `tests/test_services/test_hybrid_recommender.py`)
- **Naming:** test functions use `test_<what_it_does>` (e.g., `test_hybrid_falls_back_to_content_for_cold_start_user`)
- **Fixtures:** defined in `conftest.py` — reusable test data (sample movies, mock users, mock embeddings, mock ALS model)
- **Mocking:** mock external dependencies (database sessions, Redis, embedding model, ALS model) — never load real ML models in unit tests
- **Integration tests:** use FastAPI TestClient with test database and overridden dependencies
- **Coverage:** aim for >80% on new code; every new feature or change must include tests
- **Evaluation tests:** verify metric calculations against known expected values with synthetic data

## Database & Migrations
- ORM: SQLAlchemy 2.0 with async session support (asyncpg driver)
- Extensions: pgvector (vector similarity), pg_trgm (fuzzy text search)
- Migrations: Alembic — always create a migration for schema changes, never modify the database manually
- Run `alembic upgrade head` after pulling new changes
- Run `alembic revision --autogenerate -m "description"` to create migrations
- Always review autogenerated migrations before committing — check for destructive operations
- The IVFFlat vector index on `movies.embedding` is created AFTER bulk data load for optimal list distribution
- Use `pgvector/pgvector:pg16` Docker image — pgvector extension is pre-installed

## Data Pipeline
- MovieLens ml-25m provides ratings (25M rows) and links.csv (movieId <-> tmdbId mapping)
- TMDb metadata from Kaggle provides overviews, genres, keywords, cast, crew
- Known TMDb CSV quirks: some rows have dates in the `id` column, `genres` uses Python dict syntax not JSON, duplicate tmdb_ids exist
- Embeddings are L2-normalized so cosine similarity = dot product (enables pgvector `<#>` and FAISS `IndexFlatIP`)
- ALS collaborative filtering uses confidence weighting: `confidence = 1 + 40 * rating`
- All pipeline artifacts are saved to `data/processed/` and are gitignored

## Important
- NEVER commit `.env` files — use `.env.example` for reference
- NEVER commit data files — `data/` directory is gitignored
- NEVER commit model artifacts (`.pkl`, `.npy`, `.index` files) — they are gitignored
- All user input must be validated via Pydantic schemas before processing
- All config is read from environment variables with `CINEMATCH_` prefix via Pydantic Settings
- The embedding model (all-MiniLM-L6-v2) is for embeddings ONLY — never use the optional LLM (Mistral 7B) for embeddings
- Cold-start users (no ratings) get pure content-based recommendations (alpha forced to 1.0)
- Cache invalidation: user recommendation cache is invalidated when a new rating is posted
- The system must run fully locally with NO paid APIs or API keys

## Subagents
All custom subagents live in `.claude/agents/`. Use them to keep the main context window clean.

| Agent | When to Use |
|-------|-------------|
| `codebase-researcher` | Any codebase exploration, architecture questions, or finding code patterns. Use before making changes you're unsure about. |
| `pre-change` | **Before every code change.** Identifies affected files, existing tests, dependencies, and risks. |
| `post-change` | **After every code change.** Runs tests, checks regressions, writes missing tests, and produces a commit message. |
| `test-runner` | Quick test verification without full post-change review. Use to check if a specific test passes. |
| `data-pipeline` | When working on pipeline code (cleaner, embedder, FAISS, ALS). Validates data integrity and artifact output. |
| `api-tester` | When modifying API endpoints. Sends test requests and validates responses against expected schemas. |
| `doc-fetcher` | **Before answering any library-specific question.** Fetches current docs for pgvector, FAISS, implicit, sentence-transformers, SQLAlchemy, FastAPI. Prevents stale advice. |
| `build-error-resolver` | When pip install fails, imports break, or ML dependencies conflict. Diagnoses faiss-cpu, implicit, torch, asyncpg build issues. |
| `db-migration-reviewer` | **Before running any Alembic migration.** Catches destructive operations, pgvector autogenerate bugs, missing indexes, and extension ordering issues. |
| `security-reviewer` | When touching SQL queries, pgvector operators, user input handling, search endpoints, or file operations. Checks for injection, DoS, data exposure. |

## Automatic Agent Routing

IMPORTANT: You MUST automatically activate the appropriate subagent(s) based on what the user's prompt involves. Do NOT wait for the user to ask for a specific agent — detect the intent and route automatically. Multiple agents can be triggered by a single prompt.

### Trigger Rules (evaluate EVERY prompt against ALL rules)

**`pre-change`** — Auto-trigger BEFORE any code modification when:
- The user asks to add, change, fix, refactor, or delete code
- The user asks to implement a feature, fix a bug, or update a file
- ANY task that will result in editing or creating source files

**`post-change`** — Auto-trigger AFTER any code modification when:
- You have just finished writing or editing source files
- ALWAYS runs after `pre-change` work is complete — no exceptions
- Produces the commit message and verifies nothing broke

**`doc-fetcher`** — Auto-trigger when the prompt involves:
- Questions about pgvector, FAISS, implicit, sentence-transformers, SQLAlchemy, FastAPI, Alembic, asyncpg, Pydantic, or Redis APIs
- "How do I use...", "What's the API for...", "Does X support..."
- Writing code that calls library-specific methods (e.g., `model.encode()`, `index.search()`, `<=>` operator)
- Debugging library-specific errors or unexpected behavior

**`build-error-resolver`** — Auto-trigger when the prompt involves:
- `pip install` failures or dependency conflicts
- `ImportError`, `ModuleNotFoundError`, or `dlopen` errors
- "X won't install", "import fails", "build error", "dependency conflict"
- Any error traceback mentioning faiss, implicit, torch, asyncpg, or numpy

**`db-migration-reviewer`** — Auto-trigger when the prompt involves:
- Creating or running Alembic migrations (`alembic revision`, `alembic upgrade`)
- Changing SQLAlchemy models (adding/removing/modifying columns, tables, constraints)
- Any database schema change
- MUST run before `alembic upgrade head` is executed

**`security-reviewer`** — Auto-trigger when the prompt involves:
- Writing or modifying SQL queries (especially raw SQL, ILIKE, pgvector operators)
- Writing or modifying API endpoints that accept user input
- Touching authentication, authorization, or user data
- File operations with paths that could come from input
- Pickle loading, deserialization, or model file handling
- Search functionality, CORS configuration, or error response formatting

**`data-pipeline`** — Auto-trigger when the prompt involves:
- Modifying files in `src/cinematch/pipeline/` or `scripts/`
- Changes to data cleaning, embedding generation, FAISS index building, or ALS training
- Questions about data formats, parquet schemas, or artifact files
- "Re-run the pipeline", "data looks wrong", "embeddings don't match"

**`api-tester`** — Auto-trigger when the prompt involves:
- Adding or modifying API endpoints in `src/cinematch/api/`
- Changing Pydantic schemas in `src/cinematch/schemas/`
- "Test the endpoint", "does the API work", "check the response"

**`codebase-researcher`** — Auto-trigger when the prompt involves:
- "Where is...", "How does... work", "Find the code that..."
- Understanding architecture, tracing data flow, finding patterns
- Any exploration needed before you can confidently make a change
- When you're unsure what exists or how something is implemented

**`test-runner`** — Auto-trigger when the prompt involves:
- "Run the tests", "does this test pass", "check if tests are green"
- Quick verification without the full post-change review

### Routing Examples

| User Prompt | Agents Triggered (in order) |
|------------|----------------------------|
| "Add a genre filter to the search endpoint" | `pre-change` → (make changes) → `security-reviewer` + `api-tester` → `post-change` |
| "Why is FAISS returning wrong results?" | `doc-fetcher` + `codebase-researcher` |
| "pip install keeps failing on implicit" | `build-error-resolver` |
| "Create migration for adding a tags column" | `pre-change` → (make changes) → `db-migration-reviewer` → `post-change` |
| "How does the hybrid recommender combine scores?" | `codebase-researcher` |
| "Fix the SQL injection in movie search" | `pre-change` → (make changes) → `security-reviewer` → `post-change` |
| "Update the embedder to use a different model" | `doc-fetcher` → `pre-change` → (make changes) → `data-pipeline` → `post-change` |
| "Run tests for the recommendation service" | `test-runner` |
| "Add rating validation to the API" | `pre-change` → (make changes) → `security-reviewer` + `api-tester` → `post-change` |
| "What does the ALS recommend method return?" | `doc-fetcher` |

### Execution Order
When multiple agents are triggered, follow this order:
1. **Research phase**: `codebase-researcher`, `doc-fetcher` (run in parallel if both needed)
2. **Pre-analysis**: `pre-change` (only if code will be modified)
3. **Implementation**: Make the actual code changes
4. **Validation phase**: `security-reviewer`, `db-migration-reviewer`, `data-pipeline`, `api-tester` (run relevant ones in parallel)
5. **Finalization**: `post-change` (always last when code was modified)

## Workflow
- IMPORTANT: Only do what is explicitly asked. Do NOT add extra features, refactors, or improvements beyond the request.
- IMPORTANT: Agents are triggered AUTOMATICALLY based on the rules above. Do not ask the user which agent to use — just activate the right ones.
- IMPORTANT: `pre-change` before code edits and `post-change` after code edits are MANDATORY — never skip them.
- IMPORTANT: When in doubt about whether to trigger an agent, trigger it. False positives are cheap; missed issues are expensive.
- Every code change must come with a 3-6 word git commit message (produced by `post-change`).
- Every new feature or change must include tests.
- New changes must not break existing functionality — always run the relevant test suite after changes.

## Context Management
- Use subagents for all codebase research — keeps main context clean
- When compacting, ALWAYS preserve: list of modified files, test commands run, any failing test details, and current task progress
- Prefer reading specific files over broad exploration
- Run single tests first, full suite only for final verification
- Maximize parallel agent execution: research agents run together, validation agents run together
