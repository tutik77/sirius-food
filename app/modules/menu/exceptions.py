from app.domain.errors import BusinessRuleError, NotFoundError


class MenuItemNotFoundError(NotFoundError):
    message = "Блюдо не найдено"


class InvalidPriceError(BusinessRuleError):
    message = "Цена должна быть положительной"


class MenuItemNameTooShortError(BusinessRuleError):
    message = "Название блюда слишком короткое"


class DuplicateMenuItemError(BusinessRuleError):
    message = "Блюдо с таким названием уже существует"
