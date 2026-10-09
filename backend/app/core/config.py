from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Every secret comes from the environment (NFR-02)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "HR Copilot API"
    environment: Literal["local", "test", "staging", "production"] = "local"
    log_level: str = "INFO"

    # The API connects as a non-owner role so Postgres RLS is always enforced (PR-1).
    database_url: str
    # Migrations and seeding run as the table owner.
    migration_database_url: str

    jwt_secret: str = Field(min_length=16)
    # Shared password for the seeded demo personas; only the seed and tests read it.
    demo_password: str | None = None
    jwt_algorithm: str = "HS256"
    jwt_ttl_minutes: int = 60 * 8

    cors_origins: list[str] = ["http://localhost:3000"]

    embedding_dimensions: int = 1536


@lru_cache
def get_settings() -> Settings:
    return Settings()
