"""
Unit-тесты AuthService без СУБД: вход, ротация refresh-токенов, выход.
"""
import pytest

from app.core.jwt import ACCESS, decode_token
from app.core.security import hash_password, hash_token
from app.domain.entities import User
from app.modules.auth.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    TokenReuseError,
    UserBlockedError,
)
from app.modules.auth.service import AuthService

PASSWORD = "StrongPass123"


@pytest.fixture
def service(repos):
    return AuthService(repos.auth)


@pytest.fixture
def anna(repos):
    return repos.users.add(User(id=None, email="anna@sirius.ru", password_hash=hash_password(PASSWORD)))


def test_login_returns_token_pair(service, anna):
    tokens = service.login("anna@sirius.ru", PASSWORD)

    assert tokens["token_type"] == "bearer"
    assert decode_token(tokens["access_token"], ACCESS) == anna.id


def test_refresh_token_is_stored_as_hash(service, repos, anna):
    tokens = service.login("anna@sirius.ru", PASSWORD)

    assert repos.auth.get_refresh_token(tokens["refresh_token"]) is None
    assert repos.auth.get_refresh_token(hash_token(tokens["refresh_token"])).user_id == anna.id


def test_wrong_password_and_unknown_email_give_same_error(service, anna):
    with pytest.raises(InvalidCredentialsError) as wrong_password:
        service.login("anna@sirius.ru", "wrong-password")
    with pytest.raises(InvalidCredentialsError) as unknown_email:
        service.login("nobody@sirius.ru", PASSWORD)

    assert wrong_password.value.message == unknown_email.value.message


def test_user_without_password_cannot_login(service, repos):
    """Пользователи, перенесённые миграцией, получили непригодный хеш '!'."""
    repos.users.add(User(id=None, email="old@sirius.ru", password_hash="!"))

    with pytest.raises(InvalidCredentialsError):
        service.login("old@sirius.ru", "!")


def test_blocked_user_cannot_login(service, repos):
    repos.users.add(
        User(id=None, email="blocked@sirius.ru", password_hash=hash_password(PASSWORD), is_blocked=True)
    )

    with pytest.raises(UserBlockedError):
        service.login("blocked@sirius.ru", PASSWORD)


def test_refresh_rotates_tokens(service, repos, anna):
    old = service.login("anna@sirius.ru", PASSWORD)

    new = service.refresh(old["refresh_token"])

    assert new["refresh_token"] != old["refresh_token"]
    assert repos.auth.get_refresh_token(hash_token(old["refresh_token"])).is_revoked
    assert not repos.auth.get_refresh_token(hash_token(new["refresh_token"])).is_revoked


def test_reused_refresh_token_revokes_whole_session(service, anna):
    """Украденный старый refresh-токен: повторное использование сбрасывает все сессии."""
    stolen = service.login("anna@sirius.ru", PASSWORD)["refresh_token"]
    legit = service.refresh(stolen)["refresh_token"]

    with pytest.raises(TokenReuseError):
        service.refresh(stolen)
    # Новый токен легитимного пользователя тоже отозван — нужно войти заново.
    with pytest.raises(TokenReuseError):
        service.refresh(legit)


def test_access_token_cannot_be_used_as_refresh(service, anna):
    tokens = service.login("anna@sirius.ru", PASSWORD)

    with pytest.raises(InvalidTokenError):
        service.refresh(tokens["access_token"])


def test_garbage_refresh_token(service):
    with pytest.raises(InvalidTokenError):
        service.refresh("not-a-jwt")


def test_logout_revokes_refresh_token(service, repos, anna):
    tokens = service.login("anna@sirius.ru", PASSWORD)

    service.logout(tokens["refresh_token"])

    assert repos.auth.get_refresh_token(hash_token(tokens["refresh_token"])).is_revoked
    with pytest.raises(TokenReuseError):
        service.refresh(tokens["refresh_token"])
