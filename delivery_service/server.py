import logging
import time
from collections.abc import Callable
from concurrent import futures
from contextlib import AbstractContextManager, contextmanager

import grpc

from app.core.logging import setup_logging
from app.core.sentry import setup_sentry
from app.database import SessionLocal
from app.domain.entities import Delivery, User
from app.domain.errors import BusinessRuleError, DomainError, ForbiddenError, NotFoundError
from delivery_service.repository import SqlAlchemyDeliveryRepository
from delivery_service.service import DeliveryService
from proto import delivery_pb2, delivery_pb2_grpc

logger = logging.getLogger("delivery_service")

PORT = 50051
TRACK_STATUSES = ("in_progress", "on_the_way", "delivered")
TRACK_STEP_SECONDS = 2

GRPC_CODES = {
    NotFoundError: grpc.StatusCode.NOT_FOUND,
    ForbiddenError: grpc.StatusCode.PERMISSION_DENIED,
    BusinessRuleError: grpc.StatusCode.FAILED_PRECONDITION,
}

ServiceScope = Callable[[], AbstractContextManager[DeliveryService]]


@contextmanager
def postgres_scope():
    with SessionLocal() as db:
        yield DeliveryService(SqlAlchemyDeliveryRepository(db))


def to_reply(delivery: Delivery) -> delivery_pb2.DeliveryReply:
    return delivery_pb2.DeliveryReply(
        id=delivery.id,
        order_id=delivery.order_id,
        courier_id=delivery.courier_id,
        status=delivery.status,
    )


def to_user(actor: delivery_pb2.Actor) -> User:
    return User(id=actor.user_id, email="", role=actor.role)


def abort_on_domain_error(context: grpc.ServicerContext, error: DomainError) -> None:
    code = next((c for t, c in GRPC_CODES.items() if isinstance(error, t)), grpc.StatusCode.INVALID_ARGUMENT)
    context.abort(code, error.message)


class DeliveryServicer(delivery_pb2_grpc.DeliveryServiceServicer):
    def __init__(self, scope: ServiceScope = postgres_scope):
        self.scope = scope

    def AssignCourier(self, request, context):
        logger.info("AssignCourier order=%s courier=%s", request.order_id, request.courier_id)
        with self.scope() as service:
            try:
                return to_reply(service.assign_courier(request.order_id, request.courier_id))
            except DomainError as e:
                abort_on_domain_error(context, e)

    def GetDelivery(self, request, context):
        logger.info("GetDelivery delivery=%s actor=%s", request.delivery_id, request.actor.user_id)
        with self.scope() as service:
            try:
                return to_reply(service.get_delivery(request.delivery_id, to_user(request.actor)))
            except DomainError as e:
                abort_on_domain_error(context, e)

    def ListCourierDeliveries(self, request, context):
        logger.info("ListCourierDeliveries courier=%s", request.courier_id)
        with self.scope() as service:
            courier = User(id=request.courier_id, email="")
            deliveries = service.list_courier_deliveries(courier)
            return delivery_pb2.DeliveryList(deliveries=[to_reply(d) for d in deliveries])

    def CompleteDelivery(self, request, context):
        logger.info("CompleteDelivery delivery=%s actor=%s", request.delivery_id, request.actor.user_id)
        with self.scope() as service:
            try:
                return to_reply(service.complete_delivery(request.delivery_id, to_user(request.actor)))
            except DomainError as e:
                abort_on_domain_error(context, e)

    def TrackDelivery(self, request, context):
        logger.info("TrackDelivery delivery=%s", request.delivery_id)
        with self.scope() as service:
            try:
                service.get_delivery(request.delivery_id, to_user(request.actor))
            except DomainError as e:
                abort_on_domain_error(context, e)
        for index, status in enumerate(TRACK_STATUSES):
            if index:
                time.sleep(TRACK_STEP_SECONDS)
            yield delivery_pb2.DeliveryStatusUpdate(delivery_id=request.delivery_id, status=status)

    def ChatWithCourier(self, request_iterator, context):
        for message in request_iterator:
            logger.info("Chat delivery=%s %s: %s", message.delivery_id, message.sender, message.text)
            yield delivery_pb2.ChatMessage(
                delivery_id=message.delivery_id,
                sender="courier",
                text=f"Принял: «{message.text}». Буду через 10 минут",
            )


def create_server(address: str, scope: ServiceScope = postgres_scope) -> tuple[grpc.Server, int]:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    delivery_pb2_grpc.add_DeliveryServiceServicer_to_server(DeliveryServicer(scope), server)
    port = server.add_insecure_port(address)
    return server, port


def serve() -> None:
    setup_logging("delivery_service")
    setup_sentry("delivery_service")
    server, _ = create_server(f"[::]:{PORT}")
    server.start()
    logger.info("Delivery gRPC server running on port %s", PORT)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
