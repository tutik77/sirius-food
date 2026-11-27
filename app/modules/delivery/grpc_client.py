from collections.abc import Iterator

import grpc

from app.domain.entities import Delivery, User
from app.domain.errors import (
    BusinessRuleError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
)
from app.modules.delivery.gateway import DeliveryGateway
from proto import delivery_pb2, delivery_pb2_grpc

TIMEOUT_SECONDS = 5

DOMAIN_ERRORS = {
    grpc.StatusCode.NOT_FOUND: NotFoundError,
    grpc.StatusCode.PERMISSION_DENIED: ForbiddenError,
    grpc.StatusCode.FAILED_PRECONDITION: BusinessRuleError,
}


def to_delivery(reply: delivery_pb2.DeliveryReply) -> Delivery:
    return Delivery(
        id=reply.id,
        order_id=reply.order_id,
        courier_id=reply.courier_id if reply.HasField("courier_id") else None,
        status=reply.status,
    )


def to_actor(user: User) -> delivery_pb2.Actor:
    return delivery_pb2.Actor(user_id=user.id, role=user.role)


def to_domain_error(error: grpc.RpcError) -> DomainError:
    if error.code() == grpc.StatusCode.UNAVAILABLE:
        return ServiceUnavailableError("Сервис доставки недоступен")
    if error.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
        return ServiceUnavailableError("Сервис доставки не ответил вовремя")
    return DOMAIN_ERRORS.get(error.code(), DomainError)(error.details())


class DeliveryGrpcClient(DeliveryGateway):
    def __init__(self, address: str):
        self.channel = grpc.insecure_channel(address)
        self.stub = delivery_pb2_grpc.DeliveryServiceStub(self.channel)

    def assign_courier(self, order_id: int, courier_id: int) -> Delivery:
        request = delivery_pb2.AssignCourierRequest(order_id=order_id, courier_id=courier_id)
        return to_delivery(self._call(self.stub.AssignCourier, request))

    def get_delivery(self, delivery_id: int, current_user: User) -> Delivery:
        request = delivery_pb2.GetDeliveryRequest(delivery_id=delivery_id, actor=to_actor(current_user))
        return to_delivery(self._call(self.stub.GetDelivery, request))

    def list_courier_deliveries(self, courier: User) -> list[Delivery]:
        request = delivery_pb2.ListCourierDeliveriesRequest(courier_id=courier.id)
        return [to_delivery(d) for d in self._call(self.stub.ListCourierDeliveries, request).deliveries]

    def complete_delivery(self, delivery_id: int, current_user: User) -> Delivery:
        request = delivery_pb2.CompleteDeliveryRequest(delivery_id=delivery_id, actor=to_actor(current_user))
        return to_delivery(self._call(self.stub.CompleteDelivery, request))

    def track_delivery(self, delivery_id: int, current_user: User) -> Iterator[str]:
        request = delivery_pb2.TrackDeliveryRequest(delivery_id=delivery_id, actor=to_actor(current_user))
        try:
            for update in self.stub.TrackDelivery(request, timeout=30):
                yield update.status
        except grpc.RpcError as e:
            raise to_domain_error(e) from e

    def chat_with_courier(self, delivery_id: int, texts: Iterator[str]) -> Iterator[str]:
        messages = (delivery_pb2.ChatMessage(delivery_id=delivery_id, sender="client", text=t) for t in texts)
        try:
            for reply in self.stub.ChatWithCourier(messages, timeout=60):
                yield reply.text
        except grpc.RpcError as e:
            raise to_domain_error(e) from e

    @staticmethod
    def _call(method, request):
        try:
            return method(request, timeout=TIMEOUT_SECONDS)
        except grpc.RpcError as e:
            raise to_domain_error(e) from e
