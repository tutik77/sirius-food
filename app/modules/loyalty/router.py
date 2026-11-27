from fastapi import APIRouter, Depends

from app.container import get_loyalty_service
from app.core.dependencies import get_current_user
from app.domain.entities import TIER_RATES, LoyaltyTier, User
from app.modules.loyalty.service import LoyaltyService
from app.schemas import LoyaltySummary

router = APIRouter()


@router.get("/me", response_model=LoyaltySummary)
def my_loyalty(
    current_user: User = Depends(get_current_user),
    service: LoyaltyService = Depends(get_loyalty_service),
):
    account = service.account_for(current_user.id)
    return LoyaltySummary(
        balance=account.balance,
        total_earned=account.total_earned,
        tier=account.tier,
        earn_rate=TIER_RATES[LoyaltyTier(account.tier)],
        transactions=service.history(account),
    )
