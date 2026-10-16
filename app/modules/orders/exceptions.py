"""
Доменные исключения модуля заказов.
"""
from app.domain.errors import BusinessRuleError, NotFoundError


class UserNotFoundError(NotFoundError):
    message = "Пользователь не найден"


class MenuItemNotFoundError(NotFoundError):
    message = "Блюдо не найдено"


class MenuItemUnavailableError(BusinessRuleError):
    message = "Блюдо недоступно"


class InsufficientFundsError(BusinessRuleError):
    message = "Недостаточно средств на балансе студента"
