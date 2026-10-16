"""
Базовые доменные исключения.

Слой бизнес-логики сообщает о нарушении правил только через них и ничего
не знает про HTTP-статусы. Перевод в HTTP делает транспортный слой
(см. app/http_errors.py).
"""


class DomainError(Exception):
    """Нарушение правила предметной области."""

    message = "Ошибка бизнес-логики"

    def __init__(self, message: str | None = None):
        self.message = message or self.message
        super().__init__(self.message)


class NotFoundError(DomainError):
    """Запрошенный объект не существует."""


class UnauthorizedError(DomainError):
    """Не удалось подтвердить, кто выполняет запрос (неверный пароль, токен)."""


class ForbiddenError(DomainError):
    """Операция запрещена для этого субъекта: чужой объект, блокировка и т. п."""


class BusinessRuleError(DomainError):
    """Операция нарушает бизнес-правило."""
