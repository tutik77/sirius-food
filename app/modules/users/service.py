"""
Слой бизнес-логики модуля пользователей (круги Entities и Use Cases).
"""
from app.domain.entities import User
from app.modules.users.exceptions import (
    EmailAlreadyExistsError,
    TopUpLimitExceededError,
    UserBlockedError,
    UserNotFoundError,
)
from app.modules.users.repository import UserRepository

MAX_TOP_UP = 50000


class UserService:
    """Бизнес-правила регистрации и пополнения баланса."""

    def __init__(self, repository: UserRepository):
        self.repository = repository

    def register(self, email: str, phone: str | None = None) -> User:
        """Регистрирует пользователя с нулевым балансом. Email должен быть уникальным."""
        if self.repository.get_by_email(email) is not None:
            raise EmailAlreadyExistsError()

        user = User(id=None, email=email, phone=phone, balance=0.0, is_blocked=False)
        return self.repository.add(user)

    def top_up(self, user_id: int, amount: float) -> User:
        """Пополняет баланс. Заблокированным нельзя, разовый лимит — MAX_TOP_UP."""
        user = self.repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()
        if user.is_blocked:
            raise UserBlockedError()
        if amount > MAX_TOP_UP:
            raise TopUpLimitExceededError()

        user.balance += amount
        return self.repository.update(user)
