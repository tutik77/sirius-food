import json
import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, replace

from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from app import models
from app.domain.entities import MenuItem
from app.mappers import to_menu_item
from app.memory_storage import InMemoryStorage, copy

logger = logging.getLogger(__name__)

MENU_CACHE_KEY = "menu:all"
MENU_CACHE_TTL = 300
MENU_LOCK_KEY = "lock:menu:all"


class MenuRepository(ABC):
    @abstractmethod
    def get_by_id(self, item_id: int) -> MenuItem | None:
        ...

    @abstractmethod
    def get_by_name(self, name: str) -> MenuItem | None:
        ...

    @abstractmethod
    def list_all(self) -> list[MenuItem]:
        ...

    @abstractmethod
    def add(self, item: MenuItem) -> MenuItem:
        ...

    @abstractmethod
    def update(self, item: MenuItem) -> MenuItem:
        ...

    @abstractmethod
    def invalidate_cache(self) -> None:
        ...


class SqlAlchemyMenuRepository(MenuRepository):
    def __init__(self, db: Session, cache: Redis | None = None):
        self.db = db
        self.cache = cache

    def get_by_id(self, item_id: int) -> MenuItem | None:
        row = self.db.get(models.MenuItem, item_id)
        return to_menu_item(row) if row else None

    def get_by_name(self, name: str) -> MenuItem | None:
        row = self.db.query(models.MenuItem).filter(models.MenuItem.name == name).first()
        return to_menu_item(row) if row else None

    def list_all(self) -> list[MenuItem]:
        if self.cache is None:
            return self._load_all()

        cached = self._read_cache()
        if cached is not None:
            return cached

        try:
            with self.cache.lock(MENU_LOCK_KEY, timeout=10, blocking_timeout=5):
                cached = self._read_cache()
                if cached is not None:
                    return cached
                items = self._load_all()
                self._write_cache(items)
                return items
        except RedisError:
            logger.warning("Кеш меню недоступен, чтение из PostgreSQL")
            return self._load_all()

    def warm_up(self) -> None:
        if self.cache is not None:
            self._write_cache(self._load_all())

    def invalidate_cache(self) -> None:
        if self.cache is None:
            return
        try:
            self.cache.delete(MENU_CACHE_KEY)
        except RedisError:
            logger.warning("Не удалось сбросить кеш меню, он истечёт по TTL")

    def _load_all(self) -> list[MenuItem]:
        return [to_menu_item(row) for row in self.db.query(models.MenuItem).order_by(models.MenuItem.id)]

    def _read_cache(self) -> list[MenuItem] | None:
        try:
            raw = self.cache.get(MENU_CACHE_KEY)
        except RedisError:
            return None
        return [MenuItem(**item) for item in json.loads(raw)] if raw else None

    def _write_cache(self, items: list[MenuItem]) -> None:
        payload = json.dumps([asdict(item) for item in items], ensure_ascii=False)
        self.cache.set(MENU_CACHE_KEY, payload, ex=MENU_CACHE_TTL)

    def add(self, item: MenuItem) -> MenuItem:
        row = models.MenuItem(name=item.name, price=item.price, is_available=item.is_available)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return to_menu_item(row)

    def update(self, item: MenuItem) -> MenuItem:
        row = self.db.get(models.MenuItem, item.id)
        row.name = item.name
        row.price = item.price
        row.is_available = item.is_available
        self.db.commit()
        self.db.refresh(row)
        return to_menu_item(row)


class InMemoryMenuRepository(MenuRepository):
    def __init__(self, storage: InMemoryStorage):
        self.storage = storage

    def get_by_id(self, item_id: int) -> MenuItem | None:
        return copy(self.storage.menu_items.get(item_id))

    def get_by_name(self, name: str) -> MenuItem | None:
        found = next((i for i in self.storage.menu_items.values() if i.name == name), None)
        return copy(found)

    def list_all(self) -> list[MenuItem]:
        return [copy(i) for i in self.storage.menu_items.values()]

    def add(self, item: MenuItem) -> MenuItem:
        saved = replace(item, id=self.storage.next_id("menu_items"))
        self.storage.menu_items[saved.id] = saved
        return copy(saved)

    def update(self, item: MenuItem) -> MenuItem:
        self.storage.menu_items[item.id] = copy(item)
        return copy(item)

    def invalidate_cache(self) -> None:
        ...
