"""
Транспортный слой модуля аутентификации.

/auth/login принимает JSON, /auth/token — форму OAuth2 (её использует кнопка
Authorize в Swagger, поле username — это email). Логика у них общая.
"""
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.container import get_auth_service
from app.core.rate_limit import rate_limit
from app.domain.errors import DomainError
from app.http_errors import to_http
from app.modules.auth.service import AuthService
from app.schemas import LoginSchema, RefreshSchema, TokenPair

router = APIRouter()


@router.post("/login", response_model=TokenPair, dependencies=[Depends(rate_limit(5, 60))])
def login(payload: LoginSchema, service: AuthService = Depends(get_auth_service)):
    """Аутентификация по email и паролю, выдача пары токенов."""
    try:
        return service.login(payload.email, payload.password)
    except DomainError as e:
        raise to_http(e)


@router.post("/token", response_model=TokenPair, dependencies=[Depends(rate_limit(5, 60))])
def login_form(
    form: OAuth2PasswordRequestForm = Depends(),
    service: AuthService = Depends(get_auth_service),
):
    """То же, что /auth/login, но в формате OAuth2-формы (для Swagger)."""
    try:
        return service.login(form.username, form.password)
    except DomainError as e:
        raise to_http(e)


@router.post("/refresh", response_model=TokenPair, dependencies=[Depends(rate_limit(10, 60))])
def refresh(payload: RefreshSchema, service: AuthService = Depends(get_auth_service)):
    """Обмен refresh-токена на новую пару. Старый refresh-токен после этого недействителен."""
    try:
        return service.refresh(payload.refresh_token)
    except DomainError as e:
        raise to_http(e)


@router.post("/logout")
def logout(payload: RefreshSchema, service: AuthService = Depends(get_auth_service)):
    """Отзыв refresh-токена."""
    service.logout(payload.refresh_token)
    return {"status": "success"}
