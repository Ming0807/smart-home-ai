from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


DeviceType = Literal["relay", "sensor", "motion", "virtual"]
DeviceCreateType = Literal["relay", "virtual"]
DeviceState = Literal["unknown", "on", "off", "pending", "unavailable"]
PinMode = Literal["input", "output", "i2s", "virtual"]
CommandLifecycleStatus = Literal["queued", "sent", "applied", "failed", "timeout"]


class DeviceDefinition(BaseModel):
    """Configured smart-home device known by the assistant."""

    id: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=120)
    device_type: DeviceType
    room: str | None = Field(default=None, max_length=120)
    esp32_device_id: str = Field(min_length=1, max_length=64)
    gpio_pin: int | None = Field(default=None, ge=0, le=48)
    pin_mode: PinMode = "virtual"
    relay_channel: int | None = Field(default=None, ge=1, le=16)
    active_high: bool | None = None
    aliases: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    state: DeviceState = "unknown"
    enabled: bool = True
    is_user_defined: bool = False
    last_command_id: str | None = None
    last_command_status: CommandLifecycleStatus | None = None
    last_updated_at: datetime | None = None


class DeviceListResponse(BaseModel):
    devices: list[DeviceDefinition]


class DeviceDetailResponse(BaseModel):
    device: DeviceDefinition


class DeviceCreateRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    device_type: DeviceCreateType = "virtual"
    room: str | None = Field(default=None, max_length=120)
    esp32_device_id: str | None = Field(default=None, min_length=1, max_length=64)
    gpio_pin: int | None = Field(default=None, ge=0, le=48)
    relay_channel: int | None = Field(default=None, ge=1, le=1)
    active_high: bool | None = None
    aliases: list[str] = Field(default_factory=list, max_length=20)
    enabled: bool = True

    @field_validator("display_name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("text field must not be empty")
        return stripped_value

    @field_validator("room", "esp32_device_id")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped_value = value.strip()
        return stripped_value or None

    @field_validator("aliases")
    @classmethod
    def normalize_create_aliases(cls, value: list[str]) -> list[str]:
        return _normalize_alias_list(value)


class DeviceMetadataUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    room: str | None = Field(default=None, max_length=120)
    aliases: list[str] | None = Field(default=None, max_length=20)
    enabled: bool | None = None

    @field_validator("display_name", "room")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped_value = value.strip()
        return stripped_value or None

    @field_validator("aliases")
    @classmethod
    def normalize_aliases(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _normalize_alias_list(value)


class DeviceRegistryStatusResponse(BaseModel):
    devices: list[DeviceDefinition]
    total: int
    enabled: int


def _normalize_alias_list(values: list[str]) -> list[str]:
    aliases: list[str] = []
    seen: set[str] = set()
    for alias in values:
        clean_alias = alias.strip()
        if not clean_alias:
            continue
        normalized_alias = "".join(clean_alias.casefold().split())
        if normalized_alias in seen:
            continue
        seen.add(normalized_alias)
        aliases.append(clean_alias[:80])
    return aliases
