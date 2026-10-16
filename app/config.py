"""
Настройки приложения из переменных окружения.
"""
import os

# Реализация репозиториев: postgres (SQLAlchemy) или memory (in-memory хранилище).
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "postgres")
