from sqlalchemy.orm import Session

from app import models


def claim_event(db: Session, consumer: str, event_id: str) -> bool:
    if db.get(models.ProcessedEvent, (consumer, event_id)) is not None:
        return False
    db.add(models.ProcessedEvent(consumer=consumer, event_id=event_id))
    return True
