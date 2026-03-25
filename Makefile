.PHONY: setup run test download pipeline seed evaluate clean lint format

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

format:         ## Format code
	ruff format src/ tests/
