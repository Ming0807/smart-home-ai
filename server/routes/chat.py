import logging

from fastapi import APIRouter, BackgroundTasks, Depends, status

from server.config import Settings, get_settings
from server.models.chat import ChatRequest, ChatResponse
from server.services.device_control import (
    DeviceControlService,
    get_device_control_service,
)
from server.services.intent_router import IntentRouter, get_intent_router
from server.services.llm_manager import LLMManager, get_llm_manager
from server.services.sensor_manager import SensorManager, get_sensor_manager
from server.services.system_status_service import (
    SystemStatusService,
    get_system_status_service,
)
from server.services.tts_service import TTSService, get_tts_service
from server.services.weather_service import WeatherService, get_weather_service
from server.utils.observability import log_timing, start_timer

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    intent_router: IntentRouter = Depends(get_intent_router),
    llm_manager: LLMManager = Depends(get_llm_manager),
    device_control_service: DeviceControlService = Depends(get_device_control_service),
    sensor_manager: SensorManager = Depends(get_sensor_manager),
    system_status_service: SystemStatusService = Depends(get_system_status_service),
    tts_service: TTSService = Depends(get_tts_service),
    weather_service: WeatherService = Depends(get_weather_service),
) -> ChatResponse:
    timer = start_timer()
    intent = "unknown"
    source = "unknown"
    status_text = "ok"

    try:
        intent_match = intent_router.classify(request.message)
        intent = intent_match.intent
        if intent_match.intent == "device_control":
            device_result = device_control_service.handle_message(
                message=request.message,
                device_id=settings.default_esp32_device_id,
            )
            source = device_result.source
            return ChatResponse(
                reply=device_result.reply,
                intent="device_control",
                source=device_result.source,
                audio_url=_schedule_audio_generation(
                    settings,
                    background_tasks,
                    tts_service,
                    device_result.reply,
                ),
            )

        if intent_match.intent == "sensor_query":
            sensor_answer = sensor_manager.answer_sensor_query(
                message=request.message,
                device_id=settings.default_esp32_device_id,
                freshness_seconds=settings.sensor_freshness_seconds,
            )
            source = sensor_answer.source
            return ChatResponse(
                reply=sensor_answer.reply,
                intent="sensor_query",
                source=sensor_answer.source,
                audio_url=_schedule_audio_generation(
                    settings,
                    background_tasks,
                    tts_service,
                    sensor_answer.reply,
                ),
            )

        if intent_match.intent == "system_status":
            system_status_answer = system_status_service.get_status(
                device_id=settings.default_esp32_device_id,
            )
            source = system_status_answer.source
            return ChatResponse(
                reply=system_status_answer.reply,
                intent="system_status",
                source=system_status_answer.source,
                audio_url=_schedule_audio_generation(
                    settings,
                    background_tasks,
                    tts_service,
                    system_status_answer.reply,
                ),
            )

        if intent_match.intent == "weather_query":
            weather_answer = weather_service.answer_weather_query(request.message)
            source = weather_answer.source
            return ChatResponse(
                reply=weather_answer.reply,
                intent="weather_query",
                source=weather_answer.source,
                audio_url=_schedule_audio_generation(
                    settings,
                    background_tasks,
                    tts_service,
                    weather_answer.reply,
                ),
            )

        placeholder_response = intent_router.get_placeholder_response(intent_match.intent)
        if placeholder_response is not None:
            source = "placeholder"
            return ChatResponse(
                reply=placeholder_response.reply,
                intent=placeholder_response.intent,
                source="placeholder",
                audio_url=_schedule_audio_generation(
                    settings,
                    background_tasks,
                    tts_service,
                    placeholder_response.reply,
                ),
            )

        llm_response = llm_manager.generate_reply(request.message)
        intent = "general_chat"
        source = llm_response.source
        return ChatResponse(
            reply=llm_response.reply,
            intent="general_chat",
            source=llm_response.source,
            audio_url=_schedule_audio_generation(
                settings,
                background_tasks,
                tts_service,
                llm_response.reply,
            ),
        )
    except Exception:
        status_text = "error"
        raise
    finally:
        log_timing(
            logger,
            settings,
            "chat.total",
            timer.elapsed_ms,
            intent=intent,
            source=source,
            status=status_text,
        )


def _schedule_audio_generation(
    settings: Settings,
    background_tasks: BackgroundTasks,
    tts_service: TTSService,
    reply: str,
) -> str | None:
    if not settings.demo_voice_mode or not settings.tts_enabled:
        return None
    token, audio_url = tts_service.create_pending_audio_url()
    background_tasks.add_task(tts_service.synthesize, reply, token)
    return audio_url
