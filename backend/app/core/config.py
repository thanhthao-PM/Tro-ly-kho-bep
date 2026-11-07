from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


def to_sqlalchemy_url(url: str) -> str:
    """Accept postgresql:// and force the psycopg 3 driver."""
    if url.startswith("postgresql+psycopg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "production"] = "development"
    database_url: str = ""
    migration_database_url: str = ""
    supabase_url: str = ""
    jwt_mode: Literal["auto", "hs256", "jwks"] = "auto"
    supabase_jwt_secret: str = ""
    cors_origins: str = "http://localhost:5173"

    # Starting values from the implementation plan; to be load-tested.
    pool_size: int = 2
    max_overflow: int = 2
    pool_timeout: int = 10
    pool_recycle: int = 300

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
