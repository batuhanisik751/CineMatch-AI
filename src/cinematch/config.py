"""Application configuration via environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="CINEMATCH_", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://cinematch:cinematch@localhost:5432/cinematch"
    database_url_sync: str = "postgresql://cinematch:cinematch@localhost:5432/cinematch"
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
    hybrid_alpha: float = 0.5

    # LLM (optional)
    llm_enabled: bool = False
    llm_model_name: str = "mistral"
    llm_base_url: str = "http://localhost:11434"
    llm_backend: str = "ollama"

    # Data paths
    data_raw_dir: str = "data/raw"
    data_processed_dir: str = "data/processed"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
