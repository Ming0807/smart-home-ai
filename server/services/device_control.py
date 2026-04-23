from dataclasses import dataclass

from server.models.esp32 import RelayAction
from server.services.esp32_manager import Esp32Manager, get_esp32_manager


@dataclass(frozen=True)
class DeviceControlResult:
    reply: str
    source: str = "device_control"


class DeviceControlService:
    """Create hardware commands from simple Thai device-control messages."""

    def __init__(self, esp32_manager: Esp32Manager) -> None:
        self._esp32_manager = esp32_manager

    def handle_message(
        self,
        message: str,
        device_id: str,
    ) -> DeviceControlResult:
        action = self._detect_action(message)
        device_name = self._detect_device_name(message)
        if action is None:
            return DeviceControlResult(
                reply="ยังไม่แน่ใจว่าจะเปิดหรือปิดอุปกรณ์ ลองพิมพ์ว่า เปิดไฟ หรือ ปิดไฟ ได้ไหม",
                source="fallback",
            )

        self._esp32_manager.enqueue_relay_command(
            device_id=device_id,
            action=action,
            channel=1,
        )
        verb = "เปิด" if action == "on" else "ปิด"
        return DeviceControlResult(reply=f"{verb}{device_name}ให้แล้วนะ")

    @staticmethod
    def _detect_action(message: str) -> RelayAction | None:
        normalized_message = _normalize(message)
        if "เปิด" in normalized_message:
            return "on"
        if "ปิด" in normalized_message:
            return "off"
        return None

    @staticmethod
    def _detect_device_name(message: str) -> str:
        normalized_message = _normalize(message)
        if "พัดลม" in normalized_message:
            return "พัดลม"
        if "ไฟ" in normalized_message:
            return "ไฟ"
        return "อุปกรณ์"


def _normalize(text: str) -> str:
    return "".join(text.casefold().split())


_device_control_service = DeviceControlService(get_esp32_manager())


def get_device_control_service() -> DeviceControlService:
    return _device_control_service
