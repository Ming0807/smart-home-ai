from collections import defaultdict, deque
from datetime import datetime, timezone
import logging
from threading import Lock

from server.config import get_settings
from server.models.esp32 import (
    DeviceHeartbeat,
    DeviceStatusResponse,
    HeartbeatRequest,
    RelayAction,
    RelayCommand,
)
from server.utils.observability import log_timing

logger = logging.getLogger(__name__)


class Esp32Manager:
    """In-memory ESP32 state and command queue.

    This keeps Phase D simple for demos and can be replaced by SQLite later
    without changing the API layer.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._heartbeats: dict[str, DeviceHeartbeat] = {}
        self._commands: defaultdict[str, deque[tuple[RelayCommand, datetime]]] = defaultdict(deque)
        self._latest_commands: dict[str, RelayCommand] = {}

    def record_heartbeat(self, request: HeartbeatRequest) -> None:
        with self._lock:
            self._heartbeats[request.device_id] = DeviceHeartbeat(
                device_id=request.device_id,
                last_seen_at=self._now(),
            )

    def enqueue_relay_command(
        self,
        device_id: str,
        action: RelayAction,
        channel: int = 1,
    ) -> None:
        with self._lock:
            command = RelayCommand(channel=channel, action=action)
            self._commands[device_id].append((command, self._now()))
            self._latest_commands[device_id] = command

    def get_next_command(self, device_id: str) -> RelayCommand | None:
        with self._lock:
            if not self._commands[device_id]:
                return None
            command, enqueued_at = self._commands[device_id].popleft()
        queue_latency_ms = (self._now() - enqueued_at).total_seconds() * 1000
        log_timing(
            logger,
            get_settings(),
            "esp32.command.dequeue",
            queue_latency_ms,
            device_id=device_id,
            action=command.action,
        )
        return command

    def get_latest_heartbeat(self, device_id: str) -> DeviceHeartbeat | None:
        with self._lock:
            return self._heartbeats.get(device_id)

    def get_device_status(
        self,
        device_id: str,
        offline_timeout_seconds: int,
    ) -> DeviceStatusResponse:
        heartbeat = self.get_latest_heartbeat(device_id)
        if heartbeat is None:
            return DeviceStatusResponse(
                device_id=device_id,
                online=False,
                last_seen_at=None,
                seconds_since_heartbeat=None,
                pending_command_count=self.get_pending_command_count(device_id),
                latest_command=self.get_latest_command(device_id),
            )

        seconds_since_heartbeat = max(
            0,
            int(round((self._now() - heartbeat.last_seen_at).total_seconds())),
        )
        return DeviceStatusResponse(
            device_id=device_id,
            online=seconds_since_heartbeat <= offline_timeout_seconds,
            last_seen_at=heartbeat.last_seen_at,
            seconds_since_heartbeat=seconds_since_heartbeat,
            pending_command_count=self.get_pending_command_count(device_id),
            latest_command=self.get_latest_command(device_id),
        )

    def get_latest_command(self, device_id: str) -> RelayCommand | None:
        with self._lock:
            return self._latest_commands.get(device_id)

    def get_pending_command_count(self, device_id: str) -> int:
        with self._lock:
            return len(self._commands[device_id])

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)


_esp32_manager = Esp32Manager()


def get_esp32_manager() -> Esp32Manager:
    return _esp32_manager
