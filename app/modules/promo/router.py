from fastapi import APIRouter, Depends

from app.container import get_promo_service
from app.core.dependencies import require_role
from app.domain.entities import PromoCode, Role, User
from app.domain.errors import DomainError
from app.http_errors import to_http
from app.modules.promo.service import PromoService
from app.schemas import PromoCodeCreate, PromoCodeResponse

router = APIRouter()

admin_only = require_role(Role.ADMIN)


@router.post("", response_model=PromoCodeResponse, status_code=201)
def create_promo_code(
    payload: PromoCodeCreate,
    current_user: User = Depends(admin_only),
    service: PromoService = Depends(get_promo_service),
):
    try:
        return service.create(PromoCode(id=None, **payload.model_dump()))
    except DomainError as e:
        raise to_http(e) from e


@router.get("", response_model=list[PromoCodeResponse])
def list_promo_codes(
    current_user: User = Depends(admin_only),
    service: PromoService = Depends(get_promo_service),
):
    return service.list_codes()
