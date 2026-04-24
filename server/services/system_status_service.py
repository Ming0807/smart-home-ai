from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from server.config import Settings, get_settings
from server.models.esp32 import DeviceHeartbeat, SensorReading
from server.services.esp32_manager import Esp32Manager, get_esp32_manager
from server.services.sensor_manager import SensorManager, get_sensor_manager


@dataclass(frozen=True)
class SystemStatusAnswer:
    reply: str
    source: str = "system_status"


class SystemStatusService:
    """Summarize real ESP32 connectivity state from heartbeat and sensor data."""

    def __init__(
        self,
        settings: Settings,
        esp32_manager: Esp32Manager,
        sensor_manager: SensorManager,
    ) -> None:
        self._settings = settings
        self._esp32_manager = esp32_manager
        self._sensor_manager = sensor_manager

    def get_status(self, device_id: str) -> SystemStatusAnswer:
        heartbeat = self._esp32_manager.get_latest_heartbeat(device_id)
        reading = self._sensor_manager.get_latest_reading(device_id)

        if heartbeat is None:
            return SystemStatusAnswer(
                reply=(
                    "ตอนนี้ยังไม่พบ heartbeat จาก ESP32 เลย "
                    "ระบบ IoT อาจยังไม่เชื่อมต่อหรือบอร์ดยังไม่ออนไลน์"
                ),
            )

        heartbeat_age_seconds = self._age_seconds(heartbeat.last_seen_at)
        if heartbeat_age_seconds > self._settings.sensor_freshness_seconds:
            return SystemStatusAnswer(
                reply=(
                    f"ตอนนี้ยังไม่มั่นใจว่า ESP32 ออนไลน์อยู่ เพราะ heartbeat ล่าสุดมาเมื่อ "
                    f"{heartbeat_age_seconds} วินาทีก่อน "
                    "ระบบ IoT อาจหลุดการเชื่อมต่อ ลองตรวจสอบบอร์ดอีกครั้งได้"
                ),
            )

        sensor_status = self._describe_sensor_status(reading)
        return SystemStatusAnswer(
            reply=(
                f"ตอนนี้ ESP32 ออนไลน์อยู่ ได้รับ heartbeat ล่าสุดเมื่อ "
                f"{heartbeat_age_seconds} วินาทีก่อน {sensor_status}"
            ),
        )

    def _describe_sensor_status(self, reading: SensorReading | None) -> str:
        if reading is None:
            return "แต่ยังไม่มีข้อมูลเซนเซอร์ล่าสุดส่งเข้ามา"

        if not self._sensor_manager.is_fresh(
            reading,
            self._settings.sensor_freshness_seconds,
        ):
            sensor_age_seconds = self._age_seconds(reading.received_at)
            return (
                f"แต่ข้อมูลเซนเซอร์ล่าสุดค่อนข้างเก่าแล้ว ประมาณ {sensor_age_seconds} วินาทีก่อน"
            )

        return "และมีข้อมูลเซนเซอร์ล่าสุดพร้อมใช้งาน ระบบ IoT พร้อมใช้งาน"

    @staticmethod
    def _age_seconds(timestamp: datetime) -> int:
        age_seconds = (datetime.now(timezone.utc) - timestamp).total_seconds()
        return max(0, int(round(age_seconds)))


def get_system_status_service() -> SystemStatusService:
    return SystemStatusService(
        settings=get_settings(),
        esp32_manager=get_esp32_manager(),
        sensor_manager=get_sensor_manager(),
    )
