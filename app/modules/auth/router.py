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
    try:
        return service.login(payload.email, payload.password)
    except DomainError as e:
        raise to_http(e) from e


@router.post("/token", response_model=TokenPair, dependencies=[Depends(rate_limit(5, 60))])
def login_form(
    form: OAuth2PasswordRequestForm = Depends(),
    service: AuthService = Depends(get_auth_service),
):
    try:
        return service.login(form.username, form.password)
    except DomainError as e:
        raise to_http(e) from e


@router.post("/refresh", response_model=TokenPair, dependencies=[Depends(rate_limit(10, 60))])
def refresh(payload: RefreshSchema, service: AuthService = Depends(get_auth_service)):
    try:
        return service.refresh(payload.refresh_token)
    except DomainError as e:
        raise to_http(e) from e


@router.post("/logout")
def logout(payload: RefreshSchema, service: AuthService = Depends(get_auth_service)):
    service.logout(payload.refresh_token)
    return {"status": "success"}
