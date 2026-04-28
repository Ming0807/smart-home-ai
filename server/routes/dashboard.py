from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from server.config import Settings, get_settings, resolve_project_path
from server.models.dashboard import (
    AppSnapshot,
    DashboardStatusResponse,
    DeviceSnapshot,
    LLMSnapshot,
    MotionSnapshot,
    SensorSnapshot,
    VoiceSnapshot,
)
from server.services.esp32_manager import Esp32Manager, get_esp32_manager
from server.services.llm_manager import LLMManager, get_llm_manager
from server.services.motion_manager import MotionManager, get_motion_manager
from server.services.sensor_manager import SensorManager, get_sensor_manager

router = APIRouter(tags=["dashboard"])


@router.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(resolve_project_path("webui/index.html"))


@router.get(
    "/dashboard/status",
    response_model=DashboardStatusResponse,
)
def dashboard_status(
    settings: Settings = Depends(get_settings),
    sensor_manager: SensorManager = Depends(get_sensor_manager),
    esp32_manager: Esp32Manager = Depends(get_esp32_manager),
    motion_manager: MotionManager = Depends(get_motion_manager),
    llm_manager: LLMManager = Depends(get_llm_manager),
) -> DashboardStatusResponse:
    device_id = settings.default_esp32_device_id
    reading = sensor_manager.get_latest_reading(device_id)
    device_status = esp32_manager.get_device_status(
        device_id=device_id,
        offline_timeout_seconds=settings.esp32_offline_timeout_seconds,
    )
    latest_command = esp32_manager.get_latest_command(device_id)
    latest_motion_event = motion_manager.get_latest_event(device_id)
    latest_detected_motion = motion_manager.get_latest_detected_event(device_id)
    llm_health = llm_manager.get_health_status()

    sensor_snapshot = SensorSnapshot(
        device_id=device_id,
        temperature=reading.temperature if reading is not None else None,
        humidity=reading.humidity if reading is not None else None,
        timestamp=reading.timestamp if reading is not None else None,
        received_at=reading.received_at if reading is not None else None,
        is_fresh=(
            sensor_manager.is_fresh(reading, settings.sensor_freshness_seconds)
            if reading is not None
            else False
        ),
    )
    device_snapshot = DeviceSnapshot(
        device_id=device_id,
        online=device_status.online,
        last_seen_at=device_status.last_seen_at,
        seconds_since_heartbeat=device_status.seconds_since_heartbeat,
        pending_command_count=device_status.pending_command_count,
        latest_command=device_status.latest_command or latest_command,
    )
    motion_snapshot = MotionSnapshot(
        device_id=device_id,
        motion_detected=(
            latest_motion_event.motion if latest_motion_event is not None else False
        ),
        last_motion_at=(
            latest_detected_motion.received_at
            if latest_detected_motion is not None
            else None
        ),
        last_event_at=(
            latest_motion_event.received_at if latest_motion_event is not None else None
        ),
        greeting_message=motion_manager.get_latest_greeting(device_id),
    )
    voice_snapshot = VoiceSnapshot(
        tts_enabled=settings.tts_enabled,
        demo_voice_mode=settings.demo_voice_mode,
        provider=settings.tts_provider,
        default_voice=settings.tts_default_voice,
        output_file=settings.tts_output_file,
    )
    llm_snapshot = LLMSnapshot(
        status="ok" if llm_health.available else "degraded",
        available=llm_health.available,
        model_present=llm_health.model_present,
        warmed_up=llm_health.warmed_up,
        model=settings.ollama_model,
        source=llm_health.source,
        checked_at=llm_health.checked_at,
        last_error=llm_health.last_error,
        latency_ms=llm_health.last_latency_ms,
        keep_awake_enabled=settings.demo_mode and settings.llm_keep_awake_in_demo,
        keep_awake_paused=llm_manager.is_keep_awake_paused,
    )
    return DashboardStatusResponse(
        sensor=sensor_snapshot,
        device=device_snapshot,
        motion=motion_snapshot,
        voice=voice_snapshot,
        llm=llm_snapshot,
        app=AppSnapshot(
            demo_mode=settings.demo_mode,
            debug_logs=settings.debug_logs,
            max_chat_history_items=settings.max_chat_history_items,
        ),
    )
