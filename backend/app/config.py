"""Application settings.

Everything configurable comes from environment variables or a `.env` file at
the repository root (see `.env.example`). Nothing secret is hard-coded.
"""

from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent

_PLACEHOLDER_SECRET = "change-me-to-a-long-random-string"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_env: str = "development"
    app_version: str = "1.0.0"
    secret_key: str = _PLACEHOLDER_SECRET
    access_token_minutes: int = 480
    cookie_secure: bool = False
    cookie_name: str = "pm_session"

    # --- Network ---
    frontend_origin: str = "http://localhost:3000"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000

    # --- Storage ---
    storage_dir: Path = BACKEND_DIR / "storage"
    data_dir: Path = BACKEND_DIR / "data"
    eval_dir: Path = ROOT_DIR / "eval"
    database_url: str = ""

    # --- LLM ---
    llm_provider: str = "gemini"  # gemini | local | extractive
    gemini_api_key: str = Field(
        default="", validation_alias=AliasChoices("GEMINI_KEY", "GOOGLE_GEMINI_KEY")
    )
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_timeout_seconds: int = 30
    local_model: str = "Qwen/Qwen2.5-0.5B-Instruct"
    local_max_new_tokens: int = 220
    llm_max_output_tokens: int = 500

    # --- Retrieval ---
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    hf_offline: bool = True
    retrieve_candidates: int = 20
    rrf_k: int = 60
    top_k: int = 5
    # Refusal thresholds. `final` compares the cross-encoder logit of the best
    # passage; `baseline` compares cosine similarity. Tuned on the eval set.
    rerank_refusal_threshold: float = 0.0
    baseline_refusal_threshold: float = 0.35

    # --- Limits ---
    rate_limit_per_minute: int = 120
    auth_rate_limit_per_minute: int = 10
    probe_rate_limit_per_minute: int = 5
    max_upload_mb: int = 5
    max_question_chars: int = 2000
    max_resume_chars: int = 20000

    # --- Agent ---
    agent_max_steps: int = 8
    agent_step_retries: int = 2

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def db_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{(self.storage_dir / 'placemate.db').as_posix()}"

    @property
    def index_dir(self) -> Path:
        return self.storage_dir / "index"

    @property
    def upload_dir(self) -> Path:
        return self.storage_dir / "uploads"

    @property
    def log_dir(self) -> Path:
        return self.storage_dir / "logs"

    def resolve_secret_key(self) -> str:
        """Return the signing key.

        In production a real key is mandatory. In development, if none was
        set, a random key is generated once and kept in the ignored storage
        folder so sessions survive a restart without a secret living in git.
        """
        if self.secret_key and self.secret_key != _PLACEHOLDER_SECRET:
            return self.secret_key
        if self.is_production:
            raise RuntimeError("SECRET_KEY must be set in production.")
        key_file = self.storage_dir / "dev_secret.key"
        if key_file.exists():
            return key_file.read_text(encoding="utf-8").strip()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        key = secrets.token_urlsafe(48)
        key_file.write_text(key, encoding="utf-8")
        return key


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    for folder in (settings.storage_dir, settings.index_dir, settings.upload_dir, settings.log_dir):
        folder.mkdir(parents=True, exist_ok=True)
    return settings
