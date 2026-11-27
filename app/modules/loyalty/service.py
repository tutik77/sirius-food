from decimal import Decimal

from app.domain.entities import LoyaltyAccount, LoyaltyTransaction, LoyaltyTransactionType, money
from app.modules.loyalty.exceptions import NotEnoughPointsError, PointsLimitExceededError
from app.modules.loyalty.repository import LoyaltyRepository

MAX_POINTS_SHARE = Decimal("0.5")


def earn_key(order_id: int) -> str:
    return f"earn_order_{order_id}"


def spend_key(order_id: int) -> str:
    return f"spend_order_{order_id}"


def refund_key(order_id: int) -> str:
    return f"refund_order_{order_id}"


def revoke_key(order_id: int) -> str:
    return f"revoke_earn_order_{order_id}"


class LoyaltyService:
    def __init__(self, repository: LoyaltyRepository):
        self.repository = repository

    def account_for(self, user_id: int) -> LoyaltyAccount:
        return self.repository.get_account(user_id) or self.repository.create_account(user_id)

    def history(self, account: LoyaltyAccount) -> list[LoyaltyTransaction]:
        return self.repository.list_transactions(account.id)

    def earn(self, user_id: int, order_id: int, paid_amount: Decimal) -> LoyaltyTransaction | None:
        if self.repository.find_transaction(earn_key(order_id)) is not None:
            return None
        account = self.account_for(user_id)
        points = account.points_for(paid_amount)
        account.balance += points
        account.total_earned += points
        account.update_tier()
        return self._record(account, points, LoyaltyTransactionType.EARN, order_id, earn_key(order_id))

    def spend(self, user_id: int, order_id: int, points: Decimal, order_amount: Decimal) -> LoyaltyTransaction | None:
        points = money(points)
        if points <= 0 or self.repository.find_transaction(spend_key(order_id)) is not None:
            return None
        if points > money(order_amount * MAX_POINTS_SHARE):
            raise PointsLimitExceededError()
        account = self.account_for(user_id)
        if account.balance < points:
            raise NotEnoughPointsError()
        account.balance -= points
        return self._record(account, -points, LoyaltyTransactionType.SPEND, order_id, spend_key(order_id))

    def compensate_order(self, order_id: int) -> list[LoyaltyTransaction]:
        compensations = []
        spent = self.repository.find_transaction(spend_key(order_id))
        if spent is not None and self.repository.find_transaction(refund_key(order_id)) is None:
            account = self.repository.get_account_by_id(spent.account_id)
            account.balance += -spent.amount
            compensations.append(
                self._record(account, -spent.amount, LoyaltyTransactionType.REFUND, order_id, refund_key(order_id))
            )

        earned = self.repository.find_transaction(earn_key(order_id))
        if earned is not None and self.repository.find_transaction(revoke_key(order_id)) is None:
            account = self.repository.get_account_by_id(earned.account_id)
            revoked = min(earned.amount, account.balance)
            account.balance -= revoked
            account.total_earned -= earned.amount
            account.update_tier()
            compensations.append(
                self._record(account, -revoked, LoyaltyTransactionType.REVOKE, order_id, revoke_key(order_id))
            )
        return compensations

    def _record(self, account: LoyaltyAccount, amount: Decimal, kind: str, order_id: int, key: str) -> LoyaltyTransaction:
        self.repository.save_account(account)
        return self.repository.add_transaction(
            LoyaltyTransaction(id=None, account_id=account.id, amount=amount, type=kind, order_id=order_id, idempotency_key=key)
        )
