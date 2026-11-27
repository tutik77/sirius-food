from app.domain.errors import BusinessRuleError, NotFoundError


class PromoCodeNotFoundError(NotFoundError):
    message = "Промокод не найден"


class PromoCodeInactiveError(BusinessRuleError):
    message = "Промокод не активен или срок его действия истёк"


class PromoCodeExhaustedError(BusinessRuleError):
    message = "Промокод исчерпан"


class PromoCodeMinAmountError(BusinessRuleError):
    message = "Сумма заказа меньше минимальной для промокода"


class PromoCodeAlreadyUsedError(BusinessRuleError):
    message = "Вы уже применяли этот промокод"


class PromoCodeDuplicateError(BusinessRuleError):
    message = "Промокод с таким кодом уже существует"


class InvalidPromoCodeError(BusinessRuleError):
    message = "Некорректные параметры промокода"
