"""
Консольные команды администратора.

Пример: первый администратор (через API его создать нельзя — регистрация
всегда выдаёт роль student, а назначать роли может только admin):

    python -m app.cli create-user admin@sirius.ru 'StrongPassword1' --role admin

Команда использует тот же UserService, что и API: бизнес-логика
не привязана к HTTP и переиспользуется из любого входа.
"""
import argparse
import getpass

from app.database import SessionLocal
from app.domain.entities import Role
from app.domain.errors import DomainError
from app.modules.users.repository import SqlAlchemyUserRepository
from app.modules.users.service import UserService


def create_user(email: str, password: str | None, role: str) -> None:
    password = password or getpass.getpass("Пароль: ")
    with SessionLocal() as db:
        service = UserService(SqlAlchemyUserRepository(db))
        try:
            user = service.register(email=email, password=password, role=role)
        except DomainError as e:
            raise SystemExit(f"Ошибка: {e.message}")
    print(f"Создан пользователь id={user.id} email={user.email} роль={user.role}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create-user", help="создать пользователя с ролью")
    create.add_argument("email")
    create.add_argument("password", nargs="?", help="если не указан, будет запрошен")
    create.add_argument("--role", choices=[r.value for r in Role], default=Role.STUDENT.value)

    args = parser.parse_args()
    if args.command == "create-user":
        create_user(args.email, args.password, args.role)


if __name__ == "__main__":
    main()
