from dataclasses import dataclass
from datetime import datetime

from langchain_core.tools import BaseTool, tool

from app.domain.entities import TIER_RATES, LoyaltyTier, User
from app.domain.errors import NotFoundError
from app.modules.assistant.knowledge import KnowledgeBase
from app.modules.loyalty.service import LoyaltyService
from app.modules.menu.service import MenuService
from app.modules.orders.service import OrderService
from app.modules.promo.service import PromoService

RECENT_ORDERS = 5


@dataclass
class AssistantContext:
    knowledge: KnowledgeBase
    orders: OrderService
    menu: MenuService
    loyalty: LoyaltyService
    promo: PromoService


def build_tools(user: User, context: AssistantContext) -> list[BaseTool]:
    @tool(description="Ищет в меню столовой и в правилах (доставка, оплата, отмена, лояльность, промокоды). Используй для любых вопросов о блюдах, ценах и правилах.")
    def search_knowledge(query: str) -> str:
        documents = context.knowledge.search(query)
        return "\n".join(document.page_content for document in documents) or "Ничего не найдено."

    @tool(description="Последние заказы текущего клиента: блюдо, количество, сумма, статус. Используй для вопросов «где мой заказ», «что я заказывал».")
    def my_orders() -> str:
        orders = context.orders.list_user_orders(user)[-RECENT_ORDERS:]
        if not orders:
            return "У клиента пока нет заказов."
        return "\n".join(
            f"Заказ #{order.id}: {dish_name(context.menu, order.item_id)} × {order.quantity}, "
            f"{order.total_cost:.0f} ₽, статус {order.status}"
            for order in reversed(orders)
        )

    @tool(description="Баллы и уровень лояльности текущего клиента и действующие промокоды. Используй, чтобы предложить скидку или оплату баллами.")
    def my_loyalty() -> str:
        account = context.loyalty.account_for(user.id)
        percent = int(TIER_RATES[LoyaltyTier(account.tier)] * 100)
        now = datetime.utcnow()
        codes = [p for p in context.promo.list_codes() if p.is_valid_at(now) and p.has_uses_left()]
        promo_text = ", ".join(f"{p.code} ({p.discount_value:g}{'%' if p.discount_type == 'percent' else ' ₽'})" for p in codes)
        return (
            f"Баланс: {account.balance} баллов, уровень {account.tier}, начисление {percent} % от суммы заказа. "
            f"Действующие промокоды: {promo_text or 'нет'}."
        )

    return [search_knowledge, my_orders, my_loyalty]


def dish_name(menu: MenuService, item_id: int) -> str:
    try:
        return menu.get_item(item_id).name
    except NotFoundError:
        return f"блюдо #{item_id}"
