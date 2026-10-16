"""
Хеширование паролей (bcrypt) и refresh-токенов (SHA-256).
"""
import hashlib

from passlib.context import CryptContext

from app.core.config import settings

# bcrypt — медленный хеш с солью: перебор паролей по утёкшей базе очень дорог.
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.BCRYPT_ROUNDS,
)

# Хеш «пустышка» для выравнивания времени ответа, когда пользователь не найден:
# иначе по скорости ответа на /auth/login можно перебирать существующие email.
DUMMY_PASSWORD_HASH = pwd_context.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    """Возвращает bcrypt-хеш пароля."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str | None) -> bool:
    """Проверяет пароль. Для пустого или непригодного хеша (например, '!') — False."""
    if not hashed:
        return False
    try:
        return pwd_context.verify(plain, hashed)
    except ValueError:
        return False


def hash_token(token: str) -> str:
    """
    SHA-256 от refresh-токена для хранения в БД.

    Токен — случайная строка большой длины, поэтому медленный bcrypt не нужен,
    а детерминированный хеш позволяет искать запись по токену.
    """
    return hashlib.sha256(token.encode()).hexdigest()
