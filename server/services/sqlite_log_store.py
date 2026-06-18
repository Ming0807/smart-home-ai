from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
import sqlite3
from threading import Lock
from typing import Any

from server.config import get_settings, resolve_project_path
from server.models.activity import ActivityLogItem
from server.models.esp32 import CommandResult, MotionEvent, RelayCommand, SensorReading

logger = logging.getLogger(__name__)


class SQLiteLogStore:
    """Small local persistence layer for demo logs.

    The store is intentionally non-critical: callers should never fail a device
    request just because local logging is unavailable.
    """

    def __init__(self, db_path: Path, enabled: bool = True) -> None:
        self._db_path = db_path
        self._enabled = enabled
        self._lock = Lock()
        self._initialized = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def db_path(self) -> Path:
        return self._db_path

    def initialize(self) -> None:
        if not self._enabled:
            return
        with self._lock:
            if self._initialized:
                return
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as conn:
                conn.executescript(
                    """
                    PRAGMA journal_mode=WAL;
                    CREATE TABLE IF NOT EXISTS motion_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_id TEXT NOT NULL,
                        motion INTEGER NOT NULL,
                        sensor_timestamp TEXT NOT NULL,
                        received_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_motion_events_device_received
                        ON motion_events(device_id, received_at DESC);

                    CREATE TABLE IF NOT EXISTS sensor_readings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_id TEXT NOT NULL,
                        temperature REAL NOT NULL,
                        humidity REAL NOT NULL,
                        sensor_timestamp TEXT NOT NULL,
                        received_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_sensor_readings_device_received
                        ON sensor_readings(device_id, received_at DESC);

                    CREATE TABLE IF NOT EXISTS relay_commands (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        command_id TEXT,
                        device_id TEXT NOT NULL,
                        target_device_id TEXT,
                        channel INTEGER,
                        gpio_pin INTEGER,
                        action TEXT NOT NULL,
                        queued_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_relay_commands_device_queued
                        ON relay_commands(device_id, queued_at DESC);

                    CREATE TABLE IF NOT EXISTS command_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        command_id TEXT NOT NULL,
                        device_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        state TEXT,
                        error TEXT,
                        sensor_timestamp TEXT NOT NULL,
                        received_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_command_results_device_received
                        ON command_results(device_id, received_at DESC);

                    CREATE TABLE IF NOT EXISTS voice_node_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        state TEXT,
                        ok INTEGER,
                        payload_json TEXT,
                        created_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_voice_node_events_device_created
                        ON voice_node_events(device_id, created_at DESC);

                    CREATE TABLE IF NOT EXISTS activity_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type TEXT NOT NULL,
                        device_id TEXT,
                        message TEXT NOT NULL,
                        payload_json TEXT,
                        created_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_activity_logs_created
                        ON activity_logs(created_at DESC);
                    """
                )
            self._initialized = True

    def record_motion_event(self, event: MotionEvent) -> None:
        if not self._enabled:
            return
        self._safe_write(
            "motion event",
            lambda conn: (
                conn.execute(
                    """
                    INSERT INTO motion_events
                        (device_id, motion, sensor_timestamp, received_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        event.device_id,
                        1 if event.motion else 0,
                        _to_iso(event.timestamp),
                        _to_iso(event.received_at),
                    ),
                ),
                conn.execute(
                    """
                    INSERT INTO activity_logs
                        (event_type, device_id, message, payload_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        "motion_detected" if event.motion else "motion_clear",
                        event.device_id,
                        "PIR detected motion" if event.motion else "PIR reports no motion",
                        json.dumps({"motion": event.motion}, ensure_ascii=False),
                        _to_iso(event.received_at),
                    ),
                ),
            ),
        )

    def record_sensor_reading(self, reading: SensorReading) -> None:
        if not self._enabled:
            return
        self._safe_write(
            "sensor reading",
            lambda conn: (
                conn.execute(
                    """
                    INSERT INTO sensor_readings
                        (device_id, temperature, humidity, sensor_timestamp, received_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        reading.device_id,
                        reading.temperature,
                        reading.humidity,
                        _to_iso(reading.timestamp),
                        _to_iso(reading.received_at),
                    ),
                ),
                conn.execute(
                    """
                    INSERT INTO activity_logs
                        (event_type, device_id, message, payload_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        "sensor_reading",
                        reading.device_id,
                        f"DHT22 {reading.temperature:.1f}C / {reading.humidity:.1f}%",
                        json.dumps(
                            {
                                "temperature": reading.temperature,
                                "humidity": reading.humidity,
                            },
                            ensure_ascii=False,
                        ),
                        _to_iso(reading.received_at),
                    ),
                ),
            ),
        )

    def record_relay_command(
        self,
        device_id: str,
        command: RelayCommand,
        queued_at: datetime,
    ) -> None:
        if not self._enabled:
            return
        self._safe_write(
            "relay command",
            lambda conn: (
                conn.execute(
                    """
                    INSERT INTO relay_commands
                        (command_id, device_id, target_device_id, channel, gpio_pin, action, queued_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        command.command_id,
                        device_id,
                        command.target_device_id,
                        command.channel,
                        command.gpio_pin,
                        command.action,
                        _to_iso(queued_at),
                    ),
                ),
                conn.execute(
                    """
                    INSERT INTO activity_logs
                        (event_type, device_id, message, payload_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        "relay_command",
                        device_id,
                        f"Relay channel {command.channel} -> {command.action}",
                        json.dumps(command.model_dump(mode="json"), ensure_ascii=False),
                        _to_iso(queued_at),
                    ),
                ),
            ),
        )

    def record_command_result(self, result: CommandResult) -> None:
        if not self._enabled:
            return
        self._safe_write(
            "command result",
            lambda conn: (
                conn.execute(
                    """
                    INSERT INTO command_results
                        (command_id, device_id, status, state, error, sensor_timestamp, received_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.command_id,
                        result.device_id,
                        result.status,
                        result.state,
                        result.error,
                        _to_iso(result.timestamp),
                        _to_iso(result.received_at),
                    ),
                ),
                conn.execute(
                    """
                    INSERT INTO activity_logs
                        (event_type, device_id, message, payload_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        "command_result",
                        result.device_id,
                        f"Command {result.command_id} {result.status}",
                        json.dumps(result.model_dump(mode="json"), ensure_ascii=False),
                        _to_iso(result.received_at),
                    ),
                ),
            ),
        )

    def record_voice_node_heartbeat(
        self,
        *,
        device_id: str,
        state: str,
        firmware_version: str | None,
        ip_address: str | None,
        seen_at: datetime,
        state_changed: bool,
    ) -> None:
        if not self._enabled:
            return
        payload = {
            "state": state,
            "firmware_version": firmware_version,
            "ip_address": ip_address,
        }

        def operation(conn: sqlite3.Connection) -> None:
            conn.execute(
                """
                INSERT INTO voice_node_events
                    (device_id, event_type, state, ok, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    device_id,
                    "voice_node_heartbeat",
                    state,
                    1,
                    json.dumps(payload, ensure_ascii=False),
                    _to_iso(seen_at),
                ),
            )
            if state_changed:
                conn.execute(
                    """
                    INSERT INTO activity_logs
                        (event_type, device_id, message, payload_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        "voice_node_state",
                        device_id,
                        f"Voice Node -> {state}",
                        json.dumps(payload, ensure_ascii=False),
                        _to_iso(seen_at),
                    ),
                )

        self._safe_write("voice node heartbeat", operation)

    def record_voice_node_command(
        self,
        *,
        device_id: str,
        command_id: str,
        command_type: str,
        queued_at: datetime,
        audio_url: str | None = None,
        expected_text: str | None = None,
        pending_command_count: int | None = None,
    ) -> None:
        if not self._enabled:
            return
        payload = {
            "command_id": command_id,
            "type": command_type,
            "audio_url": audio_url,
            "expected_text": expected_text,
            "pending_command_count": pending_command_count,
        }
        self._safe_write(
            "voice node command",
            lambda conn: conn.execute(
                """
                INSERT INTO voice_node_events
                    (device_id, event_type, state, ok, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    device_id,
                    "voice_node_command",
                    command_type,
                    None,
                    json.dumps(payload, ensure_ascii=False),
                    _to_iso(queued_at),
                ),
            ),
        )

    def record_voice_node_audio_result(
        self,
        *,
        device_id: str,
        received_at: datetime,
        stt_ok: bool,
        stt_error: str | None,
        stt_raw_text: str | None,
        expected_text: str | None,
        stt_similarity: float | None,
        heard_text: str,
        reply: str,
        intent: str,
        source: str,
        action: str,
        keep_mic_open: bool,
        uploaded_audio_size_bytes: int,
        uploaded_audio_duration_ms: int | None,
        uploaded_audio_quality: str,
        uploaded_audio_peak_ratio: float | None,
        uploaded_audio_rms_ratio: float | None,
    ) -> None:
        if not self._enabled:
            return
        event_type = "voice_node_audio_ok" if stt_ok else "voice_node_audio_error"
        message = (
            f"Voice Node heard: {heard_text[:80]}"
            if stt_ok and heard_text.strip()
            else f"Voice Node STT failed: {stt_error or 'no speech'}"
        )
        payload = {
            "stt_ok": stt_ok,
            "stt_error": stt_error,
            "stt_raw_text": stt_raw_text,
            "expected_text": expected_text,
            "stt_similarity": stt_similarity,
            "heard_text": heard_text,
            "reply": reply,
            "intent": intent,
            "source": source,
            "action": action,
            "keep_mic_open": keep_mic_open,
            "uploaded_audio_size_bytes": uploaded_audio_size_bytes,
            "uploaded_audio_duration_ms": uploaded_audio_duration_ms,
            "uploaded_audio_quality": uploaded_audio_quality,
            "uploaded_audio_peak_ratio": uploaded_audio_peak_ratio,
            "uploaded_audio_rms_ratio": uploaded_audio_rms_ratio,
        }

        def operation(conn: sqlite3.Connection) -> None:
            conn.execute(
                """
                INSERT INTO voice_node_events
                    (device_id, event_type, state, ok, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    device_id,
                    event_type,
                    intent,
                    1 if stt_ok else 0,
                    json.dumps(payload, ensure_ascii=False),
                    _to_iso(received_at),
                ),
            )
            conn.execute(
                """
                INSERT INTO activity_logs
                    (event_type, device_id, message, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event_type,
                    device_id,
                    message,
                    json.dumps(payload, ensure_ascii=False),
                    _to_iso(received_at),
                ),
            )

        self._safe_write("voice node audio result", operation)

    def record_voice_node_playback_status(
        self,
        *,
        device_id: str,
        reported_at: datetime,
        stage: str,
        ok: bool,
        error: str | None,
        audio_url: str | None,
        audio_size_bytes: int | None,
    ) -> None:
        if not self._enabled:
            return
        event_type = "voice_node_playback_ok" if ok else "voice_node_playback_error"
        payload = {
            "stage": stage,
            "ok": ok,
            "error": error,
            "audio_url": audio_url,
            "audio_size_bytes": audio_size_bytes,
        }

        def operation(conn: sqlite3.Connection) -> None:
            conn.execute(
                """
                INSERT INTO voice_node_events
                    (device_id, event_type, state, ok, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    device_id,
                    event_type,
                    stage,
                    1 if ok else 0,
                    json.dumps(payload, ensure_ascii=False),
                    _to_iso(reported_at),
                ),
            )
            conn.execute(
                """
                INSERT INTO activity_logs
                    (event_type, device_id, message, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event_type,
                    device_id,
                    f"Voice Node playback {stage}: {'ok' if ok else error or 'failed'}",
                    json.dumps(payload, ensure_ascii=False),
                    _to_iso(reported_at),
                ),
            )

        self._safe_write("voice node playback status", operation)

    def get_recent_motion_events(
        self,
        device_id: str,
        limit: int = 6,
    ) -> list[MotionEvent]:
        if not self._enabled:
            return []
        try:
            self.initialize()
            with self._lock, self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT device_id, motion, sensor_timestamp, received_at
                    FROM motion_events
                    WHERE device_id = ?
                    ORDER BY received_at DESC
                    LIMIT ?
                    """,
                    (device_id, max(1, min(limit, 50))),
                ).fetchall()
        except Exception as exc:  # pragma: no cover - local filesystem dependent
            logger.warning("SQLite read failed for motion events: %s", exc)
            return []

        return [
            MotionEvent(
                device_id=str(row["device_id"]),
                motion=bool(row["motion"]),
                timestamp=_from_iso(str(row["sensor_timestamp"])),
                received_at=_from_iso(str(row["received_at"])),
            )
            for row in rows
        ]

    def count_motion_events(
        self,
        device_id: str,
        hours: int = 1,
        motion_only: bool = True,
    ) -> int:
        if not self._enabled:
            return 0
        since = datetime.now(timezone.utc) - timedelta(hours=max(1, hours))
        try:
            self.initialize()
            with self._lock, self._connect() as conn:
                if motion_only:
                    row = conn.execute(
                        """
                        SELECT COUNT(*) AS total
                        FROM motion_events
                        WHERE device_id = ? AND motion = 1 AND received_at >= ?
                        """,
                        (device_id, _to_iso(since)),
                    ).fetchone()
                else:
                    row = conn.execute(
                        """
                        SELECT COUNT(*) AS total
                        FROM motion_events
                        WHERE device_id = ? AND received_at >= ?
                        """,
                        (device_id, _to_iso(since)),
                    ).fetchone()
        except Exception as exc:  # pragma: no cover - local filesystem dependent
            logger.warning("SQLite read failed for motion count: %s", exc)
            return 0

        return int(row["total"] if row is not None else 0)

    def get_recent_activity(self, limit: int = 20) -> list[ActivityLogItem]:
        if not self._enabled:
            return []
        try:
            self.initialize()
            with self._lock, self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT id, event_type, device_id, message, payload_json, created_at
                    FROM activity_logs
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (max(1, min(limit, 100)),),
                ).fetchall()
        except Exception as exc:  # pragma: no cover - local filesystem dependent
            logger.warning("SQLite read failed for activity logs: %s", exc)
            return []

        return [
            ActivityLogItem(
                id=int(row["id"]),
                event_type=str(row["event_type"]),
                device_id=row["device_id"],
                message=str(row["message"]),
                payload=_load_payload(row["payload_json"]),
                created_at=_from_iso(str(row["created_at"])),
            )
            for row in rows
        ]

    def _safe_write(self, label: str, operation: Any) -> None:
        try:
            self.initialize()
            with self._lock, self._connect() as conn:
                operation(conn)
        except Exception as exc:  # pragma: no cover - local filesystem dependent
            logger.warning("SQLite logging failed for %s: %s", label, exc)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn


def _to_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _load_payload(value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


_sqlite_log_store: SQLiteLogStore | None = None


def get_sqlite_log_store() -> SQLiteLogStore:
    global _sqlite_log_store
    if _sqlite_log_store is None:
        settings = get_settings()
        _sqlite_log_store = SQLiteLogStore(
            db_path=resolve_project_path(settings.sqlite_log_path),
            enabled=settings.sqlite_log_enabled,
        )
    return _sqlite_log_store
