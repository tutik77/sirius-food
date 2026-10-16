"""
Слой бизнес-логики модуля заказов (круги Entities и Use Cases).

Импорты fastapi и sqlalchemy здесь запрещены: сервис зависит только
от доменных сущностей и абстрактного OrderRepository.
"""
from app.domain.entities import Order, OrderStatus
from app.modules.orders.exceptions import (
    InsufficientFundsError,
    MenuItemNotFoundError,
    MenuItemUnavailableError,
    UserNotFoundError,
)
from app.modules.orders.repository import OrderRepository


class OrderService:
    """Бизнес-правила оформления заказов."""

    def __init__(self, repository: OrderRepository):
        # Зависимость приходит снаружи через конструктор (инверсия зависимостей).
        self.repository = repository

    def create_order(self, user_id: int, item_id: int, quantity: int) -> Order:
        """
        Сценарий оформления заказа: проверяет пользователя, блюдо и баланс,
        списывает стоимость и сохраняет заказ.
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
        )
        return self.repository.save_order(order, payer=user)
