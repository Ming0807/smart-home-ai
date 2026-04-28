from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.responses import StreamingResponse

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


@router.post(
    "/chat/stream",
    status_code=status.HTTP_200_OK,
)
def chat_stream(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    chat_service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    return StreamingResponse(
        chat_service.stream_message(request.message, background_tasks=background_tasks),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
        background=background_tasks,
    )
