"""
Слой бизнес-логики модуля пользователей (круги Entities и Use Cases).
"""
from app.core.security import hash_password
from app.domain.entities import Role, User
from app.modules.users.exceptions import (
    EmailAlreadyExistsError,
    ForeignBalanceError,
    TopUpLimitExceededError,
    UnknownRoleError,
    UserBlockedError,
    UserNotFoundError,
)
from app.modules.users.repository import UserRepository

MAX_TOP_UP = 50000


class UserService:
    """Бизнес-правила регистрации, пополнения баланса и назначения ролей."""

    def __init__(self, repository: UserRepository):
        self.repository = repository

    def register(self, email: str, password: str, phone: str | None = None, role: str = Role.STUDENT) -> User:
        """
        Регистрирует пользователя с нулевым балансом. Email должен быть уникальным.
        Пароль сохраняется только в виде bcrypt-хеша.
        """
        if role not in Role.__members__.values():
            raise UnknownRoleError()
        if self.repository.get_by_email(email) is not None:
            raise EmailAlreadyExistsError()

        user = User(
            id=None,
            email=email,
            phone=phone,
            balance=0.0,
            is_blocked=False,
            password_hash=hash_password(password),
            role=role,
        )
        return self.repository.add(user)

    def top_up(self, user_id: int, amount: float, actor: User) -> User:
        """
        Пополняет баланс. Студент пополняет только свой баланс (защита от IDOR),
        администратор — любой. Заблокированным нельзя, разовый лимит — MAX_TOP_UP.
        """
        user = self.repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()
        if user.id != actor.id and not actor.is_admin:
            raise ForeignBalanceError()
        if user.is_blocked:
            raise UserBlockedError()
        if amount > MAX_TOP_UP:
            raise TopUpLimitExceededError()

        user.balance += amount
        return self.repository.update(user)

    def change_role(self, user_id: int, role: str) -> User:
        """Назначает пользователю роль. Право на операцию проверяет API-слой (admin)."""
        if role not in Role.__members__.values():
            raise UnknownRoleError()
        user = self.repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()

        user.role = role
        return self.repository.update(user)
