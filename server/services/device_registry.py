from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from server.config import Settings, get_settings, resolve_project_path
from server.models.device import (
    CommandLifecycleStatus,
    DeviceCreateRequest,
    DeviceDefinition,
    DeviceMetadataUpdateRequest,
    DeviceState,
)
from server.models.esp32 import CommandResult, DeviceStatusResponse, RelayCommand

logger = logging.getLogger(__name__)


class DeviceRegistryError(ValueError):
    """Raised when a requested device registry change is unsafe or invalid."""


class DeviceRegistry:
    """Source of truth for configured home devices."""

    def __init__(self, settings: Settings) -> None:
        self._lock = Lock()
        self._registry_path = resolve_project_path(settings.device_registry_path)
        self._default_esp32_device_id = settings.default_esp32_device_id
        self._devices: dict[str, DeviceDefinition] = {
            device.id: device for device in self._build_default_devices(settings)
        }
        self._load_saved_config()

    def list_devices(self) -> list[DeviceDefinition]:
        with self._lock:
            return list(self._devices.values())

    def get_device(self, device_id: str) -> DeviceDefinition | None:
        with self._lock:
            return self._devices.get(device_id)

    def find_by_alias(self, text: str) -> DeviceDefinition | None:
        normalized_text = _normalize(text)
        if not normalized_text:
            return None

        with self._lock:
            for device in self._devices.values():
                names = (device.display_name, *device.aliases)
                if any(_normalize(name) in normalized_text for name in names):
                    return device
        return None

    def find_controllable_device(self, text: str) -> DeviceDefinition | None:
        normalized_text = _normalize(text)
        if not normalized_text:
            return self.get_device("relay_1")

        with self._lock:
            relay_devices = [
                device
                for device in self._devices.values()
                if device.enabled and device.device_type == "relay"
            ]
            for device in relay_devices:
                names = (device.display_name, *device.aliases)
                if any(_normalize(name) in normalized_text for name in names):
                    return device
        return None

    def update_metadata(
        self,
        device_id: str,
        request: DeviceMetadataUpdateRequest,
    ) -> DeviceDefinition | None:
        with self._lock:
            device = self._devices.get(device_id)
            if device is None:
                return None

            updates: dict[str, object] = {
                "last_updated_at": datetime.now(timezone.utc),
            }
            if request.display_name is not None:
                updates["display_name"] = request.display_name
            if request.room is not None:
                updates["room"] = request.room
            if request.aliases is not None:
                updates["aliases"] = request.aliases
            if request.enabled is not None:
                updates["enabled"] = request.enabled

            updated_device = device.model_copy(update=updates)
            self._devices[device_id] = updated_device
            self._save_config_locked()
            return updated_device

    def create_device(
        self,
        request: DeviceCreateRequest,
        esp32_status: DeviceStatusResponse | None = None,
    ) -> DeviceDefinition:
        if request.device_type == "virtual":
            return self.create_virtual_device(request)
        if request.device_type == "relay":
            return self.create_relay_device(request, esp32_status)
        raise DeviceRegistryError("ยังไม่รองรับประเภทอุปกรณ์นี้")

    def create_virtual_device(
        self,
        request: DeviceCreateRequest,
    ) -> DeviceDefinition:
        with self._lock:
            device_id = self._create_virtual_device_id_locked()
            aliases = request.aliases or [request.display_name]
            device = DeviceDefinition(
                id=device_id,
                display_name=request.display_name,
                device_type="virtual",
                room=request.room,
                esp32_device_id="virtual",
                gpio_pin=None,
                pin_mode="virtual",
                aliases=aliases,
                actions=[],
                enabled=request.enabled,
                is_user_defined=True,
                last_updated_at=datetime.now(timezone.utc),
            )
            self._devices[device_id] = device
            self._save_config_locked()
            return device

    def create_relay_device(
        self,
        request: DeviceCreateRequest,
        esp32_status: DeviceStatusResponse | None,
    ) -> DeviceDefinition:
        esp32_device_id = request.esp32_device_id or self._default_esp32_device_id
        relay_channel = request.relay_channel or 1
        active_high = True if request.active_high is None else request.active_high

        if request.gpio_pin is None:
            raise DeviceRegistryError("กรุณาระบุ GPIO pin สำหรับ relay")
        if esp32_status is None or esp32_status.device_id != esp32_device_id:
            raise DeviceRegistryError("ยังไม่มีสถานะ ESP32 สำหรับตรวจสอบ GPIO")
        if not esp32_status.online:
            raise DeviceRegistryError("ESP32 ยังไม่ออนไลน์ จึงยังเพิ่ม relay จริงไม่ได้")
        if esp32_status.capabilities is None:
            raise DeviceRegistryError("ยังไม่มีข้อมูล capabilities จาก ESP32 จึงยังตรวจสอบ GPIO ไม่ได้")
        if "relay" not in {item.casefold() for item in esp32_status.capabilities.capabilities}:
            raise DeviceRegistryError("ESP32 เครื่องนี้ยังไม่ได้รายงานว่ารองรับ relay")

        self._validate_gpio_for_relay(
            esp32_device_id=esp32_device_id,
            gpio_pin=request.gpio_pin,
            relay_channel=relay_channel,
            esp32_status=esp32_status,
        )

        with self._lock:
            self._validate_aliases_available_locked(
                aliases=[request.display_name, *request.aliases],
            )
            device_id = self._create_user_device_id_locked("relay")
            aliases = request.aliases or [request.display_name]
            device = DeviceDefinition(
                id=device_id,
                display_name=request.display_name,
                device_type="relay",
                room=request.room,
                esp32_device_id=esp32_device_id,
                gpio_pin=request.gpio_pin,
                pin_mode="output",
                relay_channel=relay_channel,
                active_high=active_high,
                aliases=aliases,
                actions=["on", "off"],
                enabled=request.enabled,
                is_user_defined=True,
                last_updated_at=datetime.now(timezone.utc),
            )
            self._devices[device_id] = device
            self._save_config_locked()
            return device

    def mark_command_queued(
        self,
        device_id: str,
        command_id: str | None,
    ) -> DeviceDefinition | None:
        return self._update_device(
            device_id=device_id,
            state="pending",
            command_id=command_id,
            command_status="queued",
        )

    def mark_command_sent(
        self,
        device_id: str | None,
        command_id: str | None,
    ) -> DeviceDefinition | None:
        if not device_id:
            return None
        return self._update_device(
            device_id=device_id,
            state="pending",
            command_id=command_id,
            command_status="sent",
        )

    def apply_command_result(
        self,
        command: RelayCommand,
        result: CommandResult,
    ) -> DeviceDefinition | None:
        target_device_id = command.target_device_id
        if not target_device_id:
            return None

        if result.status == "applied":
            next_state: DeviceState = result.state or "unknown"
            command_status: CommandLifecycleStatus = "applied"
        else:
            next_state = "unknown"
            command_status = "failed"

        return self._update_device(
            device_id=target_device_id,
            state=next_state,
            command_id=result.command_id,
            command_status=command_status,
        )

    def _update_device(
        self,
        device_id: str,
        state: DeviceState,
        command_id: str | None,
        command_status: CommandLifecycleStatus,
    ) -> DeviceDefinition | None:
        with self._lock:
            device = self._devices.get(device_id)
            if device is None:
                return None
            updated_device = device.model_copy(
                update={
                    "state": state,
                    "last_command_id": command_id,
                    "last_command_status": command_status,
                    "last_updated_at": datetime.now(timezone.utc),
                },
            )
            self._devices[device_id] = updated_device
            return updated_device

    def _load_saved_config(self) -> None:
        try:
            raw_data = json.loads(self._registry_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            self._save_initial_config()
            return
        except (OSError, json.JSONDecodeError):
            logger.warning("Failed to load device registry config from %s", self._registry_path)
            return

        devices_config = raw_data.get("devices") if isinstance(raw_data, dict) else None
        if not isinstance(devices_config, dict):
            return

        with self._lock:
            for device_id, config in devices_config.items():
                if not isinstance(config, dict):
                    continue
                device = self._devices.get(device_id)
                if device is None:
                    custom_device = self._coerce_saved_custom_device(device_id, config)
                    if custom_device is not None:
                        self._devices[device_id] = custom_device
                    continue
                updates = self._coerce_saved_metadata(config)
                if updates:
                    self._devices[device_id] = device.model_copy(update=updates)

    def _save_initial_config(self) -> None:
        with self._lock:
            self._save_config_locked()

    def _save_config_locked(self) -> None:
        payload = {
            "version": 1,
            "devices": {
                device_id: self._serialize_config(device)
                for device_id, device in self._devices.items()
            },
        }
        try:
            self._registry_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self._temporary_path(self._registry_path)
            temp_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temp_path.replace(self._registry_path)
        except OSError:
            logger.warning("Failed to save device registry config to %s", self._registry_path)

    @staticmethod
    def _serialize_config(device: DeviceDefinition) -> dict[str, object]:
        return {
            "display_name": device.display_name,
            "device_type": device.device_type,
            "room": device.room,
            "esp32_device_id": device.esp32_device_id,
            "gpio_pin": device.gpio_pin,
            "pin_mode": device.pin_mode,
            "relay_channel": device.relay_channel,
            "active_high": device.active_high,
            "aliases": device.aliases,
            "actions": device.actions,
            "enabled": device.enabled,
            "is_user_defined": device.is_user_defined,
        }

    @staticmethod
    def _coerce_saved_metadata(config: dict[str, object]) -> dict[str, object]:
        updates: dict[str, object] = {}
        display_name = config.get("display_name")
        if isinstance(display_name, str) and display_name.strip():
            updates["display_name"] = display_name.strip()[:120]

        room = config.get("room")
        if isinstance(room, str):
            updates["room"] = room.strip()[:120] or None

        aliases = config.get("aliases")
        if isinstance(aliases, list):
            clean_aliases = []
            seen: set[str] = set()
            for alias in aliases:
                if not isinstance(alias, str):
                    continue
                clean_alias = alias.strip()
                if not clean_alias:
                    continue
                normalized_alias = _normalize(clean_alias)
                if normalized_alias in seen:
                    continue
                seen.add(normalized_alias)
                clean_aliases.append(clean_alias[:80])
            updates["aliases"] = clean_aliases[:20]

        enabled = config.get("enabled")
        if isinstance(enabled, bool):
            updates["enabled"] = enabled
        return updates

    def _coerce_saved_custom_device(
        self,
        device_id: str,
        config: dict[str, object],
    ) -> DeviceDefinition | None:
        if not config.get("is_user_defined"):
            return None

        device_type = config.get("device_type")
        if device_type not in {"virtual", "relay"}:
            return None

        metadata = self._coerce_saved_metadata(config)
        display_name = metadata.get("display_name")
        if not isinstance(display_name, str) or not display_name:
            return None

        if device_type == "relay":
            esp32_device_id = _coerce_str(config.get("esp32_device_id")) or self._default_esp32_device_id
            gpio_pin = _coerce_gpio_pin(config.get("gpio_pin"))
            relay_channel = _coerce_relay_channel(config.get("relay_channel"))
            if gpio_pin is None or relay_channel is None:
                return None

            return DeviceDefinition(
                id=device_id[:64],
                display_name=display_name,
                device_type="relay",
                room=metadata.get("room") if isinstance(metadata.get("room"), str) else None,
                esp32_device_id=esp32_device_id,
                gpio_pin=gpio_pin,
                pin_mode="output",
                relay_channel=relay_channel,
                active_high=(
                    config.get("active_high")
                    if isinstance(config.get("active_high"), bool)
                    else True
                ),
                aliases=(
                    metadata.get("aliases")
                    if isinstance(metadata.get("aliases"), list)
                    else [display_name]
                ),
                actions=["on", "off"],
                enabled=(
                    metadata.get("enabled")
                    if isinstance(metadata.get("enabled"), bool)
                    else True
                ),
                is_user_defined=True,
            )

        return DeviceDefinition(
            id=device_id[:64],
            display_name=display_name,
            device_type="virtual",
            room=metadata.get("room") if isinstance(metadata.get("room"), str) else None,
            esp32_device_id="virtual",
            gpio_pin=None,
            pin_mode="virtual",
            aliases=(
                metadata.get("aliases")
                if isinstance(metadata.get("aliases"), list)
                else [display_name]
            ),
            actions=[],
            enabled=(
                metadata.get("enabled")
                if isinstance(metadata.get("enabled"), bool)
                else True
            ),
            is_user_defined=True,
        )

    def _validate_gpio_for_relay(
        self,
        esp32_device_id: str,
        gpio_pin: int,
        relay_channel: int,
        esp32_status: DeviceStatusResponse,
    ) -> None:
        if relay_channel != 1:
            raise DeviceRegistryError("ตอนนี้รองรับ relay channel 1 เท่านั้น")

        capabilities = esp32_status.capabilities
        if capabilities is None:
            raise DeviceRegistryError("ยังไม่มีข้อมูล capabilities จาก ESP32")

        reserved_pins = set(capabilities.reserved_pins)
        available_pins = set(capabilities.available_pins)
        relay_pins = set(capabilities.relay_pins)
        if available_pins and gpio_pin not in available_pins:
            raise DeviceRegistryError(f"GPIO {gpio_pin} ไม่อยู่ในรายการพินที่ ESP32 แจ้งว่าว่าง")
        if not available_pins and relay_pins and gpio_pin not in relay_pins:
            raise DeviceRegistryError(f"GPIO {gpio_pin} ไม่อยู่ในรายการ relay pins ที่ ESP32 รายงาน")
        if gpio_pin in reserved_pins:
            raise DeviceRegistryError(f"GPIO {gpio_pin} ถูกใช้งานหรือถูกจองไว้แล้ว")

        with self._lock:
            for device in self._devices.values():
                if device.esp32_device_id != esp32_device_id:
                    continue
                if device.gpio_pin == gpio_pin:
                    raise DeviceRegistryError(
                        f"GPIO {gpio_pin} ถูกใช้โดย {device.display_name} อยู่แล้ว"
                    )

    def _validate_aliases_available_locked(self, aliases: list[str]) -> None:
        normalized_aliases = {_normalize(alias) for alias in aliases if _normalize(alias)}
        if not normalized_aliases:
            return
        for device in self._devices.values():
            names = (device.display_name, *device.aliases)
            for name in names:
                if _normalize(name) in normalized_aliases:
                    raise DeviceRegistryError(
                        f"คำเรียก '{name}' ถูกใช้กับ {device.display_name} อยู่แล้ว"
                    )

    def _create_virtual_device_id_locked(self) -> str:
        index = 1
        while True:
            candidate = f"virtual_{index}"
            if candidate not in self._devices:
                return candidate
            index += 1

    def _create_user_device_id_locked(self, prefix: str) -> str:
        index = 1
        while True:
            candidate = f"{prefix}_user_{index}"
            if candidate not in self._devices:
                return candidate
            index += 1

    @staticmethod
    def _temporary_path(path: Path) -> Path:
        return path.with_name(f"{path.name}.tmp")

    @staticmethod
    def _build_default_devices(settings: Settings) -> list[DeviceDefinition]:
        esp32_device_id = settings.default_esp32_device_id
        return [
            DeviceDefinition(
                id="relay_1",
                display_name="รีเลย์ช่อง 1",
                device_type="relay",
                room="demo",
                esp32_device_id=esp32_device_id,
                gpio_pin=settings.default_relay_gpio_pin,
                pin_mode="output",
                relay_channel=1,
                active_high=settings.default_relay_active_high,
                aliases=[
                    "รีเลย์",
                    "relay",
                    "ไฟ",
                    "หลอดไฟ",
                    "พัดลม",
                    "ปลั๊ก",
                ],
                actions=["on", "off"],
            ),
            DeviceDefinition(
                id="dht22_1",
                display_name="DHT22",
                device_type="sensor",
                room="demo",
                esp32_device_id=esp32_device_id,
                gpio_pin=settings.default_dht22_gpio_pin,
                pin_mode="input",
                aliases=[
                    "อุณหภูมิ",
                    "ความชื้น",
                    "เซนเซอร์",
                    "dht22",
                ],
            ),
            DeviceDefinition(
                id="pir_1",
                display_name="PIR Motion",
                device_type="motion",
                room="demo",
                esp32_device_id=esp32_device_id,
                gpio_pin=settings.default_pir_gpio_pin,
                pin_mode="input",
                aliases=[
                    "pir",
                    "motion",
                    "การเคลื่อนไหว",
                    "คนเดินผ่าน",
                ],
            ),
        ]


def _normalize(text: str) -> str:
    return "".join(text.casefold().split())


def _coerce_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped_value = value.strip()
    return stripped_value[:64] or None


def _coerce_gpio_pin(value: object) -> int | None:
    if not isinstance(value, int) or isinstance(value, bool):
        return None
    if 0 <= value <= 48:
        return value
    return None


def _coerce_relay_channel(value: object) -> int | None:
    if not isinstance(value, int) or isinstance(value, bool):
        return None
    if value == 1:
        return value
    return None


_device_registry = DeviceRegistry(get_settings())


def get_device_registry() -> DeviceRegistry:
    return _device_registry
