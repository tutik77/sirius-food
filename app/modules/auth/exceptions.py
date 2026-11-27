from app.domain.errors import ForbiddenError, UnauthorizedError


class InvalidCredentialsError(UnauthorizedError):
    message = "Неверный email или пароль"


class InvalidTokenError(UnauthorizedError):
    message = "Недействительный токен"


class TokenReuseError(UnauthorizedError):
    message = "Refresh-токен уже был использован. Все сессии пользователя завершены"


class UserBlockedError(ForbiddenError):
    message = "Пользователь заблокирован"
