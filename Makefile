.PHONY: setup run test download pipeline seed evaluate clean lint format prod-build prod-up prod-down prod-logs

setup:          ## Install dependencies and run migrations
	pip install -e ".[dev]"
	chflags -R nohidden .venv
	alembic upgrade head

run:            ## Start the FastAPI development server
	PYTHONPATH=src uvicorn cinematch.main:app --reload --reload-dir src --host 0.0.0.0 --port 8000

test:           ## Run test suite
	PYTHONPATH=src pytest tests/ -v --cov=cinematch

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

format:         ## Format code
	ruff format src/ tests/

prod-build:     ## Build frontend and production Docker images
	cd frontend && npm run build
	docker compose -f docker-compose.prod.yml build

prod-up:        ## Start production stack (HTTPS via Caddy)
	docker compose -f docker-compose.prod.yml up -d

prod-down:      ## Stop production stack
	docker compose -f docker-compose.prod.yml down

prod-logs:      ## Tail production logs
	docker compose -f docker-compose.prod.yml logs -f
