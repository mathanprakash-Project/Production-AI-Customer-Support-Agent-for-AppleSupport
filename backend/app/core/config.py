"""
Central configuration module using Pydantic Settings.
Reads environment variables with sensible production and local defaults.
"""

from pathlib import Path
from typing import Any, List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_NAME: str = "TweetSupport AI Support Agent"
    APP_ENV: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            if not v.strip().startswith("["):
                return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # Security & Auth
    JWT_SECRET: str = "tweetsupport-dev-jwt-secret-key-32-chars-minimum-prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ADMIN_EMAIL: str = "admin@tweetsupport.local"
    ADMIN_PASSWORD: str = "admin123"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://app:app@localhost:5432/tweetsupport",
        description="Async database connection string. Can be postgresql+asyncpg:// or sqlite+aiosqlite://",
    )
    DATABASE_SYNC_URL: str = Field(
        default="postgresql://app:app@localhost:5432/tweetsupport",
        description="Sync database connection string for Alembic migrations",
    )

    # LLM Settings
    LLM_PROVIDER: str = "ollama"  # ollama | openai | mock
    LLM_MODEL: str = "llama3.2:3b"
    LLM_BASE_URL: str = "http://localhost:11434"
    LLM_TEMPERATURE_CLASSIFIER: float = 0.0
    LLM_TEMPERATURE_DRAFTER: float = 0.3
    OPENAI_API_KEY: str = ""

    # Evaluation / Judge LLM
    JUDGE_PROVIDER: str = "ollama"  # ollama | openai | mock
    JUDGE_MODEL: str = "qwen2.5:14b-instruct"

    # Retrieval & Embeddings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384
    TOP_K_RETRIEVAL: int = 3

    # Brand & Ingestion
    BRAND: str = "AppleSupport"
    SUBSAMPLE_SIZE: int = 5000
    GOLDEN_SET_SIZE: int = 200

    # Paths
    PROJECT_ROOT_PATH: Path = PROJECT_ROOT
    DATA_DIR: Path = PROJECT_ROOT / "data"
    GOLDEN_SET_PATH: Path = BACKEND_DIR / "app" / "eval" / "golden_set" / "golden_set.jsonl"
    RULES_PATH: Path = BACKEND_DIR / "app" / "config" / "escalation_rules.yaml"


settings = Settings()

