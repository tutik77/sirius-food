from collections import defaultdict
from dataclasses import replace
from typing import TypeVar

from app.domain.entities import (
    AssistantMessage,
    Delivery,
    LoyaltyAccount,
    LoyaltyTransaction,
    MenuItem,
    Order,
    PromoCode,
    PromoUsage,
    RefreshToken,
    User,
)
from app.domain.events import Event

T = TypeVar("T")


class InMemoryStorage:
    def __init__(self):
        self.users: dict[int, User] = {}
        self.menu_items: dict[int, MenuItem] = {}
        self.orders: dict[int, Order] = {}
        self.deliveries: dict[int, Delivery] = {}
        self.refresh_tokens: dict[str, RefreshToken] = {}
        self.outbox: list[Event] = []
        self.promo_codes: dict[int, PromoCode] = {}
        self.promo_usages: dict[int, PromoUsage] = {}
        self.loyalty_accounts: dict[int, LoyaltyAccount] = {}
        self.loyalty_transactions: dict[str, LoyaltyTransaction] = {}
        self.assistant_messages: dict[int, AssistantMessage] = {}
        self._sequences: dict[str, int] = defaultdict(int)

    def next_id(self, table: str) -> int:
        self._sequences[table] += 1
        return self._sequences[table]


def copy(entity: T | None) -> T | None:
    return replace(entity) if entity is not None else None
