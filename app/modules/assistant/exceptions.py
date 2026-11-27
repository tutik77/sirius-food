from app.domain.errors import ForbiddenError, NotFoundError


class MessageNotFoundError(NotFoundError):
    message = "Сообщение ассистента не найдено"


class ForeignMessageError(ForbiddenError):
    message = "Оценить можно только ответ на свой вопрос"
