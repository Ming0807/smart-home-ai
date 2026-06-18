from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock

from server.models.esp32 import MotionEvent, MotionRequest
from server.services.sqlite_log_store import SQLiteLogStore, get_sqlite_log_store


@dataclass(frozen=True)
class MotionAnswer:
    reply: str
    source: str


@dataclass(frozen=True)
class MotionInsight:
    occupancy_status: str
    recommendation: str
    events_last_hour: int
    recent_events: list[MotionEvent]


class MotionManager:
    """Store and summarize the latest PIR motion event."""

    def __init__(self, log_store: SQLiteLogStore | None = None) -> None:
        self._lock = Lock()
        self._latest_event_by_device: dict[str, MotionEvent] = {}
        self._latest_detected_event_by_device: dict[str, MotionEvent] = {}
        self._latest_greeting_by_device: dict[str, str] = {}
        self._log_store = log_store or get_sqlite_log_store()

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
        self._log_store.record_motion_event(event)

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

        insight = self.build_insight(device_id)
        detected_age_seconds = self._age_seconds(latest_detected.received_at)
        if latest_event is not None and not latest_event.motion:
            latest_state_age_seconds = self._age_seconds(latest_event.received_at)
            return MotionAnswer(
                reply=(
                    f"ล่าสุดตรวจพบการเคลื่อนไหวเมื่อ {detected_age_seconds} วินาทีก่อน "
                    f"ตอนนี้ยังไม่พบการเคลื่อนไหวใหม่ในช่วง {latest_state_age_seconds} วินาทีล่าสุด "
                    f"สรุป: {insight.occupancy_status} คำแนะนำ: {insight.recommendation}"
                ),
                source="motion_sensor",
            )

        return MotionAnswer(
            reply=(
                f"ล่าสุดตรวจพบการเคลื่อนไหวเมื่อ {detected_age_seconds} วินาทีก่อน "
                f"สรุป: {insight.occupancy_status} คำแนะนำ: {insight.recommendation}"
            ),
            source="motion_sensor",
        )

    def build_insight(self, device_id: str) -> MotionInsight:
        latest_event = self.get_latest_event(device_id)
        latest_detected = self.get_latest_detected_event(device_id)
        recent_events = self._log_store.get_recent_motion_events(device_id, limit=6)
        if not recent_events and latest_event is not None:
            recent_events = [latest_event]
        events_last_hour = self._log_store.count_motion_events(device_id, hours=1)

        if latest_event is None:
            return MotionInsight(
                occupancy_status="ยังไม่มีข้อมูล PIR",
                recommendation="รอ ESP32 ส่ง motion event เพื่อเริ่มเก็บ log",
                events_last_hour=events_last_hour,
                recent_events=recent_events,
            )

        latest_state_age_seconds = self._age_seconds(latest_event.received_at)
        latest_detected_age_seconds = (
            self._age_seconds(latest_detected.received_at)
            if latest_detected is not None
            else None
        )

        if latest_event.motion and latest_state_age_seconds <= 120:
            return MotionInsight(
                occupancy_status="มีคนอยู่หรือกำลังเคลื่อนไหว",
                recommendation="เหมาะกับการเปิดไฟ/เปิดไมค์ต่อ และบันทึกเป็น activity ล่าสุด",
                events_last_hour=events_last_hour,
                recent_events=recent_events,
            )

        if latest_detected_age_seconds is not None and latest_detected_age_seconds <= 600:
            minutes = max(1, round(latest_detected_age_seconds / 60))
            return MotionInsight(
                occupancy_status=f"เพิ่งมีคนผ่านเมื่อประมาณ {minutes} นาทีที่แล้ว",
                recommendation="ยังไม่ควรปิดไฟอัตโนมัติทันที แต่ใช้เป็นข้อมูลช่วยตัดสินใจได้",
                events_last_hour=events_last_hour,
                recent_events=recent_events,
            )

        if latest_detected_age_seconds is not None:
            minutes = max(1, round(latest_detected_age_seconds / 60))
            return MotionInsight(
                occupancy_status=f"ไม่พบการเคลื่อนไหวมาประมาณ {minutes} นาที",
                recommendation="แนะนำแจ้งเตือนหรือเสนอให้ปิดไฟเพื่อประหยัดพลังงาน",
                events_last_hour=events_last_hour,
                recent_events=recent_events,
            )

        return MotionInsight(
            occupancy_status="ยังไม่พบ motion จริง",
            recommendation="ใช้เป็นโหมดเฝ้าระวังได้เมื่อ PIR ส่ง event แรกเข้ามา",
            events_last_hour=events_last_hour,
            recent_events=recent_events,
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
