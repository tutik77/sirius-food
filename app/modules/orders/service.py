"""
Слой бизнес-логики модуля заказов (круги Entities и Use Cases).

Импорты fastapi и sqlalchemy здесь запрещены: сервис зависит только
от доменных сущностей и абстрактного OrderRepository.
"""
from app.domain.entities import Order, OrderStatus, User
from app.modules.orders.exceptions import (
    AccessDeniedError,
    InsufficientFundsError,
    MenuItemNotFoundError,
    MenuItemUnavailableError,
    OrderCannotBeCancelledError,
    OrderNotFoundError,
    UserNotFoundError,
)
from app.modules.orders.repository import OrderRepository


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
        return self.repository.save_order(order, payer=user)

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

    def list_user_orders(self, current_user: User) -> list[Order]:
        """Заказы текущего пользователя — только его собственные."""
        return self.repository.list_by_user(current_user.id)

    def get_kitchen_orders(self) -> list[Order]:
        """Очередь кухни: заказы, которые нужно приготовить."""
        return self.repository.list_by_status(OrderStatus.PROCESSING)
