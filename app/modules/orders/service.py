from datetime import date, datetime, time, timedelta
from decimal import Decimal

import structlog

from app.domain.entities import Order, OrderStatus, PromoUsage, User, money
from app.domain.events import OrderCancelled, OrderPaid
from app.modules.loyalty.service import LoyaltyService
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
from app.modules.promo.service import PromoQuote, PromoService
from app.tasks.orders import generate_order_pdf, send_order_email, send_order_sms

logger = structlog.get_logger(__name__)


class OrderService:
    def __init__(
        self,
        repository: OrderRepository,
        promo: PromoService | None = None,
        loyalty: LoyaltyService | None = None,
    ):
        self.repository = repository
        self.promo = promo
        self.loyalty = loyalty

    def create_order(self, user_id: int, item_id: int, quantity: int, promo_code: str | None = None) -> Order:
        user = self.repository.get_user_by_id(user_id)
        if user is None:
            raise UserNotFoundError()

        item = self.repository.get_menu_item_by_id(item_id)
        if item is None:
            raise MenuItemNotFoundError()
        if not item.is_available:
            raise MenuItemUnavailableError()

        full_price = item.price * quantity
        quote = self.promo.quote(promo_code, user.id, money(full_price)) if promo_code else None
        discount = float(quote.discount) if quote else 0.0
        total_cost = full_price - discount
        if user.balance < total_cost:
            raise InsufficientFundsError()
        if quote:
            self.promo.reserve(quote)

        user.balance -= total_cost
        order = Order(
            id=None,
            user_id=user.id,
            item_id=item.id,
            quantity=quantity,
            status=OrderStatus.PROCESSING,
            total_cost=total_cost,
            promo_code_id=quote.promo.id if quote else None,
            discount=discount,
        )
        saved = self.repository.save_order(order, payer=user, promo_usage=self._promo_usage(quote, user))
        logger.info("order_created", order_id=saved.id, user_id=user.id, total_cost=total_cost)
        self._schedule_order_notifications(saved, user)
        return saved

    @staticmethod
    def _promo_usage(quote: PromoQuote | None, user: User) -> PromoUsage | None:
        if quote is None:
            return None
        return PromoUsage(id=None, promo_code_id=quote.promo.id, user_id=user.id, order_id=None, discount=quote.discount)

    @staticmethod
    def _schedule_order_notifications(order: Order, user: User) -> None:
        generate_order_pdf.delay(order.id)
        send_order_email.delay(order.id, user.email)
        if user.phone:
            send_order_sms.delay(order.id, user.phone)

    def cancel_order(self, order_id: int, current_user: User) -> Order:
        order = self.repository.get_order(order_id)
        if order is None:
            raise OrderNotFoundError()
        if not order.belongs_to(current_user) and not current_user.is_admin:
            raise AccessDeniedError()
        if order.status != OrderStatus.PROCESSING:
            raise OrderCannotBeCancelledError()

        payer = self.repository.get_user_by_id(order.user_id)
        refund = order.paid_with_money
        payer.balance += refund
        order.status = OrderStatus.CANCELLED
        event = OrderCancelled(order_id=order.id, refund=refund, reason="Отменён клиентом")
        self.repository.save_cancellation(order, payer, event)
        return order

    def pay_order(self, order_id: int, current_user: User, points: Decimal = Decimal("0")) -> Order:
        order = self.repository.get_order(order_id)
        if order is None:
            raise OrderNotFoundError()
        if not order.belongs_to(current_user):
            raise AccessDeniedError()
        if order.status != OrderStatus.PROCESSING:
            raise OrderCannotBePaidError()

        payer = self.repository.get_user_by_id(order.user_id)
        spent = self.loyalty.spend(payer.id, order.id, points, money(order.total_cost or 0)) if points else None
        if spent:
            order.points_spent = float(-spent.amount)
            payer.balance += order.points_spent

        order.status = OrderStatus.PAID
        event = OrderPaid(order_id=order.id, user_id=order.user_id, amount=order.paid_with_money)
        self.repository.save_payment(order, payer, event)
        logger.info("order_paid", order_id=order.id, user_id=order.user_id, event_id=event.event_id)
        return order

    def compensate_failed_delivery(self, order_id: int, reason: str) -> Order | None:
        order = self.repository.get_order(order_id)
        if order is None or order.status != OrderStatus.PAID:
            return None

        refund = order.paid_with_money
        payer = self.repository.get_user_by_id(order.user_id)
        payer.balance += refund
        order.status = OrderStatus.CANCELLED
        event = OrderCancelled(order_id=order.id, refund=refund, reason=reason)
        self.repository.save_compensation(order, payer, event)
        return order

    def list_user_orders(self, current_user: User) -> list[Order]:
        return self.repository.list_by_user(current_user.id)

    def count_orders_for_day(self, day: date) -> int:
        start = datetime.combine(day, time.min)
        return self.repository.count_created_between(start, start + timedelta(days=1))

    def get_kitchen_orders(self) -> list[Order]:
        return self.repository.list_by_status(OrderStatus.PROCESSING)
