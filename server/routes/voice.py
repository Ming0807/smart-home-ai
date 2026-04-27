from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from pydantic import ValidationError

from server.models.voice import (
    SpeakRequest,
    SpeakResponse,
    VoiceChatRequestMeta,
    VoiceChatResponse,
    VoiceStatusResponse,
)
from server.services.stt_service import STTService, get_stt_service
from server.services.tts_service import TTSService, get_tts_service
from server.services.voice_conversation_service import (
    VoiceConversationService,
    get_voice_conversation_service,
)

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post(
    "/speak",
    response_model=SpeakResponse,
    status_code=status.HTTP_200_OK,
)
def speak(
    request: SpeakRequest,
    tts_service: TTSService = Depends(get_tts_service),
) -> SpeakResponse:
    result = tts_service.synthesize(request.text)
    if result.ok:
        return SpeakResponse(
            status="ok",
            text=result.text,
            audio_url=result.audio_url,
            provider=result.provider,
        )
    return SpeakResponse(
        status="error",
        text=result.text,
        provider=result.provider,
        error=result.error,
    )


@router.post(
    "/chat",
    response_model=VoiceChatResponse,
    status_code=status.HTTP_200_OK,
)
async def voice_chat(
    background_tasks: BackgroundTasks,
    message: str | None = Form(default=None),
    pir_state: int = Form(default=0),
    audio: UploadFile | None = File(default=None),
    stt_service: STTService = Depends(get_stt_service),
    voice_conversation_service: VoiceConversationService = Depends(
        get_voice_conversation_service
    ),
) -> VoiceChatResponse:
    try:
        request_meta = VoiceChatRequestMeta(message=message, pir_state=pir_state)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc
    heard_text = request_meta.message

    if heard_text is None:
        if audio is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="message or audio is required",
            )

        stt_result = await stt_service.transcribe_upload(audio)
        if not stt_result.ok:
            return VoiceChatResponse(
                data=voice_conversation_service.build_stt_unavailable_response(
                    background_tasks=background_tasks,
                )
            )
        heard_text = stt_result.text

    return VoiceChatResponse(
        data=voice_conversation_service.handle_turn(
            heard_text=heard_text,
            pir_state=request_meta.pir_state,
            background_tasks=background_tasks,
        )
    )


@router.get(
    "/status",
    response_model=VoiceStatusResponse,
)
def voice_status(
    tts_service: TTSService = Depends(get_tts_service),
) -> VoiceStatusResponse:
    status_data = tts_service.get_status()
    return VoiceStatusResponse(
        tts_enabled=status_data.tts_enabled,
        provider=status_data.provider,
        output_file=status_data.output_file,
        current_token=status_data.current_token,
        audio_ready=status_data.audio_ready,
        file_size_bytes=status_data.file_size_bytes,
        last_generated_at=status_data.last_generated_at,
        last_error=status_data.last_error,
    )


@router.get(
    "/audio/current",
    include_in_schema=False,
)
def current_audio(
    token: str | None = Query(default=None, min_length=1, max_length=64),
    tts_service: TTSService = Depends(get_tts_service),
) -> Response:
    audio_bytes = tts_service.get_current_audio_bytes(token=token)
    if audio_bytes is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="audio not ready")

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Accept-Ranges": "none",
        },
    )
