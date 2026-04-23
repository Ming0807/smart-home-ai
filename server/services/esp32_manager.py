from collections import defaultdict, deque
from datetime import datetime, timezone
from threading import Lock

from server.models.esp32 import (
    DeviceHeartbeat,
    HeartbeatRequest,
    RelayAction,
    RelayCommand,
)


class Esp32Manager:
    """In-memory ESP32 state and command queue.

    This keeps Phase D simple for demos and can be replaced by SQLite later
    without changing the API layer.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._heartbeats: dict[str, DeviceHeartbeat] = {}
        self._commands: defaultdict[str, deque[RelayCommand]] = defaultdict(deque)

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
            self._commands[device_id].append(
                RelayCommand(channel=channel, action=action),
            )

    def get_next_command(self, device_id: str) -> RelayCommand | None:
        with self._lock:
            if not self._commands[device_id]:
                return None
            return self._commands[device_id].popleft()

    def get_latest_heartbeat(self, device_id: str) -> DeviceHeartbeat | None:
        with self._lock:
            return self._heartbeats.get(device_id)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)


_esp32_manager = Esp32Manager()


def get_esp32_manager() -> Esp32Manager:
    return _esp32_manager
