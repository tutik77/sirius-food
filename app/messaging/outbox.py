from datetime import datetime

from sqlalchemy.orm import Session

from app import models
from app.domain.events import Event
from app.messaging.context import outgoing_headers


def to_outbox_row(event: Event) -> models.OutboxEvent:
    return models.OutboxEvent(
        id=event.event_id,
        routing_key=event.routing_key,
        payload=event.payload(),
        headers=outgoing_headers(),
    )


class OutboxRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, event: Event) -> None:
        self.db.add(to_outbox_row(event))

    def fetch_unpublished(self, limit: int = 100) -> list[models.OutboxEvent]:
        return (
            self.db.query(models.OutboxEvent)
            .filter(models.OutboxEvent.published_at.is_(None))
            .order_by(models.OutboxEvent.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
            .all()
        )

    def mark_published(self, row: models.OutboxEvent) -> None:
        row.published_at = datetime.utcnow()
