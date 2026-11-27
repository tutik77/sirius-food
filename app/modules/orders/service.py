"""
Слой бизнес-логики модуля заказов (круги Entities и Use Cases).

Импорты fastapi и sqlalchemy здесь запрещены: сервис зависит только
от доменных сущностей и абстрактного OrderRepository.
"""
from datetime import date, datetime, time, timedelta

import structlog

from app.domain.entities import Order, OrderStatus, User
from app.domain.events import OrderCancelled, OrderPaid
from app.modules.orders.exceptions import (
    AccessDeniedError,
    InsufficientFundsError,
    MenuItemNotFoundError,
    MenuItemUnavailableError,
    OrderCannotBeCancelledError,
    OrderCannotBePaidError,
    OrderNotFoundError,
    UserNotFoundError,
)
from app.modules.orders.repository import OrderRepository
from app.tasks.orders import generate_order_pdf, send_order_email, send_order_sms

logger = structlog.get_logger(__name__)


class OrderService:
    """Бизнес-правила оформления и отмены заказов."""

    def __init__(self, repository: OrderRepository):
        # Зависимость приходит снаружи через конструктор (инверсия зависимостей).
        self.repository = repository

    def create_order(self, user_id: int, item_id: int, quantity: int) -> Order:
        """
        Сценарий оформления заказа: проверяет пользователя, блюдо и баланс,
        списывает стоимость и сохраняет заказ.
        user_id приходит из JWT, а не из тела запроса.
        """
        user = self.repository.get_user_by_id(user_id)
        if user is None:
            raise UserNotFoundError()

        item = self.repository.get_menu_item_by_id(item_id)
        if item is None:
            raise MenuItemNotFoundError()
        if not item.is_available:
            raise MenuItemUnavailableError()

        total_cost = item.price * quantity
        if user.balance < total_cost:
            raise InsufficientFundsError()

        user.balance -= total_cost
        order = Order(
            id=None,
            user_id=user.id,
            item_id=item.id,
            quantity=quantity,
            status=OrderStatus.PROCESSING,
            total_cost=total_cost,
        )
        saved = self.repository.save_order(order, payer=user)
        logger.info("order_created", order_id=saved.id, user_id=user.id, total_cost=total_cost)
        self._schedule_order_notifications(saved, user)
        return saved

    @staticmethod
    def _schedule_order_notifications(order: Order, user: User) -> None:
        generate_order_pdf.delay(order.id)
        send_order_email.delay(order.id, user.email)
        if user.phone:
            send_order_sms.delay(order.id, user.phone)

    def cancel_order(self, order_id: int, current_user: User) -> Order:
        """
        Отменяет заказ и возвращает деньги. Защита от IDOR: отменить можно
        только свой заказ (администратор — любой), и только пока он готовится.
        """
        order = self.repository.get_order(order_id)
        if order is None:
            raise OrderNotFoundError()
        if not order.belongs_to(current_user) and not current_user.is_admin:
            raise AccessDeniedError()
        if order.status != OrderStatus.PROCESSING:
            raise OrderCannotBeCancelledError()

        payer = self.repository.get_user_by_id(order.user_id)
        payer.balance += order.total_cost or 0.0
        order.status = OrderStatus.CANCELLED
        self.repository.save_cancellation(order, payer)
        return order

    def pay_order(self, order_id: int, current_user: User) -> Order:
        order = self.repository.get_order(order_id)
        if order is None:
            raise OrderNotFoundError()
        if not order.belongs_to(current_user):
            raise AccessDeniedError()
        if order.status != OrderStatus.PROCESSING:
            raise OrderCannotBePaidError()

        order.status = OrderStatus.PAID
        event = OrderPaid(order_id=order.id, user_id=order.user_id, amount=order.total_cost or 0.0)
        self.repository.save_payment(order, event)
        logger.info("order_paid", order_id=order.id, user_id=order.user_id, event_id=event.event_id)
        return order

    def compensate_failed_delivery(self, order_id: int, reason: str) -> Order | None:
        order = self.repository.get_order(order_id)
        if order is None or order.status != OrderStatus.PAID:
            return None

        refund = order.total_cost or 0.0
        payer = self.repository.get_user_by_id(order.user_id)
        payer.balance += refund
        order.status = OrderStatus.CANCELLED
        event = OrderCancelled(order_id=order.id, refund=refund, reason=reason)
        self.repository.save_compensation(order, payer, event)
        return order

    def list_user_orders(self, current_user: User) -> list[Order]:
        """Заказы текущего пользователя — только его собственные."""
        return self.repository.list_by_user(current_user.id)

    def count_orders_for_day(self, day: date) -> int:
        start = datetime.combine(day, time.min)
        return self.repository.count_created_between(start, start + timedelta(days=1))

    def get_kitchen_orders(self) -> list[Order]:
        """Очередь кухни: заказы, которые нужно приготовить."""
        return self.repository.list_by_status(OrderStatus.PROCESSING)
