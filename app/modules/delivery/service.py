"""
Слой бизнес-логики модуля доставки (круги Entities и Use Cases).
"""
from app.domain.entities import Delivery, DeliveryStatus, OrderStatus
from app.modules.delivery.exceptions import (
    CourierBlockedError,
    CourierBusyError,
    CourierNotFoundError,
    DeliveryAlreadyCompletedError,
    DeliveryCancelledError,
    DeliveryNotFoundError,
    OrderNotFoundError,
    OrderNotPaidError,
)
from app.modules.delivery.repository import DeliveryRepository


class DeliveryService:
    """Бизнес-правила назначения курьеров и завершения доставок."""

    def __init__(self, repository: DeliveryRepository):
        self.repository = repository

    def assign_courier(self, order_id: int, courier_id: int) -> Delivery:
        """
        Назначает курьера на заказ. Заказ должен быть оплачен,
        курьер — существовать, не быть заблокированным и не иметь активной доставки.
        """
        order = self.repository.get_order(order_id)
        if order is None:
            raise OrderNotFoundError()
        if order.status != OrderStatus.PAID:
            raise OrderNotPaidError()

        courier = self.repository.get_user(courier_id)
        if courier is None:
            raise CourierNotFoundError()
        if courier.is_blocked:
            raise CourierBlockedError()

        if self.repository.find_active_by_courier(courier_id) is not None:
            raise CourierBusyError()

        delivery = Delivery(
            id=None,
            order_id=order_id,
            courier_id=courier_id,
            status=DeliveryStatus.IN_PROGRESS,
        )
        return self.repository.add(delivery)

    def complete_delivery(self, delivery_id: int) -> Delivery:
        """Завершает доставку и переводит заказ в статус delivered."""
        delivery = self.repository.get_delivery(delivery_id)
        if delivery is None:
            raise DeliveryNotFoundError()
        if delivery.status == DeliveryStatus.COMPLETED:
            raise DeliveryAlreadyCompletedError()
        if delivery.status == DeliveryStatus.CANCELLED:
            raise DeliveryCancelledError()

        delivery.status = DeliveryStatus.COMPLETED
        order = self.repository.get_order(delivery.order_id)
        if order is not None:
            order.status = OrderStatus.DELIVERED

        self.repository.save_completion(delivery, order)
        return delivery
