from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    SECRET_KEY: str = Field(min_length=32)
    DATABASE_URL: str
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT_SECONDS: int = 10
    REDIS_URL: str = "redis://127.0.0.1:6379"
    DELIVERY_GRPC_ADDR: str = "127.0.0.1:50051"
    RABBITMQ_URL: str = "amqp://sirius:sirius@127.0.0.1:5672/"
    SENTRY_DSN: str | None = None
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None

    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    ASSISTANT_MODEL: str = "google/gemini-3.8-flash"
    EMBEDDING_MODEL: str = "openai/text-embedding-ada-002"
    QDRANT_URL: str = "http://127.0.0.1:6333"
    ASSISTANT_TIMEOUT_SECONDS: int = 30
    DEBUG: bool = False
    ALLOWED_ORIGINS: list[str] = []

    STORAGE_BACKEND: Literal["postgres", "memory"] = "postgres"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BCRYPT_ROUNDS: int = 12


settings = Settings()
