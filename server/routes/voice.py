from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from server.models.voice import SpeakRequest, SpeakResponse, VoiceStatusResponse
from server.services.tts_service import TTSService, get_tts_service

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
