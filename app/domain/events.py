import uuid
from dataclasses import asdict, dataclass, field
from typing import ClassVar

ORDER_PAID = "order.paid"
ORDER_CANCELLED = "order.cancelled"
DELIVERY_FAILED = "delivery.failed"


@dataclass(frozen=True)
class Event:
    routing_key: ClassVar[str]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()), kw_only=True)

    def payload(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class OrderPaid(Event):
    routing_key: ClassVar[str] = ORDER_PAID
    order_id: int
    user_id: int
    amount: float


@dataclass(frozen=True)
class OrderCancelled(Event):
    routing_key: ClassVar[str] = ORDER_CANCELLED
    order_id: int
    refund: float
    reason: str


@dataclass(frozen=True)
class DeliveryFailed(Event):
    routing_key: ClassVar[str] = DELIVERY_FAILED
    order_id: int
    reason: str
