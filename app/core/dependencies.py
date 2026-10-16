"""
Зависимости безопасности для роутеров (транспортный слой).

get_current_user — аутентификация: кто делает запрос (по access-токену).
require_role — авторизация по роли: можно ли ему вызывать этот эндпоинт.
Права на конкретный объект (чей это заказ) проверяет уже Service-слой.
"""
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from app.container import get_user_repository
from app.core.jwt import ACCESS, TokenError, decode_token
from app.domain.entities import User
from app.modules.users.repository import UserRepository

# Токен берётся из заголовка Authorization: Bearer <token>.
# tokenUrl указывает Swagger, куда отправлять логин/пароль для кнопки Authorize.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

CREDENTIALS_ERROR = HTTPException(
    status_code=401,
    detail="Недействительный токен",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    users: UserRepository = Depends(get_user_repository),
) -> User:
    """
    Извлекает пользователя из access-токена.
    401 — токен невалиден или пользователя нет; 403 — пользователь заблокирован.
    """
    try:
        user_id = decode_token(token, ACCESS)
    except TokenError:
        raise CREDENTIALS_ERROR

    user = users.get_by_id(user_id)
    if user is None:
        raise CREDENTIALS_ERROR
    if user.is_blocked:
        raise HTTPException(status_code=403, detail="Пользователь заблокирован")
    return user


def require_role(*roles: str):
    """Dependency: пропускает только пользователей с одной из ролей, иначе 403."""

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Доступ запрещён")
        return current_user

    return checker
