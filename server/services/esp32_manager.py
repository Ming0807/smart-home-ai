from collections import defaultdict, deque
from datetime import datetime, timezone
import logging
from threading import Lock
from uuid import uuid4

from server.config import get_settings
from server.models.esp32 import (
    CommandResult,
    CommandResultRequest,
    Esp32Capabilities,
    Esp32CapabilitiesRequest,
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
        self._commands_by_id: dict[str, RelayCommand] = {}
        self._latest_command_results: dict[str, CommandResult] = {}
        self._capabilities: dict[str, Esp32Capabilities] = {}

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
        target_device_id: str | None = None,
        gpio_pin: int | None = None,
    ) -> RelayCommand:
        with self._lock:
            command = RelayCommand(
                command_id=self._create_command_id(),
                target_device_id=target_device_id,
                channel=channel,
                gpio_pin=gpio_pin,
                action=action,
            )
            self._commands[device_id].append((command, self._now()))
            self._latest_commands[device_id] = command
            if command.command_id is not None:
                self._commands_by_id[command.command_id] = command
            return command

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
                latest_command_result=self.get_latest_command_result(device_id),
                capabilities=self.get_capabilities(device_id),
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
            latest_command_result=self.get_latest_command_result(device_id),
            capabilities=self.get_capabilities(device_id),
        )

    def get_latest_command(self, device_id: str) -> RelayCommand | None:
        with self._lock:
            return self._latest_commands.get(device_id)

    def get_command_by_id(self, command_id: str) -> RelayCommand | None:
        with self._lock:
            return self._commands_by_id.get(command_id)

    def record_command_result(
        self,
        request: CommandResultRequest,
    ) -> CommandResult:
        result = CommandResult(
            device_id=request.device_id,
            command_id=request.command_id,
            status=request.status,
            state=request.state,
            error=request.error,
            timestamp=request.timestamp,
            received_at=self._now(),
        )
        with self._lock:
            self._latest_command_results[request.device_id] = result
        return result

    def get_latest_command_result(self, device_id: str) -> CommandResult | None:
        with self._lock:
            return self._latest_command_results.get(device_id)

    def record_capabilities(
        self,
        request: Esp32CapabilitiesRequest,
    ) -> Esp32Capabilities:
        capabilities = Esp32Capabilities(
            device_id=request.device_id,
            board_type=request.board_type,
            firmware_version=request.firmware_version,
            capabilities=_dedupe_strings(request.capabilities),
            relay_pins=_dedupe_ints(request.relay_pins),
            sensor_pins=_dedupe_ints(request.sensor_pins),
            reserved_pins=_dedupe_ints(request.reserved_pins),
            i2s_pins=_dedupe_ints(request.i2s_pins),
            available_pins=_dedupe_ints(request.available_pins),
            timestamp=request.timestamp,
            received_at=self._now(),
        )
        with self._lock:
            self._capabilities[request.device_id] = capabilities
        return capabilities

    def get_capabilities(self, device_id: str) -> Esp32Capabilities | None:
        with self._lock:
            return self._capabilities.get(device_id)

    def get_pending_command_count(self, device_id: str) -> int:
        with self._lock:
            return len(self._commands[device_id])

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _create_command_id() -> str:
        return f"cmd_{uuid4().hex}"


_esp32_manager = Esp32Manager()


def get_esp32_manager() -> Esp32Manager:
    return _esp32_manager


def _dedupe_ints(values: list[int]) -> list[int]:
    return sorted({value for value in values if 0 <= value <= 48})


def _dedupe_strings(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean_value = value.strip()
        if not clean_value:
            continue
        normalized_value = clean_value.casefold()
        if normalized_value in seen:
            continue
        seen.add(normalized_value)
        result.append(clean_value[:80])
    return result
