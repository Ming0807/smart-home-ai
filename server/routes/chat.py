from fastapi import APIRouter, Depends, status

from server.config import Settings, get_settings
from server.models.chat import ChatRequest, ChatResponse
from server.services.device_control import (
    DeviceControlService,
    get_device_control_service,
)
from server.services.intent_router import IntentRouter, get_intent_router
from server.services.llm_manager import LLMManager, get_llm_manager
from server.services.sensor_manager import SensorManager, get_sensor_manager
from server.services.weather_service import WeatherService, get_weather_service

router = APIRouter(tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
def chat(
    request: ChatRequest,
    settings: Settings = Depends(get_settings),
    intent_router: IntentRouter = Depends(get_intent_router),
    llm_manager: LLMManager = Depends(get_llm_manager),
    device_control_service: DeviceControlService = Depends(get_device_control_service),
    sensor_manager: SensorManager = Depends(get_sensor_manager),
    weather_service: WeatherService = Depends(get_weather_service),
) -> ChatResponse:
    intent_match = intent_router.classify(request.message)
    if intent_match.intent == "device_control":
        device_result = device_control_service.handle_message(
            message=request.message,
            device_id=settings.default_esp32_device_id,
        )
        return ChatResponse(
            reply=device_result.reply,
            intent="device_control",
            source=device_result.source,
        )

    if intent_match.intent == "sensor_query":
        sensor_answer = sensor_manager.answer_sensor_query(
            message=request.message,
            device_id=settings.default_esp32_device_id,
            freshness_seconds=settings.sensor_freshness_seconds,
        )
        return ChatResponse(
            reply=sensor_answer.reply,
            intent="sensor_query",
            source=sensor_answer.source,
        )

    if intent_match.intent == "weather_query":
        weather_answer = weather_service.answer_weather_query(request.message)
        return ChatResponse(
            reply=weather_answer.reply,
            intent="weather_query",
            source=weather_answer.source,
        )

    placeholder_response = intent_router.get_placeholder_response(intent_match.intent)
    if placeholder_response is not None:
        return ChatResponse(
            reply=placeholder_response.reply,
            intent=placeholder_response.intent,
            source="placeholder",
        )

    llm_response = llm_manager.generate_reply(request.message)
    return ChatResponse(
        reply=llm_response.reply,
        intent="general_chat",
        source=llm_response.source,
    )
