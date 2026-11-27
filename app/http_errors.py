from fastapi import HTTPException

from app.domain.errors import (
    BusinessRuleError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
    UnauthorizedError,
)

STATUS_BY_ERROR = {
    NotFoundError: 404,
    UnauthorizedError: 401,
    ForbiddenError: 403,
    BusinessRuleError: 400,
    ServiceUnavailableError: 503,
}


def to_http(error: DomainError) -> HTTPException:
    for error_type, status_code in STATUS_BY_ERROR.items():
        if isinstance(error, error_type):
            headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
            return HTTPException(status_code=status_code, detail=error.message, headers=headers)
    return HTTPException(status_code=400, detail=error.message)
