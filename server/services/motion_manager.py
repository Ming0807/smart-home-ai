from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock

from server.models.esp32 import MotionEvent, MotionRequest


@dataclass(frozen=True)
class MotionAnswer:
    reply: str
    source: str


class MotionManager:
    """Store and summarize the latest PIR motion event."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._latest_event_by_device: dict[str, MotionEvent] = {}
        self._latest_detected_event_by_device: dict[str, MotionEvent] = {}
        self._latest_greeting_by_device: dict[str, str] = {}

    def record_event(self, request: MotionRequest) -> None:
        event = MotionEvent(
            device_id=request.device_id,
            motion=request.motion,
            timestamp=request.timestamp,
            received_at=self._now(),
        )
        with self._lock:
            self._latest_event_by_device[request.device_id] = event
            if request.motion:
                self._latest_detected_event_by_device[request.device_id] = event
                self._latest_greeting_by_device[
                    request.device_id
                ] = "ตรวจพบคนเดินผ่าน ยินดีต้อนรับครับ"

    def get_latest_event(self, device_id: str) -> MotionEvent | None:
        with self._lock:
            return self._latest_event_by_device.get(device_id)

    def get_latest_detected_event(self, device_id: str) -> MotionEvent | None:
        with self._lock:
            return self._latest_detected_event_by_device.get(device_id)

    def get_latest_greeting(self, device_id: str) -> str | None:
        with self._lock:
            return self._latest_greeting_by_device.get(device_id)

    def answer_motion_query(self, device_id: str) -> MotionAnswer:
        latest_detected = self.get_latest_detected_event(device_id)
        latest_event = self.get_latest_event(device_id)

        if latest_detected is None:
            return MotionAnswer(
                reply="ตอนนี้ยังไม่พบข้อมูลการเคลื่อนไหวล่าสุดจาก PIR ลองให้ ESP32 ส่ง event มาก่อนนะ",
                source="fallback",
            )

        detected_age_seconds = self._age_seconds(latest_detected.received_at)
        if latest_event is not None and not latest_event.motion:
            latest_state_age_seconds = self._age_seconds(latest_event.received_at)
            return MotionAnswer(
                reply=(
                    f"ล่าสุดตรวจพบการเคลื่อนไหวเมื่อ {detected_age_seconds} วินาทีก่อน "
                    f"ตอนนี้ยังไม่พบการเคลื่อนไหวใหม่ในช่วง {latest_state_age_seconds} วินาทีล่าสุด"
                ),
                source="motion_sensor",
            )

        return MotionAnswer(
            reply=(
                f"ล่าสุดตรวจพบการเคลื่อนไหวเมื่อ {detected_age_seconds} วินาทีก่อน "
                "ตอนนี้มีสัญญาณว่ามีคนเดินผ่านหรือกำลังเคลื่อนไหวอยู่"
            ),
            source="motion_sensor",
        )

    @staticmethod
    def _age_seconds(timestamp: datetime) -> int:
        age_seconds = (MotionManager._now() - timestamp).total_seconds()
        return max(0, int(round(age_seconds)))

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)


_motion_manager = MotionManager()


def get_motion_manager() -> MotionManager:
    return _motion_manager
