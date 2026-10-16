"""
Трансляция доменных исключений в HTTP-ответы (транспортный слой).
"""
from fastapi import HTTPException

from app.domain.errors import BusinessRuleError, DomainError, ForbiddenError, NotFoundError

STATUS_BY_ERROR = {
    NotFoundError: 404,
    ForbiddenError: 403,
    BusinessRuleError: 400,
}


def to_http(error: DomainError) -> HTTPException:
    """Возвращает HTTPException с кодом, соответствующим типу доменной ошибки."""
    for error_type, status_code in STATUS_BY_ERROR.items():
        if isinstance(error, error_type):
            return HTTPException(status_code=status_code, detail=error.message)
    return HTTPException(status_code=400, detail=error.message)
