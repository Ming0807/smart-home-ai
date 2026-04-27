from __future__ import annotations

import logging

from fastapi import BackgroundTasks

from server.config import Settings, get_settings
from server.models.chat import ChatResponse
from server.services.device_control import (
    DeviceControlService,
    get_device_control_service,
)
from server.services.intent_router import IntentRouter, get_intent_router
from server.services.llm_manager import LLMManager, get_llm_manager
from server.services.navigation_service import (
    NavigationService,
    get_navigation_service,
)
from server.services.news_service import NewsService, get_news_service
from server.services.sensor_manager import SensorManager, get_sensor_manager
from server.services.system_status_service import (
    SystemStatusService,
    get_system_status_service,
)
from server.services.traffic_service import TrafficService, get_traffic_service
from server.services.tts_service import TTSService, get_tts_service
from server.services.weather_service import WeatherService, get_weather_service
from server.utils.observability import log_timing, start_timer

logger = logging.getLogger(__name__)


class ChatService:
    """Shared chat orchestration for text and voice entry points."""

    def __init__(
        self,
        settings: Settings,
        intent_router: IntentRouter,
        llm_manager: LLMManager,
        device_control_service: DeviceControlService,
        navigation_service: NavigationService,
        news_service: NewsService,
        sensor_manager: SensorManager,
        system_status_service: SystemStatusService,
        traffic_service: TrafficService,
        tts_service: TTSService,
        weather_service: WeatherService,
    ) -> None:
        self._settings = settings
        self._intent_router = intent_router
        self._llm_manager = llm_manager
        self._device_control_service = device_control_service
        self._navigation_service = navigation_service
        self._news_service = news_service
        self._sensor_manager = sensor_manager
        self._system_status_service = system_status_service
        self._traffic_service = traffic_service
        self._tts_service = tts_service
        self._weather_service = weather_service

    def handle_message(
        self,
        message: str,
        background_tasks: BackgroundTasks,
        force_audio: bool = False,
        suppress_audio: bool = False,
    ) -> ChatResponse:
        timer = start_timer()
        intent = "unknown"
        source = "unknown"
        status_text = "ok"

        try:
            intent_match = self._intent_router.classify(message)
            intent = intent_match.intent

            if intent_match.intent == "device_control":
                device_result = self._device_control_service.handle_message(
                    message=message,
                    device_id=self._settings.default_esp32_device_id,
                )
                source = device_result.source
                return self._build_response(
                    reply=device_result.reply,
                    intent="device_control",
                    source=device_result.source,
                    background_tasks=background_tasks,
                    force_audio=force_audio,
                    suppress_audio=suppress_audio,
                )

            if intent_match.intent == "sensor_query":
                sensor_answer = self._sensor_manager.answer_sensor_query(
                    message=message,
                    device_id=self._settings.default_esp32_device_id,
                    freshness_seconds=self._settings.sensor_freshness_seconds,
                )
                source = sensor_answer.source
                return self._build_response(
                    reply=sensor_answer.reply,
                    intent="sensor_query",
                    source=sensor_answer.source,
                    background_tasks=background_tasks,
                    force_audio=force_audio,
                    suppress_audio=suppress_audio,
                )

            if intent_match.intent == "news_query":
                news_answer = self._news_service.answer_news_query(message)
                source = news_answer.source
                return self._build_response(
                    reply=news_answer.reply,
                    intent="news_query",
                    source=news_answer.source,
                    background_tasks=background_tasks,
                    force_audio=force_audio,
                    suppress_audio=suppress_audio,
                )

            if intent_match.intent == "navigation_query":
                navigation_answer = self._navigation_service.answer_navigation_query(message)
                source = navigation_answer.source
                return self._build_response(
                    reply=navigation_answer.reply,
                    intent="navigation_query",
                    source=navigation_answer.source,
                    background_tasks=background_tasks,
                    force_audio=force_audio,
                    suppress_audio=suppress_audio,
                )

            if intent_match.intent == "news_detail_query":
                news_detail_answer = self._news_service.answer_news_detail_query(message)
                source = news_detail_answer.source
                return self._build_response(
                    reply=news_detail_answer.reply,
                    intent="news_detail_query",
                    source=news_detail_answer.source,
                    background_tasks=background_tasks,
                    force_audio=force_audio,
                    suppress_audio=suppress_audio,
                )

            if intent_match.intent == "system_status":
                system_status_answer = self._system_status_service.get_status(
                    device_id=self._settings.default_esp32_device_id,
                )
                source = system_status_answer.source
                return self._build_response(
                    reply=system_status_answer.reply,
                    intent="system_status",
                    source=system_status_answer.source,
                    background_tasks=background_tasks,
                    force_audio=force_audio,
                    suppress_audio=suppress_audio,
                )

            if intent_match.intent == "weather_query":
                weather_answer = self._weather_service.answer_weather_query(message)
                source = weather_answer.source
                return self._build_response(
                    reply=weather_answer.reply,
                    intent="weather_query",
                    source=weather_answer.source,
                    background_tasks=background_tasks,
                    force_audio=force_audio,
                    suppress_audio=suppress_audio,
                )

            if intent_match.intent == "traffic_query":
                traffic_answer = self._traffic_service.answer_traffic_query(message)
                source = traffic_answer.source
                return self._build_response(
                    reply=traffic_answer.reply,
                    intent="traffic_query",
                    source=traffic_answer.source,
                    background_tasks=background_tasks,
                    force_audio=force_audio,
                    suppress_audio=suppress_audio,
                )

            placeholder_response = self._intent_router.get_placeholder_response(intent_match.intent)
            if placeholder_response is not None:
                source = "placeholder"
                return self._build_response(
                    reply=placeholder_response.reply,
                    intent=placeholder_response.intent,
                    source="placeholder",
                    background_tasks=background_tasks,
                    force_audio=force_audio,
                    suppress_audio=suppress_audio,
                )

            llm_response = self._llm_manager.generate_reply(message)
            intent = "general_chat"
            source = llm_response.source
            return self._build_response(
                reply=llm_response.reply,
                intent="general_chat",
                source=llm_response.source,
                background_tasks=background_tasks,
                force_audio=force_audio,
                suppress_audio=suppress_audio,
            )
        except Exception:
            status_text = "error"
            raise
        finally:
            log_timing(
                logger,
                self._settings,
                "chat.total",
                timer.elapsed_ms,
                intent=intent,
                source=source,
                status=status_text,
            )

    def build_fallback_response(
        self,
        reply: str,
        background_tasks: BackgroundTasks,
        force_audio: bool = False,
        suppress_audio: bool = False,
    ) -> ChatResponse:
        return self._build_response(
            reply=reply,
            intent="general_chat",
            source="fallback",
            background_tasks=background_tasks,
            force_audio=force_audio,
            suppress_audio=suppress_audio,
        )

    def _build_response(
        self,
        reply: str,
        intent: str,
        source: str,
        background_tasks: BackgroundTasks,
        force_audio: bool,
        suppress_audio: bool,
    ) -> ChatResponse:
        return ChatResponse(
            reply=reply,
            intent=intent,
            source=source,
            audio_url=self._schedule_audio_generation(
                background_tasks=background_tasks,
                reply=reply,
                force_audio=force_audio,
                suppress_audio=suppress_audio,
            ),
        )

    def _schedule_audio_generation(
        self,
        background_tasks: BackgroundTasks,
        reply: str,
        force_audio: bool,
        suppress_audio: bool,
    ) -> str | None:
        if suppress_audio:
            return None
        if not self._settings.tts_enabled:
            return None
        if not force_audio and not self._settings.demo_voice_mode:
            return None
        token, audio_url = self._tts_service.create_pending_audio_url()
        background_tasks.add_task(self._tts_service.synthesize, reply, token)
        return audio_url


_chat_service = ChatService(
    settings=get_settings(),
    intent_router=get_intent_router(),
    llm_manager=get_llm_manager(),
    device_control_service=get_device_control_service(),
    navigation_service=get_navigation_service(),
    news_service=get_news_service(),
    sensor_manager=get_sensor_manager(),
    system_status_service=get_system_status_service(),
    traffic_service=get_traffic_service(),
    tts_service=get_tts_service(),
    weather_service=get_weather_service(),
)


def get_chat_service() -> ChatService:
    return _chat_service
