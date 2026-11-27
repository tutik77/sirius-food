"""
Настройки приложения, загружаемые из переменных окружения и файла .env.

Secure by Default: SECRET_KEY и DATABASE_URL обязательны и не имеют значений
по умолчанию, режим отладки (и вместе с ним Swagger) по умолчанию выключен,
CORS по умолчанию не разрешает ни одного чужого домена.
"""
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    SECRET_KEY: str = Field(min_length=32)
    DATABASE_URL: str
    REDIS_URL: str = "redis://127.0.0.1:6379"
    DELIVERY_GRPC_ADDR: str = "127.0.0.1:50051"
    RABBITMQ_URL: str = "amqp://sirius:sirius@127.0.0.1:5672/"
    SENTRY_DSN: str | None = None
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None
    DEBUG: bool = False
    ALLOWED_ORIGINS: list[str] = []

    # Реализация репозиториев: postgres (SQLAlchemy) или memory (in-memory хранилище).
    STORAGE_BACKEND: Literal["postgres", "memory"] = "postgres"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BCRYPT_ROUNDS: int = 12


settings = Settings()
