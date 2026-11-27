from app.domain.errors import BusinessRuleError, ForbiddenError, NotFoundError


class OrderNotFoundError(NotFoundError):
    message = "Заказ не найден"


class OrderNotPaidError(BusinessRuleError):
    message = "Курьера можно назначить только на оплаченный заказ"


class CourierNotFoundError(NotFoundError):
    message = "Курьер не найден"


class CourierBlockedError(ForbiddenError):
    message = "Курьер заблокирован и не может быть назначен"


class NotACourierError(BusinessRuleError):
    message = "Назначить можно только пользователя с ролью courier"


class CourierBusyError(BusinessRuleError):
    message = "У курьера уже есть активная доставка"


class DeliveryNotFoundError(NotFoundError):
    message = "Доставка не найдена"


class DeliveryAccessDeniedError(ForbiddenError):
    message = "Нет доступа к чужой доставке"


class DeliveryAlreadyCompletedError(BusinessRuleError):
    message = "Доставка уже завершена"


class DeliveryCancelledError(BusinessRuleError):
    message = "Отменённую доставку нельзя завершить"


class NoFreeCourierError(BusinessRuleError):
    message = "Нет свободного курьера"
