"""
Инфраструктурный слой модуля меню (круг Interface Adapters).

MenuRepository — абстрактный интерфейс, от которого зависит сервис.
Реализации: SqlAlchemyMenuRepository (PostgreSQL) и InMemoryMenuRepository.
"""
from abc import ABC, abstractmethod
from dataclasses import replace

from sqlalchemy.orm import Session

from app import models
from app.domain.entities import MenuItem
from app.mappers import to_menu_item
from app.memory_storage import InMemoryStorage, copy


class MenuRepository(ABC):
    """Хранилище блюд меню."""

    @abstractmethod
    def get_by_id(self, item_id: int) -> MenuItem | None:
        """Блюдо по идентификатору или None."""

    @abstractmethod
    def get_by_name(self, name: str) -> MenuItem | None:
        """Блюдо по точному названию или None."""

    @abstractmethod
    def list_all(self) -> list[MenuItem]:
        """Все блюда меню."""

    @abstractmethod
    def add(self, item: MenuItem) -> MenuItem:
        """Сохраняет новое блюдо, возвращает его с идентификатором."""

    @abstractmethod
    def update(self, item: MenuItem) -> MenuItem:
        """Сохраняет изменения существующего блюда."""


class SqlAlchemyMenuRepository(MenuRepository):
    """Реализация репозитория меню на SQLAlchemy ORM."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, item_id: int) -> MenuItem | None:
        row = self.db.get(models.MenuItem, item_id)
        return to_menu_item(row) if row else None

    def get_by_name(self, name: str) -> MenuItem | None:
        row = self.db.query(models.MenuItem).filter(models.MenuItem.name == name).first()
        return to_menu_item(row) if row else None

    def list_all(self) -> list[MenuItem]:
        return [to_menu_item(row) for row in self.db.query(models.MenuItem).order_by(models.MenuItem.id)]

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
    """Реализация репозитория меню в памяти процесса."""

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
