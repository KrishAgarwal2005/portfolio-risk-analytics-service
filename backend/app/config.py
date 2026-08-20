from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "TradeSense Risk API"
    environment: str = "development"

    database_url: str = "postgresql+psycopg2://tradesense:tradesense@localhost:5432/tradesense"

    redis_url: str = "redis://localhost:6379/0"
    risk_cache_ttl_seconds: int = 300

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    default_var_confidence: float = 0.95
    default_lookback_days: int = 252


@lru_cache
def get_settings() -> Settings:
    return Settings()
