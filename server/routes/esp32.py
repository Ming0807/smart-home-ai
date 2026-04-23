from fastapi import APIRouter, Depends, Query, status

from server.models.esp32 import (
    CommandResponse,
    HeartbeatRequest,
    SensorRequest,
    StatusResponse,
)
from server.services.esp32_manager import Esp32Manager, get_esp32_manager
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


@router.get(
    "/commands",
    response_model=CommandResponse,
    status_code=status.HTTP_200_OK,
)
def commands(
    device_id: str = Query(default="esp32-01", min_length=1, max_length=64),
    esp32_manager: Esp32Manager = Depends(get_esp32_manager),
) -> CommandResponse:
    return CommandResponse(command=esp32_manager.get_next_command(device_id))
