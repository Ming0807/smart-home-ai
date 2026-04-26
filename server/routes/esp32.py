from fastapi import APIRouter, Depends, Query, status

from server.config import Settings, get_settings
from server.models.esp32 import (
    CommandResponse,
    DeviceStatusResponse,
    HeartbeatRequest,
    MotionRequest,
    SensorRequest,
    StatusResponse,
)
from server.services.esp32_manager import Esp32Manager, get_esp32_manager
from server.services.motion_manager import MotionManager, get_motion_manager
from server.services.sensor_manager import SensorManager, get_sensor_manager

router = APIRouter(prefix="/esp32", tags=["esp32"])


@router.post(
    "/heartbeat",
    response_model=StatusResponse,
    status_code=status.HTTP_200_OK,
)
def heartbeat(
    request: HeartbeatRequest,
    esp32_manager: Esp32Manager = Depends(get_esp32_manager),
) -> StatusResponse:
    esp32_manager.record_heartbeat(request)
    return StatusResponse()


@router.post(
    "/sensor",
    response_model=StatusResponse,
    status_code=status.HTTP_200_OK,
)
def sensor(
    request: SensorRequest,
    sensor_manager: SensorManager = Depends(get_sensor_manager),
) -> StatusResponse:
    sensor_manager.record_reading(request)
    return StatusResponse()


@router.post(
    "/motion",
    response_model=StatusResponse,
    status_code=status.HTTP_200_OK,
)
def motion(
    request: MotionRequest,
    motion_manager: MotionManager = Depends(get_motion_manager),
) -> StatusResponse:
    motion_manager.record_event(request)
    return StatusResponse()


@router.get(
    "/commands",
    response_model=CommandResponse,
    status_code=status.HTTP_200_OK,
)
def commands(
    device_id: str | None = Query(default=None, min_length=1, max_length=64),
    settings: Settings = Depends(get_settings),
    esp32_manager: Esp32Manager = Depends(get_esp32_manager),
) -> CommandResponse:
    resolved_device_id = device_id or settings.default_esp32_device_id
    return CommandResponse(command=esp32_manager.get_next_command(resolved_device_id))


@router.get(
    "/status",
    response_model=DeviceStatusResponse,
    status_code=status.HTTP_200_OK,
)
def status_view(
    device_id: str | None = Query(default=None, min_length=1, max_length=64),
    settings: Settings = Depends(get_settings),
    esp32_manager: Esp32Manager = Depends(get_esp32_manager),
) -> DeviceStatusResponse:
    resolved_device_id = device_id or settings.default_esp32_device_id
    return esp32_manager.get_device_status(
        device_id=resolved_device_id,
        offline_timeout_seconds=settings.esp32_offline_timeout_seconds,
    )
