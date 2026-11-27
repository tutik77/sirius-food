class DomainError(Exception):
    message = "Ошибка бизнес-логики"

    def __init__(self, message: str | None = None):
        self.message = message or self.message
        super().__init__(self.message)


class NotFoundError(DomainError):
    ...


class UnauthorizedError(DomainError):
    ...


class ForbiddenError(DomainError):
    ...


class BusinessRuleError(DomainError):
    ...


class ServiceUnavailableError(DomainError):
    message = "Сервис временно недоступен"
