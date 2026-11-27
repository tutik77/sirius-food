from app.domain.entities import Delivery, DeliveryStatus, OrderStatus, Role, User
from delivery_service.exceptions import (
    CourierBlockedError,
    CourierBusyError,
    CourierNotFoundError,
    DeliveryAccessDeniedError,
    DeliveryAlreadyCompletedError,
    DeliveryCancelledError,
    DeliveryNotFoundError,
    NoFreeCourierError,
    NotACourierError,
    OrderNotFoundError,
    OrderNotPaidError,
)
from delivery_service.repository import DeliveryRepository


class DeliveryService:
    def __init__(self, repository: DeliveryRepository):
        self.repository = repository

    def assign_courier(self, order_id: int, courier_id: int) -> Delivery:
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
        if courier.role != Role.COURIER:
            raise NotACourierError()

        if self.repository.find_active_by_courier(courier_id) is not None:
            raise CourierBusyError()

        delivery = Delivery(
            id=None,
            order_id=order_id,
            courier_id=courier_id,
            status=DeliveryStatus.IN_PROGRESS,
        )
        return self.repository.add(delivery)

    def assign_free_courier(self, order_id: int) -> Delivery:
        courier = self.repository.find_free_courier()
        if courier is None:
            raise NoFreeCourierError()
        return self.assign_courier(order_id, courier.id)

    def get_delivery(self, delivery_id: int, current_user: User) -> Delivery:
        delivery = self.repository.get_delivery(delivery_id)
        if delivery is None:
            raise DeliveryNotFoundError()
        if current_user.is_admin or delivery.courier_id == current_user.id:
            return delivery

        order = self.repository.get_order(delivery.order_id)
        if order is None or not order.belongs_to(current_user):
            raise DeliveryAccessDeniedError()
        return delivery

    def list_courier_deliveries(self, courier: User) -> list[Delivery]:
        return self.repository.list_by_courier(courier.id)

    def complete_delivery(self, delivery_id: int, current_user: User) -> Delivery:
        delivery = self.repository.get_delivery(delivery_id)
        if delivery is None:
            raise DeliveryNotFoundError()
        if delivery.courier_id != current_user.id and not current_user.is_admin:
            raise DeliveryAccessDeniedError()
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
