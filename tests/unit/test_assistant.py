from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.vectorstores import InMemoryVectorStore

from app.domain.entities import DiscountType, PromoCode, User
from app.memory_storage import InMemoryStorage
from app.modules.assistant.exceptions import ForeignMessageError, MessageNotFoundError
from app.modules.assistant.knowledge import FAQ_PATH, KnowledgeBase, faq_documents, menu_documents
from app.modules.assistant.langgraph_agent import LangGraphAssistantAgent
from app.modules.assistant.repository import InMemoryAssistantMessageRepository
from app.modules.assistant.service import FALLBACK_ANSWER, AssistantAgent, AssistantService
from app.modules.assistant.tools import AssistantContext, build_tools
from app.modules.loyalty.repository import InMemoryLoyaltyRepository
from app.modules.loyalty.service import LoyaltyService
from app.modules.menu.repository import InMemoryMenuRepository
from app.modules.menu.service import MenuService
from app.modules.orders.repository import InMemoryOrderRepository
from app.modules.orders.service import OrderService
from app.modules.promo.repository import InMemoryPromoRepository
from app.modules.promo.service import PromoService


class FixedAgent(AssistantAgent):
    def __init__(self, answer: str | None = None):
        self.reply = answer

    def answer(self, user: User, question: str) -> str:
        if self.reply is None:
            raise TimeoutError("LLM не отвечает")
        return self.reply


class ScriptedModel(BaseChatModel):
    responses: list
    seen: list = []

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        self.seen.append(messages)
        return ChatResult(generations=[ChatGeneration(message=self.responses.pop(0))])

    def bind_tools(self, tools, **kwargs):
        return self


@pytest.fixture
def storage():
    return InMemoryStorage()


@pytest.fixture
def student(storage):
    user = User(id=storage.next_id("users"), email="anna@sirius.ru", balance=1000)
    storage.users[user.id] = user
    return user


@pytest.fixture
def context(storage):
    menu = MenuService(InMemoryMenuRepository(storage))
    for name, price in [("Сырники со сметаной", 150), ("Борщ с пампушками", 250), ("Капучино", 140)]:
        menu.create_item(name, price)
    store = InMemoryVectorStore.from_documents(
        menu_documents(menu.list_items()) + faq_documents(FAQ_PATH.read_text(encoding="utf-8")),
        DeterministicFakeEmbedding(size=64),
    )
    promo = PromoService(InMemoryPromoRepository(storage))
    loyalty = LoyaltyService(InMemoryLoyaltyRepository(storage))
    return AssistantContext(
        knowledge=KnowledgeBase(lambda: store),
        orders=OrderService(InMemoryOrderRepository(storage), promo, loyalty),
        menu=menu,
        loyalty=loyalty,
        promo=promo,
    )


def tool(user: User, context: AssistantContext, name: str):
    return next(t for t in build_tools(user, context) if t.name == name)


def test_answer_is_stored_with_latency(storage, student):
    service = AssistantService(FixedAgent("Есть сырники за 150 ₽"), InMemoryAssistantMessageRepository(storage))

    message = service.ask(student, "Что есть на завтрак?")

    assert (message.answer, message.is_fallback, message.user_id) == ("Есть сырники за 150 ₽", False, student.id)
    assert message.latency_ms >= 0
    assert storage.assistant_messages[message.id].question == "Что есть на завтрак?"


def test_unavailable_model_gives_fallback(storage, student):
    service = AssistantService(FixedAgent(None), InMemoryAssistantMessageRepository(storage))

    message = service.ask(student, "Где мой заказ?")

    assert (message.answer, message.is_fallback) == (FALLBACK_ANSWER, True)


def test_feedback_only_for_own_answers(storage, student):
    service = AssistantService(FixedAgent("Ответ"), InMemoryAssistantMessageRepository(storage))
    message = service.ask(student, "Вопрос")
    stranger = User(id=999, email="x@sirius.ru")

    assert service.rate(student, message.id, helpful=True).helpful is True
    with pytest.raises(ForeignMessageError):
        service.rate(stranger, message.id, helpful=False)
    with pytest.raises(MessageNotFoundError):
        service.rate(student, 404, helpful=True)


def test_faq_is_split_into_topics():
    topics = [d.metadata["topic"] for d in faq_documents(FAQ_PATH.read_text(encoding="utf-8"))]

    assert topics[:3] == ["Доставка", "Время работы", "Оплата"]
    assert len(topics) == 7


def test_search_knowledge_returns_documents(student, context):
    result = tool(student, context, "search_knowledge").invoke({"query": "Сырники со сметаной"})

    assert "Блюдо «" in result or "." in result
    assert len(result.splitlines()) == 4


def test_my_orders_shows_only_current_user_orders(storage, student, context):
    other = User(id=storage.next_id("users"), email="boris@sirius.ru", balance=1000)
    storage.users[other.id] = other
    context.orders.create_order(student.id, item_id=1, quantity=2)
    context.orders.create_order(other.id, item_id=2, quantity=1)

    result = tool(student, context, "my_orders").invoke({})

    assert "Сырники со сметаной × 2, 300 ₽, статус processing" in result
    assert "Борщ" not in result


def test_my_loyalty_shows_points_and_active_promo(student, context):
    context.loyalty.earn(student.id, order_id=1, paid_amount=Decimal("1000"))
    now = datetime.utcnow()
    context.promo.create(
        PromoCode(id=None, code="STUDENT10", discount_type=DiscountType.PERCENT, discount_value=Decimal("10"),
                  valid_from=now - timedelta(days=1), valid_until=now + timedelta(days=1), max_uses=10)
    )

    result = tool(student, context, "my_loyalty").invoke({})

    assert "Баланс: 30.00 баллов, уровень bronze, начисление 3 %" in result
    assert "STUDENT10 (10%)" in result


def test_langgraph_agent_calls_tool_bound_to_user(storage, student, context):
    menu_item = context.menu.list_items()[0]
    context.orders.create_order(student.id, item_id=menu_item.id, quantity=1)
    model = ScriptedModel(
        responses=[
            AIMessage(content="", tool_calls=[{"name": "my_orders", "args": {}, "id": "call-1"}]),
            AIMessage(content="Ваш заказ #1 со сырниками ждёт оплаты."),
        ],
        seen=[],
    )

    answer = LangGraphAssistantAgent(lambda: model, context).answer(student, "Где мой заказ?")

    assert answer == "Ваш заказ #1 со сырниками ждёт оплаты."
    tool_result = next(m for m in model.seen[-1] if isinstance(m, ToolMessage))
    assert "Заказ #1: Сырники со сметаной × 1" in tool_result.content
    assert "Сириус.Еда" in model.seen[0][0].content
