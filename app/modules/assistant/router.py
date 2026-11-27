from fastapi import APIRouter, Depends

from app.container import get_assistant_service
from app.core.dependencies import get_current_user
from app.domain.entities import User
from app.domain.errors import DomainError
from app.http_errors import to_http
from app.modules.assistant.service import AssistantService
from app.schemas import AssistantAnswer, AssistantFeedback, AssistantQuestion

router = APIRouter()


@router.post("/chat", response_model=AssistantAnswer)
def chat(
    payload: AssistantQuestion,
    current_user: User = Depends(get_current_user),
    service: AssistantService = Depends(get_assistant_service),
):
    return service.ask(current_user, payload.question)


@router.post("/messages/{message_id}/feedback", response_model=AssistantAnswer)
def feedback(
    message_id: int,
    payload: AssistantFeedback,
    current_user: User = Depends(get_current_user),
    service: AssistantService = Depends(get_assistant_service),
):
    try:
        return service.rate(current_user, message_id, payload.helpful)
    except DomainError as e:
        raise to_http(e) from e
