"""
Unit-тесты UserService. СУБД не запускается: репозитории — in-memory
или SQLAlchemy поверх SQLite в памяти (фикстура repos).
"""
import pytest

from app.core.security import verify_password
from app.domain.entities import Role
from app.modules.users.exceptions import (
    EmailAlreadyExistsError,
    ForeignBalanceError,
    TopUpLimitExceededError,
    UnknownRoleError,
    UserBlockedError,
    UserNotFoundError,
)
from app.modules.users.service import UserService

PASSWORD = "StrongPass123"


@pytest.fixture
def service(repos):
    return UserService(repos.users)


def test_register_creates_student_with_zero_balance(service, repos):
    user = service.register("anna@sirius.ru", PASSWORD, phone="89990000001")

    assert user.id is not None
    assert user.balance == 0.0
    assert user.role == Role.STUDENT
    assert repos.users.get_by_email("anna@sirius.ru").id == user.id


def test_register_stores_only_bcrypt_hash(service, repos):
    user = service.register("anna@sirius.ru", PASSWORD)

    stored = repos.users.get_by_id(user.id)
    assert stored.password_hash != PASSWORD
    assert stored.password_hash.startswith("$2b$")
    assert verify_password(PASSWORD, stored.password_hash)


def test_register_rejects_duplicate_email(service):
    service.register("anna@sirius.ru", PASSWORD)

    with pytest.raises(EmailAlreadyExistsError):
        service.register("anna@sirius.ru", PASSWORD)


def test_top_up_own_balance(service, make_user):
    user = make_user()

    updated = service.top_up(user.id, 1500, actor=user)

    assert updated.balance == 1500


def test_top_up_foreign_balance_is_forbidden(service, make_user):
    owner, stranger = make_user(), make_user()

    with pytest.raises(ForeignBalanceError):
        service.top_up(owner.id, 100, actor=stranger)


def test_admin_can_top_up_any_balance(service, make_user):
    owner, admin = make_user(), make_user(role=Role.ADMIN)

    assert service.top_up(owner.id, 100, actor=admin).balance == 100


def test_top_up_unknown_user(service, make_user):
    with pytest.raises(UserNotFoundError):
        service.top_up(999, 100, actor=make_user(role=Role.ADMIN))


def test_top_up_forbidden_for_blocked_user(service, make_user):
    blocked = make_user(is_blocked=True)

    with pytest.raises(UserBlockedError):
        service.top_up(blocked.id, 100, actor=blocked)


def test_top_up_limit_keeps_balance(service, repos, make_user):
    user = make_user()

    with pytest.raises(TopUpLimitExceededError):
        service.top_up(user.id, 50001, actor=user)

    assert repos.users.get_by_id(user.id).balance == 0.0


def test_change_role(service, repos, make_user):
    user = make_user()

    service.change_role(user.id, Role.COOK)

    assert repos.users.get_by_id(user.id).role == Role.COOK


def test_change_role_rejects_unknown_role(service, make_user):
    with pytest.raises(UnknownRoleError):
        service.change_role(make_user().id, "superuser")
