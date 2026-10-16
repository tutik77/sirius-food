"""
In-memory хранилище для in-memory реализаций репозиториев.

Один объект InMemoryStorage — это «база данных» из нескольких словарей.
Объекты копируются при записи и чтении, чтобы поведение совпадало
с настоящей СУБД: изменение полученной сущности без вызова репозитория
ничего не сохраняет.
"""
from collections import defaultdict
from dataclasses import replace
from typing import TypeVar

from app.domain.entities import Delivery, MenuItem, Order, RefreshToken, User

T = TypeVar("T")


class InMemoryStorage:
    def __init__(self):
        self.users: dict[int, User] = {}
        self.menu_items: dict[int, MenuItem] = {}
        self.orders: dict[int, Order] = {}
        self.deliveries: dict[int, Delivery] = {}
        # Ключ — хеш токена, как уникальный индекс token_hash в БД.
        self.refresh_tokens: dict[str, RefreshToken] = {}
        self._sequences: dict[str, int] = defaultdict(int)

    def next_id(self, table: str) -> int:
        """Аналог автоинкремента первичного ключа."""
        self._sequences[table] += 1
        return self._sequences[table]


def copy(entity: T | None) -> T | None:
    """Копия сущности (или None), чтобы снаружи нельзя было менять хранилище напрямую."""
    return replace(entity) if entity is not None else None
