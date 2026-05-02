from fastapi import APIRouter, Depends, HTTPException, status

from server.config import Settings, get_settings
from server.models.device import (
    DeviceCreateRequest,
    DeviceDetailResponse,
    DeviceListResponse,
    DeviceMetadataUpdateRequest,
    DeviceRegistryStatusResponse,
)
from server.services.device_registry import (
    DeviceRegistry,
    DeviceRegistryError,
    get_device_registry,
)
from server.services.esp32_manager import Esp32Manager, get_esp32_manager

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get(
    "",
    response_model=DeviceListResponse,
    status_code=status.HTTP_200_OK,
)
def list_devices(
    registry: DeviceRegistry = Depends(get_device_registry),
) -> DeviceListResponse:
    return DeviceListResponse(devices=registry.list_devices())


@router.get(
    "/",
    response_model=DeviceListResponse,
    include_in_schema=False,
    status_code=status.HTTP_200_OK,
)
def list_devices_with_slash(
    registry: DeviceRegistry = Depends(get_device_registry),
) -> DeviceListResponse:
    return list_devices(registry)


@router.post(
    "",
    response_model=DeviceDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_device(
    request: DeviceCreateRequest,
    settings: Settings = Depends(get_settings),
    registry: DeviceRegistry = Depends(get_device_registry),
    esp32_manager: Esp32Manager = Depends(get_esp32_manager),
) -> DeviceDetailResponse:
    esp32_status = None
    if request.device_type == "relay":
        esp32_device_id = request.esp32_device_id or settings.default_esp32_device_id
        esp32_status = esp32_manager.get_device_status(
            device_id=esp32_device_id,
            offline_timeout_seconds=settings.esp32_offline_timeout_seconds,
        )

    try:
        device = registry.create_device(request, esp32_status=esp32_status)
    except DeviceRegistryError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return DeviceDetailResponse(device=device)


@router.get(
    "/status",
    response_model=DeviceRegistryStatusResponse,
    status_code=status.HTTP_200_OK,
)
def get_registry_status(
    registry: DeviceRegistry = Depends(get_device_registry),
) -> DeviceRegistryStatusResponse:
    devices = registry.list_devices()
    return DeviceRegistryStatusResponse(
        devices=devices,
        total=len(devices),
        enabled=sum(1 for device in devices if device.enabled),
    )


@router.get(
    "/{device_id}",
    response_model=DeviceDetailResponse,
    status_code=status.HTTP_200_OK,
)
def get_device(
    device_id: str,
    registry: DeviceRegistry = Depends(get_device_registry),
) -> DeviceDetailResponse:
    device = registry.get_device(device_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="device not found",
        )
    return DeviceDetailResponse(device=device)


@router.patch(
    "/{device_id}",
    response_model=DeviceDetailResponse,
    status_code=status.HTTP_200_OK,
)
def update_device_metadata(
    device_id: str,
    request: DeviceMetadataUpdateRequest,
    registry: DeviceRegistry = Depends(get_device_registry),
) -> DeviceDetailResponse:
    device = registry.update_metadata(device_id, request)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="device not found",
        )
    return DeviceDetailResponse(device=device)
