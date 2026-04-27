from fastapi import APIRouter, BackgroundTasks, Depends, status

from server.models.chat import ChatRequest, ChatResponse
from server.services.chat_service import ChatService, get_chat_service

router = APIRouter(tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    return chat_service.handle_message(request.message, background_tasks=background_tasks)
