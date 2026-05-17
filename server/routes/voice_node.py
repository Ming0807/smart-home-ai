from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from server.config import Settings, get_settings
from server.models.voice_node import (
    VoiceNodeAudioHistoryClearResponse,
    VoiceNodeAudioHistoryResponse,
    VoiceNodeAudioReportResponse,
    VoiceNodeAudioStatusResponse,
    VoiceNodeCommandPollResponse,
    VoiceNodeCommandQueueResponse,
    VoiceNodeConfigResponse,
    VoiceNodeConfigUpdateRequest,
    VoiceNodeHeartbeatRequest,
    VoiceNodeHeartbeatResponse,
    VoiceNodePlaybackStatusRequest,
    VoiceNodePlaybackStatusResponse,
    VoiceNodeStatusResponse,
    VoiceNodeStreamStatusResponse,
)
from server.services.assistant_audio_service import get_assistant_audio_service
from server.services.tts_service import TTSService, get_tts_service
from server.services.voice_node_manager import VoiceNodeManager, get_voice_node_manager
from server.utils.pcm_audio import pcm16_to_wav_bytes, prepare_pcm16_for_stt

router = APIRouter(prefix="/voice-node", tags=["voice-node"])


@router.post(
    "/heartbeat",
    response_model=VoiceNodeHeartbeatResponse,
    status_code=status.HTTP_200_OK,
)
def voice_node_heartbeat(
    request: VoiceNodeHeartbeatRequest,
    voice_node_manager: VoiceNodeManager = Depends(get_voice_node_manager),
) -> VoiceNodeHeartbeatResponse:
    server_time = voice_node_manager.record_heartbeat(request)
    return VoiceNodeHeartbeatResponse(server_time=server_time)


@router.get(
    "/config",
    response_model=VoiceNodeConfigResponse,
)
def voice_node_config(
    device_id: str | None = Query(default=None, min_length=1, max_length=64),
    voice_node_manager: VoiceNodeManager = Depends(get_voice_node_manager),
) -> VoiceNodeConfigResponse:
    return voice_node_manager.get_config(device_id=device_id)


@router.post(
    "/config",
    response_model=VoiceNodeConfigResponse,
)
def update_voice_node_config(
    request: VoiceNodeConfigUpdateRequest,
    device_id: str | None = Query(default=None, min_length=1, max_length=64),
    voice_node_manager: VoiceNodeManager = Depends(get_voice_node_manager),
) -> VoiceNodeConfigResponse:
    return voice_node_manager.update_config(request=request, device_id=device_id)


@router.get(
    "/status",
    response_model=VoiceNodeStatusResponse,
)
def voice_node_status(
    device_id: str | None = Query(default=None, min_length=1, max_length=64),
    voice_node_manager: VoiceNodeManager = Depends(get_voice_node_manager),
) -> VoiceNodeStatusResponse:
    return voice_node_manager.get_status(device_id=device_id)


@router.get(
    "/audio/status",
    response_model=VoiceNodeAudioStatusResponse,
)
def voice_node_audio_status(
    device_id: str | None = Query(default=None, min_length=1, max_length=64),
    voice_node_manager: VoiceNodeManager = Depends(get_voice_node_manager),
) -> VoiceNodeAudioStatusResponse:
    return voice_node_manager.get_audio_status(device_id=device_id)


@router.get(
    "/audio/stream/status",
    response_model=VoiceNodeStreamStatusResponse,
)
def voice_node_audio_stream_status(
    device_id: str | None = Query(default=None, min_length=1, max_length=64),
    voice_node_manager: VoiceNodeManager = Depends(get_voice_node_manager),
) -> VoiceNodeStreamStatusResponse:
    return voice_node_manager.get_stream_status(device_id=device_id)


@router.websocket("/audio/stream")
async def voice_node_audio_stream(
    websocket: WebSocket,
    device_id: str = Query(default="voice-node-01", min_length=1, max_length=64),
    sample_rate: int = Query(default=16000, ge=8000, le=48000),
    channels: int = Query(default=1, ge=1, le=2),
    bits_per_sample: int = Query(default=16, ge=8, le=32),
    process: bool = Query(default=False),
    pir_state: int = Query(default=1, ge=0, le=1),
) -> None:
    voice_node_manager = get_voice_node_manager()
    assistant_audio_service = get_assistant_audio_service()
    settings = get_settings()
    pcm_buffer = bytearray()
    await websocket.accept()
    voice_node_manager.record_stream_open(
        device_id=device_id,
        sample_rate_hz=sample_rate,
        channels=channels,
        bits_per_sample=bits_per_sample,
    )
    await websocket.send_json({"status": "ok", "mode": "pcm_stream_diagnostics"})

    close_error: str | None = None
    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
            chunk = message.get("bytes")
            if chunk is not None:
                if process:
                    pcm_buffer.extend(chunk)
                voice_node_manager.record_stream_chunk(
                    device_id=device_id,
                    chunk=chunk,
                    sample_rate_hz=sample_rate,
                    channels=channels,
                    bits_per_sample=bits_per_sample,
                )
                continue
            text = (message.get("text") or "").strip().lower()
            if text == "ping":
                await websocket.send_json({"status": "ok"})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        close_error = exc.__class__.__name__
        raise
    finally:
        voice_node_manager.record_stream_close(device_id=device_id, error=close_error)
        if process and pcm_buffer and bits_per_sample == 16:
            stream_status = voice_node_manager.get_stream_status(device_id=device_id)
            pcm_bytes = bytes(pcm_buffer)
            if settings.voice_node_stream_preprocess and stream_status.speech_audio_seconds >= 0.4:
                pcm_bytes = prepare_pcm16_for_stt(
                    pcm_bytes=pcm_bytes,
                    sample_rate_hz=sample_rate,
                    vad_rms_threshold=stream_status.vad_rms_threshold,
                    trim_padding_ms=settings.voice_node_stream_trim_padding_ms,
                    target_peak=settings.stt_normalize_target_peak,
                    max_gain=settings.stt_normalize_max_gain,
                )
            wav_bytes = pcm16_to_wav_bytes(
                pcm_bytes=pcm_bytes,
                sample_rate_hz=sample_rate,
                channels=channels,
            )
            try:
                if stream_status.speech_audio_seconds < 0.4:
                    assistant_response = assistant_audio_service.handle_no_speech_audio_bytes(
                        audio_bytes=wav_bytes,
                        device_id=device_id,
                        content_type="audio/wav",
                        background_tasks=BackgroundTasks(),
                    )
                else:
                    assistant_response = await assistant_audio_service.handle_audio_bytes(
                        audio_bytes=wav_bytes,
                        filename="stream_command.wav",
                        content_type="audio/wav",
                        device_id=device_id,
                        pir_state=pir_state,
                        source="voice_node_stream",
                        background_tasks=BackgroundTasks(),
                    )
                if assistant_response.data.reply_audio_url:
                    voice_node_manager.queue_command(
                        "play_audio",
                        device_id=device_id,
                        audio_url=assistant_response.data.reply_audio_url,
                    )
            except Exception as exc:
                voice_node_manager.record_stream_close(
                    device_id=device_id,
                    error=f"process:{exc.__class__.__name__}",
                )
                raise


@router.get(
    "/audio/history",
    response_model=VoiceNodeAudioHistoryResponse,
)
def voice_node_audio_history(
    device_id: str | None = Query(default=None, min_length=1, max_length=64),
    voice_node_manager: VoiceNodeManager = Depends(get_voice_node_manager),
) -> VoiceNodeAudioHistoryResponse:
    return voice_node_manager.get_audio_history(device_id=device_id)


@router.get(
    "/audio/report",
    response_model=VoiceNodeAudioReportResponse,
)
def voice_node_audio_report(
    device_id: str | None = Query(default=None, min_length=1, max_length=64),
    voice_node_manager: VoiceNodeManager = Depends(get_voice_node_manager),
) -> VoiceNodeAudioReportResponse:
    return voice_node_manager.get_audio_report(device_id=device_id)


@router.delete(
    "/audio/history",
    response_model=VoiceNodeAudioHistoryClearResponse,
)
def clear_voice_node_audio_history(
    device_id: str | None = Query(default=None, min_length=1, max_length=64),
    voice_node_manager: VoiceNodeManager = Depends(get_voice_node_manager),
) -> VoiceNodeAudioHistoryClearResponse:
    return voice_node_manager.clear_audio_history(device_id=device_id)


@router.post(
    "/playback-status",
    response_model=VoiceNodePlaybackStatusResponse,
    status_code=status.HTTP_200_OK,
)
def voice_node_playback_status(
    request: VoiceNodePlaybackStatusRequest,
    voice_node_manager: VoiceNodeManager = Depends(get_voice_node_manager),
) -> VoiceNodePlaybackStatusResponse:
    voice_node_manager.record_playback_status(request)
    return VoiceNodePlaybackStatusResponse()


@router.post(
    "/commands/speaker-test",
    response_model=VoiceNodeCommandQueueResponse,
    status_code=status.HTTP_200_OK,
)
def queue_voice_node_speaker_test(
    device_id: str | None = Query(default=None, min_length=1, max_length=64),
    voice_node_manager: VoiceNodeManager = Depends(get_voice_node_manager),
) -> VoiceNodeCommandQueueResponse:
    return voice_node_manager.queue_command("speaker_test", device_id=device_id)


@router.post(
    "/commands/record-once",
    response_model=VoiceNodeCommandQueueResponse,
    status_code=status.HTTP_200_OK,
)
def queue_voice_node_record_once(
    device_id: str | None = Query(default=None, min_length=1, max_length=64),
    expected_text: str | None = Query(default=None, min_length=1, max_length=160),
    voice_node_manager: VoiceNodeManager = Depends(get_voice_node_manager),
) -> VoiceNodeCommandQueueResponse:
    return voice_node_manager.queue_command(
        "record_once",
        device_id=device_id,
        expected_text=expected_text,
    )


@router.post(
    "/commands/conversation-start",
    response_model=VoiceNodeCommandQueueResponse,
    status_code=status.HTTP_200_OK,
)
def queue_voice_node_conversation_start(
    device_id: str | None = Query(default=None, min_length=1, max_length=64),
    voice_node_manager: VoiceNodeManager = Depends(get_voice_node_manager),
) -> VoiceNodeCommandQueueResponse:
    return voice_node_manager.queue_command("conversation_start", device_id=device_id)


@router.post(
    "/commands/conversation-stop",
    response_model=VoiceNodeCommandQueueResponse,
    status_code=status.HTTP_200_OK,
)
def queue_voice_node_conversation_stop(
    device_id: str | None = Query(default=None, min_length=1, max_length=64),
    voice_node_manager: VoiceNodeManager = Depends(get_voice_node_manager),
) -> VoiceNodeCommandQueueResponse:
    return voice_node_manager.queue_command("conversation_stop", device_id=device_id)


@router.post(
    "/commands/wake-listen-start",
    response_model=VoiceNodeCommandQueueResponse,
    status_code=status.HTTP_200_OK,
)
def queue_voice_node_wake_listen_start(
    device_id: str | None = Query(default=None, min_length=1, max_length=64),
    voice_node_manager: VoiceNodeManager = Depends(get_voice_node_manager),
) -> VoiceNodeCommandQueueResponse:
    return voice_node_manager.queue_wake_listen_start(device_id=device_id)


@router.post(
    "/commands/wake-listen-stop",
    response_model=VoiceNodeCommandQueueResponse,
    status_code=status.HTTP_200_OK,
)
def queue_voice_node_wake_listen_stop(
    device_id: str | None = Query(default=None, min_length=1, max_length=64),
    voice_node_manager: VoiceNodeManager = Depends(get_voice_node_manager),
) -> VoiceNodeCommandQueueResponse:
    return voice_node_manager.queue_wake_listen_stop(device_id=device_id)


@router.post(
    "/commands/stream-test-start",
    response_model=VoiceNodeCommandQueueResponse,
    status_code=status.HTTP_200_OK,
)
def queue_voice_node_stream_test_start(
    device_id: str | None = Query(default=None, min_length=1, max_length=64),
    voice_node_manager: VoiceNodeManager = Depends(get_voice_node_manager),
) -> VoiceNodeCommandQueueResponse:
    return voice_node_manager.queue_command("stream_test_start", device_id=device_id)


@router.post(
    "/commands/stream-process-start",
    response_model=VoiceNodeCommandQueueResponse,
    status_code=status.HTTP_200_OK,
)
def queue_voice_node_stream_process_start(
    device_id: str | None = Query(default=None, min_length=1, max_length=64),
    voice_node_manager: VoiceNodeManager = Depends(get_voice_node_manager),
) -> VoiceNodeCommandQueueResponse:
    return voice_node_manager.queue_command("stream_process_start", device_id=device_id)


@router.post(
    "/commands/speech-test",
    response_model=VoiceNodeCommandQueueResponse,
    status_code=status.HTTP_200_OK,
)
def queue_voice_node_speech_test(
    device_id: str | None = Query(default=None, min_length=1, max_length=64),
    voice_node_manager: VoiceNodeManager = Depends(get_voice_node_manager),
    tts_service: TTSService = Depends(get_tts_service),
    settings: Settings = Depends(get_settings),
) -> VoiceNodeCommandQueueResponse:
    tts_result = tts_service.synthesize(
        "ทดสอบเสียงน้องฟ้า เสียงนี้ส่งจากเซิร์ฟเวอร์ไปยังบอร์ดแบบสตรีมมิง"
    )
    if not tts_result.ok or not tts_result.audio_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=tts_result.error or "voice node speech test audio not ready",
        )

    audio_url = voice_node_manager.to_voice_node_audio_url(tts_result.audio_url)
    if (
        audio_url is not None
        and settings.voice_node_reply_audio_format.strip().lower() == "wav"
    ):
        audio_url = audio_url.replace(
            "/voice-node/audio/current",
            "/voice-node/audio/current.wav",
            1,
        )
    return voice_node_manager.queue_command(
        "play_audio",
        device_id=device_id,
        audio_url=audio_url,
    )


@router.get(
    "/commands",
    response_model=VoiceNodeCommandPollResponse,
)
def poll_voice_node_command(
    device_id: str | None = Query(default=None, min_length=1, max_length=64),
    voice_node_manager: VoiceNodeManager = Depends(get_voice_node_manager),
) -> VoiceNodeCommandPollResponse:
    return voice_node_manager.pop_next_command(device_id=device_id)


@router.get(
    "/audio/current",
    include_in_schema=False,
)
def current_voice_node_audio(
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
            "X-Generated-At": datetime.now(timezone.utc).isoformat(),
        },
    )


@router.get(
    "/audio/current.wav",
    include_in_schema=False,
)
def current_voice_node_audio_wav(
    token: str | None = Query(default=None, min_length=1, max_length=64),
    tts_service: TTSService = Depends(get_tts_service),
    settings: Settings = Depends(get_settings),
) -> Response:
    audio_bytes = tts_service.get_current_audio_wav_bytes(
        token=token,
        sample_rate=settings.voice_node_reply_sample_rate,
    )
    if audio_bytes is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="wav audio not ready")

    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Accept-Ranges": "none",
            "X-Generated-At": datetime.now(timezone.utc).isoformat(),
        },
    )


@router.get(
    "/audio/uploaded",
    include_in_schema=False,
)
def latest_uploaded_voice_node_audio(
    device_id: str | None = Query(default=None, min_length=1, max_length=64),
    voice_node_manager: VoiceNodeManager = Depends(get_voice_node_manager),
) -> Response:
    latest_audio = voice_node_manager.get_uploaded_audio(device_id=device_id)
    if latest_audio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="uploaded audio not ready")

    audio_bytes, content_type, received_at = latest_audio
    return Response(
        content=audio_bytes,
        media_type=content_type,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Accept-Ranges": "none",
            "X-Uploaded-At": received_at.isoformat(),
        },
    )
