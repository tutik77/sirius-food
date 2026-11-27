from fastapi import APIRouter, Depends, HTTPException

from app.container import get_user_service
from app.core.dependencies import get_current_user, require_role
from app.core.rate_limit import rate_limit
from app.domain.entities import Role, User
from app.domain.errors import DomainError
from app.http_errors import to_http
from app.modules.users.service import UserService
from app.schemas import RoleUpdate, UserCreate, UserResponse

router = APIRouter()


@router.post("/register", dependencies=[Depends(rate_limit(5, 60))])
def register_user(payload: UserCreate, service: UserService = Depends(get_user_service)):
    if payload.phone and len(payload.phone) < 10:
        raise HTTPException(status_code=400, detail="Некорректный формат номера телефона")

    try:
        user = service.register(email=payload.email, password=payload.password, phone=payload.phone)
    except DomainError as e:
        raise to_http(e) from e

    return {"status": "success", "user_id": user.id, "email": user.email}


@router.get("/me", response_model=UserResponse)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/{user_id}/topup")
def top_up_balance(
    user_id: int,
    amount: float,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Сумма пополнения должна быть положительной")

    try:
        user = service.top_up(user_id, amount, actor=current_user)
    except DomainError as e:
        raise to_http(e) from e

    return {"status": "success", "new_balance": user.balance}


@router.patch("/{user_id}/role")
def change_role(
    user_id: int,
    payload: RoleUpdate,
    current_user: User = Depends(require_role(Role.ADMIN)),
    service: UserService = Depends(get_user_service),
):
    try:
        user = service.change_role(user_id, payload.role)
    except DomainError as e:
        raise to_http(e) from e

    return {"status": "success", "user_id": user.id, "role": user.role}
