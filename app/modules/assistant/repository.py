from abc import ABC, abstractmethod
from dataclasses import replace
from datetime import datetime

from sqlalchemy.orm import Session

from app import models
from app.domain.entities import AssistantMessage
from app.mappers import to_assistant_message
from app.memory_storage import InMemoryStorage, copy


class AssistantMessageRepository(ABC):
    @abstractmethod
    def add(self, message: AssistantMessage) -> AssistantMessage: ...

    @abstractmethod
    def get(self, message_id: int) -> AssistantMessage | None: ...

    @abstractmethod
    def save_feedback(self, message: AssistantMessage) -> None: ...


class SqlAlchemyAssistantMessageRepository(AssistantMessageRepository):
    def __init__(self, db: Session):
        self.db = db

    def add(self, message: AssistantMessage) -> AssistantMessage:
        row = models.AssistantMessage(
            user_id=message.user_id,
            question=message.question,
            answer=message.answer,
            latency_ms=message.latency_ms,
            is_fallback=message.is_fallback,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return to_assistant_message(row)

    def get(self, message_id: int) -> AssistantMessage | None:
        row = self.db.get(models.AssistantMessage, message_id)
        return to_assistant_message(row) if row else None

    def save_feedback(self, message: AssistantMessage) -> None:
        self.db.get(models.AssistantMessage, message.id).helpful = message.helpful
        self.db.commit()


class InMemoryAssistantMessageRepository(AssistantMessageRepository):
    def __init__(self, storage: InMemoryStorage):
        self.storage = storage

    def add(self, message: AssistantMessage) -> AssistantMessage:
        saved = replace(message, id=self.storage.next_id("assistant_messages"), created_at=datetime.utcnow())
        self.storage.assistant_messages[saved.id] = saved
        return copy(saved)

    def get(self, message_id: int) -> AssistantMessage | None:
        return copy(self.storage.assistant_messages.get(message_id))

    def save_feedback(self, message: AssistantMessage) -> None:
        self.storage.assistant_messages[message.id] = copy(message)
