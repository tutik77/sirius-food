"""
Транспортный слой модуля пользователей (круг Frameworks & Drivers).
"""
from fastapi import APIRouter, Depends, HTTPException

from app.container import get_user_service
from app.domain.errors import DomainError
from app.http_errors import to_http
from app.modules.users.service import UserService
from app.schemas import UserCreate

router = APIRouter()


@router.post("/register")
def register_user(payload: UserCreate, service: UserService = Depends(get_user_service)):
    # Формат email проверяет Pydantic (EmailStr), длину телефона — роутер.
    # Уникальность email — бизнес-правило, его проверяет сервис.
    if payload.phone and len(payload.phone) < 10:
        raise HTTPException(status_code=400, detail="Некорректный формат номера телефона")

    try:
        user = service.register(email=payload.email, phone=payload.phone)
    except DomainError as e:
        raise to_http(e)

    return {"status": "success", "user_id": user.id, "email": user.email}


@router.post("/{user_id}/topup")
def top_up_balance(user_id: int, amount: float, service: UserService = Depends(get_user_service)):
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Сумма пополнения должна быть положительной")

    try:
        user = service.top_up(user_id, amount)
    except DomainError as e:
        raise to_http(e)

    return {"status": "success", "new_balance": user.balance}
