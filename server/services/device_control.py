from dataclasses import dataclass
from datetime import datetime, timezone

from server.config import Settings, get_settings
from server.models.device import DeviceDefinition
from server.models.esp32 import DeviceStatusResponse, RelayAction
from server.services.device_registry import DeviceRegistry, get_device_registry
from server.services.esp32_manager import Esp32Manager, get_esp32_manager
from server.services.voice_node_text_normalizer import normalize_voice_node_transcript


@dataclass(frozen=True)
class DeviceControlResult:
    reply: str
    source: str = "device_control"


ACTION_ON_HINTS = (
    "เปิด",
    "ติดไฟ",
    "ให้ไฟติด",
    "ช่วยเปิด",
    "สั่งเปิด",
    "turnon",
)
ACTION_OFF_HINTS = (
    "ปิด",
    "ดับ",
    "ดับไฟ",
    "ให้ไฟดับ",
    "ช่วยปิด",
    "สั่งปิด",
    "turnoff",
)
STATUS_QUERY_MARKERS = (
    "อยู่ไหม",
    "สถานะ",
    "เปิดอยู่",
    "ปิดอยู่",
    "ทำงานไหม",
    "ติดไหม",
    "ดับไหม",
    "พร้อมไหม",
    "สั่งได้ไหม",
    "ออนไลน์ไหม",
    "ออฟไลน์ไหม",
    "ล่าสุด",
    "เป็นยังไง",
)
ALL_RELAY_HINTS = (
    "ทั้งหมด",
    "ทุกดวง",
    "ทุกห้อง",
    "ทุกตัว",
    "ทุกช่อง",
    "all",
)


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
        normalized_message = normalize_voice_node_transcript(message)
        if self._is_all_relay_request(normalized_message):
            return self._handle_all_relay_message(
                message=normalized_message,
                device_id=device_id,
            )

        target_device = self._device_registry.find_controllable_device(normalized_message)
        if target_device is None:
            return DeviceControlResult(
                reply="ยังไม่พบอุปกรณ์ที่สั่งได้ ลองเพิ่มอุปกรณ์ใน Device Registry ก่อนนะ",
                source="fallback",
            )

        spoken_name = target_device.display_name
        target_device = self._mark_timed_out_pending_command(target_device)
        esp32_device_id = target_device.esp32_device_id or device_id
        device_status = (
            None
            if esp32_device_id == "virtual"
            else self._esp32_manager.get_device_status(
                device_id=esp32_device_id,
                offline_timeout_seconds=self._settings.esp32_offline_timeout_seconds,
            )
        )
        if self._is_status_query(normalized_message):
            return DeviceControlResult(
                reply=self._build_status_reply(
                    spoken_name=spoken_name,
                    state=target_device.state,
                    command_status=target_device.last_command_status,
                    esp32_device_id=esp32_device_id,
                    board_status=device_status,
                ),
            )

        action = self._detect_action(normalized_message)
        if action is None:
            board_text = ""
            if device_status is None or not device_status.online:
                board_text = f" ตอนนี้บอร์ด {esp32_device_id} ยังไม่ออนไลน์ด้วย"
            return DeviceControlResult(
                reply=(
                    f"เจอ{spoken_name}แล้ว แต่ยังไม่แน่ใจว่าจะเปิดหรือปิด"
                    f"{board_text} ลองพูดว่า เปิด{spoken_name} หรือ ปิด{spoken_name} ได้เลย"
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

        if device_status is None or not device_status.online:
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
            if self._is_pending_command_fresh(target_device):
                return DeviceControlResult(
                    reply=(
                        f"มีคำสั่งล่าสุดของ{spoken_name}ค้างอยู่แล้ว "
                        "กำลังรอ ESP32 ยืนยันผลก่อนนะ"
                    ),
                )
            self._device_registry.mark_command_timeout(
                device_id=target_device.id,
                command_id=target_device.last_command_id,
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

    def _handle_all_relay_message(
        self,
        message: str,
        device_id: str,
    ) -> DeviceControlResult:
        relay_devices = [
            device
            for device in self._device_registry.list_devices()
            if device.enabled and device.device_type == "relay" and device.relay_channel is not None
        ]
        if not relay_devices:
            return DeviceControlResult(
                reply="ยังไม่มี relay ที่เปิดใช้งานอยู่ในระบบ",
                source="fallback",
            )

        esp32_device_id = relay_devices[0].esp32_device_id or device_id
        device_status = self._esp32_manager.get_device_status(
            device_id=esp32_device_id,
            offline_timeout_seconds=self._settings.esp32_offline_timeout_seconds,
        )

        if self._is_status_query(message):
            states = ", ".join(
                self._format_device_state(
                    spoken_name=device.display_name,
                    state=device.state,
                    command_status=device.last_command_status,
                )
                for device in relay_devices
            )
            if not device_status.online:
                return DeviceControlResult(
                    reply=(
                        f"ตอนนี้บอร์ด {esp32_device_id} ออฟไลน์ "
                        f"เลยยืนยันสถานะจริงไม่ได้ ล่าสุดระบบจำว่า {states}"
                    ),
                )
            return DeviceControlResult(
                reply=f"บอร์ด {esp32_device_id} ออนไลน์ สถานะล่าสุดคือ {states}",
            )

        action = self._detect_action(message)
        if action is None:
            return DeviceControlResult(
                reply="ยังไม่แน่ใจว่าจะเปิดหรือปิดไฟทั้งหมด ลองพูดว่า เปิดไฟทั้งหมด หรือ ปิดไฟทั้งหมด",
                source="fallback",
            )
        if not device_status.online:
            return DeviceControlResult(
                reply=(
                    f"ตอนนี้บอร์ด {esp32_device_id} ยังไม่ออนไลน์ "
                    f"เลยยังสั่ง{self._action_verb(action)}ไฟทั้งหมดไม่ได้"
                ),
            )

        queued_count = 0
        for relay_device in relay_devices:
            command = self._esp32_manager.enqueue_relay_command(
                device_id=relay_device.esp32_device_id or esp32_device_id,
                action=action,
                channel=relay_device.relay_channel or 1,
                target_device_id=relay_device.id,
                gpio_pin=relay_device.gpio_pin,
            )
            self._device_registry.mark_command_queued(
                device_id=relay_device.id,
                command_id=command.command_id,
            )
            queued_count += 1

        return DeviceControlResult(
            reply=(
                f"ส่งคำสั่ง{self._action_verb(action)}ไฟทั้งหมด {queued_count} จุดให้แล้ว "
                "กำลังรอ ESP32 ยืนยันผล"
            ),
        )

    def _is_pending_command_fresh(self, target_device: DeviceDefinition) -> bool:
        updated_at = target_device.last_updated_at
        if updated_at is None:
            return True
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        elapsed_seconds = (datetime.now(timezone.utc) - updated_at).total_seconds()
        return elapsed_seconds <= self._settings.device_command_timeout_seconds

    def _mark_timed_out_pending_command(
        self,
        target_device: DeviceDefinition,
    ) -> DeviceDefinition:
        if target_device.state != "pending" or target_device.last_command_status not in {
            "queued",
            "sent",
        }:
            return target_device
        if self._is_pending_command_fresh(target_device):
            return target_device
        return (
            self._device_registry.mark_command_timeout(
                device_id=target_device.id,
                command_id=target_device.last_command_id,
            )
            or target_device
        )

    @staticmethod
    def _detect_action(message: str) -> RelayAction | None:
        normalized_message = _normalize(message)
        if any(_normalize(hint) in normalized_message for hint in ACTION_ON_HINTS):
            return "on"
        if any(_normalize(hint) in normalized_message for hint in ACTION_OFF_HINTS):
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
            _normalize(marker) in normalized_message
            for marker in STATUS_QUERY_MARKERS
        )

    @staticmethod
    def _is_all_relay_request(message: str) -> bool:
        normalized_message = _normalize(message)
        has_all_hint = any(_normalize(hint) in normalized_message for hint in ALL_RELAY_HINTS)
        has_relay_hint = any(
            hint in normalized_message
            for hint in ("ไฟ", "รีเลย์", "relay", "ช่อง")
        )
        return has_all_hint and has_relay_hint

    @classmethod
    def _build_status_reply(
        cls,
        spoken_name: str,
        state: str,
        command_status: str | None,
        esp32_device_id: str | None = None,
        board_status: DeviceStatusResponse | None = None,
    ) -> str:
        state_text = cls._format_device_state(
            spoken_name=spoken_name,
            state=state,
            command_status=command_status,
        )
        if board_status is not None and not board_status.online:
            age_text = (
                f" ล่าสุดเห็นเมื่อ {board_status.seconds_since_heartbeat} วินาทีก่อน"
                if board_status.seconds_since_heartbeat is not None
                else ""
            )
            return (
                f"ตอนนี้บอร์ด {esp32_device_id} ออฟไลน์{age_text} "
                f"เลยยืนยันสถานะจริงไม่ได้ ล่าสุดระบบจำว่า{state_text}"
            )

        if board_status is not None:
            pending_text = (
                f" และมีคำสั่งค้างในคิว {board_status.pending_command_count} รายการ"
                if board_status.pending_command_count
                else ""
            )
            return f"บอร์ด {esp32_device_id} ออนไลน์ ตอนนี้{state_text}{pending_text}"

        return state_text

    @staticmethod
    def _format_device_state(
        spoken_name: str,
        state: str,
        command_status: str | None,
    ) -> str:
        if command_status == "timeout":
            return f"คำสั่งล่าสุดของ{spoken_name}หมดเวลาแล้ว ตอนนี้ยังไม่รู้สถานะจริงจาก ESP32"
        if state == "on":
            return f"{spoken_name}เปิดอยู่"
        if state == "off":
            return f"{spoken_name}ปิดอยู่"
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
