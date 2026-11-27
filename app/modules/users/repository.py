from abc import ABC, abstractmethod
from dataclasses import replace

from sqlalchemy.orm import Session

from app import models
from app.domain.entities import User
from app.mappers import to_user
from app.memory_storage import InMemoryStorage, copy


class UserRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_id: int) -> User | None:
        ...

    @abstractmethod
    def get_by_email(self, email: str) -> User | None:
        ...

    @abstractmethod
    def add(self, user: User) -> User:
        ...

    @abstractmethod
    def update(self, user: User) -> User:
        ...


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        row = self.db.get(models.User, user_id)
        return to_user(row) if row else None

    def get_by_email(self, email: str) -> User | None:
        row = self.db.query(models.User).filter(models.User.email == email).first()
        return to_user(row) if row else None

    def add(self, user: User) -> User:
        row = models.User()
        self._fill(row, user)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return to_user(row)

    def update(self, user: User) -> User:
        row = self.db.get(models.User, user.id)
        self._fill(row, user)
        self.db.commit()
        self.db.refresh(row)
        return to_user(row)

    def _fill(self, row: models.User, user: User) -> None:
        row.email = user.email
        row.phone = user.phone
        row.balance = user.balance
        row.is_blocked = user.is_blocked
        row.password_hash = user.password_hash
        row.role = self.db.query(models.Role).filter(models.Role.name == user.role).one()


class InMemoryUserRepository(UserRepository):
    def __init__(self, storage: InMemoryStorage):
        self.storage = storage

    def get_by_id(self, user_id: int) -> User | None:
        return copy(self.storage.users.get(user_id))

    def get_by_email(self, email: str) -> User | None:
        found = next((u for u in self.storage.users.values() if u.email == email), None)
        return copy(found)

    def add(self, user: User) -> User:
        saved = replace(user, id=self.storage.next_id("users"))
        self.storage.users[saved.id] = saved
        return copy(saved)

    def update(self, user: User) -> User:
        self.storage.users[user.id] = copy(user)
        return copy(user)
