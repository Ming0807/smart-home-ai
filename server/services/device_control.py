from dataclasses import dataclass

from server.config import Settings, get_settings
from server.models.esp32 import RelayAction
from server.services.device_registry import DeviceRegistry, get_device_registry
from server.services.esp32_manager import Esp32Manager, get_esp32_manager


@dataclass(frozen=True)
class DeviceControlResult:
    reply: str
    source: str = "device_control"


class DeviceControlService:
    """Create safe hardware commands from Thai device-control messages."""

    def __init__(
        self,
        settings: Settings,
        esp32_manager: Esp32Manager,
        device_registry: DeviceRegistry,
    ) -> None:
        self._settings = settings
        self._esp32_manager = esp32_manager
        self._device_registry = device_registry

    def handle_message(
        self,
        message: str,
        device_id: str,
    ) -> DeviceControlResult:
        target_device = self._device_registry.find_controllable_device(message)
        if target_device is None:
            return DeviceControlResult(
                reply="ยังไม่พบอุปกรณ์ที่สั่งได้ ลองเพิ่มอุปกรณ์ใน Device Registry ก่อนนะ",
                source="fallback",
            )

        spoken_name = self._detect_device_name(message) or target_device.display_name
        if self._is_status_query(message):
            return DeviceControlResult(
                reply=self._build_status_reply(
                    spoken_name=spoken_name,
                    state=target_device.state,
                    command_status=target_device.last_command_status,
                ),
            )

        action = self._detect_action(message)
        if action is None:
            return DeviceControlResult(
                reply=(
                    "ยังไม่แน่ใจว่าจะเปิดหรือปิดอุปกรณ์ "
                    "ลองพูดว่า เปิดไฟ หรือ ปิดไฟ ได้เลย"
                ),
                source="fallback",
            )

        if not target_device.enabled:
            return DeviceControlResult(
                reply=f"{spoken_name} ถูกปิดการใช้งานอยู่ เลยยังสั่งงานไม่ได้",
                source="fallback",
            )

        if target_device.relay_channel is None:
            return DeviceControlResult(
                reply=f"{spoken_name} ยังไม่ได้ตั้งค่า relay channel เลยยังสั่งงานไม่ได้",
                source="fallback",
            )

        esp32_device_id = target_device.esp32_device_id or device_id
        device_status = self._esp32_manager.get_device_status(
            device_id=esp32_device_id,
            offline_timeout_seconds=self._settings.esp32_offline_timeout_seconds,
        )
        if not device_status.online:
            return DeviceControlResult(
                reply=(
                    f"ตอนนี้บอร์ด {esp32_device_id} ยังไม่ออนไลน์ "
                    f"เลยยังสั่ง{self._action_verb(action)}{spoken_name}ไม่ได้"
                ),
            )

        if target_device.state == action:
            state_text = "เปิดอยู่แล้ว" if action == "on" else "ปิดอยู่แล้ว"
            return DeviceControlResult(reply=f"{spoken_name}{state_text}นะ")

        if target_device.state == "pending" and target_device.last_command_status in {
            "queued",
            "sent",
        }:
            return DeviceControlResult(
                reply=(
                    f"มีคำสั่งล่าสุดของ{spoken_name}ค้างอยู่แล้ว "
                    "กำลังรอ ESP32 ยืนยันผลก่อนนะ"
                ),
            )

        command = self._esp32_manager.enqueue_relay_command(
            device_id=esp32_device_id,
            action=action,
            channel=target_device.relay_channel,
            target_device_id=target_device.id,
            gpio_pin=target_device.gpio_pin,
        )
        self._device_registry.mark_command_queued(
            device_id=target_device.id,
            command_id=command.command_id,
        )

        return DeviceControlResult(
            reply=(
                f"ส่งคำสั่ง{self._action_verb(action)}{spoken_name}ให้แล้ว "
                "กำลังรอ ESP32 ยืนยันผล"
            ),
        )

    @staticmethod
    def _detect_action(message: str) -> RelayAction | None:
        normalized_message = _normalize(message)
        if "เปิด" in normalized_message:
            return "on"
        if "ปิด" in normalized_message:
            return "off"
        return None

    @staticmethod
    def _detect_device_name(message: str) -> str | None:
        normalized_message = _normalize(message)
        if "พัดลม" in normalized_message:
            return "พัดลม"
        if "ไฟ" in normalized_message or "หลอดไฟ" in normalized_message:
            return "ไฟ"
        if "ปลั๊ก" in normalized_message:
            return "ปลั๊ก"
        if "รีเลย์" in normalized_message or "relay" in normalized_message:
            return "รีเลย์"
        return None

    @staticmethod
    def _is_status_query(message: str) -> bool:
        normalized_message = _normalize(message)
        return any(
            marker in normalized_message
            for marker in (
                "อยู่ไหม",
                "สถานะ",
                "เปิดอยู่",
                "ปิดอยู่",
                "ทำงานไหม",
                "ติดไหม",
            )
        )

    @staticmethod
    def _build_status_reply(
        spoken_name: str,
        state: str,
        command_status: str | None,
    ) -> str:
        if state == "on":
            return f"{spoken_name}เปิดอยู่ตอนนี้"
        if state == "off":
            return f"{spoken_name}ปิดอยู่ตอนนี้"
        if state == "pending":
            if command_status == "sent":
                return f"{spoken_name}กำลังรอ ESP32 ยืนยันผลคำสั่งล่าสุด"
            return f"{spoken_name}มีคำสั่งค้างอยู่ในคิว"
        if state == "unavailable":
            return f"{spoken_name}ยังไม่พร้อมใช้งานตอนนี้"
        return f"ตอนนี้ยังไม่รู้สถานะล่าสุดของ{spoken_name} ต้องรอ ESP32 รายงานผลก่อน"

    @staticmethod
    def _action_verb(action: RelayAction) -> str:
        return "เปิด" if action == "on" else "ปิด"


def _normalize(text: str) -> str:
    return "".join(text.casefold().split())


_device_control_service = DeviceControlService(
    settings=get_settings(),
    esp32_manager=get_esp32_manager(),
    device_registry=get_device_registry(),
)


def get_device_control_service() -> DeviceControlService:
    return _device_control_service
