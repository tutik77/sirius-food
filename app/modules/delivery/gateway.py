from abc import ABC, abstractmethod

from app.domain.entities import Delivery, User


class DeliveryGateway(ABC):
    @abstractmethod
    def assign_courier(self, order_id: int, courier_id: int) -> Delivery: ...

    @abstractmethod
    def get_delivery(self, delivery_id: int, current_user: User) -> Delivery: ...

    @abstractmethod
    def list_courier_deliveries(self, courier: User) -> list[Delivery]: ...

    @abstractmethod
    def complete_delivery(self, delivery_id: int, current_user: User) -> Delivery: ...
