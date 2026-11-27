from app.domain.errors import BusinessRuleError


class NotEnoughPointsError(BusinessRuleError):
    message = "Недостаточно баллов"


class PointsLimitExceededError(BusinessRuleError):
    message = "Баллами можно оплатить не больше 50 % суммы заказа"
