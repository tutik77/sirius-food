from collections.abc import Callable

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel

from app.domain.entities import User
from app.modules.assistant.service import AssistantAgent
from app.modules.assistant.tools import AssistantContext, build_tools

SYSTEM_PROMPT = """Ты — ассистент столовой «Сириус.Еда» в кампусе «Сириус». Отвечай по-русски, коротко и дружелюбно.
Отвечай только по фактам из инструментов: о блюдах, ценах и правилах — через search_knowledge,
о заказах клиента — через my_orders, о баллах и промокодах — через my_loyalty. Ничего не выдумывай:
если в инструментах нет ответа, так и скажи и предложи обратиться в поддержку.
Когда уместно, предлагай повторить прошлый заказ, оплатить часть заказа баллами (до 50 %) или применить промокод."""


class LangGraphAssistantAgent(AssistantAgent):
    def __init__(self, model: Callable[[], BaseChatModel], context: AssistantContext):
        self.model = model
        self.context = context

    def answer(self, user: User, question: str) -> str:
        agent = create_agent(self.model(), build_tools(user, self.context), system_prompt=SYSTEM_PROMPT)
        result = agent.invoke({"messages": [("user", question)]})
        return result["messages"][-1].content
