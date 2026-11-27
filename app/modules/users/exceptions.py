from app.domain.errors import BusinessRuleError, ForbiddenError, NotFoundError


class EmailAlreadyExistsError(BusinessRuleError):
    message = "Пользователь с таким email уже зарегистрирован"


class UserNotFoundError(NotFoundError):
    message = "Пользователь не найден"


class UserBlockedError(ForbiddenError):
    message = "Пользователь заблокирован. Пополнение невозможно"


class TopUpLimitExceededError(BusinessRuleError):
    message = "Максимальная сумма пополнения — 50000 рублей"


class ForeignBalanceError(ForbiddenError):
    message = "Пополнять можно только свой баланс"


class UnknownRoleError(BusinessRuleError):
    message = "Неизвестная роль"
