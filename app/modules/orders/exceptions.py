from app.domain.errors import BusinessRuleError, ForbiddenError, NotFoundError


class UserNotFoundError(NotFoundError):
    message = "Пользователь не найден"


class MenuItemNotFoundError(NotFoundError):
    message = "Блюдо не найдено"


class MenuItemUnavailableError(BusinessRuleError):
    message = "Блюдо недоступно"


class InsufficientFundsError(BusinessRuleError):
    message = "Недостаточно средств на балансе студента"


class OrderNotFoundError(NotFoundError):
    message = "Заказ не найден"


class AccessDeniedError(ForbiddenError):
    message = "Нет доступа к чужому заказу"


class OrderCannotBeCancelledError(BusinessRuleError):
    message = "Отменить можно только заказ, который ещё готовится"


class OrderCannotBePaidError(BusinessRuleError):
    message = "Оплатить можно только заказ, который ещё не оплачен и не отменён"
