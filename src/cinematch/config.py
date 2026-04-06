"""Application configuration via environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="CINEMATCH_", extra="ignore")

    # Database (required — no insecure defaults)
    database_url: SecretStr
    database_url_sync: SecretStr
    db_pool_size: int = 20
    db_max_overflow: int = 10

    # Database connection security
    database_ssl_mode: str = "disable"
    database_statement_timeout: int = 30000
    db_pool_recycle: int = 1800
    db_pool_pre_ping: bool = True

    # Redis (required — no insecure defaults)
    redis_url: SecretStr
    cache_ttl_seconds: int = 3600

    # Lightweight mode (skip ML model loading; use pgvector + HF API + cache table)
    lightweight_mode: bool = False
    hf_inference_url: str = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"
    hf_api_token: SecretStr | None = None

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
    hybrid_diversity_lambda: float = 0.7
    hybrid_sequel_penalty: float = 0.5

    # LLM (optional — Ollama local or Groq cloud)
    llm_enabled: bool = True
    llm_model_name: str = "mistral"
    llm_base_url: str = "http://localhost:11434"
    llm_backend: str = "ollama"
    llm_api_key: SecretStr | None = None
    llm_rerank_enabled: bool = True
    llm_rerank_timeout: float = 60.0
    llm_rerank_candidates: int = 50

    # Data paths
    data_raw_dir: str = "data/raw"
    data_processed_dir: str = "data/processed"

    # Onboarding
    onboarding_threshold: int = 10

    # Import/Export
    import_max_rows: int = 10_000
    import_max_file_size_mb: int = 5

    # Authentication (required — no insecure defaults)
    secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440

    # API
    api_host: str = "0.0.0.0"  # nosec B104 - container binding
    api_port: int = 8000
    debug: bool = False

    # Domain (for production HTTPS / Caddy TLS)
    domain: str = "localhost"

    # CORS origins (JSON list; defaults work for local dev)
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    # CORS allowed methods (restrict in production; defaults cover all API verbs)
    cors_methods: list[str] = [
        "GET",
        "POST",
        "PATCH",
        "PUT",
        "DELETE",
        "OPTIONS",
    ]
    # CORS allowed headers
    cors_headers: list[str] = ["Content-Type", "Authorization"]

    # Security headers
    hsts_enabled: bool = True
    content_security_policy: str = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' https://image.tmdb.org data:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )

    # Audit logging
    audit_log_file: str = "logs/audit.log"
    audit_log_enabled: bool = True

    # Dependency scanning
    dep_scan_timeout: int = 120

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_default: str = "100/minute"
    rate_limit_auth: str = "5/minute"
    rate_limit_recommendations: str = "10/minute"
    rate_limit_search: str = "30/minute"
    rate_limit_csv_import: str = "3/minute"


@lru_cache
def get_settings() -> Settings:
    return Settings()
