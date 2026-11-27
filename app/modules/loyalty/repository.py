from abc import ABC, abstractmethod
from dataclasses import replace

from sqlalchemy.orm import Session

from app import models
from app.domain.entities import LoyaltyAccount, LoyaltyTransaction
from app.mappers import to_loyalty_account, to_loyalty_transaction
from app.memory_storage import InMemoryStorage, copy


class LoyaltyRepository(ABC):
    @abstractmethod
    def get_account(self, user_id: int) -> LoyaltyAccount | None: ...

    @abstractmethod
    def get_account_by_id(self, account_id: int) -> LoyaltyAccount: ...

    @abstractmethod
    def create_account(self, user_id: int) -> LoyaltyAccount: ...

    @abstractmethod
    def save_account(self, account: LoyaltyAccount) -> None: ...

    @abstractmethod
    def find_transaction(self, idempotency_key: str) -> LoyaltyTransaction | None: ...

    @abstractmethod
    def add_transaction(self, transaction: LoyaltyTransaction) -> LoyaltyTransaction: ...

    @abstractmethod
    def list_transactions(self, account_id: int) -> list[LoyaltyTransaction]: ...


class SqlAlchemyLoyaltyRepository(LoyaltyRepository):
    def __init__(self, db: Session):
        self.db = db

    def get_account(self, user_id: int) -> LoyaltyAccount | None:
        row = self.db.query(models.LoyaltyAccount).filter_by(user_id=user_id).with_for_update().first()
        return to_loyalty_account(row) if row else None

    def get_account_by_id(self, account_id: int) -> LoyaltyAccount:
        return to_loyalty_account(self.db.get(models.LoyaltyAccount, account_id, with_for_update=True))

    def create_account(self, user_id: int) -> LoyaltyAccount:
        row = models.LoyaltyAccount(user_id=user_id, balance=0, total_earned=0, tier="bronze")
        self.db.add(row)
        self.db.flush()
        return to_loyalty_account(row)

    def save_account(self, account: LoyaltyAccount) -> None:
        row = self.db.get(models.LoyaltyAccount, account.id)
        row.balance = account.balance
        row.total_earned = account.total_earned
        row.tier = account.tier

    def find_transaction(self, idempotency_key: str) -> LoyaltyTransaction | None:
        row = self.db.query(models.LoyaltyTransaction).filter_by(idempotency_key=idempotency_key).first()
        return to_loyalty_transaction(row) if row else None

    def add_transaction(self, transaction: LoyaltyTransaction) -> LoyaltyTransaction:
        row = models.LoyaltyTransaction(
            account_id=transaction.account_id,
            amount=transaction.amount,
            type=transaction.type,
            order_id=transaction.order_id,
            idempotency_key=transaction.idempotency_key,
        )
        self.db.add(row)
        self.db.flush()
        return to_loyalty_transaction(row)

    def list_transactions(self, account_id: int) -> list[LoyaltyTransaction]:
        rows = (
            self.db.query(models.LoyaltyTransaction)
            .filter_by(account_id=account_id)
            .order_by(models.LoyaltyTransaction.id)
        )
        return [to_loyalty_transaction(row) for row in rows]


class InMemoryLoyaltyRepository(LoyaltyRepository):
    def __init__(self, storage: InMemoryStorage):
        self.storage = storage

    def get_account(self, user_id: int) -> LoyaltyAccount | None:
        return copy(next((a for a in self.storage.loyalty_accounts.values() if a.user_id == user_id), None))

    def get_account_by_id(self, account_id: int) -> LoyaltyAccount:
        return copy(self.storage.loyalty_accounts[account_id])

    def create_account(self, user_id: int) -> LoyaltyAccount:
        account = LoyaltyAccount(id=self.storage.next_id("loyalty_accounts"), user_id=user_id)
        self.storage.loyalty_accounts[account.id] = account
        return copy(account)

    def save_account(self, account: LoyaltyAccount) -> None:
        self.storage.loyalty_accounts[account.id] = copy(account)

    def find_transaction(self, idempotency_key: str) -> LoyaltyTransaction | None:
        return copy(self.storage.loyalty_transactions.get(idempotency_key))

    def add_transaction(self, transaction: LoyaltyTransaction) -> LoyaltyTransaction:
        saved = replace(transaction, id=self.storage.next_id("loyalty_transactions"))
        self.storage.loyalty_transactions[saved.idempotency_key] = saved
        return copy(saved)

    def list_transactions(self, account_id: int) -> list[LoyaltyTransaction]:
        return [copy(t) for t in self.storage.loyalty_transactions.values() if t.account_id == account_id]
