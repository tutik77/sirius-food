from abc import ABC, abstractmethod
from dataclasses import replace

from sqlalchemy import update
from sqlalchemy.orm import Session

from app import models
from app.domain.entities import RefreshToken, User
from app.mappers import to_refresh_token, to_user
from app.memory_storage import InMemoryStorage, copy


class AuthRepository(ABC):
    @abstractmethod
    def get_user_by_email(self, email: str) -> User | None:
        ...

    @abstractmethod
    def get_user_by_id(self, user_id: int) -> User | None:
        ...

    @abstractmethod
    def add_refresh_token(self, token: RefreshToken) -> None:
        ...

    @abstractmethod
    def get_refresh_token(self, token_hash: str) -> RefreshToken | None:
        ...

    @abstractmethod
    def revoke_if_active(self, token_hash: str) -> bool:
        ...

    @abstractmethod
    def revoke_all_for_user(self, user_id: int) -> None:
        ...


class SqlAlchemyAuthRepository(AuthRepository):
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_email(self, email: str) -> User | None:
        row = self.db.query(models.User).filter(models.User.email == email).first()
        return to_user(row) if row else None

    def get_user_by_id(self, user_id: int) -> User | None:
        row = self.db.get(models.User, user_id)
        return to_user(row) if row else None

    def add_refresh_token(self, token: RefreshToken) -> None:
        self.db.add(
            models.RefreshToken(
                user_id=token.user_id,
                token_hash=token.token_hash,
                expires_at=token.expires_at,
                is_revoked=token.is_revoked,
            )
        )
        self.db.commit()

    def get_refresh_token(self, token_hash: str) -> RefreshToken | None:
        row = (
            self.db.query(models.RefreshToken)
            .filter(models.RefreshToken.token_hash == token_hash)
            .first()
        )
        return to_refresh_token(row) if row else None

    def revoke_if_active(self, token_hash: str) -> bool:
        result = self.db.execute(
            update(models.RefreshToken)
            .where(
                models.RefreshToken.token_hash == token_hash,
                models.RefreshToken.is_revoked.is_(False),
            )
            .values(is_revoked=True)
        )
        self.db.commit()
        return result.rowcount == 1

    def revoke_all_for_user(self, user_id: int) -> None:
        self.db.execute(
            update(models.RefreshToken)
            .where(models.RefreshToken.user_id == user_id)
            .values(is_revoked=True)
        )
        self.db.commit()


class InMemoryAuthRepository(AuthRepository):
    def __init__(self, storage: InMemoryStorage):
        self.storage = storage

    def get_user_by_email(self, email: str) -> User | None:
        found = next((u for u in self.storage.users.values() if u.email == email), None)
        return copy(found)

    def get_user_by_id(self, user_id: int) -> User | None:
        return copy(self.storage.users.get(user_id))

    def add_refresh_token(self, token: RefreshToken) -> None:
        saved = replace(token, id=self.storage.next_id("refresh_tokens"))
        self.storage.refresh_tokens[saved.token_hash] = saved

    def get_refresh_token(self, token_hash: str) -> RefreshToken | None:
        return copy(self.storage.refresh_tokens.get(token_hash))

    def revoke_if_active(self, token_hash: str) -> bool:
        token = self.storage.refresh_tokens.get(token_hash)
        if token is None or token.is_revoked:
            return False
        token.is_revoked = True
        return True

    def revoke_all_for_user(self, user_id: int) -> None:
        for token in self.storage.refresh_tokens.values():
            if token.user_id == user_id:
                token.is_revoked = True
