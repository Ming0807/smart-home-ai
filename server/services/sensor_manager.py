from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock

from server.config import get_settings
from server.models.esp32 import SensorReading, SensorRequest


@dataclass(frozen=True)
class SensorAnswer:
    reply: str
    source: str


class SensorManager:
    """Store and explain the latest ESP32 DHT22 reading."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._latest_readings: dict[str, SensorReading] = {}

    def record_reading(self, request: SensorRequest) -> None:
        with self._lock:
            self._latest_readings[request.device_id] = SensorReading(
                device_id=request.device_id,
                temperature=request.temperature,
                humidity=request.humidity,
                timestamp=request.timestamp,
                received_at=self._now(),
            )

    def get_latest_reading(self, device_id: str) -> SensorReading | None:
        with self._lock:
            return self._latest_readings.get(device_id)

    def answer_sensor_query(
        self,
        message: str,
        device_id: str,
        freshness_seconds: int,
    ) -> SensorAnswer:
        reading = self.get_latest_reading(device_id)
        if reading is None:
            return SensorAnswer(
                reply="ตอนนี้ยังไม่มีข้อมูลจากเซนเซอร์ DHT22 ล่าสุด ลองให้ ESP32 ส่งค่ามาก่อนนะ",
                source="fallback",
            )
        if not self.is_fresh(reading, freshness_seconds):
            return SensorAnswer(
                reply="ข้อมูลเซนเซอร์ล่าสุดเก่าไปนิดนึง รอ ESP32 ส่งค่าใหม่แล้วถามอีกครั้งได้ไหม",
                source="fallback",
            )

        return SensorAnswer(
            reply=self._build_reply(message, reading),
            source="sensor",
        )

    def is_fresh(
        self,
        reading: SensorReading,
        freshness_seconds: int | None = None,
    ) -> bool:
        max_age_seconds = freshness_seconds
        if max_age_seconds is None:
            max_age_seconds = get_settings().sensor_freshness_seconds
        age_seconds = (self._now() - reading.received_at).total_seconds()
        return age_seconds <= max_age_seconds

    @staticmethod
    def _build_reply(message: str, reading: SensorReading) -> str:
        temperature = round(reading.temperature)
        humidity = round(reading.humidity)
        normalized_message = _normalize(message)

        if "ความชื้น" in normalized_message:
            return f"ตอนนี้ความชื้นประมาณ {humidity}% {SensorManager._humidity_summary(humidity)}"
        if "กี่องศา" in normalized_message or "อุณหภูมิ" in normalized_message:
            return (
                f"ตอนนี้ประมาณ {temperature} องศา "
                f"{SensorManager._temperature_summary(temperature)} "
                f"ความชื้นราว {humidity}%"
            )
        return (
            f"ตอนนี้ประมาณ {temperature} องศา "
            f"{SensorManager._temperature_summary(temperature)} "
            f"ความชื้นราว {humidity}%"
        )

    @staticmethod
    def _temperature_summary(temperature: int) -> str:
        if temperature >= 32:
            return "ร้อนมากเลยนะ"
        if temperature >= 30:
            return "ค่อนข้างร้อนนะ"
        if temperature >= 27:
            return "อุ่นนิดหน่อย"
        if temperature >= 24:
            return "กำลังสบาย"
        return "ค่อนข้างเย็น"

    @staticmethod
    def _humidity_summary(humidity: int) -> str:
        if humidity >= 75:
            return "ชื้นมากพอสมควร"
        if humidity >= 65:
            return "ค่อนข้างชื้นนะ"
        if humidity >= 45:
            return "อยู่ในระดับปกติ"
        return "ค่อนข้างแห้ง"

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)


def _normalize(text: str) -> str:
    return "".join(text.casefold().split())


_sensor_manager = SensorManager()


def get_sensor_manager() -> SensorManager:
    return _sensor_manager
