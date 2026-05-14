from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    UploadFile,
    status,
)

from server.models.voice_node import AssistantAudioResponse
from server.services.assistant_audio_service import (
    AssistantAudioService,
    get_assistant_audio_service,
)

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post(
    "/audio",
    response_model=AssistantAudioResponse,
    status_code=status.HTTP_200_OK,
)
async def assistant_audio(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    device_id: str = Form(default="voice-node-01", min_length=1, max_length=64),
    pir_state: int = Form(default=0, ge=0, le=1),
    source: str = Form(default="voice_node", max_length=40),
    assistant_audio_service: AssistantAudioService = Depends(get_assistant_audio_service),
) -> AssistantAudioResponse:
    return await assistant_audio_service.handle_audio_upload(
        audio=audio,
        device_id=device_id,
        pir_state=pir_state,
        background_tasks=background_tasks,
    )

