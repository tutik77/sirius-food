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
    REDIS_URL: str = "redis://localhost:6379"
    DEBUG: bool = False
    ALLOWED_ORIGINS: list[str] = []

    # Реализация репозиториев: postgres (SQLAlchemy) или memory (in-memory хранилище).
    STORAGE_BACKEND: Literal["postgres", "memory"] = "postgres"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BCRYPT_ROUNDS: int = 12


settings = Settings()
