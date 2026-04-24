from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from server.config import Settings, get_settings, resolve_project_path
from server.models.dashboard import (
    AppSnapshot,
    DashboardStatusResponse,
    DeviceSnapshot,
    SensorSnapshot,
    VoiceSnapshot,
)
from server.services.esp32_manager import Esp32Manager, get_esp32_manager
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
) -> DashboardStatusResponse:
    device_id = settings.default_esp32_device_id
    reading = sensor_manager.get_latest_reading(device_id)
    heartbeat = esp32_manager.get_latest_heartbeat(device_id)
    latest_command = esp32_manager.get_latest_command(device_id)

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
        online=heartbeat is not None,
        last_seen_at=heartbeat.last_seen_at if heartbeat is not None else None,
        pending_command_count=esp32_manager.get_pending_command_count(device_id),
        latest_command=latest_command,
    )
    voice_snapshot = VoiceSnapshot(
        tts_enabled=settings.tts_enabled,
        demo_voice_mode=settings.demo_voice_mode,
        provider=settings.tts_provider,
        default_voice=settings.tts_default_voice,
        output_file=settings.tts_output_file,
    )
    return DashboardStatusResponse(
        sensor=sensor_snapshot,
        device=device_snapshot,
        voice=voice_snapshot,
        app=AppSnapshot(
            demo_mode=settings.demo_mode,
            debug_logs=settings.debug_logs,
            max_chat_history_items=settings.max_chat_history_items,
        ),
    )
