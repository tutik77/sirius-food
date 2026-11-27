from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.entities import DiscountType, PromoCode
from app.modules.promo.exceptions import (
    InvalidPromoCodeError,
    PromoCodeAlreadyUsedError,
    PromoCodeDuplicateError,
    PromoCodeExhaustedError,
    PromoCodeInactiveError,
    PromoCodeMinAmountError,
    PromoCodeNotFoundError,
)
from app.modules.promo.repository import PromoRepository


@dataclass(frozen=True)
class PromoQuote:
    promo: PromoCode
    discount: Decimal


class PromoService:
    def __init__(self, repository: PromoRepository, clock: Callable[[], datetime] = datetime.utcnow):
        self.repository = repository
        self.clock = clock

    def create(self, promo: PromoCode) -> PromoCode:
        if promo.discount_value <= 0 or promo.max_uses < 1 or promo.valid_until <= promo.valid_from:
            raise InvalidPromoCodeError()
        if promo.discount_type == DiscountType.PERCENT and promo.discount_value > 100:
            raise InvalidPromoCodeError()
        if self.repository.get_by_code(promo.code) is not None:
            raise PromoCodeDuplicateError()
        return self.repository.add(promo)

    def list_codes(self) -> list[PromoCode]:
        return self.repository.list_all()

    def quote(self, code: str, user_id: int, amount: Decimal) -> PromoQuote:
        promo = self.repository.get_by_code(code)
        if promo is None:
            raise PromoCodeNotFoundError()
        if not promo.is_valid_at(self.clock()):
            raise PromoCodeInactiveError()
        if not promo.has_uses_left():
            raise PromoCodeExhaustedError()
        if amount < promo.min_order_amount:
            raise PromoCodeMinAmountError()
        if self.repository.was_used_by(promo.id, user_id):
            raise PromoCodeAlreadyUsedError()
        return PromoQuote(promo=promo, discount=promo.discount_for(amount))

    def reserve(self, quote: PromoQuote) -> None:
        if not self.repository.reserve_use(quote.promo.id):
            raise PromoCodeExhaustedError()

    def restore_for_order(self, order_id: int) -> bool:
        usage = self.repository.get_usage_by_order(order_id)
        if usage is None:
            return False
        self.repository.release_usage(usage)
        return True

    def deactivate_expired(self) -> int:
        return self.repository.deactivate_expired(self.clock())
