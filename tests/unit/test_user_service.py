"""
Unit-тесты UserService. СУБД не запускается: репозитории — in-memory
или SQLAlchemy поверх SQLite в памяти (фикстура repos).
"""
import pytest

from app.domain.entities import User
from app.modules.users.exceptions import (
    EmailAlreadyExistsError,
    TopUpLimitExceededError,
    UserBlockedError,
    UserNotFoundError,
)
from app.modules.users.service import UserService


@pytest.fixture
def service(repos):
    return UserService(repos.users)


def test_register_creates_user_with_zero_balance(service, repos):
    user = service.register("anna@sirius.ru", phone="89990000001")

    assert user.id is not None
    assert user.balance == 0.0
    assert repos.users.get_by_email("anna@sirius.ru").id == user.id


def test_register_rejects_duplicate_email(service):
    service.register("anna@sirius.ru")

    with pytest.raises(EmailAlreadyExistsError):
        service.register("anna@sirius.ru")


def test_top_up_increases_balance(service):
    user = service.register("anna@sirius.ru")

    updated = service.top_up(user.id, 1500)

    assert updated.balance == 1500


def test_top_up_unknown_user(service):
    with pytest.raises(UserNotFoundError):
        service.top_up(999, 100)


def test_top_up_forbidden_for_blocked_user(service, repos):
    blocked = repos.users.add(User(id=None, email="blocked@sirius.ru", is_blocked=True))

    with pytest.raises(UserBlockedError):
        service.top_up(blocked.id, 100)


def test_top_up_limit_keeps_balance(service, repos):
    user = service.register("anna@sirius.ru")

    with pytest.raises(TopUpLimitExceededError):
        service.top_up(user.id, 50001)

    assert repos.users.get_by_id(user.id).balance == 0.0
