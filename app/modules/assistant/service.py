import time
from abc import ABC, abstractmethod

import structlog

from app.domain.entities import AssistantMessage, User
from app.modules.assistant import metrics
from app.modules.assistant.exceptions import ForeignMessageError, MessageNotFoundError
from app.modules.assistant.repository import AssistantMessageRepository

logger = structlog.get_logger(__name__)

FALLBACK_ANSWER = "Извините, ассистент сейчас недоступен. Попробуйте позже."


class AssistantAgent(ABC):
    @abstractmethod
    def answer(self, user: User, question: str) -> str: ...


class AssistantService:
    def __init__(self, agent: AssistantAgent, repository: AssistantMessageRepository):
        self.agent = agent
        self.repository = repository

    def ask(self, user: User, question: str) -> AssistantMessage:
        started = time.perf_counter()
        try:
            answer, is_fallback = self.agent.answer(user, question), False
        except Exception:
            logger.exception("assistant_failed", user_id=user.id)
            answer, is_fallback = FALLBACK_ANSWER, True
        seconds = time.perf_counter() - started

        metrics.RESPONSE_SECONDS.observe(seconds)
        metrics.REQUESTS.labels(outcome="fallback" if is_fallback else "answered").inc()
        message = self.repository.add(
            AssistantMessage(
                id=None,
                user_id=user.id,
                question=question,
                answer=answer,
                latency_ms=round(seconds * 1000),
                is_fallback=is_fallback,
            )
        )
        logger.info(
            "assistant_answered",
            message_id=message.id,
            user_id=user.id,
            question=question,
            answer=answer,
            latency_ms=message.latency_ms,
            is_fallback=is_fallback,
        )
        return message

    def rate(self, user: User, message_id: int, helpful: bool) -> AssistantMessage:
        message = self.repository.get(message_id)
        if message is None:
            raise MessageNotFoundError()
        if message.user_id != user.id:
            raise ForeignMessageError()

        message.helpful = helpful
        self.repository.save_feedback(message)
        metrics.FEEDBACK.labels(helpful=str(helpful).lower()).inc()
        logger.info("assistant_feedback", message_id=message.id, helpful=helpful)
        return message
