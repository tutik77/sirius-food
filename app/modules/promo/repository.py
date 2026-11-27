from abc import ABC, abstractmethod
from dataclasses import replace
from datetime import datetime

from sqlalchemy import update
from sqlalchemy.orm import Session

from app import models
from app.domain.entities import PromoCode, PromoUsage
from app.mappers import to_promo_code, to_promo_usage
from app.memory_storage import InMemoryStorage, copy


class PromoRepository(ABC):
    @abstractmethod
    def get_by_code(self, code: str) -> PromoCode | None: ...

    @abstractmethod
    def add(self, promo: PromoCode) -> PromoCode: ...

    @abstractmethod
    def list_all(self) -> list[PromoCode]: ...

    @abstractmethod
    def was_used_by(self, promo_id: int, user_id: int) -> bool: ...

    @abstractmethod
    def reserve_use(self, promo_id: int) -> bool: ...

    @abstractmethod
    def get_usage_by_order(self, order_id: int) -> PromoUsage | None: ...

    @abstractmethod
    def release_usage(self, usage: PromoUsage) -> None: ...

    @abstractmethod
    def deactivate_expired(self, moment: datetime) -> int: ...


class SqlAlchemyPromoRepository(PromoRepository):
    def __init__(self, db: Session):
        self.db = db

    def get_by_code(self, code: str) -> PromoCode | None:
        row = self.db.query(models.PromoCode).filter(models.PromoCode.code == code).first()
        return to_promo_code(row) if row else None

    def add(self, promo: PromoCode) -> PromoCode:
        row = models.PromoCode(
            code=promo.code,
            discount_type=promo.discount_type,
            discount_value=promo.discount_value,
            valid_from=promo.valid_from,
            valid_until=promo.valid_until,
            max_uses=promo.max_uses,
            current_uses=0,
            min_order_amount=promo.min_order_amount,
            is_active=promo.is_active,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return to_promo_code(row)

    def list_all(self) -> list[PromoCode]:
        return [to_promo_code(row) for row in self.db.query(models.PromoCode).order_by(models.PromoCode.id)]

    def was_used_by(self, promo_id: int, user_id: int) -> bool:
        return (
            self.db.query(models.PromoCodeUsage)
            .filter_by(promo_code_id=promo_id, user_id=user_id)
            .first()
            is not None
        )

    def reserve_use(self, promo_id: int) -> bool:
        result = self.db.execute(
            update(models.PromoCode)
            .where(models.PromoCode.id == promo_id, models.PromoCode.current_uses < models.PromoCode.max_uses)
            .values(current_uses=models.PromoCode.current_uses + 1)
        )
        return result.rowcount == 1

    def get_usage_by_order(self, order_id: int) -> PromoUsage | None:
        row = self.db.query(models.PromoCodeUsage).filter_by(order_id=order_id).first()
        return to_promo_usage(row) if row else None

    def release_usage(self, usage: PromoUsage) -> None:
        self.db.query(models.PromoCodeUsage).filter_by(id=usage.id).delete()
        self.db.execute(
            update(models.PromoCode)
            .where(models.PromoCode.id == usage.promo_code_id, models.PromoCode.current_uses > 0)
            .values(current_uses=models.PromoCode.current_uses - 1)
        )

    def deactivate_expired(self, moment: datetime) -> int:
        result = self.db.execute(
            update(models.PromoCode)
            .where(models.PromoCode.is_active.is_(True), models.PromoCode.valid_until < moment)
            .values(is_active=False)
        )
        self.db.commit()
        return result.rowcount


class InMemoryPromoRepository(PromoRepository):
    def __init__(self, storage: InMemoryStorage):
        self.storage = storage

    def get_by_code(self, code: str) -> PromoCode | None:
        return copy(next((p for p in self.storage.promo_codes.values() if p.code == code), None))

    def add(self, promo: PromoCode) -> PromoCode:
        saved = replace(promo, id=self.storage.next_id("promo_codes"), current_uses=0)
        self.storage.promo_codes[saved.id] = saved
        return copy(saved)

    def list_all(self) -> list[PromoCode]:
        return [copy(p) for p in self.storage.promo_codes.values()]

    def was_used_by(self, promo_id: int, user_id: int) -> bool:
        return any(u.promo_code_id == promo_id and u.user_id == user_id for u in self.storage.promo_usages.values())

    def reserve_use(self, promo_id: int) -> bool:
        promo = self.storage.promo_codes[promo_id]
        if not promo.has_uses_left():
            return False
        promo.current_uses += 1
        return True

    def get_usage_by_order(self, order_id: int) -> PromoUsage | None:
        return copy(next((u for u in self.storage.promo_usages.values() if u.order_id == order_id), None))

    def release_usage(self, usage: PromoUsage) -> None:
        del self.storage.promo_usages[usage.id]
        promo = self.storage.promo_codes[usage.promo_code_id]
        promo.current_uses = max(promo.current_uses - 1, 0)

    def deactivate_expired(self, moment: datetime) -> int:
        expired = [p for p in self.storage.promo_codes.values() if p.is_active and p.valid_until < moment]
        for promo in expired:
            promo.is_active = False
        return len(expired)
